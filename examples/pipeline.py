"""Pipeline example. Offline by default; set SEND21_LIVE=1 and SEND21_API_KEY for the real MCP."""
import os

from haystack import Pipeline

from send21_haystack import MockSend21Client, Send21PaymentRequest

client = None if os.environ.get("SEND21_LIVE") == "1" else MockSend21Client()
p = Pipeline()
p.add_component("payment", Send21PaymentRequest(currency="USDC", network="base",
                                                address=os.environ.get("PAYEE_ADDRESS", "0xYourAddress"),
                                                client=client))
out = p.run({"payment": {"amount": 1.5, "fiat_currency": "USD", "order_id": "run-42", "memo": "agent top-up"}})
print(out["payment"]["pay_link"])
