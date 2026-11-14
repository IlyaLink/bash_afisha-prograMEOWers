"""Управление подписками пользователей без сбора персональных данных (ТЗ 6.1, 6.2)."""

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from bot.api_client import api_client
from bot.keyboards.menu import get_main_menu_keyboard, get_subscription_menu_keyboard

router = Router()


@router.callback_query(F.data == "btn_subscriptions")
async def cb_subscriptions_menu(call: CallbackQuery):
    """Главный экран управления подписками."""
    text = (
        "🔔 **Управление подписками на культурные события:**\n\n"
        "Вы можете подписаться на интересующий вас город или категорию (спектакли, концерты и др.).\n"
        "При появлении новых мероприятий бот будет присылать уведомления.\n\n"
        "🔒 *Приватность: мы сохраняем только ваш Telegram ID и выбранные фильтры.*"
    )
    await call.message.edit_text(text, reply_markup=get_subscription_menu_keyboard(), parse_mode="Markdown")
    await call.answer()


@router.callback_query(F.data == "sub_add_city")
async def cb_sub_choose_city(call: CallbackQuery):
    """Выбор города для подписки."""
    cities = ["Уфа", "Стерлитамак", "Салават", "Нефтекамск", "Октябрьский", "Белорецк", "Сибай", "Туймазы"]
    buttons = []
    for i in range(0, len(cities), 2):
        row = [InlineKeyboardButton(text=f"📍 {cities[i]}", callback_data=f"do_sub_city:{cities[i]}")]
        if i + 1 < len(cities):
            row.append(InlineKeyboardButton(text=f"📍 {cities[i+1]}", callback_data=f"do_sub_city:{cities[i+1]}"))
        buttons.append(row)
    buttons.append([InlineKeyboardButton(text="« Назад", callback_data="btn_subscriptions")])

    kb = InlineKeyboardMarkup(inline_keyboard=buttons)
    await call.message.edit_text("Выберите город для оформления подписки:", reply_markup=kb)
    await call.answer()


@router.callback_query(F.data == "sub_add_cat")
async def cb_sub_choose_cat(call: CallbackQuery):
    """Выбор категории для подписки."""
    cats = ["спектакль", "концерт", "выставка", "фестиваль", "экскурсия", "кино", "другое"]
    buttons = []
    for i in range(0, len(cats), 2):
        row = [InlineKeyboardButton(text=f"🎭 {cats[i].capitalize()}", callback_data=f"do_sub_cat:{cats[i]}")]
        if i + 1 < len(cats):
            row.append(InlineKeyboardButton(text=f"🎭 {cats[i+1].capitalize()}", callback_data=f"do_sub_cat:{cats[i+1]}"))
        buttons.append(row)
    buttons.append([InlineKeyboardButton(text="« Назад", callback_data="btn_subscriptions")])

    kb = InlineKeyboardMarkup(inline_keyboard=buttons)
    await call.message.edit_text("Выберите категорию для оформления подписки:", reply_markup=kb)
    await call.answer()


@router.callback_query(F.data.startswith("do_sub_city:"))
async def cb_do_sub_city(call: CallbackQuery):
    """Сохранение подписки на город."""
    city = call.data.split(":", 1)[1]
    try:
        await api_client.create_subscription(telegram_id=str(call.from_user.id), city=city)
        text = f"✅ Вы успешно подписались на культурные события в городе **{city}**!"
    except Exception as e:
        text = f"⚠️ Не удалось оформить подписку: {str(e)}"

    await call.message.answer(text, reply_markup=get_subscription_menu_keyboard(), parse_mode="Markdown")
    await call.answer()


@router.callback_query(F.data.startswith("do_sub_cat:"))
async def cb_do_sub_cat(call: CallbackQuery):
    """Сохранение подписки на категорию."""
    cat = call.data.split(":", 1)[1]
    try:
        await api_client.create_subscription(telegram_id=str(call.from_user.id), category=cat)
        text = f"✅ Вы успешно подписались на события в категории **{cat.capitalize()}**!"
    except Exception as e:
        text = f"⚠️ Не удалось оформить подписку: {str(e)}"

    await call.message.answer(text, reply_markup=get_subscription_menu_keyboard(), parse_mode="Markdown")
    await call.answer()


@router.callback_query(F.data == "sub_list")
async def cb_list_subscriptions(call: CallbackQuery):
    """Просмотр активных подписок с возможностью точечного удаления."""
    try:
        subs = await api_client.get_user_subscriptions(str(call.from_user.id))
    except Exception as e:
        await call.message.answer(f"⚠️ Ошибка при получении подписок: {str(e)}")
        await call.answer()
        return

    if not subs:
        text = "📭 У вас пока нет активных подписок."
        kb = get_subscription_menu_keyboard()
    else:
        text = "📋 **Ваши активные подписки:**\n\n"
        buttons = []
        for idx, s in enumerate(subs, 1):
            details = []
            if s.get("city"):
                details.append(f"город: {s['city']}")
            if s.get("category"):
                details.append(f"категория: {s['category']}")
            line_desc = ", ".join(details) or "все события"
            text += f"{idx}. {line_desc}\n"
            buttons.append([InlineKeyboardButton(text=f"❌ Удалить #{idx} ({line_desc})", callback_data=f"del_sub:{s['id']}")])

        buttons.append([InlineKeyboardButton(text="🔕 Отписаться от всех", callback_data="sub_unsubscribe_all")])
        buttons.append([InlineKeyboardButton(text="« Назад в меню подписок", callback_data="btn_subscriptions")])
        kb = InlineKeyboardMarkup(inline_keyboard=buttons)

    await call.message.answer(text, reply_markup=kb, parse_mode="Markdown")
    await call.answer()


@router.callback_query(F.data.startswith("del_sub:"))
async def cb_delete_single_subscription(call: CallbackQuery):
    """Удаление одной конкретной подписки."""
    sub_id = call.data.split(":", 1)[1]
    try:
        await api_client.delete_subscription(sub_id)
        text = "🗑 Подписка успешно удалена."
    except Exception as e:
        text = f"⚠️ Ошибка при удалении подписки: {str(e)}"

    await call.message.answer(text, reply_markup=get_subscription_menu_keyboard())
    await call.answer()


@router.message(Command("unsubscribe"))
@router.callback_query(F.data == "sub_unsubscribe_all")
async def cmd_unsubscribe_all(event: Message | CallbackQuery):
    """Отписка от всех уведомлений одной командой/кнопкой (ТЗ 6.2)."""
    user_id = str(event.from_user.id)
    try:
        await api_client.unsubscribe_all(user_id)
        text = "🔕 **Вы успешно отписались от всех культурных уведомлений.**\nПодписки удалены."
    except Exception as e:
        text = f"⚠️ Не удалось отписаться: {str(e)}"

    kb = get_main_menu_keyboard()
    if isinstance(event, CallbackQuery):
        await event.message.answer(text, reply_markup=kb, parse_mode="Markdown")
        await event.answer()
    else:
        await event.answer(text, reply_markup=kb, parse_mode="Markdown")
