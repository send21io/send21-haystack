"""Webhook signature check.

Header X-Send21-Signature: sha256=<lowercase hex HMAC-SHA256 of the raw body>, keyed with the
endpoint signing secret. Check the raw bytes before parsing. X-Send21-Delivery is reused on
retries, so store it and ignore repeats. No timestamp header is documented.
"""
from __future__ import annotations

import hashlib
import hmac
from typing import Optional

SIGNATURE_HEADER = "X-Send21-Signature"
DELIVERY_HEADER = "X-Send21-Delivery"
EVENT_HEADER = "X-Send21-Event"


def sign(raw: bytes, secret: str) -> str:
    return "sha256=" + hmac.new(secret.encode(), raw, hashlib.sha256).hexdigest()


def verify_send21_signature(raw_body: bytes, signature_header: Optional[str], secret: str) -> bool:
    """True only if the header matches the HMAC of the raw body. Constant-time compare."""
    if not secret or not isinstance(signature_header, str) or not isinstance(raw_body, (bytes, bytearray)):
        return False
    return hmac.compare_digest(sign(bytes(raw_body), secret).encode(), signature_header.encode())
