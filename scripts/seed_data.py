"""Скрипт начального наполнения базы данных (сид справочников и 30+ событий)."""

import asyncio
import os
import sys
import uuid
from pathlib import Path

# Добавляем корень проекта
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import select
from src.database import AsyncSessionLocal, engine, init_db
from src.models.reference import Category, City, Venue
from src.services.import_service import ImportService


CITIES_DATA = [
    {"name": "Уфа", "normalized_name": "уфа", "sort_order": 1},
    {"name": "Стерлитамак", "normalized_name": "стерлитамак", "sort_order": 2},
    {"name": "Салават", "normalized_name": "салават", "sort_order": 3},
    {"name": "Нефтекамск", "normalized_name": "нефтекамск", "sort_order": 4},
    {"name": "Октябрьский", "normalized_name": "октябрьский", "sort_order": 5},
    {"name": "Сибай", "normalized_name": "сибай", "sort_order": 6},
    {"name": "Белорецк", "normalized_name": "белорецк", "sort_order": 7},
    {"name": "Туймазы", "normalized_name": "туймазы", "sort_order": 8},
    {"name": "Ишимбай", "normalized_name": "ишимбай", "sort_order": 9},
    {"name": "Кумертау", "normalized_name": "кумертау", "sort_order": 10},
]

CATEGORIES_DATA = [
    {"name": "спектакль", "slug": "theatre", "icon": "masks-theater", "sort_order": 1},
    {"name": "концерт", "slug": "concert", "icon": "music", "sort_order": 2},
    {"name": "выставка", "slug": "exhibition", "icon": "palette", "sort_order": 3},
    {"name": "фестиваль", "slug": "festival", "icon": "champagne-glasses", "sort_order": 4},
    {"name": "экскурсия", "slug": "tour", "icon": "landmark", "sort_order": 5},
    {"name": "кино", "slug": "cinema", "icon": "film", "sort_order": 6},
    {"name": "другое", "slug": "other", "icon": "ticket", "sort_order": 7},
]


async def seed():
    print("Инициализация таблиц базы данных...")
    await init_db()

    async with AsyncSessionLocal() as db:
        print("Наполнение справочников городов и категорий...")
        for c in CITIES_DATA:
            stmt = select(City).where(City.name == c["name"])
            existing = (await db.execute(stmt)).scalars().first()
            if not existing:
                db.add(
                    City(
                        id=uuid.uuid4(),
                        name=c["name"],
                        normalized_name=c["normalized_name"],
                        sort_order=c["sort_order"],
                        is_active=True,
                    )
                )

        for cat in CATEGORIES_DATA:
            stmt = select(Category).where(Category.name == cat["name"])
            existing = (await db.execute(stmt)).scalars().first()
            if not existing:
                db.add(
                    Category(
                        id=uuid.uuid4(),
                        name=cat["name"],
                        slug=cat["slug"],
                        icon=cat["icon"],
                        sort_order=cat["sort_order"],
                        is_active=True,
                    )
                )

        await db.commit()

        # Импорт тестовых событий
        seed_file = Path("data/events_seed.json")
        if seed_file.exists():
            print(f"Импорт 30+ событий из {seed_file}...")
            content = seed_file.read_bytes()
            import_service = ImportService(db, user="system_seed")
            report = await import_service.import_from_json(content)
            print(f"Отчет об импорте: добавлено={report.added}, обновлено={report.updated}, сведено={report.merged}, отклонено={report.rejected_count} ({report.duration_ms} мс)")

    await engine.dispose()
    print("Сидирование успешно завершено!")


if __name__ == "__main__":
    asyncio.run(seed())
