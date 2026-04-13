import sqlite3
from pathlib import Path
from typing import Any, Optional


class FilmDatabase:
    LATEST_SCHEMA_VERSION = 1

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
            self._create_schema(conn)
            if self._get_schema_version(conn) != self.LATEST_SCHEMA_VERSION:
                self._set_schema_version(conn, self.LATEST_SCHEMA_VERSION)

    @staticmethod
    def _create_schema(conn: sqlite3.Connection) -> None:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS collections (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL CHECK (trim(name) <> ''),
                film_stock TEXT,
                iso INTEGER,
                camera TEXT,
                lens TEXT,
                lab TEXT,
                push_pull TEXT,
                capacity INTEGER,
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
                status TEXT NOT NULL DEFAULT 'shot',
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                FOREIGN KEY (collection_id) REFERENCES collections(id) ON DELETE CASCADE,
                CHECK (frame_number IS NULL OR frame_number > 0)
            );

            CREATE TABLE IF NOT EXISTS preferences (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_shots_collection_id
                ON shots(collection_id);

            CREATE UNIQUE INDEX IF NOT EXISTS idx_unique_frame_per_collection
                ON shots(collection_id, frame_number)
                WHERE frame_number IS NOT NULL;
            """
        )

        default_preferences = {
            "camera_presets": "",
            "lens_presets": "",
            "last_selected_collection_id": "",
        }
        for key, value in default_preferences.items():
            conn.execute(
                """
                INSERT OR IGNORE INTO preferences (key, value)
                VALUES (?, ?)
                """,
                (key, value),
            )

    @staticmethod
    def _get_schema_version(conn: sqlite3.Connection) -> int:
        cursor = conn.execute("PRAGMA user_version")
        row = cursor.fetchone()
        return int(row[0]) if row else 0

    @staticmethod
    def _set_schema_version(conn: sqlite3.Connection, version: int) -> None:
        conn.execute(f"PRAGMA user_version = {version}")

    # Collection operations
    def list_collections(self) -> list[sqlite3.Row]:
        with self._connect() as conn:
            cursor = conn.execute(
                """
                SELECT
                    c.id,
                    c.name,
                    c.film_stock,
                    c.iso,
                    c.camera,
                    c.lens,
                    c.lab,
                    c.push_pull,
                    c.capacity,
                    c.created_at,
                    (SELECT COUNT(*) FROM shots WHERE collection_id = c.id) AS shot_count
                FROM collections c
                ORDER BY c.name COLLATE NOCASE, c.id
                """
            )
            return cursor.fetchall()

    def create_collection(
        self,
        name: str,
        film_stock: Optional[str] = None,
        iso: Optional[int] = None,
        camera: Optional[str] = None,
        lens: Optional[str] = None,
        lab: Optional[str] = None,
        push_pull: Optional[str] = None,
        capacity: Optional[int] = None,
    ) -> int:
        with self._connect() as conn:
            cursor = conn.execute(
                """
                INSERT INTO collections (name, film_stock, iso, camera, lens, lab, push_pull, capacity)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    name.strip(),
                    self.normalize_optional_text(film_stock),
                    iso,
                    self.normalize_optional_text(camera),
                    self.normalize_optional_text(lens),
                    self.normalize_optional_text(lab),
                    self.normalize_optional_text(push_pull),
                    capacity,
                ),
            )
            return int(cursor.lastrowid)

    def get_collection(self, collection_id: int) -> Optional[sqlite3.Row]:
        with self._connect() as conn:
            cursor = conn.execute(
                """
                SELECT id, name, film_stock, iso, camera, lens, lab, push_pull, capacity, created_at
                FROM collections
                WHERE id = ?
                """,
                (collection_id,),
            )
            return cursor.fetchone()

    def rename_collection(self, collection_id: int, new_name: str) -> None:
        with self._connect() as conn:
            conn.execute(
                "UPDATE collections SET name = ? WHERE id = ?",
                (new_name.strip(), collection_id),
            )

    def update_collection_metadata(
        self,
        collection_id: int,
        name: str,
        film_stock: Optional[str],
        iso: Optional[int],
        camera: Optional[str],
        lens: Optional[str],
        lab: Optional[str],
        push_pull: Optional[str],
        capacity: Optional[int] = None,
    ) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE collections
                SET name = ?,
                    film_stock = ?,
                    iso = ?,
                    camera = ?,
                    lens = ?,
                    lab = ?,
                    push_pull = ?,
                    capacity = ?
                WHERE id = ?
                """,
                (
                    name.strip(),
                    self.normalize_optional_text(film_stock),
                    iso,
                    self.normalize_optional_text(camera),
                    self.normalize_optional_text(lens),
                    self.normalize_optional_text(lab),
                    self.normalize_optional_text(push_pull),
                    capacity,
                    collection_id,
                ),
            )

    def delete_collection(self, collection_id: int) -> None:
        with self._connect() as conn:
            conn.execute("DELETE FROM collections WHERE id = ?", (collection_id,))

    # Shot operations
    def list_shots_for_collection(self, collection_id: int, status: Optional[str] = None) -> list[sqlite3.Row]:
        with self._connect() as conn:
            query = """
                SELECT id, shutter_speed, f_stop, frame_number, shot_date, notes, status, created_at
                FROM shots
                WHERE collection_id = ?
            """
            params: tuple[Any, ...] = (collection_id,)

            if status is not None:
                query += " AND status = ?"
                params += (status,)

            query += """
                ORDER BY
                    CASE WHEN frame_number IS NULL THEN 1 ELSE 0 END,
                    frame_number,
                    id
            """

            cursor = conn.execute(query, params)
            return cursor.fetchall()

    def next_frame_number_for_collection(self, collection_id: int) -> int:
        with self._connect() as conn:
            cursor = conn.execute(
                """
                SELECT MAX(frame_number) AS max_frame
                FROM shots
                WHERE collection_id = ?
                """,
                (collection_id,),
            )
            row = cursor.fetchone()
            max_frame = row["max_frame"] if row else None
            return int(max_frame) + 1 if max_frame is not None else 1

    def frame_number_exists(
        self,
        collection_id: int,
        frame_number: int,
        exclude_shot_id: Optional[int] = None,
    ) -> bool:
        with self._connect() as conn:
            query = """
                SELECT 1
                FROM shots
                WHERE collection_id = ?
                  AND frame_number = ?
            """
            params: tuple[Any, ...] = (collection_id, frame_number)
            if exclude_shot_id is not None:
                query += " AND id != ?"
                params += (exclude_shot_id,)

            query += " LIMIT 1"
            row = conn.execute(query, params).fetchone()
            return row is not None

    def create_shot(
        self,
        collection_id: int,
        shutter_speed: str,
        f_stop: str,
        frame_number: Optional[int],
        shot_date: Optional[str],
        notes: Optional[str],
        status: str = "shot",
    ) -> int:
        with self._connect() as conn:
            cursor = conn.execute(
                """
                INSERT INTO shots (
                    collection_id, shutter_speed, f_stop, frame_number, shot_date, notes, status
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    collection_id,
                    shutter_speed.strip(),
                    f_stop.strip(),
                    frame_number,
                    shot_date,
                    notes,
                    status,
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
        status: str = "shot",
    ) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE shots
                SET shutter_speed = ?,
                    f_stop = ?,
                    frame_number = ?,
                    shot_date = ?,
                    notes = ?,
                    status = ?
                WHERE id = ?
                """,
                (
                    shutter_speed.strip(),
                    f_stop.strip(),
                    frame_number,
                    shot_date,
                    notes,
                    status,
                    shot_id,
                ),
            )

    def update_shot_status(self, shot_id: int, status: str) -> None:
        with self._connect() as conn:
            conn.execute(
                "UPDATE shots SET status = ? WHERE id = ?",
                (status, shot_id),
            )

    def update_shot_status_many(self, shot_ids: list[int], status: str) -> int:
        if not shot_ids:
            return 0

        placeholders = ", ".join("?" for _ in shot_ids)
        query = f"UPDATE shots SET status = ? WHERE id IN ({placeholders})"
        with self._connect() as conn:
            cursor = conn.execute(query, (status, *shot_ids))
            return int(cursor.rowcount)

    def delete_shot(self, shot_id: int) -> None:
        with self._connect() as conn:
            conn.execute("DELETE FROM shots WHERE id = ?", (shot_id,))

    def get_shot(self, shot_id: int) -> Optional[sqlite3.Row]:
        with self._connect() as conn:
            cursor = conn.execute(
                """
                SELECT id, collection_id, shutter_speed, f_stop, frame_number, shot_date, notes, status
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

    def export_shots_for_collection(self, collection_id: int) -> list[sqlite3.Row]:
        with self._connect() as conn:
            cursor = conn.execute(
                """
                SELECT
                    frame_number,
                    status,
                    shutter_speed,
                    f_stop,
                    shot_date,
                    notes,
                    created_at
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

    def bulk_insert_shots(
        self,
        collection_id: int,
        shots: list[dict[str, Any]],
    ) -> tuple[int, list[str]]:
        inserted = 0
        errors: list[str] = []
        with self._connect() as conn:
            for index, shot in enumerate(shots, start=1):
                source_row = shot.get("_source_line", index)
                try:
                    conn.execute(
                        """
                        INSERT INTO shots (
                            collection_id,
                            shutter_speed,
                            f_stop,
                            frame_number,
                            shot_date,
                            notes,
                            status
                        ) VALUES (?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            collection_id,
                            str(shot["shutter_speed"]).strip(),
                            str(shot["f_stop"]).strip(),
                            shot.get("frame_number"),
                            shot.get("shot_date"),
                            shot.get("notes"),
                            shot.get("status", "shot"),
                        ),
                    )
                    inserted += 1
                except sqlite3.IntegrityError as exc:
                    errors.append(f"Row {source_row}: {exc}")

        return inserted, errors

    # Preferences
    def get_preferences(self) -> dict[str, str]:
        with self._connect() as conn:
            cursor = conn.execute("SELECT key, value FROM preferences")
            return {str(row["key"]): str(row["value"]) for row in cursor.fetchall()}

    def get_preference(self, key: str, default: Optional[str] = None) -> Optional[str]:
        with self._connect() as conn:
            cursor = conn.execute("SELECT value FROM preferences WHERE key = ?", (key,))
            row = cursor.fetchone()
            if row is None:
                return default
            return str(row["value"])

    def set_preference(self, key: str, value: str) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO preferences (key, value)
                VALUES (?, ?)
                ON CONFLICT(key) DO UPDATE SET value = excluded.value
                """,
                (key, value),
            )

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
