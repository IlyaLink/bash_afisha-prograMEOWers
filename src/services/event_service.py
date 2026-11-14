"""Сервис каталога, поиска и фильтрации культурных событий."""

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.models.event import Event
from src.schemas.common import PaginationMeta
from src.schemas.event import EventListResponse, EventRead
from src.services.import_service import normalize_string


def get_period_dates(period: str) -> Tuple[Optional[datetime], Optional[datetime]]:
    """Расчёт диапазона дат для типовых фильтров (сегодня, завтра, выходные, неделя)."""
    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    today_end = now.replace(hour=23, minute=59, second=59, microsecond=999999)

    period = (period or "").strip().lower()

    if period == "today":
        return today_start, today_end
    elif period == "tomorrow":
        tomorrow_start = today_start + timedelta(days=1)
        tomorrow_end = today_end + timedelta(days=1)
        return tomorrow_start, tomorrow_end
    elif period == "weekend":
        # Суббота и воскресенье текущей недели (в Python monday = 0, sunday = 6)
        days_until_saturday = (5 - now.weekday()) % 7
        if days_until_saturday == 0 and now.weekday() == 6:
            # Если сегодня воскресенье, то выходные — это сегодня
            saturday_start = today_start - timedelta(days=1)
        else:
            saturday_start = today_start + timedelta(days=days_until_saturday)
        sunday_end = saturday_start + timedelta(days=1, hours=23, minutes=59, seconds=59)
        return saturday_start, sunday_end
    elif period == "week":
        week_end = today_end + timedelta(days=7)
        return today_start, week_end

    return None, None


class EventService:
    """Бизнес-логика каталога мероприятий."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_events(
        self,
        q: Optional[str] = None,
        city: Optional[str] = None,
        category: Optional[str] = None,
        period: Optional[str] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        is_free: Optional[bool] = None,
        price_max: Optional[int] = None,
        age_limit: Optional[int] = None,
        language: Optional[str] = None,
        tag: Optional[str] = None,
        page: int = 1,
        size: int = 12,
        sort_by: str = "date_asc",
    ) -> EventListResponse:
        """Получение списка опубликованных событий с фильтрацией и пагинацией."""
        page = max(1, page)
        size = max(1, min(100, size))

        # Базовое условие: только опубликованные мероприятия (ТЗ 6.1)
        filters = [Event.status == "опубликовано"]

        # 1. Полнотекстовый поиск по нормализованному названию или описанию
        if q:
            norm_q = normalize_string(q)
            if norm_q:
                filters.append(
                    or_(
                        Event.normalized_title.ilike(f"%{norm_q}%"),
                        Event.description.ilike(f"%{q.strip()}%"),
                        Event.venue.ilike(f"%{q.strip()}%"),
                    )
                )

        # 2. Фильтр по городу
        if city:
            filters.append(Event.city.ilike(city.strip()))

        # 3. Фильтр по категории
        if category:
            filters.append(Event.category.ilike(category.strip()))

        # 4. Фильтр по периоду или явным датам
        p_start, p_end = get_period_dates(period)
        effective_start = date_from or p_start
        effective_end = date_to or p_end

        if effective_start:
            filters.append(Event.date_start >= effective_start)
        if effective_end:
            filters.append(Event.date_start <= effective_end)

        # 5. Фильтр по бесплатности и максимальной цене
        if is_free is True:
            filters.append(Event.is_free.is_(True))
        elif price_max is not None and price_max >= 0:
            filters.append(Event.price_min <= price_max)

        # 6. Возрастное ограничение (события, доступные для возраста <= age_limit)
        if age_limit is not None and age_limit >= 0:
            filters.append(Event.age_limit <= age_limit)

        # 7. Язык мероприятия
        if language:
            filters.append(Event.language.ilike(f"%{language.strip()}%"))

        # 8. Тег (например: "дети", "джаз", "башкирский язык")
        if tag:
            # Для универсальности SQLite/Postgres поиск в JSON через строковое представление
            filters.append(func.lower(func.cast(Event.tags, Event.description.type)).ilike(f"%{tag.lower()}%"))

        # Подсчёт общего количества
        count_stmt = select(func.count(Event.id)).where(and_(*filters))
        total = (await self.db.execute(count_stmt)).scalar() or 0

        # Сортировка
        order_clause = Event.date_start.asc()
        if sort_by == "date_desc":
            order_clause = Event.date_start.desc()
        elif sort_by == "price_asc":
            order_clause = Event.price_min.asc()
        elif sort_by == "price_desc":
            order_clause = Event.price_min.desc()

        # Выборка элементов
        offset = (page - 1) * size
        stmt = (
            select(Event)
            .where(and_(*filters))
            .options(selectinload(Event.sources))
            .order_by(order_clause)
            .offset(offset)
            .limit(size)
        )
        result = await self.db.execute(stmt)
        events = result.scalars().all()

        pages = (total + size - 1) // size if total > 0 else 1
        meta = PaginationMeta(
            total=total,
            page=page,
            size=size,
            pages=pages,
            has_next=page < pages,
            has_prev=page > 1,
        )

        read_items = [
            EventRead(
                **{k: getattr(e, k) for k in e.__table__.columns.keys()},
                is_cancelled=(e.status == "отменено"),
                sources=e.sources,
            )
            for e in events
        ]

        return EventListResponse(items=read_items, meta=meta)

    async def get_event_by_id(self, event_id: uuid.UUID) -> Optional[EventRead]:
        """Получение детальной карточки события по ID.

        Согласно ТЗ 6.1: отменённое событие не попадает в выдачу каталога,
        но остаётся доступным по прямой ссылке с явной пометкой 'отменено'.
        """
        stmt = (
            select(Event)
            .where(Event.id == event_id)
            .options(selectinload(Event.sources))
        )
        result = await self.db.execute(stmt)
        event = result.scalars().first()
        if not event:
            return None

        return EventRead(
            **{k: getattr(event, k) for k in event.__table__.columns.keys()},
            is_cancelled=(event.status == "отменено"),
            sources=event.sources,
        )

    async def explain_empty_result(
        self,
        q: Optional[str] = None,
        city: Optional[str] = None,
        category: Optional[str] = None,
        period: Optional[str] = None,
        is_free: Optional[bool] = None,
        price_max: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Анализ причин пустой выдачи с рекомендациями по ослаблению ограничений (ТЗ 6.1)."""
        reasons = []
        suggestions = []

        # 1. Проверяем, есть ли вообще события в данном городе
        if city:
            city_count_stmt = (
                select(func.count(Event.id))
                .where(and_(Event.city.ilike(city), Event.status == "опубликовано"))
            )
            city_count = (await self.db.execute(city_count_stmt)).scalar() or 0
            if city_count == 0:
                reasons.append(f"В выбранном городе «{city}» сейчас нет актуальных мероприятий.")
                suggestions.append("Попробуйте выбрать столицу республики — Уфу, где проходит больше всего событий.")
            else:
                # В городе есть события, значит дело в комбинации с категорией, датой или ценой
                if category:
                    cat_city_count_stmt = (
                        select(func.count(Event.id))
                        .where(
                            and_(
                                Event.city.ilike(city),
                                Event.category.ilike(category),
                                Event.status == "опубликовано",
                            )
                        )
                    )
                    cat_city_count = (await self.db.execute(cat_city_count_stmt)).scalar() or 0
                    if cat_city_count == 0:
                        reasons.append(f"В городе «{city}» нет мероприятий в категории «{category}».")
                        suggestions.append(f"Снимите фильтр по категории «{category}» или поищите её в Уфе.")

        # 2. Проверяем фильтр по цене и бесплатности
        if is_free is True:
            reasons.append("Включён фильтр «Только бесплатные».")
            suggestions.append("Попробуйте отключить ограничение «Только бесплатные», чтобы увидеть билеты от 100-300 ₽.")

        if price_max is not None and price_max < 500:
            reasons.append(f"Установлен низкий ценовой порог: до {price_max} ₽.")
            suggestions.append("Увеличьте максимальную цену билета до 1000–1500 ₽.")

        # 3. Период
        if period:
            period_labels = {
                "today": "сегодня",
                "tomorrow": "завтра",
                "weekend": "в эти выходные",
                "week": "на этой неделе",
            }
            label = period_labels.get(period, period)
            reasons.append(f"На период «{label}» событий с выбранными критериями не запланировано.")
            suggestions.append("Выберите период «Все даты», чтобы увидеть афишу на месяц вперёд.")

        if q:
            reasons.append(f"По поисковому запросу «{q}» ничего не найдено.")
            suggestions.append("Проверьте правильность написания или используйте более общее слово (например, «театр» или «концерт»).")

        if not reasons:
            reasons.append("По заданным критериям фильтрации мероприятий не найдено.")
            suggestions.append("Попробуйте сбросить фильтры для просмотра всей культурной афиши республики.")

        return {
            "title": "Мероприятий не найдено",
            "reasons": reasons,
            "suggestions": suggestions,
        }
