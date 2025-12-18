from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select
from typing import List,Optional
from datetime import datetime
from pydantic import BaseModel

from backend.database import get_session
from backend.auth_utils import get_client_from_header
from backend.models import Shortcut

router = APIRouter(
    prefix='/shortcuts',
    tags=['shortcuts']
)

# Request/Response Models
class ShortcutCreate(BaseModel):
    action_type: str
    command: str
    message: str

class ShortcutUpdate(BaseModel):
    action_type: Optional[str] = None
    command: Optional[str] = None
    message: Optional[str] = None

class ShortcutResponse(BaseModel):
    id: int
    client_id: str
    action_type: str
    command: str
    message: str
    created_at: datetime
    updated_at: datetime


@router.get("/", response_model=List[ShortcutResponse])
async def get_shortcuts(
    client_id: str = Depends(get_client_from_header),
    session: AsyncSession = Depends(get_session)
):
    """Get all active shortcuts for the authenticated client"""
    try:
        stmt = select(Shortcut).where(
            (Shortcut.client_id == client_id) &
            (Shortcut.is_active == 1)
        ).order_by(Shortcut.action_type, Shortcut.command)

        result = await session.execute(stmt)
        shortcuts = result.scalars().all()

        return shortcuts
    except Exception as e:
        print(f"❌ Error fetching shortcuts: {e}")
        raise HTTPException(status_code=500, detail=f"Error fetching shortcuts: {str(e)}")


@router.post("/", response_model=ShortcutResponse)
async def create_shortcut(
    shortcut: ShortcutCreate,
    client_id: str = Depends(get_client_from_header),
    session: AsyncSession = Depends(get_session)
):
    """Create a new shortcut"""
    try:
        # Check if command already exists for this client
        stmt = select(Shortcut).where(
            (Shortcut.client_id == client_id) &
            (Shortcut.command == shortcut.command.lower()) &
            (Shortcut.is_active == 1)
        )
        result = await session.execute(stmt)
        existing = result.scalar_one_or_none()

        if existing:
            raise HTTPException(
                status_code=400,
                detail=f"Shortcut command '/{shortcut.command}' already exists"
            )

        # Create new shortcut
        new_shortcut = Shortcut(
            client_id=client_id,
            action_type=shortcut.action_type,
            command=shortcut.command.lower(),  # Store in lowercase
            message=shortcut.message,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            is_active=1
        )

        session.add(new_shortcut)
        await session.commit()
        await session.refresh(new_shortcut)

        print(f"✅ Created shortcut: /{new_shortcut.command} for client {client_id}")

        return new_shortcut
    except HTTPException:
        raise
    except Exception as e:
        await session.rollback()
        print(f"❌ Error creating shortcut: {e}")
        raise HTTPException(status_code=500, detail=f"Error creating shortcut: {str(e)}")


@router.get("/{shortcut_id}", response_model=ShortcutResponse)
async def get_shortcut(
    shortcut_id: int,
    client_id: str = Depends(get_client_from_header),
    session: AsyncSession = Depends(get_session)
):
    """Get a specific shortcut by ID"""
    try:
        shortcut = await session.get(Shortcut, shortcut_id)

        if not shortcut or shortcut.client_id != client_id or shortcut.is_active == 0:
            raise HTTPException(status_code=404, detail="Shortcut not found")

        return shortcut
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching shortcut: {str(e)}")


@router.get("/command/{command}", response_model=ShortcutResponse)
async def get_shortcut_by_command(
    command: str,
    client_id: str = Depends(get_client_from_header),
    session: AsyncSession = Depends(get_session)
):
    """Get a shortcut by its command (for quick lookup in admin chat)"""
    try:
        # Remove leading slash if present
        command_clean = command.lstrip('/').lower()

        stmt = select(Shortcut).where(
            (Shortcut.client_id == client_id) &
            (Shortcut.command == command_clean) &
            (Shortcut.is_active == 1)
        )
        result = await session.execute(stmt)
        shortcut = result.scalar_one_or_none()

        if not shortcut:
            raise HTTPException(status_code=404, detail=f"Shortcut '/{command_clean}' not found")

        return shortcut
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching shortcut: {str(e)}")


@router.put("/{shortcut_id}", response_model=ShortcutResponse)
async def update_shortcut(
    shortcut_id: int,
    shortcut_update: ShortcutUpdate,
    client_id: str = Depends(get_client_from_header),
    session: AsyncSession = Depends(get_session)
):
    """Update an existing shortcut"""
    try:
        shortcut = await session.get(Shortcut, shortcut_id)

        if not shortcut or shortcut.client_id != client_id or shortcut.is_active == 0:
            raise HTTPException(status_code=404, detail="Shortcut not found")

        # Update fields if provided
        if shortcut_update.action_type:
            shortcut.action_type = shortcut_update.action_type
        if shortcut_update.command:
            # Check if new command conflicts
            stmt = select(Shortcut).where(
                (Shortcut.client_id == client_id) &
                (Shortcut.command == shortcut_update.command.lower()) &
                (Shortcut.id != shortcut_id) &
                (Shortcut.is_active == 1)
            )
            result = await session.execute(stmt)
            existing = result.scalar_one_or_none()
            if existing:
                raise HTTPException(
                    status_code=400,
                    detail=f"Shortcut command '/{shortcut_update.command}' already exists"
                )
            shortcut.command = shortcut_update.command.lower()
        if shortcut_update.message:
            shortcut.message = shortcut_update.message

        shortcut.updated_at = datetime.utcnow()

        session.add(shortcut)
        await session.commit()
        await session.refresh(shortcut)

        print(f"✅ Updated shortcut: /{shortcut.command}")

        return shortcut
    except HTTPException:
        raise
    except Exception as e:
        await session.rollback()
        raise HTTPException(status_code=500, detail=f"Error updating shortcut: {str(e)}")


@router.delete("/{shortcut_id}")
async def delete_shortcut(
    shortcut_id: int,
    client_id: str = Depends(get_client_from_header),
    session: AsyncSession = Depends(get_session)
):
    """Soft delete a shortcut"""
    try:
        shortcut = await session.get(Shortcut, shortcut_id)

        if not shortcut or shortcut.client_id != client_id:
            raise HTTPException(status_code=404, detail="Shortcut not found")

        # Soft delete
        shortcut.is_active = 0
        shortcut.updated_at = datetime.utcnow()

        session.add(shortcut)
        await session.commit()

        print(f"✅ Deleted shortcut: /{shortcut.command}")

        return {"success": True, "message": "Shortcut deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        await session.rollback()
        raise HTTPException(status_code=500, detail=f"Error deleting shortcut: {str(e)}")


@router.post("/bulk-delete")
async def bulk_delete_shortcuts(
    shortcut_ids: List[int],
    client_id: str = Depends(get_client_from_header),
    session: AsyncSession = Depends(get_session)
):
    """Bulk delete multiple shortcuts"""
    try:
        stmt = select(Shortcut).where(
            (Shortcut.client_id == client_id) &
            (Shortcut.id.in_(shortcut_ids))
        )
        result = await session.execute(stmt)
        shortcuts = result.scalars().all()

        deleted_count = 0
        for shortcut in shortcuts:
            shortcut.is_active = 0
            shortcut.updated_at = datetime.utcnow()
            session.add(shortcut)
            deleted_count += 1

        await session.commit()

        print(f"✅ Bulk deleted {deleted_count} shortcuts")

        return {
            "success": True,
            "message": f"Deleted {deleted_count} shortcuts",
            "deleted_count": deleted_count
        }
    except Exception as e:
        await session.rollback()
        raise HTTPException(status_code=500, detail=f"Error bulk deleting shortcuts: {str(e)}")
