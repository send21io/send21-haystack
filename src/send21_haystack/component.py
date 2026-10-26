"""Haystack component: ask send21 to prepare a payment request and return the pay link.

send21 prepares payment instructions. It never holds keys or funds, never signs and never
broadcasts. Use an API key with the drafts:write scope only; such a key cannot move funds.
"""
from __future__ import annotations

import os
import uuid
from decimal import Decimal
from typing import Any, Optional

from haystack import component, default_from_dict, default_to_dict
from haystack.utils import Secret, deserialize_secrets_inplace

from .client import Send21MCPClient, build_create_args, pay_link

MCP_URL = "https://send21.io/mcp"


@component
class Send21PaymentRequest:
    """Creates a send21 payment request and returns its id and pay link.

    Usage:
        pr = Send21PaymentRequest(currency="USDC", network="base", address="0x...")
        pr.run(amount=1.5, fiat_currency="USD", order_id="run-42", memo="agent top-up")
        # {"id": "...", "pay_link": "https://send21.io/pay/...", "raw": {...}}
    """

    def __init__(self, currency: str, network: str, address: str,
                 api_key: Secret = Secret.from_env_var("SEND21_API_KEY"),
                 mcp_url: str = MCP_URL, expiry_hours: Optional[int] = None,
                 client: Any = None) -> None:
        self.currency, self.network, self.address = currency, network, address
        self.api_key, self.mcp_url, self.expiry_hours = api_key, mcp_url, expiry_hours
        self._client = client

    def _get_client(self):
        if self._client is None:
            self._client = Send21MCPClient(self.mcp_url, self.api_key.resolve_value() or "")
        return self._client

    @component.output_types(id=str, pay_link=str, raw=dict)
    def run(self, amount: float, fiat_currency: str, order_id: str, memo: str = "",
            idempotency_key: Optional[str] = None) -> dict:
        if Decimal(str(amount)) <= 0:
            raise ValueError("amount must be positive")
        args = build_create_args(amount=Decimal(str(amount)), fiat_currency=fiat_currency,
                                 currency=self.currency, network=self.network, address=self.address,
                                 order_id=order_id, memo=memo,
                                 idempotency_key=idempotency_key or f"{order_id}-{uuid.uuid4()}",
                                 expiry_hours=self.expiry_hours)
        res = self._get_client().call("create_payment_request", args)
        if "id" not in res or "payPath" not in res:
            raise RuntimeError(f"unexpected send21 response: {res}")
        return {"id": str(res["id"]), "pay_link": pay_link(res["payPath"]), "raw": res}

    def to_dict(self) -> dict:
        return default_to_dict(self, currency=self.currency, network=self.network, address=self.address,
                               api_key=self.api_key.to_dict(), mcp_url=self.mcp_url,
                               expiry_hours=self.expiry_hours)

    @classmethod
    def from_dict(cls, data: dict) -> "Send21PaymentRequest":
        deserialize_secrets_inplace(data["init_parameters"], keys=["api_key"])
        return default_from_dict(cls, data)
