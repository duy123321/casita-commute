"""User-declared places you travel to regularly, loaded from places.yaml.

Distinct from the curated anchors in walk.py: those are lifestyle amenities
("nearest good bakery"). These are obligations — you go to work whether or
not the listing is convenient — so each carries an importance weight, its own
travel mode, and its own acceptable-time target.

The file is gitignored: a home/work address pair is exactly the private data
the public-repo contract keeps out of the tree. places.example.yaml is the
committed template. Missing file => [] and the feature disappears cleanly.
"""
import os
from dataclasses import dataclass
from pathlib import Path

import yaml

from .walk import Anchor

_DEFAULT_PATH = Path(__file__).parent.parent.parent / "places.yaml"
_VALID_MODES = {"walk", "drive", "transit"}
_VALID_IMPORTANCE = {1, 2, 3}
_MODE_DEFAULT_TARGET = {"walk": 20, "drive": 25, "transit": 40}


@dataclass(frozen=True)
class Place(Anchor):
    """An Anchor you have an obligation to reach, not just a preference for."""
    importance: int = 2        # 1 = near-daily, 3 = occasional
    mode: str = "drive"
    cadence: str | None = None
    target_minutes: int = 25


def places_path() -> Path:
    return Path(os.environ.get("CASITA_PLACES_PATH", str(_DEFAULT_PATH)))


def load_places(path: Path | None = None) -> list[Place]:
    """Parse places.yaml. Missing file -> []; the feature is opt-in.

    Raises ValueError on a malformed entry — a typo'd importance should be
    loud, not silently coerced into a weight you didn't intend.
    """
    path = path or places_path()
    if not path.exists():
        return []
    raw = yaml.safe_load(path.read_text()) or {}
    entries = raw.get("commutes") or []

    names: set[str] = set()
    out: list[Place] = []
    for i, entry in enumerate(entries):
        label = entry.get("name") or f"commutes[{i}]"

        name = entry.get("name")
        if not name:
            raise ValueError(f"{label}: 'name' is required")
        if name in names:
            raise ValueError(f"{label}: duplicate 'name' — names must be unique")
        names.add(name)

        if "lat" not in entry or "lng" not in entry:
            raise ValueError(f"{label}: 'lat' and 'lng' are required")
        lat, lng = float(entry["lat"]), float(entry["lng"])

        importance = entry.get("importance", 2)
        if importance not in _VALID_IMPORTANCE:
            raise ValueError(f"{label}: importance must be 1, 2, or 3, got {importance!r}")

        mode = entry.get("mode", "drive")
        if mode not in _VALID_MODES:
            raise ValueError(f"{label}: mode must be one of {sorted(_VALID_MODES)}, got {mode!r}")

        target_minutes = entry.get("target_minutes", _MODE_DEFAULT_TARGET[mode])

        out.append(Place(
            name=name,
            short=entry.get("short", name),
            lat=lat,
            lng=lng,
            place_id=entry.get("place_id"),
            importance=importance,
            mode=mode,
            cadence=entry.get("cadence"),
            target_minutes=target_minutes,
        ))
    return out
