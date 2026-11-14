"""Тесты отменённых событий (ТЗ 6.1: скрытие из каталога, плашка по прямой ссылке)."""

import pytest
import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from src.models.event import Event


@pytest.mark.asyncio
async def test_cancelled_event_hidden_from_catalog(
    async_client: httpx.AsyncClient, db_session: AsyncSession
):
    """Отменённое событие отсутствует в общей выдаче каталога мероприятий."""
    # Находим ID отменённого события из сидов («Карагул»)
    stmt = select(Event).where(Event.status == "отменено")
    cancelled = (await db_session.execute(stmt)).scalars().first()
    assert cancelled is not None, "В сидах должно быть хотя бы одно отменённое событие"

    # Запрашиваем каталог
    resp = await async_client.get("/api/v1/events", params={"size": 100})
    assert resp.status_code == 200
    items = resp.json()["items"]

    event_ids = [it["id"] for it in items]
    assert str(cancelled.id) not in event_ids, "Отменённое событие НЕ должно попадать в каталог"


@pytest.mark.asyncio
async def test_cancelled_event_accessible_by_direct_link(
    async_client: httpx.AsyncClient, db_session: AsyncSession
):
    """По прямой ссылке отменённое событие доступно со статусом 'отменено' и флагом is_cancelled."""
    stmt = select(Event).where(Event.status == "отменено")
    cancelled = (await db_session.execute(stmt)).scalars().first()
    assert cancelled is not None

    resp = await async_client.get(f"/api/v1/events/{cancelled.id}")
    assert resp.status_code == 200
    data = resp.json()

    assert data["id"] == str(cancelled.id)
    assert data["status"] == "отменено"
    assert data["is_cancelled"] is True
