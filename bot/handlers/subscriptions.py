"""Управление подписками пользователей (ТЗ 6.2)."""

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from bot.api_client import api_client
from bot.keyboards.menu import get_main_menu_keyboard, get_subscription_menu_keyboard

router = Router()


@router.callback_query(F.data == "btn_subscriptions")
async def cb_subscriptions_menu(call: CallbackQuery):
    text = (
        "🔔 **Управление подписками на афишу:**\n\n"
        "Вы можете подписаться на интересные вам города или категории, чтобы первыми узнавать о новых событиях.\n"
        "Отписаться можно в любой момент одной кнопкой."
    )
    await call.message.edit_text(text, reply_markup=get_subscription_menu_keyboard(), parse_mode="Markdown")
    await call.answer()


@router.callback_query(F.data == "sub_add_city")
async def cb_sub_choose_city(call: CallbackQuery):
    cities = ["Уфа", "Стерлитамак", "Салават", "Нефтекамск", "Октябрьский", "Сибай"]
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=f"📍 {c}", callback_data=f"do_sub_city:{c}")]
            for c in cities
        ] + [[InlineKeyboardButton(text="« Назад", callback_data="btn_subscriptions")]]
    )
    await call.message.edit_text("Выберите город для подписки:", reply_markup=kb)
    await call.answer()


@router.callback_query(F.data == "sub_add_cat")
async def cb_sub_choose_cat(call: CallbackQuery):
    cats = ["спектакль", "концерт", "выставка", "фестиваль", "экскурсия", "кино"]
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=f"🎭 {c.capitalize()}", callback_data=f"do_sub_cat:{c}")]
            for c in cats
        ] + [[InlineKeyboardButton(text="« Назад", callback_data="btn_subscriptions")]]
    )
    await call.message.edit_text("Выберите категорию для подписки:", reply_markup=kb)
    await call.answer()


@router.callback_query(F.data.startswith("do_sub_city:"))
async def cb_do_sub_city(call: CallbackQuery):
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
    try:
        subs = await api_client.get_user_subscriptions(str(call.from_user.id))
    except Exception as e:
        await call.message.answer(f"⚠️ Ошибка при получении подписок: {str(e)}")
        await call.answer()
        return

    if not subs:
        text = "📭 У вас пока нет активных подписок."
    else:
        text = "📋 **Ваши активные подписки:**\n\n"
        for idx, s in enumerate(subs, 1):
            details = []
            if s.get("city"):
                details.append(f"город: {s['city']}")
            if s.get("category"):
                details.append(f"категория: {s['category']}")
            text += f"{idx}. {', '.join(details)}\n"

    await call.message.answer(text, reply_markup=get_subscription_menu_keyboard(), parse_mode="Markdown")
    await call.answer()


@router.message(Command("unsubscribe"))
@router.callback_query(F.data == "sub_unsubscribe_all")
async def cmd_unsubscribe_all(event: Message | CallbackQuery):
    """Отписка от всех уведомлений одной командой (ТЗ 6.2)."""
    user_id = str(event.from_user.id)
    try:
        await api_client.unsubscribe_all(user_id)
        text = "🔕 **Вы успешно отписались от всех культурных уведомлений.**"
    except Exception as e:
        text = f"⚠️ Не удалось отписаться: {str(e)}"

    kb = get_main_menu_keyboard()
    if isinstance(event, CallbackQuery):
        await event.message.answer(text, reply_markup=kb, parse_mode="Markdown")
        await event.answer()
    else:
        await event.answer(text, reply_markup=kb, parse_mode="Markdown")
