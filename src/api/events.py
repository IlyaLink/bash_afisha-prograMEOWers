"""Эндпоинты каталога событий /api/v1/events."""

import uuid
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.deps import get_db_session
from src.schemas.common import ErrorResponse
from src.schemas.event import EventListResponse, EventRead
from src.services.event_service import EventService

router = APIRouter(prefix="/events", tags=["Events"])


@router.get(
    "",
    response_model=EventListResponse,
    summary="Каталог культурных событий Башкортостана",
    description="Список опубликованных событий с фильтрацией по дате, городу, категории, цене и свободным поиском.",
    responses={
        200: {"description": "Успешный список событий с пагинацией"},
        422: {"model": ErrorResponse, "description": "Ошибка валидации параметров"},
    },
)
async def list_events(
    response: Response,
    q: Optional[str] = Query(None, description="Поиск по названию или описанию"),
    city: Optional[str] = Query(None, description="Город (Уфа, Стерлитамак, Салават...)"),
    category: Optional[str] = Query(None, description="Категория (концерт, спектакль, выставка...)"),
    period: Optional[str] = Query(None, description="Период: today, tomorrow, weekend, week"),
    date_from: Optional[datetime] = Query(None, description="Дата начала с (ISO 8601)"),
    date_to: Optional[datetime] = Query(None, description="Дата начала по (ISO 8601)"),
    is_free: Optional[bool] = Query(None, description="Только бесплатные мероприятия"),
    price_max: Optional[int] = Query(None, ge=0, description="Максимальная цена билета"),
    age_limit: Optional[int] = Query(None, ge=0, le=18, description="Возрастное ограничение"),
    language: Optional[str] = Query(None, description="Язык (башкирский, русский)"),
    tag: Optional[str] = Query(None, description="Тег (дети, джаз, бесплатно)"),
    page: int = Query(1, ge=1, description="Номер страницы"),
    size: int = Query(12, ge=1, le=100, description="Количество событий на странице"),
    sort_by: str = Query("date_asc", description="Сортировка: date_asc, date_desc, price_asc, price_desc"),
    db: AsyncSession = Depends(get_db_session),
):
    service = EventService(db)
    result = await service.get_events(
        q=q,
        city=city,
        category=category,
        period=period,
        date_from=date_from,
        date_to=date_to,
        is_free=is_free,
        price_max=price_max,
        age_limit=age_limit,
        language=language,
        tag=tag,
        page=page,
        size=size,
        sort_by=sort_by,
    )
    # Кеширование каталога на 60 секунд
    response.headers["Cache-Control"] = "public, max-age=60"
    return result


@router.get(
    "/explain-empty",
    summary="Объяснение причин пустой выдачи",
    description="Анализирует заданные ограничения и подсказывает, какое из них можно ослабить (ТЗ 6.1).",
)
async def explain_empty_result(
    q: Optional[str] = Query(None),
    city: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    period: Optional[str] = Query(None),
    is_free: Optional[bool] = Query(None),
    price_max: Optional[int] = Query(None),
    db: AsyncSession = Depends(get_db_session),
):
    service = EventService(db)
    return await service.explain_empty_result(
        q=q,
        city=city,
        category=category,
        period=period,
        is_free=is_free,
        price_max=price_max,
    )


@router.get(
    "/{event_id}",
    response_model=EventRead,
    summary="Карточка события по идентификатору",
    description="Возвращает полную карточку мероприятия со списком подтверждённых источников. Отменённые события возвращаются с флагом is_cancelled=true (ТЗ 6.1).",
    responses={
        200: {"description": "Карточка мероприятия"},
        404: {"model": ErrorResponse, "description": "Мероприятие не найдено"},
    },
)
async def get_event(
    event_id: uuid.UUID,
    response: Response,
    db: AsyncSession = Depends(get_db_session),
):
    service = EventService(db)
    event = await service.get_event_by_id(event_id)
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": {
                    "code": "EVENT_NOT_FOUND",
                    "message": f"Мероприятие с ID {event_id} не найдено",
                    "details": {"id": str(event_id)},
                }
            },
        )
    # Кеширование карточки
    response.headers["Cache-Control"] = "public, max-age=120"
    return event
