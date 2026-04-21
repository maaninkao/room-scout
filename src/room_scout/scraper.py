"""HTML scraper — parses Joivy listing pages into Listing objects (Strategy B: selectolax)."""
import logging
import re
from datetime import date, datetime
from pathlib import Path
from typing import Optional

from selectolax.parser import HTMLParser

from .models import Listing

logger = logging.getLogger(__name__)

_BASE_URL = "https://coliving.joivy.com"
_SLUG_RE = re.compile(r'/(tn-\d{4}-\d{2}-[a-z])/?$')
_PRICE_RE = re.compile(r'€\s*(\d+(?:[.,]\d+)?)')
_DATE_RE = re.compile(r'From\s+(\d{1,2}\s+\w+\s+\d{4})')


def _parse_date(text: str) -> Optional[date]:
    m = _DATE_RE.search(text)
    if not m:
        return None
    for fmt in ("%d %b %Y", "%d %B %Y"):
        try:
            return datetime.strptime(m.group(1), fmt).date()
        except ValueError:
            continue
    return None


def _parse_card(node) -> Optional[Listing]:
    href = node.attributes.get('href', '')
    slug_m = _SLUG_RE.search(href)
    if not slug_m:
        return None

    slug = slug_m.group(1)
    url = _BASE_URL + href

    title = node.attributes.get('title') or ''
    address = title.split(' - ', 1)[1] if ' - ' in title else None

    img = node.css_first('img')
    image_url = img.attributes.get('src') if img else None

    card_text = node.text(separator=' ')

    price_m = _PRICE_RE.search(card_text)
    price_eur = float(price_m.group(1).replace(',', '.')) if price_m else None

    recently_booked = 'Recently Booked' in card_text
    available_from = None if recently_booked else _parse_date(card_text)

    size_sqm = None
    flatmates = None
    for span in node.css('span'):
        classes = span.attributes.get('class') or ''
        if 'leading-5' not in classes:
            continue
        t = span.text().strip()
        if 'm²' in t:
            m = re.search(r'(\d+(?:\.\d+)?)', t)
            if m:
                size_sqm = float(m.group(1))
        elif t.isdigit():
            flatmates = int(t)

    return Listing(
        slug=slug,
        url=url,
        title=title or None,
        address=address,
        size_sqm=size_sqm,
        flatmates=flatmates,
        price_eur=price_eur,
        available_from=available_from,
        recently_booked=recently_booked,
        image_url=image_url,
    )


def parse_html(html: str) -> list[Listing]:
    """Parse a Joivy listing page HTML and return all Listing objects found."""
    tree = HTMLParser(html)
    listings = []
    seen: set[str] = set()
    for node in tree.css('a[href*="/en/rent-single-room-trento-"]'):
        href = node.attributes.get('href', '')
        slug_m = _SLUG_RE.search(href)
        if not slug_m:
            continue
        slug = slug_m.group(1)
        if slug in seen:
            continue
        seen.add(slug)
        try:
            listing = _parse_card(node)
            if listing:
                listings.append(listing)
        except Exception:
            logger.warning("Failed to parse card with href=%s", href, exc_info=True)
    return listings


def scrape_fixture(path: "str | Path | None" = None) -> list[Listing]:
    """Parse listings from the local fixture file (no live HTTP requests)."""
    if path is None:
        path = Path(__file__).parent.parent.parent / 'tests' / 'fixtures' / 'trento_sample.html'
    html = Path(path).read_text(encoding='utf-8')
    return parse_html(html)
