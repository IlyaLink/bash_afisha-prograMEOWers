"""Pydantic схемы событий культурной афиши."""

import uuid
from datetime import datetime
from typing import Any, List, Optional
from pydantic import BaseModel, ConfigDict, Field
from src.schemas.common import PaginationMeta


class EventSourceRead(BaseModel):
    """Сведения об источнике карточки (дедупликация ТЗ 6.3)."""
    id: uuid.UUID
    source_url: str = Field(..., description="URL источника")
    source_type: str = Field(..., description="Тип источника (ручной ввод, импорт, RSS, API)")
    source_title: Optional[str] = Field(None, description="Название у источника")
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class EventBase(BaseModel):
    """Базовые поля карточки события согласно разделу 8.1 ТЗ."""
    title: str = Field(..., min_length=1, max_length=500, description="Название как у источника")
    category: str = Field(..., description="Категория: концерт, спектакль, выставка, фестиваль, кино, экскурсия, другое")
    tags: List[str] = Field(default_factory=list, description="Метки: джаз, дети, бесплатно, башкирский язык")
    date_start: datetime = Field(..., description="Дата и время начала")
    date_end: Optional[datetime] = Field(None, description="Дата и время окончания")
    duration_min: Optional[int] = Field(None, description="Длительность в минутах")
    city: str = Field(..., description="Город или населённый пункт")
    venue: str = Field(..., description="Площадка или учреждение культуры")
    address: str = Field(..., description="Адрес проведения")
    lat: Optional[float] = Field(None, description="Широта")
    lon: Optional[float] = Field(None, description="Долгота")
    description: str = Field(default="", description="Краткое описание мероприятия")
    price_min: int = Field(default=0, ge=0, description="Минимальная цена (0 — бесплатно)")
    price_max: int = Field(default=0, ge=0, description="Максимальная цена")
    is_free: bool = Field(default=False, description="Признак бесплатного входа")
    age_limit: int = Field(default=0, ge=0, le=18, description="Возрастное ограничение: 0, 6, 12, 16, 18")
    language: Optional[str] = Field(None, description="Язык мероприятия (башкирский, русский)")
    org_link: Optional[str] = Field(None, description="Ссылка на организатора или билеты")
    source_url: Optional[str] = Field(None, description="Источник, откуда взято событие")
    source_type: str = Field(default="ручной ввод", description="Тип источника: ручной ввод, импорт, RSS, API")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0, description="Оценка уверенности извлечения")
    status: str = Field(default="опубликовано", description="Статус: опубликовано, черновик, отменено")


class EventCreate(EventBase):
    """Схема создания события."""
    pass


class EventUpdate(BaseModel):
    """Схема частичного обновления события."""
    title: Optional[str] = None
    category: Optional[str] = None
    tags: Optional[List[str]] = None
    date_start: Optional[datetime] = None
    date_end: Optional[datetime] = None
    duration_min: Optional[int] = None
    city: Optional[str] = None
    venue: Optional[str] = None
    address: Optional[str] = None
    lat: Optional[float] = None
    lon: Optional[float] = None
    description: Optional[str] = None
    price_min: Optional[int] = None
    price_max: Optional[int] = None
    is_free: Optional[bool] = None
    age_limit: Optional[int] = None
    language: Optional[str] = None
    org_link: Optional[str] = None
    source_url: Optional[str] = None
    status: Optional[str] = None


class EventRead(EventBase):
    """Схема чтения полной карточки события."""
    id: uuid.UUID
    normalized_title: str
    source_hash: str
    verified_at: Optional[datetime] = None
    dedup_key: str
    created_at: datetime
    updated_at: datetime
    is_cancelled: bool = Field(default=False, description="Флаг: отменено ли событие")
    sources: List[EventSourceRead] = Field(default_factory=list, description="Список подтверждённых источников")

    model_config = ConfigDict(from_attributes=True)


class EventListResponse(BaseModel):
    """Список событий с метаданными пагинации."""
    items: List[EventRead]
    meta: PaginationMeta
