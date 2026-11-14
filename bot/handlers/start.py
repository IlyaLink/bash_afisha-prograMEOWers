"""Обработчики команд /start, /help, /cancel."""

from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from bot.keyboards.menu import get_main_menu_keyboard

router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    """Приветствие и главное меню на инлайн-кнопках без 'простыни' текста (ТЗ 6.2)."""
    await state.clear()
    text = (
        "👋 **Добро пожаловать в Афишу культуры Башкортостана!**\n\n"
        "Здесь собраны актуальные спектакли, концерты, выставки и детские мероприятия республики.\n\n"
        "Выберите раздел кнопками ниже или просто **напишите название** (например: *«Лебединое озеро»* или *«джаз»*):"
    )
    await message.answer(text, reply_markup=get_main_menu_keyboard(), parse_mode="Markdown")


@router.message(Command("help"))
@router.callback_query(F.data == "btn_help")
async def cmd_help(event: Message | CallbackQuery):
    """Справка по сервису."""
    text = (
        "ℹ️ **Как пользоваться ботом «Афиша культуры Башкортостана»:**\n\n"
        "• **Свободный поиск:** напишите любое слово в чат (название театра, артиста, город) — бот сразу найдет подходящие события.\n"
        "• **Быстрые кнопки:** выбирайте мероприятия на сегодня, выходные или только бесплатные.\n"
        "• **Подписки:** оформите подписку на любимый город или категорию и будьте в курсе новинок.\n"
        "• **Отмена операции:** команда /cancel в любой момент возвращает в меню.\n\n"
        "📌 *Сервис является независимым агрегатором культурных событий РБ.*"
    )
    kb = get_main_menu_keyboard()
    if isinstance(event, CallbackQuery):
        await event.message.edit_text(text, reply_markup=kb, parse_mode="Markdown")
        await event.answer()
    else:
        await event.answer(text, reply_markup=kb, parse_mode="Markdown")


@router.message(Command("cancel"))
async def cmd_cancel(message: Message, state: FSMContext):
    """Сброс FSM состояния."""
    await state.clear()
    await message.answer("Действие отменено. Вы в главном меню:", reply_markup=get_main_menu_keyboard())


@router.callback_query(F.data == "to_main_menu")
async def cb_to_main_menu(call: CallbackQuery, state: FSMContext):
    """Возврат в главное меню."""
    await state.clear()
    text = "Главное меню «Афиша культуры Башкортостана»:\nВыберите раздел или введите поисковый запрос:"
    await call.message.edit_text(text, reply_markup=get_main_menu_keyboard())
    await call.answer()
