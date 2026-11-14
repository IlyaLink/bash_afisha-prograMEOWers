"""Тесты наблюдаемости (/health, /metrics, request_id) и защиты от спама (ТЗ 6.3)."""

import pytest
import httpx
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from src.models.audit import Feedback


@pytest.mark.asyncio
async def test_health_endpoint(async_client: httpx.AsyncClient):
    """Проверка /health возвращает 200 и статус здоровой БД."""
    resp = await async_client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert "healthy" in data["database"]
    assert "version" in data


@pytest.mark.asyncio
async def test_metrics_endpoint(async_client: httpx.AsyncClient):
    """Проверка сбора базовых метрик (/metrics)."""
    resp = await async_client.get("/metrics")
    assert resp.status_code == 200
    data = resp.json()
    assert "uptime_seconds" in data
    assert "total_requests" in data
    assert data["total_requests"] > 0


@pytest.mark.asyncio
async def test_request_id_in_response_headers(async_client: httpx.AsyncClient):
    """Проверка наличия заголовка X-Request-ID для сквозной трассировки."""
    resp = await async_client.get("/health")
    assert "x-request-id" in resp.headers
    req_id = resp.headers["x-request-id"]
    assert len(req_id) >= 10


@pytest.mark.asyncio
async def test_feedback_honeypot_spam_defense(
    async_client: httpx.AsyncClient, db_session: AsyncSession
):
    """Проверка защиты формы обратной связи от спама через honeypot."""
    count_before = (await db_session.execute(select(func.count(Feedback.id)))).scalar() or 0

    # Бот заполняет скрытое поле honeypot
    spam_payload = {
        "organizer_name": "Spam Bot 3000",
        "contact": "spam@seo-promo.com",
        "message": "Buy cheap watches online now!",
        "honeypot": "I am a robot",
    }
    resp = await async_client.post("/api/v1/feedback", json=spam_payload)
    # Отдаем статус 201 чтобы бот не заподозрил, но в базу запись НЕ пишем
    assert resp.status_code == 201

    count_after = (await db_session.execute(select(func.count(Feedback.id)))).scalar() or 0
    assert count_after == count_before, "Спам из honeypot не должен сохраняться в базе данных"
