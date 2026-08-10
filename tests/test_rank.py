from casita.models import Listing
from casita.places import Place
from casita.rank import _commute_bonus, rank, score


def _listing(source_id: str, **kwargs) -> Listing:
    return Listing(source="manual", source_id=source_id, url="https://example.com", **kwargs)


def _place(name: str, importance: int, target_minutes: int) -> Place:
    return Place(name=name, short=name, lat=37.79, lng=-122.40,
                 importance=importance, mode="drive", target_minutes=target_minutes)


def test_commute_bonus_zero_with_no_places():
    assert _commute_bonus({}, "any-key", []) == 0
    assert _commute_bonus(None, "any-key", []) == 0


def test_commute_bonus_zero_when_place_missing_from_map():
    work = _place("Work", importance=1, target_minutes=35)
    assert _commute_bonus({}, "listing-1", [work]) == 0


def test_commute_bonus_positive_within_target():
    work = _place("Work", importance=1, target_minutes=35)
    place_map = {("listing-1", "Work"): 30}
    assert _commute_bonus(place_map, "listing-1", [work]) == round(15 * 3.0)


def test_commute_bonus_negative_far_over_target():
    work = _place("Work", importance=1, target_minutes=35)
    place_map = {("listing-1", "Work"): 90}  # > 2x target
    assert _commute_bonus(place_map, "listing-1", [work]) == round(-15 * 3.0)


def test_commute_bonus_scales_with_importance():
    near_daily = _place("Work", importance=1, target_minutes=30)
    occasional = _place("Parents", importance=3, target_minutes=30)
    place_map = {("listing-1", "Work"): 20, ("listing-1", "Parents"): 20}

    daily_bonus = _commute_bonus(place_map, "listing-1", [near_daily])
    occasional_bonus = _commute_bonus(place_map, "listing-1", [occasional])
    assert daily_bonus > occasional_bonus > 0


def test_score_unchanged_when_no_places_passed():
    L = _listing("a", dog_policy="dogs_ok", beds=3, baths=2)
    assert score(L) == score(L, place_map={("a", "Work"): 90}, places=None)
    assert score(L) == score(L, place_map=None, places=[])


def test_score_penalizes_bad_commute():
    work = _place("Work", importance=1, target_minutes=30)
    L = _listing("a", dog_policy="dogs_ok", beds=3, baths=2)
    good = score(L, place_map={(L.key, "Work"): 20}, places=[work])
    bad = score(L, place_map={(L.key, "Work"): 90}, places=[work])
    assert good > bad


def test_rank_breaks_ties_on_commute_when_everything_else_equal():
    work = _place("Work", importance=1, target_minutes=30)
    close = _listing("near", dog_policy="dogs_ok", beds=3, baths=2)
    far = _listing("far", dog_policy="dogs_ok", beds=3, baths=2)
    place_map = {(close.key, "Work"): 15, (far.key, "Work"): 90}

    ordered = rank([far, close], place_map=place_map, places=[work])
    assert [L.key for L in ordered] == [close.key, far.key]
