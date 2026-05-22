#!/usr/bin/env python3
"""
stripe_webhook.py

Minimal standard-library Stripe webhook receiver.

Purpose:
- Verify Stripe-Signature using STRIPE_WEBHOOK_SECRET.
- Log verified events to JSONL.
- Provide a safe fulfillment handoff point.

This does not grant access by default. Extend handle_verified_event() after your product/access model is defined.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any


HOST = os.getenv("STRIPE_WEBHOOK_HOST", "0.0.0.0")
PORT = int(os.getenv("STRIPE_WEBHOOK_PORT", "8080"))
WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET", "").strip()
WEBHOOK_LOG = Path(os.getenv("STRIPE_WEBHOOK_LOG", "stripe_webhook_events.jsonl"))
MAX_BODY_BYTES = int(os.getenv("STRIPE_WEBHOOK_MAX_BODY_BYTES", "1048576"))
SIGNATURE_TOLERANCE_SECONDS = int(os.getenv("STRIPE_SIGNATURE_TOLERANCE_SECONDS", "300"))


def now_ts() -> int:
    return int(time.time())


def append_jsonl(path: Path, obj: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(obj, sort_keys=True, separators=(",", ":")) + "\n")


def parse_stripe_signature(header: str) -> tuple[int | None, list[str]]:
    timestamp = None
    signatures: list[str] = []
    for part in header.split(","):
        if "=" not in part:
            continue
        key, value = part.split("=", 1)
        key = key.strip()
        value = value.strip()
        if key == "t":
            try:
                timestamp = int(value)
            except ValueError:
                timestamp = None
        elif key == "v1":
            signatures.append(value)
    return timestamp, signatures


def verify_stripe_signature(payload: bytes, signature_header: str, secret: str) -> bool:
    if not secret or not signature_header:
        return False

    timestamp, signatures = parse_stripe_signature(signature_header)
    if timestamp is None or not signatures:
        return False

    if abs(now_ts() - timestamp) > SIGNATURE_TOLERANCE_SECONDS:
        return False

    signed_payload = f"{timestamp}.".encode("utf-8") + payload
    expected = hmac.new(secret.encode("utf-8"), signed_payload, hashlib.sha256).hexdigest()
    return any(hmac.compare_digest(expected, sig) for sig in signatures)


def handle_verified_event(event: dict[str, Any]) -> None:
    event_type = str(event.get("type", ""))
    event_id = str(event.get("id", ""))
    obj = event.get("data", {}).get("object", {}) if isinstance(event.get("data"), dict) else {}

    append_jsonl(WEBHOOK_LOG, {
        "ts": now_ts(),
        "event_id": event_id,
        "event_type": event_type,
        "object_id": obj.get("id") if isinstance(obj, dict) else None,
        "client_reference_id": obj.get("client_reference_id") if isinstance(obj, dict) else None,
        "customer": obj.get("customer") if isinstance(obj, dict) else None,
        "customer_email": obj.get("customer_email") if isinstance(obj, dict) else None,
        "payment_status": obj.get("payment_status") if isinstance(obj, dict) else None,
        "subscription": obj.get("subscription") if isinstance(obj, dict) else None,
        "mode": obj.get("mode") if isinstance(obj, dict) else None,
        "metadata": obj.get("metadata") if isinstance(obj, dict) else None,
    })


class StripeWebhookHandler(BaseHTTPRequestHandler):
    server_version = "MembraStripeWebhook/1.0"

    def _json(self, status: int, payload: dict[str, Any]) -> None:
        body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        if self.path == "/healthz":
            self._json(200, {"ok": True, "service": "stripe_webhook"})
        else:
            self._json(404, {"ok": False, "error": "not_found"})

    def do_POST(self) -> None:
        if self.path != "/webhook":
            self._json(404, {"ok": False, "error": "not_found"})
            return

        content_length = int(self.headers.get("Content-Length", "0") or "0")
        if content_length <= 0 or content_length > MAX_BODY_BYTES:
            self._json(413, {"ok": False, "error": "invalid_body_size"})
            return

        payload = self.rfile.read(content_length)
        signature_header = self.headers.get("Stripe-Signature", "")

        if not verify_stripe_signature(payload, signature_header, WEBHOOK_SECRET):
            self._json(400, {"ok": False, "error": "invalid_signature"})
            return

        try:
            event = json.loads(payload.decode("utf-8"))
        except json.JSONDecodeError:
            self._json(400, {"ok": False, "error": "invalid_json"})
            return

        handle_verified_event(event)
        self._json(200, {"ok": True, "received": True, "event_id": event.get("id"), "type": event.get("type")})

    def log_message(self, fmt: str, *args: Any) -> None:
        print(f"{self.address_string()} - {fmt % args}")


def main() -> int:
    if not WEBHOOK_SECRET:
        raise SystemExit("STRIPE_WEBHOOK_SECRET is required")

    server = ThreadingHTTPServer((HOST, PORT), StripeWebhookHandler)
    print(f"Stripe webhook verifier listening on http://{HOST}:{PORT}/webhook")
    server.serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
