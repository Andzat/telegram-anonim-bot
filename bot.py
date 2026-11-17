import asyncio
import logging
import sys

from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties

import config
import database as db
from handlers import register_all_handlers

# Налаштування логування
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("telegram_anonim_bot")

async def main():
    if not config.BOT_TOKEN:
        logger.error("ПОМИЛКА: BOT_TOKEN не вказано у файлі .env!")
        return

    # Ініціалізація бази даних SQLite
    await db.init_db()
    logger.info("База даних успішно ініціалізована.")

    # Створення бота та диспетчера
    bot = Bot(
        token=config.BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    dp = Dispatcher()

    # Реєстрація всіх хендлерів
    register_all_handlers(dp)

    bot_info = await bot.get_me()
    logger.info(f"Бот @{bot_info.username} (ID: {bot_info.id}) запущено та готовий до роботи!")

    if not config.SUPPORT_CHAT_ID:
        logger.warning(
            "УВАГА: SUPPORT_CHAT_ID не встановлено в .env! "
            "Додайте бота до групи підтримки та надішліть команду /id, щоб дізнатися ID чату."
        )

    try:
        # Скидаємо старі вебхуки/апдейти
        await bot.delete_webhook(drop_pending_updates=True)
        # Запуск polling
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        await bot.session.close()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Бот зупинено.")
