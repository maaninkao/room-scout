"""Configuration loader — merges config.yaml and .env."""

import os
from pathlib import Path

import yaml
from dotenv import load_dotenv

from .models import AppConfig, FilterConfig


def load_config() -> AppConfig:
    """Load AppConfig from config.yaml and .env (NTFY_TOPIC required)."""
    load_dotenv()

    ntfy_topic = os.environ.get("NTFY_TOPIC")
    if not ntfy_topic:
        raise ValueError("NTFY_TOPIC is required — set it in .env or the environment")

    config_path = Path(os.environ.get("ROOM_SCOUT_CONFIG", "config.yaml"))
    raw: dict = {}
    if config_path.exists():
        with open(config_path, encoding="utf-8") as fh:
            raw = yaml.safe_load(fh) or {}

    filters_raw = raw.get("filters") or {}
    filter_config = FilterConfig(
        max_price=filters_raw.get("max_price_eur"),
        min_price=filters_raw.get("min_price_eur"),
        min_sqm=filters_raw.get("min_size_sqm"),
        max_sqm=filters_raw.get("max_size_sqm"),
        earliest_available=filters_raw.get("earliest_available"),
        latest_available=filters_raw.get("latest_available"),
        address_must_contain=filters_raw.get("address_must_contain") or [],
        address_must_not_contain=filters_raw.get("address_must_not_contain") or [],
        include_recently_booked=filters_raw.get("include_recently_booked", False),
    )

    ntfy_raw = raw.get("ntfy") or {}
    storage_raw = raw.get("storage") or {}

    return AppConfig(
        city=raw.get("city", "trento"),
        ntfy_server=ntfy_raw.get("server", "https://ntfy.sh"),
        ntfy_topic=ntfy_topic,
        db_path=storage_raw.get("db_path", "data/seen.db"),
        filters=filter_config,
    )
