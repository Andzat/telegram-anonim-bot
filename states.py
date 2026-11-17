from aiogram.fsm.state import State, StatesGroup

class AddShopState(StatesGroup):
    waiting_for_code = State()
    waiting_for_name = State()

class BroadcastState(StatesGroup):
    waiting_for_content = State()
    confirm = State()
