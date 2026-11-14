"""Обработчики каталога, фильтрации по датам, ценам, городам и категориям."""

import logging
import re
from datetime import datetime
from typing import Any, Optional
from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from bot.api_client import BackendAPIClient, api_client
from bot.keyboards.menu import (
    get_categories_keyboard,
    get_cities_keyboard,
    get_dates_keyboard,
    get_main_menu_keyboard,
    get_price_keyboard,
)
from bot.keyboards.pagination import get_event_card_keyboard, get_pagination_keyboard
from bot.states.search import SearchStates

logger = logging.getLogger("afisha.bot.catalog")
router = Router()


def format_event_message(e: dict) -> str:
    """Форматирование карточки события для отправки в Telegram (ТЗ 6.2)."""
    title = e.get("title", "Без названия")
    category = e.get("category", "Событие").capitalize()
    age_limit = e.get("age_limit", 0)

    # Дата и время
    dt_str = e.get("date_start", "")
    try:
        dt = datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
        date_formatted = dt.strftime("%d.%m.%Y в %H:%M")
    except Exception:
        date_formatted = dt_str

    city = e.get("city", "")
    venue = e.get("venue", "")
    address = e.get("address", "")

    # Цена
    if e.get("is_free"):
        price_text = "Бесплатно"
    elif e.get("price_min", 0) > 0 and e.get("price_max", 0) > e.get("price_min", 0):
        price_text = f"{e['price_min']} – {e['price_max']} ₽"
    elif e.get("price_min", 0) > 0:
        price_text = f"от {e['price_min']} ₽"
    else:
        price_text = "Бесплатно / Уточняется"

    language = e.get("language")
    lang_badge = " 🗣 (на башкирском языке)" if language == "башкирский" else ""

    desc = e.get("description", "")
    if len(desc) > 220:
        desc = desc[:220].rstrip() + "..."

    # Экранирование или понятная верстка Markdown
    msg = (
        f"🎭 **{title}** [{age_limit}+]{lang_badge}\n"
        f"🏷 Категория: {category}\n"
        f"📅 Дата и время: **{date_formatted}**\n"
        f"📍 Город: **{city}**\n"
        f"🏛 Площадка: {venue}\n"
        f"🏠 Адрес: {address}\n"
        f"🎟 Стоимость: **{price_text}**\n\n"
        f"📝 {desc}"
    )
    return msg


async def _send_reply(
    message: Optional[Message],
    bot: Optional[Any],
    chat_id: Optional[int],
    text: str,
    reply_markup=None,
    parse_mode: Optional[str] = "Markdown",
):
    """Безопасная отправка сообщения с фолбэком на plain text при ошибках Markdown."""
    if message:
        try:
            return await message.answer(text, reply_markup=reply_markup, parse_mode=parse_mode)
        except Exception as e:
            if parse_mode is not None:
                logger.warning("Markdown parse error on message.answer, falling back to plain text: %s", e)
                clean_text = text.replace("**", "").replace("*", "").replace("[", "").replace("]", "")
                return await message.answer(clean_text, reply_markup=reply_markup, parse_mode=None)
            raise e
    elif bot and chat_id:
        try:
            return await bot.send_message(chat_id=chat_id, text=text, reply_markup=reply_markup, parse_mode=parse_mode)
        except Exception as e:
            if parse_mode is not None:
                logger.warning("Markdown parse error on bot.send_message, falling back to plain text: %s", e)
                clean_text = text.replace("**", "").replace("*", "").replace("[", "").replace("]", "")
                return await bot.send_message(chat_id=chat_id, text=clean_text, reply_markup=reply_markup, parse_mode=None)
            raise e
    else:
        logger.error("Ни message, ни bot+chat_id не доступны для отправки ответа")


async def send_events_list(
    message: Optional[Message],
    filter_type: str,
    filter_value: str = "",
    page: int = 1,
    size: int = 3,
    client: Optional[BackendAPIClient] = None,
    bot: Optional[Any] = None,
    chat_id: Optional[int] = None,
):
    """Универсальная отправка порции событий с кнопками и пагинацией."""
    target_client = client or api_client
    params = {"page": page, "size": size}
    if filter_type == "city":
        params["city"] = filter_value
    elif filter_type == "category":
        params["category"] = filter_value
    elif filter_type == "period":
        params["period"] = filter_value
    elif filter_type == "free":
        params["is_free"] = True
    elif filter_type == "price":
        params["price_max"] = int(filter_value)
    elif filter_type == "custom_date":
        params["date_from"] = f"{filter_value}T00:00:00"
        params["date_to"] = f"{filter_value}T23:59:59"
    elif filter_type == "q":
        params["q"] = filter_value

    try:
        data = await target_client.get_events(**params)
        events = data.get("items", [])
        meta = data.get("meta", {})
    except Exception as err:
        logger.error("Не удалось загрузить события с сервера (%s): %s", target_client.base_url, err, exc_info=True)
        await _send_reply(
            message,
            bot,
            chat_id,
            f"⚠️ Не удалось загрузить события с сервера: {str(err)}",
            parse_mode=None,
        )
        return

    if not events:
        # Запрашиваем объяснение причин пустой выдачи
        explain_params = {k: v for k, v in params.items() if k not in ("page", "size")}
        try:
            explanation = await target_client.explain_empty(**explain_params)
        except Exception:
            explanation = {}

        reasons = explanation.get("reasons", [])
        suggestions = explanation.get("suggestions", [])

        msg_lines = ["🔍 **По выбранным критериям мероприятий не найдено.**\n"]
        if reasons:
            msg_lines.append("**Возможные причины:**")
            for r in reasons:
                msg_lines.append(f"• {r}")
            msg_lines.append("")

        if suggestions:
            msg_lines.append("💡 **Рекомендации:**")
            for s in suggestions:
                msg_lines.append(f"• {s}")
            msg_lines.append("")
        else:
            msg_lines.append("💡 Попробуйте выбрать другой город, дату или ввести более общий поисковый запрос.")

        msg_lines.append("\nВы можете сразу написать новый запрос текстом в чат или воспользоваться меню:")

        await _send_reply(
            message,
            bot,
            chat_id,
            "\n".join(msg_lines),
            reply_markup=get_main_menu_keyboard(),
            parse_mode="Markdown",
        )
        return

    # Отправляем карточки найденных событий
    for ev in events:
        card_text = format_event_message(ev)
        kb = get_event_card_keyboard(ev["id"], ev.get("org_link"), ev.get("source_url"))
        await _send_reply(message, bot, chat_id, card_text, reply_markup=kb, parse_mode="Markdown")

    # Пагинация «Показать ещё ⏩»
    pag_kb = get_pagination_keyboard(
        page=page,
        has_next=meta.get("has_next", False),
        filter_type=filter_type,
        filter_value=filter_value,
    )
    total = meta.get("total", len(events))
    showing = min(page * size, total)
    await _send_reply(
        message,
        bot,
        chat_id,
        f"Показано {showing} из {total} мероприятий.",
        reply_markup=pag_kb,
        parse_mode=None,
    )


@router.callback_query(F.data.startswith("event_info:"))
async def cb_event_info_hint(call: CallbackQuery):
    await call.answer("Карточка события доступна на веб-сайте афиши: http://localhost:8000/", show_alert=True)


# --- Навигация по подменю фильтров ---

@router.callback_query(F.data == "btn_dates_menu")
async def cb_show_dates(call: CallbackQuery):
    """Меню выбора даты и периода."""
    if call.message and hasattr(call.message, "edit_text"):
        await call.message.edit_text("📅 Выберите период или укажите конкретную дату:", reply_markup=get_dates_keyboard())
    elif call.message:
        await call.message.answer("📅 Выберите период или укажите конкретную дату:", reply_markup=get_dates_keyboard())
    await call.answer()


@router.callback_query(F.data == "btn_price_menu")
async def cb_show_price(call: CallbackQuery):
    """Меню фильтрации по цене."""
    if call.message and hasattr(call.message, "edit_text"):
        await call.message.edit_text("🎟 Выберите ценовой диапазон или бесплатные события:", reply_markup=get_price_keyboard())
    elif call.message:
        await call.message.answer("🎟 Выберите ценовой диапазон или бесплатные события:", reply_markup=get_price_keyboard())
    await call.answer()


@router.callback_query(F.data == "btn_categories")
async def cb_show_categories(call: CallbackQuery):
    """Меню выбора категории."""
    if call.message and hasattr(call.message, "edit_text"):
        await call.message.edit_text("🎭 Выберите категорию мероприятий:", reply_markup=get_categories_keyboard())
    elif call.message:
        await call.message.answer("🎭 Выберите категорию мероприятий:", reply_markup=get_categories_keyboard())
    await call.answer()


@router.callback_query(F.data == "btn_cities")
async def cb_show_cities(call: CallbackQuery):
    """Меню выбора города Республики Башкортостан."""
    if call.message and hasattr(call.message, "edit_text"):
        await call.message.edit_text("📍 Выберите город Республики Башкортостан:", reply_markup=get_cities_keyboard())
    elif call.message:
        await call.message.answer("📍 Выберите город Республики Башкортостан:", reply_markup=get_cities_keyboard())
    await call.answer()


@router.callback_query(F.data == "btn_search")
async def cb_start_search(call: CallbackQuery, state: FSMContext):
    """Инициация текстового поиска."""
    await state.set_state(SearchStates.waiting_for_query)
    target_msg = call.message if (call.message and hasattr(call.message, "answer")) else None
    await _send_reply(
        target_msg,
        call.bot,
        call.from_user.id if call.from_user else None,
        "🔍 Введите название спектакля, концерта, артиста или площадки для поиска:",
        parse_mode=None,
    )
    await call.answer()


# --- Быстрые фильтры периодов и дат ---

@router.callback_query(F.data == "period_today")
async def cb_filter_today(call: CallbackQuery, api_client: Optional[BackendAPIClient] = None):
    await call.answer("Загрузка афиши на сегодня...")
    target_msg = call.message if (call.message and hasattr(call.message, "answer")) else None
    await send_events_list(
        target_msg,
        filter_type="period",
        filter_value="today",
        client=api_client,
        bot=call.bot,
        chat_id=call.from_user.id if call.from_user else None,
    )


@router.callback_query(F.data == "period_tomorrow")
async def cb_filter_tomorrow(call: CallbackQuery, api_client: Optional[BackendAPIClient] = None):
    await call.answer("Загрузка афиши на завтра...")
    target_msg = call.message if (call.message and hasattr(call.message, "answer")) else None
    await send_events_list(
        target_msg,
        filter_type="period",
        filter_value="tomorrow",
        client=api_client,
        bot=call.bot,
        chat_id=call.from_user.id if call.from_user else None,
    )


@router.callback_query(F.data == "period_weekend")
async def cb_filter_weekend(call: CallbackQuery, api_client: Optional[BackendAPIClient] = None):
    await call.answer("Загрузка афиши на выходные...")
    target_msg = call.message if (call.message and hasattr(call.message, "answer")) else None
    await send_events_list(
        target_msg,
        filter_type="period",
        filter_value="weekend",
        client=api_client,
        bot=call.bot,
        chat_id=call.from_user.id if call.from_user else None,
    )


@router.callback_query(F.data == "period_week")
async def cb_filter_week(call: CallbackQuery, api_client: Optional[BackendAPIClient] = None):
    await call.answer("Загрузка афиши на неделю...")
    target_msg = call.message if (call.message and hasattr(call.message, "answer")) else None
    await send_events_list(
        target_msg,
        filter_type="period",
        filter_value="week",
        client=api_client,
        bot=call.bot,
        chat_id=call.from_user.id if call.from_user else None,
    )


@router.callback_query(F.data == "period_custom")
async def cb_filter_custom_date_prompt(call: CallbackQuery, state: FSMContext):
    """Запрос конкретной даты у пользователя."""
    await state.set_state(SearchStates.waiting_for_date)
    target_msg = call.message if (call.message and hasattr(call.message, "answer")) else None
    prompt_text = (
        "📆 Введите желаемую дату в формате **ДД.ММ.ГГГГ** (например: *25.11.2026*):\n\n"
        "Для отмены отправьте /cancel"
    )
    await _send_reply(
        target_msg,
        call.bot,
        call.from_user.id if call.from_user else None,
        prompt_text,
        parse_mode="Markdown",
    )
    await call.answer()


# --- Фильтры по цене ---

@router.callback_query(F.data == "filter_free")
async def cb_filter_free(call: CallbackQuery, api_client: Optional[BackendAPIClient] = None):
    await call.answer("Загрузка бесплатных мероприятий...")
    target_msg = call.message if (call.message and hasattr(call.message, "answer")) else None
    await send_events_list(
        target_msg,
        filter_type="free",
        client=api_client,
        bot=call.bot,
        chat_id=call.from_user.id if call.from_user else None,
    )


@router.callback_query(F.data == "price_500")
async def cb_filter_price_500(call: CallbackQuery, api_client: Optional[BackendAPIClient] = None):
    await call.answer("Мероприятия до 500 ₽...")
    target_msg = call.message if (call.message and hasattr(call.message, "answer")) else None
    await send_events_list(
        target_msg,
        filter_type="price",
        filter_value="500",
        client=api_client,
        bot=call.bot,
        chat_id=call.from_user.id if call.from_user else None,
    )


@router.callback_query(F.data == "price_1000")
async def cb_filter_price_1000(call: CallbackQuery, api_client: Optional[BackendAPIClient] = None):
    await call.answer("Мероприятия до 1000 ₽...")
    target_msg = call.message if (call.message and hasattr(call.message, "answer")) else None
    await send_events_list(
        target_msg,
        filter_type="price",
        filter_value="1000",
        client=api_client,
        bot=call.bot,
        chat_id=call.from_user.id if call.from_user else None,
    )


@router.callback_query(F.data == "price_2000")
async def cb_filter_price_2000(call: CallbackQuery, api_client: Optional[BackendAPIClient] = None):
    await call.answer("Мероприятия до 2000 ₽...")
    target_msg = call.message if (call.message and hasattr(call.message, "answer")) else None
    await send_events_list(
        target_msg,
        filter_type="price",
        filter_value="2000",
        client=api_client,
        bot=call.bot,
        chat_id=call.from_user.id if call.from_user else None,
    )


@router.callback_query(F.data == "price_custom")
async def cb_filter_custom_price_prompt(call: CallbackQuery, state: FSMContext):
    """Запрос максимальной цены."""
    await state.set_state(SearchStates.waiting_for_price)
    target_msg = call.message if (call.message and hasattr(call.message, "answer")) else None
    prompt_text = (
        "💰 Введите максимальную стоимость билета в рублях (например: *700*):\n\n"
        "Для отмены отправьте /cancel"
    )
    await _send_reply(
        target_msg,
        call.bot,
        call.from_user.id if call.from_user else None,
        prompt_text,
        parse_mode="Markdown",
    )
    await call.answer()


# --- Фильтры категорий и городов ---

@router.callback_query(F.data.startswith("cat_"))
async def cb_filter_by_cat(call: CallbackQuery, api_client: Optional[BackendAPIClient] = None):
    cat = call.data.replace("cat_", "")
    await call.answer(f"Категория: {cat}")
    target_msg = call.message if (call.message and hasattr(call.message, "answer")) else None
    await send_events_list(
        target_msg,
        filter_type="category",
        filter_value=cat,
        client=api_client,
        bot=call.bot,
        chat_id=call.from_user.id if call.from_user else None,
    )


@router.callback_query(F.data.startswith("city_"))
async def cb_filter_by_city(call: CallbackQuery, api_client: Optional[BackendAPIClient] = None):
    city = call.data.replace("city_", "")
    await call.answer(f"Город: {city}")
    target_msg = call.message if (call.message and hasattr(call.message, "answer")) else None
    await send_events_list(
        target_msg,
        filter_type="city",
        filter_value=city,
        client=api_client,
        bot=call.bot,
        chat_id=call.from_user.id if call.from_user else None,
    )


# --- Пагинация: Показать ещё ⏩ ---

@router.callback_query(F.data.startswith("more:"))
async def cb_pagination_more(call: CallbackQuery, api_client: Optional[BackendAPIClient] = None):
    _, f_type, f_val, next_page = call.data.split(":", 3)
    await call.answer("Загрузка следующей страницы...")
    target_msg = call.message if (call.message and hasattr(call.message, "answer")) else None
    await send_events_list(
        target_msg,
        filter_type=f_type,
        filter_value=f_val,
        page=int(next_page),
        client=api_client,
        bot=call.bot,
        chat_id=call.from_user.id if call.from_user else None,
    )


# --- Обработчики состояний ввода даты и цены ---

@router.message(SearchStates.waiting_for_date)
async def process_custom_date_input(message: Message, state: FSMContext):
    """Парсинг и валидация даты от пользователя."""
    if message.text and message.text.startswith("/"):
        return

    raw_text = (message.text or "").strip()
    parsed_date = None
    # Если передан формат без года (ДД.ММ), добавляем текущий год
    if re.match(r"^\d{1,2}[\./]\d{1,2}$", raw_text):
        raw_text = f"{raw_text}.{datetime.now().year}"

    for fmt in ("%d.%m.%Y", "%d/%m/%Y", "%Y-%m-%d"):
        try:
            dt = datetime.strptime(raw_text, fmt)
            parsed_date = dt.strftime("%Y-%m-%d")
            break
        except ValueError:
            continue

    if not parsed_date:
        await message.answer(
            "⚠️ Не удалось распознать дату.\n"
            "Пожалуйста, введите дату в формате **ДД.ММ.ГГГГ** (например: *25.11.2026*) или нажмите /cancel для отмены:",
            parse_mode="Markdown",
        )
        return

    await state.clear()
    await message.answer(f"📅 Ищу мероприятия на **{raw_text}**...", parse_mode="Markdown")
    await send_events_list(message, filter_type="custom_date", filter_value=parsed_date)


@router.message(SearchStates.waiting_for_price)
async def process_custom_price_input(message: Message, state: FSMContext):
    """Парсинг и валидация суммы от пользователя."""
    if message.text and message.text.startswith("/"):
        return

    raw_text = (message.text or "").strip().replace(" ", "").replace("₽", "").replace("руб", "")
    try:
        price_val = int(raw_text)
        if price_val < 0:
            raise ValueError
    except ValueError:
        await message.answer(
            "⚠️ Пожалуйста, введите корректное положительное число рублей (например: *800*) или нажмите /cancel для отмены:",
            parse_mode="Markdown",
        )
        return

    await state.clear()
    await message.answer(f"💰 Ищу мероприятия с билетами до **{price_val} ₽**...", parse_mode="Markdown")
    await send_events_list(message, filter_type="price", filter_value=str(price_val))
