"""Click CLI entry points for room-scout."""

import click

from .config import load_config
from .filters import matches
from .models import Listing
from .notifier import send_notification
from .scraper import fetch_live
from .storage import Storage


@click.group()
def main():
    """Room Scout — monitor Joivy coliving listings and push new matches via ntfy.sh."""


@main.command("run-once")
def run_once():
    """Fetch listings, filter new matches, send push notifications."""
    config = load_config()
    storage = Storage(config.db_path)

    listings = fetch_live(config)

    found = len(listings)
    new_count = 0
    matched_count = 0
    notified_count = 0

    for listing in listings:
        is_new = storage.mark_seen(listing)
        if is_new:
            new_count += 1
            ok, _ = matches(listing, config.filters)
            if ok:
                matched_count += 1
                send_notification(config, listing)
                storage.mark_notified(listing.slug)
                notified_count += 1

    storage.close()
    click.echo(f"Found {found}, {new_count} new, {matched_count} matched, {notified_count} notified")


@main.command("test-notify")
def test_notify():
    """Send a test push notification to verify ntfy setup."""
    from datetime import date

    config = load_config()
    test_listing = Listing(
        slug="test-room",
        url="https://coliving.joivy.com/en/rent-single-room-trento-test",
        title="Test Room — Via Test 1, Trento",
        address="Via Test 1, Trento",
        size_sqm=20.0,
        price_eur=500.0,
        available_from=date.today(),
    )
    send_notification(config, test_listing)
    click.echo("Test notification sent.")
