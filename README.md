# llm-experiments

## 35mm Film Shot Tracker

This repository now includes a Tkinter desktop app for tracking film shots per roll collection.

### Features

- Roll collections (for example: Portra 400 - Roll 3)
- Shot entries inside each collection
- Shot fields:
	- Shutter speed
	- F-stop
	- Frame number (optional)
	- Shot date (optional, `YYYY-MM-DD`)
	- Notes (optional)
	- Status (`shot`, `developed`, `scanned`, `edited`, `printed`)
- SQLite persistence at `data/film_tracker.db`
- Delete protection prompts for collections and shots
- Automatic schema migration support (uses SQLite `PRAGMA user_version`)

### Run

1. Ensure Python 3.10+ is installed.
2. Start the app:

```bash
python3 film_tracker.py
```

No third-party packages are required (`tkinter` and `sqlite3` are from the Python standard library).

### Data Model

- `collections`
	- `id` (PK)
	- `name`
	- `created_at`
- `shots`
	- `id` (PK)
	- `collection_id` (FK -> collections.id, cascade delete)
	- `shutter_speed`
	- `f_stop`
	- `frame_number` (optional)
	- `shot_date` (optional)
	- `notes` (optional)
	- `status` (default: `shot`)
	- `created_at`

Frame numbers are unique within the same collection when provided.

### Usage

1. Add a collection from the left panel.
2. Select a collection.
3. Enter shot details in the form on the right.
4. Click `Save Shot` to add a new shot.
5. Select an existing shot to edit, then click `Save Shot`.
6. Use `Delete Shot` or `Delete` (collection) to remove data.

### Manual Smoke Test Checklist

1. Launch app and verify `data/film_tracker.db` is created.
2. Add a collection and restart app to verify persistence.
3. Add multiple shots and verify they appear in the shot table.
4. Edit one shot and verify values update.
5. Delete a shot and verify removal.
6. Delete a collection and verify associated shots are removed.