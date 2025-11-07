from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
import os
import json
import aiofiles
from PyPDF2 import PdfReader
from pathlib import Path
from backend.database import get_session
from backend.auth_utils import get_client_from_header
from backend.schemas import TaskResponse

# Import your Celery tasks
from backend.tasks import pdf_embed_pipeline

# Import LLM service functions
import sys
BASE_DIR = Path(__file__).resolve().parent
CHATBOT_LLM_DIR = os.path.abspath(os.path.join(BASE_DIR, "../../Chatbot/llm"))
sys.path.append(CHATBOT_LLM_DIR)

from llm_service import _load_custom_qa_cached, reload_custom_qa_cache

router = APIRouter(
    prefix='/client',
    tags=['files']
)

# Configuration
CLIENTS_DIR = (BASE_DIR / "../client_data").resolve()  # backend/client_data
CLIENTS_DIR.mkdir(exist_ok=True, parents=True)


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

        # Merge
        merged_data = old_data + new_data

        # Save back
        async with aiofiles.open(file_path, "w") as f:
            await f.write(json.dumps(merged_data, indent=2))

        # Clear cache
        try:
            _load_custom_qa_cached.cache_clear()
        except Exception:
            pass

        return {
            "status": "success",
            "message": f"Uploaded Q&A for {client_id} - merged and cache refreshed"
        }
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON file")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error uploading Q&A: {str(e)}")


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
            "text_length": len(text_content)
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to extract text from PDF: {str(e)}")


@router.post("/me/embed-pdf", response_model=TaskResponse)
async def embed_pdf(
    client_id: str = Depends(get_client_from_header)
):
    """Start embedding process for uploaded PDF"""
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
            message="PDF embedding task queued."
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error queuing PDF embed task: {str(e)}")


@router.get("/pdf-status/me")
async def check_pdf_status(
    client_id: str = Depends(get_client_from_header)
):
    """Check PDF processing status"""
    try:
        client_dir = os.path.join(CLIENTS_DIR, client_id)
        return {
            "pdf_uploaded": os.path.exists(os.path.join(client_dir, "custom_pdf.pdf")),
            "text_extracted": os.path.exists(os.path.join(client_dir, "custom_pdf.txt")),
            "embedded": os.path.exists(os.path.join(client_dir, "embeddings.json")),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error checking PDF status: {str(e)}")


@router.get("/status/me")
async def check_status(
    client_id: str = Depends(get_client_from_header)
):
    """Check overall client data status"""
    try:
        client_dir = os.path.join(CLIENTS_DIR, client_id)
        return {
            "crawled": os.path.exists(os.path.join(client_dir, "website_content.json")),
            "qa_uploaded": os.path.exists(os.path.join(client_dir, "custom_qa.json")),
            "embedded": True,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error checking status: {str(e)}")


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

        return {
            "has_qa": True,
            "qa_data": qa_data,
            "qa_count": len(qa_data),
            "message": f"Found {len(qa_data)} Q&A pairs"
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


@router.delete("/delete-qa/me")
async def delete_qa(
    client_id: str = Depends(get_client_from_header)
):
    """Delete Q&A file"""
    try:
        client_dir = os.path.join(CLIENTS_DIR, client_id)
        qa_path = os.path.join(client_dir, "custom_qa.json")

        if not os.path.exists(qa_path):
            raise HTTPException(status_code=404, detail="No Q&A file found")

        os.remove(qa_path)

        # Clear cache
        reload_custom_qa_cache(client_id)

        return {"success": True, "message": "Q&A file deleted and cache cleared"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete Q&A file: {str(e)}")


@router.delete("/delete-pdf/me")
async def delete_pdf(
    client_id: str = Depends(get_client_from_header)
):
    """Delete PDF files"""
    try:
        client_dir = os.path.join(CLIENTS_DIR, client_id)
        pdf_path = os.path.join(client_dir, "custom_pdf.pdf")
        text_path = os.path.join(client_dir, "custom_pdf.txt")

        deleted_files = []
        errors = []

        for file_path, file_type in [(pdf_path, "PDF"), (text_path, "extracted text")]:
            if os.path.exists(file_path):
                try:
                    os.remove(file_path)
                    deleted_files.append(file_type)
                except Exception as e:
                    errors.append(f"Failed to delete {file_type}: {str(e)}")

        if not deleted_files:
            raise HTTPException(status_code=404, detail="No PDF files found")

        result = {"success": True, "deleted_files": deleted_files}
        if errors:
            result["errors"] = errors

        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error deleting PDF files: {str(e)}")
