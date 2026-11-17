from aiogram import Dispatcher
from .admin import router as admin_router
from .shop import router as shop_router
from .support import router as support_router

def register_all_handlers(dp: Dispatcher):
    # Порядок важен: сначала админские команды, затем группа поддержки, затем личка магазинов
    dp.include_router(admin_router)
    dp.include_router(support_router)
    dp.include_router(shop_router)
