"""Форма обратной связи от организаторов с защитой от спама (ТЗ 6.3)."""

import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.deps import get_db_session
from src.models.audit import Feedback
from src.schemas.subscription import FeedbackCreate, FeedbackRead
from src.services.audit_service import log_audit

router = APIRouter(prefix="/feedback", tags=["Feedback"])


@router.post(
    "",
    response_model=FeedbackRead,
    status_code=status.HTTP_201_CREATED,
    summary="Отправить заявку или уточнение организатора",
)
async def submit_feedback(
    payload: FeedbackCreate,
    request: Request,
    db: AsyncSession = Depends(get_db_session),
):
    # Защита от спам-ботов через Honeypot (ТЗ 6.3)
    if payload.honeypot:
        # Спам-бот заполнил скрытое поле. Возвращаем фейковый успех без сохранения.
        return FeedbackRead(
            id=uuid.uuid4(),
            event_id=payload.event_id,
            organizer_name=payload.organizer_name,
            contact=payload.contact,
            message=payload.message,
            is_reviewed=False,
            created_at=datetime.now(timezone.utc),
        )

    client_ip = request.client.host if request.client else None
    feedback = Feedback(
        id=uuid.uuid4(),
        event_id=payload.event_id,
        organizer_name=payload.organizer_name,
        contact=payload.contact,
        message=payload.message,
        ip_address=client_ip,
        is_reviewed=False,
    )
    db.add(feedback)
    await log_audit(
        db,
        action="create",
        entity_type="feedback",
        entity_id=str(feedback.id),
        user="organizer",
        changes={"organizer": payload.organizer_name},
    )
    await db.commit()
    await db.refresh(feedback)
    return feedback
