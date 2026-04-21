"""Click CLI entry points for room-scout."""

import logging

import click

from .config import load_config
from .filters import matches
from .models import Listing
from .notifier import send_notification
from .scraper import fetch_live
from .storage import Storage

logger = logging.getLogger(__name__)


@click.group()
def main():
    """Room Scout — monitor Joivy coliving listings and push new matches via ntfy.sh."""


@main.command("run-once")
def run_once():
    """Fetch listings, filter new matches, send push notifications.

    Per-listing errors are logged and swallowed — one bad card does not
    stop the loop. A listing is marked "seen"+"notified" only AFTER a
    successful push, so ntfy failures are retried on the next run.
    """
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    config = load_config()
    storage = Storage(config.db_path)

    try:
        listings = fetch_live(config)
    except Exception as e:
        logger.exception("fetch_live failed: %s", e)
        storage.close()
        raise click.ClickException(f"Failed to fetch listings: {e}")

    found = len(listings)
    new_count = 0
    matched_count = 0
    notified_count = 0
    error_count = 0

    for listing in listings:
        try:
            if storage.was_notified(listing.slug):
                continue

            ok, _reason = matches(listing, config.filters)

            if not ok:
                is_new = storage.mark_seen(listing)
                if is_new:
                    new_count += 1
                continue

            matched_count += 1
            try:
                send_notification(config, listing)
            except Exception as push_err:
                error_count += 1
                logger.error(
                    "send_notification failed for %s: %s — will retry next run",
                    listing.slug, push_err,
                    exc_info=True,
                )
                continue

            is_new = storage.mark_seen(listing)
            if is_new:
                new_count += 1
            storage.mark_notified(listing.slug)
            notified_count += 1

        except Exception as unexpected:
            error_count += 1
            logger.exception(
                "Unexpected error processing %s: %s",
                getattr(listing, "slug", "<unknown>"), unexpected,
            )

    storage.close()
    click.echo(
        f"Found {found}, {new_count} new, {matched_count} matched, "
        f"{notified_count} notified, {error_count} errors"
    )


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
