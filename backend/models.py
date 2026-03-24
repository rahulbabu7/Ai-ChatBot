from __future__ import annotations

from datetime import datetime, timezone, timedelta
from typing import Optional, List
import uuid

from sqlmodel import SQLModel, Field, select
from sqlalchemy.orm import relationship  # Use SQLAlchemy's relationship
from sqlalchemy.sql import func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import Column, String, Integer, Text, DateTime, Index, Float, ForeignKey, JSON


def utc_now() -> datetime:
    """Helper function to get current UTC datetime (timezone-aware)"""
    return datetime.now(timezone.utc)


def ist_now() -> datetime:
    """Helper function to get current IST datetime (timezone-aware)"""
    ist = timezone(timedelta(hours=5, minutes=30))
    return datetime.now(ist)


def utc_to_ist(utc_dt: datetime) -> datetime:
    """Convert UTC datetime to IST"""
    if utc_dt is None:
        return None

    # If datetime is naive, assume it's UTC
    if utc_dt.tzinfo is None:
        utc_dt = utc_dt.replace(tzinfo=timezone.utc)

    # Convert to IST
    ist = timezone(timedelta(hours=5, minutes=30))
    return utc_dt.astimezone(ist)


# -----------------------------------------------------------------------------
# Models
# -----------------------------------------------------------------------------
class User(SQLModel, table=True):
    __tablename__ = "users"
    id: Optional[int] = Field(default=None, primary_key=True)
    username: str = Field(sa_column=Column(String(100), unique=True, nullable=False, index=True))
    password: str = Field(sa_column=Column(String(255), nullable=False))
    name: Optional[str] = Field(default=None, sa_column=Column(String(100)))
    email: Optional[str] = Field(default=None, sa_column=Column(String(100)))
    mobile: Optional[str] = Field(default=None, sa_column=Column(String(20)))
    role: str = Field(default="client", sa_column=Column(String(20), nullable=False))
    client_id: str = Field(sa_column=Column(String(100), unique=True, nullable=False, index=True))
    chatbot_key: Optional[str] = Field(default=None, sa_column=Column(String(100), unique=True))
    chatbot_enabled: bool = Field(default=True, sa_column=Column(Integer, nullable=False, server_default="1"))
    plan: str = Field(default="trial", sa_column=Column(String(20), nullable=False, server_default="trial"))
    plan_expires_at: Optional[datetime] = Field(default=None, sa_column=Column(DateTime, nullable=True))


class ChatbotName(SQLModel, table=True):
    __tablename__ = "chatbot_name"
    id: Optional[int] = Field(default=None, primary_key=True)
    client_id: str = Field(
        sa_column=Column(
            String(100),
            ForeignKey("users.client_id", ondelete="CASCADE"),
            nullable=False,
            index=True
        )
    )
    chatbot_name: str = Field(
        default="AI Assistant",
        sa_column=Column(String(100), nullable=False)
    )




class Chat(SQLModel, table=True):
    __tablename__ = "chats"
    __table_args__ = (
        Index("idx_chats_client_session", "client_id", "session_id"),
        Index("idx_chats_is_active", "is_active"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    client_id: str = Field(sa_column=Column(String(100), nullable=False, index=True))
    session_id: str = Field(sa_column=Column(String(100), nullable=False, index=True))
    role: str = Field(sa_column=Column(String(20), nullable=False))
    message: str = Field(sa_column=Column(Text, nullable=False))
    user_agent: Optional[str] = Field(default=None, sa_column=Column(String(255)))
    created_at: datetime = Field(
        default_factory=utc_now,
        sa_column=Column(DateTime, nullable=False, server_default=func.utc_timestamp()),
    )
    country_code: str = Field(default="unknown", sa_column=Column(String(10), nullable=False))
    admin_override: int = Field(default=0, sa_column=Column(Integer, nullable=False, server_default="0"))
    is_active: int = Field(default=1, sa_column=Column(Integer, nullable=False, server_default="1"))
    response_time: Optional[float] = Field(
        default=None,
        sa_column=Column(Float, nullable=True)
    )

    def to_dict_ist(self) -> dict:
        """Return dict with IST timestamps"""
        return {
            "id": self.id,
            "client_id": self.client_id,
            "session_id": self.session_id,
            "role": self.role,
            "message": self.message,
            "user_agent": self.user_agent,
            "created_at": utc_to_ist(self.created_at).isoformat() if self.created_at else None,
            "country_code": self.country_code,
            "admin_override": self.admin_override,
            "is_active": self.is_active,
            "response_time": self.response_time,
        }


class DomainMapping(SQLModel, table=True):
    __tablename__ = "domain_mappings"
    __table_args__ = (
        Index("idx_domain_mappings_domain", "domain"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    domain: str = Field(sa_column=Column(String(255), unique=True, nullable=False, index=True))
    client_id: str = Field(sa_column=Column(String(100), nullable=False))
    chatbot_key: str = Field(sa_column=Column(String(100), nullable=False))
    created_at: datetime = Field(
        default_factory=utc_now,
        sa_column=Column(DateTime, nullable=False, server_default=func.now()),
    )


class Task(SQLModel, table=True):
    __tablename__ = "tasks"
    __table_args__ = (
        Index("idx_tasks_client", "client_id"),
    )

    id: str = Field(sa_column=Column(String(100), primary_key=True))
    client_id: str = Field(sa_column=Column(String(100), nullable=False, index=True))
    name: Optional[str] = Field(default=None, sa_column=Column(String(100)))
    status: Optional[str] = Field(default=None, sa_column=Column(String(20)))
    info: Optional[str] = Field(default=None, sa_column=Column(Text))
    created_at: datetime = Field(
        default_factory=utc_now,
        sa_column=Column(DateTime, nullable=False, server_default=func.now()),
    )
    updated_at: datetime = Field(
        default_factory=utc_now,
        sa_column=Column(
            DateTime,
            nullable=False,
            server_default=func.now(),
            onupdate=func.now(),
        ),
    )


class Shortcut(SQLModel, table=True):
    __tablename__ = "shortcut"
    """Shortcuts for quick admin responses"""
    id: Optional[int] = Field(default=None, primary_key=True)
    client_id: str = Field(index=True)
    action_type: str
    command: str
    message: str
    created_at: datetime = Field(
        default_factory=utc_now,
        sa_column=Column(DateTime, nullable=False, server_default=func.now()),
    )
    updated_at: datetime = Field(
        default_factory=utc_now,
        sa_column=Column(DateTime, nullable=False, server_default=func.now()),
    )
    is_active: int = Field(default=1)



class Lead(SQLModel, table=True):
    """Store collected lead data from chatbot forms"""
    __tablename__ = "leads"
    __table_args__ = (
        Index("idx_leads_client", "client_id"),
        Index("idx_leads_session", "session_id"),
        Index("idx_leads_email", "email"),
        Index("idx_leads_created", "created_at"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    client_id: str = Field(sa_column=Column(String(100), nullable=False, index=True))
    session_id: str = Field(sa_column=Column(String(100), nullable=False, index=True))

    # Contact information
    name: Optional[str] = Field(default=None, sa_column=Column(String(255)))
    email: Optional[str] = Field(default=None, sa_column=Column(String(255), index=True))
    phone: Optional[str] = Field(default=None, sa_column=Column(String(50)))
    company: Optional[str] = Field(default=None, sa_column=Column(String(255)))
    message: Optional[str] = Field(default=None, sa_column=Column(Text))

    # Form metadata
    form_type: str = Field(sa_column=Column(String(50), nullable=False))  # 'contact', 'demo_booking', etc.
    preferred_time: Optional[str] = Field(default=None, sa_column=Column(String(50)))  # For demo bookings

    # Additional data (store any extra fields as JSON)
    extra_data: Optional[dict] = Field(default=None, sa_column=Column(JSON, nullable=True))

    # Tracking
    country_code: Optional[str] = Field(default="unknown", sa_column=Column(String(10)))
    user_agent: Optional[str] = Field(default=None, sa_column=Column(String(255)))

    # Status tracking
    status: str = Field(default="new", sa_column=Column(String(50), nullable=False))  # 'new', 'contacted', 'converted', 'closed'
    contacted_at: Optional[datetime] = Field(default=None, sa_column=Column(DateTime, nullable=True))
    notes: Optional[str] = Field(default=None, sa_column=Column(Text))

    # Timestamps
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime, nullable=False, server_default=func.utc_timestamp()),
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(
            DateTime,
            nullable=False,
            server_default=func.now(),
            onupdate=func.now(),
        ),
    )

    def to_dict_ist(self) -> dict:
        """Return dict with IST timestamps"""
        from backend.models import utc_to_ist

        return {
            "id": self.id,
            "client_id": self.client_id,
            "session_id": self.session_id,
            "name": self.name,
            "email": self.email,
            "phone": self.phone,
            "company": self.company,
            "message": self.message,
            "form_type": self.form_type,
            "preferred_time": self.preferred_time,
            "extra_data": self.extra_data,
            "status": self.status,
            "contacted_at": utc_to_ist(self.contacted_at).isoformat() if self.contacted_at else None,
            "notes": self.notes,
            "country_code": self.country_code,
            "user_agent": self.user_agent,
            "created_at": utc_to_ist(self.created_at).isoformat() if self.created_at else None,
            "updated_at": utc_to_ist(self.updated_at).isoformat() if self.updated_at else None,
        }



# -----------------------------------------------------------------------------
# Helper Functions (Async)
# -----------------------------------------------------------------------------
def _clean_domain(domain: str) -> str:
    """Clean and normalize domain string"""
    return (
        domain.lower()
        .replace("https://", "")
        .replace("http://", "")
        .replace("www.", "")
        .rstrip("/")
        .strip()
    )


async def register_domain(session: AsyncSession, domain: str, client_id: str) -> bool:
    """
    Register (or upsert) a domain for a client.
    - If the user has no chatbot_key, one is generated & saved.
    - INSERT OR REPLACE semantics for domain -> (client_id, chatbot_key).
    """
    clean = _clean_domain(domain)
    try:
        # Find user by client_id
        statement = select(User).where(User.client_id == client_id)
        result = await session.execute(statement)
        user = result.scalar_one_or_none()

        if not user:
            print(f"❌ User not found for client_id: {client_id}")
            return False

        # Ensure chatbot_key exists
        if not user.chatbot_key:
            user.chatbot_key = str(uuid.uuid4())
            session.add(user)
            print(f"✅ Generated new chatbot_key for client: {client_id}")

        # Upsert domain mapping by unique 'domain'
        statement = select(DomainMapping).where(DomainMapping.domain == clean)
        result = await session.execute(statement)
        existing = result.scalar_one_or_none()

        if existing:
            existing.client_id = client_id
            existing.chatbot_key = user.chatbot_key
            session.add(existing)
        else:
            session.add(
                DomainMapping(
                    domain=clean,
                    client_id=client_id,
                    chatbot_key=user.chatbot_key,
                )
            )

        await session.commit()
        print(f"✅ Domain registered successfully: {clean}")
        return True
    except Exception as e:
        await session.rollback()
        print(f"❌ Error registering domain: {e}")
        return False


async def remove_domain(session: AsyncSession, domain: str, client_id: str) -> bool:
    """
    Remove a domain mapping for a client.
    Returns True if a row was deleted, False otherwise.
    """
    clean = _clean_domain(domain)
    try:
        statement = select(DomainMapping).where(
            (DomainMapping.domain == clean)
            & (DomainMapping.client_id == client_id)
        )
        result = await session.execute(statement)
        dm = result.scalar_one_or_none()

        if not dm:
            return False

        await session.delete(dm)
        await session.commit()
        return True
    except Exception as e:
        await session.rollback()
        print(f"❌ Error removing domain: {e}")
        return False


async def get_client_by_domain(session: AsyncSession, domain: str) -> Optional[dict]:
    """
    Get client information by domain:
    - client_id
    - chatbot_key
    - client_name (users.name)
    """
    clean = _clean_domain(domain)
    try:
        statement = (
            select(DomainMapping, User.name)
            .join(User, DomainMapping.client_id == User.client_id)
            .where(DomainMapping.domain == clean)
        )
        result = await session.execute(statement)
        row = result.first()

        if not row:
            print(f"No result found for domain: {clean}")
            return None

        domain_mapping, client_name = row
        return {
            "client_id": domain_mapping.client_id,
            "chatbot_key": domain_mapping.chatbot_key,
            "client_name": client_name,
        }
    except Exception as e:
        print(f"Error looking up domain: {e}")
        return None


# ----------------------------
# TASK HELPERS (Async)
# ----------------------------
async def add_task(
    session: AsyncSession,
    task_id: str,
    client_id: str,
    name: str,
    status: str = "queued",
    info: Optional[str] = None
) -> bool:
    """Add a new task"""
    try:
        session.add(
            Task(
                id=task_id,
                client_id=client_id,
                name=name,
                status=status,
                info=info,
            )
        )
        await session.commit()
        return True
    except Exception as e:
        await session.rollback()
        print(f"Error adding task: {e}")
        return False


async def update_task(
    session: AsyncSession,
    task_id: str,
    status: str,
    info: Optional[str] = None
) -> bool:
    """Update task status and info"""
    try:
        task = await session.get(Task, task_id)
        if not task:
            return False

        task.status = status
        task.info = info
        task.updated_at = utc_now()
        session.add(task)
        await session.commit()
        return True
    except Exception as e:
        await session.rollback()
        print(f"Error updating task: {e}")
        return False


async def get_tasks_for_client(session: AsyncSession, client_id: str) -> List[dict]:
    """Get all tasks for a client"""
    try:
        statement = (
            select(Task)
            .where(Task.client_id == client_id)
            .order_by(Task.created_at.desc())
        )
        result = await session.execute(statement)
        rows = result.scalars().all()

        return [
            {
                "id": r.id,
                "name": r.name,
                "status": r.status,
                "info": r.info,
                "created_at": utc_to_ist(r.created_at).isoformat() if r.created_at else None,
                "updated_at": utc_to_ist(r.updated_at).isoformat() if r.updated_at else None,
            }
            for r in rows
        ]
    except Exception as e:
        print(f"Error getting tasks: {e}")
        return []



# ----------------------------
# CHATBOT NAME HELPERS (Async)
# ----------------------------
async def get_chatbot_name(session: AsyncSession, client_id: str) -> Optional[str]:
    """Get chatbot name for a client"""
    try:
        statement = select(ChatbotName).where(ChatbotName.client_id == client_id)
        result = await session.execute(statement)
        chatbot = result.scalar_one_or_none()
        return chatbot.chatbot_name if chatbot else "AI Assistant"
    except Exception as e:
        print(f"Error getting chatbot name: {e}")
        return "AI Assistant"


async def set_chatbot_name(session: AsyncSession, client_id: str, chatbot_name: str) -> bool:
    """Set or update chatbot name for a client"""
    try:
        statement = select(ChatbotName).where(ChatbotName.client_id == client_id)
        result = await session.execute(statement)
        existing = result.scalar_one_or_none()

        if existing:
            existing.chatbot_name = chatbot_name
            session.add(existing)
        else:
            session.add(
                ChatbotName(
                    client_id=client_id,
                    chatbot_name=chatbot_name,
                )
            )

        await session.commit()
        return True
    except Exception as e:
        await session.rollback()
        print(f"Error setting chatbot name: {e}")
        return False



# -----------------------------------------------------------------------------
# Lead Helper Functions (Add these after the Lead model)
# -----------------------------------------------------------------------------

async def save_lead_to_db(
    session,
    client_id: str,
    session_id: str,
    lead_data: dict,
    form_type: str,
    country_code: str = "unknown",
    user_agent: str = None
) -> Optional[Lead]:
    """
    Save lead data to database

    Args:
        session: AsyncSession
        client_id: Client identifier
        session_id: Chat session identifier
        lead_data: Dictionary containing form data
        form_type: Type of form (contact, demo_booking, etc.)
        country_code: User's country code
        user_agent: User's browser user agent

    Returns:
        Lead object if successful, None otherwise
    """
    try:
        # Extract known fields
        name = lead_data.get('name')
        email = lead_data.get('email')
        phone = lead_data.get('phone')
        company = lead_data.get('company')
        message = lead_data.get('message')
        preferred_time = lead_data.get('preferred_time')

        # Store any extra fields in extra_data
        known_fields = {'name', 'email', 'phone', 'company', 'message', 'preferred_time'}
        extra_data = {k: v for k, v in lead_data.items() if k not in known_fields}

        lead = Lead(
            client_id=client_id,
            session_id=session_id,
            name=name,
            email=email,
            phone=phone,
            company=company,
            message=message,
            form_type=form_type,
            preferred_time=preferred_time,
            extra_data=extra_data if extra_data else None,
            country_code=country_code,
            user_agent=user_agent,
            status="new"
        )

        session.add(lead)
        await session.commit()
        await session.refresh(lead)

        print(f"✅ Lead saved successfully: {lead.id} - {lead.email}")
        return lead

    except Exception as e:
        await session.rollback()
        print(f"❌ Error saving lead: {e}")
        import traceback
        traceback.print_exc()
        return None


async def get_leads_for_client(
    session,
    client_id: str,
    status: Optional[str] = None,
    limit: int = 100
) -> list[dict]:
    """
    Get leads for a client

    Args:
        session: AsyncSession
        client_id: Client identifier
        status: Filter by status (optional)
        limit: Maximum number of leads to return

    Returns:
        List of lead dictionaries with IST timestamps
    """
    from sqlmodel import select

    try:
        statement = select(Lead).where(Lead.client_id == client_id)

        if status:
            statement = statement.where(Lead.status == status)

        statement = statement.order_by(Lead.created_at.desc()).limit(limit)

        result = await session.execute(statement)
        leads = result.scalars().all()

        return [lead.to_dict_ist() for lead in leads]

    except Exception as e:
        print(f"❌ Error getting leads: {e}")
        return []


async def update_lead_status(
    session,
    lead_id: int,
    status: str,
    notes: Optional[str] = None
) -> bool:
    """
    Update lead status

    Args:
        session: AsyncSession
        lead_id: Lead ID
        status: New status (new, contacted, converted, closed)
        notes: Optional notes

    Returns:
        True if successful, False otherwise
    """
    try:
        lead = await session.get(Lead, lead_id)
        if not lead:
            return False

        lead.status = status
        if notes:
            lead.notes = notes

        if status == "contacted" and not lead.contacted_at:
            lead.contacted_at = datetime.now(timezone.utc)

        session.add(lead)
        await session.commit()

        return True

    except Exception as e:
        await session.rollback()
        print(f"❌ Error updating lead status: {e}")
        return False
