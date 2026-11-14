"""Общие Pydantic схемы (формат ошибок, пагинация, healthcheck)."""

from typing import Any, Dict, Optional
from pydantic import BaseModel, Field


class ErrorDetail(BaseModel):
    """Детали ошибки API."""
    code: str = Field(..., description="Машиночитаемый код ошибки")
    message: str = Field(..., description="Понятное человеку описание ошибки")
    details: Optional[Any] = Field(None, description="Дополнительные сведения")


class ErrorResponse(BaseModel):
    """Единый формат ошибок согласно разделу 6.3 ТЗ."""
    error: ErrorDetail


class PaginationMeta(BaseModel):
    """Метаданные пагинации."""
    total: int = Field(..., description="Общее число элементов")
    page: int = Field(..., description="Текущая страница (начиная с 1)")
    size: int = Field(..., description="Размер страницы")
    pages: int = Field(..., description="Всего страниц")
    has_next: bool = Field(..., description="Есть ли следующая страница")
    has_prev: bool = Field(..., description="Есть ли предыдущая страница")


class HealthResponse(BaseModel):
    """Ответ проверки работоспособности сервиса."""
    status: str = Field(default="ok", json_schema_extra={"example": "ok"})
    database: str = Field(default="healthy", json_schema_extra={"example": "healthy"})
    version: str = Field(default="1.0.0", json_schema_extra={"example": "1.0.0"})
    environment: str = Field(default="production", json_schema_extra={"example": "production"})
