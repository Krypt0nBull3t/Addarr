---
title: "Bot can die silently; startup checks and healthcheck are fragile"
labels: [bug, ops, agent-ready, priority:high]
slice: 16
findings: [F145, F140, F144, F141, F142, F147, F148, F143, F146]
---
## Bug

- **F145** prerun runs `pip list` in a subprocess. Without pip (uv venv), stdout is empty, `json.loads` raises JSONDecodeError, every dependency is "missing" and startup stops. The install step uses a cwd-relative `requirements.txt` (bandit B603).
- **F140** The keep-alive loop never checks polling. After for example InvalidToken, the bot idles forever.
- **F144** The disk check returns the first app's `/diskspace` only. With one container per app, Sonarr and Lidarr drives get no low-space warning.
- **F141** The healthcheck `pgrep -f "python.*run.py"` matches PID 1, so it never fails.
- **F142** SIGTERM runs `stop()` as a side task. `asyncio.run` cancels it before `application.shutdown()`. aiohttp sessions are not closed.
- **F147** Docker console logs have no size limit.
- **F148** The 256M memory limit is reached at about 7000 movies, because GET /movie loads the whole library (measured).
- **F143** Two log lines print a literal `{Fore.YELLOW}` (missing `f`).
- **F146** health.py uses `print()` instead of the logger.

## Steps to reproduce

1. **F145** Create a venv with `uv venv` (no pip), install the requirements and run `python run.py`. prerun reports every dependency as missing and stops.
2. **F140** Start the bot, then revoke its token so polling fails with InvalidToken. The process keeps running and does nothing.
3. **F144** Run Radarr, Sonarr and Lidarr in separate containers. Fill a drive that only Sonarr uses. No low-space warning comes.
4. **F141** Run the container and stop polling as in step 2. Docker still reports the container as healthy.
5. **F142** Run `docker stop` on the container. `application.shutdown()` does not run and the aiohttp sessions stay open.
6. **F147** Run the container from `docker-compose.yml` for a long time. The console log file grows without limit.
7. **F148** Connect a Radarr library of about 7000 movies and trigger a full library load (GET /movie). The container reaches the 256M limit.
8. **F143** Stop the bot. The log shows `{Fore.YELLOW}Shutting down...` as literal text.
9. **F146** Run the health check. Its output goes to stdout through `print()`, not to the logger.

## Expected behavior

prerun works without pip and installs from an absolute path. The bot exits when polling stops, so its supervisor restarts it. The disk check covers every enabled app. The Docker healthcheck fails when the loop stops. SIGTERM shuts down cleanly and closes the clients. Docker logs are capped. The README says that large libraries (about 7000+ movies) need a memory limit above 256M. Log lines contain no literal color codes. health.py logs through the logger.

## Fix

- [ ] **F145** Use `importlib.metadata.version()` instead of `pip list`; build the `requirements.txt` path from ROOT_DIR (`src/utils/prerun.py:117-135`, `:165`)
- [ ] **F140** Exit the loop when `not self.application.updater.running` (`src/main.py:259`)
- [ ] **F144** Query every enabled app; dedupe by path (`src/services/health.py:451-473`)
- [ ] **F141** Touch a heartbeat file in the loop; the healthcheck checks its age (`Dockerfile:29-30`, `docker-compose.yml:35`)
- [ ] **F142** Await `bot.stop()` in `start_bot`; close the clients (`src/main.py:314`)
- [ ] **F147** Add `logging:` with `max-size: 10m` and `max-file: 3` (`docker-compose.yml:7`)
- [ ] **F148** Keep the 256M limit. Document in README that large libraries (about 7000+ movies) need a higher limit (`docker-compose.yml:44`, `src/api/radarr.py:287`)
- [ ] **F143** Add the missing `f` (`src/main.py:322`, `:334`)
- [ ] **F146** Use the logger instead of `print()` (`src/services/health.py:37`)

## Acceptance criteria

Each test fails before its fix and passes after:

- **F145** `tests/test_utils/test_prerun.py`: with empty `pip list` output, installed packages are still found. The install command uses an absolute `requirements.txt` path.
- **F140** `tests/test_main.py`: when `application.updater.running` becomes False, the loop exits.
- **F144** `tests/test_services/test_health_service.py`: with Radarr and Sonarr on different paths, `get_disk_space()` returns both. A path shared by two apps appears once.
- **F141** `tests/test_dockerfile.py` and `tests/test_docker_compose.py`: the healthcheck checks the heartbeat file age, not `pgrep`. `tests/test_main.py`: the loop touches the heartbeat file.
- **F142** `tests/test_main.py`: on SIGTERM, `application.shutdown()` runs and the client sessions are closed.
- **F147** `tests/test_docker_compose.py`: the service sets logging `max-size: 10m` and `max-file: 3`.
- **F148** Docs only, no test. `README.md` says that about 7000+ movies need a limit above 256M. `docker-compose.yml` still sets 256M.
- **F143** `tests/test_main.py`: the shutdown log line contains no literal `{Fore.YELLOW}`.
- **F146** `tests/test_services/test_health_service.py`: the health output goes to the logger and nothing goes to stdout (`capsys`).
- `pytest`, `flake8` and `mypy src/` pass.

## Notes

- Source: audit 2026-10-28, docs/issues/audit-2026-10-28/FINDINGS.md (F-ids F145, F140, F144, F141, F142, F147, F148, F143, F146).
- Priority: max P 25, sum P 159 (high).
- Order: do slices 1-8 first. The Dockerfile lines above include the uncommitted pip change that slice 19 (F153) commits.
- Decided 2026-10-28: F148 keep the 256M limit; README says large libraries (about 7000+ movies) need a higher limit.
