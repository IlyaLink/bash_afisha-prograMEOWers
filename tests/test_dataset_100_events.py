"""Тесты эталонного датасета 100+ событий Башкортостана, идемпотентности и дедупликации."""

import json
from pathlib import Path
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.event import Event
from src.services.import_service import ImportService, compute_dedup_key, parse_datetime


def test_dataset_100_events_metadata_and_quality():
    """Проверка качества датасета bashkortostan_events_100.json (100+ событий, >= 95% заполненность)."""
    file_path = Path("data/bashkortostan_events_100.json")
    assert file_path.exists(), "Файл data/bashkortostan_events_100.json должен существовать"

    data = json.loads(file_path.read_text(encoding="utf-8"))
    assert len(data) >= 100, f"В датасете должно быть 100+ событий, получено: {len(data)}"

    # 1. Проверка заполненности обязательных и ключевых полей (>= 95%)
    required_fields = [
        "title",
        "category",
        "tags",
        "date_start",
        "city",
        "venue",
        "address",
        "lat",
        "lon",
        "description",
        "price_min",
        "age_limit",
        "source_url",
        "source_type",
        "status",
    ]
    for field in required_fields:
        non_empty_count = sum(1 for e in data if e.get(field) is not None and e.get(field) != "")
        completeness = non_empty_count / len(data)
        assert completeness >= 0.95, f"Заполненность поля '{field}' ниже 95%: {completeness:.1%}"

    # 2. Проверка разнообразия категорий
    categories = {e.get("category") for e in data}
    expected_categories = {"спектакль", "концерт", "выставка", "фестиваль", "экскурсия", "кино"}
    assert expected_categories.issubset(categories), f"Категории должны содержать {expected_categories}, получено: {categories}"

    # 3. Проверка разнообразия городов Башкортостана
    cities = {e.get("city") for e in data}
    expected_cities = {"Уфа", "Стерлитамак", "Салават", "Нефтекамск", "Белорецк", "Сибай"}
    assert expected_cities.issubset(cities), f"Города должны содержать ключевые центры РБ, получено: {cities}"

    # 4. Наличие отменённых событий (2-3 события)
    cancelled = [e for e in data if e.get("status") in ("отменено", "cancelled")]
    assert len(cancelled) >= 2, f"В датасете должно быть 2-3 отмененных события, найдено: {len(cancelled)}"

    # 5. Наличие бесплатных и детских событий
    free_events = [e for e in data if e.get("is_free") is True]
    assert len(free_events) >= 10, f"Должно присутствовать достаточное количество бесплатных событий, найдено: {len(free_events)}"

    kids_events = [e for e in data if e.get("age_limit") in (0, 6)]
    assert len(kids_events) >= 15, f"Должно присутствовать достаточное количество детских событий 0+/6+, найдено: {len(kids_events)}"

    # 6. Проверка дубликатов для тестирования дедупликации
    dedup_groups = {}
    for e in data:
        k = compute_dedup_key(e["city"], e["title"], parse_datetime(e["date_start"]))
        dedup_groups.setdefault(k, []).append(e)

    duplicate_pairs = [v for v in dedup_groups.values() if len(v) > 1]
    assert len(duplicate_pairs) >= 2, f"В датасете должны присутствовать дубликаты из разных источников, найдено групп: {len(duplicate_pairs)}"


@pytest.mark.asyncio
async def test_import_100_events_idempotence_and_deduplication(db_session: AsyncSession):
    """Импорт 100+ событий: сведение дубликатов, сохранение источников и строгая идемпотентность."""
    file_path = Path("data/bashkortostan_events_100.json")
    data = json.loads(file_path.read_text(encoding="utf-8"))

    service = ImportService(db_session, user="test_100_importer")
    report = await service.import_from_json(data)

    assert report.total >= 100
    assert report.rejected_count == 0
    # Проверяем, что дубликаты успешно сведены
    assert report.merged >= 2

    # Проверяем, что отмененные события имеют корректный статус в БД
    cancelled_stmt = select(Event).where(Event.status == "отменено")
    cancelled_events = (await db_session.execute(cancelled_stmt)).scalars().all()
    assert len(cancelled_events) >= 2

    # ПОВТОРНЫЙ ИМПОРТ ТОГО ЖЕ ФАЙЛА (Проверка идемпотентности)
    second_report = await service.import_from_json(data)
    assert second_report.total == report.total
    assert second_report.added == 0, f"Повторный импорт не должен создавать новых записей (added={second_report.added})"
    assert second_report.rejected_count == 0
