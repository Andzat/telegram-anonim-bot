import html
from aiogram import Router, Bot, F
from aiogram.filters import CommandStart, CommandObject
from aiogram.types import Message, CallbackQuery, ReactionTypeEmoji

from config import ADMIN_IDS
import database as db
from keyboards import (
    get_admin_keyboard,
    get_shop_departments_reply_keyboard,
    get_ticket_status_keyboard,
    get_urgent_button_keyboard
)

router = Router()

def is_admin(user_id: int) -> bool:
    if not ADMIN_IDS:
        return True
    return user_id in ADMIN_IDS

ADMIN_BUTTONS = {
    "➕ Новий магазин",
    "📋 Список магазинів",
    "📢 Розсилка магазинам",
    "🗑 Очистити дані"
}

DEPT_BUTTONS_MAP = {
    "💻 IT-відділ": ("it", "💻 IT-відділ"),
    "📊 Бухгалтерія": ("buh", "📊 Бухгалтерія"),
    "📦 Склад": ("sklad", "📦 Склад"),
    "🏢 Офіс": ("office", "🏢 Офіс")
}

URGENT_KEYWORDS = [
    "терміново", "терминово", "срочно", "термінова", "термінове",
    "не працює каса", "каса не працює", "впала каса", "немає світла",
    "інтернет ліг", "немає інтернету"
]

def check_urgent(text: str) -> bool:
    if not text:
        return False
    lower_text = text.lower()
    return any(word in lower_text for word in URGENT_KEYWORDS)

# ----------------- /start -----------------

@router.message(F.chat.type == "private", CommandStart())
async def cmd_start(message: Message, command: CommandObject, bot: Bot):
    user = message.from_user
    args = command.args
    support_chat_id = await db.get_support_chat_id()

    # 1. Якщо передали код магазину в посиланні
    if args:
        code = args.strip().lower()
        shop = await db.register_shop(
            code=code,
            user_id=user.id,
            username=user.username,
            first_name=user.first_name
        )

        if shop:
            # За замовчуванням ставимо IT-відділ
            await db.set_shop_selected_dept(user.id, "it")

            welcome_text = (
                f"🎉 <b>Ласкаво просимо!</b>\n\n"
                f"Ви успішно підключені до системи як: <b>{html.escape(shop['name'])}</b>.\n\n"
                f"🏢 <b>Оберіть відділ унизу екрана</b> (за замовчуванням обрано 💻 IT-відділ) "
                f"та пишіть ваше запитання або надсилайте фото/документи. "
                f"Фахівці одразу отримають ваше звернення!"
            )

            await message.answer(
                welcome_text,
                reply_markup=get_shop_departments_reply_keyboard(),
                parse_mode="HTML"
            )

            if support_chat_id:
                try:
                    await bot.send_message(
                        chat_id=support_chat_id,
                        text=(
                            f"🔔 <b>Магазин підключився до бота:</b>\n"
                            f"🏢 {html.escape(shop['name'])}\n"
                            f"🔑 Код: <code>{shop['code']}</code>\n"
                            f"👤 Співробітник: {html.escape(user.full_name)} "
                            f"({'@' + user.username if user.username else 'id: ' + str(user.id)})"
                        ),
                        parse_mode="HTML"
                    )
                except Exception:
                    pass
            return
        else:
            await message.answer(
                "⚠️ Код магазину з посилання не знайдено або він недійсний.\n"
                "Будь ласка, зверніться до адміністратора за правильним посиланням."
            )
            return

    # 2. Якщо це Адміністратор
    if is_admin(user.id):
        await message.answer(
            f"👋 Вітаємо, {html.escape(user.first_name)}!\n\n"
            f"Ви увійшли з правами <b>Адміністратора</b>.\n"
            f"Використовуйте кнопки внизу екрана для керування системою.",
            reply_markup=get_admin_keyboard(),
            parse_mode="HTML"
        )
        return

    # 3. Якщо вже зареєстрований магазин
    shop = await db.get_shop_by_user_id(user.id)
    if shop:
        selected_code = shop.get("selected_dept") or "it"
        dept_name = DEPT_BUTTONS_MAP.get(selected_code, ("", "💻 IT-відділ"))[1]
        for name, (c, title) in DEPT_BUTTONS_MAP.items():
            if c == selected_code:
                dept_name = title
                break

        text = (
            f"👋 Вітаємо!\n\n"
            f"Ви авторизовані як: <b>{html.escape(shop['name'])}</b>.\n"
            f"🎯 Поточний відділ: <b>{html.escape(dept_name)}</b>.\n\n"
            f"Напишіть ваше запитання або оберіть інший відділ кнопками внизу екрана 👇"
        )
        await message.answer(
            text,
            reply_markup=get_shop_departments_reply_keyboard(),
            parse_mode="HTML"
        )
    else:
        await message.answer("У вас немає прав")

# ----------------- Перемикання відділу кнопками внизу екрана -----------------

@router.message(F.chat.type == "private", F.text.in_(DEPT_BUTTONS_MAP.keys()))
async def handle_dept_button_click(message: Message):
    shop = await db.get_shop_by_user_id(message.from_user.id)
    if not shop:
        return

    dept_code, dept_title = DEPT_BUTTONS_MAP[message.text]
    await db.set_shop_selected_dept(message.from_user.id, dept_code)

    await message.answer(
        f"🎯 <b>Ви обрали відділ: {dept_title}</b> ✅\n\n"
        f"Напишіть ваше запитання, надішліть фото або документ — фахівці цього відділу одразу його отримають!",
        reply_markup=get_shop_departments_reply_keyboard(),
        parse_mode="HTML"
    )

# ----------------- Кнопка "Зробити терміновим" -----------------

@router.callback_query(F.data.startswith("make_urgent_"))
async def callback_make_urgent(callback: CallbackQuery, bot: Bot):
    ticket_id = int(callback.data.split("_")[2])
    ticket = await db.get_ticket(ticket_id)

    if not ticket:
        await callback.answer("Заявку не знайдено.", show_alert=True)
        return

    await db.set_ticket_urgent(ticket_id)

    if ticket.get("shop_message_id"):
        try:
            await bot.set_message_reaction(
                chat_id=callback.message.chat.id,
                message_id=ticket["shop_message_id"],
                reaction=[ReactionTypeEmoji(emoji="🔥")]
            )
        except Exception:
            pass

    target_chat_id = None
    if ticket.get("dept_code"):
        dept = await db.get_department(ticket["dept_code"])
        if dept:
            target_chat_id = dept["chat_id"]
    if not target_chat_id:
        target_chat_id = await db.get_support_chat_id()

    if target_chat_id and ticket.get("group_message_id"):
        try:
            urgent_prefix = "🚨🚨🚨 <b>[ТЕРМІНОВО!]</b> "
            orig_text = ticket.get("message_text") or ""
            dept_title = f" ➔ {html.escape(ticket.get('dept_name') or '')}" if ticket.get("dept_name") else ""
            new_text = f"{urgent_prefix}📩 <b>{html.escape(ticket['shop_name'])}</b>{dept_title}:\n\n{html.escape(orig_text)}"
            await bot.edit_message_text(
                chat_id=target_chat_id,
                message_id=ticket["group_message_id"],
                text=new_text,
                reply_markup=get_ticket_status_keyboard(ticket_id, ticket.get("status", "open")),
                parse_mode="HTML"
            )
        except Exception:
            pass

    await callback.message.edit_text(
        "🚨 <b>Ваше звернення позначено як ТЕРМІНОВЕ!</b>\nСпеціалісти сповіщені з найвищим пріоритетом.",
        parse_mode="HTML"
    )
    await callback.answer()



# ----------------- Пересилання повідомлень від магазину -----------------

@router.message(F.chat.type == "private")
async def handle_shop_message(message: Message, bot: Bot):
    user = message.from_user

    if message.text in ADMIN_BUTTONS or (message.text and message.text.startswith("/")):
        return

    shop = await db.get_shop_by_user_id(user.id)
    if not shop:
        if is_admin(user.id):
            await message.answer("Використовуйте кнопки меню внизу для керування ботом.", reply_markup=get_admin_keyboard())
            return

        await message.answer("У вас немає прав")
        return

    # Визначаємо відділ
    selected_code = shop.get("selected_dept") or "it"
    dept = await db.get_department(selected_code)

    dept_title = "💻 IT-відділ"
    for name, (c, title) in DEPT_BUTTONS_MAP.items():
        if c == selected_code:
            dept_title = title
            break

    target_chat_id = dept["chat_id"] if dept else await db.get_support_chat_id()

    if not target_chat_id:
        await message.answer(
            "⚠️ Група підтримки тимчасово не налаштована.\n"
            "Будь ласка, зверніться до системного адміністратора."
        )
        return

    dept_name = dept["name"] if dept else dept_title

    content_text = message.text or message.caption or ""
    is_urgent = check_urgent(content_text)

    try:
        reaction_emoji = "🔥" if is_urgent else "👀"
        await bot.set_message_reaction(
            chat_id=message.chat.id,
            message_id=message.message_id,
            reaction=[ReactionTypeEmoji(emoji=reaction_emoji)]
        )
    except Exception:
        pass

    dept_tag = f" ➔ <b>{html.escape(dept_name)}</b>"
    if is_urgent:
        shop_header = f"🚨🚨🚨 <b>[ТЕРМІНОВО!]</b> 📩 <b>{html.escape(shop['name'])}</b>{dept_tag}"
    else:
        shop_header = f"📩 <b>{html.escape(shop['name'])}</b>{dept_tag}"

    try:
        ticket_id = await db.create_ticket(
            shop_user_id=user.id,
            shop_name=shop["name"],
            dept_code=selected_code,
            dept_name=dept_name,
            group_message_id=0,
            shop_message_id=message.message_id,
            is_urgent=is_urgent,
            message_text=content_text
        )

        status_markup = get_ticket_status_keyboard(ticket_id, "open")

        if message.text:
            sent_msg = await bot.send_message(
                chat_id=target_chat_id,
                text=f"{shop_header}:\n\n{html.escape(message.text)}",
                reply_markup=status_markup,
                parse_mode="HTML"
            )
        else:
            caption = f"{shop_header}"
            if message.caption:
                caption += f":\n\n{html.escape(message.caption)}"

            sent_msg = await bot.copy_message(
                chat_id=target_chat_id,
                from_chat_id=message.chat.id,
                message_id=message.message_id,
                caption=caption,
                reply_markup=status_markup,
                parse_mode="HTML"
            )

        await db.save_message_link(sent_msg.message_id, user.id)
        async with aiosqlite_connect() as db_conn:
            await db_conn.execute("UPDATE tickets SET group_message_id = ? WHERE id = ?", (sent_msg.message_id, ticket_id))
            await db_conn.commit()

        if not is_urgent:
            try:
                await message.reply(
                    "ㅤ",
                    reply_markup=get_urgent_button_keyboard(ticket_id)
                )
            except Exception:
                pass



    except Exception:
        await message.reply("❌ Не вдалося надіслати повідомлення до підтримки. Спробуйте пізніше.")

def aiosqlite_connect():
    import aiosqlite
    from config import DB_PATH
    return aiosqlite.connect(DB_PATH)
