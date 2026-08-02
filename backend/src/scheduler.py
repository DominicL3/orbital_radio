"""Background task scheduler for Orbital Radio backend.

Provides periodic background task execution using APScheduler for tasks such as
refreshing TLE data, updating playlist caches, and cleaning up expired sessions.
"""

import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from src.services.satellite_service import SatelliteService

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()


async def refresh_tle_data_job() -> None:
    """Refresh TLE data for all satellites every 12 hours."""
    logger.info("Executing scheduled job: refresh_tle_data_job")
    try:
        service = SatelliteService()
        service.refresh_tle_data()
    except Exception as exc:
        logger.error("Error executing refresh_tle_data_job: %s", exc)


def init_scheduler() -> AsyncIOScheduler:
    """Initialize and configure the background scheduler with periodic jobs.

    Returns:
        AsyncIOScheduler: The configured AsyncIOScheduler instance.
    """
    if not scheduler.get_jobs():
        scheduler.add_job(
            refresh_tle_data_job,
            "interval",
            hours=12,
            id="refresh_tle_data",
            replace_existing=True,
        )
    return scheduler


def stop_scheduler() -> None:
    """Stop the background scheduler if it is currently running."""
    if scheduler.running:
        scheduler.shutdown(wait=False)
