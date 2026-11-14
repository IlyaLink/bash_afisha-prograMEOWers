"""Сервис идемпотентного импорта данных и дедупликации (разделы 6.1, 6.3, 8.1 ТЗ)."""

import csv
import hashlib
import io
import json
import re
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple, Union

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.event import Event, EventSource, RawEvent
from src.models.reference import City, Category, Venue
from src.schemas.import_report import ImportReport, ImportRejectedItem
from src.services.audit_service import log_audit


def normalize_string(text: Optional[str]) -> str:
    """Нормализация строки для сопоставления и дедупликации."""
    if not text:
        return ""
    # Приведение к нижнему регистру и замена ё на е
    s = text.lower().replace("ё", "е")
    # Удаление уточнений в скобках (авторы, премьеры, пояснения)
    s = re.sub(r"[\(\[\{].*?[\)\]\}]", " ", s)
    # Удаление кавычек всех видов («, », ", ')
    s = re.sub(r'["\'«»„“”`]', "", s)
    # Замена дефисов и подчеркиваний на пробелы
    s = re.sub(r"[-_–—]", " ", s)
    # Удаление лишних спецсимволов и знаков препинания
    s = re.sub(r"[^\w\s]", "", s)
    # Схлопывание повторяющихся пробелов
    s = re.sub(r"\s+", " ", s).strip()
    return s


def compute_source_hash(payload: Dict[str, Any]) -> str:
    """Вычисление хеша исходной записи для строгой идемпотентности."""
    source_type = str(payload.get("source_type", "")).strip().lower()
    source_url = str(payload.get("source_url", "")).strip().lower()
    title = str(payload.get("title", "")).strip()
    date_start = str(payload.get("date_start", "")).strip()
    city = str(payload.get("city", "")).strip().lower()

    raw_key = f"{source_type}|{source_url}|{city}|{title}|{date_start}"
    return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()


def compute_dedup_key(city: str, title: str, date_start: datetime) -> str:
    """Вычисление ключа дедупликации: город + нормализованное название + дата начала (до часа)."""
    norm_city = normalize_string(city)
    norm_title = normalize_string(title)
    norm_date = date_start.strftime("%Y-%m-%d %H")
    raw_key = f"{norm_city}:{norm_title}:{norm_date}"
    return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()


def parse_datetime(val: Any) -> Optional[datetime]:
    """Универсальный парсинг даты и времени."""
    if not val:
        return None
    if isinstance(val, datetime):
        if val.tzinfo is None:
            return val.replace(tzinfo=timezone.utc)
        return val

    s = str(val).strip()
    formats = [
        "%Y-%m-%dT%H:%M:%S%z",
        "%Y-%m-%dT%H:%M:%SZ",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %H:%M",
        "%Y-%m-%d",
        "%d.%m.%Y %H:%M:%S",
        "%d.%m.%Y %H:%M",
        "%d.%m.%Y",
    ]
    for fmt in formats:
        try:
            dt = datetime.strptime(s, fmt)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt
        except ValueError:
            continue
    return None


class ImportService:
    """Сервис импорта и дедупликации культурных событий."""

    def __init__(self, db: AsyncSession, user: str = "import_service"):
        self.db = db
        self.user = user

    async def import_from_json(self, json_data: Union[str, bytes, List[Dict[str, Any]]]) -> ImportReport:
        """Импорт данных из JSON."""
        start_time = time.time()
        if isinstance(json_data, (str, bytes)):
            try:
                items = json.loads(json_data)
            except Exception as e:
                return ImportReport(
                    total=0,
                    added=0,
                    updated=0,
                    merged=0,
                    rejected_count=1,
                    rejected_items=[ImportRejectedItem(row=0, reason=f"Некорректный JSON: {str(e)}")],
                    duration_ms=(time.time() - start_time) * 1000,
                )
        else:
            items = json_data

        if not isinstance(items, list):
            items = [items]

        return await self._process_items(items, start_time)

    async def import_from_csv(self, csv_content: Union[str, bytes]) -> ImportReport:
        """Импорт данных из CSV (с автоопределением разделителя ',' или ';')."""
        start_time = time.time()
        if isinstance(csv_content, bytes):
            text = csv_content.decode("utf-8-sig", errors="replace")
        else:
            text = csv_content

        items = []
        try:
            # Определение диалекта / разделителя
            sample = text[:2048]
            delimiter = ";" if ";" in sample and sample.count(";") > sample.count(",") else ","
            reader = csv.DictReader(io.StringIO(text), delimiter=delimiter)
            for row in reader:
                items.append(dict(row))
        except Exception as e:
            return ImportReport(
                total=0,
                added=0,
                updated=0,
                merged=0,
                rejected_count=1,
                rejected_items=[ImportRejectedItem(row=0, reason=f"Ошибка парсинга CSV: {str(e)}")],
                duration_ms=(time.time() - start_time) * 1000,
            )

        return await self._process_items(items, start_time)

    async def _process_items(self, items: List[Dict[str, Any]], start_time: float) -> ImportReport:
        """Обработка списка записей с валидацией, дедупликацией и аудитом."""
        total = len(items)
        added = 0
        updated = 0
        merged = 0
        rejected_items: List[ImportRejectedItem] = []

        for idx, row in enumerate(items, start=1):
            validation_error, event_dict = self._validate_and_clean_row(row, idx)
            source_hash = compute_source_hash(row)

            # Сохранение сырых данных (ТЗ 6.1)
            raw_event = RawEvent(
                id=uuid.uuid4(),
                source_type=str(row.get("source_type", "импорт")),
                source_url=row.get("source_url"),
                source_hash=source_hash,
                raw_payload=row,
                import_status="rejected" if validation_error else "processed",
                error_message=validation_error,
            )
            self.db.add(raw_event)

            if validation_error:
                rejected_items.append(
                    ImportRejectedItem(
                        row=idx,
                        title=row.get("title"),
                        reason=validation_error,
                        raw_data=row,
                    )
                )
                continue

            # 1. Проверка на строгий дубль по source_hash (идемпотентность импорта того же источника)
            stmt_hash = select(Event).where(Event.source_hash == source_hash)
            existing_by_hash = (await self.db.execute(stmt_hash)).scalars().first()

            if existing_by_hash:
                # Запись уже импортирована из этого же источника: проверяем, нужно ли обновить поля
                is_changed = False
                for field, new_val in event_dict.items():
                    if field in ("id", "created_at", "updated_at", "dedup_key", "source_hash"):
                        continue
                    existing_val = getattr(existing_by_hash, field)
                    if isinstance(existing_val, datetime) and isinstance(new_val, datetime):
                        if existing_val.replace(tzinfo=None) != new_val.replace(tzinfo=None):
                            setattr(existing_by_hash, field, new_val)
                            is_changed = True
                    elif existing_val != new_val:
                        setattr(existing_by_hash, field, new_val)
                        is_changed = True

                if is_changed:
                    existing_by_hash.updated_at = datetime.now(timezone.utc)
                    await log_audit(
                        self.db,
                        action="update",
                        entity_type="event",
                        entity_id=str(existing_by_hash.id),
                        user=self.user,
                        changes={"reason": "Идемпотентное обновление из того же источника"},
                    )
                    updated += 1
                # Если не изменилось — ничего не делаем (идемпотентно пропущено)
                continue

            # 2. Проверка дедупликации: то же событие из ДРУГОГО источника
            dedup_key = event_dict["dedup_key"]
            stmt_dedup = select(Event).where(Event.dedup_key == dedup_key)
            existing_by_dedup = (await self.db.execute(stmt_dedup)).scalars().first()

            if existing_by_dedup:
                # Сведение дубля в единую карточку (ТЗ 6.1, 6.3)
                source_entry = EventSource(
                    id=uuid.uuid4(),
                    event_id=existing_by_dedup.id,
                    source_url=event_dict.get("source_url") or "не указан",
                    source_type=event_dict.get("source_type") or "импорт",
                    source_title=event_dict.get("title"),
                    source_hash=source_hash,
                )
                self.db.add(source_entry)

                # Обогащение карточки недостающими данными (адрес, описание, билеты)
                enriched_fields = []
                if not existing_by_dedup.org_link and event_dict.get("org_link"):
                    existing_by_dedup.org_link = event_dict["org_link"]
                    enriched_fields.append("org_link")
                if not existing_by_dedup.description and event_dict.get("description"):
                    existing_by_dedup.description = event_dict["description"]
                    enriched_fields.append("description")
                if (not existing_by_dedup.lat or not existing_by_dedup.lon) and event_dict.get("lat"):
                    existing_by_dedup.lat = event_dict.get("lat")
                    existing_by_dedup.lon = event_dict.get("lon")
                    enriched_fields.append("coordinates")

                # Объединение тегов
                new_tags = list(set(existing_by_dedup.tags + event_dict.get("tags", [])))
                existing_by_dedup.tags = new_tags

                await log_audit(
                    self.db,
                    action="dedup_merge",
                    entity_type="event",
                    entity_id=str(existing_by_dedup.id),
                    user=self.user,
                    changes={
                        "merged_source_url": event_dict.get("source_url"),
                        "enriched_fields": enriched_fields,
                    },
                )
                merged += 1
                continue

            # 3. Новое уникальное событие: создание карточки + первой записи в sources
            new_event_id = uuid.uuid4()
            new_event = Event(
                id=new_event_id,
                title=event_dict["title"],
                normalized_title=event_dict["normalized_title"],
                category=event_dict["category"],
                tags=event_dict["tags"],
                date_start=event_dict["date_start"],
                date_end=event_dict.get("date_end"),
                duration_min=event_dict.get("duration_min"),
                city=event_dict["city"],
                venue=event_dict["venue"],
                address=event_dict["address"],
                lat=event_dict.get("lat"),
                lon=event_dict.get("lon"),
                description=event_dict.get("description", ""),
                price_min=event_dict.get("price_min", 0),
                price_max=event_dict.get("price_max", 0),
                is_free=event_dict.get("is_free", False),
                age_limit=event_dict.get("age_limit", 0),
                language=event_dict.get("language"),
                org_link=event_dict.get("org_link"),
                source_url=event_dict.get("source_url"),
                source_type=event_dict.get("source_type", "импорт"),
                source_hash=source_hash,
                verified_at=datetime.now(timezone.utc),
                confidence=event_dict.get("confidence", 1.0),
                status=event_dict.get("status", "опубликовано"),
                dedup_key=dedup_key,
            )
            self.db.add(new_event)

            # Сохраняем исходный источник
            first_source = EventSource(
                id=uuid.uuid4(),
                event_id=new_event_id,
                source_url=event_dict.get("source_url") or "не указан",
                source_type=event_dict.get("source_type") or "импорт",
                source_title=event_dict.get("title"),
                source_hash=source_hash,
            )
            self.db.add(first_source)

            await log_audit(
                self.db,
                action="create",
                entity_type="event",
                entity_id=str(new_event_id),
                user=self.user,
                changes={"title": new_event.title, "city": new_event.city},
            )
            added += 1

        await self.db.commit()

        duration = (time.time() - start_time) * 1000
        return ImportReport(
            total=total,
            added=added,
            updated=updated,
            merged=merged,
            rejected_count=len(rejected_items),
            rejected_items=rejected_items,
            duration_ms=round(duration, 2),
        )

    def _validate_and_clean_row(self, row: Dict[str, Any], row_num: int) -> Tuple[Optional[str], Dict[str, Any]]:
        """Валидация полей согласно разделу 6.1 и 8.1 ТЗ."""
        title = str(row.get("title", "")).strip()
        if not title:
            return "Отсутствует обязательное поле 'title'", {}

        city = str(row.get("city", "")).strip()
        if not city:
            return "Отсутствует обязательное поле 'city'", {}

        venue = str(row.get("venue", "")).strip()
        if not venue:
            return "Отсутствует обязательное поле 'venue'", {}

        address = str(row.get("address", "")).strip() or venue

        # Проверка и парсинг дат
        date_start = parse_datetime(row.get("date_start"))
        if not date_start:
            return "Отсутствует или некорректна дата начала 'date_start'", {}

        date_end = parse_datetime(row.get("date_end"))
        if date_end and date_end < date_start:
            return "Дата окончания 'date_end' не может быть раньше начала 'date_start'", {}

        # Категория
        category = str(row.get("category", "другое")).strip().lower()
        valid_categories = {"концерт", "спектакль", "выставка", "фестиваль", "кино", "экскурсия", "другое"}
        if category not in valid_categories:
            category = "другое"

        # Теги
        raw_tags = row.get("tags", [])
        if isinstance(raw_tags, str):
            tags = [t.strip().lower() for t in raw_tags.split(",") if t.strip()]
        elif isinstance(raw_tags, list):
            tags = [str(t).strip().lower() for t in raw_tags if str(t).strip()]
        else:
            tags = []

        # Цены и бесплатность
        try:
            price_min = int(row.get("price_min", 0))
        except (ValueError, TypeError):
            price_min = 0

        try:
            price_max = int(row.get("price_max", 0))
        except (ValueError, TypeError):
            price_max = price_min

        if price_max < price_min:
            price_max = price_min

        is_free_val = row.get("is_free")
        if isinstance(is_free_val, str):
            is_free = is_free_val.strip().lower() in ("true", "1", "да", "yes")
        elif isinstance(is_free_val, bool):
            is_free = is_free_val
        else:
            is_free = (price_min == 0 and price_max == 0)

        # Возрастное ограничение
        try:
            age_limit = int(row.get("age_limit", 0))
            if age_limit not in (0, 6, 12, 16, 18):
                age_limit = 0
        except (ValueError, TypeError):
            age_limit = 0

        # Статус
        raw_status = str(row.get("status", "опубликовано")).strip().lower()
        if raw_status in ("cancelled", "canceled", "отменено"):
            status = "отменено"
        elif raw_status in ("draft", "черновик"):
            status = "черновик"
        elif raw_status in ("published", "опубликовано"):
            status = "опубликовано"
        else:
            status = "опубликовано"

        # Длительность
        try:
            duration_min = int(row.get("duration_min")) if row.get("duration_min") is not None else None
        except (ValueError, TypeError):
            duration_min = None

        # Координаты
        try:
            lat = float(row.get("lat")) if row.get("lat") is not None else None
            lon = float(row.get("lon")) if row.get("lon") is not None else None
        except (ValueError, TypeError):
            lat, lon = None, None

        # Нормализованное название и ключ дедупликации
        norm_title = normalize_string(title)
        dedup_key = compute_dedup_key(city, title, date_start)

        cleaned: Dict[str, Any] = {
            "title": title,
            "normalized_title": norm_title,
            "category": category,
            "tags": tags,
            "date_start": date_start,
            "date_end": date_end,
            "duration_min": duration_min,
            "city": city,
            "venue": venue,
            "address": address,
            "lat": lat,
            "lon": lon,
            "description": str(row.get("description", "")).strip(),
            "price_min": price_min,
            "price_max": price_max,
            "is_free": is_free,
            "age_limit": age_limit,
            "language": str(row.get("language")).strip() if row.get("language") else None,
            "org_link": str(row.get("org_link")).strip() if row.get("org_link") else None,
            "source_url": str(row.get("source_url")).strip() if row.get("source_url") else None,
            "source_type": str(row.get("source_type", "импорт")).strip(),
            "status": status,
            "confidence": float(row.get("confidence", 1.0)),
            "dedup_key": dedup_key,
        }
        return None, cleaned
