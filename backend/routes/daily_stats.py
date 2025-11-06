from fastapi import APIRouter, Depends, HTTPException,Header,Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func, distinct
from sqlmodel import select
from pydantic import BaseModel
from typing import Dict
from datetime import datetime, timedelta
import threading
import time

from backend.database import get_session
from backend.models import Chat,User
from backend.auth_utils import get_client_from_header
from backend.schemas import HeartbeatRequest, StatsResponse

router = APIRouter(
    prefix='/client',
    tags=['stats']
)

# Thread-safe lock for active users
active_users_lock = threading.Lock()

# In-memory store for active users (use Redis in production)
active_users: Dict[str, Dict] = {}


# Additional response model for dashboard stats
class DashboardStatsResponse(BaseModel):
    total_sessions: int
    today_sessions: int
    today_visitors: int
    active_users_now: int


@router.get("/stats/daily", response_model=StatsResponse)
async def get_daily_stats(
    client_id: str = Depends(get_client_from_header),
    session: AsyncSession = Depends(get_session)
):
    """Get daily statistics for the last 7 days"""
    try:
        # Calculate date range for last 7 days
        end_date = datetime.now()
        start_date = end_date - timedelta(days=6)

        # Query to get daily stats using SQLAlchemy
        stmt = (
            select(
                func.date(Chat.created_at).label('date'),
                func.count(distinct(Chat.session_id)).label('visitors'),
                func.count(Chat.id).label('chats')
            )
            .where(
                Chat.client_id == client_id,
                func.date(Chat.created_at) >= start_date.date(),
                func.date(Chat.created_at) <= end_date.date()
            )
            .group_by(func.date(Chat.created_at))
            .order_by(func.date(Chat.created_at).asc())
        )

        result = await session.execute(stmt)
        rows = result.all()

        # Create a dictionary for easy lookup
        stats_dict = {}
        for row in rows:
            date_str = row.date if isinstance(row.date, str) else row.date.strftime('%Y-%m-%d')
            stats_dict[date_str] = {
                "date": date_str,
                "visitors": row.visitors,
                "chats": row.chats
            }

        # Fill in missing dates with zeros
        daily_stats = []
        current_date = start_date

        while current_date <= end_date:
            date_str = current_date.strftime('%Y-%m-%d')

            if date_str in stats_dict:
                daily_stats.append(stats_dict[date_str])
            else:
                daily_stats.append({
                    "date": date_str,
                    "visitors": 0,
                    "chats": 0
                })

            current_date += timedelta(days=1)

        print(f"📊 Daily stats for {client_id}: {daily_stats}")

        return {"daily_stats": daily_stats}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching daily stats: {str(e)}")


@router.get("/stats/dashboard", response_model=DashboardStatsResponse)
async def get_dashboard_stats(
    client_id: str = Depends(get_client_from_header),
    session: AsyncSession = Depends(get_session)
):
    """Get all dashboard statistics in one call"""
    try:
        # 1. Total Sessions (all time)
        stmt_total = select(func.count(distinct(Chat.session_id))).where(
            Chat.client_id == client_id
        )
        result = await session.execute(stmt_total)
        total_sessions = result.scalar() or 0

        # 2. Today's Sessions (unique sessions today)
        today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        stmt_today = select(func.count(distinct(Chat.session_id))).where(
            Chat.client_id == client_id,
            Chat.created_at >= today_start
        )
        result = await session.execute(stmt_today)
        today_sessions = result.scalar() or 0

        # 3. Today's Visitors (same as today's sessions - unique users)
        today_visitors = today_sessions

        # 4. Active Users Now (from heartbeat - chatbot currently open)
        now = datetime.now()
        timeout = timedelta(seconds=45)

        with active_users_lock:
            active_now = sum(
                1 for data in active_users.values()
                if data["client_id"] == client_id and (now - data["last_seen"]) <= timeout
            )

        print(f"📊 Dashboard stats for {client_id}: Total={total_sessions}, Today={today_sessions}, Active={active_now}")

        return {
            "total_sessions": total_sessions,
            "today_sessions": today_sessions,
            "today_visitors": today_visitors,
            "active_users_now": active_now
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching dashboard stats: {str(e)}")


@router.post("/heartbeat")
async def heartbeat(
    req: HeartbeatRequest,
    client_id: str = Depends(get_client_from_header)
):
    """Record user heartbeat to track active users (authenticated client)"""
    try:
        key = f"{client_id}:{req.session_id}"

        with active_users_lock:
            active_users[key] = {
                "client_id": client_id,
                "session_id": req.session_id,
                "is_chatbot_open": req.is_chatbot_open,
                "last_seen": datetime.now()
            }

        return {"status": "ok", "active_users": len([
            u for u in active_users.values() if u["client_id"] == client_id
        ])}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error recording heartbeat: {str(e)}")


@router.post("/heartbeat/{client_id}")
async def chatbot_heartbeat(
    client_id: str,
    req: HeartbeatRequest,
    request: Request,
    session: AsyncSession = Depends(get_session),
    x_chatbot_key: str = Header(None)
):
    """Track active chatbot users with heartbeat mechanism (public endpoint with key validation)"""
    try:
        # Validate client + chatbot_key
        stmt = select(User).where(
            User.client_id == client_id,
            User.chatbot_key == x_chatbot_key
        )
        result = await session.execute(stmt)
        client = result.scalar_one_or_none()

        if not client:
            raise HTTPException(status_code=403, detail="Invalid client or key")

        # Create unique key for this user
        user_key = f"{client_id}:{req.session_id}"

        with active_users_lock:
            if req.is_chatbot_open:
                # User has chatbot open - update/add to active users
                active_users[user_key] = {
                    "client_id": client_id,
                    "session_id": req.session_id,
                    "last_seen": datetime.now(),
                    "ip": request.client.host if request.client else "unknown",
                    "user_agent": request.headers.get("user-agent", "unknown")
                }
            else:
                # User closed chatbot - remove from active users
                if user_key in active_users:
                    del active_users[user_key]

        return {"status": "ok", "active": req.is_chatbot_open}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error recording heartbeat: {str(e)}")


@router.get("/active-users/me")
async def get_active_users(
    client_id: str = Depends(get_client_from_header)
):
    """Get count of currently active users for this client"""
    try:
        now = datetime.now()
        timeout = timedelta(seconds=45)  # Consider inactive after 45 seconds without heartbeat

        with active_users_lock:
            # Clean up stale entries for this client
            stale_keys = [
                key for key, data in active_users.items()
                if data["client_id"] == client_id and (now - data["last_seen"]) > timeout
            ]
            for key in stale_keys:
                del active_users[key]

            # Count active users for this client
            active_count = sum(1 for data in active_users.values() if data["client_id"] == client_id)

            # Get detailed info
            active_sessions = [
                {
                    "session_id": data["session_id"],
                    "last_seen": data["last_seen"].isoformat(),
                    "ip": data.get("ip", "unknown"),
                    "user_agent": data.get("user_agent", "unknown")
                }
                for key, data in active_users.items()
                if data["client_id"] == client_id and (now - data["last_seen"]) <= timeout
            ]

        return {
            "active_users": active_count,
            "sessions": active_sessions
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching active users: {str(e)}")


# Background cleanup task
def cleanup_stale_users():
    """Background thread to clean up stale users"""
    while True:
        time.sleep(30)
        now = datetime.now()
        timeout = timedelta(seconds=45)

        with active_users_lock:
            stale_keys = [
                key for key, data in active_users.items()
                if (now - data["last_seen"]) > timeout
            ]

            for key in stale_keys:
                print(f"🧹 Cleaning stale user: {key}")
                del active_users[key]


# Start background cleanup thread
cleanup_thread = threading.Thread(target=cleanup_stale_users, daemon=True)
cleanup_thread.start()
