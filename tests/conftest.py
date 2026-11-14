"""Конфигурация и фикстуры для тестирования (pytest)."""

import asyncio
import json
from pathlib import Path
from typing import AsyncGenerator
import pytest
import pytest_asyncio
import httpx
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.database import Base, get_db
from src.api.deps import get_db_session
from src.main import app
from src.models.reference import Category, City
from src.services.import_service import ImportService

# Тестовая база данных SQLite
TEST_DB_URL = "sqlite+aiosqlite:///./test_afisha.db"

test_engine = create_async_engine(
    TEST_DB_URL,
    connect_args={"check_same_thread": False},
)

TestAsyncSessionLocal = async_sessionmaker(
    bind=test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


@pytest_asyncio.fixture(scope="session", autouse=True)
async def prepare_database():
    """Создание таблиц и наполнение тестовыми данными на время сессии тестов."""
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Заполняем справочники и сиды
    async with TestAsyncSessionLocal() as session:
        # Города
        session.add(City(name="Уфа", normalized_name="уфа", is_active=True, sort_order=1))
        session.add(City(name="Стерлитамак", normalized_name="стерлитамак", is_active=True, sort_order=2))
        session.add(City(name="Салават", normalized_name="салават", is_active=True, sort_order=3))
        session.add(City(name="Сибай", normalized_name="сибай", is_active=True, sort_order=6))

        # Категории
        session.add(Category(name="спектакль", slug="theatre", icon="theater", sort_order=1, is_active=True))
        session.add(Category(name="концерт", slug="concert", icon="music", sort_order=2, is_active=True))
        session.add(Category(name="выставка", slug="exhibition", icon="art", sort_order=3, is_active=True))
        await session.commit()

        # Импорт сидовых событий
        seed_path = Path("data/events_seed.json")
        if seed_path.exists():
            data = json.loads(seed_path.read_text(encoding="utf-8"))
            srv = ImportService(session, user="test_fixture")
            await srv.import_from_json(data)

    yield

    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await test_engine.dispose()

    # Удаляем временный файл тестовой БД
    test_db_file = Path("test_afisha.db")
    if test_db_file.exists():
        try:
            test_db_file.unlink()
        except Exception:
            pass


@pytest_asyncio.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Фикстура сессии базы данных для тестов."""
    async with TestAsyncSessionLocal() as session:
        yield session


@pytest_asyncio.fixture
async def async_client() -> AsyncGenerator[httpx.AsyncClient, None]:
    """Асинхронный HTTP-клиент для тестирования API."""
    async def override_get_db():
        async with TestAsyncSessionLocal() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_db_session] = override_get_db

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        yield client

    app.dependency_overrides.clear()
