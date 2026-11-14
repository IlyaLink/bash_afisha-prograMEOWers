"""Тесты эндпоинтов каталога событий и ETag кеширования (ТЗ 6.3)."""

import pytest
import httpx


@pytest.mark.asyncio
async def test_list_events_default(async_client: httpx.AsyncClient):
    """Проверка базового получения каталога published событий."""
    resp = await async_client.get("/api/v1/events")
    assert resp.status_code == 200

    data = resp.json()
    assert "items" in data
    assert "meta" in data
    assert len(data["items"]) > 0

    # Проверка ETag и Cache-Control
    assert "etag" in resp.headers
    assert "cache-control" in resp.headers


@pytest.mark.asyncio
async def test_filter_events_by_city(async_client: httpx.AsyncClient):
    """Проверка фильтрации по городу Уфа."""
    resp = await async_client.get("/api/v1/events", params={"city": "Уфа"})
    assert resp.status_code == 200

    data = resp.json()
    for item in data["items"]:
        assert item["city"].lower() == "уфа"


@pytest.mark.asyncio
async def test_filter_events_by_category(async_client: httpx.AsyncClient):
    """Проверка фильтрации по категории."""
    resp = await async_client.get("/api/v1/events", params={"category": "спектакль"})
    assert resp.status_code == 200

    data = resp.json()
    for item in data["items"]:
        assert item["category"].lower() == "спектакль"


@pytest.mark.asyncio
async def test_filter_free_events(async_client: httpx.AsyncClient):
    """Проверка фильтрации только бесплатных событий."""
    resp = await async_client.get("/api/v1/events", params={"is_free": True})
    assert resp.status_code == 200

    data = resp.json()
    assert len(data["items"]) > 0
    for item in data["items"]:
        assert item["is_free"] is True
        assert item["price_min"] == 0


@pytest.mark.asyncio
async def test_etag_304_caching(async_client: httpx.AsyncClient):
    """Проверка кеширования через ETag и возврат 304 Not Modified."""
    resp1 = await async_client.get("/api/v1/events")
    assert resp1.status_code == 200
    etag = resp1.headers.get("etag")
    assert etag is not None

    # Повторный запрос с заголовком If-None-Match
    resp2 = await async_client.get("/api/v1/events", headers={"If-None-Match": etag})
    assert resp2.status_code == 304
    assert resp2.text == ""


@pytest.mark.asyncio
async def test_event_detail_with_sources(async_client: httpx.AsyncClient):
    """Проверка получения детальной карточки и списка её источников."""
    resp = await async_client.get("/api/v1/events")
    items = resp.json()["items"]
    event_id = items[0]["id"]

    detail_resp = await async_client.get(f"/api/v1/events/{event_id}")
    assert detail_resp.status_code == 200
    detail = detail_resp.json()

    assert detail["id"] == event_id
    assert "sources" in detail
    assert isinstance(detail["sources"], list)
    assert len(detail["sources"]) >= 1
