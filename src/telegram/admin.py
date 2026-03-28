import logging
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message
from src.wb.categories import CATEGORIES

logger = logging.getLogger(__name__)

router = Router()


def setup_admin_router(pipeline, storage, scheduler, admin_user_id: int):
    """Configure admin router with dependencies via closure."""

    # Admin filter - only allow configured admin user
    router.message.filter(F.from_user.id == admin_user_id)

    @router.message(Command("post"))
    async def cmd_post(message: Message):
        await message.reply("Запускаю генерацию поста...")
        result = await pipeline.run()
        await message.reply(result)

    @router.message(Command("status"))
    async def cmd_status(message: Message):
        stats = await storage.get_stats()
        jobs = scheduler.get_jobs()
        next_fires = []
        for job in jobs:
            if job.next_run_time:
                next_fires.append(f"  {job.name}: {job.next_run_time.strftime('%H:%M %d.%m')}")

        text = (
            f"\U0001f4ca Статус бота\n\n"
            f"Постов: {stats['total_posts']}\n"
            f"Товаров: {stats['total_products']}\n"
            f"Последний пост: {stats['last_post_at'] or 'нет'}\n\n"
            f"Расписание:\n" + ("\n".join(next_fires) if next_fires else "  нет запланированных")
        )
        await message.reply(text)

    @router.message(Command("categories"))
    async def cmd_categories(message: Message):
        recent = await storage.get_recent_categories(n=5)
        lines = ["\U0001f4cb Категории:\n"]
        for cat in CATEGORIES:
            marker = " (недавно)" if cat["name"] in recent else ""
            lines.append(f"{cat['emoji']} {cat['name']}{marker}")
        await message.reply("\n".join(lines))

    return router
