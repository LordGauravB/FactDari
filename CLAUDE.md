# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

Install and run:

```bash
pip install -r util/requirements_factdari.txt
python factdari.py              # desktop widget (tkinter)
python analytics_factdari.py    # Flask dashboard at http://localhost:5000
```

Testing (pytest, config in [pytest.ini](pytest.ini)):

```bash
pytest                                              # run all; auto-writes HTML to templates/report.html
pytest tests/test_gamification.py                   # single file
pytest tests/test_gamification.py::TestLevelCalculation   # single class
pytest -m "not slow and not integration"            # skip DB/slow tests
pytest -m integration                               # DB-backed tests (needs SQL Server + FactDari DB)
pytest --cov=. --cov-report=html
```

Custom markers: `slow`, `integration` (needs DB), `ui` (needs tkinter). [tests/conftest.py](tests/conftest.py) auto-blocks external HTTP (localhost only) and disables Flask-Limiter during tests.

Database setup: run [database_setup/factdari_setup.sql](database_setup/factdari_setup.sql) against SQL Server / SQL Server Express. Schema reference: [database_setup/schema_definitions.md](database_setup/schema_definitions.md).

## Architecture

Three Python modules at the repo root form the system. They share one SQL Server database (connection built by `config.get_connection_string()`, ODBC via `pyodbc`). There is no ORM — all SQL is hand-written and executed through `pyodbc` cursors.

**[factdari.py](factdari.py) — Desktop widget** (~3.9k lines, single `FactDariApp` class). A tkinter always-on-top frameless window. Owns the review loop: opens a `ReviewSessions` row in `start_reviewing()`, writes a `FactLogs` row per view in `track_fact_view()`, pauses the per-view timer whenever a modal opens (shortcuts, AI explain, edit/add/delete, question display, category dropdown — see README "Review Timer Pausing"), and finalizes views on inactivity via `IDLE_TIMEOUT_SECONDS`. Also embeds the Together AI client for on-demand explanations and question generation — any AI call writes an `AIUsageLogs` row with tokens/cost/latency.

**[analytics_factdari.py](analytics_factdari.py) — Flask dashboard** (~2.2k lines). Read-only over the same DB. Every chart/table endpoint is a separate route returning JSON; the frontend ([templates/analytics_factdari.html](templates/analytics_factdari.html) + [static/js](static/js)) renders via Chart.js. CSRF is on by default (Flask-WTF), and rate limiting is enforced via Flask-Limiter using `ANALYTICS_CONFIG['rate_limit_per_minute']`. Tests disable the limiter via the autouse fixture.

**[gamification.py](gamification.py) — XP / levels / streaks / achievements**. Single `Gamification` class backed by `GamificationProfile`, `Achievements`, `AchievementUnlocks`. `award_xp()` applies XP and recomputes level against the banded curve in `LEVELING_CONFIG`. `daily_checkin()` advances or resets `CurrentStreak` based on `LastCheckinDate`. Counter increments use an **allowlist** (`ALLOWED_COUNTER_FIELDS`) and an explicit field→SQL map — do not replace with dynamic field interpolation. `factdari.py` calls into this module; `analytics_factdari.py` only reads the resulting rows.

### Key cross-cutting conventions

- **[config.py](config.py) is the single source of truth.** Everything tunable — DB connection, ODBC driver, XP amounts, level bands, AI pricing/endpoint, idle timeout, analytics windows, colors/fonts, logging — reads from env vars with defaults there. Add new tunables here rather than hardcoding.
- **Logging** is via `config.setup_logging('factdari.<module>')` with rotating file handler in `logs/`. Reuse the helper instead of configuring `logging` directly.
- **Level 100 is gated**: even when XP crosses the threshold, stored `Level` caps at 99 until every achievement is unlocked. Any XP/level change should keep this invariant.
- **Analytics scoping**: `Facts.CreatedBy` and `Categories.CreatedBy` scope rows to the active profile. New analytics queries must filter by the active `ProfileID` to match existing charts.
- **Question refresh lifecycle**: `Facts.QuestionsRefreshCountdown` starts at 50 and decrements per review. Hitting 0 triggers deletion of old `Questions` for that fact, regeneration via Together AI, and reset to 50. Keep this contract if you touch question code.
- **Together AI**: model/endpoint/pricing live in `AI_PRICING` / `AI_REQUEST_CONFIG`. Every call must log to `AIUsageLogs` with input/output tokens, computed cost, latency, status, and provider — analytics and `GamificationProfile.TotalAI*` counters depend on it.

### Database tables to know

`Categories`, `Facts`, `ProfileFacts` (per-profile state: `IsFavorite`, `IsEasy`, `KnownSince`, `LastViewedByUser`), `ReviewSessions`, `FactLogs` (one per view/action, can outlive deleted facts via content snapshot), `GamificationProfile`, `Achievements`, `AchievementUnlocks`, `AIUsageLogs`, `Questions`, `QuestionLogs`. Full column-level docs in [database_setup/schema_definitions.md](database_setup/schema_definitions.md).

## Platform notes

Windows-only for the desktop widget (uses `pywin32`, `ctypes.wintypes`, `pyttsx3` SAPI). The shell for this environment is bash — use forward slashes and Unix shell syntax in scripts; the app itself still targets Windows at runtime. `analytics_factdari.py` runs Flask in debug for local use — do not expose publicly.
