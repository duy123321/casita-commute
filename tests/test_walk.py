import sqlite3
from datetime import datetime
from zoneinfo import ZoneInfo

from casita import walk
from casita.models import Listing
from casita.places import Place


def _listing(source_id: str, lat: float, lng: float) -> Listing:
    return Listing(source="manual", source_id=source_id, url="https://example.com", lat=lat, lng=lng)


def test_routes_api_disabled_without_key(monkeypatch):
    monkeypatch.delenv("GOOGLE_MAPS_API_KEY", raising=False)
    monkeypatch.delenv("CASITA_ROUTES_OFFLINE", raising=False)

    assert walk._routes_api_enabled() is False


def test_routes_api_disabled_when_offline(monkeypatch):
    monkeypatch.setenv("GOOGLE_MAPS_API_KEY", "fake-key")
    monkeypatch.setenv("CASITA_ROUTES_OFFLINE", "1")

    assert walk._routes_api_enabled() is False


def test_routes_api_enabled_with_key(monkeypatch):
    monkeypatch.setenv("GOOGLE_MAPS_API_KEY", "fake-key")
    monkeypatch.delenv("CASITA_ROUTES_OFFLINE", raising=False)

    assert walk._routes_api_enabled() is True


def test_ensure_cache_migrates_mode_into_primary_key(tmp_path):
    db_path = tmp_path / "routes.sqlite"
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            """CREATE TABLE walk_cache (
                from_lat REAL, from_lng REAL,
                to_lat REAL, to_lng REAL,
                mode TEXT NOT NULL DEFAULT 'walk',
                minutes INTEGER NOT NULL,
                source TEXT NOT NULL,
                ts TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (from_lat, from_lng, to_lat, to_lng)
            )"""
        )
        conn.execute(
            "INSERT INTO walk_cache "
            "(from_lat, from_lng, to_lat, to_lng, mode, minutes, source) "
            "VALUES (1, 2, 3, 4, 'walk', 10, 'api')"
        )
        walk._ensure_cache(conn)

        pk_cols = {row[1] for row in conn.execute("PRAGMA table_info(walk_cache)") if row[5]}
        assert "mode" in pk_cols

        conn.execute(
            "INSERT INTO walk_cache "
            "(from_lat, from_lng, to_lat, to_lng, mode, minutes, source) "
            "VALUES (1, 2, 3, 4, 'drive', 5, 'api')"
        )
        count = conn.execute(
            "SELECT COUNT(*) FROM walk_cache WHERE from_lat=1 AND from_lng=2"
        ).fetchone()[0]
        assert count == 2


def test_next_weekday_departure_is_weekday_morning():
    departure = walk._next_weekday_departure()
    assert departure.endswith("Z")
    dt_utc = datetime.strptime(departure, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=ZoneInfo("UTC"))
    local = dt_utc.astimezone(walk._PACIFIC)
    assert local.weekday() < 5  # Mon-Fri
    assert (local.hour, local.minute) == (8, 30)


def test_haversine_for_mode_dispatches_by_mode():
    anchor = walk.Anchor("Anchor", "Anchor", 37.79, -122.40)
    walk_m = walk._haversine_for_mode("walk", 37.77, -122.42, anchor)
    drive_m = walk._haversine_for_mode("drive", 37.77, -122.42, anchor)
    transit_m = walk._haversine_for_mode("transit", 37.77, -122.42, anchor)

    assert walk_m == walk._haversine_minutes(37.77, -122.42, anchor)
    assert drive_m == walk._haversine_drive_minutes(37.77, -122.42, anchor)
    assert transit_m == walk._haversine_transit_minutes(37.77, -122.42, anchor)
    assert transit_m > drive_m  # transit penalty (×1.8) over raw drive time


def test_populate_for_places_empty_places_returns_empty():
    assert walk.populate_for_places([_listing("a", 37.77, -122.42)], []) == {}


def test_populate_for_places_offline_groups_calls_by_mode(monkeypatch, tmp_path):
    monkeypatch.setenv("CASITA_ROUTES_OFFLINE", "1")
    monkeypatch.setenv("CASITA_ROUTE_CACHE_DB", str(tmp_path / "routes.sqlite"))

    listing = _listing("a", 37.7749, -122.4194)
    places = [
        Place(name="Work", short="Work", lat=37.7897, lng=-122.3972,
              mode="transit", target_minutes=35),
        Place(name="Gym", short="Gym", lat=37.7590, lng=-122.3880,
              mode="drive", target_minutes=20),
    ]

    modes_called: list[str] = []
    real_call = walk._call_routes_api

    def spy(*args, **kwargs):
        modes_called.append(kwargs.get("mode"))
        return real_call(*args, **kwargs)

    monkeypatch.setattr(walk, "_call_routes_api", spy)

    result = walk.populate_for_places([listing], places)

    assert sorted(modes_called) == ["drive", "transit"]  # one call per mode group
    assert result[(listing.key, "Work")] > 0
    assert result[(listing.key, "Gym")] > 0


def test_populate_for_places_is_cached_on_second_call(monkeypatch, tmp_path):
    monkeypatch.setenv("CASITA_ROUTES_OFFLINE", "1")
    monkeypatch.setenv("CASITA_ROUTE_CACHE_DB", str(tmp_path / "routes.sqlite"))

    listing = _listing("a", 37.7749, -122.4194)
    places = [Place(name="Work", short="Work", lat=37.7897, lng=-122.3972, mode="drive")]

    first = walk.populate_for_places([listing], places)

    call_count = 0
    real_call = walk._call_routes_api

    def spy(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        return real_call(*args, **kwargs)

    monkeypatch.setattr(walk, "_call_routes_api", spy)
    second = walk.populate_for_places([listing], places)

    assert second == first
    assert call_count == 0  # fully served from cache, no API/fallback call issued
