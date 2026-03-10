"""
Tests for src/services/scheduler.py -- JobScheduler.

aiocron.crontab is mocked to avoid real cron scheduling in tests.

NOTE: We use patch.object with an explicit module reference instead of
@patch("src.services.scheduler.aiocron") because src/services/__init__.py
exports a variable named `scheduler` (the JobScheduler instance), which
shadows the `scheduler` submodule in getattr-based resolution. Python 3.10's
unittest.mock resolves "src.services.scheduler" to the variable (JobScheduler
instance) instead of the module, causing AttributeError. patch.object avoids
this by targeting the module object directly.
"""

import sys

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

# Get the actual module object to use with patch.object
# This import brings the module into sys.modules
from src.services.scheduler import JobScheduler  # noqa: F401

_scheduler_mod = sys.modules["src.services.scheduler"]


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


class TestJobSchedulerSingleton:
    def test_singleton(self):
        a = JobScheduler()
        b = JobScheduler()
        assert a is b


class TestAddJob:
    @patch.object(_scheduler_mod, "aiocron")
    def test_add_job(self, mock_aiocron):
        mock_cron = _make_mock_cron()
        mock_aiocron.crontab.return_value = mock_cron

        scheduler = JobScheduler()
        func = AsyncMock()
        scheduler.add_job("test_job", func, "*/5 * * * *")

        assert "test_job" in scheduler.jobs
        mock_aiocron.crontab.assert_called_once()

    @patch.object(_scheduler_mod, "aiocron")
    def test_add_job_replaces_existing(self, mock_aiocron):
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

    @patch.object(_scheduler_mod, "aiocron")
    @pytest.mark.asyncio
    async def test_wrapped_job_success(self, mock_aiocron):
        """Test the wrapped job function executes the async func."""
        mock_cron = _make_mock_cron()
        mock_aiocron.crontab.return_value = mock_cron

        scheduler = JobScheduler()
        func = AsyncMock()
        scheduler.add_job("test_job", func, "*/5 * * * *")

        # Extract the wrapped_job function passed to crontab
        wrapped_job = mock_aiocron.crontab.call_args[1].get(
            "func"
        ) or mock_aiocron.crontab.call_args[0][1] if len(
            mock_aiocron.crontab.call_args[0]
        ) > 1 else mock_aiocron.crontab.call_args[1]["func"]

        await wrapped_job()
        func.assert_awaited_once()

    @patch.object(_scheduler_mod, "aiocron")
    @pytest.mark.asyncio
    async def test_wrapped_job_exception(self, mock_aiocron):
        """Test the wrapped job catches exceptions."""
        mock_cron = _make_mock_cron()
        mock_aiocron.crontab.return_value = mock_cron

        scheduler = JobScheduler()
        func = AsyncMock(side_effect=RuntimeError("Job failed"))
        scheduler.add_job("test_job", func, "*/5 * * * *")

        # Extract the wrapped_job function
        wrapped_job = mock_aiocron.crontab.call_args[1].get(
            "func"
        ) or mock_aiocron.crontab.call_args[0][1] if len(
            mock_aiocron.crontab.call_args[0]
        ) > 1 else mock_aiocron.crontab.call_args[1]["func"]

        # Should not raise
        await wrapped_job()
        func.assert_awaited_once()


class TestRemoveJob:
    @patch.object(_scheduler_mod, "aiocron")
    def test_remove_job(self, mock_aiocron):
        mock_cron = _make_mock_cron()
        mock_aiocron.crontab.return_value = mock_cron

        scheduler = JobScheduler()
        scheduler.add_job("temp_job", AsyncMock(), "*/5 * * * *")
        scheduler.remove_job("temp_job")

        assert "temp_job" not in scheduler.jobs
        mock_cron.stop.assert_called_once()

    @patch.object(_scheduler_mod, "aiocron")
    def test_remove_nonexistent(self, mock_aiocron):
        scheduler = JobScheduler()
        # Should not raise
        scheduler.remove_job("does_not_exist")


class TestStartStop:
    @patch.object(_scheduler_mod, "aiocron")
    def test_start(self, mock_aiocron):
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

    @patch.object(_scheduler_mod, "aiocron")
    def test_stop(self, mock_aiocron):
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
