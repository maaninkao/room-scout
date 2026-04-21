"""Filter logic — matches(listing, config) -> (bool, reason)."""

from .models import Listing, FilterConfig


def matches(listing: Listing, f: FilterConfig) -> tuple[bool, str]:
    if not f.include_recently_booked and listing.recently_booked:
        return False, "recently_booked"

    if f.min_price is not None and listing.price_eur is not None:
        if listing.price_eur < f.min_price:
            return False, f"price {listing.price_eur} < min {f.min_price}"

    if f.max_price is not None and listing.price_eur is not None:
        if listing.price_eur > f.max_price:
            return False, f"price {listing.price_eur} > max {f.max_price}"

    if f.min_sqm is not None and listing.size_sqm is not None:
        if listing.size_sqm < f.min_sqm:
            return False, f"size {listing.size_sqm} < min {f.min_sqm}"

    if f.max_sqm is not None and listing.size_sqm is not None:
        if listing.size_sqm > f.max_sqm:
            return False, f"size {listing.size_sqm} > max {f.max_sqm}"

    if f.earliest_available is not None and listing.available_from is not None:
        if listing.available_from < f.earliest_available:
            return False, f"available_from {listing.available_from} before earliest {f.earliest_available}"

    if f.latest_available is not None and listing.available_from is not None:
        if listing.available_from > f.latest_available:
            return False, f"available_from {listing.available_from} after latest {f.latest_available}"

    if f.address_must_contain and listing.address is not None:
        addr_lower = listing.address.lower()
        if not any(s.lower() in addr_lower for s in f.address_must_contain):
            return False, f"address missing required substring"

    if f.address_must_not_contain and listing.address is not None:
        addr_lower = listing.address.lower()
        for s in f.address_must_not_contain:
            if s.lower() in addr_lower:
                return False, f"address contains excluded substring '{s}'"

    return True, "ok"
