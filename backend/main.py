from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from .routes import auth,chat,domain,daily_stats,crawl_embed_pipeline,custom_files,admin_reply,shortcuts,websockets,userProfile,public_chatbot,leads
from .config import settings

# === FastAPI App ===
app = FastAPI()

# === Rate Limiting ===
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_credentials=True,
    allow_methods=["POST", "GET", "PUT", "PATCH", "DELETE"],
    allow_headers=["Content-Type", "x-chatbot-key", "Authorization"],
)


app.include_router(auth.router)
app.include_router(chat.router)
app.include_router(domain.router)
app.include_router(daily_stats.router)
app.include_router(crawl_embed_pipeline.router)
app.include_router(custom_files.router)
app.include_router(admin_reply.router)
app.include_router(shortcuts.router)
app.include_router(websockets.router)
app.include_router(userProfile.router)
app.include_router(public_chatbot.router)
app.include_router(leads.router)
