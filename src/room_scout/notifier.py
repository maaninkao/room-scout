"""ntfy.sh push notification sender."""
from base64 import b64encode

import httpx

from .models import AppConfig, Listing


def _encode_header(value: str) -> str:
    """Encode header value as RFC 2047 Base64 if non-ASCII, else return as-is."""
    try:
        value.encode("ascii")
        return value
    except UnicodeEncodeError:
        b64 = b64encode(value.encode("utf-8")).decode("ascii")
        return f"=?utf-8?B?{b64}?="


def send_notification(config: AppConfig, listing: Listing) -> None:
    """POST a push notification for a listing to the configured ntfy server."""
    url = f"{config.ntfy_server}/{config.ntfy_topic}"

    price = f"EUR {int(listing.price_eur)}" if listing.price_eur is not None else "?"
    size = f"{int(listing.size_sqm)} m2" if listing.size_sqm is not None else "? m2"

    if listing.recently_booked:
        avail = "booked"
    elif listing.available_from:
        avail = listing.available_from.strftime("%d %b %Y")
    else:
        avail = "unknown"

    body_lines = [f"{price}/kk | {size} | from {avail}"]
    if listing.address:
        body_lines.append(listing.address)
    body = "\n".join(body_lines)

    title = listing.title or listing.slug

    headers = {
        "Title": _encode_header(title),
        "Click": _encode_header(listing.url),
        "Priority": "high",
        "Tags": "house",
    }
    if listing.image_url:
        headers["Attach"] = _encode_header(listing.image_url)

    resp = httpx.post(url, content=body.encode("utf-8"), headers=headers, timeout=10.0)
    resp.raise_for_status()
