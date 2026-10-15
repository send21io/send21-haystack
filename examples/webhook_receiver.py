"""Tiny send21 webhook receiver (stdlib only). Run: SEND21_WEBHOOK_SECRET=... python examples/webhook_receiver.py"""
import json
import os
from http.server import BaseHTTPRequestHandler, HTTPServer

from send21_haystack import verify_send21_webhook

SECRET = os.environ.get("SEND21_WEBHOOK_SECRET", "")
seen: set[str] = set()


class Handler(BaseHTTPRequestHandler):
    def do_POST(self):
        raw = self.rfile.read(min(int(self.headers.get("Content-Length", 0)), 1024 * 1024))
        # X-Send21-Signature-V2 first (timestamp + delivery id, 5-minute window);
        # the legacy body-only X-Send21-Signature only when no V2 header is sent.
        valid, _scheme = verify_send21_webhook(raw, dict(self.headers.items()), SECRET)
        if not valid:
            self.send_response(401); self.end_headers(); return
        delivery = self.headers.get("X-Send21-Delivery")
        if delivery and delivery in seen:
            self.send_response(200); self.end_headers(); return
        if delivery:
            seen.add(delivery)
        payload = json.loads(raw)
        if payload.get("event") == "draft.confirmed":
            print("confirmed orderId", (payload.get("data") or {}).get("orderId"))
        self.send_response(200); self.end_headers()


if __name__ == "__main__":
    HTTPServer(("127.0.0.1", int(os.environ.get("PORT", 8787))), Handler).serve_forever()
