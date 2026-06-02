from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from db.database import AsyncSessionLocal
from services.token_service import TokenService


scheduler = AsyncIOScheduler()


async def _cleanup_job():
    async with AsyncSessionLocal() as db:
        await TokenService.cleanup_expired(db)


def start_scheduler():
    scheduler.add_job(
        _cleanup_job,
        trigger=IntervalTrigger(hours=1),
        id="cleanup_expired_tokens",
        replace_existing=True,
    )
    scheduler.start()


def stop_scheduler():
    if scheduler.running:
        scheduler.shutdown(wait=False)
