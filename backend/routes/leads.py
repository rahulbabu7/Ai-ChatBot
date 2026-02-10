from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select, func
from typing import Optional
from datetime import datetime, timezone, timedelta
from backend.database import get_session
from backend.models import Lead, get_leads_for_client, update_lead_status
from backend.auth_utils import get_client_from_header
from backend.schemas import UpdateLeadStatusRequest
# ============================================================================
# ROUTER
# ============================================================================

router = APIRouter(
    prefix='/leads',
    tags=['leads']
)


# ============================================================================
# GET ALL LEADS
# ============================================================================

@router.get("/me")
async def get_my_leads(
    status: Optional[str] = None,
    limit: int = 100,
    client_id: str = Depends(get_client_from_header),
    session: AsyncSession = Depends(get_session)
):
    """Get all leads for authenticated client"""
    try:
        leads = await get_leads_for_client(
            session=session,
            client_id=client_id,
            status=status,
            limit=limit
        )

        return {
            "leads": leads,
            "count": len(leads)
        }

    except Exception as e:
        print(f"❌ Error fetching leads: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch leads: {str(e)}"
        )


# ============================================================================
# GET LEAD STATISTICS
# ============================================================================

@router.get("/stats/me")
async def get_lead_stats(
    client_id: str = Depends(get_client_from_header),
    session: AsyncSession = Depends(get_session)
):
    """Get lead statistics for authenticated client"""
    try:
        # Total leads
        total_stmt = select(func.count(Lead.id)).where(Lead.client_id == client_id)
        total_result = await session.execute(total_stmt)
        total_leads = total_result.scalar()

        # Leads by status
        status_stmt = select(Lead.status, func.count(Lead.id)).where(
            Lead.client_id == client_id
        ).group_by(Lead.status)
        status_result = await session.execute(status_stmt)
        status_counts = {row[0]: row[1] for row in status_result.all()}

        # Recent leads (last 7 days)
        seven_days_ago = datetime.now(timezone.utc) - timedelta(days=7)
        recent_stmt = select(func.count(Lead.id)).where(
            Lead.client_id == client_id,
            Lead.created_at >= seven_days_ago
        )
        recent_result = await session.execute(recent_stmt)
        recent_leads = recent_result.scalar()

        return {
            "total_leads": total_leads,
            "leads_by_status": status_counts,
            "recent_leads_7d": recent_leads
        }

    except Exception as e:
        print(f"❌ Error fetching lead stats: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch lead stats: {str(e)}"
        )


# ============================================================================
# GET SINGLE LEAD DETAILS
# ============================================================================

@router.get("/{lead_id}")
async def get_lead_details(
    lead_id: int,
    client_id: str = Depends(get_client_from_header),
    session: AsyncSession = Depends(get_session)
):
    """Get detailed information about a specific lead"""
    try:
        lead = await session.get(Lead, lead_id)

        if not lead or lead.client_id != client_id:
            raise HTTPException(status_code=404, detail="Lead not found")

        return lead.to_dict_ist()

    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error fetching lead details: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch lead details: {str(e)}"
        )


# ============================================================================
# UPDATE LEAD STATUS
# ============================================================================

@router.patch("/{lead_id}/status")
async def update_lead_status_endpoint(
    lead_id: int,
    req: UpdateLeadStatusRequest,  # Changed to use Pydantic model
    client_id: str = Depends(get_client_from_header),
    session: AsyncSession = Depends(get_session)
):
    """Update lead status"""
    try:
        # Verify lead belongs to client
        lead = await session.get(Lead, lead_id)
        if not lead or lead.client_id != client_id:
            raise HTTPException(status_code=404, detail="Lead not found")

        # Valid statuses
        valid_statuses = ["new", "contacted", "converted", "closed"]
        if req.status not in valid_statuses:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid status. Must be one of: {', '.join(valid_statuses)}"
            )

        success = await update_lead_status(
            session=session,
            lead_id=lead_id,
            status=req.status,
            notes=req.notes
        )

        if not success:
            raise HTTPException(status_code=500, detail="Failed to update lead status")

        return {
            "success": True,
            "message": f"Lead status updated to '{req.status}'"
        }

    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error updating lead status: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to update lead status: {str(e)}"
        )


# ============================================================================
# DELETE LEAD (Optional)
# ============================================================================

@router.delete("/{lead_id}")
async def delete_lead(
    lead_id: int,
    client_id: str = Depends(get_client_from_header),
    session: AsyncSession = Depends(get_session)
):
    """Delete a lead (optional endpoint)"""
    try:
        # Verify lead belongs to client
        lead = await session.get(Lead, lead_id)
        if not lead or lead.client_id != client_id:
            raise HTTPException(status_code=404, detail="Lead not found")

        await session.delete(lead)
        await session.commit()

        return {
            "success": True,
            "message": f"Lead #{lead_id} deleted successfully"
        }

    except HTTPException:
        raise
    except Exception as e:
        await session.rollback()
        print(f"❌ Error deleting lead: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to delete lead: {str(e)}"
        )
