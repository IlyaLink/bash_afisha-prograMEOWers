"""FSM-состояния для поиска и фильтрации в Telegram-боте."""

from aiogram.fsm.state import State, StatesGroup


class SearchStates(StatesGroup):
    """Состояния ожидания ввода пользователя."""

    waiting_for_query = State()  # Поиск по ключевому слову / названию
    waiting_for_date = State()   # Ввод конкретной даты (ДД.ММ.ГГГГ)
    waiting_for_price = State()  # Ввод максимальной цены билета
