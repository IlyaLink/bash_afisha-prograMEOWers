"""Инлайн-клавиатуры главного меню и фильтров."""

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def get_main_menu_keyboard() -> InlineKeyboardMarkup:
    """Главное меню (компактное, ТЗ 6.2)."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🔍 Найти событие", callback_data="btn_search"),
                InlineKeyboardButton(text="🎟 Бесплатные", callback_data="filter_free"),
            ],
            [
                InlineKeyboardButton(text="📅 Сегодня", callback_data="period_today"),
                InlineKeyboardButton(text="🗓 В эти выходные", callback_data="period_weekend"),
            ],
            [
                InlineKeyboardButton(text="🎭 Категории", callback_data="btn_categories"),
                InlineKeyboardButton(text="📍 Города", callback_data="btn_cities"),
            ],
            [
                InlineKeyboardButton(text="🔔 Мои подписки", callback_data="btn_subscriptions"),
                InlineKeyboardButton(text="ℹ️ О сервисе", callback_data="btn_help"),
            ],
        ]
    )


def get_categories_keyboard() -> InlineKeyboardMarkup:
    """Выбор категории."""
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
                InlineKeyboardButton(text="« Назад в меню", callback_data="to_main_menu"),
            ],
        ]
    )


def get_cities_keyboard() -> InlineKeyboardMarkup:
    """Выбор ключевых городов Башкортостана."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="Уфа", callback_data="city_Уфа"),
                InlineKeyboardButton(text="Стерлитамак", callback_data="city_Стерлитамак"),
            ],
            [
                InlineKeyboardButton(text="Салават", callback_data="city_Салават"),
                InlineKeyboardButton(text="Нефтекамск", callback_data="city_Нефтекамск"),
            ],
            [
                InlineKeyboardButton(text="Октябрьский", callback_data="city_Октябрьский"),
                InlineKeyboardButton(text="Сибай", callback_data="city_Сибай"),
            ],
            [
                InlineKeyboardButton(text="« Назад в меню", callback_data="to_main_menu"),
            ],
        ]
    )


def get_subscription_menu_keyboard() -> InlineKeyboardMarkup:
    """Меню управления подписками."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="➕ Подписаться на город", callback_data="sub_add_city"),
                InlineKeyboardButton(text="➕ На категорию", callback_data="sub_add_cat"),
            ],
            [
                InlineKeyboardButton(text="📋 Список моих подписок", callback_data="sub_list"),
                InlineKeyboardButton(text="❌ Отписаться от всех", callback_data="sub_unsubscribe_all"),
            ],
            [
                InlineKeyboardButton(text="« Назад в меню", callback_data="to_main_menu"),
            ],
        ]
    )
