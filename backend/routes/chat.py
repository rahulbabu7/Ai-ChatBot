from fastapi import APIRouter, Depends, Header, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional
import uuid
import requests
import os
import sys
from backend.database import get_session
from backend.models import User, Chat
from backend.schemas import ChatRequest
from backend.auth_utils import get_client_from_header

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CHATBOT_LLM_DIR = os.path.abspath(os.path.join(BASE_DIR, "../../Chatbot/llm"))
sys.path.append(CHATBOT_LLM_DIR)

from llm_service import chat_with_model, explain_context

router = APIRouter(
    prefix='/client',
    tags=['client']
)


@router.post("/chat/{client_id}")
async def client_chat(
    client_id: str,
    req: ChatRequest,
    request: Request,
    session: AsyncSession = Depends(get_session),
    x_chatbot_key: str = Header(None)
):
    # Validate client + chatbot_key
    stmt = select(User).where(
        User.client_id == client_id,
        User.chatbot_key == x_chatbot_key
    )
    result = await session.execute(stmt)
    client = result.scalar_one_or_none()

    if not client:
        raise HTTPException(status_code=403, detail="Invalid client or key")

    # Ensure session_id
    session_id = req.session_id or str(uuid.uuid4())

    # Capture user-agent and IP address
    user_agent = request.headers.get("user-agent", "unknown")
    user_ip = request.client.host if request.client else "unknown"

    # Get the user's location from ipinfo.io API
    try:
        location_response = requests.get(f"https://ipinfo.io/{user_ip}/json", timeout=2)
        location_data = location_response.json()
        country_code = location_data.get("country", "Unknown")
    except requests.RequestException:
        country_code = "Unknown"

    # Store user message
    user_chat = Chat(
        client_id=client_id,
        session_id=session_id,
        role="user",
        message=req.message,
        user_agent=user_agent,
        country_code=country_code,
        admin_override=0,  # int, not bool
        is_active=1  # int, not bool
    )
    session.add(user_chat)
    await session.commit()

    # Generate chatbot reply
    bot_response = chat_with_model(client_id, req.message)

    # Extract just the answer text from the response dictionary
    bot_reply = (
        bot_response.get("answer", "I'm sorry, I couldn't generate a response.")
        if isinstance(bot_response, dict)
        else str(bot_response)
    )

    # Store assistant reply
    assistant_chat = Chat(
        client_id=client_id,
        session_id=session_id,
        role="assistant",
        message=bot_reply,
        user_agent=user_agent,
        country_code=country_code,
        admin_override=0,  # int, not bool
        is_active=1  # int, not bool
    )
    session.add(assistant_chat)
    await session.commit()

    # Return the response with session_id and bot reply
    return {
        "session_id": session_id,
        "reply": bot_reply,
        "confidence": bot_response.get("confidence") if isinstance(bot_response, dict) else None,
        "type": bot_response.get("type") if isinstance(bot_response, dict) else None
    }


@router.post("/context/{client_id}")
async def context_endpoint(
    client_id: str,
    req: ChatRequest,
    session: AsyncSession = Depends(get_session),
    x_chatbot_key: str = Header(None)
):
    # Validate client + chatbot_key
    stmt = select(User).where(
        User.client_id == client_id,
        User.chatbot_key == x_chatbot_key
    )
    result = await session.execute(stmt)
    client = result.scalar_one_or_none()

    if not client:
        raise HTTPException(status_code=403, detail="Invalid client or key")

    # Fetch and explain context for the user
    ctx = explain_context(client_id, req.message)

    # Return context or a default message if no context found
    return {"context": ctx or "No relevant context found."}


@router.get("/sessions/me")
async def get_sessions(
    client_id: str = Depends(get_client_from_header),
    session: AsyncSession = Depends(get_session)
):
    """Get all distinct session IDs for the authenticated client"""
    try:
        stmt = (
            select(Chat.session_id)
            .where(Chat.client_id == client_id)
            .distinct()
            .order_by(Chat.created_at.desc())
        )
        
        result = await session.execute(stmt)
        sessions = result.scalars().all()
        
        return {"sessions": sessions}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching sessions: {str(e)}")


@router.get("/chats/me")
async def get_chats(
    session_id: str,
    session: AsyncSession = Depends(get_session),
    client_id: str = Depends(get_client_from_header)
):
    # Fetch chats for the session
    stmt = select(Chat).where(
        Chat.client_id == client_id,
        Chat.session_id == session_id,
        Chat.is_active == 1  # int, not bool
    ).order_by(Chat.created_at.asc())

    result = await session.execute(stmt)
    chats = result.scalars().all()

    # Convert to dict format
    chats_data = [
        {
            "id": chat.id,
            "client_id": chat.client_id,
            "session_id": chat.session_id,
            "role": chat.role,
            "message": chat.message,
            "user_agent": chat.user_agent,
            "country_code": chat.country_code,
            "admin_override": chat.admin_override,
            "is_active": chat.is_active,
            "created_at": chat.created_at.format() if chat.created_at else None
        }
        for chat in chats
    ]

    return {"chats": chats_data}