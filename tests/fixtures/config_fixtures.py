from copy import deepcopy

from tests.conftest import MOCK_CONFIG_DATA


def make_config(**overrides):
    """Returns MOCK_CONFIG_DATA with overrides merged at top level."""
    data = deepcopy(MOCK_CONFIG_DATA)
    data.update(overrides)
    return data


def make_radarr_config(enable=True, **overrides):
    """Returns radarr-specific config."""
    data = deepcopy(MOCK_CONFIG_DATA["radarr"])
    data["enable"] = enable
    data.update(overrides)
    return data


def make_sonarr_config(enable=True, **overrides):
    """Returns sonarr-specific config."""
    data = deepcopy(MOCK_CONFIG_DATA["sonarr"])
    data["enable"] = enable
    data.update(overrides)
    return data


def make_lidarr_config(enable=True, **overrides):
    """Returns lidarr-specific config."""
    data = deepcopy(MOCK_CONFIG_DATA["lidarr"])
    data["enable"] = enable
    data.update(overrides)
    return data


def make_transmission_config(enable=False, **overrides):
    """Returns transmission-specific config."""
    data = deepcopy(MOCK_CONFIG_DATA["transmission"])
    data["enable"] = enable
    data.update(overrides)
    return data


def make_sabnzbd_config(enable=False, **overrides):
    """Returns sabnzbd-specific config."""
    data = deepcopy(MOCK_CONFIG_DATA["sabnzbd"])
    data["enable"] = enable
    data.update(overrides)
    return data
