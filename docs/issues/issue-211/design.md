# Issue 211: Bot can die silently; startup checks and healthcheck are fragile

Issue: https://github.com/Krypt0nBull3t/Addarr/issues/211 (audit findings F140 to F148).
Decisions confirmed by the orchestrator on 2026-11-05.

## Scope

Nine independent fixes in one PR. Layers: `src/utils/prerun.py`, `src/main.py`,
`src/services/` (health, media, bazarr), `src/definitions.py`, `Dockerfile`,
`docker-compose.yml`, `README.md`.

## Root-cause finding for F140

The issue says to exit the keep-alive loop when `not self.application.updater.running`.
In python-telegram-bot 22.8 that is not enough. `network_retry_loop`
(`telegram/ext/_utils/networkloop.py`) re-raises `InvalidToken`. The private polling task in
`Updater` then ends with that exception, but `Updater._running` stays `True`. A `Conflict` from a
second bot instance ends the task the same way.

Decision: the loop stops when `not updater.running` OR the polling task is done. The task is read with
`getattr(updater, "_Updater__polling_task", None)`. PTB is pinned `==22.8`. A test builds a real
`Updater` and fails if that attribute is renamed on a PTB bump. A one-line comment at the
`getattr` says why.

A dead updater makes `start()` raise `RuntimeError`. `start_bot` already catches it, calls
`bot.stop()` and runs `sys.exit(1)`. Docker (`restart: unless-stopped`) restarts the container.

Consequence for `stop()`: `Updater.stop()` awaits the dead polling task, so it re-raises the
`InvalidToken`. Today a single `try` then skips `application.stop()` and `shutdown()`. Each
shutdown step must be guarded on its own.

## Decisions per finding

- **F145** `get_installed_packages()` reads `importlib.metadata.distributions()` instead of running
  `pip list`. It keeps its return type (a set of names with `-`/`_` variants), so
  `check_dependencies` stays as it is. The install command and `parse_requirements()` default use
  `os.path.join(self.root_dir, "requirements.txt")`.
- **F140** See above.
- **F144** `HealthService.get_disk_space()` queries every enabled app. Drives are deduplicated by
  `path`, first app wins. A drive without `path` is kept.
- **F141** `src/definitions.py` gets `HEARTBEAT_FILE`: env `ADDARR_HEARTBEAT_FILE`, default
  `<tempdir>/addarr-heartbeat` (`/tmp/addarr-heartbeat` in the container: writable by the non-root user and
  empty after a container restart, so a stale file cannot pass). The keep-alive loop touches it
  every 10 ticks of 1 s, starting on loop entry. A failed touch logs one warning. `HEALTHCHECK` (Dockerfile) and
  `healthcheck` (compose) fail when the file is missing or older than 60 s. They use busybox `sh`
  and `stat -c %Y`, so no Python starts per check.
- **F142** `stop()` becomes idempotent (an `asyncio.Lock` and a `_stopped` flag set only when an
  application exists). `start_bot` awaits `bot.stop()` after `start()` returns, so `asyncio.run`
  cannot cancel the shutdown. `stop()` closes the long-lived `BaseApiClient` sessions through new
  `MediaService.close()` (radarr, sonarr, lidarr) and `BazarrService.close()`. `TransmissionClient`
  and `SABnzbdService` open a session per call, so they need no close.
- **F147** Compose `logging:` with `driver: json-file`, `max-size: 10m`, `max-file: 3`.
- **F148** Docs only. README says libraries of about 7000+ movies need a memory limit above 256M.
  `docker-compose.yml` keeps `256M`.
- **F143** Add the missing `f` on both log lines and import `Fore` from `colorama` in `src/main.py`.
- **F146** All `print()` calls in `health.py` (`display_health_status`) become logger calls.

## Not in scope

The uv-venv `python -m pip install` fallback in prerun (F153, issue #214). The Dockerfile pip line
is already committed on `development`.
