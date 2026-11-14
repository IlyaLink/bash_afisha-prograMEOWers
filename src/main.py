"""Главный модуль приложения FastAPI 'Афиша культуры Башкортостана'."""

import time
from contextlib import asynccontextmanager
from typing import Dict
from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text
from starlette.exceptions import HTTPException as StarletteHTTPException

from src.api.router import api_v1_router
from src.config import get_settings
from src.database import engine, init_db
from src.middleware.etag import ETagMiddleware
from src.middleware.logging import RequestIDAndLoggingMiddleware
from src.middleware.rate_limit import RateLimitMiddleware
from src.schemas.common import ErrorResponse, HealthResponse
from src.web.router import web_router

settings = get_settings()

# Метрики сервиса (ТЗ 6.3: запросы, ошибки, задержка)
METRICS_DATA = {
    "total_requests": 0,
    "error_requests": 0,
    "start_time": time.time(),
}


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Инициализация ресурсов при старте и освобождение при выключении."""
    # Инициализация таблиц БД при необходимости (SQLite fallback)
    if settings.DATABASE_URL.startswith("sqlite"):
        await init_db()
    yield
    await engine.dispose()


app = FastAPI(
    title=settings.PROJECT_NAME,
    version="1.0.0",
    description="Информационный сервис 'Афиша культуры Башкортостана' (Уровень 2: Веб-каталог, REST API, Виджет, Админка, Telegram-бот). Строгое соответствие ТЗ.",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# Подключение промежуточного ПО
app.add_middleware(RateLimitMiddleware)
app.add_middleware(ETagMiddleware)
app.add_middleware(RequestIDAndLoggingMiddleware)

# Подключение статических файлов (favicon, css)
try:
    app.mount("/static", StaticFiles(directory="src/static"), name="static")
except Exception:
    pass


# Middleware для подсчёта базовых метрик
@app.middleware("http")
async def metrics_middleware(request: Request, call_next):
    METRICS_DATA["total_requests"] += 1
    response = await call_next(request)
    if response.status_code >= 400:
        METRICS_DATA["error_requests"] += 1
    return response


# --- Единый формат ошибок (ТЗ 6.3) ---

@app.exception_handler(StarletteHTTPException)
async def custom_http_exception_handler(request: Request, exc: StarletteHTTPException):
    headers = dict(exc.headers) if exc.headers else {}
    if exc.status_code == status.HTTP_401_UNAUTHORIZED and "WWW-Authenticate" not in headers:
        headers["WWW-Authenticate"] = "Basic"

    # Если это веб-страница (HTML), возвращаем понятный HTML с сохранением заголовков (включая WWW-Authenticate)
    if "text/html" in request.headers.get("accept", "") and not request.url.path.startswith("/api/"):
        return HTMLResponse(
            status_code=exc.status_code,
            content=f"<h1>{exc.status_code} Unauthorized</h1><p>{exc.detail}</p>" if exc.status_code == 401 else f"<h1>Ошибка {exc.status_code}</h1><p>{exc.detail}</p>",
            headers=headers,
        )

    # Для API возвращаем строго контрактный ErrorResponse
    detail = exc.detail
    if isinstance(detail, dict) and "error" in detail:
        content = detail
    else:
        content = {
            "error": {
                "code": f"HTTP_{exc.status_code}",
                "message": str(detail),
                "details": None,
            }
        }
    return JSONResponse(status_code=exc.status_code, content=content, headers=headers)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "Ошибка валидации входных параметров запроса",
                "details": exc.errors(),
            }
        },
    )


# --- Наблюдаемость: /health и базовые метрики (ТЗ 6.3) ---

@app.get(
    "/health",
    response_model=HealthResponse,
    tags=["Observability"],
    summary="Проверка работоспособности сервиса и соединения с БД",
)
async def health_check():
    """Проверка доступности базы данных и сервиса."""
    db_status = "healthy"
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
    except Exception as e:
        db_status = f"unhealthy: {str(e)}"

    return HealthResponse(
        status="ok" if "unhealthy" not in db_status else "degraded",
        database=db_status,
        version="1.0.0",
        environment=settings.ENVIRONMENT,
    )


@app.get(
    "/metrics",
    tags=["Observability"],
    summary="Базовые метрики сервиса (запросы, ошибки, задержка)",
)
async def get_metrics():
    """Отдача счетчиков запросов, ошибок и времени непрерывной работы."""
    uptime_seconds = round(time.time() - METRICS_DATA["start_time"], 1)
    total = METRICS_DATA["total_requests"]
    errors = METRICS_DATA["error_requests"]
    error_rate = round((errors / total) * 100, 2) if total > 0 else 0.0

    return {
        "uptime_seconds": uptime_seconds,
        "total_requests": total,
        "error_requests": errors,
        "error_rate_percent": error_rate,
    }


# Подключение роутеров API и Веб-интерфейса
app.include_router(api_v1_router)
app.include_router(web_router)
