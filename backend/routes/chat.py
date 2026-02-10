import logging
import os
import sys
import uuid
from typing import Optional

import requests
from fastapi import APIRouter, Depends, Header, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from backend.database import get_session
from backend.models import User, Chat, Lead, save_lead_to_db
from backend.schemas import ChatRequest, LeadDataRequest
from backend.auth_utils import get_client_from_header
from backend.routes.websockets import manager
from backend.security_monitor import security_monitor
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
logger = logging.getLogger(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CHATBOT_LLM_DIR = os.path.abspath(os.path.join(BASE_DIR, "../../Chatbot/llm"))
sys.path.append(CHATBOT_LLM_DIR)

# from llm_service import chat_with_model, explain_context, get_conversation_state, reset_conversation, clear_session
from llm_service import chat_with_model, get_conversation_state, reset_conversation, clear_session

router = APIRouter(
    prefix='/client',
    tags=['client']
)


@router.post("/chat/{client_id}")
@limiter.limit("20/minute")
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
    chatbot_session_id = req.session_id or str(uuid.uuid4())

    # Check for suspicious input
    if security_monitor.should_block_session(client_id, chatbot_session_id):
        raise HTTPException(
            status_code=429,
            detail="Session blocked due to suspicious activity"
        )

    is_suspicious, pattern = security_monitor.check_suspicious_input(
        req.message, chatbot_session_id, client_id
    )
    if is_suspicious:
        logger.warning("Suspicious pattern '%s' from client=%s session=%s", pattern, client_id, chatbot_session_id)

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
    await session.refresh(user_chat)  # ← IMPORTANT: Get the database ID

    # Store the user message ID
    user_message_id = user_chat.id

    # Generate chatbot reply with session context
    bot_response = chat_with_model(
        client_id=client_id,
        query=req.message,
        session_id=chatbot_session_id,
        include_history=True,
        # enable_clarifications=True
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
    await session.refresh(assistant_chat)  # ← IMPORTANT: Get the database ID

    # Store the bot message ID
    bot_message_id = assistant_chat.id

    # Broadcast chatbot reply to admin via WebSocket
    await manager.send_to_admin(chatbot_session_id, {
        "type": "new_bot_message",
        "session_id": chatbot_session_id,
        "message": {
            "id": assistant_chat.id,
            "role": "assistant",
            "message": bot_reply,
            "timestamp": assistant_chat.created_at.isoformat().replace('+00:00', 'Z') if assistant_chat.created_at else None,
            "admin_override": False,
            "response_time": response_time
        }
    })

    return {
            "session_id": bot_response.get("session_id", chatbot_session_id),
            "reply": bot_reply,
            "user_message_id": user_message_id,
            "message_id": bot_message_id,
            "admin_override": False,
            "confidence": bot_response.get("confidence"),
            "type": bot_response.get("type"),
            "form_active": bot_response.get("form_active", False),
            "form_status": bot_response.get("form_status"),
            "collected_data": bot_response.get("collected_data"),
            "needs_clarification": bot_response.get("needs_clarification", False),
            "clarification_questions": bot_response.get("clarification_questions", []),
            "follow_up_question": bot_response.get("follow_up_question"),
            "probing_questions": bot_response.get("probing_questions", []),
            "sources": bot_response.get("sources", []),
            "processing_time": bot_response.get("processing_time", response_time),
            "metadata": bot_response.get("metadata", {})
        }

# @router.post("/context/{client_id}")
# async def context_endpoint(
#     client_id: str,
#     req: ChatRequest,
#     session: AsyncSession = Depends(get_session),
#     x_chatbot_key: str = Header(None)
# ):
#     """Debug endpoint to see retrieved context"""
#     # Validate client + chatbot_key
#     stmt = select(User).where(
#         User.client_id == client_id,
#         User.chatbot_key == x_chatbot_key
#     )
#     result = await session.execute(stmt)
#     client = result.scalar_one_or_none()

#     if not client:
#         raise HTTPException(status_code=403, detail="Invalid client or key")

#     # Fetch and explain context for the user
#     ctx = explain_context(client_id, req.message)

#     return {"context": ctx or "No relevant context found."}


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
            "created_at": chat.created_at.isoformat().replace('+00:00', 'Z') if chat.created_at else None
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


@router.post("/save-lead")
@limiter.limit("10/minute")
async def save_lead(
    req: LeadDataRequest,
    request: Request,
    session: AsyncSession = Depends(get_session),
    x_chatbot_key: str = Header(None)
):
    """Save collected lead data from chatbot form to database"""
    try:
        # Validate client
        stmt = select(User).where(
            User.client_id == req.client_id,
            User.chatbot_key == x_chatbot_key
        )
        result = await session.execute(stmt)
        client = result.scalar_one_or_none()

        if not client:
            raise HTTPException(status_code=403, detail="Invalid client or key")

        # Get user location and user-agent
        user_agent = request.headers.get("user-agent", "unknown")
        user_ip = request.client.host if request.client else "unknown"

        # Get country code (optional - reuse your existing logic)
        try:
            location_response = requests.get(f"https://ipinfo.io/{user_ip}/json", timeout=2)
            location_data = location_response.json()
            country_code = location_data.get("country", "Unknown")
        except Exception:
            country_code = "Unknown"

        # Save lead to database
        lead = await save_lead_to_db(
            session=session,
            client_id=req.client_id,
            session_id=req.session_id,
            lead_data=req.lead_data,
            form_type=req.form_type,
            country_code=country_code,
            user_agent=user_agent
        )

        if not lead:
            raise HTTPException(
                status_code=500,
                detail="Failed to save lead data"
            )

        print(f"✅ Lead saved: ID={lead.id}, Email={lead.email}, Name={lead.name}")

        return {
            "success": True,
            "message": "Lead data saved successfully",
            "lead_id": lead.id,
            "data": lead.to_dict_ist()
        }

    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error in save_lead endpoint: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to save lead data: {str(e)}"
        )
