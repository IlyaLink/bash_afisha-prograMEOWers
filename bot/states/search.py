"""FSM состояния Telegram-бота."""

from aiogram.fsm.state import State, StatesGroup


class SearchStates(StatesGroup):
    waiting_for_query = State()


class SubscriptionStates(StatesGroup):
    waiting_for_city = State()
    waiting_for_category = State()
