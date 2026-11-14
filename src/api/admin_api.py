"""REST API администратора: импорт, модерация, аудит (ТЗ 6.1, 6.3)."""

import uuid
from typing import Any, Dict, List
from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.deps import get_current_admin, get_db_session
from src.models.audit import AuditLog
from src.models.event import Event
from src.schemas.import_report import ImportReport
from src.services.audit_service import log_audit
from src.services.import_service import ImportService

router = APIRouter(prefix="/admin", tags=["Admin API"])


class StatusUpdatePayload(BaseModel):
    status: str  # опубликовано, черновик, отменено


@router.post(
    "/import",
    response_model=ImportReport,
    summary="Идемпотентный импорт CSV или JSON с отчётом",
)
async def import_events_file(
    file: UploadFile = File(...),
    admin_user: str = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db_session),
):
    service = ImportService(db, user=admin_user)
    content = await file.read()
    filename = (file.filename or "").lower()

    if filename.endswith(".csv"):
        report = await service.import_from_csv(content)
    elif filename.endswith(".json"):
        report = await service.import_from_json(content)
    else:
        # Пытаемся распарсить как JSON, иначе как CSV
        try:
            report = await service.import_from_json(content)
        except Exception:
            report = await service.import_from_csv(content)

    return report


@router.patch(
    "/events/{event_id}/status",
    summary="Смена статуса мероприятия (модерация)",
)
async def update_event_status(
    event_id: uuid.UUID,
    payload: StatusUpdatePayload,
    admin_user: str = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db_session),
):
    new_status = payload.status.strip().lower()
    if new_status not in ("опубликовано", "черновик", "отменено"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": {"code": "INVALID_STATUS", "message": "Допустимые статусы: опубликовано, черновик, отменено"}},
        )

    stmt = select(Event).where(Event.id == event_id)
    event = (await db.execute(stmt)).scalars().first()
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": {"code": "EVENT_NOT_FOUND", "message": "Событие не найдено"}},
        )

    old_status = event.status
    event.status = new_status
    await log_audit(
        db,
        action="status_change",
        entity_type="event",
        entity_id=str(event.id),
        user=admin_user,
        changes={"old_status": old_status, "new_status": new_status},
    )
    await db.commit()
    return {"id": str(event.id), "old_status": old_status, "new_status": new_status}


@router.get(
    "/audit",
    summary="Просмотр журнала изменений (Audit Logs)",
)
async def get_audit_logs(
    limit: int = Query(50, ge=1, le=200),
    admin_user: str = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db_session),
):
    stmt = select(AuditLog).order_by(AuditLog.created_at.desc()).limit(limit)
    logs = (await db.execute(stmt)).scalars().all()
    return [
        {
            "id": str(l.id),
            "user": l.user,
            "action": l.action,
            "entity_type": l.entity_type,
            "entity_id": l.entity_id,
            "changes": l.changes,
            "created_at": l.created_at.isoformat(),
        }
        for l in logs
    ]
