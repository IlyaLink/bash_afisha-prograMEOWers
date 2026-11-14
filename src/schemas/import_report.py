"""Pydantic схемы отчёта об импорте данных."""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class ImportRejectedItem(BaseModel):
    """Отклонённая запись при импорте с указанием причины."""
    row: Optional[int] = Field(None, description="Номер строки или индекс элемента")
    title: Optional[str] = Field(None, description="Название события")
    reason: str = Field(..., description="Причина отклонения")
    raw_data: Optional[Dict[str, Any]] = None


class ImportReport(BaseModel):
    """Отчёт об импорте согласно разделам 6.1 и 6.3 ТЗ."""
    total: int = Field(..., description="Всего обработано записей")
    added: int = Field(..., description="Добавлено новых событий")
    updated: int = Field(..., description="Обновлено существующих событий")
    merged: int = Field(..., description="Сведено дублей из разных источников")
    rejected_count: int = Field(..., description="Отклонено некорректных записей")
    rejected_items: List[ImportRejectedItem] = Field(default_factory=list, description="Список причин отклонений")
    duration_ms: Optional[float] = Field(None, description="Время выполнения импорта в миллисекундах")
