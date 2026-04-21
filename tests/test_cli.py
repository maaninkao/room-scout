"""Test cli.run_once retry/error-handling semantics."""

from datetime import date
from unittest.mock import patch

from click.testing import CliRunner

from room_scout.cli import main
from room_scout.models import Listing


def _fake_listing(slug: str, price: float = 500.0) -> Listing:
    return Listing(
        slug=slug,
        url=f"https://coliving.joivy.com/en/rent-single-room-trento-{slug}/",
        title=f"Room {slug}",
        size_sqm=18.0,
        price_eur=price,
        available_from=date(2026, 9, 1),
        recently_booked=False,
    )


def _write_config(tmp_path, db_path):
    cfg = tmp_path / "config.yaml"
    cfg.write_text(
        f"city: trento\n"
        f"storage:\n"
        f"  db_path: {db_path}\n"
        f"filters:\n"
        f"  max_price_eur: 600\n"
        f"  include_recently_booked: false\n",
        encoding="utf-8",
    )
    return cfg


def test_push_failure_does_not_mark_notified(tmp_path, monkeypatch):
    """If send_notification raises, the listing must NOT be marked notified."""
    db_path = tmp_path / "seen.db"
    monkeypatch.setenv("NTFY_TOPIC", "test-topic")
    cfg = _write_config(tmp_path, db_path)
    monkeypatch.setenv("ROOM_SCOUT_CONFIG", str(cfg))

    listing = _fake_listing("tn-9001-01-a", price=500.0)

    with patch("room_scout.cli.fetch_live", return_value=[listing]), \
         patch(
             "room_scout.cli.send_notification",
             side_effect=RuntimeError("ntfy down"),
         ):
        result = CliRunner().invoke(main, ["run-once"])

    assert result.exit_code == 0
    assert "1 matched" in result.output
    assert "0 notified" in result.output
    assert "1 errors" in result.output

    from room_scout.storage import Storage
    s = Storage(str(db_path))
    assert s.was_notified("tn-9001-01-a") is False
    s.close()


def test_one_failure_does_not_break_other_listings(tmp_path, monkeypatch):
    """One listing failing must not prevent the others being processed."""
    db_path = tmp_path / "seen.db"
    monkeypatch.setenv("NTFY_TOPIC", "test-topic")
    cfg = _write_config(tmp_path, db_path)
    monkeypatch.setenv("ROOM_SCOUT_CONFIG", str(cfg))

    listings = [
        _fake_listing("tn-1001-01-a", price=500.0),
        _fake_listing("tn-1002-01-a", price=550.0),
        _fake_listing("tn-1003-01-a", price=580.0),
    ]
    call_log = []

    def _flaky_send(_cfg, listing):
        call_log.append(listing.slug)
        if listing.slug == "tn-1002-01-a":
            raise RuntimeError("simulated ntfy error for 1002")

    with patch("room_scout.cli.fetch_live", return_value=listings), \
         patch("room_scout.cli.send_notification", side_effect=_flaky_send):
        result = CliRunner().invoke(main, ["run-once"])

    assert result.exit_code == 0
    assert len(call_log) == 3
    assert "2 notified" in result.output
    assert "1 errors" in result.output

    from room_scout.storage import Storage
    s = Storage(str(db_path))
    assert s.was_notified("tn-1001-01-a") is True
    assert s.was_notified("tn-1002-01-a") is False
    assert s.was_notified("tn-1003-01-a") is True
    s.close()


def test_successful_push_marks_both_seen_and_notified(tmp_path, monkeypatch):
    """Happy path: successful push commits both flags."""
    db_path = tmp_path / "seen.db"
    monkeypatch.setenv("NTFY_TOPIC", "test-topic")
    cfg = _write_config(tmp_path, db_path)
    monkeypatch.setenv("ROOM_SCOUT_CONFIG", str(cfg))

    listing = _fake_listing("tn-2001-01-a", price=500.0)

    with patch("room_scout.cli.fetch_live", return_value=[listing]), \
         patch("room_scout.cli.send_notification") as mock_send:
        result = CliRunner().invoke(main, ["run-once"])

    assert result.exit_code == 0
    assert mock_send.call_count == 1
    assert "1 notified" in result.output

    from room_scout.storage import Storage
    s = Storage(str(db_path))
    assert s.was_notified("tn-2001-01-a") is True
    s.close()
