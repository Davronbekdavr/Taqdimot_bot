import asyncio

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from app.bot.admin import router as admin_router
from app.bot.user import router as user_router
from app.config import settings
from app.storage.database import Database
from app.services.billing import BillingService


async def subscription_worker(bot: Bot, db: Database) -> None:
    billing = BillingService(db)
    while True:
        billing.expire_subscriptions()
        billing.purge_expired_files(settings.output_dir)
        for subscription_id, user_id, ends_at in billing.due_reminders():
            try:
                await bot.send_message(user_id, f"Eslatma: obunangizning muddati {ends_at} UTC da tugaydi.")
                billing.mark_reminder_sent(subscription_id)
            except Exception:
                pass
        await asyncio.sleep(3600)


async def main() -> None:
    if not settings.bot_token or not (settings.admin_ids or settings.super_admin_ids):
        raise RuntimeError(".env faylida BOT_TOKEN va kamida bitta ADMIN_IDS Telegram ID ko‘rsatilishi kerak")
    db = Database(settings.database_path)
    db.initialize()
    bot = Bot(settings.bot_token)
    dispatcher = Dispatcher(storage=MemoryStorage())
    dispatcher.include_router(admin_router)
    dispatcher.include_router(user_router)
    worker = asyncio.create_task(subscription_worker(bot, db))
    try:
        await dispatcher.start_polling(bot, db=db, settings=settings)
    finally:
        worker.cancel()
        await asyncio.gather(worker, return_exceptions=True)
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
