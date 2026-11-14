"""Точка входа запуска Telegram-бота (aiogram 3.x)."""

import asyncio
import logging
import sys

from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode

from bot.config import bot_settings
from bot.handlers.catalog import router as catalog_router
from bot.handlers.start import router as start_router
from bot.handlers.subscriptions import router as subscriptions_router
from bot.handlers.text_search import router as text_search_router

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("afisha.bot")


async def main():
    token = bot_settings.BOT_TOKEN
    if not token or token in ("dummy_token", "YOUR_TELEGRAM_BOT_TOKEN_HERE", "dummy_token_for_local_dev"):
        logger.warning(
            "⚠️ BOT_TOKEN не задан или является демонстрационным. "
            "Для подключения реального Telegram-бота укажите валидный токен в файле .env."
        )
        return

    bot = Bot(token=token, parse_mode=ParseMode.MARKDOWN)
    dp = Dispatcher()

    # Порядок регистрации роутеров важен: команды и фильтры перед обработчиком свободного текста
    dp.include_router(start_router)
    dp.include_router(catalog_router)
    dp.include_router(subscriptions_router)
    dp.include_router(text_search_router)

    logger.info("🤖 Telegram-бот 'Афиша культуры Башкортостана' успешно запущен...")
    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Бот остановлен.")
