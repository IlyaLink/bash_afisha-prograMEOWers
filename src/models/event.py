"""ORM модели событий, сырых данных и источников."""

import uuid
from datetime import datetime, timezone
from typing import List, Optional
from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    JSON,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from src.database import Base


def utcnow() -> datetime:
    """Текущее время в UTC с часовым поясом."""
    return datetime.now(timezone.utc)


class Event(Base):
    """Карточка культурного события (раздел 8.1 ТЗ)."""

    __tablename__ = "events"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=uuid.uuid4, index=True
    )
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    normalized_title: Mapped[str] = mapped_column(
        String(500), nullable=False, index=True
    )
    category: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    tags: Mapped[list] = mapped_column(JSON, default=list)

    date_start: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    date_end: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    duration_min: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    city: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    venue: Mapped[str] = mapped_column(String(255), nullable=False)
    address: Mapped[str] = mapped_column(String(255), nullable=False)
    lat: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    lon: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    price_min: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    price_max: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_free: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False, index=True
    )
    age_limit: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    language: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    org_link: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    source_url: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    source_type: Mapped[str] = mapped_column(
        String(50), default="ручной ввод", nullable=False
    )
    source_hash: Mapped[str] = mapped_column(
        String(64), nullable=False, index=True
    )
    verified_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    confidence: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    status: Mapped[str] = mapped_column(
        String(20), default="опубликовано", nullable=False, index=True
    )
    dedup_key: Mapped[str] = mapped_column(
        String(128), nullable=False, index=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False
    )

    # Отношение к источникам (при дедупликации сведение дублей в единую карточку)
    sources: Mapped[List["EventSource"]] = relationship(
        "EventSource", back_populates="event", cascade="all, delete-orphan", lazy="selectin"
    )

    __table_args__ = (
        Index("ix_events_city_category_date", "city", "category", "date_start"),
        Index("ix_events_status_date", "status", "date_start"),
    )


class EventSource(Base):
    """Подтверждённые источники мероприятия (дедупликация ТЗ 6.3)."""

    __tablename__ = "event_sources"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=uuid.uuid4
    )
    event_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("events.id", ondelete="CASCADE"), nullable=False, index=True
    )
    source_url: Mapped[str] = mapped_column(String(1000), nullable=False)
    source_type: Mapped[str] = mapped_column(String(50), nullable=False)
    source_title: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    source_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )

    event: Mapped["Event"] = relationship("Event", back_populates="sources")


class RawEvent(Base):
    """Сырые данные источника (ТЗ 6.1: хранение отдельно от нормализованных)."""

    __tablename__ = "raw_events"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=uuid.uuid4
    )
    source_type: Mapped[str] = mapped_column(String(50), nullable=False)
    source_url: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    source_hash: Mapped[str] = mapped_column(
        String(64), nullable=False, index=True
    )
    raw_payload: Mapped[dict] = mapped_column(JSON, nullable=False)
    import_status: Mapped[str] = mapped_column(
        String(50), default="processed", nullable=False
    )
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )
