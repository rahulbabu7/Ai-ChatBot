from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func
from sqlmodel import select
from pathlib import Path

from backend.database import get_session
from backend.models import Chat, DomainMapping
from backend.auth_utils import get_client_from_header

router = APIRouter(prefix="/client", tags=["onboarding"])

CLIENT_DATA_DIR = Path("client_data")


@router.get("/onboarding-status/me")
async def get_onboarding_status(
    client_id: str = Depends(get_client_from_header),
    session: AsyncSession = Depends(get_session),
):
    """Return completion status for each onboarding step"""
    try:
        base_dir = CLIENT_DATA_DIR / client_id

        # Step 1: Website crawled
        website_crawled = (base_dir / "website_content.json").exists()

        # Step 2: PDF uploaded
        pdf_uploaded = (
            (base_dir / "pdfs" / "manifest.json").exists()
            or (base_dir / "custom_pdf.txt").exists()
        )

        # Step 3: Q&A added
        qa_added = (base_dir / "custom_qa.json").exists()

        # Step 4: Chatbot tested (at least 1 chat exists)
        stmt = select(func.count(Chat.id)).where(Chat.client_id == client_id)
        result = await session.execute(stmt)
        chat_count = result.scalar() or 0
        chatbot_tested = chat_count > 0

        # Step 5: Domain configured
        stmt = select(DomainMapping).where(DomainMapping.client_id == client_id)
        result = await session.execute(stmt)
        domain_configured = result.scalar_one_or_none() is not None

        steps = {
            "website_crawled": website_crawled,
            "pdf_uploaded": pdf_uploaded,
            "qa_added": qa_added,
            "chatbot_tested": chatbot_tested,
            "domain_configured": domain_configured,
        }

        completed = sum(1 for v in steps.values() if v)
        total = len(steps)

        return {
            "steps": steps,
            "completed": completed,
            "total": total,
            "percentage": round((completed / total) * 100),
        }
    except Exception as e:
        print(f"❌ Error fetching onboarding status: {e}")
        raise HTTPException(status_code=500, detail=f"Error fetching onboarding status: {str(e)}")
