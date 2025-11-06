from pydantic import BaseModel


class ChatRequest(BaseModel):
    session_id: str | None
    message: str


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
