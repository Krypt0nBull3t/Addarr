"""MockConfig data must not drift from config_example.yaml."""

import yaml

from src.definitions import CONFIG_EXAMPLE_PATH
from tests.conftest import MOCK_CONFIG_DATA


def test_mock_transmission_keys_match_config_example():
    with open(CONFIG_EXAMPLE_PATH, encoding="utf-8") as f:
        example = yaml.safe_load(f)

    assert set(MOCK_CONFIG_DATA["transmission"]) == set(example["transmission"])
