# Project Guidelines: 35mm Film Shot Tracker

## Architecture

A **Tkinter desktop application** for tracking analog film shots with a clean separation of concerns:

- **`db.py`** — `FilmDatabase` class handles all persistence (SQLite CRUD, schema migrations, preferences)
- **`film_tracker.py`** — UI layer with `FilmTrackerApp` (main window), dialogs, and event handlers
- **`ValidationUtils`** — Static utility class for input validation (ISO, frame numbers, dates, text normalization)

### Key Design Patterns

1. **Database Connectivity**
   - Context managers (`with self._connect()`) ensure connections are committed/rolled back
   - Parameterized queries prevent SQL injection
   - `sqlite3.Row` objects returned to UI for easy dict-like access

2. **Schema Migrations**
   - Version-based system using `PRAGMA user_version`
   - Sequential if-blocks in `_initialize()` (v1→v5)
   - Idempotent operations ensure safe re-runs

3. **Input Validation**
   - `ValidationUtils` provides static methods for optional fields: `parse_optional_iso()`, `parse_optional_frame()`, `parse_optional_date()`, `normalize_optional_text()`
   - Used in form submission and CSV import to ensure consistency
   - Raises `ValueError` with user-friendly messages

4. **Preferences as Key-Value Store**
   - Stored in SQLite preferences table
   - Retrieved as strings and dynamically parsed (e.g., pipe-delimited lists for presets)
   - Defaults fallback for missing keys

5. **Modal Dialogs**
   - Use `CollectionMetadataDialog` pattern: create, call `.show()`, handle result
   - Always `transient()` and `grab_set()` to block parent

## Code Style

- **Type hints** required for all function signatures (Python 3.10+)
- **Context managers** for resource cleanup (DB connections, file I/O)
- **Static utility methods** for reusable logic
- **Parameterized queries** (`?` placeholders) for all SQL
- **Enum-like tuples** for constants (e.g., `STATUS_VALUES`)
- **Null-safe operations** via `normalize_optional_*()` helpers

Example:
```python
@staticmethod
def parse_optional_iso(value: str | None) -> int | None:
    if value is None:
        return None
    stripped = value.strip()
    if not stripped:
        return None
    parsed = int(stripped)
    if parsed <= 0:
        raise ValueError("ISO must be a positive number.")
    return parsed
```

## Build and Test

### Run Locally

**Linux/macOS:**
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python film_tracker.py
```

**Windows (PowerShell):**
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python film_tracker.py
```

Or use `run.bat` from File Explorer to automate the above.

### Dependencies

- **ttkbootstrap** — Theming for Tkinter
- **tkinter, sqlite3** — Standard library

### Testing

⚠️ **No automated tests exist.** Manual testing required for:
- CSV import/export functionality
- Database schema migrations (when schema changes)
- Status filter and bulk operations
- Dialog form validation

Use the dedicated manual checklist in `.github/manual-smoke-test.instructions.md` for a full end-to-end smoke pass.

Consider adding unit tests for `ValidationUtils` and `FilmDatabase` for confidence in future refactoring.

## Conventions

### Database Migrations

When modifying the schema:
1. Increment `LATEST_SCHEMA_VERSION` in `FilmDatabase`
2. Add a new `_migrate_to_vX()` method with `CREATE TABLE`, `ALTER TABLE`, etc.
3. Chain it in `_initialize()` with `if current_version < X:` block

### Validation

- Always validate user input before database operations
- Use `ValidationUtils` methods; don't duplicate validation logic
- Catch `ValueError` and display in modal dialogs (not console)

### UI State Management

- Track selected collection/shot IDs in instance variables
- Reload table views after any database mutation (create/update/delete)
- Use `_load_shots_for_selected_collection()` pattern for consistency

## Known Gotchas

1. **Dual Normalization** — Text normalization happens in *both* `FilmDatabase` and `ValidationUtils`. If you change one, update the other to stay in sync.

2. **No Logging** — Errors are shown as messagebox dialogs. Debugging server/database issues requires adding print statements or logging.

3. **No Test Suite** — CSV import, migrations, and bulk status updates are only tested manually. High refactoring risk.

4. **Preference Defaults on Startup** — New preference keys added in code default to hardcoded defaults if missing in DB until manually saved.

5. **Status Filter Not Persisted** — Current filter resets to the default status on app restart (not the last selected filter).

6. **Race Condition in Frame Uniqueness** — Frame number uniqueness is checked before insert but not wrapped in a transaction. In single-user Tkinter app this is unlikely but theoretically possible.

## Recommended Next Steps

- Add `tests/test_validation.py` and `tests/test_db.py` for regression detection
- Add basic logging (file or stderr) for debugging
- Extract business logic (shot filtering, status workflows) into a service layer
- Consider JSON/pickle for preferences instead of manual pipe-delimited parsing
