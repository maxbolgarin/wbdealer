import asyncio
import logging
from aiogram import Bot, Dispatcher
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from src.config import Settings
from src.wb.search import WBSearchClient
from src.ai.curator import AICurator
from src.media.collage import CollageBuilder
from src.telegram.publisher import TelegramPublisher
from src.telegram.admin import router as admin_router, setup_admin_router
from src.storage.db import Storage
from src.pipeline import Pipeline

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger(__name__)


async def main():
    settings = Settings()

    # Init storage
    storage = Storage(settings.postgres_dsn)
    await storage.init()

    # Init components
    bot = Bot(token=settings.telegram_bot_token)
    search_client = WBSearchClient()
    curator = AICurator(settings.openrouter_api_key, settings.openrouter_base_url, settings.openrouter_model)
    collage_builder = CollageBuilder(settings)
    publisher = TelegramPublisher(bot, settings.telegram_chat_id)

    pipeline = Pipeline(settings, search_client, curator, collage_builder, publisher, storage)

    # Scheduler
    scheduler = AsyncIOScheduler(timezone="Europe/Moscow")
    for hour in settings.schedule_hours:
        scheduler.add_job(
            pipeline.run,
            CronTrigger(hour=hour, minute=0, timezone="Europe/Moscow"),
            id=f"post_{hour}",
            name=f"Пост в {hour}:00 MSK",
        )
    scheduler.start()
    logger.info(f"Scheduler started. Posts at {settings.schedule_hours} MSK")

    # Dispatcher with admin commands
    dp = Dispatcher()
    setup_admin_router(pipeline, storage, scheduler, settings.admin_user_id)
    dp.include_router(admin_router)

    # Run polling (blocks until shutdown)
    try:
        logger.info("Bot started, polling for admin commands...")
        await dp.start_polling(bot)
    finally:
        scheduler.shutdown()
        await storage.close()
        await bot.session.close()
        logger.info("Bot stopped")


if __name__ == "__main__":
    asyncio.run(main())
