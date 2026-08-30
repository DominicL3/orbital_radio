"""Background task scheduler for Orbital Radio backend.

Provides periodic background task execution using APScheduler for tasks such as
refreshing TLE data, updating playlist caches, and cleaning up expired sessions.
"""

import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from src.config import get_settings
from src.services.auth_service import session_manager
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


async def cleanup_auth_sessions_job() -> None:
    """Remove expired authentication sessions and OAuth states."""
    session_manager.cleanup_expired()


def init_scheduler() -> AsyncIOScheduler:
    """Initialize and configure the background scheduler with periodic jobs.

    Returns:
        AsyncIOScheduler: The configured AsyncIOScheduler instance.
    """
    if scheduler.get_job("refresh_tle_data") is None:
        scheduler.add_job(
            refresh_tle_data_job,
            "interval",
            hours=get_settings().tle_refresh_hours,
            id="refresh_tle_data",
            replace_existing=True,
        )
    if scheduler.get_job("cleanup_auth_sessions") is None:
        scheduler.add_job(
            cleanup_auth_sessions_job,
            "interval",
            minutes=30,
            id="cleanup_auth_sessions",
            replace_existing=True,
        )
    return scheduler


def stop_scheduler() -> None:
    """Stop the background scheduler if it is currently running."""
    if scheduler.running:
        scheduler.shutdown(wait=False)
