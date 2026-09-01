"""Background task scheduler for Orbital Radio backend.

Provides the periodic TLE refresh task using APScheduler.  Radio Browser
metadata is fetched on demand and cached by ``RadioService``; there are no
authentication, playlist, or station-prefetch jobs.
"""

import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from src.config import get_settings
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
    if scheduler.get_job("refresh_tle_data") is None:
        scheduler.add_job(
            refresh_tle_data_job,
            "interval",
            hours=get_settings().tle_refresh_hours,
            id="refresh_tle_data",
            replace_existing=True,
        )
    # Remove this legacy job if a long-lived process was upgraded in place.
    # New processes never register it, and no auth/session state exists.
    if scheduler.get_job("cleanup_auth_sessions") is not None:
        scheduler.remove_job("cleanup_auth_sessions")
    return scheduler


def stop_scheduler() -> None:
    """Stop the background scheduler if it is currently running."""
    if scheduler.running:
        scheduler.shutdown(wait=False)
