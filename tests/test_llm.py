from casita import llm, storage
from casita.models import Listing
from casita.places import Place


def _listing(source_id: str, **kwargs) -> Listing:
    return Listing(source="manual", source_id=source_id, url="https://example.com", **kwargs)


def test_commute_summary_empty_without_places():
    L = _listing("a", lat=37.77, lng=-122.42)
    assert llm._commute_summary(L, None, []) == ""
    assert llm._commute_summary(L, {}, []) == ""


def test_commute_summary_formats_and_sorts_by_importance():
    L = _listing("a")
    work = Place(name="Work", short="Work", lat=37.79, lng=-122.40,
                 importance=1, mode="transit", target_minutes=35, cadence="weekdays")
    gym = Place(name="Gym", short="Gym", lat=37.75, lng=-122.38,
                importance=2, mode="drive", target_minutes=20)
    place_map = {(L.key, "Work"): 38, (L.key, "Gym"): 14}

    # Passed in importance-descending order; summary must still lead with
    # the near-daily place regardless of input order.
    summary = llm._commute_summary(L, place_map, [gym, work])
    assert summary == "COMMUTES: Work 38m transit (target 35, weekdays), Gym 14m drive (target 20)"


def test_commute_summary_skips_places_without_a_computed_time():
    L = _listing("a")
    work = Place(name="Work", short="Work", lat=37.79, lng=-122.40, importance=1)
    assert llm._commute_summary(L, {}, [work]) == ""


def test_rank_system_documents_commute_filter_threshold():
    assert "COMMUTES" in llm._RANK_SYSTEM
    assert 'severity="filtered"' in llm._RANK_SYSTEM
    assert "importance=1" in llm._RANK_SYSTEM


def test_rank_listings_prompt_byte_identical_without_places(monkeypatch, tmp_path):
    """Same discipline as _preference_examples on cold start: the prompt sent
    to the model must not change shape when there's no places.yaml.
    """
    monkeypatch.setenv("CASITA_DB_PATH", str(tmp_path / "casita.sqlite"))
    L = _listing("a", lat=37.7749, lng=-122.4194, dog_policy="dogs_ok", beds=3, baths=2)

    captured: list[str] = []

    def fake_call_structured(model, system, content, schema, **kwargs):
        captured.append(content)
        return None

    monkeypatch.setattr(llm, "_call_structured", fake_call_structured)

    with storage.connect() as conn:
        llm.rank_listings([L], {}, conn)
        llm.rank_listings([L], {}, conn, place_map=None, places=None)
        llm.rank_listings([L], {}, conn, place_map={}, places=[])

    assert captured[0] == captured[1] == captured[2]
    assert "COMMUTES" not in captured[0]


def test_rank_listings_prompt_carries_commutes_when_places_present(monkeypatch, tmp_path):
    monkeypatch.setenv("CASITA_DB_PATH", str(tmp_path / "casita.sqlite"))
    L = _listing("a", lat=37.7749, lng=-122.4194, dog_policy="dogs_ok", beds=3, baths=2)
    work = Place(name="Work", short="Work", lat=37.79, lng=-122.40,
                 importance=1, mode="transit", target_minutes=35, cadence="weekdays")

    captured: list[str] = []

    def fake_call_structured(model, system, content, schema, **kwargs):
        captured.append(content)
        return None

    monkeypatch.setattr(llm, "_call_structured", fake_call_structured)

    with storage.connect() as conn:
        llm.rank_listings([L], {}, conn, place_map={(L.key, "Work"): 40}, places=[work])

    assert "COMMUTES: Work 40m transit (target 35, weekdays)" in captured[0]
