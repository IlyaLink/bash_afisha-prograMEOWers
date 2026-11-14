"""Настройка подключения к базе данных SQLAlchemy 2.0 (Async)."""

from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase
from src.config import get_settings

settings = get_settings()

# Параметры подключения в зависимости от типа СУБД
engine_kwargs = {}
if settings.DATABASE_URL.startswith("sqlite"):
    engine_kwargs["connect_args"] = {"check_same_thread": False}
else:
    engine_kwargs["pool_pre_ping"] = True
    engine_kwargs["pool_size"] = 10
    engine_kwargs["max_overflow"] = 20

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    **engine_kwargs
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


class Base(DeclarativeBase):
    """Базовый класс для всех ORM моделей."""
    pass


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI зависимость для получения сессии базы данных."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


async def init_db() -> None:
    """Создание таблиц, если они еще не существуют (для dev/тестов)."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
