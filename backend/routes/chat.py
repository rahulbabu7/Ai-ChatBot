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

from llm_service import chat_with_model, explain_context, get_conversation_state, reset_conversation, clear_session

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
    """Chat endpoint with session management and response time tracking"""
    import time

    # Start timing
    start_time = time.time()

    # Validate client + chatbot_key
    stmt = select(User).where(
        User.client_id == client_id,
        User.chatbot_key == x_chatbot_key
    )
    result = await session.execute(stmt)
    client = result.scalar_one_or_none()

    if not client:
        raise HTTPException(status_code=403, detail="Invalid client or key")

    # Use provided session_id or create new one
    # IMPORTANT: Frontend should send back the session_id for conversation continuity
    chatbot_session_id = req.session_id or str(uuid.uuid4())

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
        session_id=chatbot_session_id,
        role="user",
        message=req.message,
        user_agent=user_agent,
        country_code=country_code,
        admin_override=0,
        is_active=1
    )
    session.add(user_chat)
    await session.commit()

    # Generate chatbot reply with session context
    # This maintains conversation history across requests!
    bot_response = chat_with_model(
        client_id=client_id,
        query=req.message,
        session_id=chatbot_session_id,  # ← KEY: Pass session_id for context
        include_history=True,
        enable_clarifications=True
    )
    
    response_time = time.time() - start_time

    # Extract answer from response
    bot_reply = (
        bot_response.get("answer", "I'm sorry, I couldn't generate a response.")
        if isinstance(bot_response, dict)
        else str(bot_response)
    )

    # Store assistant reply with response time
    assistant_chat = Chat(
        client_id=client_id,
        session_id=chatbot_session_id,
        role="assistant",
        message=bot_reply,
        user_agent=user_agent,
        country_code=country_code,
        admin_override=0,
        is_active=1,
        response_time=response_time
    )
    session.add(assistant_chat)
    await session.commit()

    # Return enhanced response with all interactive features
    return {
        "session_id": bot_response.get("session_id", chatbot_session_id),  # Return session_id
        "reply": bot_reply,
        "confidence": bot_response.get("confidence"),
        "type": bot_response.get("type"),
        "needs_clarification": bot_response.get("needs_clarification", False),
        "clarification_questions": bot_response.get("clarification_questions", []),
        "follow_up_question": bot_response.get("follow_up_question"),
        "probing_questions": bot_response.get("probing_questions", []),
        "sources": bot_response.get("sources", []),
        "processing_time": bot_response.get("processing_time", response_time),
        "metadata": bot_response.get("metadata", {})
    }


@router.post("/context/{client_id}")
async def context_endpoint(
    client_id: str,
    req: ChatRequest,
    session: AsyncSession = Depends(get_session),
    x_chatbot_key: str = Header(None)
):
    """Debug endpoint to see retrieved context"""
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
    """Fetch chats for a specific session"""
    # Fetch chats for the session
    stmt = select(Chat).where(
        Chat.client_id == client_id,
        Chat.session_id == session_id,
        Chat.is_active == 1
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
            "created_at": chat.created_at.isoformat() if chat.created_at else None
        }
        for chat in chats
    ]

    return {"chats": chats_data}


@router.get("/conversation-state/{client_id}")
async def get_conversation_state_endpoint(
    client_id: str,
    session_id: str,
    session: AsyncSession = Depends(get_session),
    x_chatbot_key: str = Header(None)
):
    """Get current conversation state and summary"""
    # Validate client + chatbot_key
    stmt = select(User).where(
        User.client_id == client_id,
        User.chatbot_key == x_chatbot_key
    )
    result = await session.execute(stmt)
    client = result.scalar_one_or_none()

    if not client:
        raise HTTPException(status_code=403, detail="Invalid client or key")

    # Get conversation state from LLM service
    state = get_conversation_state(client_id, session_id)
    return state


@router.post("/reset-conversation/{client_id}")
async def reset_conversation_endpoint(
    client_id: str,
    session_id: str,
    session: AsyncSession = Depends(get_session),
    x_chatbot_key: str = Header(None)
):
    """Reset conversation history for a session"""
    # Validate client + chatbot_key
    stmt = select(User).where(
        User.client_id == client_id,
        User.chatbot_key == x_chatbot_key
    )
    result = await session.execute(stmt)
    client = result.scalar_one_or_none()

    if not client:
        raise HTTPException(status_code=403, detail="Invalid client or key")

    # Reset conversation in LLM service
    result = reset_conversation(client_id, session_id)
    return result


@router.delete("/clear-session/{client_id}")
async def clear_session_endpoint(
    client_id: str,
    session_id: str,
    session: AsyncSession = Depends(get_session),
    x_chatbot_key: str = Header(None)
):
    """Completely remove a session from memory"""
    # Validate client + chatbot_key
    stmt = select(User).where(
        User.client_id == client_id,
        User.chatbot_key == x_chatbot_key
    )
    result = await session.execute(stmt)
    client = result.scalar_one_or_none()

    if not client:
        raise HTTPException(status_code=403, detail="Invalid client or key")

    # Clear session from LLM service
    result = clear_session(client_id, session_id)
    return result