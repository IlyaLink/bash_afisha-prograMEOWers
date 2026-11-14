"""Pydantic схемы подписок и обратной связи."""

import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


class SubscriptionCreate(BaseModel):
    """Создание подписки (без PII, только telegram_id и фильтры)."""
    telegram_id: str = Field(..., description="ID пользователя или чата в Telegram")
    city: Optional[str] = Field(None, description="Город для отслеживания событий")
    category: Optional[str] = Field(None, description="Категория для отслеживания событий")


class SubscriptionRead(BaseModel):
    id: uuid.UUID
    telegram_id: str
    city: Optional[str] = None
    category: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class FeedbackCreate(BaseModel):
    """Форма обратной связи / заявки от организаторов (ТЗ 6.3)."""
    event_id: Optional[str] = Field(None, description="ID события, если обращение по нему")
    organizer_name: str = Field(..., min_length=2, max_length=200, description="Имя или название организации")
    contact: str = Field(..., min_length=3, max_length=200, description="Контактные данные (email или телефон)")
    message: str = Field(..., min_length=5, max_length=3000, description="Текст заявки или уточнения")
    honeypot: Optional[str] = Field(None, description="Скрытое поле для защиты от спам-ботов")


class FeedbackRead(BaseModel):
    id: uuid.UUID
    event_id: Optional[str] = None
    organizer_name: str
    contact: str
    message: str
    is_reviewed: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
