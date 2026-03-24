from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import bcrypt
import uuid
from backend.database import get_session  # Your async session dependency
from backend.models import User  # Your SQLModel User model
from backend.schemas import SignupRequest, LoginRequest, ChangePasswordRequest  # Your Pydantic schemas
from backend.auth_utils import create_jwt, get_client_from_header  # Your JWT functions
import re
router = APIRouter(
    prefix='/auth',
    tags=['auth']
)

@router.post("/signup")
async def signup(req: SignupRequest, session: AsyncSession = Depends(get_session)):
    client_id = f"{req.username}_{uuid.uuid4().hex[:6]}"
    hashed_password = bcrypt.hashpw(req.password.encode(), bcrypt.gensalt()).decode()

    try:
        # Check if username already exists
        stmt = select(User).where(User.username == req.username)
        result = await session.execute(stmt)
        existing_user = result.scalar_one_or_none()

        if existing_user:
            raise HTTPException(status_code=400, detail="Username already exists")

        # Create new user
        new_user = User(
            username=req.username,
            password=hashed_password,
            name=req.name,
            email=req.email,
            mobile=req.mobile,
            client_id=client_id
        )

        session.add(new_user)
        await session.commit()
        await session.refresh(new_user)

    except HTTPException:
        raise
    except Exception as e:
        await session.rollback()
        raise HTTPException(status_code=400, detail=f"Signup failed: {str(e)}")

    token = create_jwt(client_id)
    return {
        "success": True,
        "token": token,
        "client_id": client_id,
        "message": "Signup successful"
    }

@router.post("/login")
async def login(req: LoginRequest, session: AsyncSession = Depends(get_session)):
    # Query user by username
    stmt = select(User).where(User.username == req.username)
    result = await session.execute(stmt)
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=401, detail="Invalid username or password")

    # Verify password
    stored_password = user.password
    if isinstance(stored_password, bytes):
        stored_password = stored_password.decode()

    if not bcrypt.checkpw(req.password.encode(), stored_password.encode()):
        raise HTTPException(status_code=401, detail="Invalid username or password")

    token = create_jwt(user.client_id)
    return {
        "success": True,
        "token": token,
        "client_id": user.client_id,
        "role": user.role,
        "message": "Login successful"
    }

@router.get("/me")
async def get_me(
    client_id: str = Depends(get_client_from_header),
    session: AsyncSession = Depends(get_session)
):
    # Query user by client_id
    stmt = select(User).where(User.client_id == client_id)
    result = await session.execute(stmt)
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="Client not found")

    return {
        "client_id": user.client_id,
        "name": user.name,
        "username": user.username,
        "email": user.email
    }

@router.post("/change-password")
async def change_password(
    req: ChangePasswordRequest,
    client_id: str = Depends(get_client_from_header),
    session: AsyncSession = Depends(get_session)
):
    # Validate new password strength
    if len(req.new_password) < 6:
        raise HTTPException(
            status_code=400,
            detail="Password must be at least 6 characters long"
        )

    # Check password complexity
    password_regex = r'^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]'
    if not re.match(password_regex, req.new_password):
        raise HTTPException(
            status_code=400,
            detail="Password must contain at least one uppercase letter, one lowercase letter, one number, and one special character"
        )

    # Check if new password is same as current
    if req.current_password == req.new_password:
        raise HTTPException(
            status_code=400,
            detail="New password must be different from current password"
        )

    # Get user from database
    stmt = select(User).where(User.client_id == client_id)
    result = await session.execute(stmt)
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Verify current password
    stored_password = user.password
    if isinstance(stored_password, bytes):
        stored_password = stored_password.decode()

    if not bcrypt.checkpw(req.current_password.encode(), stored_password.encode()):
        raise HTTPException(status_code=401, detail="Current password is incorrect")

    # Hash new password and update
    try:
        new_hashed_password = bcrypt.hashpw(req.new_password.encode(), bcrypt.gensalt()).decode()
        user.password = new_hashed_password

        await session.commit()
        await session.refresh(user)

        return {
            "success": True,
            "message": "Password changed successfully"
        }
    except Exception as e:
        await session.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to change password: {str(e)}"
        )
