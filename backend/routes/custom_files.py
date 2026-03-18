from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
import os
import json
import aiofiles
from PyPDF2 import PdfReader
from pathlib import Path
from backend.database import get_session
from backend.auth_utils import get_client_from_header
from backend.schemas import TaskResponse
import asyncio

# Import your Celery tasks
from backend.tasks import pdf_embed_pipeline, qa_embed_pipeline

# Import LLM service functions
import sys
BASE_DIR = Path(__file__).resolve().parent
CHATBOT_LLM_DIR = os.path.abspath(os.path.join(BASE_DIR, "../../Chatbot/llm"))
sys.path.append(CHATBOT_LLM_DIR)

from llm_service import chat_with_model, UniversalRAGChatbot, invalidate_client_sessions

router = APIRouter(
    prefix='/client',
    tags=['files']
)

# Configuration
CLIENTS_DIR = (BASE_DIR / "../../client_data").resolve()
CLIENTS_DIR.mkdir(exist_ok=True, parents=True)
CHROMA_DIR = os.path.abspath(os.path.join(BASE_DIR, "../../ChromaDatabase/vector-database/chroma_db"))


def _purge_chroma_by_source(client_id: str, source: str) -> int:
    """Immediately delete all ChromaDB chunks with the given source metadata.

    Returns the number of deleted chunks, or -1 on error.
    """
    try:
        import chromadb
        chroma_client = chromadb.PersistentClient(path=CHROMA_DIR)
        collection = chroma_client.get_collection(client_id.lower())

        # Get IDs of all documents matching this source
        all_docs = collection.get(where={"source": source})
        ids_to_delete = all_docs.get("ids", [])

        if ids_to_delete:
            collection.delete(ids=ids_to_delete)

        return len(ids_to_delete)
    except Exception as e:
        print(f"⚠️ Failed to purge ChromaDB chunks for source={source}: {e}")
        return -1


# ============================================================================
# UPLOAD ENDPOINTS
# ============================================================================

@router.post("/upload-qa/me")
async def upload_qa(
    file: UploadFile = File(...),
    client_id: str = Depends(get_client_from_header)
):
    """Upload and merge Q&A JSON file"""
    try:
        client_dir = os.path.join(CLIENTS_DIR, client_id)
        os.makedirs(client_dir, exist_ok=True)
        file_path = os.path.join(client_dir, "custom_qa.json")

        # Read new uploaded JSON
        content = await file.read()
        new_data = json.loads(content.decode("utf-8"))

        # Ensure it's always a list
        if not isinstance(new_data, list):
            new_data = [new_data]

        # Validate Q&A format
        for item in new_data:
            if "questions" not in item and "question" not in item:
                raise ValueError("Each Q&A entry must have 'questions' or 'question' field")
            if "answer" not in item:
                raise ValueError("Each Q&A entry must have 'answer' field")

        # Load existing data if file exists
        if os.path.exists(file_path):
            async with aiofiles.open(file_path, "r") as f:
                old_content = await f.read()
                try:
                    old_data = json.loads(old_content)
                    if not isinstance(old_data, list):
                        old_data = [old_data]
                except Exception:
                    old_data = []
        else:
            old_data = []

        # Merge (remove duplicates based on question text)
        existing_questions = set()
        for qa in old_data:
            questions = qa.get("questions", [qa.get("question")]) if qa.get("questions") else [qa.get("question")]
            for q in questions:
                if q:
                    existing_questions.add(q.lower().strip())

        # Only add new unique questions
        merged_data = old_data.copy()
        new_count = 0
        for qa in new_data:
            questions = qa.get("questions", [qa.get("question")]) if qa.get("questions") else [qa.get("question")]
            is_duplicate = any(q.lower().strip() in existing_questions for q in questions if q)

            if not is_duplicate:
                merged_data.append(qa)
                new_count += 1
                # Add to set to prevent duplicates within this upload
                for q in questions:
                    if q:
                        existing_questions.add(q.lower().strip())

        # Save back
        async with aiofiles.open(file_path, "w") as f:
            await f.write(json.dumps(merged_data, indent=2))

        return {
            "status": "success",
            "message": f"Uploaded {new_count} new Q&A entries for {client_id}",
            "total_qa": len(merged_data),
            "new_entries": new_count,
            "note": "Q&A available immediately via direct matching. Run /client/me/re-embed to add to vector search."
        }
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON file")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error uploading Q&A: {str(e)}")


@router.post("/upload-qa/me/embed", response_model=TaskResponse)
async def upload_qa_and_embed(
    file: UploadFile = File(...),
    client_id: str = Depends(get_client_from_header)
):
    """Upload Q&A and trigger re-embedding automatically"""
    try:
        # First upload the Q&A
        upload_result = await upload_qa(file, client_id)

        # Then trigger re-embedding if new entries were added
        if upload_result.get("new_entries", 0) > 0:
            task = qa_embed_pipeline.delay(client_id)
            return TaskResponse(
                task_id=task.id,
                status="queued",
                message=f"Uploaded {upload_result['new_entries']} Q&A entries. Re-embedding task queued."
            )
        else:
            return TaskResponse(
                task_id="none",
                status="completed",
                message="No new Q&A entries to add. No re-embedding needed."
            )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error uploading Q&A with embedding: {str(e)}")


@router.post("/upload-pdf/me")
async def upload_pdf(
    file: UploadFile = File(...),
    client_id: str = Depends(get_client_from_header)
):
    """Upload and extract text from a PDF file"""
    try:
        if not file.filename.lower().endswith('.pdf'):
            raise HTTPException(status_code=400, detail="Only PDF files are allowed")

        client_dir = os.path.join(CLIENTS_DIR, client_id)
        os.makedirs(client_dir, exist_ok=True)

        # Save the PDF file
        pdf_path = os.path.join(client_dir, "custom_pdf.pdf")
        async with aiofiles.open(pdf_path, "wb") as f:
            content = await file.read()
            await f.write(content)

        # Extract text from PDF using PyPDF2
        reader = PdfReader(pdf_path)
        text_content = ""

        for page in reader.pages:
            text_content += page.extract_text() + "\n\n"

        # Save extracted text
        text_path = os.path.join(client_dir, "custom_pdf.txt")
        async with aiofiles.open(text_path, "w", encoding="utf-8") as f:
            await f.write(text_content)

        return {
            "status": "success",
            "message": f"PDF uploaded and text extracted for {client_id}",
            "pages_extracted": len(reader.pages),
            "text_length": len(text_content),
            "note": "Run /client/me/embed-pdf or /client/me/re-embed to create embeddings for chatbot use"
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to extract text from PDF: {str(e)}")


# ============================================================================
# EMBEDDING ENDPOINTS
# ============================================================================

@router.post("/me/embed-pdf", response_model=TaskResponse)
async def embed_pdf(
    client_id: str = Depends(get_client_from_header)
):
    """Start embedding process for uploaded PDF using enhanced pipeline"""
    try:
        client_dir = os.path.join(CLIENTS_DIR, client_id)
        pdf_text_path = os.path.join(client_dir, "custom_pdf.txt")

        if not os.path.exists(pdf_text_path):
            raise HTTPException(
                status_code=404,
                detail="No PDF text found. Please upload a PDF first."
            )

        task = pdf_embed_pipeline.delay(client_id)
        return TaskResponse(
            task_id=task.id,
            status="queued",
            message="PDF embedding task queued using enhanced pipeline."
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error queuing PDF embed task: {str(e)}")


@router.post("/me/re-embed", response_model=TaskResponse)
async def re_embed_all(
    client_id: str = Depends(get_client_from_header)
):
    """Re-embed all sources (website, PDF, Q&A) for this client"""
    try:
        client_dir = os.path.join(CLIENTS_DIR, client_id)

        # Check what sources exist
        has_website = os.path.exists(os.path.join(client_dir, "website_content.json"))
        has_pdf = os.path.exists(os.path.join(client_dir, "custom_pdf.txt"))
        has_qa = os.path.exists(os.path.join(client_dir, "custom_qa.json"))

        if not (has_website or has_pdf or has_qa):
            raise HTTPException(
                status_code=404,
                detail="No sources found to embed. Please upload website data, PDF, or Q&A first."
            )

        task = qa_embed_pipeline.delay(client_id)

        sources = []
        if has_website:
            sources.append("website")
        if has_pdf:
            sources.append("PDF")
        if has_qa:
            sources.append("Q&A")

        return TaskResponse(
            task_id=task.id,
            status="queued",
            message=f"Re-embedding task queued for: {', '.join(sources)}"
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error queuing re-embed task: {str(e)}")


# ============================================================================
# STATUS & VERIFICATION ENDPOINTS
# ============================================================================

@router.get("/status/me")
async def check_status(
    client_id: str = Depends(get_client_from_header)
):
    """Check overall client data status"""
    try:
        client_dir = os.path.join(CLIENTS_DIR, client_id)
        chroma_dir = os.path.abspath(os.path.join(BASE_DIR, "../../ChromaDatabase/vector-database/chroma_db"))

        # Check if collection exists in ChromaDB
        has_embeddings = False
        num_documents = 0
        try:
            import chromadb
            chroma_client = chromadb.PersistentClient(path=chroma_dir)
            collection = chroma_client.get_collection(client_id.lower())
            num_documents = collection.count()
            has_embeddings = num_documents > 0
        except:
            pass

        return {
            "crawled": os.path.exists(os.path.join(client_dir, "website_content.json")),
            "qa_uploaded": os.path.exists(os.path.join(client_dir, "custom_qa.json")),
            "pdf_uploaded": os.path.exists(os.path.join(client_dir, "custom_pdf.pdf")),
            "embedded": has_embeddings,
            "num_documents": num_documents,
            "chunks_file": os.path.exists(os.path.join(client_dir, "chunks.json")),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error checking status: {str(e)}")


@router.get("/pdf-status/me")
async def check_pdf_status(
    client_id: str = Depends(get_client_from_header)
):
    """Check PDF processing status"""
    try:
        client_dir = os.path.join(CLIENTS_DIR, client_id)
        chroma_dir = os.path.abspath(os.path.join(BASE_DIR, "../../ChromaDatabase/vector-database/chroma_db"))

        # Check if collection exists in ChromaDB
        has_embeddings = False
        try:
            import chromadb
            chroma_client = chromadb.PersistentClient(path=chroma_dir)
            collection = chroma_client.get_collection(client_id.lower())
            has_embeddings = collection.count() > 0
        except:
            pass

        return {
            "pdf_uploaded": os.path.exists(os.path.join(client_dir, "custom_pdf.pdf")),
            "text_extracted": os.path.exists(os.path.join(client_dir, "custom_pdf.txt")),
            "embedded": has_embeddings,
            "chunks_file": os.path.exists(os.path.join(client_dir, "chunks.json")),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error checking PDF status: {str(e)}")


@router.get("/embeddings-status/me")
async def check_embeddings_status(
    client_id: str = Depends(get_client_from_header)
):
    """Check what's currently in the vector database - useful for verifying deletions worked"""
    try:
        chroma_dir = os.path.abspath(os.path.join(BASE_DIR, "../../ChromaDatabase/vector-database/chroma_db"))

        result = {
            "client_id": client_id,
            "collection_exists": False,
            "document_count": 0,
            "sources_in_db": {},
            "sources_on_disk": {}
        }

        # Check ChromaDB
        try:
            import chromadb
            chroma_client = chromadb.PersistentClient(path=chroma_dir)
            collection = chroma_client.get_collection(client_id.lower())

            result["collection_exists"] = True
            result["document_count"] = collection.count()

            # Sample documents to see what sources are present
            if result["document_count"] > 0:
                sample = collection.get(limit=min(100, result["document_count"]))
                sources = {}
                for metadata in sample.get("metadatas", []):
                    source = metadata.get("source", "unknown")
                    sources[source] = sources.get(source, 0) + 1
                result["sources_in_db"] = sources
        except Exception as e:
            result["db_error"] = str(e)

        # Check disk
        client_dir = os.path.join(CLIENTS_DIR, client_id)
        result["sources_on_disk"] = {
            "website": os.path.exists(os.path.join(client_dir, "website_content.json")),
            "pdf": os.path.exists(os.path.join(client_dir, "custom_pdf.txt")),
            "qa": os.path.exists(os.path.join(client_dir, "custom_qa.json"))
        }

        # Check for mismatch (indicates embeddings out of sync)
        disk_sources = [k for k, v in result["sources_on_disk"].items() if v]
        db_sources = list(result.get("sources_in_db", {}).keys())

        result["synchronized"] = set(disk_sources) == set(db_sources) if db_sources else len(disk_sources) == 0
        if not result["synchronized"]:
            result["warning"] = "Sources on disk don't match vector database. Consider running /client/me/re-embed"

        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error checking embeddings status: {str(e)}")


@router.get("/verify-qa-embedding/me")
async def verify_qa_embedding(
    client_id: str = Depends(get_client_from_header)
):
    """
    Verify that Q&A is properly embedded in the vector database.
    Checks BOTH in-memory Q&A and ChromaDB embeddings.
    """
    try:
        client_dir = os.path.join(CLIENTS_DIR, client_id)
        qa_path = os.path.join(client_dir, "custom_qa.json")

        result = {
            "qa_file_exists": os.path.exists(qa_path),
            "qa_count": 0,
            "qa_in_memory": False,
            "qa_in_vector_db": False,
            "qa_chunks_in_db": 0
        }

        # Check Q&A file
        if os.path.exists(qa_path):
            async with aiofiles.open(qa_path, "r", encoding="utf-8") as f:
                content = await f.read()
                qa_data = json.loads(content)
                result["qa_count"] = len(qa_data)
                result["qa_in_memory"] = True

        # Check ChromaDB for Q&A embeddings
        try:
            chroma_dir = os.path.abspath(os.path.join(BASE_DIR, "../../ChromaDatabase/vector-database/chroma_db"))
            import chromadb
            chroma_client = chromadb.PersistentClient(path=chroma_dir)
            collection = chroma_client.get_collection(client_id.lower())

            # Count Q&A documents
            all_docs = collection.get(limit=collection.count())
            qa_count = sum(1 for meta in all_docs.get("metadatas", [])
                          if meta.get("source") == "qa" or meta.get("type") == "custom_qa")

            result["qa_in_vector_db"] = qa_count > 0
            result["qa_chunks_in_db"] = qa_count

            # Sample Q&A
            if qa_count > 0:
                sample_qa = []
                for i, metadata in enumerate(all_docs.get("metadatas", [])):
                    if metadata.get("source") == "qa":
                        sample_qa.append({
                            "content": all_docs["documents"][i][:200] + "...",
                            "metadata": metadata
                        })
                        if len(sample_qa) >= 3:
                            break
                result["sample_qa_from_db"] = sample_qa
        except Exception as e:
            result["vector_db_error"] = str(e)

        # Overall status
        if result["qa_in_memory"] and result["qa_in_vector_db"]:
            result["status"] = "✅ Q&A is properly embedded (both in-memory and vector DB)"
        elif result["qa_in_memory"] and not result["qa_in_vector_db"]:
            result["status"] = "⚠️ Q&A file exists but not embedded. Run /client/me/re-embed"
        elif not result["qa_in_memory"]:
            result["status"] = "❌ No Q&A file uploaded"

        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error verifying Q&A: {str(e)}")


@router.get("/test-qa-retrieval/me")
async def test_qa_retrieval(
    query: str,
    client_id: str = Depends(get_client_from_header)
):
    """
    Test Q&A retrieval for a specific query.
    Shows both direct matching and vector search results.
    """
    try:
        from llm_service import HybridRetriever

        retriever = HybridRetriever(client_id)

        result = {
            "query": query,
            "direct_qa_match": None,
            "vector_search_results": []
        }

        # Test direct Q&A matching
        qa_match = retriever.match_custom_qa(query, threshold=0.75)
        if qa_match:
            result["direct_qa_match"] = {
                "found": True,
                "confidence": qa_match.get("confidence"),
                "score": qa_match.get("score"),
                "matched_question": qa_match.get("matched_question"),
                "answer_preview": qa_match.get("answer", "")[:200] + "..."
            }
        else:
            result["direct_qa_match"] = {"found": False}

        # Test vector search
        documents = retriever.retrieve_documents(query, top_k=10)
        qa_docs = [doc for doc in documents if doc.get('metadata', {}).get('source') == 'qa']

        result["vector_search_results"] = [
            {
                "score": doc.get("score"),
                "content_preview": doc.get("content", "")[:200] + "...",
                "metadata": doc.get("metadata")
            }
            for doc in qa_docs[:5]
        ]

        result["qa_docs_found_in_vector_search"] = len(qa_docs)

        # Recommendation
        if result["direct_qa_match"]["found"]:
            result["recommendation"] = "✅ Direct Q&A match found - chatbot will use this"
        elif result["qa_docs_found_in_vector_search"] > 0:
            result["recommendation"] = "⚠️ No direct match, but Q&A found in vector search"
        else:
            result["recommendation"] = "❌ No Q&A found for this query"

        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error testing Q&A retrieval: {str(e)}")


# ============================================================================
# VIEW ENDPOINTS
# ============================================================================

@router.get("/view-qa/me")
async def view_qa(
    client_id: str = Depends(get_client_from_header)
):
    """View uploaded Q&A content"""
    try:
        client_dir = os.path.join(CLIENTS_DIR, client_id)
        qa_path = os.path.join(client_dir, "custom_qa.json")

        if not os.path.exists(qa_path):
            return {
                "has_qa": False,
                "qa_data": [],
                "message": "No Q&A file found"
            }

        async with aiofiles.open(qa_path, "r", encoding="utf-8") as f:
            content = await f.read()
            qa_data = json.loads(content)

        # Format for display
        formatted_qa = []
        for item in qa_data:
            questions = item.get("questions", [item.get("question")]) if item.get("questions") else [item.get("question")]
            formatted_qa.append({
                "questions": questions,
                "answer": item.get("answer", ""),
                "metadata": item.get("metadata", {})
            })

        return {
            "has_qa": True,
            "qa_data": formatted_qa,
            "qa_count": len(qa_data),
            "total_questions": sum(len(item["questions"]) for item in formatted_qa),
            "message": f"Found {len(qa_data)} Q&A entries"
        }
    except Exception as e:
        return {
            "has_qa": False,
            "qa_data": [],
            "error": str(e),
            "message": "Error reading Q&A file"
        }


@router.get("/view-pdf-info/me")
async def view_pdf_info(
    client_id: str = Depends(get_client_from_header)
):
    """View PDF upload information"""
    try:
        client_dir = os.path.join(CLIENTS_DIR, client_id)
        pdf_path = os.path.join(client_dir, "custom_pdf.pdf")
        text_path = os.path.join(client_dir, "custom_pdf.txt")

        result = {
            "has_pdf": os.path.exists(pdf_path),
            "has_extracted_text": os.path.exists(text_path),
            "pdf_info": {}
        }

        if result["has_pdf"]:
            # Get PDF file info
            pdf_stat = os.stat(pdf_path)
            result["pdf_info"] = {
                "filename": "custom_pdf.pdf",
                "size_bytes": pdf_stat.st_size,
                "size_mb": round(pdf_stat.st_size / (1024 * 1024), 2),
                "uploaded_date": pdf_stat.st_mtime
            }

            # Get text extraction info if available
            if result["has_extracted_text"]:
                try:
                    async with aiofiles.open(text_path, "r", encoding="utf-8") as f:
                        text_content = await f.read()

                    result["pdf_info"]["text_length"] = len(text_content)
                    result["pdf_info"]["word_count"] = len(text_content.split())
                    result["pdf_info"]["preview"] = (
                        text_content[:500] + "..." if len(text_content) > 500 else text_content
                    )
                except Exception:
                    result["pdf_info"]["text_extraction_error"] = "Could not read extracted text"

        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching PDF info: {str(e)}")


@router.get("/download-pdf/me")
async def download_pdf(
    client_id: str = Depends(get_client_from_header)
):
    """Download the uploaded PDF file for this client."""
    pdf_path = os.path.join(CLIENTS_DIR, client_id, "custom_pdf.pdf")
    if not os.path.exists(pdf_path):
        raise HTTPException(status_code=404, detail="No PDF uploaded for this client.")
    return FileResponse(
        path=pdf_path,
        media_type="application/pdf",
        filename="document.pdf",
    )


@router.get("/view-chunks/me")
async def view_chunks(
    client_id: str = Depends(get_client_from_header),
    limit: int = 10
):
    """View generated chunks for debugging"""
    try:
        client_dir = os.path.join(CLIENTS_DIR, client_id)
        chunks_path = os.path.join(client_dir, "chunks.json")

        if not os.path.exists(chunks_path):
            return {
                "has_chunks": False,
                "message": "No chunks file found. Run embedding pipeline first."
            }

        async with aiofiles.open(chunks_path, "r", encoding="utf-8") as f:
            content = await f.read()
            chunks = json.loads(content)

        # Return limited chunks for preview
        preview_chunks = chunks[:limit]

        # Get statistics
        sources = {}
        for chunk in chunks:
            source = chunk.get("metadata", {}).get("source", "unknown")
            sources[source] = sources.get(source, 0) + 1

        return {
            "has_chunks": True,
            "total_chunks": len(chunks),
            "preview_chunks": preview_chunks,
            "sources_breakdown": sources,
            "showing": min(limit, len(chunks)),
            "message": f"Showing {min(limit, len(chunks))} of {len(chunks)} chunks"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reading chunks: {str(e)}")


# ============================================================================
# DELETE ENDPOINTS (with auto re-embedding)
# ============================================================================

@router.delete("/delete-qa/me")
async def delete_qa(
    client_id: str = Depends(get_client_from_header)
):
    """Delete Q&A file and automatically re-embed remaining sources"""
    try:
        client_dir = os.path.join(CLIENTS_DIR, client_id)
        qa_path = os.path.join(client_dir, "custom_qa.json")

        if not os.path.exists(qa_path):
            raise HTTPException(status_code=404, detail="No Q&A file found")

        os.remove(qa_path)

        # Immediately purge Q&A chunks from ChromaDB so the chatbot stops using them
        purged = _purge_chroma_by_source(client_id, "qa")

        # Invalidate cached chat sessions so they pick up the updated collection
        invalidate_client_sessions(client_id)

        # Check if other sources exist AFTER deletion
        has_website = os.path.exists(os.path.join(client_dir, "website_content.json"))
        has_pdf = os.path.exists(os.path.join(client_dir, "custom_pdf.txt"))

        result = {
            "success": True,
            "message": "Q&A file deleted",
            "chunks_purged": purged,
        }

        # Automatically trigger re-embedding if other sources exist
        if has_website or has_pdf:
            task = qa_embed_pipeline.delay(client_id)
            result["re_embedding"] = {
                "status": "queued",
                "task_id": task.id,
                "message": "Automatically re-embedding remaining sources to remove Q&A data from chatbot",
                "remaining_sources": []
            }
            if has_website:
                result["re_embedding"]["remaining_sources"].append("website")
            if has_pdf:
                result["re_embedding"]["remaining_sources"].append("PDF")
        else:
            # No sources left - clear the entire collection
            try:
                import chromadb
                chroma_client = chromadb.PersistentClient(path=CHROMA_DIR)
                chroma_client.delete_collection(client_id.lower())
                result["message"] = "Q&A deleted and vector database cleared (no other sources remain)"
            except Exception as e:
                result["message"] = f"Q&A deleted. Note: {str(e)}"

        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete Q&A file: {str(e)}")


@router.delete("/delete-pdf/me")
async def delete_pdf(
    client_id: str = Depends(get_client_from_header)
):
    """Delete PDF files and automatically re-embed remaining sources"""
    try:
        client_dir = os.path.join(CLIENTS_DIR, client_id)
        pdf_path = os.path.join(client_dir, "custom_pdf.pdf")
        text_path = os.path.join(client_dir, "custom_pdf.txt")

        deleted_files = []
        errors = []

        # Check if PDF exists before deletion
        pdf_existed = os.path.exists(pdf_path) or os.path.exists(text_path)

        for file_path, file_type in [(pdf_path, "PDF"), (text_path, "extracted text")]:
            if os.path.exists(file_path):
                try:
                    os.remove(file_path)
                    deleted_files.append(file_type)
                except Exception as e:
                    errors.append(f"Failed to delete {file_type}: {str(e)}")

        if not pdf_existed:
            raise HTTPException(status_code=404, detail="No PDF files found")

        # Immediately purge PDF chunks from ChromaDB so the chatbot stops using them
        purged = _purge_chroma_by_source(client_id, "pdf")

        # Invalidate cached chat sessions so they pick up the updated collection
        invalidate_client_sessions(client_id)

        # Check if other sources exist AFTER deletion
        has_website = os.path.exists(os.path.join(client_dir, "website_content.json"))
        has_qa = os.path.exists(os.path.join(client_dir, "custom_qa.json"))

        result = {
            "success": True,
            "deleted_files": deleted_files,
            "chunks_purged": purged,
        }

        if errors:
            result["errors"] = errors

        # Automatically trigger re-embedding if other sources exist
        if has_website or has_qa:
            task = qa_embed_pipeline.delay(client_id)
            result["re_embedding"] = {
                "status": "queued",
                "task_id": task.id,
                "message": "Automatically re-embedding remaining sources to remove PDF data from chatbot",
                "remaining_sources": []
            }
            if has_website:
                result["re_embedding"]["remaining_sources"].append("website")
            if has_qa:
                result["re_embedding"]["remaining_sources"].append("Q&A")
        else:
            # No sources left - clear the entire collection
            try:
                import chromadb
                chroma_client = chromadb.PersistentClient(path=CHROMA_DIR)
                chroma_client.delete_collection(client_id.lower())
                result["message"] = "PDF deleted and vector database cleared (no other sources remain)"
            except Exception as e:
                result["message"] = f"PDF deleted. Note: {str(e)}"

        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error deleting PDF files: {str(e)}")


@router.delete("/delete-website/me")
async def delete_website(
    client_id: str = Depends(get_client_from_header)
):
    """Delete website crawl data and automatically re-embed remaining sources"""
    try:
        client_dir = os.path.join(CLIENTS_DIR, client_id)
        website_path = os.path.join(client_dir, "website_content.json")

        if not os.path.exists(website_path):
            raise HTTPException(status_code=404, detail="No website data found")

        os.remove(website_path)

        # Immediately purge website chunks from ChromaDB so the chatbot stops using them
        purged = _purge_chroma_by_source(client_id, "website")

        # Invalidate cached chat sessions so they pick up the updated collection
        invalidate_client_sessions(client_id)

        # Check if other sources exist AFTER deletion
        has_pdf = os.path.exists(os.path.join(client_dir, "custom_pdf.txt"))
        has_qa = os.path.exists(os.path.join(client_dir, "custom_qa.json"))

        result = {
            "success": True,
            "message": "Website data deleted",
            "chunks_purged": purged,
        }

        if has_pdf or has_qa:
            task = qa_embed_pipeline.delay(client_id)
            result["re_embedding"] = {
                "status": "queued",
                "task_id": task.id,
                "message": "Automatically re-embedding remaining sources to remove website data from chatbot",
                "remaining_sources": []
            }
            if has_pdf:
                result["re_embedding"]["remaining_sources"].append("PDF")
            if has_qa:
                result["re_embedding"]["remaining_sources"].append("Q&A")
        else:
            try:
                import chromadb
                chroma_client = chromadb.PersistentClient(path=CHROMA_DIR)
                chroma_client.delete_collection(client_id.lower())
                result["message"] = "Website data deleted and vector database cleared (no other sources remain)"
            except Exception as e:
                result["message"] = f"Website data deleted. Note: {str(e)}"

        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete website data: {str(e)}")


@router.delete("/clear-all/me")
async def clear_all_data(
    client_id: str = Depends(get_client_from_header)
):
    """Delete all client data (website, PDF, Q&A, embeddings)"""
    try:
        client_dir = os.path.join(CLIENTS_DIR, client_id)

        if not os.path.exists(client_dir):
            raise HTTPException(status_code=404, detail="No client data found")

        deleted_items = []
        errors = []

        # Files to delete
        files_to_delete = [
            ("website_content.json", "website crawl data"),
            ("custom_pdf.pdf", "PDF file"),
            ("custom_pdf.txt", "PDF text"),
            ("custom_qa.json", "Q&A data"),
            ("chunks.json", "chunks file"),
            ("embeddings.json", "embeddings file"),
        ]

        for filename, description in files_to_delete:
            file_path = os.path.join(client_dir, filename)
            if os.path.exists(file_path):
                try:
                    os.remove(file_path)
                    deleted_items.append(description)
                except Exception as e:
                    errors.append(f"Failed to delete {description}: {str(e)}")

        # Delete ChromaDB collection
        try:
            import chromadb
            chroma_client = chromadb.PersistentClient(path=CHROMA_DIR)
            chroma_client.delete_collection(client_id.lower())
            deleted_items.append("vector database")
        except Exception as e:
            errors.append(f"Failed to delete vector database: {str(e)}")

        # Invalidate cached chat sessions
        invalidate_client_sessions(client_id)

        result = {
            "success": True,
            "deleted_items": deleted_items,
            "message": f"Deleted {len(deleted_items)} data sources for {client_id}"
        }

        if errors:
            result["errors"] = errors
            result["message"] += f" (with {len(errors)} errors)"

        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error clearing data: {str(e)}")
