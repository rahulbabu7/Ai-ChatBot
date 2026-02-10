import re
from pydantic import BaseModel, Field, validator
from typing import Optional

class ChangePasswordRequest(BaseModel):
    current_password: str = Field(..., min_length=1)
    new_password: str = Field(..., min_length=6)

class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=5000)
    session_id: Optional[str] = Field(None, max_length=100)

    @validator('message')
    def sanitize_message(cls, v):
        # Remove null bytes and excessive whitespace
        v = v.replace('\x00', '').strip()
        # Limit consecutive newlines
        v = re.sub(r'\n{4,}', '\n\n\n', v)
        if not v:
            raise ValueError("Message cannot be empty")
        return v

    @validator('session_id')
    def validate_session_id(cls, v):
        if v is not None:
            if not re.match(r'^[a-zA-Z0-9_\-]{1,100}$', v):
                raise ValueError("Invalid session_id format")
        return v


class CrawlRequest(BaseModel):
    allowed_domain: str
    start_url: str


class SignupRequest(BaseModel):
    name: str
    username: str
    password: str
    mobile: str
    email: str


class LoginRequest(BaseModel):
    username: str
    password: str


class TaskResponse(BaseModel):
    task_id: str
    status: str
    message: str


class DailyStats(BaseModel):
    date: str
    visitors: int
    chats: int


class StatsResponse(BaseModel):
    daily_stats: list[DailyStats]

class AdminReplyRequest(BaseModel):
    message: str

class HeartbeatRequest(BaseModel):
    session_id: str
    is_chatbot_open: bool

# Additional response model for dashboard stats
class DashboardStatsResponse(BaseModel):
    total_sessions: int
    today_sessions: int
    today_visitors: int
    active_users_now: int


class ClientProfileUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    mobile_number: Optional[str] = None
    chatbot_name: Optional[str] = None

class LeadDataRequest(BaseModel):
    session_id: str = Field(..., max_length=100)
    client_id: str = Field(..., max_length=100)
    lead_data: dict
    form_type: str = Field(..., max_length=50)

    @validator('lead_data')
    def validate_lead_data(cls, v):
        if 'email' in v:
            email = v['email']
            if not isinstance(email, str) or '@' not in email:
                raise ValueError("Invalid email format")
        if 'phone' in v:
            phone = re.sub(r'[^\d+]', '', str(v['phone']))
            if len(phone) < 10 or len(phone) > 15:
                raise ValueError("Invalid phone number")
        return v

class UpdateLeadStatusRequest(BaseModel):
    status: str
    notes: Optional[str] = None
