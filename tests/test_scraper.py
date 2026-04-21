"""Tests for scraper.py — parses Joivy HTML fixture into Listing objects."""
import re
from pathlib import Path

import pytest

from room_scout.scraper import scrape_fixture

FIXTURE = Path(__file__).parent / 'fixtures' / 'trento_sample.html'
SLUG_RE = re.compile(r'^tn-\d{4}-\d{2}-[a-z]$')


@pytest.fixture(scope='module')
def listings():
    return scrape_fixture(FIXTURE)


def test_returns_at_least_five_listings(listings):
    assert len(listings) >= 5


def test_all_slugs_match_pattern(listings):
    for listing in listings:
        assert SLUG_RE.match(listing.slug), f"Bad slug: {listing.slug}"


def test_at_least_one_recently_booked(listings):
    assert any(l.recently_booked for l in listings)


def test_listings_have_urls(listings):
    for listing in listings:
        assert listing.url.startswith('https://coliving.joivy.com')


def test_listings_have_prices(listings):
    with_price = [l for l in listings if l.price_eur is not None]
    assert len(with_price) >= 5
