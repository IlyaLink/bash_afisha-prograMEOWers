"""Сервис аудита изменений."""

import uuid
from typing import Any, Dict, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from src.models.audit import AuditLog


async def log_audit(
    db: AsyncSession,
    action: str,
    entity_type: str,
    entity_id: str,
    user: str = "system",
    changes: Optional[Dict[str, Any]] = None,
) -> AuditLog:
    """Записать событие в журнал изменений."""
    audit_entry = AuditLog(
        id=uuid.uuid4(),
        user=user,
        action=action,
        entity_type=entity_type,
        entity_id=str(entity_id),
        changes=changes or {},
    )
    db.add(audit_entry)
    await db.flush()
    return audit_entry
