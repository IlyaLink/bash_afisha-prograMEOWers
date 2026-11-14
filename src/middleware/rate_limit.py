"""Защита от спама и ограничение частоты запросов (Rate Limiting)."""

import time
from collections import defaultdict
from typing import Callable, Dict, List
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from src.config import get_settings

settings = get_settings()


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Ограничение частоты запросов по IP адресу."""

    def __init__(self, app):
        super().__init__(app)
        self.requests_log: Dict[str, List[float]] = defaultdict(list)
        self.feedback_log: Dict[str, List[float]] = defaultdict(list)

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        client_ip = request.client.host if request.client else "unknown"
        now = time.time()

        # 1. Специфический лимит для формы обратной связи /api/v1/feedback
        if request.url.path.endswith("/feedback") and request.method == "POST":
            history = self.feedback_log[client_ip]
            # Удаляем запросы старше 60 секунд
            self.feedback_log[client_ip] = [t for t in history if now - t < 60]
            if len(self.feedback_log[client_ip]) >= settings.FEEDBACK_RATE_LIMIT_PER_MINUTE:
                return JSONResponse(
                    status_code=429,
                    content={
                        "error": {
                            "code": "RATE_LIMIT_EXCEEDED",
                            "message": "Слишком много сообщений. Пожалуйста, подождите одну минуту.",
                            "details": {"retry_after_seconds": 60},
                        }
                    },
                )
            self.feedback_log[client_ip].append(now)

        # 2. Общий лимит для API
        if request.url.path.startswith("/api/"):
            history = self.requests_log[client_ip]
            self.requests_log[client_ip] = [t for t in history if now - t < 60]
            if len(self.requests_log[client_ip]) >= settings.RATE_LIMIT_PER_MINUTE:
                return JSONResponse(
                    status_code=429,
                    content={
                        "error": {
                            "code": "TOO_MANY_REQUESTS",
                            "message": "Превышен лимит запросов к API. Попробуйте позже.",
                            "details": {"limit": settings.RATE_LIMIT_PER_MINUTE},
                        }
                    },
                )
            self.requests_log[client_ip].append(now)

        return await call_next(request)
