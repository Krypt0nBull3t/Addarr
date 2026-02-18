import pytest
from aioresponses import aioresponses


@pytest.fixture
def aio_mock():
    """Provide aioresponses mock for async HTTP requests."""
    with aioresponses() as m:
        yield m


@pytest.fixture
def radarr_url():
    return "http://localhost:7878"


@pytest.fixture
def sonarr_url():
    return "http://localhost:8989"


@pytest.fixture
def lidarr_url():
    return "http://localhost:8686"


@pytest.fixture
def sabnzbd_url():
    return "http://localhost:8090"


@pytest.fixture
def radarr_client():
    from src.api.radarr import RadarrClient
    return RadarrClient()


@pytest.fixture
def sonarr_client():
    from src.api.sonarr import SonarrClient
    return SonarrClient()


@pytest.fixture
def lidarr_client():
    from src.api.lidarr import LidarrClient
    return LidarrClient()


@pytest.fixture
def sabnzbd_client():
    from src.api.sabnzbd import SabnzbdClient
    return SabnzbdClient()


@pytest.fixture
def transmission_url():
    return "http://localhost:9091"


@pytest.fixture
def transmission_client():
    from src.api.transmission import TransmissionClient
    return TransmissionClient()
