"""Tests for the satellite-only background scheduler."""

from unittest.mock import PropertyMock, patch

import pytest
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from src.scheduler import (
    init_scheduler,
    refresh_tle_data_job,
    scheduler,
    stop_scheduler,
)


@pytest.mark.asyncio
async def test_refresh_tle_data_job_success() -> None:
    """Delegate the scheduled refresh to SatelliteService."""
    with patch("src.scheduler.SatelliteService") as service_class:
        await refresh_tle_data_job()

    service_class.assert_called_once_with()
    service_class.return_value.refresh_tle_data.assert_called_once_with()


@pytest.mark.asyncio
async def test_refresh_tle_data_job_handles_exception() -> None:
    """Log a refresh failure without crashing the scheduler loop."""
    with patch("src.scheduler.SatelliteService") as service_class:
        service_class.return_value.refresh_tle_data.side_effect = RuntimeError(
            "service unavailable"
        )
        await refresh_tle_data_job()


def test_init_scheduler_registers_only_tle_refresh() -> None:
    """Register TLE refresh and no auth, playlist, or station jobs."""
    scheduled = init_scheduler()

    assert isinstance(scheduled, AsyncIOScheduler)
    job_ids = {job.id for job in scheduled.get_jobs()}
    assert "refresh_tle_data" in job_ids
    assert "cleanup_auth_sessions" not in job_ids


def test_stop_scheduler_stops_running_scheduler() -> None:
    """Shut down a running scheduler without waiting for jobs."""
    with (
        patch.object(
            type(scheduler), "running", new_callable=PropertyMock, return_value=True
        ),
        patch.object(scheduler, "shutdown") as shutdown,
    ):
        stop_scheduler()

    shutdown.assert_called_once_with(wait=False)
