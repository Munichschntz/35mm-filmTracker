"""Roll tracking: model and persistent JSON-backed log."""

from __future__ import annotations

import json
import uuid
from dataclasses import asdict, dataclass, field
from datetime import date
from pathlib import Path
from typing import Optional

from film_catalog import FilmCatalog


# ---------------------------------------------------------------------------
# Model
# ---------------------------------------------------------------------------

@dataclass
class Roll:
    roll_id: str
    film_id: str
    camera: str
    lens: Optional[str] = None
    date_loaded: str = ""
    date_finished: Optional[str] = None
    notes: Optional[str] = None
    status: str = "loaded"          # loaded | in_progress | finished | developed
    frames_shot: int = 0
    location: Optional[str] = None
    lab: Optional[str] = None
    scanned: bool = False

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "Roll":
        return cls(
            roll_id=data["roll_id"],
            film_id=data["film_id"],
            camera=data["camera"],
            lens=data.get("lens"),
            date_loaded=data.get("date_loaded", ""),
            date_finished=data.get("date_finished"),
            notes=data.get("notes"),
            status=data.get("status", "loaded"),
            frames_shot=int(data.get("frames_shot", 0)),
            location=data.get("location"),
            lab=data.get("lab"),
            scanned=bool(data.get("scanned", False)),
        )


# ---------------------------------------------------------------------------
# Repository
# ---------------------------------------------------------------------------

class RollLog:
    VALID_STATUSES = ("loaded", "in_progress", "finished", "developed")

    def __init__(
        self,
        catalog: FilmCatalog,
        json_path: str = "data/rolls.json",
    ) -> None:
        self._catalog = catalog
        self._path = Path(json_path)
        self._path.parent.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # Persistence helpers
    # ------------------------------------------------------------------

    def _load(self) -> list[Roll]:
        if not self._path.exists():
            return []
        with self._path.open(encoding="utf-8") as fh:
            raw = json.load(fh)
        return [Roll.from_dict(entry) for entry in raw]

    def _save(self, rolls: list[Roll]) -> None:
        with self._path.open("w", encoding="utf-8") as fh:
            json.dump([r.to_dict() for r in rolls], fh, indent=2, ensure_ascii=False)

    def _find_roll(self, rolls: list[Roll], roll_id: str) -> Roll:
        for r in rolls:
            if r.roll_id == roll_id:
                return r
        raise ValueError(f"Roll '{roll_id}' not found.")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def create_roll(
        self,
        film_id: str,
        camera: str,
        lens: Optional[str] = None,
        location: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> Roll:
        """Create and persist a new loaded roll.

        Raises ValueError if film_id does not exist in the catalog.
        """
        if not camera.strip():
            raise ValueError("Camera name must not be empty.")
        if self._catalog.get_by_id(film_id) is None:
            raise ValueError(
                f"Unknown film id '{film_id}'. Load the catalog before creating rolls."
            )
        roll = Roll(
            roll_id=str(uuid.uuid4()),
            film_id=film_id,
            camera=camera.strip(),
            lens=lens.strip() if lens and lens.strip() else None,
            date_loaded=date.today().isoformat(),
            location=location.strip() if location and location.strip() else None,
            notes=notes.strip() if notes and notes.strip() else None,
            status="loaded",
            frames_shot=0,
        )
        rolls = self._load()
        rolls.append(roll)
        self._save(rolls)
        return roll

    def increment_frame(self, roll_id: str) -> Roll:
        """Increment frames_shot by 1. Auto-sets status to 'in_progress'."""
        rolls = self._load()
        roll = self._find_roll(rolls, roll_id)
        roll.frames_shot += 1
        if roll.status == "loaded":
            roll.status = "in_progress"
        self._save(rolls)
        return roll

    def mark_finished(self, roll_id: str) -> Roll:
        """Mark the roll as finished and record today as date_finished."""
        rolls = self._load()
        roll = self._find_roll(rolls, roll_id)
        roll.date_finished = date.today().isoformat()
        roll.status = "finished"
        self._save(rolls)
        return roll

    def set_developed(
        self,
        roll_id: str,
        lab: Optional[str] = None,
        scanned: bool = False,
    ) -> Roll:
        """Mark the roll as developed; optionally record lab and scanned flag."""
        rolls = self._load()
        roll = self._find_roll(rolls, roll_id)
        roll.status = "developed"
        if lab:
            roll.lab = lab.strip() or None
        roll.scanned = scanned
        self._save(rolls)
        return roll

    def attach_note(self, roll_id: str, note: str) -> Roll:
        """Append to this roll's notes field (separated by a newline)."""
        note = note.strip()
        if not note:
            raise ValueError("Note must not be empty.")
        rolls = self._load()
        roll = self._find_roll(rolls, roll_id)
        if roll.notes:
            roll.notes = f"{roll.notes}\n{note}"
        else:
            roll.notes = note
        self._save(rolls)
        return roll

    def list_rolls(self) -> list[Roll]:
        """Return all rolls, most-recently-loaded first."""
        return list(reversed(self._load()))

    def get_roll(self, roll_id: str) -> Optional[Roll]:
        """Return the roll with the given id, or None if not found."""
        for r in self._load():
            if r.roll_id == roll_id:
                return r
        return None
