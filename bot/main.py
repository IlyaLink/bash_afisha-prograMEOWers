"""Точка входа запуска Telegram-бота (aiogram 3.x)."""

import asyncio
import logging
import sys

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.types import ErrorEvent

from bot.api_client import api_client
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

    # Настройка и валидация адреса бэкенда
    backend_url = bot_settings.BACKEND_API_URL
    api_client.base_url = backend_url
    logger.info("🌐 Подключение Telegram-бота к REST API: %s", api_client.base_url)

    bot = Bot(
        token=token,
        default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN),
    )
    dp = Dispatcher()

    # Передача API-клиента в workflow_data для хендлеров и middleware
    dp.workflow_data["api_client"] = api_client
    dp.workflow_data["backend_api_url"] = api_client.base_url
    dp["api_client"] = api_client
    dp["backend_api_url"] = api_client.base_url

    # Порядок регистрации роутеров: команды и фильтры перед общим обработчиком свободного текста
    dp.include_router(start_router)
    dp.include_router(catalog_router)
    dp.include_router(subscriptions_router)
    dp.include_router(text_search_router)

    # Глобальный обработчик ошибок (ТЗ 6.2 - бот не должен падать на неожиданных ошибках)
    @dp.error()
    async def global_error_handler(event: ErrorEvent):
        logger.exception("Unhandled bot error", exc_info=event.exception)
        error_msg = (
            "⚠️ Произошла непредвиденная ошибка при обработке запроса. "
            "Пожалуйста, попробуйте ещё раз или воспользуйтесь командой /start для возврата в главное меню."
        )
        try:
            if event.update.message:
                await event.update.message.answer(error_msg, parse_mode=None)
            elif event.update.callback_query:
                # Пытаемся ответить на callback toast (если ещё не был отвечен)
                try:
                    await event.update.callback_query.answer("⚠️ Произошла ошибка. Пожалуйста, повторите попытку.", show_alert=True)
                except Exception:
                    pass
                # Обязательно отправляем сообщение в чат, чтобы пользователь видел статус
                if event.update.callback_query.message:
                    await event.update.callback_query.message.answer(error_msg, parse_mode=None)
                else:
                    await bot.send_message(chat_id=event.update.callback_query.from_user.id, text=error_msg, parse_mode=None)
        except Exception as send_err:
            logger.error("Не удалось отправить сообщение об ошибке пользователю: %s", send_err)

    logger.info("🤖 Telegram-бот 'Афиша культуры Башкортостана' успешно запущен...")
    try:
        await dp.start_polling(bot, api_client=api_client)
    finally:
        await bot.session.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Бот остановлен.")
