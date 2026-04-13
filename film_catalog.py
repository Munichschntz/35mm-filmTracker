"""Film stock catalog: model, filtering, search, and recommendation."""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


# ---------------------------------------------------------------------------
# Model
# ---------------------------------------------------------------------------

@dataclass
class FilmStock:
    id: str
    name: str
    manufacturer: str
    type: str          # color_negative | black_and_white | slide | cinema
    process: str       # C-41 | BW | E-6 | ECN-2
    iso: int
    iso_native: Optional[int] = None
    is_rebranded: bool = False
    cinema_derived: bool = False
    notes: Optional[str] = None
    active: bool = True

    @property
    def is_push_pull_sensitive(self) -> bool:
        return self.iso_native is not None and self.iso != self.iso_native

    @property
    def exposure_warning(self) -> Optional[str]:
        if self.id == "cinestill_800t":
            return (
                "CineStill 800T is tungsten-balanced. Expect warm/orange cast in daylight "
                "and characteristic halation glow around highlights. Rate at ISO 800 and "
                "adjust white balance if shooting under daylight or mixed sources."
            )
        if self.id == "kodak_tmax_p3200":
            return (
                "T-Max P3200 has a native ISO of ~800–1000. For best results, expose at "
                "1600–3200 and request push processing (+1 to +2 stops) from your lab."
            )
        if self.id == "ilford_delta_3200":
            return (
                "Delta 3200 has a native ISO of ~1000. Expose at 1600–3200 and request "
                "push processing. Higher ratings yield increased but atmospheric grain."
            )
        if self.is_push_pull_sensitive:
            iso_native = self.iso_native or self.iso
            stops = abs(math.log2(self.iso / iso_native))
            stop_text = f"{stops:.1f}" if not stops.is_integer() else str(int(stops))
            direction = "push" if self.iso > (self.iso_native or self.iso) else "pull"
            return (
                f"This stock is rated at ISO {self.iso} but its native sensitivity is "
                f"ISO {self.iso_native}. Consider {direction} processing and adjust "
                f"exposure accordingly (~{stop_text} stop difference)."
            )
        return None


# ---------------------------------------------------------------------------
# Catalog
# ---------------------------------------------------------------------------

_SCENARIO_EXPLANATIONS: dict[str, dict[str, str]] = {
    "portrait": {
        "kodak_portra_160": "Portra 160 — ultra-fine grain, natural skin tones in bright light.",
        "kodak_portra_400": "Portra 400 — industry-standard portrait film, beautiful skin tones, wide latitude.",
        "kodak_portra_800": "Portra 800 — retains warmth and skin tones in lower portrait lighting.",
        "kodak_gold_200": "Gold 200 — warm tones complement skin well at an accessible price.",
        "_default": "Warm-toned C-41 film well-suited for portrait work.",
    },
    "low_light": {
        "kodak_portra_800": "Portra 800 — high-speed portrait film with excellent shadow detail.",
        "cinestill_800t": "CineStill 800T — cinema-grade 800 ISO; iconic look for low-light scenes.",
        "ilford_hp5_plus": "HP5 Plus — pushes cleanly to 1600 or 3200 for very low light.",
        "kodak_tmax_p3200": "T-Max P3200 — rated 3200; designed for available-light shooting.",
        "ilford_delta_3200": "Delta 3200 — high-speed B&W with distinctive atmospheric grain.",
        "_default": "High ISO film suitable for low-light conditions.",
    },
    "landscape": {
        "kodak_ektar_100": "Ektar 100 — world's finest-grain color negative; ultra-saturated for landscapes.",
        "velvia_50": "Velvia 50 — legendary saturation and micro-contrast for nature photography.",
        "velvia_100": "Velvia 100 — slightly more flexible than Velvia 50; still beautifully saturated.",
        "ektachrome_e100": "Ektachrome E100 — cool, neutral slide film; vivid greens and blues.",
        "provia_100f": "Provia 100F — balanced transparency film; versatile for landscapes.",
        "_default": "Fine-grain, saturated film well-suited for landscape work.",
    },
    "budget": {
        "kodak_ultramax_400": "UltraMax 400 — versatile, affordable Kodak consumer film.",
        "kentmere_400": "Kentmere 400 — excellent budget B&W; good latitude for everyday shooting.",
        "fujifilm_200": "Fujifilm 200 — inexpensive entry-level film; neutral/cool tones.",
        "fujifilm_400": "Fujifilm 400 — budget-friendly 400-speed; cool/green character.",
        "_default": "Cost-effective film that delivers good results for everyday shooting.",
    },
    "night": {
        "cinestill_800t": "CineStill 800T — the definitive night film; tungsten-balanced with dreamy halation.",
        "kodak_portra_800": "Portra 800 — high-speed color negative; cleaner look for night portraits.",
        "kodak_tmax_p3200": "T-Max P3200 — rated 3200; designed for available-light night shooting.",
        "ilford_delta_3200": "Delta 3200 — high-speed B&W with grain that suits gritty night scenes.",
        "ilford_hp5_plus": "HP5 Plus — pushes to 3200 and handles night lighting gracefully.",
        "_default": "High-speed film suitable for night and low-available-light scenes.",
    },
}


def _score_film(film: FilmStock, scenario: str) -> int:
    """Return a numeric priority score for a film under the given scenario."""
    if scenario == "portrait":
        if film.id in ("kodak_portra_160", "kodak_portra_400", "kodak_portra_800"):
            return 3
        if film.id == "kodak_gold_200":
            return 2
        if film.process == "C-41" and film.type == "color_negative" and film.iso <= 400:
            return 1
        return 0

    if scenario == "low_light":
        if film.iso >= 800:
            return 3
        if film.iso >= 400:
            return 1
        return 0

    if scenario == "landscape":
        if film.id in ("kodak_ektar_100", "velvia_50", "velvia_100"):
            return 3
        if film.process == "E-6":
            return 2
        return 0

    if scenario == "budget":
        if film.id in ("kodak_ultramax_400", "kentmere_400"):
            return 3
        if film.id in ("fujifilm_200", "fujifilm_400"):
            return 2
        if film.process == "C-41" and film.iso >= 200:
            return 1
        return 0

    if scenario == "night":
        if film.id == "cinestill_800t":
            return 5
        if film.iso >= 800 and film.type == "color_negative":
            return 2
        if film.iso >= 800:
            return 1
        return 0

    return 0


class FilmCatalog:
    VALID_SCENARIOS = ("portrait", "low_light", "landscape", "budget", "night")

    def __init__(self, json_path: str = "json/film_stocks.json") -> None:
        self._json_path = Path(json_path)
        self._films: list[FilmStock] = []

    def load(self) -> None:
        """Load and parse film_stocks.json. Raises FileNotFoundError if missing."""
        if not self._json_path.exists():
            raise FileNotFoundError(f"Film stock data not found: {self._json_path}")
        with self._json_path.open(encoding="utf-8") as fh:
            data = json.load(fh)
        self._films = [
            FilmStock(
                id=entry["id"],
                name=entry["name"],
                manufacturer=entry.get("manufacturer", ""),
                type=entry.get("type", ""),
                process=entry.get("process", ""),
                iso=int(entry["iso"]),
                iso_native=int(entry["iso_native"]) if entry.get("iso_native") else None,
                is_rebranded=bool(entry.get("is_rebranded", False)),
                cinema_derived=bool(entry.get("cinema_derived", False)),
                notes=entry.get("notes") or None,
                active=bool(entry.get("active", True)),
            )
            for entry in data.get("films", [])
        ]

    def _active(self) -> list[FilmStock]:
        return [f for f in self._films if f.active]

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def filter(
        self,
        iso_min: int | None = None,
        iso_max: int | None = None,
        film_type: str | None = None,
        process: str | None = None,
        active_only: bool = True,
    ) -> list[FilmStock]:
        """Return films matching all supplied criteria, sorted by ISO ascending."""
        pool = self._active() if active_only else list(self._films)
        results: list[FilmStock] = []
        for film in pool:
            if iso_min is not None and film.iso < iso_min:
                continue
            if iso_max is not None and film.iso > iso_max:
                continue
            if film_type and film.type != film_type:
                continue
            if process and film.process != process:
                continue
            results.append(film)
        return sorted(results, key=lambda f: f.iso)

    def search(self, query: str) -> list[FilmStock]:
        """Case-insensitive substring search on film name, sorted by ISO ascending."""
        q = query.strip().lower()
        if not q:
            return sorted(self._active(), key=lambda f: f.iso)
        return sorted(
            [f for f in self._active() if q in f.name.lower()],
            key=lambda f: f.iso,
        )

    def get_by_id(self, film_id: str) -> Optional[FilmStock]:
        """Return the film with the given id, or None if not found."""
        for film in self._films:
            if film.id == film_id:
                return film
        return None

    def recommend(self, scenario: str) -> list[tuple[FilmStock, str]]:
        """Return top 3 film recommendations for the given scenario with explanations.

        Each tuple contains (FilmStock, explanation_string).
        Raises ValueError for unknown scenarios.
        """
        if scenario not in self.VALID_SCENARIOS:
            raise ValueError(
                f"Unknown scenario '{scenario}'. "
                f"Valid scenarios: {', '.join(self.VALID_SCENARIOS)}"
            )
        explanations = _SCENARIO_EXPLANATIONS[scenario]
        scored = [
            (film, _score_film(film, scenario))
            for film in self._active()
        ]
        scored = [(f, s) for f, s in scored if s > 0]
        scored.sort(key=lambda x: (-x[1], x[0].iso))

        results: list[tuple[FilmStock, str]] = []
        for film, _ in scored[:3]:
            base = explanations.get(film.id, explanations.get("_default", ""))
            warning = film.exposure_warning
            if warning:
                explanation = f"{base}\n\u26a0\ufe0f {warning}"
            else:
                explanation = base
            results.append((film, explanation))
        return results
