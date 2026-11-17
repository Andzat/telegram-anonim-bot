import html
from aiogram import Router, Bot, F
from aiogram.types import Message, CallbackQuery, ReactionTypeEmoji
import database as db
from keyboards import get_ticket_status_keyboard

router = Router()

# ----------------- Обробка кнопок статусу тікета в групі -----------------

@router.callback_query(F.data.startswith("ticket_take_"))
async def callback_ticket_take(callback: CallbackQuery, bot: Bot):
    ticket_id = int(callback.data.split("_")[2])
    ticket = await db.get_ticket(ticket_id)
    if not ticket:
        await callback.answer("Заявку не знайдено.", show_alert=True)
        return

    worker_label = f"@{callback.from_user.username}" if callback.from_user.username else callback.from_user.full_name
    await db.update_ticket_status(ticket_id, status="in_progress", worker_name=worker_label)

    new_markup = get_ticket_status_keyboard(ticket_id, "in_progress")
    work_status_text = f"\n\n🟡 <i>У роботі: {html.escape(worker_label)}</i>"

    try:
        if callback.message.text:
            orig = getattr(callback.message, "html_text", None) or html.escape(callback.message.text or "")
            await callback.message.edit_text(
                text=orig + work_status_text,
                reply_markup=new_markup,
                parse_mode="HTML"
            )
        elif callback.message.caption is not None:
            orig = getattr(callback.message, "html_caption", None) or html.escape(callback.message.caption or "")
            await callback.message.edit_caption(
                caption=orig + work_status_text,
                reply_markup=new_markup,
                parse_mode="HTML"
            )
        else:
            await callback.message.edit_reply_markup(reply_markup=new_markup)
    except Exception:
        try:
            await callback.message.edit_reply_markup(reply_markup=new_markup)
        except Exception:
            pass

    await callback.answer(f"Ви взяли заявку в роботу ({worker_label})!", show_alert=False)

@router.callback_query(F.data.startswith("ticket_close_"))
async def callback_ticket_close(callback: CallbackQuery, bot: Bot):
    ticket_id = int(callback.data.split("_")[2])
    ticket = await db.get_ticket(ticket_id)
    if not ticket:
        await callback.answer("Заявку не знайдено.", show_alert=True)
        return

    worker_label = f"@{callback.from_user.username}" if callback.from_user.username else callback.from_user.full_name
    await db.update_ticket_status(ticket_id, status="closed", worker_name=worker_label)

    close_status_text = f"\n\n🟢 <b>Вирішено:</b> {html.escape(worker_label)}"

    try:
        if callback.message.text:
            orig = getattr(callback.message, "html_text", None) or html.escape(callback.message.text or "")
            if "🟡 <i>У роботі:" in orig:
                idx = orig.find("🟡 <i>У роботі:")
                base = orig[:idx].rstrip()
                new_text = base + close_status_text
            else:
                new_text = orig + close_status_text

            await callback.message.edit_text(
                text=new_text,
                reply_markup=None,
                parse_mode="HTML"
            )
        elif callback.message.caption is not None:
            orig = getattr(callback.message, "html_caption", None) or html.escape(callback.message.caption or "")
            if "🟡 <i>У роботі:" in orig:
                idx = orig.find("🟡 <i>У роботі:")
                base = orig[:idx].rstrip()
                new_caption = base + close_status_text
            else:
                new_caption = orig + close_status_text

            await callback.message.edit_caption(
                caption=new_caption,
                reply_markup=None,
                parse_mode="HTML"
            )
        else:
            await callback.message.edit_reply_markup(reply_markup=None)
    except Exception:
        try:
            await callback.message.edit_reply_markup(reply_markup=None)
        except Exception:
            pass

    # Ставимо реакцію 👍
    if ticket.get("shop_message_id"):
        try:
            await bot.set_message_reaction(
                chat_id=ticket["shop_user_id"],
                message_id=ticket["shop_message_id"],
                reaction=[ReactionTypeEmoji(emoji="👍")]
            )
        except Exception:
            pass

    await callback.answer("Заявку позначено як вирішену!", show_alert=False)



# ----------------- Відповідь через звичайний Reply -----------------

@router.message(F.chat.type.in_({"group", "supergroup"}))
async def handle_support_reply(message: Message, bot: Bot):
    if not message.reply_to_message:
        return

    replied_msg_id = message.reply_to_message.message_id
    shop_user_id = await db.get_shop_user_by_group_message(replied_msg_id)

    if not shop_user_id:
        return

    shop = await db.get_shop_by_user_id(shop_user_id)
    shop_name = shop["name"] if shop else "Магазин"

    # Визначаємо, з якої групи/відділу надійшла відповідь
    dept = await db.get_department_by_chat_id(message.chat.id)
    dept_title = dept["name"] if dept else "Підтримки"

    try:
        if message.text:
            sent_msg = await bot.send_message(
                chat_id=shop_user_id,
                text=f"💬 <b>Відповідь від {html.escape(dept_title)}:</b>\n\n{html.escape(message.text)}",
                parse_mode="HTML"
            )
        else:
            caption = f"💬 <b>Відповідь від {html.escape(dept_title)}:</b>"
            if message.caption:
                caption += f"\n\n{html.escape(message.caption)}"

            sent_msg = await bot.copy_message(
                chat_id=shop_user_id,
                from_chat_id=message.chat.id,
                message_id=message.message_id,
                caption=caption,
                parse_mode="HTML"
            )

        await db.save_message_link(message.message_id, shop_user_id)

        try:
            await bot.set_message_reaction(
                chat_id=message.chat.id,
                message_id=message.message_id,
                reaction=[ReactionTypeEmoji(emoji="👌")]
            )
        except Exception:
            await message.reply(f"✅ Доставлено в <b>{html.escape(shop_name)}</b>", parse_mode="HTML")

    except Exception:
        await message.reply("❌ Помилка надсилання повідомлення в магазин (можливо, користувач заблокував бота).")
