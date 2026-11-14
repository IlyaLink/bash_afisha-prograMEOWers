"""Обработчики каталога, кнопок фильтрации и пагинации."""

from datetime import datetime
from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from bot.api_client import api_client
from bot.keyboards.menu import (
    get_categories_keyboard,
    get_cities_keyboard,
    get_main_menu_keyboard,
)
from bot.keyboards.pagination import get_event_card_keyboard, get_pagination_keyboard
from bot.states.search import SearchStates

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
        price_text = "Вход свободный / Уточняется"

    language = e.get("language")
    lang_badge = " (на башкирском языке)" if language == "башкирский" else ""

    desc = e.get("description", "")
    if len(desc) > 200:
        desc = desc[:200] + "..."

    msg = (
        f"🎭 **{title}** [{age_limit}+]{lang_badge}\n"
        f"🏷 Категория: {category}\n"
        f"📅 Дата: **{date_formatted}**\n"
        f"📍 Место: **{city}**, {venue}\n"
        f"🏠 Адрес: {address}\n"
        f"🎟 Стоимость: **{price_text}**\n\n"
        f"{desc}"
    )
    return msg


async def send_events_list(
    message: Message,
    filter_type: str,
    filter_value: str = "",
    page: int = 1,
    size: int = 3,
):
    """Универсальная отправка порции событий с кнопками и пагинацией."""
    params = {"page": page, "size": size}
    if filter_type == "city":
        params["city"] = filter_value
    elif filter_type == "category":
        params["category"] = filter_value
    elif filter_type == "period":
        params["period"] = filter_value
    elif filter_type == "free":
        params["is_free"] = True
    elif filter_type == "q":
        params["q"] = filter_value

    try:
        data = await api_client.get_events(**params)
        events = data.get("items", [])
        meta = data.get("meta", {})
    except Exception as err:
        await message.answer(f"⚠️ Не удалось загрузить события с сервера: {str(err)}")
        return

    if not events:
        await message.answer(
            f"🔍 По выбранным параметрам мероприятий не найдено.\n"
            f"Попробуйте изменить город, период или воспользоваться поиском по названию.",
            reply_markup=get_main_menu_keyboard(),
        )
        return

    # Отправляем карточки
    for ev in events:
        card_text = format_event_message(ev)
        kb = get_event_card_keyboard(ev["id"], ev.get("org_link"), ev.get("source_url"))
        await message.answer(card_text, reply_markup=kb, parse_mode="Markdown")

    # Пагинация «Показать ещё ⏩»
    pag_kb = get_pagination_keyboard(
        page=page,
        has_next=meta.get("has_next", False),
        filter_type=filter_type,
        filter_value=filter_value,
    )
    total = meta.get("total", len(events))
    showing = min(page * size, total)
    await message.answer(
        f"Показано {showing} из {total} мероприятий.",
        reply_markup=pag_kb,
    )


# --- Кнопки выбора категорий и городов ---

@router.callback_query(F.data == "btn_categories")
async def cb_show_categories(call: CallbackQuery):
    await call.message.edit_text("Выберите категорию мероприятий:", reply_markup=get_categories_keyboard())
    await call.answer()


@router.callback_query(F.data == "btn_cities")
async def cb_show_cities(call: CallbackQuery):
    await call.message.edit_text("Выберите город Республики Башкортостан:", reply_markup=get_cities_keyboard())
    await call.answer()


@router.callback_query(F.data == "btn_search")
async def cb_start_search(call: CallbackQuery, state: FSMContext):
    await state.set_state(SearchStates.waiting_for_query)
    await call.message.answer("🔍 Введите название спектакля, концерта, артиста или площадки для поиска:")
    await call.answer()


# --- Быстрые фильтры периодов и цен ---

@router.callback_query(F.data == "period_today")
async def cb_filter_today(call: CallbackQuery):
    await call.answer("Загрузка афиши на сегодня...")
    await send_events_list(call.message, filter_type="period", filter_value="today")


@router.callback_query(F.data == "period_weekend")
async def cb_filter_weekend(call: CallbackQuery):
    await call.answer("Загрузка афиши на выходные...")
    await send_events_list(call.message, filter_type="period", filter_value="weekend")


@router.callback_query(F.data == "filter_free")
async def cb_filter_free(call: CallbackQuery):
    await call.answer("Загрузка бесплатных мероприятий...")
    await send_events_list(call.message, filter_type="free")


@router.callback_query(F.data.startswith("cat_"))
async def cb_filter_by_cat(call: CallbackQuery):
    cat = call.data.replace("cat_", "")
    await call.answer(f"Категория: {cat}")
    await send_events_list(call.message, filter_type="category", filter_value=cat)


@router.callback_query(F.data.startswith("city_"))
async def cb_filter_by_city(call: CallbackQuery):
    city = call.data.replace("city_", "")
    await call.answer(f"Город: {city}")
    await send_events_list(call.message, filter_type="city", filter_value=city)


# --- Пагинация: Показать ещё ⏩ ---

@router.callback_query(F.data.startswith("more:"))
async def cb_pagination_more(call: CallbackQuery):
    # more:filter_type:filter_val:next_page
    _, f_type, f_val, next_page = call.data.split(":", 3)
    await call.answer("Загрузка следующей страницы...")
    await send_events_list(
        call.message,
        filter_type=f_type,
        filter_value=f_val,
        page=int(next_page),
    )
