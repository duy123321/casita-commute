import pytest

from casita.places import load_places, places_path


def _write(tmp_path, text):
    path = tmp_path / "places.yaml"
    path.write_text(text)
    return path


def test_load_places_missing_file_returns_empty(tmp_path):
    assert load_places(tmp_path / "nope.yaml") == []


def test_load_places_empty_file_returns_empty(tmp_path):
    path = _write(tmp_path, "")
    assert load_places(path) == []


def test_load_places_parses_full_entry(tmp_path):
    path = _write(tmp_path, """
commutes:
  - name: "Work — Financial District"
    short: Work
    lat: 37.7897
    lng: -122.3972
    importance: 1
    mode: transit
    cadence: "weekdays"
    target_minutes: 35
""")
    places = load_places(path)
    assert len(places) == 1
    p = places[0]
    assert p.name == "Work — Financial District"
    assert p.short == "Work"
    assert p.lat == 37.7897
    assert p.lng == -122.3972
    assert p.importance == 1
    assert p.mode == "transit"
    assert p.cadence == "weekdays"
    assert p.target_minutes == 35


def test_load_places_applies_defaults(tmp_path):
    path = _write(tmp_path, """
commutes:
  - name: "Gym"
    lat: 37.759
    lng: -122.388
""")
    p = load_places(path)[0]
    assert p.short == "Gym"          # defaults to name
    assert p.importance == 2
    assert p.mode == "drive"
    assert p.cadence is None
    assert p.target_minutes == 25    # drive default


def test_load_places_target_minutes_defaults_by_mode(tmp_path):
    path = _write(tmp_path, """
commutes:
  - name: "Walkable place"
    lat: 37.75
    lng: -122.40
    mode: walk
  - name: "Transit place"
    lat: 37.76
    lng: -122.41
    mode: transit
""")
    walk_place, transit_place = load_places(path)
    assert walk_place.target_minutes == 20
    assert transit_place.target_minutes == 40


def test_load_places_rejects_invalid_importance(tmp_path):
    path = _write(tmp_path, """
commutes:
  - name: "Bad"
    lat: 37.75
    lng: -122.40
    importance: 5
""")
    with pytest.raises(ValueError, match="importance"):
        load_places(path)


def test_load_places_rejects_invalid_mode(tmp_path):
    path = _write(tmp_path, """
commutes:
  - name: "Bad"
    lat: 37.75
    lng: -122.40
    mode: bike
""")
    with pytest.raises(ValueError, match="mode"):
        load_places(path)


def test_load_places_rejects_missing_coordinates(tmp_path):
    path = _write(tmp_path, """
commutes:
  - name: "No coords"
""")
    with pytest.raises(ValueError, match="lat"):
        load_places(path)


def test_load_places_rejects_duplicate_names(tmp_path):
    path = _write(tmp_path, """
commutes:
  - name: "Dup"
    lat: 37.75
    lng: -122.40
  - name: "Dup"
    lat: 37.76
    lng: -122.41
""")
    with pytest.raises(ValueError, match="duplicate"):
        load_places(path)


def test_places_path_honors_env_override(monkeypatch, tmp_path):
    custom = tmp_path / "custom.yaml"
    monkeypatch.setenv("CASITA_PLACES_PATH", str(custom))
    assert places_path() == custom
