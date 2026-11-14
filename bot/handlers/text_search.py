"""Обработка свободного текстового ввода как поискового запроса (ТЗ 6.2)."""

from aiogram import Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from bot.handlers.catalog import send_events_list
from bot.states.search import SearchStates

router = Router()


@router.message(SearchStates.waiting_for_query)
@router.message()
async def handle_free_text_search(message: Message, state: FSMContext):
    """Свободный текст обрабатывается как поиск по афише (ТЗ 6.2)."""
    # Игнорируем команды (они обрабатываются соответствующими роутерами)
    if message.text and message.text.startswith("/"):
        return

    query = (message.text or "").strip()
    if not query:
        return

    await state.clear()
    await message.answer(f"🔎 Ищу мероприятия по запросу: «**{query}**»...")
    await send_events_list(message, filter_type="q", filter_value=query)
