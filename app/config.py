from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    DATABASE_URL: str = "sqlite:///./coworking.db"
    SECRET_KEY: str = "your-secret-key-here-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440

    APP_NAME: str = "共享办公空间智能调度系统"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True

    APPROVAL_TIMEOUT_HOURS: int = 2
    ESCALATION_TIMEOUT_MINUTES: int = 30

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
