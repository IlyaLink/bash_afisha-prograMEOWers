"""ETag кеширование для REST API и справочников (ТЗ 6.3)."""

import hashlib
from typing import Callable
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response


class ETagMiddleware(BaseHTTPMiddleware):
    """Поддержка ETag и If-None-Match для GET-запросов к API и карточкам."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        if request.method != "GET":
            return await call_next(request)

        # Обрабатываем только эндпоинты API и справочники
        path = request.url.path
        if not (path.startswith("/api/v1/") or path.startswith("/widget")):
            return await call_next(request)

        response = await call_next(request)

        # ETag рассчитываем только для успешных ответов 200 OK
        if response.status_code == 200:
            body = [chunk async for chunk in response.body_iterator]
            response.body_iterator = self._reiterate(body)
            full_body = b"".join(body)

            etag = f'"{hashlib.sha256(full_body).hexdigest()}"'
            response.headers["ETag"] = etag

            # Проверяем If-None-Match от клиента
            client_etag = request.headers.get("if-none-match")
            if client_etag and client_etag.strip() == etag:
                return Response(status_code=304, headers={"ETag": etag})

        return response

    async def _reiterate(self, chunks):
        for chunk in chunks:
            yield chunk
