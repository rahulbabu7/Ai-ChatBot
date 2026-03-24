"""
Enhanced Universal Embedding Pipeline with Structure Preservation
Handles tables, lists, notes, and maintains semantic relationships
"""

import os
import sys
import json
import re
from typing import List, Dict, Any, Optional
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
# Structured Content Processor
# ──────────────────────────────────────────────────────────────────────────────

class StructuredContentProcessor:
    """Process structured content while maintaining semantic relationships."""

    @staticmethod
    def extract_structured_elements(content: str) -> Dict[str, Any]:
        """
        Extract structured elements (tables, lists, notes) from content.

        Returns:
            Dictionary with separated text, tables, lists, and notes
        """
        result = {
            'main_text': '',
            'tables': [],
            'lists': [],
            'notes': []
        }

        # Split content into sections
        sections = content.split('='*50)

        current_section = 'main'
        text_parts = []

        for section in sections:
            section = section.strip()
            if not section:
                continue

            # Detect section type
            if 'STRUCTURED TABLES' in section:
                current_section = 'tables'
                # Extract tables
                table_blocks = re.split(r'\n\n(?=\|)', section)
                for block in table_blocks[1:]:  # Skip header
                    if block.strip().startswith('|'):
                        # Extract context
                        context_match = re.search(r'\*\*Context:\*\*\s*(.+?)(?=\n\|)', block)
                        note_match = re.search(r'\*\*Note:\*\*\s*(.+?)$', block, re.MULTILINE)

                        table_text = '\n'.join([line for line in block.split('\n') if line.strip().startswith('|')])

                        result['tables'].append({
                            'context': context_match.group(1).strip() if context_match else '',
                            'content': table_text,
                            'note': note_match.group(1).strip() if note_match else ''
                        })

            elif 'IMPORTANT LISTS' in section:
                current_section = 'lists'
                # Extract lists
                list_blocks = section.split('\n\n')
                current_list = None
                for block in list_blocks[1:]:
                    if block.strip().startswith('**') and block.strip().endswith('**'):
                        # Context for list
                        if current_list:
                            result['lists'].append(current_list)
                        current_list = {
                            'context': block.strip('*').strip(),
                            'items': []
                        }
                    elif block.strip() and (block.strip()[0].isdigit() or block.strip().startswith('-')):
                        if current_list:
                            items = [item.strip() for item in block.split('\n') if item.strip()]
                            current_list['items'].extend(items)
                if current_list:
                    result['lists'].append(current_list)

            elif 'IMPORTANT NOTES' in section:
                current_section = 'notes'
                # Extract notes
                note_lines = [line.strip() for line in section.split('\n') if line.strip() and not line.strip() == 'IMPORTANT NOTES']
                # Remove numbering
                notes = [re.sub(r'^\d+\.\s*', '', note) for note in note_lines if note]
                result['notes'] = notes

            elif current_section == 'main':
                text_parts.append(section)

        result['main_text'] = '\n\n'.join(text_parts).strip()

        return result

    @staticmethod
    def create_table_document(table: Dict[str, str], base_metadata: Dict) -> Optional[Document]:
        """Create a document for a table with rich context."""
        if not table['content']:
            return None

        # Build comprehensive table representation
        parts = []

        if table['context']:
            parts.append(f"Table Context: {table['context']}")

        parts.append("Table Data:")
        parts.append(table['content'])

        if table['note']:
            parts.append(f"\nImportant Note: {table['note']}")

        content = '\n'.join(parts)

        # Create metadata
        metadata = base_metadata.copy()
        metadata.update({
            'content_type': 'table',
            'has_context': bool(table['context']),
            'has_note': bool(table['note']),
            'is_structured': True
        })

        return Document(page_content=content, metadata=metadata)

    @staticmethod
    def create_list_document(lst: Dict[str, Any], base_metadata: Dict) -> Optional[Document]:
        """Create a document for a list with context."""
        if not lst['items']:
            return None

        parts = []

        if lst['context']:
            parts.append(f"List Topic: {lst['context']}")

        parts.append("Items:")
        parts.extend(lst['items'])

        content = '\n'.join(parts)

        metadata = base_metadata.copy()
        metadata.update({
            'content_type': 'list',
            'num_items': len(lst['items']),
            'is_structured': True
        })

        return Document(page_content=content, metadata=metadata)


# ──────────────────────────────────────────────────────────────────────────────
# Advanced Text Processing
# ──────────────────────────────────────────────────────────────────────────────

class SmartTextCleaner:
    """Intelligent text cleaning that preserves semantic meaning."""

    @staticmethod
    def clean_text(text: str, preserve_structure: bool = True) -> str:
        """Clean text while preserving important structure."""
        if preserve_structure:
            text = re.sub(r'\n{3,}', '\n\n', text)
            text = re.sub(r'(?<!\n)\n(?!\n)', ' ', text)

        text = re.sub(r'\b\d{15,}\b', '', text)
        text = re.sub(r'([.!?]){3,}', r'\1', text)
        text = re.sub(r' +', ' ', text)

        noise_patterns = [
            r'Skip to (main )?content',
            r'Cookie (Policy|Notice|Consent)',
            r'Accept (all )?cookies',
            r'JavaScript (is )?(disabled|required)',
            r'Loading\.\.\.+',
            r'\[.*?\](\s*\[.*?\])+',
        ]

        for pattern in noise_patterns:
            text = re.sub(pattern, '', text, flags=re.IGNORECASE)

        return text.strip()

    @staticmethod
    def extract_metadata(text: str) -> Dict[str, Any]:
        """Extract useful metadata from text for better retrieval."""
        metadata = {}

        if re.search(r'\b[\w\.-]+@[\w\.-]+\.\w+\b', text):
            metadata['contains_contact'] = True

        # Enhanced financial detection
        if re.search(r'[\$€£¥₹]\s*\d+|price|cost|fee|scholarship|tuition', text, re.IGNORECASE):
            metadata['contains_pricing'] = True

        # Detect table content
        if re.search(r'\|.*\|.*\|', text):
            metadata['contains_table'] = True

        if re.search(r'\d{1,2}:\d{2}|hours?|schedule|timing', text, re.IGNORECASE):
            metadata['contains_timing'] = True

        if re.search(r'address|location|street|city', text, re.IGNORECASE):
            metadata['contains_location'] = True

        return metadata


# ──────────────────────────────────────────────────────────────────────────────
# Smart Chunker
# ──────────────────────────────────────────────────────────────────────────────

class UniversalChunker:
    """Universal document chunker with special handling for structured content."""

    def __init__(
        self,
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
        min_chunk_size: int = 50
    ):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.min_chunk_size = min_chunk_size

        self.separators = [
            "\n\n\n",
            "\n\n",
            "\n",
            ". ",
            "! ",
            "? ",
            "; ",
            ", ",
            " ",
            ""
        ]

    def chunk_document(
        self,
        text: str,
        metadata: Dict[str, Any] = None
    ) -> List[Document]:
        """Chunk document intelligently based on content structure."""
        if not text or len(text.strip()) < self.min_chunk_size:
            return []

        # Detect if this is table content (needs special handling)
        is_table = '|' in text and text.count('|') > 10

        if is_table:
            # Tables: keep together if possible, don't split across rows
            chunk_size = min(self.chunk_size * 2, 2000)  # Larger chunks for tables
            overlap = 80
            separators = ["\n|", "\n\n", "\n"]  # Split at row boundaries
        else:
            doc_type = self._detect_document_type(text)
            if doc_type == 'structured':
                chunk_size = self.chunk_size - 150
                overlap = self.chunk_overlap - 40
            elif doc_type == 'narrative':
                chunk_size = self.chunk_size + 200
                overlap = self.chunk_overlap + 50
            else:
                chunk_size = self.chunk_size
                overlap = self.chunk_overlap
            separators = self.separators

        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=overlap,
            length_function=len,
            separators=separators,
            keep_separator=True
        )

        chunks = text_splitter.split_text(text)

        documents = []
        for i, chunk in enumerate(chunks):
            if len(chunk.strip()) < self.min_chunk_size:
                continue

            chunk_metadata = metadata.copy() if metadata else {}
            chunk_metadata['chunk_index'] = i
            chunk_metadata['total_chunks'] = len(chunks)

            if is_table:
                chunk_metadata['contains_table'] = True

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
        list_items = len(re.findall(r'^\s*[-•*]\s', text, re.MULTILINE))
        numbered_items = len(re.findall(r'^\s*\d+[\.)]\s', text, re.MULTILINE))
        paragraphs = len(re.findall(r'\n\n', text))

        if list_items + numbered_items > 5:
            return 'structured'

        if paragraphs > 3 and len(text) > 1000:
            return 'narrative'

        return 'general'


# ──────────────────────────────────────────────────────────────────────────────
# Enhanced Pipeline
# ──────────────────────────────────────────────────────────────────────────────

class UniversalEmbeddingPipeline:
    """Universal embedding pipeline with structure preservation."""

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
            chunk_size=600,
            chunk_overlap=100,
            min_chunk_size=50
        )
        self.structure_processor = StructuredContentProcessor()

        self._setup_paths()

    def _setup_paths(self):
        """Setup directory structure."""
        script_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(os.path.dirname(script_dir))

        self.client_dir = os.path.join(project_root, "client_data", self.client_id)
        self.chroma_dir = os.path.join(project_root, "ChromaDatabase", "vector-database", "chroma_db")

        os.makedirs(self.client_dir, exist_ok=True)
        os.makedirs(self.chroma_dir, exist_ok=True)

    def _load_embedding_model(self):
        """Lazy load embedding model."""
        if self.model is None:
            print(f"🔄 Loading embedding model: {self.embedding_model_name}")
            self.model = SentenceTransformer(self.embedding_model_name)

    def process_website(self, max_pages: int = None) -> tuple[List[Document], Dict[str, Any]]:
        """Process website crawl data with structure preservation."""
        print("\n" + "="*60)
        print("🌐 Processing Website Content (Structure-Aware)")
        print("="*60)

        content_path = os.path.join(self.client_dir, "website_content.json")
        if not os.path.exists(content_path):
            raise FileNotFoundError(f"Website content not found: {content_path}")

        with open(content_path, 'r', encoding='utf-8') as f:
            pages = json.load(f)

        if max_pages:
            pages = pages[:max_pages]

        print(f"📄 Loaded {len(pages)} web pages")

        all_documents = []
        stats = {
            'total_pages': len(pages),
            'processed_pages': 0,
            'total_chunks': 0,
            'tables_processed': 0,
            'lists_processed': 0,
            'notes_processed': 0,
            'skipped_pages': 0
        }

        for page in pages:
            url = page.get('url', '')
            title = page.get('title', 'Untitled')
            content = page.get('content', '')

            # Check for new structured data format
            structured_data = page.get('structured_data', {})
            page_metadata = page.get('metadata', {})

            if not content or len(content.strip()) < 100:
                stats['skipped_pages'] += 1
                continue

            # Base metadata
            base_metadata = {
                'source': 'crawl',
                'url': url,
                'title': title,
                'page_type': page_metadata.get('content_type', 'general'),
                'has_tables': page_metadata.get('has_tables', False),
                'has_lists': page_metadata.get('has_lists', False)
            }

            # Process structured content if available
            if structured_data:
                # Process tables separately
                tables = structured_data.get('tables', [])
                for table_data in tables:
                    table_doc = self.structure_processor.create_table_document(
                        {
                            'context': table_data.get('context_before', ''),
                            'content': table_data.get('markdown', ''),
                            'note': table_data.get('context_after', '')
                        },
                        base_metadata
                    )
                    if table_doc:
                        all_documents.append(table_doc)
                        stats['tables_processed'] += 1

                # Process lists separately
                lists = structured_data.get('lists', [])
                for list_data in lists:
                    list_doc = self.structure_processor.create_list_document(
                        {
                            'context': list_data.get('context', ''),
                            'items': list_data.get('items', [])
                        },
                        base_metadata
                    )
                    if list_doc:
                        all_documents.append(list_doc)
                        stats['lists_processed'] += 1

                # Process notes
                notes = structured_data.get('notes', [])
                if notes:
                    notes_content = "Important Information:\n\n" + "\n\n".join([f"• {note}" for note in notes])
                    note_meta = base_metadata.copy()
                    note_meta['content_type'] = 'notes'
                    note_meta['is_structured'] = True

                    all_documents.append(Document(
                        page_content=notes_content,
                        metadata=note_meta
                    ))
                    stats['notes_processed'] += len(notes)

            # Extract and process structured elements from content string
            structured = self.structure_processor.extract_structured_elements(content)

            # Clean main text
            main_text = self.cleaner.clean_text(structured['main_text'], preserve_structure=True)

            if main_text:
                # Chunk main text
                documents = self.chunker.chunk_document(main_text, base_metadata)
                all_documents.extend(documents)

            # Process embedded tables (if not already in structured_data)
            if not structured_data.get('tables') and structured['tables']:
                for table in structured['tables']:
                    table_doc = self.structure_processor.create_table_document(table, base_metadata)
                    if table_doc:
                        all_documents.append(table_doc)
                        stats['tables_processed'] += 1

            # Process embedded lists
            if not structured_data.get('lists') and structured['lists']:
                for lst in structured['lists']:
                    list_doc = self.structure_processor.create_list_document(lst, base_metadata)
                    if list_doc:
                        all_documents.append(list_doc)
                        stats['lists_processed'] += 1

            if len(all_documents) > stats['total_chunks']:
                stats['processed_pages'] += 1
                new_chunks = len(all_documents) - stats['total_chunks']
                stats['total_chunks'] = len(all_documents)
                print(f"  ✅ {title[:50]}... → {new_chunks} chunks (T:{stats['tables_processed']} L:{stats['lists_processed']})")
            else:
                stats['skipped_pages'] += 1

        return all_documents, stats

    def process_pdf(self) -> tuple[List[Document], Dict[str, Any]]:
        """Process all uploaded PDFs for this client.

        Supports the new multi-PDF structure (pdfs/ directory with manifest.json).
        Falls back to legacy single-PDF (custom_pdf.txt) for backward compatibility.
        """
        print("\n" + "="*60)
        print("📄 Processing PDF Content")
        print("="*60)

        all_documents: List[Document] = []
        total_stats: Dict[str, Any] = {"pdfs_processed": 0, "total_chunks": 0}

        # ── New multi-PDF structure ───────────────────────────────────────────
        manifest_path = os.path.join(self.client_dir, "pdfs", "manifest.json")
        if os.path.exists(manifest_path):
            with open(manifest_path) as f:
                manifest = json.load(f)

            for entry in manifest:
                pdf_id = entry["pdf_id"]
                original_name = entry.get("original_name", "document.pdf")
                text_path = os.path.join(self.client_dir, "pdfs", f"{pdf_id}.txt")

                if not os.path.exists(text_path):
                    print(f"  ⚠️ Missing text for PDF {original_name} ({pdf_id}), skipping")
                    continue

                with open(text_path, 'r', encoding='utf-8') as f:
                    text = f.read()

                print(f"  📄 Processing: {original_name}")
                cleaned_text = self.cleaner.clean_text(text, preserve_structure=True)

                metadata = {
                    'source': 'pdf',
                    'pdf_id': pdf_id,
                    'filename': original_name,
                    'title': f"PDF: {original_name}"
                }

                docs = self.chunker.chunk_document(cleaned_text, metadata)
                all_documents.extend(docs)
                total_stats["pdfs_processed"] += 1
                total_stats["total_chunks"] += len(docs)
                print(f"  ✅ {original_name}: {len(docs)} chunks")

        # ── Legacy single-PDF fallback ────────────────────────────────────────
        elif os.path.exists(os.path.join(self.client_dir, "custom_pdf.txt")):
            pdf_text_path = os.path.join(self.client_dir, "custom_pdf.txt")
            with open(pdf_text_path, 'r', encoding='utf-8') as f:
                text = f.read()

            pdf_filename = "custom_pdf.pdf"
            print(f"  📄 Legacy PDF: {pdf_filename}")
            cleaned_text = self.cleaner.clean_text(text, preserve_structure=True)

            metadata = {
                'source': 'pdf',
                'pdf_id': 'legacy',
                'filename': pdf_filename,
                'title': f"PDF: {pdf_filename}"
            }

            docs = self.chunker.chunk_document(cleaned_text, metadata)
            all_documents.extend(docs)
            total_stats["pdfs_processed"] = 1
            total_stats["total_chunks"] = len(docs)
            print(f"  ✅ Legacy PDF: {len(docs)} chunks")

        if not all_documents:
            raise FileNotFoundError("No PDF text files found to process")

        print(f"\n📚 Total: {total_stats['pdfs_processed']} PDFs → {total_stats['total_chunks']} chunks")
        return all_documents, total_stats

    def process_custom_qa(self) -> tuple[List[Document], Dict[str, Any]]:
        """Process custom Q&A pairs."""
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
            questions = qa.get('questions', [])
            if not questions and 'question' in qa:
                questions = [qa['question']]

            answer = qa.get('answer', '')

            if not questions or not answer:
                continue

            for question in questions:
                content = f"Q: {question}\nA: {answer}"

                metadata = {
                    'source': 'qa',
                    'type': 'custom_qa',
                    'title': 'Custom Q&A',
                    'question': question
                }

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
        """Generate embeddings for documents."""
        if not documents:
            return []

        self._load_embedding_model()

        print(f"\n🔄 Generating embeddings for {len(documents)} chunks...")

        texts = [doc.page_content for doc in documents]

        embeddings = self.model.encode(
            texts,
            show_progress_bar=True,
            batch_size=32
        )

        embedded_docs = []
        for doc, embedding in zip(documents, embeddings):
            embedded_docs.append({
                'content': doc.page_content,
                'metadata': doc.metadata,
                'embedding': embedding.tolist()
            })

        return embedded_docs

    def store_in_chroma(self, embedded_docs: List[Dict[str, Any]], batch_size: int = 100):
        """Store embedded documents in ChromaDB with batching."""
        if not embedded_docs:
            print("⚠️ No documents to store")
            return

        print(f"\n📦 Storing {len(embedded_docs)} documents in ChromaDB...")

        client = chromadb.PersistentClient(path=self.chroma_dir)

        collection_name = self.client_id.lower()
        try:
            client.delete_collection(name=collection_name)
            print(f"🗑️  Deleted existing collection '{collection_name}'")
        except:
            pass

        collection = client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"}
        )

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

        embeddings_path = os.path.join(self.client_dir, "embeddings.json")
        with open(embeddings_path, 'w', encoding='utf-8') as f:
            json.dump(embedded_docs, f, indent=2, ensure_ascii=False)

        print(f"💾 Saved embeddings to {embeddings_path}")

    def run(self, source_type: str = 'crawl'):
        """Run complete pipeline."""
        print("\n" + "="*60)
        print(f"🚀 Starting Enhanced Structure-Aware Embedding Pipeline")
        print(f"Client: {self.client_id}")
        print(f"Source: {source_type}")
        print("="*60)

        all_documents = []
        total_stats = {}

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

        try:
            docs, stats = self.process_custom_qa()
            all_documents.extend(docs)
            total_stats['custom_qa'] = stats
        except Exception as e:
            print(f"⚠️ Error processing Q&A: {e}")

        if not all_documents:
            raise RuntimeError("❌ No documents to process! Check your input files.")

        print(f"\n📊 Total documents to embed: {len(all_documents)}")

        embedded_docs = self.embed_documents(all_documents)
        self.store_in_chroma(embedded_docs)
        self.save_artifacts(all_documents, embedded_docs)

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
        description='Enhanced Structure-Aware Embedding Pipeline'
    )
    parser.add_argument('client_id', help='Client identifier')
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
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
