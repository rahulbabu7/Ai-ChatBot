from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select
from typing import List

# Assuming these imports from your project structure
from backend.database import get_session  # Your async session dependency
from backend.auth_utils import get_client_from_header  # Your auth dependency
from backend.models import (
    DomainMapping,
    User,
    register_domain,
    remove_domain,
    _clean_domain,
    get_client_by_domain
)

router = APIRouter(
    prefix='/client',
    tags=['client']
)


@router.get("/domains/me")
async def get_domains(
    client_id: str = Depends(get_client_from_header),
    session: AsyncSession = Depends(get_session)
):
    """Get all domains registered for the authenticated client"""
    try:
        statement = select(DomainMapping).where(
            DomainMapping.client_id == client_id
        ).order_by(DomainMapping.created_at.desc())

        result = await session.execute(statement)
        domains = result.scalars().all()

        return {
            "domains": [
                {
                    "domain": dm.domain,
                    "created_at": dm.created_at
                }
                for dm in domains
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching domains: {str(e)}")


@router.get("/lookup-by-domain")
async def lookup_client_by_domain_route(
    domain: str,
    session: AsyncSession = Depends(get_session)
):
    """Lookup client information by domain (public endpoint)"""
    try:
        result = await get_client_by_domain(session, domain)

        if not result:
            raise HTTPException(status_code=404, detail="Domain not found")

        return {
            "client_id": result["client_id"],
            "chatbot_key": result["chatbot_key"],
            "client_name": result["client_name"],
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error looking up domain: {str(e)}")


@router.post("/register-my-domains/me")
async def register_domains_route(
    domains: List[str],
    client_id: str = Depends(get_client_from_header),
    session: AsyncSession = Depends(get_session)
):
    """Register multiple domains for the authenticated client"""
    registered = []
    failed = []

    for domain in domains:
        try:
            success = await register_domain(session, domain, client_id)
            if success:
                clean = _clean_domain(domain)
                registered.append(clean)
            else:
                failed.append(domain)
        except Exception as e:
            print(f"Error registering domain {domain}: {e}")
            failed.append(domain)

    return {
        "success": len(failed) == 0,
        "registered_domains": registered,
        "failed_domains": failed
    }


@router.delete("/domains/me/{domain}")
async def delete_domain_route(
    domain: str,
    client_id: str = Depends(get_client_from_header),
    session: AsyncSession = Depends(get_session)
):
    """Delete a domain for the authenticated client"""
    try:
        success = await remove_domain(session, domain, client_id)

        if not success:
            raise HTTPException(
                status_code=404,
                detail=f"Domain '{domain}' not found or does not belong to you"
            )

        clean = _clean_domain(domain)
        return {
            "success": True,
            "message": f"Domain '{clean}' deleted successfully"
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error deleting domain: {str(e)}")
