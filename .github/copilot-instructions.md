# Project Guidelines: 35mm Film Shot Tracker

Use this file for project-wide rules only. For feature usage and UI walkthroughs, see README.md. For manual QA, see .github/manual-smoke-test.instructions.md.

## Architecture

Tkinter desktop app with clear layer boundaries:

- `db.py`: `FilmDatabase` owns SQLite schema creation, CRUD, and preference storage.
- `film_tracker.py`: `FilmTrackerApp`, dialogs, and event handlers.
- `film_catalog.py`: film stock reference/catalog utilities loaded from JSON.
- `roll_log.py`: roll lifecycle tracking with JSON persistence.

Design patterns to preserve:

- Use context-managed DB connections (`with self._connect()`).
- Keep SQL parameterized (`?` placeholders).
- Keep validation centralized in `ValidationUtils` for UI and CSV paths.
- Keep dialogs modal (`transient()` + `grab_set()`) and use `.show()` flow.

## Code Style

- Python 3.10+ type hints on function signatures.
- Small, focused helpers for parsing/normalizing optional values.
- Avoid duplicated logic across UI and DB layers unless both paths require it.
- Preserve existing naming and status constants (`STATUS_VALUES`).

## Build and Verify

Run locally:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python film_tracker.py
```

Quick syntax sanity check before handing off larger changes:

```bash
python -m compileall db.py film_tracker.py film_catalog.py roll_log.py
```

Testing status:

- No automated tests currently exist.
- Run the manual checklist in .github/manual-smoke-test.instructions.md after UI, DB, CSV, or preferences changes.

## Conventions

Schema and migrations:

- Current schema is created idempotently in `FilmDatabase._create_schema()`.
- `LATEST_SCHEMA_VERSION` currently tracks schema version via `PRAGMA user_version`.
- If introducing future migrations, keep upgrade steps explicit and safe to re-run.

Validation and normalization:

- Validate form and CSV inputs before DB calls.
- Raise `ValueError` with user-facing messages, then surface via dialogs.
- Keep `ValidationUtils.normalize_optional_text()` and `FilmDatabase.normalize_optional_text()` behavior in sync.

Preferences:

- Preferences are string values in SQLite key-value storage.
- Boolean preferences are serialized as `"true"` / `"false"` strings.
- Camera/lens preset lists are pipe-delimited strings.

UI state:

- Preserve selected collection/shot IDs across UI refreshes.
- Reload table/list views after any mutation.
- Keep `_load_shots_for_selected_collection()` as the standard refresh path.

## Bug and Typo Review Focus

When asked to look for bugs or typos, prioritize:

- Behavioral regressions in save/edit/delete/import/export flows.
- Validation mismatches between form input, CSV import, and DB constraints.
- Typos in preference keys, status values, SQL column names, and JSON keys.
- User-facing text issues in dialogs, error messages, and labels.

Report findings with file paths and concrete impact first, then suggest minimal fixes.

## Known Gotchas

- No automated tests; manual smoke checks are required.
- Text normalization logic exists in both UI and DB code paths.
- Changing the status filter immediately updates the stored `default_status_filter` preference.
- Errors are primarily surfaced via message boxes (minimal logging).
