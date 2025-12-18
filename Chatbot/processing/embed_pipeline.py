"""
Enhanced Universal Embedding Pipeline with LangChain
Works for any website with intelligent chunking and metadata preservation
"""

import os
import sys
import json
import re
from typing import List, Dict, Any
from sentence_transformers import SentenceTransformer
import chromadb
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document
import nltk

# Download NLTK data if needed
try:
    nltk.data.find('tokenizers/punkt_tab')
except LookupError:
    nltk.download('punkt_tab')

# ──────────────────────────────────────────────────────────────────────────────
# Advanced Text Processing
# ──────────────────────────────────────────────────────────────────────────────

class SmartTextCleaner:
    """Intelligent text cleaning that preserves semantic meaning."""

    @staticmethod
    def clean_text(text: str, preserve_structure: bool = True) -> str:
        """Clean text while preserving important structure."""

        # Remove excessive whitespace but preserve paragraph breaks
        if preserve_structure:
            # Preserve double newlines (paragraph breaks)
            text = re.sub(r'\n{3,}', '\n\n', text)
            # Normalize single line breaks to spaces
            text = re.sub(r'(?<!\n)\n(?!\n)', ' ', text)

        # Remove very long numbers (IDs, not meaningful data)
        text = re.sub(r'\b\d{15,}\b', '', text)

        # Clean up excessive punctuation
        text = re.sub(r'([.!?]){3,}', r'\1', text)

        # Normalize spaces
        text = re.sub(r' +', ' ', text)

        # Remove noise patterns common in web scraping
        noise_patterns = [
            r'Skip to (main )?content',
            r'Cookie (Policy|Notice|Consent)',
            r'Accept (all )?cookies',
            r'JavaScript (is )?(disabled|required)',
            r'Loading\.\.\.+',
            r'\[.*?\](\s*\[.*?\])+',  # Multiple empty brackets
        ]

        for pattern in noise_patterns:
            text = re.sub(pattern, '', text, flags=re.IGNORECASE)

        return text.strip()

    @staticmethod
    def extract_metadata(text: str) -> Dict[str, Any]:
        """Extract useful metadata from text for better retrieval."""
        metadata = {}

        # Detect if text contains contact information
        if re.search(r'\b[\w\.-]+@[\w\.-]+\.\w+\b', text):
            metadata['contains_contact'] = True

        # Detect pricing information
        if re.search(r'[\$€£¥₹]\s*\d+|price|cost|fee', text, re.IGNORECASE):
            metadata['contains_pricing'] = True

        # Detect timing/schedule information
        if re.search(r'\d{1,2}:\d{2}|hours?|schedule|timing', text, re.IGNORECASE):
            metadata['contains_timing'] = True

        # Detect location information
        if re.search(r'address|location|street|city', text, re.IGNORECASE):
            metadata['contains_location'] = True

        return metadata


class UniversalChunker:
    """
    Universal document chunker that adapts to content type.
    Uses LangChain's RecursiveCharacterTextSplitter with smart separators.
    """

    def __init__(
        self,
        chunk_size: int = 500,
        chunk_overlap: int = 100,
        min_chunk_size: int = 50
    ):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.min_chunk_size = min_chunk_size

        # Smart separators that preserve semantic boundaries
        self.separators = [
            "\n\n\n",  # Major section breaks
            "\n\n",    # Paragraph breaks
            "\n",      # Line breaks
            ". ",      # Sentence endings
            "! ",      # Exclamations
            "? ",      # Questions
            "; ",      # Semi-colons
            ", ",      # Commas
            " ",       # Words
            ""         # Characters
        ]

    def chunk_document(
        self,
        text: str,
        metadata: Dict[str, Any] = None
    ) -> List[Document]:
        """
        Chunk document intelligently based on content structure.

        Returns LangChain Document objects with rich metadata.
        """
        if not text or len(text.strip()) < self.min_chunk_size:
            return []

        # Detect document type and adjust chunking strategy
        doc_type = self._detect_document_type(text)

        # Use different strategies based on document type
        if doc_type == 'structured':
            # Lists, tables, structured data - smaller chunks
            chunk_size = self.chunk_size - 100
            overlap = self.chunk_overlap - 20
        elif doc_type == 'narrative':
            # Stories, articles - larger chunks for context
            chunk_size = self.chunk_size + 100
            overlap = self.chunk_overlap + 30
        else:
            chunk_size = self.chunk_size
            overlap = self.chunk_overlap

        # Create text splitter
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=overlap,
            length_function=len,
            separators=self.separators,
            keep_separator=True
        )

        # Split text into chunks
        chunks = text_splitter.split_text(text)

        # Create Document objects with metadata
        documents = []
        for i, chunk in enumerate(chunks):
            # Skip chunks that are too small
            if len(chunk.strip()) < self.min_chunk_size:
                continue

            # Build chunk metadata
            chunk_metadata = metadata.copy() if metadata else {}
            chunk_metadata['chunk_index'] = i
            chunk_metadata['total_chunks'] = len(chunks)
            chunk_metadata['doc_type'] = doc_type

            # Extract chunk-specific metadata
            chunk_info = SmartTextCleaner.extract_metadata(chunk)
            chunk_metadata.update(chunk_info)

            documents.append(Document(
                page_content=chunk.strip(),
                metadata=chunk_metadata
            ))

        return documents

    @staticmethod
    def _detect_document_type(text: str) -> str:
        """Detect document type to adapt chunking strategy."""
        # Count structural elements
        list_items = len(re.findall(r'^\s*[-•*]\s', text, re.MULTILINE))
        numbered_items = len(re.findall(r'^\s*\d+[\.)]\s', text, re.MULTILINE))
        paragraphs = len(re.findall(r'\n\n', text))

        # Structured document (lots of lists/numbered items)
        if list_items + numbered_items > 5:
            return 'structured'

        # Narrative document (lots of paragraphs)
        if paragraphs > 3 and len(text) > 1000:
            return 'narrative'

        return 'general'


# ──────────────────────────────────────────────────────────────────────────────
# Enhanced Pipeline
# ──────────────────────────────────────────────────────────────────────────────

class UniversalEmbeddingPipeline:
    """
    Universal embedding pipeline that works for any website/document.
    """

    def __init__(
        self,
        client_id: str,
        embedding_model: str = "multi-qa-mpnet-base-dot-v1"
    ):
        self.client_id = client_id
        self.embedding_model_name = embedding_model
        self.model = None
        self.cleaner = SmartTextCleaner()
        self.chunker = UniversalChunker(
            chunk_size=500,
            chunk_overlap=100,
            min_chunk_size=50
        )

        # Setup paths
        self._setup_paths()

    def _setup_paths(self):
        """Setup directory structure."""
        script_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(os.path.dirname(script_dir))

        self.client_dir = os.path.join(project_root, "client_data", self.client_id)
        self.chroma_dir = os.path.join(project_root, "ChromaDatabase", "vector-database", "chroma_db")

        # Create directories
        os.makedirs(self.client_dir, exist_ok=True)
        os.makedirs(self.chroma_dir, exist_ok=True)

    def _load_embedding_model(self):
        """Lazy load embedding model."""
        if self.model is None:
            print(f"🔄 Loading embedding model: {self.embedding_model_name}")
            self.model = SentenceTransformer(self.embedding_model_name)

    def process_website(self, max_pages: int = None) -> Dict[str, Any]:
        """
        Process website crawl data.

        Returns processing statistics.
        """
        print("\n" + "="*60)
        print("🌐 Processing Website Content")
        print("="*60)

        # Load website content
        content_path = os.path.join(self.client_dir, "website_content.json")
        if not os.path.exists(content_path):
            raise FileNotFoundError(f"Website content not found: {content_path}")

        with open(content_path, 'r', encoding='utf-8') as f:
            pages = json.load(f)

        if max_pages:
            pages = pages[:max_pages]

        print(f"📄 Loaded {len(pages)} web pages")

        # Process pages
        all_documents = []
        stats = {
            'total_pages': len(pages),
            'processed_pages': 0,
            'total_chunks': 0,
            'skipped_pages': 0
        }

        for page in pages:
            url = page.get('url', '')
            title = page.get('title', 'Untitled')
            content = page.get('content', '')

            if not content or len(content.strip()) < 100:
                stats['skipped_pages'] += 1
                continue

            # Clean content
            cleaned_content = self.cleaner.clean_text(content, preserve_structure=True)

            # Create base metadata
            base_metadata = {
                'source': 'crawl',
                'url': url,
                'title': title,
                'page_type': page.get('content_type', 'general')
            }

            # Chunk document
            documents = self.chunker.chunk_document(cleaned_content, base_metadata)

            if documents:
                all_documents.extend(documents)
                stats['processed_pages'] += 1
                stats['total_chunks'] += len(documents)
                print(f"  ✅ {title[:50]}... → {len(documents)} chunks")
            else:
                stats['skipped_pages'] += 1

        return all_documents, stats

    def process_pdf(self) -> tuple[List[Document], Dict[str, Any]]:
        """
        Process PDF document.

        Returns documents and statistics.
        """
        print("\n" + "="*60)
        print("📄 Processing PDF Content")
        print("="*60)

        # Load PDF text
        pdf_text_path = os.path.join(self.client_dir, "custom_pdf.txt")
        if not os.path.exists(pdf_text_path):
            raise FileNotFoundError(f"PDF text not found: {pdf_text_path}")

        with open(pdf_text_path, 'r', encoding='utf-8') as f:
            text = f.read()

        # Get PDF filename
        pdf_path = os.path.join(self.client_dir, "custom_pdf.pdf")
        pdf_filename = os.path.basename(pdf_path) if os.path.exists(pdf_path) else "document.pdf"

        print(f"📄 Loaded PDF: {pdf_filename}")

        # Clean text
        cleaned_text = self.cleaner.clean_text(text, preserve_structure=True)

        # Create metadata
        metadata = {
            'source': 'pdf',
            'filename': pdf_filename,
            'title': f"PDF: {pdf_filename}"
        }

        # Chunk document
        documents = self.chunker.chunk_document(cleaned_text, metadata)

        stats = {
            'filename': pdf_filename,
            'total_chunks': len(documents),
            'original_length': len(text),
            'cleaned_length': len(cleaned_text)
        }

        print(f"  ✅ Generated {len(documents)} semantic chunks")

        return documents, stats

    def process_custom_qa(self) -> tuple[List[Document], Dict[str, Any]]:
        """
        Process custom Q&A pairs.

        Returns documents and statistics.
        """
        qa_path = os.path.join(self.client_dir, "custom_qa.json")

        if not os.path.exists(qa_path):
            return [], {'total_qa': 0}

        print("\n" + "="*60)
        print("💬 Processing Custom Q&A")
        print("="*60)

        with open(qa_path, 'r', encoding='utf-8') as f:
            qa_pairs = json.load(f)

        documents = []

        for qa in qa_pairs:
            # Handle both formats
            questions = qa.get('questions', [])
            if not questions and 'question' in qa:
                questions = [qa['question']]

            answer = qa.get('answer', '')

            if not questions or not answer:
                continue

            # Create a document for each Q&A pair
            # Format: Q: question\nA: answer
            for question in questions:
                content = f"Q: {question}\nA: {answer}"

                metadata = {
                    'source': 'qa',
                    'type': 'custom_qa',
                    'title': 'Custom Q&A',
                    'question': question
                }

                # Add any additional metadata from QA
                if 'metadata' in qa:
                    metadata.update(qa['metadata'])

                documents.append(Document(
                    page_content=content,
                    metadata=metadata
                ))

        stats = {
            'total_qa': len(qa_pairs),
            'total_questions': len(documents)
        }

        print(f"  ✅ Loaded {len(documents)} Q&A entries")

        return documents, stats

    def embed_documents(self, documents: List[Document]) -> List[Dict[str, Any]]:
        """
        Generate embeddings for documents.

        Returns list of dicts with content, metadata, and embeddings.
        """
        if not documents:
            return []

        self._load_embedding_model()

        print(f"\n🔄 Generating embeddings for {len(documents)} chunks...")

        # Extract text content
        texts = [doc.page_content for doc in documents]

        # Generate embeddings with progress bar
        embeddings = self.model.encode(
            texts,
            show_progress_bar=True,
            batch_size=32
        )

        # Combine everything
        embedded_docs = []
        for doc, embedding in zip(documents, embeddings):
            embedded_docs.append({
                'content': doc.page_content,
                'metadata': doc.metadata,
                'embedding': embedding.tolist()
            })

        return embedded_docs

    def store_in_chroma(self, embedded_docs: List[Dict[str, Any]], batch_size: int = 100):
        """
        Store embedded documents in ChromaDB with batching.
        """
        if not embedded_docs:
            print("⚠️ No documents to store")
            return

        print(f"\n📦 Storing {len(embedded_docs)} documents in ChromaDB...")

        # Initialize ChromaDB
        client = chromadb.PersistentClient(path=self.chroma_dir)

        # Delete existing collection
        collection_name = self.client_id.lower()
        try:
            client.delete_collection(name=collection_name)
            print(f"🗑️  Deleted existing collection '{collection_name}'")
        except:
            pass

        # Create new collection
        collection = client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"}
        )

        # Add documents in batches
        total_docs = len(embedded_docs)

        for i in range(0, total_docs, batch_size):
            batch_end = min(i + batch_size, total_docs)
            batch = embedded_docs[i:batch_end]

            batch_ids = [f"{self.client_id}_chunk_{j}" for j in range(i, batch_end)]
            batch_documents = [doc['content'] for doc in batch]
            batch_metadatas = [doc['metadata'] for doc in batch]
            batch_embeddings = [doc['embedding'] for doc in batch]

            print(f"  📋 Batch {i//batch_size + 1}/{(total_docs-1)//batch_size + 1}: chunks {i+1}-{batch_end}")

            try:
                collection.add(
                    ids=batch_ids,
                    documents=batch_documents,
                    metadatas=batch_metadatas,
                    embeddings=batch_embeddings
                )
                print(f"  ✅ Successfully stored batch")
            except Exception as e:
                print(f"  ❌ Error storing batch: {e}")
                raise

        print(f"\n🎉 Successfully stored {total_docs} documents")
        print(f"📊 Collection '{collection_name}' now contains {collection.count()} documents")

    def save_artifacts(self, all_documents: List[Document], embedded_docs: List[Dict[str, Any]]):
        """Save processing artifacts for debugging."""
        # Save chunks (without embeddings for readability)
        chunks_path = os.path.join(self.client_dir, "chunks.json")
        chunks_data = [
            {
                'content': doc.page_content,
                'metadata': doc.metadata
            }
            for doc in all_documents
        ]

        with open(chunks_path, 'w', encoding='utf-8') as f:
            json.dump(chunks_data, f, indent=2, ensure_ascii=False)

        print(f"💾 Saved chunks to {chunks_path}")

        # Save embeddings
        embeddings_path = os.path.join(self.client_dir, "embeddings.json")
        with open(embeddings_path, 'w', encoding='utf-8') as f:
            json.dump(embedded_docs, f, indent=2, ensure_ascii=False)

        print(f"💾 Saved embeddings to {embeddings_path}")

    def run(self, source_type: str = 'crawl'):
        """
        Run complete pipeline.

        Args:
            source_type: 'crawl', 'pdf', or 'both'
        """
        print("\n" + "="*60)
        print(f"🚀 Starting Enhanced Embedding Pipeline")
        print(f"Client: {self.client_id}")
        print(f"Source: {source_type}")
        print("="*60)

        all_documents = []
        total_stats = {}

        # Process based on source type
        if source_type in ['crawl', 'both']:
            try:
                docs, stats = self.process_website()
                all_documents.extend(docs)
                total_stats['website'] = stats
            except FileNotFoundError as e:
                print(f"⚠️ {e}")

        if source_type in ['pdf', 'both']:
            try:
                docs, stats = self.process_pdf()
                all_documents.extend(docs)
                total_stats['pdf'] = stats
            except FileNotFoundError as e:
                print(f"⚠️ {e}")

        # Always try to process custom Q&A
        try:
            docs, stats = self.process_custom_qa()
            all_documents.extend(docs)
            total_stats['custom_qa'] = stats
        except Exception as e:
            print(f"⚠️ Error processing Q&A: {e}")

        if not all_documents:
            raise RuntimeError("❌ No documents to process! Check your input files.")

        print(f"\n📊 Total documents to embed: {len(all_documents)}")

        # Generate embeddings
        embedded_docs = self.embed_documents(all_documents)

        # Store in ChromaDB
        self.store_in_chroma(embedded_docs)

        # Save artifacts
        self.save_artifacts(all_documents, embedded_docs)

        # Print summary
        print("\n" + "="*60)
        print("✅ PIPELINE COMPLETE")
        print("="*60)
        print(f"📊 Processing Statistics:")
        for source, stats in total_stats.items():
            print(f"\n{source.upper()}:")
            for key, value in stats.items():
                print(f"  {key}: {value}")
        print(f"\n📦 Total chunks generated: {len(all_documents)}")
        print(f"🔢 Total embeddings: {len(embedded_docs)}")
        print("="*60 + "\n")


# ──────────────────────────────────────────────────────────────────────────────
# CLI Interface
# ──────────────────────────────────────────────────────────────────────────────

def main():
    import argparse

    parser = argparse.ArgumentParser(
        description='Enhanced Universal Embedding Pipeline'
    )
    parser.add_argument(
        'client_id',
        help='Client identifier'
    )
    parser.add_argument(
        '--source',
        choices=['crawl', 'pdf', 'both'],
        default='crawl',
        help='Data source type (default: crawl)'
    )
    parser.add_argument(
        '--embedding-model',
        default='multi-qa-mpnet-base-dot-v1',
        help='Sentence transformer model name'
    )

    args = parser.parse_args()

    try:
        pipeline = UniversalEmbeddingPipeline(
            client_id=args.client_id,
            embedding_model=args.embedding_model
        )
        pipeline.run(source_type=args.source)
    except Exception as e:
        print(f"\n❌ Pipeline failed: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()