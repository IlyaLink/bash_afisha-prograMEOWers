"""Управление подписками пользователей Telegram (без PII, ТЗ 6.1, 6.2)."""

import uuid
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.deps import get_db_session
from src.models.subscription import Subscription
from src.schemas.common import ErrorResponse
from src.schemas.subscription import SubscriptionCreate, SubscriptionRead
from src.services.audit_service import log_audit

router = APIRouter(prefix="/subscriptions", tags=["Subscriptions"])


@router.post(
    "",
    response_model=SubscriptionRead,
    status_code=status.HTTP_201_CREATED,
    summary="Оформить подписку на город или категорию",
)
async def create_subscription(
    sub_data: SubscriptionCreate,
    db: AsyncSession = Depends(get_db_session),
):
    # Проверка на существование аналогичной подписки
    stmt = select(Subscription).where(
        Subscription.telegram_id == sub_data.telegram_id,
        Subscription.city == sub_data.city,
        Subscription.category == sub_data.category,
    )
    existing = (await db.execute(stmt)).scalars().first()
    if existing:
        return existing

    new_sub = Subscription(
        id=uuid.uuid4(),
        telegram_id=sub_data.telegram_id,
        city=sub_data.city,
        category=sub_data.category,
    )
    db.add(new_sub)
    await log_audit(
        db,
        action="create",
        entity_type="subscription",
        entity_id=str(new_sub.id),
        user="telegram_bot",
        changes={"city": sub_data.city, "category": sub_data.category},
    )
    await db.commit()
    await db.refresh(new_sub)
    return new_sub


@router.get(
    "/by-telegram/{telegram_id}",
    response_model=List[SubscriptionRead],
    summary="Список активных подписок пользователя Telegram",
)
async def get_user_subscriptions(
    telegram_id: str,
    db: AsyncSession = Depends(get_db_session),
):
    stmt = (
        select(Subscription)
        .where(Subscription.telegram_id == telegram_id)
        .order_by(Subscription.created_at.desc())
    )
    return (await db.execute(stmt)).scalars().all()


@router.delete(
    "/{sub_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Удалить подписку по её ID",
)
async def delete_subscription(
    sub_id: uuid.UUID,
    db: AsyncSession = Depends(get_db_session),
):
    stmt = select(Subscription).where(Subscription.id == sub_id)
    sub = (await db.execute(stmt)).scalars().first()
    if not sub:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": {"code": "NOT_FOUND", "message": "Подписка не найдена"}},
        )

    await db.delete(sub)
    await db.commit()
    return None


@router.delete(
    "/by-telegram/{telegram_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Отписаться от всех уведомлений одной командой (ТЗ 6.2)",
)
async def unsubscribe_all(
    telegram_id: str,
    db: AsyncSession = Depends(get_db_session),
):
    stmt = delete(Subscription).where(Subscription.telegram_id == telegram_id)
    await db.execute(stmt)
    await db.commit()
    return None
