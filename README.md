# send21-haystack

A Haystack 2.x component that asks send21 to prepare a payment request and returns a pay link, plus a webhook signature helper.

This is a community package. It is **not an official deepset integration**.

send21 prepares payment instructions. A person opens the pay link and signs in their own wallet; funds go straight from the payer's wallet to the receiver's wallet. send21 never holds keys or funds, never signs and never broadcasts. Use an API key with the `drafts:write` scope only. That key can prepare a payment request but cannot move funds.

## Install

Not on PyPI yet. Install from git:

```sh
pip install git+https://github.com/send21io/send21-haystack
```

## Usage in a pipeline

```python
from haystack import Pipeline
from send21_haystack import Send21PaymentRequest

# reads SEND21_API_KEY from the environment (scope: drafts:write)
payment = Send21PaymentRequest(currency="USDC", network="base", address="0xYourReceivingAddress")

p = Pipeline()
p.add_component("payment", payment)
out = p.run({"payment": {"amount": 1.50, "fiat_currency": "USD",
                         "order_id": "run-42", "memo": "agent top-up"}})
print(out["payment"]["pay_link"])   # https://send21.io/p/...
```

Outputs: `id`, `pay_link`, `raw` (the full tool result).

Offline: pass `client=MockSend21Client()` to get deterministic fake ids with no network. See `examples/pipeline.py`.

## What it sends

The component calls the send21 MCP server at `https://send21.io/mcp` (Streamable HTTP, `Authorization: Bearer <key>`), tool `create_payment_request`, with these fields only:

`fiatCurrency`, `fiatAmount`, `options: [{currency, network, address}]`, `orderId`, `memo`, `expiryHours` (null if unset), `idempotencyKey`.

It reads `id` and `payPath` from the result; the pay link is `https://send21.io` + `payPath`. Arguments are checked against the server's live `inputSchema` before the call.

## Webhooks

```python
from send21_haystack import verify_send21_webhook

ok, scheme = verify_send21_webhook(raw_body_bytes, headers, signing_secret)  # scheme: "v2", "v1" or None
```

It checks `X-Send21-Signature-V2` first: `t=<timestamp>,v1=<lowercase hex HMAC-SHA256 of "<timestamp>.<delivery id>.<raw body>">`, keyed with the endpoint signing secret, and refuses deliveries older than 5 minutes, so a copied delivery cannot be replayed. The legacy `X-Send21-Signature` (`sha256=<lowercase hex HMAC-SHA256 of the raw body>`, no timestamp) is still sent for compatibility and is used only as a fallback when no V2 header is present (`allow_legacy=False` turns it off). `verify_send21_signature_v2` and the legacy `verify_send21_signature` are also exported. Check the raw bytes before parsing. Store `X-Send21-Delivery` and ignore repeats; deliveries can be retried and arrive out of order. A stdlib receiver is in `examples/webhook_receiver.py`.

## Tests

```sh
pip install -e ".[dev]" && pytest
```

Tests run fully offline (the MCP client is mocked).

## Unverified

Not confirmed against the live API yet; check https://send21.io/docs and the live MCP `tools/list` first.

- The `status` and `expiresAt` values in the `create_payment_request` response, and the exact `payPath` format. Only `id` and `payPath` are relied on.
- Exact accepted `currency` and `network` names for `options`; the examples use `USDC` / `base`.
- Whether API keys can target testnet. Assume mainnet; use small amounts.
- Webhook payload fields beyond `event` and `data.orderId` (for example `paymentRequestId`, `fiatAmount`).
- Whether a key's scopes can be read through the API. Create the key with `drafts:write` only.

## Related

- Agent spend-cap handoff example: https://github.com/send21io/send21-over-budget-handoff
- More examples: https://github.com/send21io/send21-examples
- Docs: https://send21.io/docs

## License and contact

MIT. Questions: info@send21.io
