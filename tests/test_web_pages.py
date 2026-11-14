"""Тесты для HTML-роутов веб-каталога, виджета и админ-панели."""

import base64
import pytest
import httpx


@pytest.mark.asyncio
async def test_catalog_root_page(async_client: httpx.AsyncClient):
    """GET / возвращает 200 OK и рендерит веб-каталог с обязательным дисклеймером."""
    response = await async_client.get("/")
    assert response.status_code == 200
    assert "text/html" in response.headers.get("content-type", "")
    assert "Афиша культуры Башкортостана" in response.text
    # Проверка обязательного дисклеймера (ТЗ 6.1)
    assert "Сервис является независимым информационным агрегатором" in response.text


@pytest.mark.asyncio
async def test_widget_page(async_client: httpx.AsyncClient):
    """GET /widget возвращает 200 OK и HTML-разметку виджета."""
    response = await async_client.get("/widget")
    assert response.status_code == 200
    assert "text/html" in response.headers.get("content-type", "")
    assert "Виджет" in response.text
    assert "Башкортостан" in response.text


@pytest.mark.asyncio
async def test_admin_page_unauthorized_has_www_authenticate(async_client: httpx.AsyncClient):
    """GET /admin без авторизации возвращает 401 и заголовок WWW-Authenticate: Basic."""
    response = await async_client.get("/admin")
    assert response.status_code == 401
    auth_header = response.headers.get("www-authenticate", "")
    assert "Basic" in auth_header


@pytest.mark.asyncio
async def test_admin_page_authorized_ok(async_client: httpx.AsyncClient):
    """GET /admin с корректным логином и паролем возвращает 200 OK."""
    auth_credentials = base64.b64encode(b"admin:culture_bashkortostan_2026").decode("utf-8")
    headers = {"Authorization": f"Basic {auth_credentials}"}
    response = await async_client.get("/admin", headers=headers)
    assert response.status_code == 200
    assert "text/html" in response.headers.get("content-type", "")
    assert "Админ-панель" in response.text


@pytest.mark.asyncio
async def test_event_detail_html_page(async_client: httpx.AsyncClient):
    """GET /events/{id} возвращает 200 OK и HTML-карточку мероприятия."""
    events_res = await async_client.get("/api/v1/events")
    assert events_res.status_code == 200
    items = events_res.json()["items"]
    assert len(items) > 0
    event_id = items[0]["id"]

    response = await async_client.get(f"/events/{event_id}")
    assert response.status_code == 200
    assert "text/html" in response.headers.get("content-type", "")
    assert items[0]["title"] in response.text
