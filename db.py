import sqlite3
from pathlib import Path
from typing import Any, Optional


class FilmDatabase:
    def __init__(self, db_path: str = "data/film_tracker.db") -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    def _initialize(self) -> None:
        with self._connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS collections (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL CHECK (trim(name) <> ''),
                    created_at TEXT NOT NULL DEFAULT (datetime('now'))
                );

                CREATE TABLE IF NOT EXISTS shots (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    collection_id INTEGER NOT NULL,
                    shutter_speed TEXT NOT NULL CHECK (trim(shutter_speed) <> ''),
                    f_stop TEXT NOT NULL CHECK (trim(f_stop) <> ''),
                    frame_number INTEGER,
                    shot_date TEXT,
                    notes TEXT,
                    created_at TEXT NOT NULL DEFAULT (datetime('now')),
                    FOREIGN KEY (collection_id) REFERENCES collections(id) ON DELETE CASCADE,
                    CHECK (frame_number IS NULL OR frame_number > 0)
                );

                CREATE INDEX IF NOT EXISTS idx_shots_collection_id
                    ON shots(collection_id);

                CREATE UNIQUE INDEX IF NOT EXISTS idx_unique_frame_per_collection
                    ON shots(collection_id, frame_number)
                    WHERE frame_number IS NOT NULL;
                """
            )

    # Collection operations
    def list_collections(self) -> list[sqlite3.Row]:
        with self._connect() as conn:
            cursor = conn.execute(
                """
                SELECT id, name, created_at
                FROM collections
                ORDER BY name COLLATE NOCASE, id
                """
            )
            return cursor.fetchall()

    def create_collection(self, name: str) -> int:
        with self._connect() as conn:
            cursor = conn.execute(
                "INSERT INTO collections (name) VALUES (?)",
                (name.strip(),),
            )
            return int(cursor.lastrowid)

    def rename_collection(self, collection_id: int, new_name: str) -> None:
        with self._connect() as conn:
            conn.execute(
                "UPDATE collections SET name = ? WHERE id = ?",
                (new_name.strip(), collection_id),
            )

    def delete_collection(self, collection_id: int) -> None:
        with self._connect() as conn:
            conn.execute("DELETE FROM collections WHERE id = ?", (collection_id,))

    # Shot operations
    def list_shots_for_collection(self, collection_id: int) -> list[sqlite3.Row]:
        with self._connect() as conn:
            cursor = conn.execute(
                """
                SELECT id, shutter_speed, f_stop, frame_number, shot_date, notes, created_at
                FROM shots
                WHERE collection_id = ?
                ORDER BY
                    CASE WHEN frame_number IS NULL THEN 1 ELSE 0 END,
                    frame_number,
                    id
                """,
                (collection_id,),
            )
            return cursor.fetchall()

    def create_shot(
        self,
        collection_id: int,
        shutter_speed: str,
        f_stop: str,
        frame_number: Optional[int],
        shot_date: Optional[str],
        notes: Optional[str],
    ) -> int:
        with self._connect() as conn:
            cursor = conn.execute(
                """
                INSERT INTO shots (
                    collection_id, shutter_speed, f_stop, frame_number, shot_date, notes
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    collection_id,
                    shutter_speed.strip(),
                    f_stop.strip(),
                    frame_number,
                    shot_date,
                    notes,
                ),
            )
            return int(cursor.lastrowid)

    def update_shot(
        self,
        shot_id: int,
        shutter_speed: str,
        f_stop: str,
        frame_number: Optional[int],
        shot_date: Optional[str],
        notes: Optional[str],
    ) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE shots
                SET shutter_speed = ?,
                    f_stop = ?,
                    frame_number = ?,
                    shot_date = ?,
                    notes = ?
                WHERE id = ?
                """,
                (
                    shutter_speed.strip(),
                    f_stop.strip(),
                    frame_number,
                    shot_date,
                    notes,
                    shot_id,
                ),
            )

    def delete_shot(self, shot_id: int) -> None:
        with self._connect() as conn:
            conn.execute("DELETE FROM shots WHERE id = ?", (shot_id,))

    def get_shot(self, shot_id: int) -> Optional[sqlite3.Row]:
        with self._connect() as conn:
            cursor = conn.execute(
                """
                SELECT id, collection_id, shutter_speed, f_stop, frame_number, shot_date, notes
                FROM shots
                WHERE id = ?
                """,
                (shot_id,),
            )
            return cursor.fetchone()

    def shot_count_for_collection(self, collection_id: int) -> int:
        with self._connect() as conn:
            cursor = conn.execute(
                "SELECT COUNT(*) AS count FROM shots WHERE collection_id = ?",
                (collection_id,),
            )
            row = cursor.fetchone()
            return int(row["count"]) if row else 0

    @staticmethod
    def normalize_optional_text(value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        stripped = value.strip()
        return stripped if stripped else None

    @staticmethod
    def normalize_optional_int(value: Optional[str]) -> Optional[int]:
        if value is None:
            return None
        stripped = value.strip()
        if not stripped:
            return None
        return int(stripped)

    @staticmethod
    def row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
        return {key: row[key] for key in row.keys()}
