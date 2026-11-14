"""Конфигурация Telegram-бота."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class BotSettings(BaseSettings):
    BOT_TOKEN: str = "dummy_token"
    BACKEND_API_URL: str = "http://localhost:8000/api/v1"
    PUBLIC_BASE_URL: str = "http://localhost:8000"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )


bot_settings = BotSettings()
