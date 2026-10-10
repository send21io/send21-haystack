import json
import pytest
from haystack import Pipeline
from send21_haystack import MockSend21Client, Send21PaymentRequest, verify_send21_signature
from send21_haystack.webhook import sign


def comp(client=None):
    return Send21PaymentRequest(currency="USDC", network="base", address="0xabc", client=client or MockSend21Client())


def test_run_returns_pay_link_and_sends_verified_fields():
    c = MockSend21Client()
    out = comp(c).run(amount=1.5, fiat_currency="usd", order_id="o1", memo="m", idempotency_key="k1")
    assert out["id"] == "demo-0001" and out["pay_link"] == "https://send21.io/p/demo-0001"
    tool, args = c.calls[0]
    assert tool == "create_payment_request"
    assert set(args) == {"fiatCurrency", "fiatAmount", "options", "orderId", "memo", "expiryHours", "idempotencyKey"}
    assert args["fiatCurrency"] == "USD" and args["options"] == [{"currency": "USDC", "network": "base", "address": "0xabc"}]


def test_idempotency_key_reuses_request():
    c = MockSend21Client(); x = comp(c)
    a = x.run(amount=1, fiat_currency="USD", order_id="o", idempotency_key="same")
    b = x.run(amount=1, fiat_currency="USD", order_id="o", idempotency_key="same")
    assert a["id"] == b["id"]


def test_rejects_non_positive_amount():
    with pytest.raises(ValueError):
        comp().run(amount=0, fiat_currency="USD", order_id="o")


def test_bad_response_raises():
    class Bad:
        def call(self, t, a): return {"oops": 1}
    with pytest.raises(RuntimeError):
        comp(Bad()).run(amount=1, fiat_currency="USD", order_id="o")


def test_in_pipeline():
    p = Pipeline(); p.add_component("pay", comp())
    out = p.run({"pay": {"amount": 2, "fiat_currency": "EUR", "order_id": "o"}})
    assert out["pay"]["pay_link"].startswith("https://send21.io/p/")


def test_serialization_roundtrip(monkeypatch):
    monkeypatch.setenv("SEND21_API_KEY", "sk-secret-123")
    d = Send21PaymentRequest(currency="USDC", network="base", address="0xabc").to_dict()
    assert "sk-secret-123" not in json.dumps(d)
    assert Send21PaymentRequest.from_dict(d).address == "0xabc"


def test_signature_valid_and_invalid():
    raw = b'{"event":"draft.confirmed","data":{"orderId":"o"}}'
    good = sign(raw, "s")
    assert good.startswith("sha256=") and verify_send21_signature(raw, good, "s")
    assert not verify_send21_signature(raw + b" ", good, "s")
    assert not verify_send21_signature(raw, good, "other")
    assert not verify_send21_signature(raw, None, "s")
    assert not verify_send21_signature(raw, good, "")
