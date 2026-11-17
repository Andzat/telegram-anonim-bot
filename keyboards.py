from aiogram.types import (
    ReplyKeyboardMarkup,
    KeyboardButton,
    InlineKeyboardMarkup,
    InlineKeyboardButton
)
from typing import List, Dict, Any

# Головна клавіатура для Адміністратора (внизу екрана)
def get_admin_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="➕ Новий магазин"),
                KeyboardButton(text="📋 Список магазинів")
            ],
            [
                KeyboardButton(text="📢 Розсилка магазинам"),
                KeyboardButton(text="🗑 Очистити дані")
            ]
        ],
        resize_keyboard=True,
        is_persistent=True
    )

# Постійна клавіатура відділів для Магазину (внизу екрана)
def get_shop_departments_reply_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="💻 IT-відділ"),
                KeyboardButton(text="📊 Бухгалтерія")
            ],
            [
                KeyboardButton(text="📦 Склад"),
                KeyboardButton(text="🏢 Офіс")
            ]
        ],
        resize_keyboard=True,
        is_persistent=True
    )

# Інлайн-кнопка скасування будь-якої дії
def get_cancel_inline() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="❌ Скасувати", callback_data="cancel_action")]
        ]
    )

# Підтвердження очищення бази даних
def get_clear_data_confirm_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="⚠️ Так, видалити все", callback_data="confirm_clear_data"),
                InlineKeyboardButton(text="❌ Скасувати", callback_data="cancel_action")
            ]
        ]
    )

# Підтвердження розсилки
def get_broadcast_confirm_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Надіслати всім", callback_data="confirm_broadcast"),
                InlineKeyboardButton(text="❌ Скасувати", callback_data="cancel_broadcast")
            ]
        ]
    )

# Кнопка під карткою створеного магазину
def get_shop_created_keyboard(bot_username: str, code: str) -> InlineKeyboardMarkup:
    link = f"https://t.me/{bot_username}?start={code}"
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔗 Відкрити посилання", url=link)],
            [InlineKeyboardButton(text="📲 Переслати колезі", url=f"https://t.me/share/url?url={link}&text=Підключення%20до%20бота%20підтримки")]
        ]
    )

# Кнопки статусів заявки в групі підтримки
def get_ticket_status_keyboard(ticket_id: int, status: str = "open") -> InlineKeyboardMarkup | None:
    if status == "open":
        return InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🟡 Взяти в роботу", callback_data=f"ticket_take_{ticket_id}")]
        ])
    elif status == "in_progress":
        return InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🟢 Закрити питання", callback_data=f"ticket_close_{ticket_id}")]
        ])
    return None

# Кнопка підтвердження повідомлення з опцією терміновості
def get_urgent_button_keyboard(ticket_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🚨 Позначити як ТЕРМІНОВО", callback_data=f"make_urgent_{ticket_id}")]
        ]
    )

# Вибір ролі групи для адміністратора при /set_group
def get_bind_dept_keyboard(chat_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="💻 IT-відділ", callback_data=f"bind_dept_it_{chat_id}"),
                InlineKeyboardButton(text="📊 Бухгалтерія", callback_data=f"bind_dept_buh_{chat_id}")
            ],
            [
                InlineKeyboardButton(text="📦 Склад", callback_data=f"bind_dept_sklad_{chat_id}"),
                InlineKeyboardButton(text="🏢 Офіс", callback_data=f"bind_dept_office_{chat_id}")
            ]
        ]
    )


