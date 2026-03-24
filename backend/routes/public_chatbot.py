import os
import json
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from backend.database import get_session
from backend.models import ChatbotName, User
from backend.config import settings

CLIENT_DATA_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "client_data")
)

router = APIRouter(prefix="/public",
 tags=["public_chatbot_name"])

@router.get("/chatbot-config")
async def get_chatbot_config(
    chatbot_key: str,
    session: AsyncSession = Depends(get_session),
):
    """
    Public endpoint for chatbot widget
    """
    try:
        # Find user by chatbot_key
        stmt = select(User).where(User.chatbot_key == chatbot_key)
        result = await session.execute(stmt)
        user = result.scalar_one_or_none()

        if not user:
            raise HTTPException(status_code=404, detail="Invalid chatbot key")

        # Get chatbot name
        stmt = select(ChatbotName).where(ChatbotName.client_id == user.client_id)
        result = await session.execute(stmt)
        chatbot = result.scalar_one_or_none()

        return {
            "chatbot_name": chatbot.chatbot_name if chatbot else "AI Assistant"
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail="Failed to load chatbot config",
        )


@router.get("/pdf")
async def public_download_pdf(
    chatbot_key: str,
    pdf_id: str,
    session: AsyncSession = Depends(get_session),
):
    """Public PDF download by pdf_id — accessible by chatbot widget users via chatbot_key."""
    try:
        stmt = select(User).where(User.chatbot_key == chatbot_key)
        result = await session.execute(stmt)
        user = result.scalar_one_or_none()
        if not user:
            raise HTTPException(status_code=404, detail="Invalid chatbot key")

        client_dir = os.path.join(CLIENT_DATA_DIR, user.client_id)

        # New multi-PDF structure
        manifest_path = os.path.join(client_dir, "pdfs", "manifest.json")
        if os.path.exists(manifest_path):
            with open(manifest_path) as f:
                manifest = json.load(f)
            entry = next((p for p in manifest if p["pdf_id"] == pdf_id), None)
            if not entry:
                raise HTTPException(status_code=404, detail="PDF not found.")
            pdf_path = os.path.join(client_dir, "pdfs", f"{pdf_id}.pdf")
            filename = entry.get("original_name", "document.pdf")
        else:
            # Legacy fallback
            pdf_path = os.path.join(client_dir, "custom_pdf.pdf")
            filename = "document.pdf"

        if not os.path.exists(pdf_path):
            raise HTTPException(status_code=404, detail="No PDF document available for this chatbot.")

        return FileResponse(path=pdf_path, media_type="application/pdf", filename=filename)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to retrieve PDF.")
