from casita import html
from casita.models import Listing
from casita.places import Place


def _listing(source_id: str, **kwargs) -> Listing:
    return Listing(source="manual", source_id=source_id, url="https://example.com", **kwargs)


def test_commute_class_thresholds():
    assert html._commute_class(20, 35) == "v"           # within target
    assert html._commute_class(35, 35) == "v"            # exactly at target
    assert html._commute_class(50, 35) == "v caution"    # > 1.4x (49)
    assert html._commute_class(71, 35) == "v warn"       # > 2.0x (70)


def test_worst_commute_none_without_data():
    L = _listing("a")
    assert html._worst_commute(None, L, []) is None
    assert html._worst_commute({}, L, []) is None


def test_worst_commute_ignores_non_importance_1():
    L = _listing("a")
    gym = Place(name="Gym", short="Gym", lat=37.75, lng=-122.38, importance=2, target_minutes=20)
    place_map = {(L.key, "Gym"): 90}  # way over target, but not importance=1
    assert html._worst_commute(place_map, L, [gym]) is None


def test_worst_commute_picks_largest_overage_ratio():
    L = _listing("a")
    work = Place(name="Work", short="Work", lat=37.79, lng=-122.40, importance=1, target_minutes=30)
    school = Place(name="School", short="School", lat=37.78, lng=-122.41, importance=1, target_minutes=10)
    # Work: 40/30 = 1.33x. School: 25/10 = 2.5x — school is "worse" by ratio.
    place_map = {(L.key, "Work"): 40, (L.key, "School"): 25}

    worst = html._worst_commute(place_map, L, [work, school])
    assert worst[0].name == "School"
    assert worst[1] == 25


def test_card_shows_commute_chip_for_importance_1_place():
    L = _listing("a", price=5000, beds=2, baths=1, dog_policy="dogs_ok")
    work = Place(name="Work", short="Work", lat=37.79, lng=-122.40, importance=1, target_minutes=30)
    place_map = {(L.key, "Work"): 90}  # 3x over target -> warn

    rendered = html._card(L, place_map=place_map, places=[work])
    assert "Work · 90m" in rendered
    assert "chip-commute-warn" in rendered


def test_card_omits_commute_chip_without_places():
    L = _listing("a", price=5000, beds=2, baths=1, dog_policy="dogs_ok")
    rendered = html._card(L)
    assert "chip-commute" not in rendered


def test_render_threads_place_map_into_cards():
    L = _listing("a", price=5000, beds=2, baths=1, dog_policy="dogs_ok", llm_severity="ok")
    work = Place(name="Work", short="Work", lat=37.79, lng=-122.40, importance=1, target_minutes=30)
    place_map = {(L.key, "Work"): 10}  # within target -> neutral chip

    rendered = html.render([L], place_map=place_map, places=[work])
    assert "Work · 10m" in rendered
