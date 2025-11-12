import os
import sys
import json
import re
from sentence_transformers import SentenceTransformer
import chromadb
from nltk.tokenize import sent_tokenize
import nltk

# -------------------------
# Download NLTK punkt if missing
# -------------------------
try:
    nltk.data.find('tokenizers/punkt_tab')
except LookupError:
    nltk.download('punkt_tab')

# -------------------------
# Helper functions
# -------------------------
def clean_text(text: str) -> str:
    """Remove emails, long numbers, and normalize whitespace."""
    # text = re.sub(r'\S+@\S+', '', text)      # remove emails
    text = re.sub(r'\d{10,}', '', text)      # remove long numbers
    text = re.sub(r'\s+', ' ', text)         # normalize spaces
    return text.strip()


def semantic_chunk_text(text: str, max_chunk_size=400, min_chunk_size=100):
    """
    Enhanced semantic chunking that preserves paragraph boundaries
    and creates more meaningful chunks.
    """
    # Split by double newlines first (paragraphs)
    paragraphs = re.split(r'\n\n+', text)
    chunks = []
    current_chunk = []
    current_size = 0

    for para in paragraphs:
        para = para.strip()
        if not para:
            continue

        words = para.split()
        para_size = len(words)

        # If single paragraph exceeds max, split it by sentences
        if para_size > max_chunk_size:
            # Save current chunk if exists
            if current_chunk:
                chunks.append(" ".join(current_chunk))
                current_chunk = []
                current_size = 0

            # Split large paragraph by sentences
            sentences = sent_tokenize(para)
            temp_chunk = []
            temp_size = 0

            for sent in sentences:
                sent_words = len(sent.split())
                if temp_size + sent_words > max_chunk_size and temp_chunk:
                    chunks.append(" ".join(temp_chunk))
                    temp_chunk = [sent]
                    temp_size = sent_words
                else:
                    temp_chunk.append(sent)
                    temp_size += sent_words

            if temp_chunk:
                chunks.append(" ".join(temp_chunk))

        elif current_size + para_size > max_chunk_size:
            # Current chunk is full, start new one
            if current_chunk:
                chunks.append(" ".join(current_chunk))
            current_chunk = [para]
            current_size = para_size
        else:
            # Add to current chunk
            current_chunk.append(para)
            current_size += para_size

    # Don't forget the last chunk
    if current_chunk:
        chunk_text = " ".join(current_chunk)
        # Only add if it meets minimum size
        if len(chunk_text.split()) >= min_chunk_size or not chunks:
            chunks.append(chunk_text)
        elif chunks:  # Merge small last chunk with previous
            chunks[-1] = chunks[-1] + " " + chunk_text

    return chunks


def chunk_text_with_overlap(text: str, chunk_size=400, overlap=50):
    """
    Fallback chunking with overlap for continuous text.
    Used when semantic chunking isn't suitable.
    """
    sentences = sent_tokenize(text)
    chunks, current, total_words = [], [], 0

    for sentence in sentences:
        words = sentence.split()
        if total_words + len(words) > chunk_size:
            if current:
                chunks.append(" ".join(current))
                # Keep last few sentences for overlap
                overlap_sentences = []
                overlap_words = 0
                for s in reversed(current):
                    s_words = len(s.split())
                    if overlap_words + s_words <= overlap:
                        overlap_sentences.insert(0, s)
                        overlap_words += s_words
                    else:
                        break
                current = overlap_sentences
                total_words = overlap_words
        current.append(sentence)
        total_words += len(words)

    if current:
        chunks.append(" ".join(current))
    return chunks


def batch_add_to_chroma(collection, chunks, client_id, max_batch_size=5000):
    """Add chunks to ChromaDB in batches to avoid size limits."""
    total_chunks = len(chunks)
    print(f"📦 Adding {total_chunks} chunks in batches of {max_batch_size}")

    for i in range(0, total_chunks, max_batch_size):
        batch_end = min(i + max_batch_size, total_chunks)
        batch_chunks = chunks[i:batch_end]

        batch_ids = [f"{client_id}_chunk_{j}" for j in range(i, batch_end)]
        batch_documents = [c["content"] for c in batch_chunks]
        batch_metadatas = []

        # Create metadata based on source type
        for c in batch_chunks:
            metadata = {
                "source": c.get("source", "unknown"),
                "title": c.get("title", "")
            }

            if c.get("source") == "crawl":
                metadata["url"] = c.get("url", "")
            elif c.get("source") == "pdf":
                metadata["filename"] = c.get("filename", "")
            elif c.get("source") == "qa":
                metadata["type"] = "custom_qa"

            batch_metadatas.append(metadata)

        batch_embeddings = [c["embedding"] for c in batch_chunks]

        print(f"  📋 Processing batch {i//max_batch_size + 1}: chunks {i+1}-{batch_end}")
        try:
            collection.add(
                documents=batch_documents,
                metadatas=batch_metadatas,
                ids=batch_ids,
                embeddings=batch_embeddings,
            )
            print(f"  ✅ Successfully added batch {i//max_batch_size + 1}")
        except Exception as e:
            print(f"  ❌ Failed to add batch {i//max_batch_size + 1}: {e}")
            raise

# -------------------------
# Main pipeline
# -------------------------
def run_pipeline(client_id: str, source_type="crawl"):
    """
    source_type: "crawl" or "pdf"
    """
    # Paths
    script_dir = os.path.dirname(os.path.abspath(__file__))  # /Chatbot/processing
    chatbot_dir = os.path.dirname(script_dir)                # /Chatbot
    project_root = os.path.dirname(chatbot_dir)              # /ProjectRoot
    # base_dir = os.path.join(project_root, "backend", "client_data", client_id)
    base_dir = os.path.join(project_root,"client_data", client_id)
    chroma_dir = os.path.join(project_root, "ChromaDatabase", "vector-database", "chroma_db")

    # Output files
    chunk_path = os.path.join(base_dir, "chunks.json")
    embed_path = os.path.join(base_dir, "embeddings.json")
    qa_path = os.path.join(base_dir, "custom_qa.json")

    chunks = []

    # -------------------------
    # Load data based on source type
    # -------------------------
    if source_type == "pdf":
        input_path = os.path.join(base_dir, "custom_pdf.txt")
        pdf_path = os.path.join(base_dir, "custom_pdf.pdf")

        if not os.path.exists(input_path):
            raise FileNotFoundError(f"❌ PDF text not found for {client_id}")

        # Get original PDF filename if available
        pdf_filename = "custom_pdf.pdf"
        if os.path.exists(pdf_path):
            pdf_filename = os.path.basename(pdf_path)

        with open(input_path, "r", encoding="utf-8") as f:
            text = f.read()

        cleaned_text = clean_text(text)
        # Use semantic chunking for PDFs
        for c in semantic_chunk_text(cleaned_text, max_chunk_size=400):
            chunks.append({
                "source": "pdf",
                "filename": pdf_filename,
                "title": f"PDF: {pdf_filename}",
                "content": c
            })
        print(f"📄 Loaded PDF and created {len(chunks)} semantic chunks")

    else:  # crawl
        input_path = os.path.join(base_dir, "website_content.json")
        if not os.path.exists(input_path):
            raise FileNotFoundError(f"❌ Crawled data not found for {client_id}")

        with open(input_path, "r", encoding="utf-8") as f:
            pages = json.load(f)

        for page in pages:
            url, title, content = page.get("url"), page.get("title", ""), page.get("content", "")
            if not content.strip():
                continue
            text = clean_text(content)
            # Use semantic chunking for web content
            for c in semantic_chunk_text(text, max_chunk_size=400):
                chunks.append({
                    "source": "crawl",
                    "url": url,
                    "title": title,
                    "content": c
                })
        print(f"🌐 Loaded website crawl and created {len(chunks)} semantic chunks")

    # -------------------------
    # Add custom Q&A (works with both sources)
    # -------------------------
    if os.path.exists(qa_path):
        with open(qa_path, "r", encoding="utf-8") as f:
            qa_pairs = json.load(f)
        for qa in qa_pairs:
            # Handle both "question" and "questions" format
            questions = qa.get("questions", [qa.get("question")]) if qa.get("questions") else [qa.get("question")]
            answer = qa.get("answer")

            if questions and answer:
                for q in questions:
                    if q:  # Skip empty questions
                        chunks.append({
                            "source": "qa",
                            "title": "Custom Q&A",
                            "content": f"Q: {q}\nA: {answer}"
                        })
        print(f"➕ Added {len(qa_pairs)} custom Q&A entries")

    # Save chunks
    with open(chunk_path, "w", encoding="utf-8") as f:
        json.dump(chunks, f, indent=2, ensure_ascii=False)
    print(f"✅ Saved {len(chunks)} chunks to {chunk_path}")

    # -------------------------
    # Generate embeddings
    # -------------------------
    print("🔄 Generating embeddings...")
    model = SentenceTransformer("multi-qa-mpnet-base-dot-v1")
    embeddings = model.encode([c["content"] for c in chunks], show_progress_bar=True)
    for c, e in zip(chunks, embeddings):
        c["embedding"] = e.tolist()

    with open(embed_path, "w", encoding="utf-8") as f:
        json.dump(chunks, f, indent=2, ensure_ascii=False)
    print(f"✅ Saved embeddings for {len(chunks)} chunks to {embed_path}")

    # -------------------------
    # Store in ChromaDB
    # -------------------------
    try:
            client = chromadb.PersistentClient(path=chroma_dir)

            # Delete existing collection if exists
            try:
                client.delete_collection(name=client_id.lower())
                print(f"🗑️  Deleted existing collection '{client_id.lower()}'")
            except:
                pass

            # CRITICAL: Create collection WITHOUT embedding function
            # This prevents ChromaDB from using its own cached embeddings
            coll = client.get_or_create_collection(
                name=client_id.lower(),
                metadata={"hnsw:space": "cosine"}  # Use cosine similarity
            )

            batch_add_to_chroma(coll, chunks, client_id)

            print(f"🎉 Successfully ingested {len(chunks)} chunks into Chroma collection '{client_id.lower()}'")
            print(f"🔍 Collection now contains {coll.count()} documents")

    except Exception as e:
        raise RuntimeError(f"❌ Failed to store in ChromaDB: {e}")

# -------------------------
# Entrypoint
# -------------------------
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python embed_pipeline.py <client_id> [source_type]")
        print("  source_type: 'crawl' (default) or 'pdf'")
        sys.exit(1)
    client_id = sys.argv[1]
    source_type = sys.argv[2] if len(sys.argv) > 2 else "crawl"
    run_pipeline(client_id, source_type)
