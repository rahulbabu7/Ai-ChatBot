import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # API Keys
    GROQ_API_KEY: str
    GROQ_MODEL: str
    # Redis
    REDIS_URL: str
    # Security
    SECRET_KEY: str
    ALGORITHM: str
    # Database (SQLite)
    DB_NAME: str = "app.db"
    DB_PATH: str = "./backend"
    
    @property
    def DATABASE_URL(self) -> str:
        """SQLite connection string for sync operations (Alembic)"""
        db_file = os.path.join(self.DB_PATH, self.DB_NAME)
        return f"sqlite:///{db_file}"
    
    @property
    def ASYNC_DATABASE_URL(self) -> str:
        """Async SQLite connection string for FastAPI"""
        db_file = os.path.join(self.DB_PATH, self.DB_NAME)
        return f"sqlite+aiosqlite:///{db_file}"
    
    @property
    def DATABASE_FILE(self) -> str:
        """Full path to the SQLite database file"""
        return os.path.join(self.DB_PATH, self.DB_NAME)
    
    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()