"""Структурное логирование без персональных данных и сквозной Request-ID."""

import json
import logging
import time
import uuid
from typing import Callable
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger("afisha.access")
logging.basicConfig(level=logging.INFO)


class RequestIDAndLoggingMiddleware(BaseHTTPMiddleware):
    """Генерация X-Request-ID и структурный лог каждого запроса без PII."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Получаем или генерируем сквозной request_id
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        request.state.request_id = request_id

        start_time = time.time()
        status_code = 500

        try:
            response = await call_next(request)
            status_code = response.status_code
            response.headers["X-Request-ID"] = request_id
            return response
        finally:
            duration_ms = round((time.time() - start_time) * 1000, 2)

            # Структурный JSON лог без персональных данных (IP обезличен, тело и токены не пишутся)
            client_ip = request.client.host if request.client else "unknown"
            # Маскируем последний октет IP для защиты приватности
            if "." in client_ip:
                parts = client_ip.split(".")
                masked_ip = f"{parts[0]}.{parts[1]}.{parts[2]}.xxx"
            else:
                masked_ip = "masked_ip"

            log_record = {
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "query": request.url.query,
                "status_code": status_code,
                "duration_ms": duration_ms,
                "client_ip": masked_ip,
                "user_agent": request.headers.get("user-agent", "unknown")[:100],
            }
            logger.info(json.dumps(log_record, ensure_ascii=False))
