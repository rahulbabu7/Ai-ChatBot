from fastapi import APIRouter, Depends, HTTPException,Header,Request,Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func, distinct
from sqlmodel import select
from pydantic import BaseModel
from typing import Dict
from datetime import datetime, timedelta
import threading
import time
from typing import Optional
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
    avg_response_time: float  # NEW: Average response time in seconds
    total_messages: int  # NEW: Total message count

class ResponseTimeStats(BaseModel):
    """Response time statistics"""
    avg_response_time: float
    min_response_time: float
    max_response_time: float
    median_response_time: float
    instant_responses: int  # < 1 second
    fast_responses: int     # 1-2 seconds
    slow_responses: int     # > 2 seconds
    total_responses: int


@router.get("/stats/daily", response_model=StatsResponse)
async def get_daily_stats(
    client_id: str = Depends(get_client_from_header),
    session: AsyncSession = Depends(get_session),
    start_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD)")
):
    """Get daily statistics for a date range (defaults to last 7 days)"""
    try:
        # Parse dates or use defaults
        if start_date and end_date:
            try:
                start = datetime.strptime(start_date, '%Y-%m-%d')
                end = datetime.strptime(end_date, '%Y-%m-%d')
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")
        else:
            end = datetime.now()
            start = end - timedelta(days=6)

        if start > end:
            raise HTTPException(status_code=400, detail="Start date cannot be after end date")

        days_diff = (end - start).days + 1
        if days_diff > 90:
            raise HTTPException(status_code=400, detail="Date range cannot exceed 90 days")

        print(f"📅 Fetching stats from {start.date()} to {end.date()} ({days_diff} days)")

        # Query daily stats with average response time
        stmt = (
            select(
                func.date(Chat.created_at).label('date'),
                func.count(distinct(Chat.session_id)).label('visitors'),
                func.count(Chat.id).label('chats'),
                func.avg(Chat.response_time).label('avg_response_time')  # NEW
            )
            .where(
                Chat.client_id == client_id,
                func.date(Chat.created_at) >= start.date(),
                func.date(Chat.created_at) <= end.date(),
                Chat.role == 'assistant'  # Only count assistant responses
            )
            .group_by(func.date(Chat.created_at))
            .order_by(func.date(Chat.created_at).asc())
        )

        result = await session.execute(stmt)
        rows = result.all()

        # Create stats dictionary
        stats_dict = {}
        for row in rows:
            date_str = row.date if isinstance(row.date, str) else row.date.strftime('%Y-%m-%d')
            stats_dict[date_str] = {
                "date": date_str,
                "visitors": row.visitors,
                "chats": row.chats,
                "avg_response_time": round(row.avg_response_time, 2) if row.avg_response_time else 0.0
            }

        # Fill in missing dates
        daily_stats = []
        current_date = start

        while current_date <= end:
            date_str = current_date.strftime('%Y-%m-%d')
            if date_str in stats_dict:
                daily_stats.append(stats_dict[date_str])
            else:
                daily_stats.append({
                    "date": date_str,
                    "visitors": 0,
                    "chats": 0,
                    "avg_response_time": 0.0
                })
            current_date += timedelta(days=1)

        print(f"📊 Daily stats for {client_id}: {len(daily_stats)} days returned")
        return {"daily_stats": daily_stats}

    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error fetching daily stats: {e}")
        raise HTTPException(status_code=500, detail=f"Error fetching daily stats: {str(e)}")


@router.get("/stats/dashboard", response_model=DashboardStatsResponse)
async def get_dashboard_stats(
    client_id: str = Depends(get_client_from_header),
    session: AsyncSession = Depends(get_session)
):
    """Get all dashboard statistics including response times"""
    try:
        # 1. Total Sessions
        stmt_total = select(func.count(distinct(Chat.session_id))).where(
            Chat.client_id == client_id
        )
        result = await session.execute(stmt_total)
        total_sessions = result.scalar() or 0

        # 2. Today's Sessions
        today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        stmt_today = select(func.count(distinct(Chat.session_id))).where(
            Chat.client_id == client_id,
            Chat.created_at >= today_start
        )
        result = await session.execute(stmt_today)
        today_sessions = result.scalar() or 0

        # 3. Today's Visitors
        today_visitors = today_sessions

        # 4. Active Users Now
        now = datetime.now()
        timeout = timedelta(seconds=45)
        with active_users_lock:
            active_now = sum(
                1 for data in active_users.values()
                if data["client_id"] == client_id and (now - data["last_seen"]) <= timeout
            )

        # 5. Average Response Time (last 7 days) - NEW
        week_ago = datetime.now() - timedelta(days=7)
        stmt_response_time = select(func.avg(Chat.response_time)).where(
            Chat.client_id == client_id,
            Chat.role == 'assistant',
            Chat.response_time.isnot(None),
            Chat.created_at >= week_ago
        )
        result = await session.execute(stmt_response_time)
        avg_response_time = result.scalar() or 0.0
        avg_response_time = round(avg_response_time, 2)

        # 6. Total Messages - NEW
        stmt_total_messages = select(func.count(Chat.id)).where(
            Chat.client_id == client_id
        )
        result = await session.execute(stmt_total_messages)
        total_messages = result.scalar() or 0

        print(f"📊 Dashboard stats for {client_id}: Total={total_sessions}, Today={today_sessions}, Active={active_now}, AvgRT={avg_response_time}s")

        return {
            "total_sessions": total_sessions,
            "today_sessions": today_sessions,
            "today_visitors": today_visitors,
            "active_users_now": active_now,
            "avg_response_time": avg_response_time,
            "total_messages": total_messages
        }
    except Exception as e:
        print(f"❌ Error fetching dashboard stats: {e}")
        raise HTTPException(status_code=500, detail=f"Error fetching dashboard stats: {str(e)}")

@router.get("/stats/response-time", response_model=ResponseTimeStats)
async def get_response_time_stats(
    client_id: str = Depends(get_client_from_header),
    session: AsyncSession = Depends(get_session),
    days: int = Query(7, ge=1, le=90, description="Number of days to analyze")
):
    """Get detailed response time statistics"""
    try:
        start_date = datetime.now() - timedelta(days=days)

        # Get all response times
        stmt = select(Chat.response_time).where(
            Chat.client_id == client_id,
            Chat.role == 'assistant',
            Chat.response_time.isnot(None),
            Chat.created_at >= start_date
        )
        result = await session.execute(stmt)
        response_times = [row[0] for row in result.all()]

        if not response_times:
            return {
                "avg_response_time": 0.0,
                "min_response_time": 0.0,
                "max_response_time": 0.0,
                "median_response_time": 0.0,
                "instant_responses": 0,
                "fast_responses": 0,
                "slow_responses": 0,
                "total_responses": 0
            }

        # Calculate statistics
        response_times.sort()
        total = len(response_times)
        median_idx = total // 2

        instant = sum(1 for rt in response_times if rt < 1.0)
        fast = sum(1 for rt in response_times if 1.0 <= rt <= 2.0)
        slow = sum(1 for rt in response_times if rt > 2.0)

        return {
            "avg_response_time": round(sum(response_times) / total, 2),
            "min_response_time": round(min(response_times), 2),
            "max_response_time": round(max(response_times), 2),
            "median_response_time": round(response_times[median_idx], 2),
            "instant_responses": instant,
            "fast_responses": fast,
            "slow_responses": slow,
            "total_responses": total
        }
    except Exception as e:
        print(f"❌ Error fetching response time stats: {e}")
        raise HTTPException(status_code=500, detail=f"Error fetching response time stats: {str(e)}")

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

session_durations: Dict[str, Dict] = {}
session_duration_lock = threading.Lock()

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
        now = datetime.now()

        with active_users_lock:
            if req.is_chatbot_open:
                # User has chatbot open
                if user_key not in active_users:
                    # New session - record start time
                    session_durations[user_key] = {
                        "start_time": now,
                        "last_seen": now,
                        "total_duration": 0  # in seconds
                    }
                else:
                    # Update existing session
                    if user_key in session_durations:
                        last_seen = session_durations[user_key]["last_seen"]
                        session_durations[user_key]["total_duration"] += (now - last_seen).total_seconds()
                        session_durations[user_key]["last_seen"] = now

                active_users[user_key] = {
                    "client_id": client_id,
                    "session_id": req.session_id,
                    "last_seen": now,
                    "ip": request.client.host if request.client else "unknown",
                    "user_agent": request.headers.get("user-agent", "unknown")
                }
            else:
                # User closed chatbot - calculate final duration
                if user_key in session_durations:
                    last_seen = session_durations[user_key]["last_seen"]
                    session_durations[user_key]["total_duration"] += (now - last_seen).total_seconds()

                    # Store final duration in database (add a new field to Chat model or create SessionDuration table)
                    print(f"📊 Session {req.session_id} duration: {session_durations[user_key]['total_duration']} seconds")

                # Remove from active users
                if user_key in active_users:
                    del active_users[user_key]

        return {"status": "ok", "active": req.is_chatbot_open}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error recording heartbeat: {str(e)}")


@router.get("/session-duration/{session_id}")
async def get_session_duration(
    session_id: str,
    client_id: str = Depends(get_client_from_header)
):
    """Get duration for a specific session"""
    user_key = f"{client_id}:{session_id}"

    with active_users_lock:
        if user_key in session_durations:
            duration_data = session_durations[user_key]
            total_duration = duration_data["total_duration"]

            # If still active, add current time
            if user_key in active_users:
                now = datetime.now()
                total_duration += (now - duration_data["last_seen"]).total_seconds()

            return {
                "session_id": session_id,
                "duration_seconds": round(total_duration, 2),
                "duration_minutes": round(total_duration / 60, 2),
                "is_active": user_key in active_users
            }

    return {
        "session_id": session_id,
        "duration_seconds": 0,
        "duration_minutes": 0,
        "is_active": False
    }

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
