from aiogram import Router, F, types
from aiogram.filters import Command, StateFilter
from aiogram.types import (
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    ReplyKeyboardMarkup,
    KeyboardButton,
)
from aiogram.fsm.context import FSMContext

from config import settings
from database import (
    get_db,
    add_user,
    get_user_by_telegram_id,
    get_user_by_username,
    is_user_allowed,
    remove_user,
    get_all_users,
    add_item,
    get_pending_items,
    mark_as_purchased,
    unmark_purchased,
    remove_item,
    clear_purchased_items,
    get_item_by_id,
    find_pending_item_by_name,
    update_item_quantity,
    get_all_items_ordered,
    add_pending_user,
    approve_user,
    reject_user,
    get_pending_users,
    get_user_by_username_all,
    find_pending_item_in_unit_group,
    create_template,
    get_all_templates,
    get_template_by_id,
    delete_template,
    rename_template,
    add_item_to_template,
    get_template_items,
    get_template_item_by_id,
    remove_template_item,
    update_template_item,
    create_template_from_items,
    find_template_item_in_unit_group,
    update_item_category,
    update_template_item_category,
    save_product_category,
    get_product_category,
    get_all_product_categories,
    get_pending_items_ordered,
    get_template_items_ordered,
)
from utils import (
    format_item,
    combine_quantities,
    get_unit_group,
    extract_unit,
    extract_quantity_parts,
)
from states import AddProductStates, EditProductStates, TemplateStates
from categories import (
    categorize_product,
    get_category_name,
    get_category_emoji,
    get_sorted_categories,
    get_all_categories,
)

router = Router()


async def delete_user_message(message: types.Message):
    try:
        await message.delete()
    except:
        pass


def build_category_keyboard(
    item_id: int, current_category: str, prefix: str = "cat"
) -> InlineKeyboardMarkup:
    keyboard = []
    sorted_cats = get_sorted_categories()
    all_cats = get_all_categories()

    row = []
    for cat_id in sorted_cats:
        if cat_id == "other":
            continue
        cat_name = all_cats[cat_id]["name"]
        marker = "✓ " if cat_id == current_category else ""
        row.append(
            InlineKeyboardButton(
                text=f"{marker}{cat_name}",
                callback_data=f"{prefix}_{item_id}_{cat_id}",
            )
        )
        if len(row) == 2:
            keyboard.append(row)
            row = []

    if row:
        keyboard.append(row)

    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_user_display_name(user: types.User) -> str:
    if user.username:
        return f"@{user.username}"
    return user.full_name or str(user.id)


def get_main_keyboard() -> ReplyKeyboardMarkup:
    keyboard = [
        [KeyboardButton(text="📋 Список"), KeyboardButton(text="📋 Шаблоны")],
        [KeyboardButton(text="❓ Помощь")],
    ]
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)


def get_cancel_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="❌ Отмена")]], resize_keyboard=True
    )


def get_unit_keyboard() -> ReplyKeyboardMarkup:
    keyboard = [
        [
            KeyboardButton(text="кг"),
            KeyboardButton(text="г"),
            KeyboardButton(text="шт"),
        ],
        [
            KeyboardButton(text="л"),
            KeyboardButton(text="мл"),
            KeyboardButton(text="уп"),
        ],
        [KeyboardButton(text="⏭ Без меры"), KeyboardButton(text="❌ Отмена")],
    ]
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)


def get_amount_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="❌ Отмена")]], resize_keyboard=True
    )


def get_list_menu_keyboard() -> ReplyKeyboardMarkup:
    keyboard = [
        [
            KeyboardButton(text="➕ Добавить товар"),
            KeyboardButton(text="➕ Добавить из шаблона"),
        ],
        [KeyboardButton(text="📋 Создать шаблон из списка")],
        [KeyboardButton(text="🗑 Очистить купленные")],
        [KeyboardButton(text="◀️ Назад")],
    ]
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)


def get_templates_menu_keyboard() -> ReplyKeyboardMarkup:
    keyboard = [
        [KeyboardButton(text="➕ Новый шаблон"), KeyboardButton(text="📥 Из списка")],
        [KeyboardButton(text="◀️ Назад")],
    ]
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)


def get_template_manage_keyboard() -> ReplyKeyboardMarkup:
    keyboard = [
        [
            KeyboardButton(text="➕ Добавить в шаблон"),
            KeyboardButton(text="🗑 Удалить шаблон"),
        ],
        [KeyboardButton(text="◀️ Назад")],
    ]
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)


async def check_access(user_id: int) -> bool:
    if user_id == settings.admin_id:
        return True
    async with get_db() as db:
        return await is_user_allowed(db, user_id)


async def build_list_message(db) -> tuple:
    items = await get_all_items_ordered(db)

    if not items:
        return "📋 Список покупок пуст.", None

    text = "📋 Список покупок:\n"
    keyboard = []

    current_category = None
    counter = 0

    for item in items:
        if item.is_purchased:
            continue

        counter += 1
        item_category = item.category

        if item_category != current_category:
            text += f"\n{get_category_name(item_category)}\n"
            current_category = item_category

        item_text = format_item(item.name, item.quantity)
        adder = item.added_by_name or "Неизвестно"
        text += f"{counter}. {item_text} (добавил: {adder})\n"
        keyboard.append(
            [
                InlineKeyboardButton(
                    text=f"✅ {counter}", callback_data=f"purchase_{item.id}"
                ),
                InlineKeyboardButton(
                    text=f"✏️ {counter}", callback_data=f"edit_{item.id}"
                ),
                InlineKeyboardButton(
                    text=f"🗑 {counter}", callback_data=f"remove_{item.id}"
                ),
            ]
        )

    purchased_items = [item for item in items if item.is_purchased]
    for item in purchased_items:
        counter += 1
        item_text = format_item(item.name, item.quantity)
        purchaser = item.purchased_by_name or "Неизвестно"
        text += f"\n✅ {counter}. {item_text} (купил: {purchaser})\n"
        keyboard.append(
            [
                InlineKeyboardButton(
                    text=f"↩️ {counter}", callback_data=f"undo_{item.id}"
                ),
                InlineKeyboardButton(
                    text=f"🗑 {counter}", callback_data=f"remove_{item.id}"
                ),
            ]
        )

    text += "\n👇 Нажмите кнопку под продуктом"

    return text, InlineKeyboardMarkup(inline_keyboard=keyboard)


async def build_pending_message(db) -> tuple:
    users = await get_pending_users(db)

    if not users:
        return "📋 Нет ожидающих подтверждения пользователей.", None

    text = f"📋 Ожидающие подтверждения ({len(users)}):\n\n"
    keyboard = []

    for i, u in enumerate(users, 1):
        display = f"@{u.username}" if u.username else u.full_name
        text += f"{i}. {display}\n"
        keyboard.append(
            [
                InlineKeyboardButton(
                    text=f"✅ {i}", callback_data=f"approve_{u.telegram_id}"
                ),
                InlineKeyboardButton(
                    text=f"❌ {i}", callback_data=f"reject_{u.telegram_id}"
                ),
            ]
        )

    text += "\n👇 Нажмите кнопку для действия"

    return text, InlineKeyboardMarkup(inline_keyboard=keyboard)


@router.message(Command("start"))
async def cmd_start(message: types.Message):
    user = message.from_user
    user_display = get_user_display_name(user)

    if user.id == settings.admin_id:
        async with get_db() as db:
            existing = await get_user_by_telegram_id(db, user.id)
            if not existing:
                await add_user(
                    db, user.id, user.username, user.full_name, user.id, approved=True
                )
            elif not existing.is_approved:
                await approve_user(db, user.id)

        await message.answer(
            f"👋 Добро пожаловать, {user_display}!\n\n"
            "Вы администратор бота.\n\n"
            "📋 Доступные команды:\n"
            "/add <продукт> — добавить продукт\n"
            "/list — показать список\n"
            "/done <N> — отметить купленным\n"
            "/undo <N> — вернуть в список\n"
            "/remove <N> — удалить\n"
            "/clear — удалить все купленные\n\n"
            "👤 Администрирование:\n"
            "/allow @username — добавить пользователя\n"
            "/pending — список ожидающих подтверждения\n"
            "/deny @username — удалить пользователя\n"
            "/users — список пользователей",
            reply_markup=get_main_keyboard(),
        )
        return

    async with get_db() as db:
        existing = await get_user_by_telegram_id(db, user.id)

        if existing:
            if existing.is_approved:
                await message.answer(
                    f"👋 Привет, {user_display}!\n\n"
                    "📋 Доступные команды:\n"
                    "/add <продукт> — добавить продукт\n"
                    "/list — показать список\n"
                    "/done <N> — отметить купленным\n"
                    "/undo <N> — вернуть в список\n"
                    "/remove <N> — удалить\n"
                    "/clear — удалить все купленные",
                    reply_markup=get_main_keyboard(),
                )
            else:
                await message.answer(
                    f"👋 Привет, {user_display}!\n\n"
                    "📝 Ваш запрос на доступ отправлен администратору.\n"
                    "⏳ Ожидайте подтверждения."
                )
        else:
            await add_pending_user(db, user.id, user.username, user.full_name)
            await message.answer(
                f"👋 Привет, {user_display}!\n\n"
                "📝 Ваш запрос на доступ отправлен администратору.\n"
                "⏳ Ожидайте подтверждения.\n\n"
                "После одобрения вы сможете использовать все функции бота."
            )


@router.message(Command("help"))
async def cmd_help(message: types.Message):
    await cmd_start(message)


@router.message(F.text == "❓ Помощь")
async def btn_help(message: types.Message):
    await delete_user_message(message)
    await cmd_start(message)


@router.message(F.text == "➕ Добавить товар")
async def btn_add_item(message: types.Message, state: FSMContext):
    await delete_user_message(message)
    if not await check_access(message.from_user.id):
        await message.answer("⛔ Доступ запрещён.")
        return

    await state.set_state(AddProductStates.waiting_for_name)
    await message.answer(
        "Введите название продукта:", reply_markup=get_cancel_keyboard()
    )


@router.message(AddProductStates.waiting_for_name, F.text == "❌ Отмена")
async def cancel_add_name(message: types.Message, state: FSMContext):
    await delete_user_message(message)
    await state.clear()
    await message.answer(
        "❌ Добавление отменено.", reply_markup=get_list_menu_keyboard()
    )


@router.message(AddProductStates.waiting_for_name)
async def process_product_name(message: types.Message, state: FSMContext):
    if not message.text or not message.text.strip():
        await message.answer("❌ Название не может быть пустым. Попробуйте снова:")
        return

    name = message.text.strip()
    await state.update_data(product_name=name)
    await state.set_state(AddProductStates.waiting_for_unit)
    await message.answer(
        f"Продукт: {name}\n\nВыберите единицу измерения:",
        reply_markup=get_unit_keyboard(),
    )


@router.message(AddProductStates.waiting_for_unit, F.text == "❌ Отмена")
async def cancel_add_unit(message: types.Message, state: FSMContext):
    await delete_user_message(message)
    await state.clear()
    await message.answer(
        "❌ Добавление отменено.", reply_markup=get_list_menu_keyboard()
    )


@router.message(AddProductStates.waiting_for_unit, F.text == "⏭ Без меры")
async def skip_unit(message: types.Message, state: FSMContext):
    await delete_user_message(message)
    await save_product(message, state, None, None)


@router.message(AddProductStates.waiting_for_unit)
async def process_unit(message: types.Message, state: FSMContext):
    unit = message.text.strip() if message.text else None

    valid_units = ["кг", "г", "шт", "л", "мл", "уп"]
    if unit not in valid_units:
        await message.answer("❌ Выберите единицу из списка.")
        return

    await state.update_data(product_unit=unit)
    await state.set_state(AddProductStates.waiting_for_amount)
    await message.answer(
        f"Введите количество ({unit}):",
        reply_markup=get_amount_keyboard(),
    )


@router.message(AddProductStates.waiting_for_amount, F.text == "❌ Отмена")
async def cancel_add_amount(message: types.Message, state: FSMContext):
    await delete_user_message(message)
    await state.clear()
    await message.answer(
        "❌ Добавление отменено.", reply_markup=get_list_menu_keyboard()
    )


@router.message(AddProductStates.waiting_for_amount)
async def process_amount(message: types.Message, state: FSMContext):
    data = await state.get_data()
    unit = data.get("product_unit")

    if not message.text or not message.text.strip():
        await message.answer("❌ Введите число:")
        return

    try:
        amount_str = message.text.strip().replace(",", ".")
        amount = float(amount_str)
        if amount <= 0:
            await message.answer("❌ Количество должно быть больше нуля:")
            return
        if amount == int(amount):
            amount = int(amount)
    except ValueError:
        await message.answer("❌ Введите корректное число:")
        return

    await save_product(message, state, amount, unit)


async def save_product(message: types.Message, state: FSMContext, amount, unit):
    data = await state.get_data()
    name = data.get("product_name")
    list_message_id = data.get("list_message_id")
    user = message.from_user
    user_display = get_user_display_name(user)

    if amount is not None and unit:
        quantity = f"{amount}{unit}"
    else:
        quantity = None

    async with get_db() as db:
        user_categories = await get_all_product_categories(db)
        category = categorize_product(name, user_categories)

        group = get_unit_group(unit)
        if group:
            existing = await find_pending_item_in_unit_group(db, name, group)
        else:
            existing = await find_pending_item_in_unit_group(db, name, "pieces")

        if existing:
            new_quantity = combine_quantities(existing.quantity, quantity)
            if new_quantity:
                await update_item_quantity(db, existing.id, new_quantity)
                text, keyboard = await build_list_message(db)
                await state.clear()
                if list_message_id:
                    try:
                        await message.bot.edit_message_text(
                            text,
                            chat_id=message.chat.id,
                            message_id=list_message_id,
                            reply_markup=keyboard,
                        )
                    except:
                        sent = await message.answer(text, reply_markup=keyboard)
                        await state.update_data(list_message_id=sent.message_id)
                else:
                    sent = await message.answer(text, reply_markup=keyboard)
                    await state.update_data(list_message_id=sent.message_id)
                await message.answer(
                    "📋 Меню списка", reply_markup=get_list_menu_keyboard()
                )
                return

        item_id = await add_item(db, name, quantity, user.id, user_display, category)
        text, keyboard = await build_list_message(db)

    await state.clear()
    if list_message_id:
        try:
            await message.bot.edit_message_text(
                text,
                chat_id=message.chat.id,
                message_id=list_message_id,
                reply_markup=keyboard,
            )
        except:
            sent = await message.answer(text, reply_markup=keyboard)
            await state.update_data(list_message_id=sent.message_id)
    else:
        sent = await message.answer(text, reply_markup=keyboard)
        await state.update_data(list_message_id=sent.message_id)

    cat_keyboard = build_category_keyboard(item_id, category, "cat")
    await message.answer(
        f"✅ Добавлено: {format_item(name, quantity)}\n📁 {get_category_name(category)}",
        reply_markup=cat_keyboard,
    )
    await message.answer("📋 Меню списка", reply_markup=get_list_menu_keyboard())


@router.message(Command("add"))
async def cmd_add(message: types.Message, state: FSMContext):
    user = message.from_user

    if not await check_access(user.id):
        await message.answer("⛔ Доступ запрещён.")
        return

    text = message.text or ""
    parts = text.split(maxsplit=1)

    if len(parts) < 2:
        await state.set_state(AddProductStates.waiting_for_name)
        await message.answer(
            "Введите название продукта:", reply_markup=get_cancel_keyboard()
        )
        return

    product_text = parts[1]
    name, quantity = product_text.strip(), None

    if " " in product_text:
        name_part, qty_part = product_text.rsplit(" ", 1)
        if any(qty_part.endswith(u) for u in ["л", "мл", "кг", "г", "шт", "уп"]):
            name = name_part.strip()
            quantity = qty_part.strip()

    if not name:
        await message.answer("❌ Некорректное название продукта.")
        return

    user_display = get_user_display_name(user)

    async with get_db() as db:
        unit = extract_unit(quantity)
        group = get_unit_group(unit)
        if group:
            existing = await find_pending_item_in_unit_group(db, name, group)
        else:
            existing = await find_pending_item_in_unit_group(db, name, "pieces")

        if existing:
            new_quantity = combine_quantities(existing.quantity, quantity)
            if new_quantity:
                await update_item_quantity(db, existing.id, new_quantity)
                return

        await add_item(db, name, quantity, user.id, user_display)


@router.message(F.text == "📋 Список")
@router.message(Command("list"))
async def btn_list_menu(message: types.Message, state: FSMContext):
    await delete_user_message(message)
    user = message.from_user

    if not await check_access(user.id):
        await message.answer("⛔ Доступ запрещён.")
        return

    await state.clear()
    async with get_db() as db:
        text, keyboard = await build_list_message(db)

    if keyboard:
        sent = await message.answer(text, reply_markup=keyboard)
        await state.update_data(list_message_id=sent.message_id)
    else:
        await message.answer(text)
    await message.answer("📋 Меню списка", reply_markup=get_list_menu_keyboard())


@router.message(F.text == "➕ Добавить из шаблона")
async def btn_add_template_to_list(message: types.Message, state: FSMContext):
    await delete_user_message(message)
    if not await check_access(message.from_user.id):
        await message.answer("⛔ Доступ запрещён.")
        return

    async with get_db() as db:
        templates = await get_all_templates(db)

    if not templates:
        await message.answer("❌ Нет сохранённых шаблонов.")
        return

    keyboard = []
    for t in templates:
        keyboard.append(
            [
                InlineKeyboardButton(
                    text=f"📋 {t.name} ({t.item_count} товаров)",
                    callback_data=f"add_template_{t.id}",
                )
            ]
        )

    await message.answer(
        "Выберите шаблон для добавления:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard),
    )


@router.callback_query(F.data.startswith("add_template_"))
async def callback_add_template_to_list(
    callback: types.CallbackQuery, state: FSMContext
):
    template_id = int(callback.data.split("_")[2])
    user = callback.from_user
    user_display = get_user_display_name(user)

    async with get_db() as db:
        template = await get_template_by_id(db, template_id)
        template_items = await get_template_items(db, template_id)
        list_items = await get_pending_items(db)

    if not template_items:
        await callback.answer("❌ Шаблон пуст.", show_alert=True)
        return

    conflicts = []
    non_conflicts = []

    for t_item in template_items:
        t_unit = extract_quantity_parts(t_item.quantity)[1] if t_item.quantity else None
        t_group = get_unit_group(t_unit)

        conflict_found = False
        for l_item in list_items:
            l_unit = (
                extract_quantity_parts(l_item.quantity)[1] if l_item.quantity else None
            )
            l_group = get_unit_group(l_unit)

            if l_item.name.lower() == t_item.name.lower() and l_group == t_group:
                conflicts.append(
                    {
                        "template_item": t_item,
                        "list_item": l_item,
                        "group": t_group,
                    }
                )
                conflict_found = True
                break

        if not conflict_found:
            non_conflicts.append(t_item)

    if not conflicts:
        async with get_db() as db:
            for item in non_conflicts:
                await add_item(
                    db,
                    item.name,
                    item.quantity,
                    user.id,
                    user_display,
                    item.category,
                )

        await callback.message.edit_text(
            f"✅ Добавлено {len(non_conflicts)} товаров из шаблона '{template.name}'."
        )
        await callback.answer()
        return

    text = f"⚠️ Найдено конфликтов: {len(conflicts)}\n\n"
    for i, conflict in enumerate(conflicts, 1):
        t_item = conflict["template_item"]
        l_item = conflict["list_item"]
        t_text = format_item(t_item.name, t_item.quantity)
        l_text = format_item(l_item.name, l_item.quantity)

        text += f"{i}. {t_item.name}\n"
        text += f"   В списке: {l_text}\n"
        text += f"   В шаблоне: {t_text}\n\n"

    text += "Выберите действие для всех конфликтов:"

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ Заменить все", callback_data=f"replace_all_{template_id}"
                ),
                InlineKeyboardButton(
                    text="⏭ Оставить все", callback_data=f"keep_all_{template_id}"
                ),
            ],
            [
                InlineKeyboardButton(
                    text="❌ Отмена", callback_data="cancel_apply_template"
                ),
            ],
        ]
    )

    await state.update_data(
        conflicts=conflicts,
        non_conflicts=non_conflicts,
        user_display=user_display,
    )

    await callback.message.edit_text(text, reply_markup=keyboard)
    await callback.answer()


@router.message(F.text == "📋 Создать шаблон из списка")
async def btn_create_template_from_list(message: types.Message, state: FSMContext):
    await delete_user_message(message)
    if not await check_access(message.from_user.id):
        await message.answer("⛔ Доступ запрещён.")
        return

    async with get_db() as db:
        items = await get_pending_items(db)

    if not items:
        await message.answer("❌ Список покупок пуст.")
        return

    await state.update_data(template_items=items)
    await state.set_state(TemplateStates.waiting_for_name)
    await message.answer(
        f"Создать шаблон из {len(items)} товаров?\n\nВведите название шаблона:",
        reply_markup=get_cancel_keyboard(),
    )


@router.message(Command("done"))
async def cmd_done(message: types.Message):
    user = message.from_user

    if not await check_access(user.id):
        await message.answer("⛔ Доступ запрещён.")
        return

    text = message.text or ""
    parts = text.split(maxsplit=1)

    if len(parts) < 2:
        await message.answer("❌ Укажите номер.\nПример: /done 1")
        return

    try:
        number = int(parts[1])
    except ValueError:
        await message.answer("❌ Некорректный номер.")
        return

    if number < 1:
        await message.answer("❌ Номер должен быть положительным.")
        return

    user_display = get_user_display_name(user)

    async with get_db() as db:
        items = await get_pending_items(db)

        if number > len(items):
            await message.answer("❌ Продукт с таким номером не найден.")
            return

        item = items[number - 1]
        success = await mark_as_purchased(db, item.id, user.id, user_display)

    if success:
        item_text = format_item(item.name, item.quantity)
        await message.answer(f"✅ Куплено: {item_text}")
    else:
        await message.answer("❌ Не удалось отметить продукт как купленный.")


@router.message(Command("undo"))
async def cmd_undo(message: types.Message):
    user = message.from_user

    if not await check_access(user.id):
        await message.answer("⛔ Доступ запрещён.")
        return

    text = message.text or ""
    parts = text.split(maxsplit=1)

    if len(parts) < 2:
        await message.answer("❌ Укажите номер.\nПример: /undo 1")
        return

    try:
        number = int(parts[1])
    except ValueError:
        await message.answer("❌ Некорректный номер.")
        return

    if number < 1:
        await message.answer("❌ Номер должен быть положительным.")
        return

    async with get_db() as db:
        items = await get_all_items_ordered(db)

        if number > len(items):
            await message.answer("❌ Продукт с таким номером не найден.")
            return

        item = items[number - 1]
        success = await unmark_purchased(db, item.id)

    if success:
        item_text = format_item(item.name, item.quantity)
        await message.answer(f"↩️ Возвращено в список: {item_text}")
    else:
        await message.answer("❌ Не удалось вернуть продукт в список.")


@router.message(Command("remove"))
async def cmd_remove(message: types.Message):
    user = message.from_user

    if not await check_access(user.id):
        await message.answer("⛔ Доступ запрещён.")
        return

    text = message.text or ""
    parts = text.split(maxsplit=1)

    if len(parts) < 2:
        await message.answer("❌ Укажите номер.\nПример: /remove 1")
        return

    try:
        number = int(parts[1])
    except ValueError:
        await message.answer("❌ Некорректный номер.")
        return

    if number < 1:
        await message.answer("❌ Номер должен быть положительным.")
        return

    async with get_db() as db:
        items = await get_all_items_ordered(db)

        if number > len(items):
            await message.answer("❌ Продукт с таким номером не найден.")
            return

        item = items[number - 1]
        success = await remove_item(db, item.id)

    if success:
        item_text = format_item(item.name, item.quantity)
        await message.answer(f"🗑 Удалено: {item_text}")
    else:
        await message.answer("❌ Не удалось удалить продукт.")


@router.message(F.text == "🗑 Очистить купленные")
@router.message(Command("clear"))
async def cmd_clear(message: types.Message, state: FSMContext):
    await delete_user_message(message)
    user = message.from_user

    if not await check_access(user.id):
        await message.answer("⛔ Доступ запрещён.")
        return

    data = await state.get_data()
    list_message_id = data.get("list_message_id")

    async with get_db() as db:
        count = await clear_purchased_items(db)
        text, keyboard = await build_list_message(db)

    if list_message_id:
        try:
            await message.bot.edit_message_text(
                text,
                chat_id=message.chat.id,
                message_id=list_message_id,
                reply_markup=keyboard,
            )
        except:
            pass


@router.message(Command("allow"))
async def cmd_allow(message: types.Message):
    user = message.from_user

    if user.id != settings.admin_id:
        await message.answer("⛔ Только администратор может добавлять пользователей.")
        return

    if message.reply_to_message:
        replied_user = message.reply_to_message.from_user
        async with get_db() as db:
            existing = await get_user_by_telegram_id(db, replied_user.id)
            if existing:
                if existing.is_approved:
                    target_display = get_user_display_name(replied_user)
                    await message.answer(
                        f"✅ Пользователь {target_display} уже имеет доступ."
                    )
                    return
                else:
                    await approve_user(db, replied_user.id)
            else:
                await add_user(
                    db,
                    replied_user.id,
                    replied_user.username,
                    replied_user.full_name,
                    user.id,
                    approved=True,
                )

        target_display = get_user_display_name(replied_user)

        try:
            await message.bot.send_message(
                replied_user.id,
                "✅ Вам разрешён доступ к боту!\n\nНапишите /start чтобы начать.",
            )
        except:
            pass

        await message.answer(f"✅ Доступ разрешён для {target_display}.")
        return

    text = message.text or ""
    parts = text.split(maxsplit=1)

    if len(parts) < 2:
        await message.answer(
            "❌ Укажите пользователя.\n"
            "Пример: /allow @username\n"
            "Или ответьте reply на сообщение пользователя."
        )
        return

    username = parts[1].strip()
    if username.startswith("@"):
        username = username[1:]

    async with get_db() as db:
        target_user = await get_user_by_username_all(db, username)

        if not target_user:
            await message.answer(f"❌ Пользователь @{username} не найден.")
            return

        if target_user.is_approved:
            await message.answer(f"✅ Пользователь @{username} уже имеет доступ.")
            return

        await approve_user(db, target_user.telegram_id)

    try:
        await message.bot.send_message(
            target_user.telegram_id,
            "✅ Вам разрешён доступ к боту!\n\nНапишите /start чтобы начать.",
        )
    except:
        pass

    await message.answer(f"✅ Доступ разрешён для @{username}.")


@router.message(Command("pending"))
async def cmd_pending(message: types.Message):
    user = message.from_user

    if user.id != settings.admin_id:
        await message.answer("⛔ Только администратор может просматривать ожидающих.")
        return

    async with get_db() as db:
        text, keyboard = await build_pending_message(db)

    if keyboard:
        await message.answer(text, reply_markup=keyboard)
    else:
        await message.answer(text)


@router.message(Command("deny"))
async def cmd_deny(message: types.Message):
    user = message.from_user

    if user.id != settings.admin_id:
        await message.answer("⛔ Только администратор может удалять пользователей.")
        return

    text = message.text or ""
    parts = text.split(maxsplit=1)

    if len(parts) < 2:
        await message.answer("❌ Укажите пользователя.\nПример: /deny @username")
        return

    username = parts[1].strip()
    if username.startswith("@"):
        username = username[1:]

    async with get_db() as db:
        target_user = await get_user_by_username_all(db, username)

        if not target_user:
            await message.answer(f"❌ Пользователь @{username} не найден.")
            return

        success = await remove_user(db, target_user.telegram_id)

    if success:
        await message.answer(f"✅ Пользователь @{username} удалён.")
    else:
        await message.answer(f"❌ Не удалось удалить пользователя @{username}.")


@router.message(Command("users"))
async def cmd_users(message: types.Message):
    user = message.from_user

    if user.id != settings.admin_id:
        await message.answer(
            "⛔ Только администратор может просматривать список пользователей."
        )
        return

    async with get_db() as db:
        users = await get_all_users(db)

    if not users:
        await message.answer("📋 Список пользователей пуст.")
        return

    text = "📋 Пользователи с доступом:\n\n"

    for u in users:
        display = f"@{u.username}" if u.username else u.full_name
        is_admin = "👑" if u.telegram_id == settings.admin_id else "👤"
        text += f"{is_admin} {display}\n"

    await message.answer(text)


@router.callback_query(F.data.startswith("cat_"))
async def callback_set_category(callback: types.CallbackQuery):
    if not await check_access(callback.from_user.id):
        await callback.answer("⛔ Доступ запрещён.", show_alert=True)
        return

    parts = callback.data.split("_")
    item_id = int(parts[1])
    category = parts[2]

    async with get_db() as db:
        item = await get_item_by_id(db, item_id)
        if not item:
            await callback.answer("❌ Товар не найден", show_alert=True)
            return

        await update_item_category(db, item_id, category)
        await save_product_category(db, item.name, category)

        cat_keyboard = build_category_keyboard(item_id, category, "cat")
        item_text = format_item(item.name, item.quantity)
        try:
            await callback.message.edit_text(
                f"✅ Добавлено: {item_text}\n📁 {get_category_name(category)}",
                reply_markup=cat_keyboard,
            )
        except:
            pass
        await callback.answer(f"Категория изменена на {get_category_name(category)}")


@router.callback_query(F.data.startswith("tcat_"))
async def callback_set_template_category(callback: types.CallbackQuery):
    if not await check_access(callback.from_user.id):
        await callback.answer("⛔ Доступ запрещён.", show_alert=True)
        return

    parts = callback.data.split("_")
    item_id = int(parts[1])
    category = parts[2]

    async with get_db() as db:
        item = await get_template_item_by_id(db, item_id)
        if not item:
            await callback.answer("❌ Товар не найден", show_alert=True)
            return

        await update_template_item_category(db, item_id, category)
        await save_product_category(db, item.name, category)

        cat_keyboard = build_category_keyboard(item_id, category, "tcat")
        item_text = format_item(item.name, item.quantity)
        try:
            await callback.message.edit_text(
                f"✅ Добавлено: {item_text}\n📁 {get_category_name(category)}",
                reply_markup=cat_keyboard,
            )
        except:
            pass
        await callback.answer(f"Категория изменена на {get_category_name(category)}")


@router.callback_query(F.data.startswith("purchase_"))
async def callback_purchase(callback: types.CallbackQuery):
    user = callback.from_user

    if not await check_access(user.id):
        await callback.answer("⛔ Доступ запрещён.", show_alert=True)
        return

    item_id = int(callback.data.split("_")[1])
    user_display = get_user_display_name(user)

    async with get_db() as db:
        success = await mark_as_purchased(db, item_id, user.id, user_display)

        if success:
            text, keyboard = await build_list_message(db)
            try:
                await callback.message.edit_text(text, reply_markup=keyboard)
            except:
                pass
            await callback.answer("✅ Отмечено как купленное")
        else:
            await callback.answer(
                "❌ Продукт уже куплен или не найден", show_alert=True
            )


@router.callback_query(F.data.startswith("undo_"))
async def callback_undo(callback: types.CallbackQuery):
    user = callback.from_user

    if not await check_access(user.id):
        await callback.answer("⛔ Доступ запрещён.", show_alert=True)
        return

    item_id = int(callback.data.split("_")[1])

    async with get_db() as db:
        success = await unmark_purchased(db, item_id)

        if success:
            text, keyboard = await build_list_message(db)
            try:
                await callback.message.edit_text(text, reply_markup=keyboard)
            except:
                pass
            await callback.answer("↩️ Возвращено в список")
        else:
            await callback.answer("❌ Продукт не куплен или не найден", show_alert=True)


@router.callback_query(F.data.startswith("remove_"))
async def callback_remove(callback: types.CallbackQuery):
    user = callback.from_user

    if not await check_access(user.id):
        await callback.answer("⛔ Доступ запрещён.", show_alert=True)
        return

    item_id = int(callback.data.split("_")[1])

    async with get_db() as db:
        success = await remove_item(db, item_id)

        if success:
            text, keyboard = await build_list_message(db)
            try:
                await callback.message.edit_text(text, reply_markup=keyboard)
            except:
                pass
            await callback.answer("🗑 Удалено")
        else:
            await callback.answer("❌ Продукт не найден", show_alert=True)


@router.callback_query(F.data.startswith("approve_"))
async def callback_approve(callback: types.CallbackQuery):
    if callback.from_user.id != settings.admin_id:
        await callback.answer(
            "⛔ Только администратор может одобрять.", show_alert=True
        )
        return

    telegram_id = int(callback.data.split("_")[1])

    async with get_db() as db:
        user = await get_user_by_telegram_id(db, telegram_id)
        if not user:
            await callback.answer("❌ Пользователь не найден", show_alert=True)
            return

        await approve_user(db, telegram_id)

    try:
        await callback.bot.send_message(
            telegram_id,
            "✅ Вам разрешён доступ к боту!\n\nНапишите /start чтобы начать.",
        )
    except:
        pass

    await callback.answer("✅ Пользователь одобрен")

    async with get_db() as db:
        text, keyboard = await build_pending_message(db)

    try:
        if keyboard:
            await callback.message.edit_text(text, reply_markup=keyboard)
        else:
            await callback.message.edit_text(text)
    except:
        pass


@router.callback_query(F.data.startswith("reject_"))
async def callback_reject(callback: types.CallbackQuery):
    if callback.from_user.id != settings.admin_id:
        await callback.answer(
            "⛔ Только администратор может отклонять.", show_alert=True
        )
        return

    telegram_id = int(callback.data.split("_")[1])

    async with get_db() as db:
        await reject_user(db, telegram_id)

    await callback.answer("❌ Пользователь отклонён")

    async with get_db() as db:
        text, keyboard = await build_pending_message(db)

    try:
        if keyboard:
            await callback.message.edit_text(text, reply_markup=keyboard)
        else:
            await callback.message.edit_text(text)
    except:
        pass


@router.callback_query(F.data.regexp(r"^edit_\d+$"))
async def callback_edit(callback: types.CallbackQuery, state: FSMContext):
    if not await check_access(callback.from_user.id):
        await callback.answer("⛔ Доступ запрещён.", show_alert=True)
        return

    item_id = int(callback.data.split("_")[1])

    async with get_db() as db:
        item = await get_item_by_id(db, item_id)

    if not item:
        await callback.answer("❌ Продукт не найден", show_alert=True)
        return

    await state.update_data(edit_item_id=item_id, edit_item_name=item.name)
    await state.set_state(EditProductStates.waiting_for_unit)
    await callback.message.answer(
        f"Редактирование: {item.name}\n\nВыберите единицу измерения:",
        reply_markup=get_unit_keyboard(),
    )
    await callback.answer()


@router.message(EditProductStates.waiting_for_unit, F.text == "❌ Отмена")
async def cancel_edit_unit(message: types.Message, state: FSMContext):
    await delete_user_message(message)
    await state.clear()
    await message.answer(
        "❌ Редактирование отменено.", reply_markup=get_list_menu_keyboard()
    )


@router.message(EditProductStates.waiting_for_unit, F.text == "⏭ Без меры")
async def edit_skip_unit(message: types.Message, state: FSMContext):
    await delete_user_message(message)
    await save_edited_product(message, state, None, None)


@router.message(EditProductStates.waiting_for_unit)
async def edit_process_unit(message: types.Message, state: FSMContext):
    unit = message.text.strip() if message.text else None

    valid_units = ["кг", "г", "шт", "л", "мл", "уп"]
    if unit not in valid_units:
        await message.answer("❌ Выберите единицу из списка.")
        return

    await state.update_data(edit_unit=unit)
    await state.set_state(EditProductStates.waiting_for_amount)
    await message.answer(
        f"Введите количество ({unit}):",
        reply_markup=get_amount_keyboard(),
    )


@router.message(EditProductStates.waiting_for_amount, F.text == "❌ Отмена")
async def cancel_edit_amount(message: types.Message, state: FSMContext):
    await delete_user_message(message)
    await state.clear()
    await message.answer(
        "❌ Редактирование отменено.", reply_markup=get_list_menu_keyboard()
    )


@router.message(EditProductStates.waiting_for_amount)
async def edit_process_amount(message: types.Message, state: FSMContext):
    data = await state.get_data()
    unit = data.get("edit_unit")

    if not message.text or not message.text.strip():
        await message.answer("❌ Введите число:")
        return

    try:
        amount_str = message.text.strip().replace(",", ".")
        amount = float(amount_str)
        if amount <= 0:
            await message.answer("❌ Количество должно быть больше нуля:")
            return
        if amount == int(amount):
            amount = int(amount)
    except ValueError:
        await message.answer("❌ Введите корректное число:")
        return

    if data.get("edit_template_item_id"):
        await save_edited_template_product(message, state, amount, unit)
    else:
        await save_edited_product(message, state, amount, unit)


async def save_edited_product(message: types.Message, state: FSMContext, amount, unit):
    data = await state.get_data()
    item_id = data.get("edit_item_id")

    if amount is not None and unit:
        quantity = f"{amount}{unit}"
    else:
        quantity = None

    async with get_db() as db:
        await update_item_quantity(db, item_id, quantity)

    await state.clear()
    await message.answer(
        f"✅ Количество обновлено.", reply_markup=get_list_menu_keyboard()
    )


async def build_templates_message(db) -> tuple:
    templates = await get_all_templates(db)

    if not templates:
        text = "📋 Шаблоны пусты.\n\nСоздайте новый шаблон или сохраните текущий список как шаблон."
        keyboard = [
            [
                InlineKeyboardButton(
                    text="➕ Новый шаблон", callback_data="new_template"
                ),
                InlineKeyboardButton(
                    text="📥 Из списка", callback_data="template_from_list"
                ),
            ]
        ]
        return text, InlineKeyboardMarkup(inline_keyboard=keyboard)

    text = "📋 Шаблоны:\n\n"
    keyboard = []

    for i, t in enumerate(templates, 1):
        text += f"{i}. {t.name} ({t.item_count} товаров)\n"
        keyboard.append(
            [
                InlineKeyboardButton(
                    text=f"📋 {t.name}", callback_data=f"view_template_{t.id}"
                ),
            ]
        )

    text += "\n👇 Нажмите на название для просмотра"

    keyboard.append(
        [
            InlineKeyboardButton(text="➕ Новый шаблон", callback_data="new_template"),
            InlineKeyboardButton(
                text="📥 Из списка", callback_data="template_from_list"
            ),
        ]
    )

    return text, InlineKeyboardMarkup(inline_keyboard=keyboard)


async def build_template_detail_message(db, template_id: int) -> tuple:
    template = await get_template_by_id(db, template_id)
    if not template:
        return "❌ Шаблон не найден.", None

    items = await get_template_items_ordered(db, template_id)

    if not items:
        text = f"📋 Шаблон: {template.name}\n\nШаблон пуст."
        keyboard = []
    else:
        text = f"📋 Шаблон: {template.name}\n"
        keyboard = []
        current_category = None
        counter = 0

        for item in items:
            counter += 1
            item_category = item.category

            if item_category != current_category:
                text += f"\n{get_category_name(item_category)}\n"
                current_category = item_category

            item_text = format_item(item.name, item.quantity)
            text += f"{counter}. {item_text}\n"
            keyboard.append(
                [
                    InlineKeyboardButton(
                        text=f"✏️ {counter}",
                        callback_data=f"edit_template_item_{item.id}",
                    ),
                    InlineKeyboardButton(
                        text=f"🗑 {counter}",
                        callback_data=f"del_template_item_{item.id}",
                    ),
                ]
            )

    return text, InlineKeyboardMarkup(inline_keyboard=keyboard) if keyboard else (
        text,
        None,
    )


@router.message(F.text == "📋 Шаблоны")
async def btn_templates(message: types.Message, state: FSMContext):
    await delete_user_message(message)
    if not await check_access(message.from_user.id):
        await message.answer("⛔ Доступ запрещён.")
        return

    await state.clear()
    async with get_db() as db:
        text, keyboard = await build_templates_message(db)

    await message.answer(text, reply_markup=keyboard)
    await message.answer("📋 Меню шаблонов", reply_markup=get_templates_menu_keyboard())


@router.callback_query(F.data == "back_to_templates")
async def callback_back_to_templates(callback: types.CallbackQuery, state: FSMContext):
    if not await check_access(callback.from_user.id):
        await callback.answer("⛔ Доступ запрещён.", show_alert=True)
        return

    await state.clear()
    async with get_db() as db:
        text, keyboard = await build_templates_message(db)

    try:
        await callback.message.edit_text(text, reply_markup=keyboard)
    except:
        pass
    await callback.message.answer(
        "📋 Меню шаблонов", reply_markup=get_templates_menu_keyboard()
    )
    await callback.answer()


@router.callback_query(F.data.startswith("view_template_"))
async def callback_view_template(callback: types.CallbackQuery, state: FSMContext):
    if not await check_access(callback.from_user.id):
        await callback.answer("⛔ Доступ запрещён.", show_alert=True)
        return

    template_id = int(callback.data.split("_")[2])
    await state.update_data(current_template_id=template_id)

    async with get_db() as db:
        text, keyboard = await build_template_detail_message(db, template_id)

    try:
        await callback.message.edit_text(text, reply_markup=keyboard)
    except:
        pass
    await callback.message.answer(
        "Выберите действие:", reply_markup=get_template_manage_keyboard()
    )
    await callback.answer()


@router.callback_query(F.data == "new_template")
async def callback_new_template(callback: types.CallbackQuery, state: FSMContext):
    if not await check_access(callback.from_user.id):
        await callback.answer("⛔ Доступ запрещён.", show_alert=True)
        return

    await state.set_state(TemplateStates.waiting_for_name)
    await callback.message.answer(
        "Введите название шаблона:", reply_markup=get_cancel_keyboard()
    )
    await callback.answer()


@router.message(TemplateStates.waiting_for_name, F.text == "❌ Отмена")
async def cancel_template_name(message: types.Message, state: FSMContext):
    await delete_user_message(message)
    await state.clear()
    await message.answer(
        "❌ Создание шаблона отменено.", reply_markup=get_templates_menu_keyboard()
    )


@router.message(TemplateStates.waiting_for_name)
async def process_template_name(message: types.Message, state: FSMContext):
    if not message.text or not message.text.strip():
        await message.answer("❌ Название не может быть пустым. Попробуйте снова:")
        return

    name = message.text.strip()
    data = await state.get_data()
    template_items = data.get("template_items")

    async with get_db() as db:
        existing = await get_template_by_id(db, name)
        if existing:
            await message.answer(
                "❌ Шаблон с таким названием уже существует. Попробуйте другое:"
            )
            return

        if template_items:
            await create_template_from_items(db, name, template_items)
            await state.clear()
            return

        template_id = await create_template(db, name)

    await state.update_data(template_id=template_id, template_name=name)
    await state.set_state(TemplateStates.waiting_for_product_name)
    await message.answer(
        f"Шаблон '{name}' создан.\n\nВведите название первого продукта:",
        reply_markup=get_cancel_keyboard(),
    )


@router.message(TemplateStates.waiting_for_product_name, F.text == "❌ Отмена")
async def cancel_template_product_name(message: types.Message, state: FSMContext):
    await delete_user_message(message)
    data = await state.get_data()
    template_id = data.get("current_template_id") or data.get("template_id")
    await state.clear()
    if template_id:
        await state.update_data(current_template_id=template_id)
        await message.answer(
            "❌ Добавление товаров отменено.",
            reply_markup=get_template_manage_keyboard(),
        )
    else:
        await message.answer(
            "❌ Добавление товаров отменено.",
            reply_markup=get_templates_menu_keyboard(),
        )


@router.message(TemplateStates.waiting_for_product_name, F.text == "✅ Готово")
async def finish_template_products(message: types.Message, state: FSMContext):
    await delete_user_message(message)
    data = await state.get_data()
    template_id = data.get("current_template_id") or data.get("template_id")
    await state.clear()
    if template_id:
        await state.update_data(current_template_id=template_id)
        await message.answer(
            "✅ Шаблон сохранён.", reply_markup=get_template_manage_keyboard()
        )
    else:
        await message.answer(
            "✅ Шаблон сохранён.", reply_markup=get_templates_menu_keyboard()
        )


@router.message(TemplateStates.waiting_for_product_name)
async def process_template_product_name(message: types.Message, state: FSMContext):
    if not message.text or not message.text.strip():
        await message.answer("❌ Название не может быть пустым. Попробуйте снова:")
        return

    name = message.text.strip()
    await state.update_data(template_product_name=name)
    await state.set_state(TemplateStates.waiting_for_product_unit)
    await message.answer(
        f"Продукт: {name}\n\nВыберите единицу измерения:",
        reply_markup=get_unit_keyboard(),
    )


@router.message(TemplateStates.waiting_for_product_unit, F.text == "❌ Отмена")
async def cancel_template_product_unit(message: types.Message, state: FSMContext):
    await delete_user_message(message)
    data = await state.get_data()
    template_id = data.get("current_template_id") or data.get("template_id")
    await state.clear()
    if template_id:
        await state.update_data(current_template_id=template_id)
        await message.answer(
            "❌ Добавление товаров отменено.",
            reply_markup=get_template_manage_keyboard(),
        )
    else:
        await message.answer(
            "❌ Добавление товаров отменено.",
            reply_markup=get_templates_menu_keyboard(),
        )


@router.message(TemplateStates.waiting_for_product_unit, F.text == "⏭ Без меры")
async def skip_template_product_unit(message: types.Message, state: FSMContext):
    await delete_user_message(message)
    await save_template_product(message, state, None, None)


@router.message(TemplateStates.waiting_for_product_unit)
async def process_template_product_unit(message: types.Message, state: FSMContext):
    unit = message.text.strip() if message.text else None

    valid_units = ["кг", "г", "шт", "л", "мл", "уп"]
    if unit not in valid_units:
        await message.answer("❌ Выберите единицу из списка.")
        return

    await state.update_data(template_product_unit=unit)
    await state.set_state(TemplateStates.waiting_for_product_amount)
    await message.answer(
        f"Введите количество ({unit}):",
        reply_markup=get_amount_keyboard(),
    )


@router.message(TemplateStates.waiting_for_product_amount, F.text == "❌ Отмена")
async def cancel_template_product_amount(message: types.Message, state: FSMContext):
    await delete_user_message(message)
    data = await state.get_data()
    template_id = data.get("current_template_id") or data.get("template_id")
    await state.clear()
    if template_id:
        await state.update_data(current_template_id=template_id)
        await message.answer(
            "❌ Добавление товаров отменено.",
            reply_markup=get_template_manage_keyboard(),
        )
    else:
        await message.answer(
            "❌ Добавление товаров отменено.",
            reply_markup=get_templates_menu_keyboard(),
        )


@router.message(TemplateStates.waiting_for_product_amount)
async def process_template_product_amount(message: types.Message, state: FSMContext):
    data = await state.get_data()
    unit = data.get("template_product_unit")

    if not message.text or not message.text.strip():
        await message.answer("❌ Введите число:")
        return

    try:
        amount_str = message.text.strip().replace(",", ".")
        amount = float(amount_str)
        if amount <= 0:
            await message.answer("❌ Количество должно быть больше нуля:")
            return
        if amount == int(amount):
            amount = int(amount)
    except ValueError:
        await message.answer("❌ Введите корректное число:")
        return

    await save_template_product(message, state, amount, unit)


async def save_template_product(
    message: types.Message, state: FSMContext, amount, unit
):
    data = await state.get_data()
    template_id = data.get("current_template_id") or data.get("template_id")
    name = data.get("template_product_name")

    if amount is not None and unit:
        quantity = f"{amount}{unit}"
    else:
        quantity = None

    async with get_db() as db:
        user_categories = await get_all_product_categories(db)
        category = categorize_product(name, user_categories)
        item_id = await add_item_to_template(db, template_id, name, quantity, category)

    await state.update_data(current_template_id=template_id)
    await state.set_state(TemplateStates.waiting_for_product_name)

    cat_keyboard = build_category_keyboard(item_id, category, "tcat")
    await message.answer(
        f"✅ Добавлено: {format_item(name, quantity)}\n📁 {get_category_name(category)}",
        reply_markup=cat_keyboard,
    )
    await message.answer(
        "Введите следующий продукт или 'Готово':",
        reply_markup=ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="✅ Готово"), KeyboardButton(text="❌ Отмена")]
            ],
            resize_keyboard=True,
        ),
    )


@router.callback_query(F.data == "template_from_list")
async def callback_template_from_list(callback: types.CallbackQuery, state: FSMContext):
    if not await check_access(callback.from_user.id):
        await callback.answer("⛔ Доступ запрещён.", show_alert=True)
        return

    async with get_db() as db:
        items = await get_pending_items(db)

    if not items:
        await callback.answer("❌ Список покупок пуст.", show_alert=True)
        return

    await state.update_data(template_items=items)
    await state.set_state(TemplateStates.waiting_for_name)
    await callback.message.answer(
        f"Создать шаблон из {len(items)} товаров?\n\nВведите название шаблона:",
        reply_markup=get_cancel_keyboard(),
    )
    await callback.answer()


@router.message(TemplateStates.waiting_for_rename, F.text == "❌ Отмена")
async def cancel_rename_template(message: types.Message, state: FSMContext):
    await delete_user_message(message)
    await state.clear()
    await message.answer(
        "❌ Переименование отменено.", reply_markup=get_template_manage_keyboard()
    )


@router.message(TemplateStates.waiting_for_rename)
async def process_rename_template(message: types.Message, state: FSMContext):
    if not message.text or not message.text.strip():
        await message.answer("❌ Название не может быть пустым. Попробуйте снова:")
        return

    new_name = message.text.strip()
    data = await state.get_data()
    template_id = data.get("rename_template_id") or data.get("current_template_id")

    async with get_db() as db:
        success = await rename_template(db, template_id, new_name)
        if not success:
            await message.answer(
                "❌ Шаблон с таким названием уже существует. Попробуйте другое:"
            )
            return
        text, keyboard = await build_template_detail_message(db, template_id)

    await state.update_data(current_template_id=template_id)
    await message.answer(
        f"✅ Шаблон переименован в '{new_name}'.",
        reply_markup=get_template_manage_keyboard(),
    )
    if keyboard:
        await message.answer(text, reply_markup=keyboard)
    else:
        await message.answer(text)


@router.message(F.text == "◀️ Назад")
async def btn_back(message: types.Message, state: FSMContext):
    await delete_user_message(message)
    data = await state.get_data()
    template_id = data.get("current_template_id")

    await state.clear()

    if template_id:
        async with get_db() as db:
            text, keyboard = await build_templates_message(db)
        await message.answer(text, reply_markup=keyboard)
        await message.answer(
            "📋 Меню шаблонов", reply_markup=get_templates_menu_keyboard()
        )
    else:
        await message.answer("Главное меню", reply_markup=get_main_keyboard())


@router.message(F.text == "➕ Новый шаблон")
async def btn_new_template(message: types.Message, state: FSMContext):
    await delete_user_message(message)
    if not await check_access(message.from_user.id):
        await message.answer("⛔ Доступ запрещён.")
        return

    await state.set_state(TemplateStates.waiting_for_name)
    await message.answer(
        "Введите название шаблона:", reply_markup=get_cancel_keyboard()
    )


@router.message(F.text == "📥 Из списка")
async def btn_template_from_list(message: types.Message, state: FSMContext):
    await delete_user_message(message)
    if not await check_access(message.from_user.id):
        await message.answer("⛔ Доступ запрещён.")
        return

    async with get_db() as db:
        items = await get_pending_items(db)

    if not items:
        await message.answer("❌ Список покупок пуст.")
        return

    await state.update_data(template_items=items)
    await state.set_state(TemplateStates.waiting_for_name)
    await message.answer(
        f"Создать шаблон из {len(items)} товаров?\n\nВведите название шаблона:",
        reply_markup=get_cancel_keyboard(),
    )


@router.message(F.text == "➕ Добавить в шаблон")
async def btn_template_add_item(message: types.Message, state: FSMContext):
    await delete_user_message(message)
    if not await check_access(message.from_user.id):
        await message.answer("⛔ Доступ запрещён.")
        return

    data = await state.get_data()
    template_id = data.get("current_template_id")

    if not template_id:
        await message.answer("❌ Сначала выберите шаблон.")
        return

    await state.set_state(TemplateStates.waiting_for_product_name)
    await message.answer(
        "Введите название продукта:", reply_markup=get_cancel_keyboard()
    )


@router.message(F.text == "🗑 Удалить товар")
async def btn_template_delete_item(message: types.Message, state: FSMContext):
    await delete_user_message(message)
    if not await check_access(message.from_user.id):
        await message.answer("⛔ Доступ запрещён.")
        return

    data = await state.get_data()
    template_id = data.get("current_template_id")

    if not template_id:
        await message.answer("❌ Сначала выберите шаблон.")
        return

    async with get_db() as db:
        items = await get_template_items(db, template_id)

    if not items:
        await message.answer("📋 Шаблон пуст.")
        return

    text = "🗑 Выберите товар для удаления:\n\n"
    keyboard = []

    for i, item in enumerate(items, 1):
        item_text = format_item(item.name, item.quantity)
        text += f"{i}. {item_text}\n"
        keyboard.append(
            [
                InlineKeyboardButton(
                    text=f"🗑 {i}. {item_text}",
                    callback_data=f"del_template_item_{item.id}",
                )
            ]
        )

    keyboard.append(
        [
            InlineKeyboardButton(
                text="❌ Отмена", callback_data="cancel_delete_template_item"
            )
        ]
    )

    await message.answer(
        text, reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
    )


@router.callback_query(F.data.startswith("del_template_item_"))
async def callback_delete_template_item(
    callback: types.CallbackQuery, state: FSMContext
):
    item_id = int(callback.data.split("_")[3])
    data = await state.get_data()
    template_id = data.get("current_template_id")

    async with get_db() as db:
        item = await get_template_item_by_id(db, item_id)
        if item:
            await remove_template_item(db, item_id)

        text, keyboard = await build_template_detail_message(db, template_id)

    try:
        if keyboard:
            await callback.message.edit_text(text, reply_markup=keyboard)
        else:
            await callback.message.edit_text(text)
    except:
        pass
    await callback.answer(f"🗑 Удалено: {item.name if item else ''}")


@router.callback_query(F.data == "cancel_delete_template_item")
async def callback_cancel_delete_template_item(callback: types.CallbackQuery):
    await callback.message.delete()
    await callback.answer()


@router.message(F.text == "✏️ Редактировать товар")
async def btn_template_edit_item(message: types.Message, state: FSMContext):
    await delete_user_message(message)
    if not await check_access(message.from_user.id):
        await message.answer("⛔ Доступ запрещён.")
        return

    data = await state.get_data()
    template_id = data.get("current_template_id")

    if not template_id:
        await message.answer("❌ Сначала выберите шаблон.")
        return

    async with get_db() as db:
        items = await get_template_items(db, template_id)

    if not items:
        await message.answer("📋 Шаблон пуст.")
        return

    text = "✏️ Выберите товар для редактирования:\n\n"
    keyboard = []

    for i, item in enumerate(items, 1):
        item_text = format_item(item.name, item.quantity)
        text += f"{i}. {item_text}\n"
        keyboard.append(
            [
                InlineKeyboardButton(
                    text=f"✏️ {i}. {item_text}",
                    callback_data=f"edit_template_item_{item.id}",
                )
            ]
        )

    keyboard.append(
        [
            InlineKeyboardButton(
                text="❌ Отмена", callback_data="cancel_edit_template_item"
            )
        ]
    )

    await message.answer(
        text, reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
    )


@router.callback_query(F.data.startswith("edit_template_item_"))
async def callback_edit_template_item(callback: types.CallbackQuery, state: FSMContext):
    item_id = int(callback.data.split("_")[3])

    async with get_db() as db:
        item = await get_template_item_by_id(db, item_id)

    if not item:
        await callback.answer("❌ Товар не найден", show_alert=True)
        return

    await state.update_data(
        edit_template_item_id=item_id, edit_template_item_name=item.name
    )
    await state.set_state(EditProductStates.waiting_for_unit)
    await callback.message.answer(
        f"Редактирование: {item.name}\n\nВыберите единицу измерения:",
        reply_markup=get_unit_keyboard(),
    )
    await callback.answer()


@router.callback_query(F.data == "cancel_edit_template_item")
async def callback_cancel_edit_template_item(callback: types.CallbackQuery):
    await callback.message.delete()
    await callback.answer()


@router.message(F.text == "✏️ Переименовать")
async def btn_template_rename(message: types.Message, state: FSMContext):
    await delete_user_message(message)
    if not await check_access(message.from_user.id):
        await message.answer("⛔ Доступ запрещён.")
        return

    data = await state.get_data()
    template_id = data.get("current_template_id")

    if not template_id:
        await message.answer("❌ Сначала выберите шаблон.")
        return

    await state.set_state(TemplateStates.waiting_for_rename)
    await message.answer(
        "Введите новое название шаблона:", reply_markup=get_cancel_keyboard()
    )


@router.message(F.text == "➕ В список")
async def btn_template_add_to_list(message: types.Message, state: FSMContext):
    await delete_user_message(message)
    if not await check_access(message.from_user.id):
        await message.answer("⛔ Доступ запрещён.")
        return

    data = await state.get_data()
    template_id = data.get("current_template_id")
    user = message.from_user
    user_display = get_user_display_name(user)

    if not template_id:
        await message.answer("❌ Сначала выберите шаблон.")
        return

    async with get_db() as db:
        template = await get_template_by_id(db, template_id)
        template_items = await get_template_items(db, template_id)
        list_items = await get_pending_items(db)

    if not template_items:
        await message.answer("❌ Шаблон пуст.")
        return

    conflicts = []
    non_conflicts = []

    for t_item in template_items:
        t_unit = extract_quantity_parts(t_item.quantity)[1] if t_item.quantity else None
        t_group = get_unit_group(t_unit)

        conflict_found = False
        for l_item in list_items:
            l_unit = (
                extract_quantity_parts(l_item.quantity)[1] if l_item.quantity else None
            )
            l_group = get_unit_group(l_unit)

            if l_item.name.lower() == t_item.name.lower() and l_group == t_group:
                conflicts.append(
                    {
                        "template_item": t_item,
                        "list_item": l_item,
                        "group": t_group,
                    }
                )
                conflict_found = True
                break

        if not conflict_found:
            non_conflicts.append(t_item)

    if not conflicts:
        async with get_db() as db:
            for item in non_conflicts:
                await add_item(db, item.name, item.quantity, user.id, user_display)

        await state.clear()
        await message.answer(
            f"✅ Добавлено {len(non_conflicts)} товаров.",
            reply_markup=get_main_keyboard(),
        )
        return

    text = f"⚠️ Найдено конфликтов: {len(conflicts)}\n\n"
    for i, conflict in enumerate(conflicts, 1):
        t_item = conflict["template_item"]
        l_item = conflict["list_item"]
        t_text = format_item(t_item.name, t_item.quantity)
        l_text = format_item(l_item.name, l_item.quantity)

        text += f"{i}. {t_item.name}\n"
        text += f"   В списке: {l_text}\n"
        text += f"   В шаблоне: {t_text}\n\n"

    text += "Выберите действие для всех конфликтов:"

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ Заменить все", callback_data=f"replace_all_{template_id}"
                ),
                InlineKeyboardButton(
                    text="⏭ Оставить все", callback_data=f"keep_all_{template_id}"
                ),
            ],
            [
                InlineKeyboardButton(
                    text="❌ Отмена", callback_data="cancel_apply_template"
                ),
            ],
        ]
    )

    await state.update_data(
        conflicts=conflicts,
        non_conflicts=non_conflicts,
        user_display=user_display,
    )

    await message.answer(text, reply_markup=keyboard)


@router.callback_query(F.data.startswith("replace_all_"))
async def callback_replace_all_conflicts(
    callback: types.CallbackQuery, state: FSMContext
):
    template_id = int(callback.data.split("_")[2])
    data = await state.get_data()
    conflicts = data.get("conflicts", [])
    non_conflicts = data.get("non_conflicts", [])
    user_display = data.get("user_display")

    async with get_db() as db:
        for conflict in conflicts:
            await update_item_quantity(
                db,
                conflict["list_item"].id,
                conflict["template_item"].quantity,
            )
        for item in non_conflicts:
            await add_item(
                db,
                item.name,
                item.quantity,
                callback.from_user.id,
                user_display,
                item.category,
            )

    await state.clear()
    await callback.message.edit_text(
        f"✅ Шаблон добавлен к списку.\n\n"
        f"Заменено: {len(conflicts)}\n"
        f"Добавлено: {len(non_conflicts)}"
    )
    await callback.message.answer(
        "📋 Список покупок", reply_markup=get_list_menu_keyboard()
    )
    await callback.answer()


@router.callback_query(F.data.startswith("keep_all_"))
async def callback_keep_all_conflicts(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    conflicts = data.get("conflicts", [])
    non_conflicts = data.get("non_conflicts", [])
    user_display = data.get("user_display")

    async with get_db() as db:
        for item in non_conflicts:
            await add_item(
                db,
                item.name,
                item.quantity,
                callback.from_user.id,
                user_display,
                item.category,
            )

    await state.clear()
    await callback.message.edit_text(
        f"✅ Шаблон добавлен к списку.\n\n"
        f"Оставлено без изменений: {len(conflicts)}\n"
        f"Добавлено: {len(non_conflicts)}"
    )
    await callback.message.answer(
        "📋 Список покупок", reply_markup=get_list_menu_keyboard()
    )
    await callback.answer()


@router.callback_query(F.data == "cancel_apply_template")
async def callback_cancel_apply_template(
    callback: types.CallbackQuery, state: FSMContext
):
    await state.clear()
    await callback.message.delete()
    await callback.answer("❌ Отменено")


@router.message(F.text == "🗑 Удалить шаблон")
async def btn_template_delete(message: types.Message, state: FSMContext):
    await delete_user_message(message)
    if not await check_access(message.from_user.id):
        await message.answer("⛔ Доступ запрещён.")
        return

    data = await state.get_data()
    template_id = data.get("current_template_id")

    if not template_id:
        await message.answer("❌ Сначала выберите шаблон.")
        return

    async with get_db() as db:
        template = await get_template_by_id(db, template_id)

    if not template:
        await message.answer("❌ Шаблон не найден.")
        return

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ Удалить",
                    callback_data=f"confirm_del_template_{template_id}",
                ),
                InlineKeyboardButton(
                    text="❌ Отмена", callback_data="cancel_del_template"
                ),
            ]
        ]
    )

    await message.answer(f"⚠️ Удалить шаблон '{template.name}'?", reply_markup=keyboard)


@router.callback_query(F.data.startswith("confirm_del_template_"))
async def callback_confirm_delete_template(
    callback: types.CallbackQuery, state: FSMContext
):
    template_id = int(callback.data.split("_")[3])

    async with get_db() as db:
        await delete_template(db, template_id)
        text, keyboard = await build_templates_message(db)

    await state.clear()
    await callback.message.edit_text("🗑 Шаблон удалён.")
    await callback.message.answer(text, reply_markup=keyboard)
    await callback.message.answer(
        "📋 Меню шаблонов", reply_markup=get_templates_menu_keyboard()
    )
    await callback.answer()


@router.callback_query(F.data == "cancel_del_template")
async def callback_cancel_delete_template(callback: types.CallbackQuery):
    await callback.message.delete()
    await callback.answer()


async def save_edited_template_product(
    message: types.Message, state: FSMContext, amount, unit
):
    data = await state.get_data()
    item_id = data.get("edit_template_item_id")

    if amount is not None and unit:
        quantity = f"{amount}{unit}"
    else:
        quantity = None

    template_id = data.get("current_template_id")

    async with get_db() as db:
        await update_template_item(db, item_id, quantity)
        text, keyboard = await build_template_detail_message(db, template_id)

    await state.clear()
    await state.update_data(current_template_id=template_id)
    await message.answer(
        "✅ Количество обновлено.", reply_markup=get_template_manage_keyboard()
    )
    if keyboard:
        await message.answer(text, reply_markup=keyboard)
    else:
        await message.answer(text)
