import os
from typing import List
from urllib.parse import quote_plus
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

    # CORS
    ALLOWED_ORIGINS: str

    @property
    def allowed_origins_list(self) -> List[str]:
        return [o.strip() for o in self.ALLOWED_ORIGINS.split(",") if o.strip()]

    # MariaDB/MySQL Configuration
    # MARIADB_ROOT_PASSWORD: str
    MARIADB_DATABASE: str
    MARIADB_USER: str
    MARIADB_PASSWORD: str
    MARIADB_HOST: str
    MARIADB_PORT: str

    @property
    def DATABASE_URL(self) -> str:
        """MariaDB connection string for sync operations (Alembic)"""
        return (
            f"mysql+pymysql://{self.MARIADB_USER}:{quote_plus(self.MARIADB_PASSWORD)}"
            f"@{self.MARIADB_HOST}:{self.MARIADB_PORT}/{self.MARIADB_DATABASE}"
        )

    @property
    def ASYNC_DATABASE_URL(self) -> str:
        """Async MariaDB connection string for FastAPI"""
        return (
            f"mysql+aiomysql://{self.MARIADB_USER}:{quote_plus(self.MARIADB_PASSWORD)}"
            f"@{self.MARIADB_HOST}:{self.MARIADB_PORT}/{self.MARIADB_DATABASE}"
        )

    class Config:
        env_file = ".env.development"
        case_sensitive = True

settings = Settings()
