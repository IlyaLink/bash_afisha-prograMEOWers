"""Маршруты веб-интерфейса: каталог, карточка события, виджет, админка."""

import uuid
from typing import Optional
from fastapi import APIRouter, Depends, Form, HTTPException, Request, Response, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.deps import get_current_admin, get_db_session
from src.models.audit import AuditLog
from src.models.event import Event
from src.models.reference import Category, City
from src.services.event_service import EventService
from src.services.import_service import ImportService

templates = Jinja2Templates(directory="src/templates")
web_router = APIRouter(include_in_schema=False)


@web_router.get("/", response_class=HTMLResponse)
async def catalog_page(
    request: Request,
    q: Optional[str] = None,
    city: Optional[str] = None,
    category: Optional[str] = None,
    period: Optional[str] = None,
    is_free: Optional[bool] = None,
    price_max: Optional[int] = None,
    age_limit: Optional[int] = None,
    language: Optional[str] = None,
    page: int = 1,
    db: AsyncSession = Depends(get_db_session),
):
    """Главная страница и каталог мероприятий с поддержкой HTMX."""
    service = EventService(db)
    events_resp = await service.get_events(
        q=q,
        city=city,
        category=category,
        period=period,
        is_free=is_free,
        price_max=price_max,
        age_limit=age_limit,
        language=language,
        page=page,
        size=12,
    )

    empty_explanation = None
    if events_resp.meta.total == 0:
        empty_explanation = await service.explain_empty_result(
            q=q, city=city, category=category, period=period, is_free=is_free, price_max=price_max
        )

    # Справочники для фильтров
    cities = (await db.execute(select(City).where(City.is_active.is_(True)).order_by(City.sort_order.asc()))).scalars().all()
    categories = (await db.execute(select(Category).where(Category.is_active.is_(True)).order_by(Category.sort_order.asc()))).scalars().all()

    context = {
        "request": request,
        "events": events_resp.items,
        "meta": events_resp.meta,
        "cities": cities,
        "categories": categories,
        "empty_explanation": empty_explanation,
        "selected_city": city,
        "selected_category": category,
        "selected_period": period,
        "selected_free": is_free,
        "selected_price": price_max,
        "selected_age": age_limit,
        "selected_language": language,
        "search_query": q,
    }

    # Если запрос пришёл от HTMX — отдаём только фрагмент списка событий
    if request.headers.get("HX-Request"):
        return templates.TemplateResponse(request, "partials/event_list.html", context)

    return templates.TemplateResponse(request, "index.html", context)


@web_router.get("/events/{event_id}", response_class=HTMLResponse)
async def event_detail_page(
    request: Request,
    event_id: uuid.UUID,
    db: AsyncSession = Depends(get_db_session),
):
    """Карточка события с постоянным URL (ТЗ 6.3)."""
    service = EventService(db)
    event = await service.get_event_by_id(event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Мероприятие не найдено")

    return templates.TemplateResponse(
        request,
        "event_detail.html",
        {"event": event},
    )


@web_router.get("/widget", response_class=HTMLResponse)
async def widget_embed_page(
    request: Request,
    city: Optional[str] = None,
    category: Optional[str] = None,
    period: Optional[str] = None,
    theme: str = "light",
    db: AsyncSession = Depends(get_db_session),
):
    """Встраиваемый виджет для официального сайта министерства (iframe, ТЗ 6.3)."""
    service = EventService(db)
    events_resp = await service.get_events(
        city=city,
        category=category,
        period=period,
        page=1,
        size=6,
    )
    return templates.TemplateResponse(
        request,
        "widget.html",
        {
            "events": events_resp.items,
            "city": city,
            "category": category,
            "period": period,
            "theme": theme,
        },
    )


@web_router.get("/feedback", response_class=HTMLResponse)
async def feedback_page(request: Request):
    """Страница подачи обращения организатора."""
    return templates.TemplateResponse(request, "feedback.html", {})


# --- Административная панель ---

@web_router.get("/admin", response_class=HTMLResponse)
async def admin_dashboard(
    request: Request,
    admin_user: str = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db_session),
):
    """Главная страница админ-панели."""
    events = (
        (await db.execute(select(Event).order_by(Event.created_at.desc()).limit(100)))
        .scalars()
        .all()
    )
    logs = (
        (await db.execute(select(AuditLog).order_by(AuditLog.created_at.desc()).limit(50)))
        .scalars()
        .all()
    )
    return templates.TemplateResponse(
        request,
        "admin/dashboard.html",
        {
            "admin_user": admin_user,
            "events": events,
            "logs": logs,
            "report": None,
        },
    )
