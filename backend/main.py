from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .routes import auth,chat,domain,daily_stats,crawl_embed_pipeline,custom_files,admin_reply,shortcuts,websockets
from .config import settings

# === FastAPI App ===
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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
