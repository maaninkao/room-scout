"""ntfy.sh push notification sender."""

import httpx

from .models import AppConfig, Listing


def send_notification(config: AppConfig, listing: Listing) -> None:
    """POST a push notification for a listing to the configured ntfy server."""
    url = f"{config.ntfy_server}/{config.ntfy_topic}"

    price = f"€{int(listing.price_eur)}" if listing.price_eur is not None else "?"
    size = f"{int(listing.size_sqm)}" if listing.size_sqm is not None else "?"

    if listing.recently_booked:
        avail = "booked"
    elif listing.available_from:
        avail = listing.available_from.strftime("%d %b %Y")
    else:
        avail = "unknown"

    body = f"{price}/mo · {size} m² · from {avail}"
    if listing.address:
        body += f"\n{listing.address}"

    headers = {
        "Title": listing.title or listing.slug,
        "Click": listing.url,
        "Priority": "high",
        "Tags": "house",
    }
    if listing.image_url:
        headers["Attach"] = listing.image_url

    resp = httpx.post(url, content=body.encode(), headers=headers, timeout=10.0)
    resp.raise_for_status()
