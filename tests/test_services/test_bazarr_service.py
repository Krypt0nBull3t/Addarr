"""
Tests for src/services/bazarr.py -- BazarrService.

The mock config has bazarr.enable=True by default, so BazarrService()
will initialize successfully. Tests that need a disabled service
use the disabled_bazarr_config fixture.
"""

import pytest
from unittest.mock import AsyncMock, patch

from tests.conftest import _mock_config


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def disabled_bazarr_config():
    """Temporarily disable bazarr in mock config."""
    original = _mock_config._config["bazarr"]["enable"]
    _mock_config._config["bazarr"]["enable"] = False
    yield
    _mock_config._config["bazarr"]["enable"] = original


@pytest.fixture
def bazarr_service():
    """Create a BazarrService with bazarr enabled (default mock config)."""
    from src.services.bazarr import BazarrService

    return BazarrService()


# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------


class TestBazarrServiceSingleton:
    def test_singleton(self):
        from src.services.bazarr import BazarrService

        a = BazarrService()
        b = BazarrService()
        assert a is b


# ---------------------------------------------------------------------------
# Initialization
# ---------------------------------------------------------------------------


class TestBazarrServiceInit:
    def test_init_enabled(self):
        """When bazarr is enabled, is_enabled() returns True."""
        from src.services.bazarr import BazarrService

        service = BazarrService()
        assert service.is_enabled() is True

    def test_init_disabled(self, disabled_bazarr_config):
        """When bazarr is disabled, is_enabled() returns False."""
        from src.services.bazarr import BazarrService

        service = BazarrService()
        assert service.is_enabled() is False

    def test_init_missing_config(self):
        """When bazarr config is entirely missing, is_enabled() is False."""
        from src.services.bazarr import BazarrService

        original = _mock_config._config.get("bazarr")
        _mock_config._config["bazarr"] = {}
        try:
            service = BazarrService()
            assert service.is_enabled() is False
        finally:
            _mock_config._config["bazarr"] = original


# ---------------------------------------------------------------------------
# Client property
# ---------------------------------------------------------------------------


class TestBazarrServiceClient:
    def test_client_lazy_init(self):
        """Client is lazily initialized on first access."""
        from src.services.bazarr import BazarrService

        service = BazarrService()
        assert service.client is not None

    def test_client_disabled_returns_none(self, disabled_bazarr_config):
        """Client returns None when service is disabled."""
        from src.services.bazarr import BazarrService

        service = BazarrService()
        assert service.client is None

    def test_client_init_failure_returns_none(self):
        """Client returns None when BazarrClient raises on init."""
        from src.services.bazarr import BazarrService

        with patch(
            "src.services.bazarr.BazarrClient",
            side_effect=ValueError("bad config"),
        ):
            service = BazarrService()
            assert service.client is None


# ---------------------------------------------------------------------------
# Delegation methods — disabled / no client
# ---------------------------------------------------------------------------


class TestBazarrServiceDelegationDisabled:
    @pytest.mark.asyncio
    async def test_search_no_client(self, disabled_bazarr_config):
        from src.services.bazarr import BazarrService

        service = BazarrService()
        result = await service.search("test")
        assert result == []

    @pytest.mark.asyncio
    async def test_get_movies_no_client(self, disabled_bazarr_config):
        from src.services.bazarr import BazarrService

        service = BazarrService()
        result = await service.get_movies()
        assert result == []

    @pytest.mark.asyncio
    async def test_get_wanted_movies_no_client(self, disabled_bazarr_config):
        from src.services.bazarr import BazarrService

        service = BazarrService()
        result = await service.get_wanted_movies()
        assert result == []

    @pytest.mark.asyncio
    async def test_get_wanted_episodes_no_client(self, disabled_bazarr_config):
        from src.services.bazarr import BazarrService

        service = BazarrService()
        result = await service.get_wanted_episodes()
        assert result == []

    @pytest.mark.asyncio
    async def test_search_movie_subtitles_no_client(
        self, disabled_bazarr_config
    ):
        from src.services.bazarr import BazarrService

        service = BazarrService()
        result = await service.search_movie_subtitles(1, "en")
        assert result is False

    @pytest.mark.asyncio
    async def test_search_episode_subtitles_no_client(
        self, disabled_bazarr_config
    ):
        from src.services.bazarr import BazarrService

        service = BazarrService()
        result = await service.search_episode_subtitles(1, 2, "en")
        assert result is False


# ---------------------------------------------------------------------------
# Delegation methods — with client
# ---------------------------------------------------------------------------


class TestBazarrServiceDelegationWithClient:
    @pytest.mark.asyncio
    async def test_search_delegates(self):
        from src.services.bazarr import BazarrService

        service = BazarrService()
        mock_client = AsyncMock()
        mock_client.search.return_value = [{"title": "Test Movie"}]
        BazarrService._client = mock_client

        result = await service.search("test")
        mock_client.search.assert_called_once_with("test")
        assert result == [{"title": "Test Movie"}]

    @pytest.mark.asyncio
    async def test_get_movies_delegates(self):
        from src.services.bazarr import BazarrService

        service = BazarrService()
        mock_client = AsyncMock()
        mock_client.get_movies.return_value = [{"title": "Movie"}]
        BazarrService._client = mock_client

        result = await service.get_movies()
        mock_client.get_movies.assert_called_once()
        assert result == [{"title": "Movie"}]

    @pytest.mark.asyncio
    async def test_get_wanted_movies_delegates(self):
        from src.services.bazarr import BazarrService

        service = BazarrService()
        mock_client = AsyncMock()
        mock_client.get_wanted_movies.return_value = [{"title": "Wanted"}]
        BazarrService._client = mock_client

        result = await service.get_wanted_movies()
        mock_client.get_wanted_movies.assert_called_once()
        assert result == [{"title": "Wanted"}]

    @pytest.mark.asyncio
    async def test_get_wanted_episodes_delegates(self):
        from src.services.bazarr import BazarrService

        service = BazarrService()
        mock_client = AsyncMock()
        mock_client.get_wanted_episodes.return_value = [{"title": "Ep1"}]
        BazarrService._client = mock_client

        result = await service.get_wanted_episodes()
        mock_client.get_wanted_episodes.assert_called_once()
        assert result == [{"title": "Ep1"}]

    @pytest.mark.asyncio
    async def test_search_movie_subtitles_delegates(self):
        from src.services.bazarr import BazarrService

        service = BazarrService()
        mock_client = AsyncMock()
        mock_client.search_movie_subtitles.return_value = True
        BazarrService._client = mock_client

        result = await service.search_movie_subtitles(
            42, "en", forced=True, hi=False
        )
        mock_client.search_movie_subtitles.assert_called_once_with(
            42, "en", forced=True, hi=False
        )
        assert result is True

    @pytest.mark.asyncio
    async def test_search_episode_subtitles_delegates(self):
        from src.services.bazarr import BazarrService

        service = BazarrService()
        mock_client = AsyncMock()
        mock_client.search_episode_subtitles.return_value = True
        BazarrService._client = mock_client

        result = await service.search_episode_subtitles(
            10, 20, "en", forced=False, hi=True
        )
        mock_client.search_episode_subtitles.assert_called_once_with(
            10, 20, "en", forced=False, hi=True
        )
        assert result is True
