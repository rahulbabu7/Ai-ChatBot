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

    # MariaDB/MySQL Configuration
    MARIADB_ROOT_PASSWORD: str
    MARIADB_DATABASE: str
    MARIADB_USER: str
    MARIADB_PASSWORD: str
    MARIADB_HOST: str = "localhost"  # Default to localhost, override in .env for Docker
    MARIADB_PORT: int = 3306

    @property
    def DATABASE_URL(self) -> str:
        """MariaDB connection string for sync operations (Alembic)"""
        return (
            f"mysql+pymysql://{self.MARIADB_USER}:{self.MARIADB_PASSWORD}"
            f"@{self.MARIADB_HOST}:{self.MARIADB_PORT}/{self.MARIADB_DATABASE}"
        )

    @property
    def ASYNC_DATABASE_URL(self) -> str:
        """Async MariaDB connection string for FastAPI"""
        return (
            f"mysql+aiomysql://{self.MARIADB_USER}:{self.MARIADB_PASSWORD}"
            f"@{self.MARIADB_HOST}:{self.MARIADB_PORT}/{self.MARIADB_DATABASE}"
        )

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
