"""Webhook signature check.

Verify X-Send21-Signature-V2 first:

    X-Send21-Signature-V2: t=<timestamp>,v1=<lowercase hex HMAC-SHA256 of "<timestamp>.<delivery id>.<raw body>">

keyed with the endpoint signing secret. <timestamp> is Unix seconds (also sent as X-Send21-Timestamp)
and <delivery id> is X-Send21-Delivery. Because the time and delivery id are signed, deliveries older
than 5 minutes are refused and a copied delivery cannot be replayed.

The legacy X-Send21-Signature: sha256=<lowercase hex HMAC-SHA256 of the raw body only> (no timestamp)
is still sent for compatibility. verify_send21_webhook uses it only when no V2 header is present.

Check the raw bytes before parsing. X-Send21-Delivery is reused on retries, so store it and ignore repeats.
"""
from __future__ import annotations

import hashlib
import hmac
import time
from typing import Mapping, Optional, Tuple

SIGNATURE_V2_HEADER = "X-Send21-Signature-V2"
SIGNATURE_HEADER = "X-Send21-Signature"
TIMESTAMP_HEADER = "X-Send21-Timestamp"
DELIVERY_HEADER = "X-Send21-Delivery"
EVENT_HEADER = "X-Send21-Event"
TOLERANCE_SECONDS = 5 * 60


def sign_v2(raw: bytes, delivery_id: str, timestamp, secret: str) -> str:
    """X-Send21-Signature-V2 value for a body, delivery id and Unix timestamp."""
    mac = hmac.new(secret.encode(), f"{timestamp}.{delivery_id}.".encode() + bytes(raw), hashlib.sha256).hexdigest()
    return f"t={timestamp},v1={mac}"


def verify_send21_signature_v2(raw_body: bytes, signature_header: Optional[str], delivery_id: Optional[str],
                               secret: str, now: Optional[float] = None,
                               tolerance: int = TOLERANCE_SECONDS) -> bool:
    """True only for a valid V2 signature no more than 5 minutes old. Constant-time compare, never raises."""
    if (not secret or not isinstance(signature_header, str) or not isinstance(delivery_id, str) or not delivery_id
            or not isinstance(raw_body, (bytes, bytearray))):
        return False
    parts = {}
    for part in signature_header.split(","):
        k, sep, v = part.partition("=")
        if sep:
            parts[k.strip()] = v.strip()
    t, v1 = parts.get("t", ""), parts.get("v1", "")
    if not t.isdigit() or not v1:
        return False
    if abs((time.time() if now is None else now) - int(t)) > tolerance:
        return False
    expected = sign_v2(bytes(raw_body), delivery_id, t, secret).split(",v1=", 1)[1]
    return hmac.compare_digest(expected.encode(), v1.encode())


def sign(raw: bytes, secret: str) -> str:
    """Legacy X-Send21-Signature value (raw body only)."""
    return "sha256=" + hmac.new(secret.encode(), raw, hashlib.sha256).hexdigest()


def verify_send21_signature(raw_body: bytes, signature_header: Optional[str], secret: str) -> bool:
    """Legacy: True only if X-Send21-Signature matches the HMAC of the raw body. Prefer verify_send21_webhook."""
    if not secret or not isinstance(signature_header, str) or not isinstance(raw_body, (bytes, bytearray)):
        return False
    return hmac.compare_digest(sign(bytes(raw_body), secret).encode(), signature_header.encode())


def verify_send21_webhook(raw_body: bytes, headers: Mapping[str, str], secret: str, allow_legacy: bool = True,
                          now: Optional[float] = None) -> Tuple[bool, Optional[str]]:
    """Verify a delivery from its headers: V2 first, legacy only when no V2 header is sent.

    Returns (valid, scheme) where scheme is "v2", "v1" or None.
    """
    h = {str(k).lower(): v for k, v in dict(headers).items()}
    v2 = h.get(SIGNATURE_V2_HEADER.lower())
    if v2 is not None:
        return verify_send21_signature_v2(raw_body, v2, h.get(DELIVERY_HEADER.lower()), secret, now=now), "v2"
    legacy = h.get(SIGNATURE_HEADER.lower())
    if allow_legacy and legacy is not None:
        return verify_send21_signature(raw_body, legacy, secret), "v1"
    return False, None
