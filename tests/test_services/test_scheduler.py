"""
Tests for src/services/scheduler.py -- JobScheduler.

aiocron.crontab is mocked to avoid real cron scheduling in tests.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_mock_cron():
    """Create a mock aiocron cron job."""
    cron = MagicMock()
    cron.start = MagicMock()
    cron.stop = MagicMock()
    return cron


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestAddJob:
    @patch("src.services.scheduler.aiocron")
    def test_add_job(self, mock_aiocron):
        from src.services.scheduler import JobScheduler

        mock_cron = _make_mock_cron()
        mock_aiocron.crontab.return_value = mock_cron

        scheduler = JobScheduler()
        func = AsyncMock()
        scheduler.add_job("test_job", func, "*/5 * * * *")

        assert "test_job" in scheduler.jobs
        mock_aiocron.crontab.assert_called_once()

    @patch("src.services.scheduler.aiocron")
    def test_add_job_replaces_existing(self, mock_aiocron):
        from src.services.scheduler import JobScheduler

        old_cron = _make_mock_cron()
        new_cron = _make_mock_cron()
        mock_aiocron.crontab.side_effect = [old_cron, new_cron]

        scheduler = JobScheduler()
        func1 = AsyncMock()
        func2 = AsyncMock()

        scheduler.add_job("my_job", func1, "*/5 * * * *")
        scheduler.add_job("my_job", func2, "*/10 * * * *")

        old_cron.stop.assert_called_once()
        assert scheduler.jobs["my_job"] is new_cron


class TestRemoveJob:
    @patch("src.services.scheduler.aiocron")
    def test_remove_job(self, mock_aiocron):
        from src.services.scheduler import JobScheduler

        mock_cron = _make_mock_cron()
        mock_aiocron.crontab.return_value = mock_cron

        scheduler = JobScheduler()
        scheduler.add_job("temp_job", AsyncMock(), "*/5 * * * *")
        scheduler.remove_job("temp_job")

        assert "temp_job" not in scheduler.jobs
        mock_cron.stop.assert_called_once()

    @patch("src.services.scheduler.aiocron")
    def test_remove_nonexistent(self, mock_aiocron):
        from src.services.scheduler import JobScheduler

        scheduler = JobScheduler()
        # Should not raise
        scheduler.remove_job("does_not_exist")


class TestStartStop:
    @patch("src.services.scheduler.aiocron")
    def test_start(self, mock_aiocron):
        from src.services.scheduler import JobScheduler

        mock_cron1 = _make_mock_cron()
        mock_cron2 = _make_mock_cron()
        mock_aiocron.crontab.side_effect = [mock_cron1, mock_cron2]

        scheduler = JobScheduler()
        scheduler.add_job("job1", AsyncMock(), "*/5 * * * *")
        scheduler.add_job("job2", AsyncMock(), "*/10 * * * *")

        scheduler.start()

        assert scheduler.running is True
        mock_cron1.start.assert_called()
        mock_cron2.start.assert_called()

    @patch("src.services.scheduler.aiocron")
    def test_stop(self, mock_aiocron):
        from src.services.scheduler import JobScheduler

        mock_cron1 = _make_mock_cron()
        mock_cron2 = _make_mock_cron()
        mock_aiocron.crontab.side_effect = [mock_cron1, mock_cron2]

        scheduler = JobScheduler()
        scheduler.add_job("job1", AsyncMock(), "*/5 * * * *")
        scheduler.add_job("job2", AsyncMock(), "*/10 * * * *")
        scheduler.running = True

        scheduler.stop()

        assert scheduler.running is False
        mock_cron1.stop.assert_called()
        mock_cron2.stop.assert_called()
