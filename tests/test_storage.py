"""Tests for the SQLite storage layer."""

import pytest
from room_scout.models import Listing
from room_scout.storage import Storage


@pytest.fixture
def store(tmp_path):
    s = Storage(str(tmp_path / "sub" / "test.db"))
    yield s
    s.close()


def _listing(slug="tn-2024-01-a"):
    return Listing(slug=slug, url=f"https://joivy.com/en/rent-single-room-trento-coliving/{slug}")


def test_insert_new_returns_true(store):
    assert store.mark_seen(_listing()) is True


def test_insert_same_returns_false(store):
    listing = _listing()
    store.mark_seen(listing)
    assert store.mark_seen(listing) is False


def test_mark_notified_persists(store):
    listing = _listing()
    store.mark_seen(listing)
    assert store.was_notified(listing.slug) is False
    store.mark_notified(listing.slug)
    assert store.was_notified(listing.slug) is True
