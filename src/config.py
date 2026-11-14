"""Конфигурация приложения на основе pydantic-settings."""

from functools import lru_cache
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Параметры сервиса из переменных окружения."""

    PROJECT_NAME: str = "Афиша культуры Башкортостана"
    ENVIRONMENT: str = "production"
    DEBUG: bool = False
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    PUBLIC_BASE_URL: str = "http://localhost:8000"

    # База данных: по умолчанию SQLite aiosqlite для тестов и локального запуска,
    # в Docker переопределяется на postgresql+asyncpg://...
    DATABASE_URL: str = "sqlite+aiosqlite:///./afisha.db"
    DATABASE_URL_SYNC: Optional[str] = "sqlite:///./afisha.db"

    # Basic Auth для административной панели
    ADMIN_USERNAME: str = "admin"
    ADMIN_PASSWORD: str = "culture_bashkortostan_2026"

    # Лимиты безопасности
    RATE_LIMIT_PER_MINUTE: int = 60
    FEEDBACK_RATE_LIMIT_PER_MINUTE: int = 3
    SUBSCRIPTION_RETENTION_DAYS: int = 180

    # Telegram бот
    BOT_TOKEN: str = "dummy_token"
    BACKEND_API_URL: str = "http://web:8000/api/v1"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )


@lru_cache()
def get_settings() -> Settings:
    """Кешированный экземпляр конфигурации."""
    return Settings()
