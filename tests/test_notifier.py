"""Tests for the ntfy push notifier."""

from datetime import date
from unittest.mock import MagicMock, patch

import pytest

from room_scout.models import AppConfig, FilterConfig, Listing
from room_scout.notifier import _encode_header, send_notification


@pytest.fixture
def config():
    return AppConfig(
        city="trento",
        ntfy_server="https://ntfy.sh",
        ntfy_topic="test-topic-abc123",
        db_path=":memory:",
        filters=FilterConfig(),
    )


@pytest.fixture
def listing():
    return Listing(
        slug="tn-2024-01-a",
        url="https://coliving.joivy.com/en/rent-single-room-trento-foo/tn-2024-01-a",
        title="Cozy Room — Via Roma 5, Trento",
        address="Via Roma 5, Trento",
        size_sqm=18.0,
        price_eur=550.0,
        available_from=date(2026, 5, 1),
        image_url="https://example.com/img.jpg",
    )


def test_send_notification_headers_and_body(config, listing):
    mock_resp = MagicMock()
    mock_resp.raise_for_status = MagicMock()

    with patch("room_scout.notifier.httpx.post", return_value=mock_resp) as mock_post:
        send_notification(config, listing)

    mock_post.assert_called_once()
    call_kwargs = mock_post.call_args

    url = call_kwargs.args[0]
    assert url == "https://ntfy.sh/test-topic-abc123"

    headers = call_kwargs.kwargs["headers"]
    assert headers["Title"] == _encode_header(listing.title)
    assert headers["Click"] == _encode_header(listing.url)
    assert headers["Priority"] == "high"
    assert headers["Tags"] == "house"
    assert headers["Attach"] == _encode_header(listing.image_url)

    body = call_kwargs.kwargs["content"].decode()
    assert "EUR 550" in body
    assert "/kk" in body
    assert "18 m2" in body
    assert "01 May 2026" in body
    assert listing.address in body


def test_send_notification_recently_booked(config):
    booked = Listing(
        slug="tn-2024-02-b",
        url="https://coliving.joivy.com/en/rent-single-room-trento-bar/tn-2024-02-b",
        title="Booked Room",
        price_eur=600.0,
        size_sqm=22.0,
        recently_booked=True,
    )
    mock_resp = MagicMock()
    mock_resp.raise_for_status = MagicMock()

    with patch("room_scout.notifier.httpx.post", return_value=mock_resp) as mock_post:
        send_notification(config, booked)

    body = mock_post.call_args.kwargs["content"].decode()
    assert "booked" in body
    assert "EUR 600" in body


def test_send_notification_no_attach_when_no_image(config):
    listing = Listing(
        slug="tn-2024-03-c",
        url="https://coliving.joivy.com/en/rent-single-room-trento-baz/tn-2024-03-c",
        price_eur=480.0,
        size_sqm=15.0,
        available_from=date(2026, 6, 1),
    )
    mock_resp = MagicMock()
    mock_resp.raise_for_status = MagicMock()

    with patch("room_scout.notifier.httpx.post", return_value=mock_resp) as mock_post:
        send_notification(config, listing)

    headers = mock_post.call_args.kwargs["headers"]
    assert "Attach" not in headers


def test_send_notification_raises_on_non_2xx(config, listing):
    mock_resp = MagicMock()
    mock_resp.raise_for_status.side_effect = Exception("HTTP 403")

    with patch("room_scout.notifier.httpx.post", return_value=mock_resp):
        with pytest.raises(Exception, match="HTTP 403"):
            send_notification(config, listing)
