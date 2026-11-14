"""Клавиатуры пагинации и карточки события."""

from typing import Optional
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from bot.config import bot_settings


def get_event_card_keyboard(
    event_id: str,
    org_link: Optional[str] = None,
    source_url: Optional[str] = None,
) -> InlineKeyboardMarkup:
    """Кнопки под карточкой события."""
    buttons = []

    # Кнопка билетов или первоисточника
    target_link = org_link or source_url
    if target_link and not any(h in target_link for h in ("localhost", "127.0.0.1", "web:")) and target_link.startswith(("http://", "https://")):
        buttons.append([InlineKeyboardButton(text="🎟 Купить билет / Источник ↗", url=target_link)])

    # Постоянная ссылка на карточку на нашем сайте (Telegram API отклоняет URL с localhost / 127.0.0.1)
    web_url = f"{bot_settings.PUBLIC_BASE_URL}/events/{event_id}"
    if not any(h in web_url for h in ("localhost", "127.0.0.1", "web:")) and web_url.startswith(("http://", "https://")):
        buttons.append([InlineKeyboardButton(text="🌐 Открыть на сайте", url=web_url)])
    else:
        buttons.append([InlineKeyboardButton(text="🌐 Карточка события (сайт)", callback_data=f"event_info:{event_id[:8]}")])

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_pagination_keyboard(
    page: int,
    has_next: bool,
    filter_type: str,
    filter_value: str = "",
) -> InlineKeyboardMarkup:
    """Клавиатура пагинации ('Показать ещё')."""
    buttons = []
    nav_row = []

    if has_next:
        # callback_data: more:filter_type:filter_val:next_page
        cb = f"more:{filter_type}:{filter_value}:{page + 1}"
        nav_row.append(InlineKeyboardButton(text="Показать ещё ⏩", callback_data=cb))

    if nav_row:
        buttons.append(nav_row)

    # Кнопка для нового поиска без возврата в /start (ТЗ 6.2)
    buttons.append([
        InlineKeyboardButton(text="🔍 Новый поиск", callback_data="btn_search"),
        InlineKeyboardButton(text="« Главное меню", callback_data="to_main_menu"),
    ])

    return InlineKeyboardMarkup(inline_keyboard=buttons)
