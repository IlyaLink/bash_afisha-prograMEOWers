"""Зависимости для эндпоинтов API (сессия БД, аутентификация)."""

import secrets
from typing import AsyncGenerator
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from src.config import get_settings
from src.database import get_db

settings = get_settings()
security = HTTPBasic()


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Получение сессии БД."""
    async for session in get_db():
        yield session


def get_current_admin(credentials: HTTPBasicCredentials = Depends(security)) -> str:
    """Проверка учетных данных администратора через HTTP Basic Auth."""
    correct_username = secrets.compare_digest(credentials.username, settings.ADMIN_USERNAME)
    correct_password = secrets.compare_digest(credentials.password, settings.ADMIN_PASSWORD)

    if not (correct_username and correct_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный логин или пароль администратора",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials.username
