import html
from aiogram import Router, Bot, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext

from config import ADMIN_IDS
import database as db
from states import AddShopState, BroadcastState
from keyboards import (
    get_admin_keyboard,
    get_cancel_inline,
    get_broadcast_confirm_keyboard,
    get_shop_created_keyboard,
    get_clear_data_confirm_keyboard,
    get_bind_dept_keyboard
)

router = Router()

def is_admin(user_id: int) -> bool:
    if not ADMIN_IDS:
        return True
    return user_id in ADMIN_IDS

DEPT_NAMES = {
    "it": "💻 IT-відділ",
    "buh": "📊 Бухгалтерія",
    "sklad": "📦 Склад",
    "office": "🏢 Офіс"
}

# ----------------- Команда /set_group (прив'язка групи до відділу) -----------------

@router.message(Command("set_group"))
async def cmd_set_group(message: Message):
    if not is_admin(message.from_user.id):
        await message.reply("У вас немає прав")
        return

    if message.chat.type not in {"group", "supergroup"}:
        await message.reply(
            "⚠️ Цю команду потрібно надіслати <b>безпосередньо всередині групи</b>, яку ви хочете підключити до бота.",
            parse_mode="HTML"
        )
        return

    args = message.text.split(maxsplit=2)
    # Якщо вказали аргумент, наприклад: /set_group it
    if len(args) > 1:
        dept_code = args[1].lower().strip()
        dept_name = args[2].strip() if len(args) > 2 else DEPT_NAMES.get(dept_code, f"Відділ {dept_code.upper()}")

        await db.set_department(dept_code, dept_name, message.chat.id)
        chat_title = message.chat.title or "Група відділу"

        await message.reply(
            f"✅ <b>Групу успішно закріплено за відділом: {html.escape(dept_name)}!</b>\n\n"
            f"📌 Назва чату: <b>{html.escape(chat_title)}</b>\n"
            f"🆔 ID чату: <code>{message.chat.id}</code>\n"
            f"🏷 Код відділу: <code>{dept_code}</code>\n\n"
            f"<i>Тепер усі звернення магазинів до цього відділу надходитимуть саме сюди.</i>",
            parse_mode="HTML"
        )
        return

    # Якщо без аргументів — показуємо зручні кнопки вибору відділу
    await message.reply(
        "🏢 <b>Оберіть, за яким відділом закріпити цю групу:</b>",
        reply_markup=get_bind_dept_keyboard(message.chat.id),
        parse_mode="HTML"
    )

@router.callback_query(F.data.startswith("bind_dept_"))
async def callback_bind_dept(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("У вас немає прав", show_alert=True)
        return

    parts = callback.data.split("_")
    dept_code = parts[2]
    chat_id = int(parts[3])

    dept_name = DEPT_NAMES.get(dept_code, f"Відділ {dept_code}")
    await db.set_department(dept_code, dept_name, chat_id)
    chat_title = callback.message.chat.title or "Група відділу"

    await callback.message.edit_text(
        f"✅ <b>Групу успішно закріплено за відділом: {html.escape(dept_name)}!</b>\n\n"
        f"📌 Назва чату: <b>{html.escape(chat_title)}</b>\n"
        f"🆔 ID чату: <code>{chat_id}</code>\n\n"
        f"<i>Тепер усі звернення магазинів до відділу {html.escape(dept_name)} надходитимуть сюди!</i>",
        parse_mode="HTML"
    )
    await callback.answer("Відділ успішно підключено!")

# ----------------- Команда /id -----------------

@router.message(Command("id"))
async def cmd_id(message: Message):
    user_id = message.from_user.id if message.from_user else "невідомо"
    chat_id = message.chat.id
    chat_type = message.chat.type

    dept = await db.get_department_by_chat_id(chat_id)
    status_str = f"<b>({dept['name']} ✅)</b>" if dept else ""

    reply_markup = None
    if chat_type in {"group", "supergroup"} and is_admin(message.from_user.id) and not dept:
        reply_markup = get_bind_dept_keyboard(chat_id)

    text = (
        f"📋 <b>Інформація про ID:</b>\n\n"
        f"👤 Ваш User ID: <code>{user_id}</code>\n"
        f"💬 ID цього чату: <code>{chat_id}</code> {status_str}\n"
        f"🏷 Тип чату: <code>{chat_type}</code>\n"
    )

    await message.reply(text, reply_markup=reply_markup, parse_mode="HTML")

# ----------------- Скасування будь-якої дії -----------------

@router.callback_query(F.data == "cancel_action")
async def cancel_action(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("❌ Дію скасовано.")
    await callback.answer()

# ----------------- Очистити дані -----------------

@router.message(F.text == "🗑 Очистити дані")
async def prompt_clear_data(message: Message):
    if not is_admin(message.from_user.id):
        return

    shops = await db.get_all_shops()
    count = len(shops)

    text = (
        f"⚠️ <b>УВАГА! Небезпечна дія!</b>\n\n"
        f"Ви дійсно бажаєте <b>видалити ВСІ магазини</b> з бази даних?\n"
        f"Зараз у базі: <b>{count} магазинів</b>.\n\n"
        f"<i>Після очищення всі магазини будуть видалені, а їхні посилання стануть недійсними.</i>"
    )
    await message.answer(text, reply_markup=get_clear_data_confirm_keyboard(), parse_mode="HTML")

@router.callback_query(F.data == "confirm_clear_data")
async def confirm_clear_data(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("У вас немає прав", show_alert=True)
        return

    await db.clear_all_shops_data()
    await callback.message.edit_text(
        "🗑 <b>Базу даних успішно очищено!</b>\n\n"
        "Всі магазини та історію зв'язків видалено. Ви можете додати нові магазини з чистого аркуша.",
        parse_mode="HTML"
    )
    await callback.answer("Дані успішно видалено!", show_alert=True)

# ----------------- Список магазинів -----------------

@router.callback_query(F.data == "admin_list_shops")
@router.message(F.text == "📋 Список магазинів")
async def list_shops_handler(event: Message | CallbackQuery):
    user_id = event.from_user.id
    if not is_admin(user_id):
        return

    shops = await db.get_all_shops()
    if not shops:
        text = "📋 <b>Список магазинів порожній.</b>\nНатисніть кнопку «➕ Новий магазин», щоб створити перший."
    else:
        lines = ["📋 <b>Список усіх магазинів компанії:</b>\n"]
        for s in shops:
            if s["user_id"]:
                user_info = f"@{s['username']}" if s["username"] else f"ID: {s['user_id']}"
                lines.append(
                    f"🟢 <b>{html.escape(s['name'])}</b>\n"
                    f"   ├ Код: <code>{s['code']}</code>\n"
                    f"   └ Співробітник: {user_info}"
                )
            else:
                lines.append(
                    f"⚪ <b>{html.escape(s['name'])}</b>\n"
                    f"   ├ Код: <code>{s['code']}</code>\n"
                    f"   └ <i>Посилання створено, очікує першого входу</i>"
                )
        text = "\n\n".join(lines)

    if isinstance(event, CallbackQuery):
        await event.message.edit_text(text, parse_mode="HTML")
        await event.answer()
    else:
        await event.answer(text, reply_markup=get_admin_keyboard(), parse_mode="HTML")

# ----------------- Покрокове додавання магазину (FSM) -----------------

@router.callback_query(F.data == "admin_add_shop")
@router.message(F.text == "➕ Новий магазин")
async def start_add_shop(event: Message | CallbackQuery, state: FSMContext):
    user_id = event.from_user.id
    if not is_admin(user_id):
        return

    await state.set_state(AddShopState.waiting_for_code)
    prompt = (
        "➕ <b>Крок 1 з 2: Код магазину</b>\n\n"
        "Введіть короткий ідентифікатор магазину латинськими літерами або цифрами.\n"
        "Наприклад: <code>shop2</code> або <code>magazin_lviv</code>"
    )

    if isinstance(event, CallbackQuery):
        await event.message.edit_text(prompt, reply_markup=get_cancel_inline(), parse_mode="HTML")
        await event.answer()
    else:
        await event.answer(prompt, reply_markup=get_cancel_inline(), parse_mode="HTML")

@router.message(AddShopState.waiting_for_code)
async def process_shop_code(message: Message, state: FSMContext):
    code = message.text.strip().lower()
    
    if not code.replace("_", "").isalnum():
        await message.answer(
            "⚠️ Код має складатися лише з латинських літер, цифр та знака _ (без пробілів).\n"
            "Спробуйте ще раз:",
            reply_markup=get_cancel_inline()
        )
        return

    existing = await db.get_shop_by_code(code)
    if existing:
        await message.answer(
            f"⚠️ Магазин із кодом <code>{code}</code> вже існує!\n"
            f"Придумайте інший код:",
            reply_markup=get_cancel_inline(),
            parse_mode="HTML"
        )
        return

    await state.update_data(shop_code=code)
    await state.set_state(AddShopState.waiting_for_name)

    await message.answer(
        f"Код <code>{code}</code> прийнято! ✅\n\n"
        f"🏢 <b>Крок 2 з 2: Назва магазину</b>\n"
        f"Тепер введіть назву магазину (вона відображатиметься у вхідних повідомленнях):\n"
        f"Наприклад: <code>Магазин №2 (ТРЦ Форум)</code>",
        reply_markup=get_cancel_inline(),
        parse_mode="HTML"
    )

@router.message(AddShopState.waiting_for_name)
async def process_shop_name(message: Message, state: FSMContext, bot: Bot):
    name = message.text.strip()
    data = await state.get_data()
    code = data["shop_code"]

    await db.create_shop(code, name)
    await state.clear()

    bot_info = await bot.get_me()
    link = f"https://t.me/{bot_info.username}?start={code}"

    text = (
        f"🎉 <b>Магазин успішно створено!</b>\n\n"
        f"🏢 <b>Назва:</b> {html.escape(name)}\n"
        f"🔑 <b>Код:</b> <code>{code}</code>\n\n"
        f"🔗 <b>Посилання для підключення магазину:</b>\n"
        f"<code>{link}</code>\n\n"
        f"<i>Натисніть кнопку нижче, щоб переслати посилання колезі:</i>"
    )
    await message.answer(
        text,
        reply_markup=get_shop_created_keyboard(bot_info.username, code),
        parse_mode="HTML"
    )

# ----------------- Покрокова розсилка (FSM) -----------------

@router.callback_query(F.data == "admin_broadcast")
@router.message(F.text == "📢 Розсилка магазинам")
async def start_broadcast(event: Message | CallbackQuery, state: FSMContext):
    user_id = event.from_user.id
    if not is_admin(user_id):
        return

    shops = await db.get_registered_shops()
    if not shops:
        text = "⚠️ Зараз немає жодного підключеного магазину для розсилки!"
        if isinstance(event, CallbackQuery):
            await event.message.edit_text(text)
            await event.answer()
        else:
            await event.answer(text, reply_markup=get_admin_keyboard())
        return

    await state.set_state(BroadcastState.waiting_for_content)
    prompt = (
        f"📢 <b>Створення масової розсилки</b>\n\n"
        f"Отримувачів (підключених магазинів): <b>{len(shops)}</b>\n\n"
        f"Напишіть текст повідомлення, яке отримають усі магазини в особисті повідомлення "
        f"(наприклад: <i>«Прохання оновити 1С до кінця дня»</i>):"
    )

    if isinstance(event, CallbackQuery):
        await event.message.edit_text(prompt, reply_markup=get_cancel_inline(), parse_mode="HTML")
        await event.answer()
    else:
        await event.answer(prompt, reply_markup=get_cancel_inline(), parse_mode="HTML")

@router.message(BroadcastState.waiting_for_content)
async def process_broadcast_content(message: Message, state: FSMContext):
    content_text = message.text or message.caption or ""
    if not content_text:
        await message.answer("⚠️ Будь ласка, введіть текст розсилки:", reply_markup=get_cancel_inline())
        return

    await state.update_data(broadcast_text=content_text)
    await state.set_state(BroadcastState.confirm)

    shops = await db.get_registered_shops()
    preview = (
        f"🔍 <b>Попередній перегляд розсилки:</b>\n"
        f"👥 Отримувачів: <b>{len(shops)} магазинів</b>\n"
        f"────────────────────\n"
        f"📢 <b>Повідомлення від керівництва:</b>\n\n"
        f"{html.escape(content_text)}\n"
        f"────────────────────\n\n"
        f"Надіслати повідомлення в усі магазини?"
    )
    await message.answer(preview, reply_markup=get_broadcast_confirm_keyboard(), parse_mode="HTML")

@router.callback_query(BroadcastState.confirm, F.data == "confirm_broadcast")
async def send_broadcast(callback: CallbackQuery, state: FSMContext, bot: Bot):
    data = await state.get_data()
    broadcast_text = data.get("broadcast_text", "")
    await state.clear()

    shops = await db.get_registered_shops()
    sent_count = 0
    fail_count = 0

    outgoing_msg = (
        f"📢 <b>Повідомлення від керівництва:</b>\n\n"
        f"{html.escape(broadcast_text)}\n\n"
        f"<i>Ви можете одразу відповісти на це повідомлення в чаті.</i>"
    )

    await callback.message.edit_text("⏳ Триває надсилання повідомлень магазинам...")

    for s in shops:
        try:
            await bot.send_message(
                chat_id=s["user_id"],
                text=outgoing_msg,
                parse_mode="HTML"
            )
            sent_count += 1
        except Exception:
            fail_count += 1

    await callback.message.edit_text(
        f"✅ <b>Розсилку успішно завершено!</b>\n\n"
        f"📨 Доставлено магазинам: <b>{sent_count}</b>\n"
        f"❌ Помилок надсилання: <b>{fail_count}</b>",
        parse_mode="HTML"
    )
    await callback.answer()

@router.callback_query(BroadcastState.confirm, F.data == "cancel_broadcast")
async def cancel_broadcast_confirm(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("❌ Розсилку скасовано.")
    await callback.answer()
