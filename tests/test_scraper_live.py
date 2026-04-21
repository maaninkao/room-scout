"""Test fetch_live uses correct URL and User-Agent without real network."""
from unittest.mock import patch, MagicMock
from pathlib import Path

from room_scout.models import AppConfig
from room_scout.scraper import fetch_live


def test_fetch_live_calls_correct_url_with_ua():
    config = AppConfig(ntfy_topic="test-topic", city="trento")
    fixture_html = (
        Path(__file__).parent / "fixtures" / "trento_sample.html"
    ).read_text(encoding="utf-8")

    mock_response = MagicMock()
    mock_response.text = fixture_html
    mock_response.raise_for_status = MagicMock()

    with patch("room_scout.scraper.httpx.get", return_value=mock_response) as mock_get:
        listings = fetch_live(config)

    assert mock_get.call_count == 1
    call_args = mock_get.call_args
    assert call_args[0][0] == "https://coliving.joivy.com/en/rent-room-trento/"
    headers = call_args[1]["headers"]
    assert "User-Agent" in headers
    assert "Mozilla" in headers["User-Agent"]
    assert len(listings) >= 5
