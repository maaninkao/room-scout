from room_scout.models import Listing, FilterConfig
from room_scout.filters import matches


def _listing(**kwargs) -> Listing:
    defaults = dict(slug="tn-2024-01-a", url="https://example.com/tn-2024-01-a")
    return Listing(**{**defaults, **kwargs})


def test_pass_all_filters():
    listing = _listing(price_eur=500, size_sqm=20, address="Via Roma 1", recently_booked=False)
    f = FilterConfig(max_price=600, min_sqm=15, address_must_contain=["roma"])
    ok, reason = matches(listing, f)
    assert ok, reason


def test_reject_by_price():
    listing = _listing(price_eur=800)
    f = FilterConfig(max_price=700)
    ok, reason = matches(listing, f)
    assert not ok
    assert "price" in reason


def test_reject_recently_booked_by_default():
    listing = _listing(recently_booked=True)
    f = FilterConfig()
    ok, reason = matches(listing, f)
    assert not ok
    assert "recently_booked" in reason


def test_include_recently_booked_when_flag_set():
    listing = _listing(recently_booked=True, price_eur=400)
    f = FilterConfig(include_recently_booked=True, max_price=500)
    ok, _ = matches(listing, f)
    assert ok


def test_reject_by_min_price():
    listing = _listing(price_eur=300)
    f = FilterConfig(min_price=400)
    ok, reason = matches(listing, f)
    assert not ok
    assert "price" in reason


def test_reject_address_must_contain():
    listing = _listing(address="Via Verdi 5")
    f = FilterConfig(address_must_contain=["Roma", "Centro"])
    ok, reason = matches(listing, f)
    assert not ok
    assert "address" in reason


def test_reject_address_must_not_contain():
    listing = _listing(address="Via Roma Centrale")
    f = FilterConfig(address_must_not_contain=["centrale"])
    ok, reason = matches(listing, f)
    assert not ok
    assert "centrale" in reason.lower()


def test_none_fields_skipped():
    listing = _listing(price_eur=None, size_sqm=None)
    f = FilterConfig(max_price=500, min_sqm=10)
    ok, _ = matches(listing, f)
    assert ok
