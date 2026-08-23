"""Unit tests for the background task scheduler."""

import pytest
from unittest.mock import patch, MagicMock, PropertyMock
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from src.scheduler import (
    cleanup_auth_sessions_job,
    scheduler,
    refresh_tle_data_job,
    init_scheduler,
    stop_scheduler,
)


@pytest.mark.asyncio
async def test_cleanup_auth_sessions_job() -> None:
    """Test the scheduled authentication cleanup delegates to session storage."""
    with patch("src.scheduler.session_manager.cleanup_expired") as cleanup:
        await cleanup_auth_sessions_job()
    cleanup.assert_called_once_with()


@pytest.mark.asyncio
async def test_refresh_tle_data_job_success() -> None:
    """Test refresh_tle_data_job calls SatelliteService.refresh_tle_data."""
    with patch("src.scheduler.SatelliteService") as mock_service_cls:
        mock_instance = MagicMock()
        mock_service_cls.return_value = mock_instance

        await refresh_tle_data_job()

        mock_service_cls.assert_called_once()
        mock_instance.refresh_tle_data.assert_called_once()


@pytest.mark.asyncio
async def test_refresh_tle_data_job_handles_exception() -> None:
    """Test refresh_tle_data_job gracefully catches exceptions."""
    with patch("src.scheduler.SatelliteService") as mock_service_cls:
        mock_instance = MagicMock()
        mock_instance.refresh_tle_data.side_effect = Exception("Service error")
        mock_service_cls.return_value = mock_instance

        # Should not raise exception
        await refresh_tle_data_job()


def test_init_scheduler() -> None:
    """Test init_scheduler configures and returns the scheduler with jobs."""
    sch = init_scheduler()
    assert isinstance(sch, AsyncIOScheduler)

    jobs = sch.get_jobs()
    job_ids = [job.id for job in jobs]

    assert "refresh_tle_data" in job_ids
    assert "cleanup_auth_sessions" in job_ids


def test_stop_scheduler() -> None:
    """Test stop_scheduler stops the scheduler if running."""
    with (
        patch.object(
            type(scheduler), "running", new_callable=PropertyMock, return_value=True
        ),
        patch.object(scheduler, "shutdown") as mock_shutdown,
    ):
        stop_scheduler()
        mock_shutdown.assert_called_once_with(wait=False)
