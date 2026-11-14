"""Инлайн-клавиатуры главного меню и фильтров Telegram-бота (ТЗ 6.2)."""

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def get_main_menu_keyboard() -> InlineKeyboardMarkup:
    """Главное меню (компактное, без лишнего визуального шума)."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🔍 Найти событие", callback_data="btn_search"),
                InlineKeyboardButton(text="🎟 По цене / Бесплатно", callback_data="btn_price_menu"),
            ],
            [
                InlineKeyboardButton(text="📅 По дате", callback_data="btn_dates_menu"),
                InlineKeyboardButton(text="🎭 Категории", callback_data="btn_categories"),
            ],
            [
                InlineKeyboardButton(text="📍 Города", callback_data="btn_cities"),
                InlineKeyboardButton(text="🔔 Подписки", callback_data="btn_subscriptions"),
            ],
            [
                InlineKeyboardButton(text="ℹ️ Помощь и о сервисе", callback_data="btn_help"),
            ],
        ]
    )


def get_dates_keyboard() -> InlineKeyboardMarkup:
    """Выбор периода или конкретной даты (ТЗ 6.2)."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="📅 Сегодня", callback_data="period_today"),
                InlineKeyboardButton(text="📅 Завтра", callback_data="period_tomorrow"),
            ],
            [
                InlineKeyboardButton(text="🗓 В эти выходные", callback_data="period_weekend"),
                InlineKeyboardButton(text="🗓 На этой неделе", callback_data="period_week"),
            ],
            [
                InlineKeyboardButton(text="📆 Ввести конкретную дату", callback_data="period_custom"),
            ],
            [
                InlineKeyboardButton(text="« Назад в главное меню", callback_data="to_main_menu"),
            ],
        ]
    )


def get_price_keyboard() -> InlineKeyboardMarkup:
    """Выбор фильтрации по цене (ТЗ 6.2)."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🎟 Только бесплатные", callback_data="filter_free"),
                InlineKeyboardButton(text="💰 До 500 ₽", callback_data="price_500"),
            ],
            [
                InlineKeyboardButton(text="💰 До 1 000 ₽", callback_data="price_1000"),
                InlineKeyboardButton(text="💰 До 2 000 ₽", callback_data="price_2000"),
            ],
            [
                InlineKeyboardButton(text="✏️ Указать свою сумму", callback_data="price_custom"),
            ],
            [
                InlineKeyboardButton(text="« Назад в главное меню", callback_data="to_main_menu"),
            ],
        ]
    )


def get_categories_keyboard() -> InlineKeyboardMarkup:
    """Выбор категории культурного события."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🎭 Спектакли", callback_data="cat_спектакль"),
                InlineKeyboardButton(text="🎵 Концерты", callback_data="cat_концерт"),
            ],
            [
                InlineKeyboardButton(text="🎨 Выставки", callback_data="cat_выставка"),
                InlineKeyboardButton(text="🎪 Фестивали", callback_data="cat_фестиваль"),
            ],
            [
                InlineKeyboardButton(text="🏛 Экскурсии", callback_data="cat_экскурсия"),
                InlineKeyboardButton(text="🎬 Кино", callback_data="cat_кино"),
            ],
            [
                InlineKeyboardButton(text="🎟 Другое", callback_data="cat_другое"),
                InlineKeyboardButton(text="« Назад в меню", callback_data="to_main_menu"),
            ],
        ]
    )


def get_cities_keyboard() -> InlineKeyboardMarkup:
    """Выбор ключевых городов и населённых пунктов Башкортостана."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="📍 Уфа", callback_data="city_Уфа"),
                InlineKeyboardButton(text="📍 Стерлитамак", callback_data="city_Стерлитамак"),
            ],
            [
                InlineKeyboardButton(text="📍 Салават", callback_data="city_Салават"),
                InlineKeyboardButton(text="📍 Нефтекамск", callback_data="city_Нефтекамск"),
            ],
            [
                InlineKeyboardButton(text="📍 Октябрьский", callback_data="city_Октябрьский"),
                InlineKeyboardButton(text="📍 Белорецк", callback_data="city_Белорецк"),
            ],
            [
                InlineKeyboardButton(text="📍 Сибай", callback_data="city_Сибай"),
                InlineKeyboardButton(text="📍 Туймазы", callback_data="city_Туймазы"),
            ],
            [
                InlineKeyboardButton(text="📍 Ишимбай", callback_data="city_Ишимбай"),
                InlineKeyboardButton(text="📍 Кумертау", callback_data="city_Кумертау"),
            ],
            [
                InlineKeyboardButton(text="« Назад в меню", callback_data="to_main_menu"),
            ],
        ]
    )


def get_subscription_menu_keyboard() -> InlineKeyboardMarkup:
    """Меню управления подписками (ТЗ 6.2)."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="➕ Подписаться на город", callback_data="sub_add_city"),
                InlineKeyboardButton(text="➕ На категорию", callback_data="sub_add_cat"),
            ],
            [
                InlineKeyboardButton(text="📋 Мои активные подписки", callback_data="sub_list"),
                InlineKeyboardButton(text="🔕 Отписаться от всех", callback_data="sub_unsubscribe_all"),
            ],
            [
                InlineKeyboardButton(text="« Назад в меню", callback_data="to_main_menu"),
            ],
        ]
    )
