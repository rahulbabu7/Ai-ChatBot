# from fastapi import APIRouter, Depends, HTTPException, Header
# from sqlalchemy.ext.asyncio import AsyncSession
# from sqlalchemy import func, desc, case
# from sqlmodel import select
# from typing import Optional
# from datetime import datetime, timedelta, timezone
#
# from backend.database import get_session
# from backend.auth_utils import get_client_from_header
# from backend.models import Chat, User
# from backend.schemas import AdminReplyRequest
# from backend.routes.websockets import manager
#
# router = APIRouter(
#     prefix='/client',
#     tags=['client-sessions']
# )
#
#
# # @router.post("/client-reply/{session_id}")
# # async def admin_reply(
# #     session_id: str,
# #     req: AdminReplyRequest,
# #     client_id: str = Depends(get_client_from_header),
# #     session: AsyncSession = Depends(get_session)
# # ):
# #     """Admin sends a manual reply to override chatbot"""
# #     try:
# #         # Optional: Uncomment to replace last bot message
# #         # statement = select(Chat).where(
# #         #     (Chat.client_id == client_id) &
# #         #     (Chat.session_id == session_id) &
# #         #     (Chat.role == 'assistant') &
# #         #     (Chat.admin_override == 0) &
# #         #     (Chat.is_active == 1)
# #         # ).order_by(Chat.created_at.desc()).limit(1)
# #         # result = await session.execute(statement)
# #         # last_bot_message = result.scalar_one_or_none()
# #         #
# #         # if last_bot_message:
# #         #     last_bot_message.is_active = 0
# #         #     session.add(last_bot_message)
#
# #         print(f"✅ Inserting admin override message")
#
# #         # Insert admin's override message
# #         admin_message = Chat(
# #             client_id=client_id,
# #             session_id=session_id,
# #             role='assistant',
# #             message=req.message,
# #             admin_override=1,
# #             user_agent='admin-override',
# #             is_active=1
# #         )
# #         session.add(admin_message)
# #         await session.commit()
#
# #         print(f"✅ Admin reply inserted successfully for session {session_id}")
#
# #         return {
# #             "success": True,
# #             "message": "Admin reply sent successfully"
# #         }
#
# #     except Exception as e:
# #         await session.rollback()
# #         print(f"❌ Failed to send admin reply: {str(e)}")
# #         import traceback
# #         traceback.print_exc()
# #         raise HTTPException(
# #             status_code=500,
# #             detail=f"Failed to send admin reply: {str(e)}"
# #         )
#
# @router.post("/client-reply/{session_id}")
# async def send_admin_reply_with_websocket(
#     session_id: str,
#     req: AdminReplyRequest,
#     client_id: str = Depends(get_client_from_header),
#     session: AsyncSession = Depends(get_session)
# ):
#     """Helper function to send admin reply via both DB and WebSocket"""
#
#     # Save to database (existing logic)
#     admin_message = Chat(
#         client_id=client_id,
#         session_id=session_id,
#         role='assistant',
#         message=req.message,
#         admin_override=1,
#         user_agent='admin-override',
#         is_active=1
#     )
#     session.add(admin_message)
#     await session.commit()
#     await session.refresh(admin_message)
#
#     # Broadcast via WebSocket
#     await manager.send_to_client(session_id, {
#         "type": "admin_message",
#         "id": admin_message.id,
#         "message": req.message,
#         "timestamp": admin_message.created_at.isoformat().replace('+00:00', 'Z') if admin_message.created_at else None,
#         "admin_override": True
#     })
#
#     return admin_message
#
# @router.get("/session-details/{session_id}")
# async def get_session_details(
#     session_id: str,
#     client_id: str = Depends(get_client_from_header),
#     session: AsyncSession = Depends(get_session)
# ):
#     """Get full session details including user info and chat history"""
#     try:
#         # Get all active chats for this session
#         statement = select(Chat).where(
#             (Chat.client_id == client_id) &
#             (Chat.session_id == session_id) &
#             (Chat.is_active == 1)
#         ).order_by(Chat.created_at.asc())
#
#         result = await session.execute(statement)
#         chats = result.scalars().all()
#
#         # Get session metadata (first message info)
#         statement = select(
#             Chat.country_code,
#             Chat.user_agent,
#             func.min(Chat.created_at).label('started_at')
#         ).where(
#             (Chat.client_id == client_id) &
#             (Chat.session_id == session_id)
#         ).group_by(Chat.session_id)
#
#         result = await session.execute(statement)
#         session_info = result.first()
#
#         chat_list = [
#             {
#                 "id": chat.id,
#                 "role": chat.role,
#                 "message": chat.message,
#                 "created_at": chat.created_at.isoformat().replace('+00:00', 'Z') if chat.created_at else None,
#                 "admin_override": chat.admin_override,
#                 "country_code": chat.country_code,
#                 "user_agent": chat.user_agent
#             }
#             for chat in chats
#         ]
#
#         session_info_dict = {}
#         if session_info:
#             session_info_dict = {
#                 "country_code": session_info.country_code,
#                 "user_agent": session_info.user_agent,
#                 "started_at": session_info.started_at.isoformat().replace('+00:00', 'Z') if session_info.started_at else None
#             }
#
#         return {
#             "session_id": session_id,
#             "chats": chat_list,
#             "session_info": session_info_dict,
#             "total_messages": len(chat_list)
#         }
#
#     except Exception as e:
#         raise HTTPException(
#             status_code=500,
#             detail=f"Error fetching session details: {str(e)}"
#         )
#
#
# @router.get("/active-sessions/me")
# async def get_active_sessions(
#     client_id: str = Depends(get_client_from_header),
#     session: AsyncSession = Depends(get_session)
# ):
#     """Get sessions that have recent activity (last 24 hours)"""
#     try:
#         # Calculate 24 hours ago
#         twenty_four_hours_ago = datetime.now(timezone.utc) - timedelta(hours=24)
#
#         # Build the query with aggregations
#         statement = select(
#             Chat.session_id,
#             func.max(Chat.created_at).label('last_activity'),
#             func.count().label('message_count'),
#             func.max(
#                 case((Chat.role == 'user', Chat.message), else_=None)
#             ).label('last_user_message'),
#             Chat.country_code,
#             Chat.user_agent
#         ).where(
#             (Chat.client_id == client_id) &
#             (Chat.created_at >= twenty_four_hours_ago) &
#             (Chat.is_active == 1)
#         ).group_by(Chat.session_id).order_by(desc('last_activity'))
#
#         result = await session.execute(statement)
#         rows = result.all()
#
#         sessions = [
#             {
#                 "session_id": row.session_id,
#                 "last_activity": row.last_activity,
#                 "message_count": row.message_count,
#                 "last_user_message": row.last_user_message,
#                 "country_code": row.country_code,
#                 "user_agent": row.user_agent
#             }
#             for row in rows
#         ]
#
#         return {"active_sessions": sessions, "count": len(sessions)}
#
#     except Exception as e:
#         raise HTTPException(
#             status_code=500,
#             detail=f"Error fetching active sessions: {str(e)}"
#         )
#
#
# @router.delete("/delete-chat/{chat_id}")
# async def delete_chat_message(
#     chat_id: int,
#     client_id: str = Depends(get_client_from_header),
#     session: AsyncSession = Depends(get_session)
# ):
#     """Soft delete a specific chat message"""
#     try:
#         # Get the chat message
#         chat = await session.get(Chat, chat_id)
#
#         if not chat:
#             raise HTTPException(status_code=404, detail="Chat message not found")
#
#         # Verify ownership
#         if chat.client_id != client_id:
#             raise HTTPException(status_code=403, detail="Unauthorized")
#
#         # Soft delete by marking as inactive
#         chat.is_active = 0
#         session.add(chat)
#         await session.commit()
#
#         return {"success": True, "message": "Chat message deleted"}
#
#     except HTTPException:
#         raise
#     except Exception as e:
#         await session.rollback()
#         raise HTTPException(
#             status_code=500,
#             detail=f"Failed to delete message: {str(e)}"
#         )
#
#
# @router.get("/chat-history/{client_id}/{session_id}")
# async def get_public_chat_history(
#     client_id: str,
#     session_id: str,
#     x_chatbot_key: Optional[str] = Header(None),
#     session: AsyncSession = Depends(get_session)
# ):
#     """Public endpoint for chatbot widget to get chat history"""
#     try:
#         # Validate client + chatbot_key
#         statement = select(User).where(
#             (User.client_id == client_id) &
#             (User.chatbot_key == x_chatbot_key)
#         )
#         result = await session.execute(statement)
#         client = result.scalar_one_or_none()
#
#         if not client:
#             raise HTTPException(status_code=403, detail="Invalid client or key")
#
#         # Get all active chats for this session
#         statement = select(Chat).where(
#             (Chat.client_id == client_id) &
#             (Chat.session_id == session_id) &
#             (Chat.is_active == 1)
#         ).order_by(Chat.created_at.asc())
#
#         result = await session.execute(statement)
#         chats = result.scalars().all()
#
#         chat_list = [
#             {
#                 "id": chat.id,
#                 "role": chat.role,
#                 "message": chat.message,
#                 "created_at": chat.created_at,
#                 "admin_override": chat.admin_override,
#                 "country_code": chat.country_code,
#                 "user_agent": chat.user_agent
#             }
#             for chat in chats
#         ]
#
#         return {"chats": chat_list}
#
#     except HTTPException:
#         raise
#     except Exception as e:
#         raise HTTPException(
#             status_code=500,
#             detail=f"Error fetching chat history: {str(e)}"
#         )



from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func, desc, case
from sqlmodel import select
from typing import Optional
from datetime import datetime, timedelta, timezone

from backend.database import get_session
from backend.auth_utils import get_client_from_header
from backend.models import Chat, User
from backend.schemas import AdminReplyRequest
from backend.routes.websockets import manager

router = APIRouter(
    prefix='/client',
    tags=['client-sessions']
)


def ist_now() -> datetime:
    """Get current IST datetime"""
    ist_tz = timezone(timedelta(hours=5, minutes=30))
    return datetime.now(ist_tz)


def utc_to_ist(utc_dt: datetime) -> datetime:
    """Convert UTC datetime to IST"""
    if utc_dt is None:
        return None

    # If datetime is naive, assume it's UTC
    if utc_dt.tzinfo is None:
        utc_dt = utc_dt.replace(tzinfo=timezone.utc)

    # Convert to IST
    ist_tz = timezone(timedelta(hours=5, minutes=30))
    return utc_dt.astimezone(ist_tz)


@router.post("/client-reply/{session_id}")
async def send_admin_reply_with_websocket(
    session_id: str,
    req: AdminReplyRequest,
    client_id: str = Depends(get_client_from_header),
    session: AsyncSession = Depends(get_session)
):
    """Send admin reply via both DB and WebSocket"""
    try:
        # Save to database
        admin_message = Chat(
            client_id=client_id,
            session_id=session_id,
            role='assistant',
            message=req.message,
            admin_override=1,
            user_agent='admin-override',
            is_active=1
        )
        session.add(admin_message)
        await session.commit()
        await session.refresh(admin_message)

        print(f"✅ Admin reply saved to DB with ID: {admin_message.id}")

        # Convert UTC to IST for response
        ist_timestamp = utc_to_ist(admin_message.created_at)

        # Broadcast via WebSocket to client only
        await manager.send_to_client(session_id, {
            "type": "admin_message",
            "id": admin_message.id,
            "message": req.message,
            "timestamp": ist_timestamp.isoformat(),
            "admin_override": True
        })

        print(f"✅ Admin reply broadcasted via WebSocket")

        return {
            "success": True,
            "message": "Admin reply sent successfully",
            "message_id": admin_message.id,
            "timestamp": ist_timestamp.isoformat()
        }

    except Exception as e:
        await session.rollback()
        print(f"❌ Failed to send admin reply: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to send admin reply: {str(e)}"
        )


@router.get("/session-details/{session_id}")
async def get_session_details(
    session_id: str,
    client_id: str = Depends(get_client_from_header),
    session: AsyncSession = Depends(get_session)
):
    """Get full session details with IST timestamps"""
    try:
        # Get all active chats for this session
        statement = select(Chat).where(
            (Chat.client_id == client_id) &
            (Chat.session_id == session_id) &
            (Chat.is_active == 1)
        ).order_by(Chat.created_at.asc())

        result = await session.execute(statement)
        chats = result.scalars().all()

        # Get session metadata
        statement = select(
            Chat.country_code,
            Chat.user_agent,
            func.min(Chat.created_at).label('started_at')
        ).where(
            (Chat.client_id == client_id) &
            (Chat.session_id == session_id)
        ).group_by(Chat.session_id)

        result = await session.execute(statement)
        session_info = result.first()

        # Convert chats to dict with IST timestamps
        chat_list = [
            {
                "id": chat.id,
                "role": chat.role,
                "message": chat.message,
                "created_at": utc_to_ist(chat.created_at).isoformat() if chat.created_at else None,
                "admin_override": chat.admin_override,
                "country_code": chat.country_code,
                "user_agent": chat.user_agent
            }
            for chat in chats
        ]

        session_info_dict = {}
        if session_info:
            session_info_dict = {
                "country_code": session_info.country_code,
                "user_agent": session_info.user_agent,
                "started_at": utc_to_ist(session_info.started_at).isoformat() if session_info.started_at else None
            }

        return {
            "session_id": session_id,
            "chats": chat_list,
            "session_info": session_info_dict,
            "total_messages": len(chat_list)
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error fetching session details: {str(e)}"
        )


@router.get("/active-sessions/me")
async def get_active_sessions(
    client_id: str = Depends(get_client_from_header),
    session: AsyncSession = Depends(get_session)
):
    """Get sessions with recent activity (last 24 hours) with IST timestamps"""
    try:
        # Calculate 24 hours ago in UTC
        twenty_four_hours_ago = datetime.now(timezone.utc) - timedelta(hours=24)

        # Build the query with aggregations
        statement = select(
            Chat.session_id,
            func.max(Chat.created_at).label('last_activity'),
            func.count().label('message_count'),
            func.max(
                case((Chat.role == 'user', Chat.message), else_=None)
            ).label('last_user_message'),
            Chat.country_code,
            Chat.user_agent
        ).where(
            (Chat.client_id == client_id) &
            (Chat.created_at >= twenty_four_hours_ago) &
            (Chat.is_active == 1)
        ).group_by(Chat.session_id).order_by(desc('last_activity'))

        result = await session.execute(statement)
        rows = result.all()

        # Convert to IST timestamps
        sessions = [
            {
                "session_id": row.session_id,
                "last_activity": utc_to_ist(row.last_activity).isoformat() if row.last_activity else None,
                "message_count": row.message_count,
                "last_user_message": row.last_user_message,
                "country_code": row.country_code,
                "user_agent": row.user_agent
            }
            for row in rows
        ]

        return {"active_sessions": sessions, "count": len(sessions)}

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error fetching active sessions: {str(e)}"
        )


@router.delete("/delete-chat/{chat_id}")
async def delete_chat_message(
    chat_id: int,
    client_id: str = Depends(get_client_from_header),
    session: AsyncSession = Depends(get_session)
):
    """Soft delete a specific chat message"""
    try:
        # Get the chat message
        chat = await session.get(Chat, chat_id)

        if not chat:
            raise HTTPException(status_code=404, detail="Chat message not found")

        # Verify ownership
        if chat.client_id != client_id:
            raise HTTPException(status_code=403, detail="Unauthorized")

        # Soft delete by marking as inactive
        chat.is_active = 0
        session.add(chat)
        await session.commit()

        return {"success": True, "message": "Chat message deleted"}

    except HTTPException:
        raise
    except Exception as e:
        await session.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to delete message: {str(e)}"
        )


@router.get("/chat-history/{client_id}/{session_id}")
async def get_public_chat_history(
    client_id: str,
    session_id: str,
    x_chatbot_key: Optional[str] = Header(None),
    session: AsyncSession = Depends(get_session)
):
    """Public endpoint for chatbot widget to get chat history with IST timestamps"""
    try:
        # Validate client + chatbot_key
        statement = select(User).where(
            (User.client_id == client_id) &
            (User.chatbot_key == x_chatbot_key)
        )
        result = await session.execute(statement)
        client = result.scalar_one_or_none()

        if not client:
            raise HTTPException(status_code=403, detail="Invalid client or key")

        # Get all active chats for this session
        statement = select(Chat).where(
            (Chat.client_id == client_id) &
            (Chat.session_id == session_id) &
            (Chat.is_active == 1)
        ).order_by(Chat.created_at.asc())

        result = await session.execute(statement)
        chats = result.scalars().all()

        # Convert to dict with IST timestamps
        chat_list = [
            {
                "id": chat.id,
                "role": chat.role,
                "message": chat.message,
                "created_at": utc_to_ist(chat.created_at).isoformat() if chat.created_at else None,
                "admin_override": chat.admin_override,
                "country_code": chat.country_code,
                "user_agent": chat.user_agent
            }
            for chat in chats
        ]

        return {"chats": chat_list}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error fetching chat history: {str(e)}"
        )
