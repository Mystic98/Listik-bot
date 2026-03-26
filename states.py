from aiogram.fsm.state import State, StatesGroup


class AddProductStates(StatesGroup):
    waiting_for_name = State()
    waiting_for_unit = State()
    waiting_for_amount = State()


class EditProductStates(StatesGroup):
    waiting_for_unit = State()
    waiting_for_amount = State()


class TemplateStates(StatesGroup):
    waiting_for_name = State()
    waiting_for_product_name = State()
    waiting_for_product_unit = State()
    waiting_for_product_amount = State()
    waiting_for_rename = State()
