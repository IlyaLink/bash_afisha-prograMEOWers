"""Тесты ключевых хендлеров и логики Telegram-бота (aiogram 3.x, ТЗ 6.2)."""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
import pytest

from bot.handlers.catalog import (
    format_event_message,
    process_custom_date_input,
    process_custom_price_input,
)
from bot.handlers.start import cmd_cancel, cmd_help, cmd_start
from bot.handlers.subscriptions import cmd_unsubscribe_all
from bot.handlers.text_search import handle_free_text_search
from bot.keyboards.menu import (
    get_categories_keyboard,
    get_cities_keyboard,
    get_dates_keyboard,
    get_main_menu_keyboard,
    get_price_keyboard,
    get_subscription_menu_keyboard,
)
from bot.keyboards.pagination import get_event_card_keyboard, get_pagination_keyboard


def make_mock_message(text: str = "", user_id: int = 123456789) -> MagicMock:
    """Создание мока объекта aiogram Message."""
    msg = MagicMock()
    msg.text = text
    msg.from_user = MagicMock()
    msg.from_user.id = user_id
    msg.from_user.username = "test_user"
    msg.answer = AsyncMock()
    return msg


def make_mock_state() -> MagicMock:
    """Создание мока FSMContext."""
    state = MagicMock()
    state.clear = AsyncMock()
    state.set_state = AsyncMock()
    state.get_state = AsyncMock(return_value=None)
    return state


@pytest.mark.asyncio
async def test_cmd_start_renders_compact_menu():
    """Команда /start: короткое понятное приветствие и инлайн-кнопки меню (ТЗ 6.2)."""
    msg = make_mock_message("/start")
    state = make_mock_state()

    await cmd_start(msg, state)

    state.clear.assert_awaited_once()
    msg.answer.assert_awaited_once()
    called_text = msg.answer.call_args[0][0]
    called_kb = msg.answer.call_args[1]["reply_markup"]

    assert "Добро пожаловать в Афишу культуры Башкортостана" in called_text
    assert called_kb is not None
    # Проверяем наличие ключевых разделов в клавиатуре
    button_texts = [btn.text for row in called_kb.inline_keyboard for btn in row]
    assert "🔍 Найти событие" in button_texts
    assert "📅 По дате" in button_texts
    assert "🎟 По цене / Бесплатно" in button_texts
    assert "📍 Города" in button_texts


@pytest.mark.asyncio
async def test_cmd_help_and_cancel():
    """Команды /help и /cancel работают корректно и сбрасывают состояние."""
    # /help
    msg_help = make_mock_message("/help")
    await cmd_help(msg_help)
    msg_help.answer.assert_awaited_once()
    assert "Как пользоваться ботом" in msg_help.answer.call_args[0][0]

    # /cancel
    msg_cancel = make_mock_message("/cancel")
    state_cancel = make_mock_state()
    await cmd_cancel(msg_cancel, state_cancel)
    state_cancel.clear.assert_awaited_once()
    msg_cancel.answer.assert_awaited_once()
    assert "отменено" in msg_cancel.answer.call_args[0][0].lower()


def test_format_event_message_contains_all_tz_fields():
    """Карточка события содержит: название, категорию, дату, место, адрес, описание, цену, возраст (ТЗ 6.2)."""
    event_data = {
        "title": "Балет «Лебединое озеро»",
        "category": "спектакль",
        "date_start": "2026-11-20T19:00:00",
        "city": "Уфа",
        "venue": "Башопера",
        "address": "г. Уфа, ул. Ленина, 5/1",
        "description": "Шедевр мировой классической хореографии П.И. Чайковского.",
        "price_min": 500,
        "price_max": 2500,
        "is_free": False,
        "age_limit": 6,
        "language": "русский",
    }

    card_text = format_event_message(event_data)

    assert "Балет «Лебединое озеро»" in card_text
    assert "Спектакль" in card_text
    assert "20.11.2026 в 19:00" in card_text
    assert "Уфа" in card_text
    assert "Башопера" in card_text
    assert "ул. Ленина, 5/1" in card_text
    assert "500 – 2500 ₽" in card_text
    assert "[6+]" in card_text
    assert "Шедевр мировой классической хореографии" in card_text


def test_format_event_free_and_bashkir_badge():
    """Бесплатные события и пометка башкирского языка."""
    free_bashkir_event = {
        "title": "Этно-спектакль «Урал-батыр»",
        "category": "спектакль",
        "date_start": "2026-11-22T18:00:00",
        "city": "Сибай",
        "venue": "Сибайский драмтеатр",
        "address": "ул. Заки Валиди, 26",
        "description": "Бесплатный народный показ.",
        "price_min": 0,
        "price_max": 0,
        "is_free": True,
        "age_limit": 12,
        "language": "башкирский",
    }
    card_text = format_event_message(free_bashkir_event)
    assert "Бесплатно" in card_text
    assert "на башкирском языке" in card_text


@pytest.mark.asyncio
async def test_custom_date_input_validation():
    """Валидация пользовательского ввода конкретной даты."""
    state = make_mock_state()

    # 1. Некорректный ввод
    msg_invalid = make_mock_message("непонятная_дата")
    await process_custom_date_input(msg_invalid, state)
    state.clear.assert_not_called()
    assert "Не удалось распознать дату" in msg_invalid.answer.call_args[0][0]

    # 2. Корректный ввод ДД.ММ.ГГГГ
    msg_valid = make_mock_message("25.11.2026")
    with patch("bot.handlers.catalog.send_events_list", new_callable=AsyncMock) as mock_send:
        await process_custom_date_input(msg_valid, state)
        state.clear.assert_awaited_once()
        mock_send.assert_awaited_once()
        assert mock_send.call_args[1]["filter_type"] == "custom_date"
        assert mock_send.call_args[1]["filter_value"] == "2026-11-25"


@pytest.mark.asyncio
async def test_custom_price_input_validation():
    """Валидация ввода максимальной цены билета."""
    state = make_mock_state()

    # 1. Не число или отрицательное
    msg_invalid = make_mock_message("много рублей")
    await process_custom_price_input(msg_invalid, state)
    state.clear.assert_not_called()
    assert "корректное положительное число" in msg_invalid.answer.call_args[0][0]

    # 2. Валидное число
    msg_valid = make_mock_message("750 ₽")
    with patch("bot.handlers.catalog.send_events_list", new_callable=AsyncMock) as mock_send:
        await process_custom_price_input(msg_valid, state)
        state.clear.assert_awaited_once()
        mock_send.assert_awaited_once()
        assert mock_send.call_args[1]["filter_type"] == "price"
        assert mock_send.call_args[1]["filter_value"] == "750"


@pytest.mark.asyncio
async def test_free_text_search_triggers_catalog():
    """Свободный текст в чате обрабатывается как поисковый запрос (ТЗ 6.2)."""
    msg = make_mock_message("Шаляпин")
    state = make_mock_state()

    with patch("bot.handlers.text_search.send_events_list", new_callable=AsyncMock) as mock_send:
        await handle_free_text_search(msg, state)
        state.clear.assert_awaited_once()
        mock_send.assert_awaited_once()
        assert mock_send.call_args[1]["filter_type"] == "q"
        assert mock_send.call_args[1]["filter_value"] == "Шаляпин"


@pytest.mark.asyncio
async def test_cmd_unsubscribe_all():
    """Отписка одной командой /unsubscribe (ТЗ 6.2)."""
    msg = make_mock_message("/unsubscribe", user_id=987654)
    with patch("bot.handlers.subscriptions.api_client.unsubscribe_all", new_callable=AsyncMock) as mock_unsub:
        mock_unsub.return_value = True
        await cmd_unsubscribe_all(msg)
        mock_unsub.assert_awaited_once_with("987654")
        assert "успешно отписались" in msg.answer.call_args[0][0]


def test_keyboards_composition():
    """Проверка структуры и наличия обязательных фильтров в клавиатурах."""
    dates_kb = get_dates_keyboard()
    date_buttons = [btn.text for row in dates_kb.inline_keyboard for btn in row]
    assert any("Сегодня" in t for t in date_buttons)
    assert any("Завтра" in t for t in date_buttons)
    assert any("выходные" in t for t in date_buttons)
    assert any("неделе" in t for t in date_buttons)
    assert any("Ввести конкретную дату" in t for t in date_buttons)

    price_kb = get_price_keyboard()
    price_buttons = [btn.text for row in price_kb.inline_keyboard for btn in row]
    assert any("бесплатные" in t.lower() for t in price_buttons)
    assert any("500" in t for t in price_buttons)
    assert any("1 000" in t for t in price_buttons)

    cities_kb = get_cities_keyboard()
    city_buttons = [btn.text for row in cities_kb.inline_keyboard for btn in row]
    assert any("Уфа" in t for t in city_buttons)
    assert any("Стерлитамак" in t for t in city_buttons)
    assert any("Салават" in t for t in city_buttons)
    assert any("Нефтекамск" in t for t in city_buttons)

    pag_kb = get_pagination_keyboard(page=1, has_next=True, filter_type="city", filter_value="Уфа")
    pag_buttons = [btn.text for row in pag_kb.inline_keyboard for btn in row]
    assert "Показать ещё ⏩" in pag_buttons
    assert "🔍 Новый поиск" in pag_buttons
    assert "« Главное меню" in pag_buttons
