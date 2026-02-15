#!/usr/bin/env python3
"""Domain-based test runner for Addarr.

Usage:
    python scripts/test_runner.py <domain> [pytest-args...]
    python scripts/test_runner.py api
    python scripts/test_runner.py handlers --coverage
    python scripts/test_runner.py all -x -v

Domains:
    api         API clients (radarr, sonarr, lidarr, transmission, sabnzbd)
    services    Service layer (media, health, translation, notification, etc.)
    handlers    Telegram bot handlers (auth, media, start, help, etc.)
    models      Data models (media, notification)
    bot         Bot structure (states, keyboards)
    utils       Utilities (chat, helpers, validation, error_handler, backup)
    config      Configuration (settings, validation)
    all         Full test suite

Options:
    --coverage  Add --cov scoped to the matching src/ directory
    Any other args are passed through to pytest.
"""

import subprocess
import sys

DOMAINS = {
    "api": {
        "test_path": "tests/test_api/",
        "cov_source": "src/api/",
    },
    "services": {
        "test_path": "tests/test_services/",
        "cov_source": "src/services/",
    },
    "handlers": {
        "test_path": "tests/test_handlers/",
        "cov_source": "src/bot/handlers/",
    },
    "models": {
        "test_path": "tests/test_models/",
        "cov_source": "src/models/",
    },
    "bot": {
        "test_path": "tests/test_bot/",
        "cov_source": "src/bot/",
    },
    "utils": {
        "test_path": "tests/test_utils/",
        "cov_source": "src/utils/",
    },
    "config": {
        "test_path": "tests/test_config/",
        "cov_source": "src/config/",
    },
    "all": {
        "test_path": "tests/",
        "cov_source": "src/",
    },
}


def main():
    if len(sys.argv) < 2 or sys.argv[1] in ("-h", "--help"):
        print(__doc__)
        print("Available domains:", ", ".join(sorted(DOMAINS)))
        sys.exit(0)

    domain = sys.argv[1]
    extra_args = sys.argv[2:]

    if domain not in DOMAINS:
        print(f"Unknown domain: {domain}")
        print("Available domains:", ", ".join(sorted(DOMAINS)))
        sys.exit(1)

    cfg = DOMAINS[domain]
    cmd = [sys.executable, "-m", "pytest", cfg["test_path"]]

    if "--coverage" in extra_args:
        extra_args.remove("--coverage")
        cmd += [
            f"--cov={cfg['cov_source']}",
            "--cov-report=term-missing",
        ]

    cmd += extra_args
    sys.exit(subprocess.call(cmd))


if __name__ == "__main__":
    main()
