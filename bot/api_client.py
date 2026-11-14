"""HTTP-клиент для взаимодействия Telegram-бота с REST API (ТЗ 6.2)."""

import logging
import os
from typing import Any, Dict, List, Optional
import httpx
from bot.config import bot_settings

logger = logging.getLogger("afisha.bot.api_client")


class BackendAPIClient:
    """Асинхронный клиент к REST API 'Афиша культуры Башкортостана'."""

    def __init__(self, base_url: Optional[str] = None):
        self._base_url = base_url

    @property
    def base_url(self) -> str:
        """Динамическое определение базового URL с нормализацией суффикса /api/v1."""
        url = (
            self._base_url
            or os.getenv("BACKEND_API_URL")
            or bot_settings.BACKEND_API_URL
            or "http://web:8000/api/v1"
        )
        url = url.rstrip("/")
        if not url.endswith("/api/v1"):
            url = f"{url}/api/v1"
        return url

    @base_url.setter
    def base_url(self, value: Optional[str]):
        if value:
            val = value.rstrip("/")
            if not val.endswith("/api/v1"):
                val = f"{val}/api/v1"
            self._base_url = val
        else:
            self._base_url = None

    async def get_events(
        self,
        q: Optional[str] = None,
        city: Optional[str] = None,
        category: Optional[str] = None,
        period: Optional[str] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        is_free: Optional[bool] = None,
        price_max: Optional[int] = None,
        page: int = 1,
        size: int = 5,
    ) -> Dict[str, Any]:
        """Получение списка событий из REST API."""
        params: Dict[str, Any] = {"page": page, "size": size}
        if q:
            params["q"] = q
        if city:
            params["city"] = city
        if category:
            params["category"] = category
        if period:
            params["period"] = period
        if date_from:
            params["date_from"] = date_from
        if date_to:
            params["date_to"] = date_to
        if is_free is not None:
            params["is_free"] = is_free
        if price_max is not None:
            params["price_max"] = price_max

        target_url = f"{self.base_url}/events"
        logger.info("HTTP запрос к бэкенду: GET %s params=%s", target_url, params)
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(target_url, params=params)
                resp.raise_for_status()
                return resp.json()
        except Exception as e:
            logger.error("Ошибка при запросе к REST API (%s): %s", target_url, e, exc_info=True)
            raise

    async def explain_empty(
        self,
        q: Optional[str] = None,
        city: Optional[str] = None,
        category: Optional[str] = None,
        period: Optional[str] = None,
        is_free: Optional[bool] = None,
        price_max: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Получение рекомендаций при пустой выдаче."""
        params: Dict[str, Any] = {}
        if q:
            params["q"] = q
        if city:
            params["city"] = city
        if category:
            params["category"] = category
        if period:
            params["period"] = period
        if is_free is not None:
            params["is_free"] = is_free
        if price_max is not None:
            params["price_max"] = price_max

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(f"{self.base_url}/events/explain-empty", params=params)
                if resp.status_code == 200:
                    return resp.json()
        except Exception as e:
            logger.warning("Не удалось получить пояснения к пустой выдаче: %s", e)
        return {}

    async def get_event_by_id(self, event_id: str) -> Optional[Dict[str, Any]]:
        """Получение карточки события."""
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(f"{self.base_url}/events/{event_id}")
            if resp.status_code == 404:
                return None
            resp.raise_for_status()
            return resp.json()

    async def get_cities(self) -> List[Dict[str, Any]]:
        """Получение справочника городов."""
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(f"{self.base_url}/cities")
            resp.raise_for_status()
            return resp.json()

    async def get_categories(self) -> List[Dict[str, Any]]:
        """Получение справочника категорий."""
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(f"{self.base_url}/categories")
            resp.raise_for_status()
            return resp.json()

    async def create_subscription(
        self, telegram_id: str, city: Optional[str] = None, category: Optional[str] = None
    ) -> Dict[str, Any]:
        """Оформление подписки."""
        payload = {"telegram_id": str(telegram_id), "city": city, "category": category}
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(f"{self.base_url}/subscriptions", json=payload)
            resp.raise_for_status()
            return resp.json()

    async def get_user_subscriptions(self, telegram_id: str) -> List[Dict[str, Any]]:
        """Получение списка подписок пользователя."""
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(f"{self.base_url}/subscriptions/by-telegram/{telegram_id}")
            resp.raise_for_status()
            return resp.json()

    async def delete_subscription(self, sub_id: str) -> bool:
        """Удаление подписки по ID."""
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.delete(f"{self.base_url}/subscriptions/{sub_id}")
            return resp.status_code == 204

    async def unsubscribe_all(self, telegram_id: str) -> bool:
        """Отписка от всех уведомлений."""
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.delete(f"{self.base_url}/subscriptions/by-telegram/{telegram_id}")
            return resp.status_code == 204


api_client = BackendAPIClient()
