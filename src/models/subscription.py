"""ORM модель подписок пользователей на города и категории (без PII)."""

import uuid
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import DateTime, Index, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column
from src.database import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Subscription(Base):
    """Подписка пользователя в Telegram на обновления афиши.

    Соответствует требованиям ТЗ: персональные данные не собираются
    (нет телефонов, имён, email). Только telegram_id и критерии отбора.
    """

    __tablename__ = "subscriptions"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    telegram_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    city: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    category: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )

    __table_args__ = (
        Index("ix_subs_tg_city_cat", "telegram_id", "city", "category", unique=True),
    )
