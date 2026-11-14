"""Тесты идемпотентного импорта, дедупликации и отчёта (ТЗ 6.1, 6.3)."""

import json
from pathlib import Path
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.services.import_service import ImportService


@pytest.mark.asyncio
async def test_import_idempotence(db_session: AsyncSession):
    """Проверка идемпотентности: повторный импорт того же файла не создаёт дублей."""
    seed_path = Path("data/events_seed.json")
    data = json.loads(seed_path.read_text(encoding="utf-8"))

    service = ImportService(db_session, user="test_runner")
    # Так как фикстура уже загрузила этот набор, повторный импорт должен дать added=0
    report = await service.import_from_json(data)

    assert report.total == len(data)
    assert report.added == 0
    assert report.rejected_count == 0


@pytest.mark.asyncio
async def test_import_deduplication(db_session: AsyncSession):
    """Проверка дедупликации: сведение одного события из разных источников в одну карточку."""
    dup_path = Path("data/events_duplicate.json")
    dup_data = json.loads(dup_path.read_text(encoding="utf-8"))

    service = ImportService(db_session, user="test_dedup_runner")
    report = await service.import_from_json(dup_data)

    assert report.total == 1
    # Должно быть сведено с существующей карточкой «Лебединое озеро», а не создано заново!
    assert report.merged == 1
    assert report.added == 0


@pytest.mark.asyncio
async def test_import_validation_rejection(db_session: AsyncSession):
    """Проверка отклонения некорректных записей с подробным отчётом."""
    invalid_data = [
        # Нет названия
        {
            "category": "концерт",
            "city": "Уфа",
            "venue": "ГКЗ",
            "date_start": "2026-11-20T19:00:00",
        },
        # Дата окончания раньше даты начала
        {
            "title": "Некорректный спектакль",
            "category": "спектакль",
            "city": "Уфа",
            "venue": "Театр",
            "date_start": "2026-11-20T19:00:00",
            "date_end": "2026-11-20T18:00:00",
        },
    ]

    service = ImportService(db_session, user="test_validator")
    report = await service.import_from_json(invalid_data)

    assert report.total == 2
    assert report.added == 0
    assert report.rejected_count == 2
    assert len(report.rejected_items) == 2
    assert "Отсутствует обязательное поле 'title'" in report.rejected_items[0].reason
    assert "не может быть раньше начала" in report.rejected_items[1].reason
