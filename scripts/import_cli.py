"""CLI-скрипт для импорта файлов мероприятий (JSON/CSV) с отчётом (ТЗ 6.1)."""

import argparse
import asyncio
import os
import sys
from pathlib import Path

# Добавляем корень проекта
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.database import AsyncSessionLocal, engine, init_db
from src.services.import_service import ImportService


async def run_import(file_path: str, user: str = "cli_importer"):
    path = Path(file_path)
    if not path.exists():
        print(f"❌ Ошибка: файл не найден: {file_path}")
        sys.exit(1)

    print(f"📦 Чтение файла: {path.name} ({path.stat().st_size} байт)...")
    content = path.read_bytes()

    print("🔌 Подключение к базе данных...")
    await init_db()

    async with AsyncSessionLocal() as session:
        service = ImportService(session, user=user)
        filename_lower = path.name.lower()

        if filename_lower.endswith(".csv"):
            report = await service.import_from_csv(content)
        else:
            report = await service.import_from_json(content)

    print("\n" + "=" * 55)
    print("📊 ИТОГОВЫЙ ОТЧЁТ ОБ ИМПОРТЕ МЕРОПРИЯТИЙ (ТЗ 6.1)")
    print("=" * 55)
    print(f"  • Всего обработано записей:  {report.total}")
    print(f"  • Успешно добавлено новых:   {report.added}")
    print(f"  • Обновлено существующих:    {report.updated}")
    print(f"  • Сведено дубликатов (dedup):{report.merged}")
    print(f"  • Отклонено записей:         {report.rejected_count}")
    print(f"  • Время выполнения:          {report.duration_ms:.2f} мс")

    if report.rejected_items:
        print("\n⚠️ Список отклонённых записей:")
        for r in report.rejected_items:
            print(f"  - Строка {r.row}: {r.reason}")

    print("=" * 55 + "\n")


def main():
    parser = argparse.ArgumentParser(description="Импорт мероприятий в базу данных Афиши Башкортостана")
    parser.add_argument("file", help="Путь к файлу JSON или CSV")
    parser.add_argument("--user", default="cli_admin", help="Имя пользователя для журнала аудита")
    args = parser.parse_args()

    asyncio.run(run_import(args.file, user=args.user))


if __name__ == "__main__":
    main()
