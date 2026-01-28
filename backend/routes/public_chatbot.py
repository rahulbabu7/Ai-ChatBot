from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from backend.database import get_session
from backend.models import ChatbotName, User

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
