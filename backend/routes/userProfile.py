from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from backend.schemas import ClientProfileUpdate
from backend.database import get_session
from backend.auth_utils import get_client_from_header
from backend.models import User,get_chatbot_name, set_chatbot_name

router = APIRouter(
    prefix="/client/profile",
    tags=["userProfile"]
)
@router.get("")
async def get_client(
    client_id: str = Depends(get_client_from_header),
    session: AsyncSession = Depends(get_session)
):
    """Get current client information"""
    try:
        # Get user
        user_statement = select(User).where(User.client_id == client_id)
        user_result = await session.execute(user_statement)
        user = user_result.scalar_one_or_none()

        if not user:
            raise HTTPException(status_code=404, detail="Client not found")

        # Get chatbot name using helper function
        chatbot_name = await get_chatbot_name(session, client_id)

        return {
            "name": user.name,
            "username": user.username,
            "email": user.email,
            "mobile_number": user.mobile,
            "chatbot_name": chatbot_name
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error fetching client information: {str(e)}"
        )


@router.patch("/edit")
async def edit_client_profile(
    payload: ClientProfileUpdate,
    client_id: str = Depends(get_client_from_header),
    session: AsyncSession = Depends(get_session),
):
    try:
        statement = select(User).where(User.client_id == client_id)
        result = await session.execute(statement)
        user = result.scalar_one_or_none()

        if not user:
            raise HTTPException(status_code=404, detail="Client not found")

        if payload.name is not None:
            user.name = payload.name

        if payload.email is not None:
            user.email = payload.email

        if payload.mobile_number is not None:
            user.mobile = payload.mobile_number

        session.add(user)

        if payload.chatbot_name is not None:
            await set_chatbot_name(
                session=session,
                client_id=client_id,
                chatbot_name=payload.chatbot_name,
            )

        await session.commit()

        return {
            "message": "Profile updated successfully",
            "updated_fields": payload.dict(exclude_none=True),
        }

    except HTTPException:
        raise
    except Exception as e:
        await session.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Error updating client profile: {str(e)}",
        )
