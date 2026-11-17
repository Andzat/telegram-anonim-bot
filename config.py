import os
from pathlib import Path
from dotenv import load_dotenv

# Загружаем переменные из .env
load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()

# ID группы поддержки (число со знаком минус, например -1001234567890)
raw_support_chat = os.getenv("SUPPORT_CHAT_ID", "").strip()
SUPPORT_CHAT_ID = int(raw_support_chat) if raw_support_chat else None

# ID админов через запятую
raw_admin_ids = os.getenv("ADMIN_IDS", "").strip()
ADMIN_IDS = [int(x.strip()) for x in raw_admin_ids.split(",") if x.strip().isdigit()]

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = os.getenv("DATA_DIR", "").strip()
if DATA_DIR:
    os.makedirs(DATA_DIR, exist_ok=True)
    DB_PATH = Path(DATA_DIR) / "bot.db"
else:
    DB_PATH = BASE_DIR / "bot.db"
