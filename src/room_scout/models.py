"""Pydantic data models for listings and configuration."""

from datetime import date
from typing import Optional
from pydantic import BaseModel


class Listing(BaseModel):
    slug: str
    url: str
    title: Optional[str] = None
    address: Optional[str] = None
    size_sqm: Optional[float] = None
    flatmates: Optional[int] = None
    price_eur: Optional[float] = None
    available_from: Optional[date] = None
    recently_booked: bool = False
    image_url: Optional[str] = None


class FilterConfig(BaseModel):
    max_price: Optional[float] = None
    min_price: Optional[float] = None
    min_sqm: Optional[float] = None
    max_sqm: Optional[float] = None
    earliest_available: Optional[date] = None
    latest_available: Optional[date] = None
    address_must_contain: list[str] = []
    address_must_not_contain: list[str] = []
    include_recently_booked: bool = False


class AppConfig(BaseModel):
    city: str = "trento"
    ntfy_server: str = "https://ntfy.sh"
    ntfy_topic: str
    db_path: str = "data/seen.db"
    filters: FilterConfig = FilterConfig()
