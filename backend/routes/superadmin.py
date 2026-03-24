from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from backend.database import get_session
from backend.models import User, Chat, Lead
from backend.auth_utils import get_client_from_header
from backend.schemas import PlanUpdateRequest

router = APIRouter(prefix="/superadmin", tags=["superadmin"])


# ── Auth guard ────────────────────────────────────────────────────────────────

async def require_superadmin(
    client_id: str = Depends(get_client_from_header),
    session: AsyncSession = Depends(get_session),
) -> str:
    stmt = select(User).where(User.client_id == client_id)
    result = await session.execute(stmt)
    user = result.scalar_one_or_none()
    if not user or user.role != "superadmin":
        raise HTTPException(status_code=403, detail="Superadmin access required")
    return client_id


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("/clients")
async def list_clients(
    _: str = Depends(require_superadmin),
    session: AsyncSession = Depends(get_session),
):
    """List all client accounts with key stats."""
    stmt = select(User).where(User.role == "client").order_by(User.id.asc())
    result = await session.execute(stmt)
    clients = result.scalars().all()

    rows = []
    for c in clients:
        stmt_last = select(func.max(Chat.created_at)).where(Chat.client_id == c.client_id)
        last_active = (await session.execute(stmt_last)).scalar()

        stmt_chats = select(func.count(Chat.id)).where(Chat.client_id == c.client_id)
        total_chats = (await session.execute(stmt_chats)).scalar() or 0

        stmt_leads = select(func.count(Lead.id)).where(Lead.client_id == c.client_id)
        total_leads = (await session.execute(stmt_leads)).scalar() or 0

        rows.append({
            "client_id": c.client_id,
            "name": c.name or c.username,
            "email": c.email,
            "plan": c.plan,
            "chatbot_enabled": bool(c.chatbot_enabled),
            "plan_expires_at": c.plan_expires_at.isoformat() if c.plan_expires_at else None,
            "last_active": last_active.isoformat() if last_active else None,
            "total_chats": total_chats,
            "total_leads": total_leads,
        })

    return {"clients": rows, "total": len(rows)}


@router.patch("/client/{client_id}/toggle")
async def toggle_chatbot(
    client_id: str,
    _: str = Depends(require_superadmin),
    session: AsyncSession = Depends(get_session),
):
    """Enable or disable a client's chatbot (kill switch)."""
    stmt = select(User).where(User.client_id == client_id, User.role == "client")
    result = await session.execute(stmt)
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="Client not found")

    user.chatbot_enabled = not user.chatbot_enabled
    session.add(user)
    await session.commit()

    status = "enabled" if user.chatbot_enabled else "disabled"
    return {"client_id": client_id, "chatbot_enabled": user.chatbot_enabled, "message": f"Chatbot {status}"}


@router.patch("/client/{client_id}/plan")
async def update_plan(
    client_id: str,
    body: PlanUpdateRequest,
    _: str = Depends(require_superadmin),
    session: AsyncSession = Depends(get_session),
):
    """Set a client's plan and optional expiry date."""
    valid_plans = {"trial", "paid", "cancelled"}
    if body.plan not in valid_plans:
        raise HTTPException(status_code=400, detail=f"Plan must be one of {valid_plans}")

    stmt = select(User).where(User.client_id == client_id, User.role == "client")
    result = await session.execute(stmt)
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="Client not found")

    user.plan = body.plan
    user.plan_expires_at = (
        datetime.utcnow() + timedelta(days=body.expires_days)
        if body.expires_days is not None
        else None
    )

    # Auto-disable on cancellation
    if body.plan == "cancelled":
        user.chatbot_enabled = False

    session.add(user)
    await session.commit()

    return {
        "client_id": client_id,
        "plan": user.plan,
        "chatbot_enabled": user.chatbot_enabled,
        "plan_expires_at": user.plan_expires_at.isoformat() if user.plan_expires_at else None,
    }
