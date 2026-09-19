"""An endpoint of the integrator, end to end: a real `http.server` handler receives a delivery over HTTP and verifies
it with the bytes and the headers exactly as the standard library hands them over — no fixture in between."""

from __future__ import annotations

import hashlib
import hmac
import http.client
import json
import time
from collections.abc import Iterator
from typing import Any

import pytest

from bitgen import BitgenClient, BitgenError
from bitgen.models import WebhookEvent, WebhookEventName
from tests.server import QuietHandler, Server

SECRET = "whsec_0123456789abcdef"
RECEIVED: list[WebhookEvent | str] = []


class Endpoint(QuietHandler):
    """What an integrator writes: read the raw body, verify with the headers as received, answer 2xx or 4xx"""

    client = BitgenClient(scope="org-uuid", apiKey="k", host="127.0.0.1", port=1, isSsl=False)

    def do_POST(self) -> None:
        raw_body = self.rfile.read(int(self.headers.get("Content-Length") or 0))
        try:
            event = self.client.webhooks.verify(raw_body, self.headers, SECRET)
        except BitgenError as error:
            RECEIVED.append(error.code)
            self.send_response(400)
        else:
            RECEIVED.append(event)
            self.send_response(204)
        self.send_header("Content-Length", "0")
        self.end_headers()


@pytest.fixture(scope="module")
def endpoint() -> Iterator[Server]:
    server = Server(Endpoint).start()
    yield server
    server.close()


def deliver(server: Server, body: bytes, headers: dict[str, str]) -> int:
    connection = http.client.HTTPConnection("127.0.0.1", server.port, timeout=5)
    try:
        connection.request("POST", "/bitgen", body, {"Content-Type": "application/json", **headers})
        response = connection.getresponse()
        response.read()
        return response.status
    finally:
        connection.close()


def signed(body: bytes, secret: str = SECRET) -> dict[str, str]:
    timestamp = str(int(time.time()))
    digest = hmac.new(secret.encode(), timestamp.encode() + b"." + body, hashlib.sha256).hexdigest()
    return {"X-BITGEN-Timestamp": timestamp, "X-BITGEN-Signature": "sha256=" + digest}


def test_a_delivery_is_verified_from_the_bytes_and_headers_the_server_hands_over(endpoint: Server) -> None:
    RECEIVED.clear()
    payload: dict[str, Any] = {
        "delivery_id": "delivery-1",
        "timestamp": 1701000000,
        "event": "custody.sent",
        "data": {"wallet": "wallet-eth", "amount": "0.5", "label": "envoyé — 0,5 ETH"},
    }
    body = json.dumps(payload, ensure_ascii=False, indent=2).encode(
        "utf-8"
    )  # any serialization: the bytes are signed as sent
    assert deliver(endpoint, body, signed(body)) == 204
    event = RECEIVED[-1]
    assert isinstance(event, WebhookEvent)
    assert (event.delivery_id, event.event, event.timestamp) == (
        "delivery-1",
        WebhookEventName.CUSTODY_SENT,
        1701000000,
    )
    assert event.data == payload["data"]


def test_a_tampered_or_unsigned_delivery_is_refused_by_the_endpoint(endpoint: Server) -> None:
    RECEIVED.clear()
    body = b'{"delivery_id":"delivery-2","timestamp":1701000000,"event":"trading.buy","data":{}}'
    headers = signed(body)
    assert deliver(endpoint, body.replace(b"delivery-2", b"delivery-9"), headers) == 400
    assert deliver(endpoint, body, signed(body, "another-secret")) == 400
    assert deliver(endpoint, body, {}) == 400
    assert deliver(endpoint, body, {"X-BITGEN-Signature": headers["X-BITGEN-Signature"]}) == 400
    assert RECEIVED == ["invalid_signature", "invalid_signature", "missing_signature", "missing_timestamp"]
    assert deliver(endpoint, body, headers) == 204  # the untouched delivery still verifies
