from casita import listing_page
from casita.models import Listing
from casita.places import Place


def _listing(source_id: str, **kwargs) -> Listing:
    return Listing(source="manual", source_id=source_id, url="https://example.com",
                    lat=37.7749, lng=-122.4194, **kwargs)


def test_render_kv_omits_commutes_section_without_places():
    L = _listing("a")
    rendered = listing_page._render_kv(L, walk_map=None, drive_map=None, drive_bakery=None)
    assert "Commutes" not in rendered


def test_render_kv_renders_commutes_sorted_by_importance():
    L = _listing("a")
    work = Place(name="Work", short="Work", lat=37.79, lng=-122.40,
                 importance=1, mode="transit", target_minutes=35, cadence="weekdays")
    gym = Place(name="Gym", short="Gym", lat=37.75, lng=-122.38,
                importance=2, mode="drive", target_minutes=20)
    place_map = {(L.key, "Work"): 38, (L.key, "Gym"): 14}

    # Passed importance-descending; output must lead with the near-daily place.
    rendered = listing_page._render_kv(
        L, walk_map=None, drive_map=None, drive_bakery=None,
        place_map=place_map, places=[gym, work],
    )
    assert "Commutes" in rendered
    work_pos = rendered.index("Work")
    gym_pos = rendered.index("Gym")
    assert work_pos < gym_pos
    assert "38 min" in rendered and "transit" in rendered
    assert "(weekdays)" in rendered


def test_render_kv_skips_place_without_a_computed_time():
    L = _listing("a")
    work = Place(name="Work", short="Work", lat=37.79, lng=-122.40, importance=1)
    rendered = listing_page._render_kv(
        L, walk_map=None, drive_map=None, drive_bakery=None,
        place_map={}, places=[work],
    )
    assert "Commutes" not in rendered
