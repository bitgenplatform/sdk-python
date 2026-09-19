"""`WebhooksResource.verify()` — local verification of a received delivery, never a request."""

from __future__ import annotations

import hashlib
import hmac
import json
import math
import time
from collections.abc import Callable, Iterable
from email.message import Message
from typing import Any

import pytest

from bitgen import BitgenError
from bitgen._http.client import HttpClient
from bitgen.models import WebhookEvent, WebhookEventName
from bitgen.resources.webhooks import WebhooksResource
from tests.fake_transport import FakeTransport

SECRET = "whsec_0123456789abcdef"
# The bytes as delivered — spaces and key order matter for the signature
BODY = b'{"delivery_id":"d-1","timestamp":1700000000,"event":"custody.sent","data":{"wallet":"w-1","amount":"0.5"}}'


def sign(body: bytes, timestamp: str, secret: str = SECRET) -> str:
    return "sha256=" + hmac.new(secret.encode(), timestamp.encode() + b"." + body, hashlib.sha256).hexdigest()


def headers(body: bytes, issued_at: float | None = None, secret: str = SECRET) -> dict[str, str]:
    timestamp = str(int(time.time()) if issued_at is None else int(issued_at))
    return {"X-BITGEN-Timestamp": timestamp, "X-BITGEN-Signature": sign(body, timestamp, secret)}


@pytest.fixture
def transport() -> FakeTransport:
    return FakeTransport()


@pytest.fixture
def webhooks(transport: FakeTransport) -> WebhooksResource:
    return WebhooksResource(HttpClient(transport, "org-uuid", "k", "https://api.test", 1.0, "ua"))


def rejected(
    webhooks: WebhooksResource, body: bytes | str, given: Any, secret: str = SECRET, tolerance: int | float = 300
) -> str:
    """The code of the `BitgenError` the delivery is refused with — `status` 0, no cause, never the secret"""
    with pytest.raises(BitgenError) as caught:
        webhooks.verify(body, given, secret, tolerance)
    error = caught.value
    assert error.status == 0
    assert str(error) == f"{error.code} (HTTP 0)"
    assert SECRET not in str(error) and SECRET not in repr(error)
    assert error.__cause__ is None
    return error.code


def test_a_valid_delivery_is_returned_as_an_envelope(webhooks: WebhooksResource, transport: FakeTransport) -> None:
    event = webhooks.verify(BODY, headers(BODY), SECRET)
    assert isinstance(event, WebhookEvent)
    assert event.delivery_id == "d-1"
    assert event.timestamp == 1700000000
    assert event.event == WebhookEventName.CUSTODY_SENT
    assert event.data == {"wallet": "w-1", "amount": "0.5"}
    assert transport.requests == []  # never a request
    # the same bytes given as text verify the same way
    assert webhooks.verify(BODY.decode(), headers(BODY), SECRET) == event


class ItemsOnly:
    """A headers object that is not a mapping but yields `items()` — the shape of Flask's `request.headers`"""

    def __init__(self, pairs: list[tuple[str, str]]) -> None:
        self._pairs = pairs

    def items(self) -> Iterable[tuple[str, str]]:
        return list(self._pairs)


def test_header_names_are_matched_case_insensitively_in_every_shape(webhooks: WebhooksResource) -> None:
    timestamp = str(int(time.time()))
    signature = sign(BODY, timestamp)
    message = Message()  # the `headers` of an `http.server` handler
    message["Content-Type"] = "application/json"
    message["X-Bitgen-Timestamp"] = timestamp
    message["X-Bitgen-Signature"] = signature
    shapes: dict[str, Any] = {
        "a dict, any case": {
            "Content-Type": "application/json",
            "x-bitgen-timestamp": timestamp,
            "X-Bitgen-Signature": signature,
        },
        "a WSGI environ": {
            "REQUEST_METHOD": "POST",
            "HTTP_X_BITGEN_TIMESTAMP": timestamp,
            "HTTP_X_BITGEN_SIGNATURE": signature,
            "wsgi.input": None,
        },
        "multi-valued headers": {
            "X-BITGEN-Timestamp": [timestamp],
            "X-BITGEN-Signature": (signature, "sha256=second-value-ignored"),
        },
        "bytes values": {"x-bitgen-timestamp": timestamp.encode(), "x-bitgen-signature": signature.encode()},
        "signature in upper case with spaces": {
            "X-BITGEN-Timestamp": timestamp,
            "X-BITGEN-Signature": "  " + signature.upper() + " ",
        },
        "an items() object": ItemsOnly([("X-BITGEN-Timestamp", timestamp), ("X-BITGEN-Signature", signature)]),
        "http.server headers": message,
        "a numeric timestamp value": {"X-BITGEN-Timestamp": int(timestamp), "X-BITGEN-Signature": signature},
        "raw ASGI pairs": [
            (b"content-type", b"application/json"),
            (b"x-bitgen-timestamp", timestamp.encode()),
            (b"x-bitgen-signature", signature.encode()),
        ],
        "a tuple of pairs": (("X-BITGEN-Timestamp", timestamp), ("X-BITGEN-Signature", signature)),
    }
    for shape, given in shapes.items():
        assert webhooks.verify(BODY, given, SECRET).delivery_id == "d-1", shape


def test_a_reserialized_body_does_not_verify(webhooks: WebhooksResource) -> None:
    given = headers(BODY)
    reserialized = json.dumps(json.loads(BODY), indent=2)
    assert reserialized.encode() != BODY
    assert rejected(webhooks, reserialized, given) == "invalid_signature"


def test_a_tampered_body_a_wrong_secret_or_a_forged_signature_is_invalid(
    webhooks: WebhooksResource, transport: FakeTransport
) -> None:
    given = headers(BODY)
    assert rejected(webhooks, BODY.replace(b'"0.5"', b'"5.0"'), given) == "invalid_signature"
    assert rejected(webhooks, BODY, given, "another-secret") == "invalid_signature"
    forged = {**given, "X-BITGEN-Signature": "sha256=" + "0" * 64}  # the right length
    assert rejected(webhooks, BODY, forged) == "invalid_signature"
    short = {**given, "X-BITGEN-Signature": "sha256=abc"}  # the wrong length is invalid too, never an error
    assert rejected(webhooks, BODY, short) == "invalid_signature"
    unicode = {**given, "X-BITGEN-Signature": "sha256=" + "é" * 32}  # non-ASCII bytes compare, they do not crash
    assert rejected(webhooks, BODY, unicode) == "invalid_signature"
    assert transport.requests == []


def test_missing_headers(webhooks: WebhooksResource) -> None:
    given = headers(BODY)
    timestamp, signature = given["X-BITGEN-Timestamp"], given["X-BITGEN-Signature"]
    assert rejected(webhooks, BODY, {}) == "missing_signature"
    assert rejected(webhooks, BODY, {"X-BITGEN-Timestamp": timestamp}) == "missing_signature"
    assert rejected(webhooks, BODY, {"X-BITGEN-Signature": "", "X-BITGEN-Timestamp": timestamp}) == "missing_signature"
    assert (
        rejected(webhooks, BODY, {"X-BITGEN-Signature": None, "X-BITGEN-Timestamp": timestamp}) == "missing_signature"
    )
    assert rejected(webhooks, BODY, {"X-BITGEN-Signature": [], "X-BITGEN-Timestamp": timestamp}) == "missing_signature"
    assert rejected(webhooks, BODY, {"X-BITGEN-Signature": signature}) == "missing_timestamp"
    assert rejected(webhooks, BODY, {"X-BITGEN-Signature": signature, "X-BITGEN-Timestamp": ""}) == "missing_timestamp"
    assert (
        rejected(webhooks, BODY, {"X-BITGEN-Signature": signature, "X-BITGEN-Timestamp": [""]}) == "missing_timestamp"
    )
    assert (
        rejected(webhooks, BODY, {"X-BITGEN-Signature": signature, "X-BITGEN-Timestamp": {"nested": 1}})
        == "missing_timestamp"
    )
    # a timestamp that is not a number: the signature is checked with it first, then it is refused
    for text in ("yesterday", "nan", "inf", "-infinity"):
        signed = sign(BODY, text)
        assert (
            rejected(webhooks, BODY, {"X-BITGEN-Signature": signed, "X-BITGEN-Timestamp": text}) == "missing_timestamp"
        ), text


def test_freshness(webhooks: WebhooksResource) -> None:
    now = time.time()
    assert rejected(webhooks, BODY, headers(BODY, now - 301)) == "timestamp_expired"
    assert webhooks.verify(BODY, headers(BODY, now - 299), SECRET).delivery_id == "d-1"
    assert rejected(webhooks, BODY, headers(BODY, now + 302)) == "timestamp_expired"
    assert webhooks.verify(BODY, headers(BODY, now + 298), SECRET).delivery_id == "d-1"
    # a custom window, and 0 disables the check
    assert rejected(webhooks, BODY, headers(BODY, now - 62), SECRET, 60) == "timestamp_expired"
    assert webhooks.verify(BODY, headers(BODY, now - 58), SECRET, 60.5).delivery_id == "d-1"
    assert webhooks.verify(BODY, headers(BODY, 1700000000), SECRET, 0).delivery_id == "d-1"
    assert webhooks.verify(BODY, headers(BODY, 1700000000), SECRET, tolerance=0).delivery_id == "d-1"


def test_the_signature_is_checked_before_the_freshness(webhooks: WebhooksResource) -> None:
    given = headers(BODY, time.time() - 3600)
    given["X-BITGEN-Signature"] = sign(BODY, given["X-BITGEN-Timestamp"], "another-secret")
    assert rejected(webhooks, BODY, given) == "invalid_signature"


@pytest.mark.parametrize(
    "body",
    [
        b"delivery_id=d-1",
        b"[1,2]",
        b'"text"',
        b'{"timestamp":1700000000,"event":"custody.sent","data":{}}',
        b'{"delivery_id":"d-1","timestamp":"1700000000","event":"custody.sent","data":{}}',
        b'{"delivery_id":"d-1","timestamp":true,"event":"custody.sent","data":{}}',
        b'{"delivery_id":"d-1","timestamp":1700000000,"data":{}}',
        b'{"delivery_id":"d-1","timestamp":1700000000,"event":"custody.sent"}',
        b'{"delivery_id":"d-1","timestamp":NaN,"event":"custody.sent","data":{}}',
        b"\xff\xfe{}",
    ],
    ids=[
        "not json",
        "a list",
        "a string",
        "no delivery_id",
        "timestamp as a string",
        "timestamp as a boolean",
        "no event",
        "no data",
        "NaN is not JSON",
        "not UTF-8",
    ],
)
def test_a_valid_signature_on_a_non_envelope_is_an_invalid_payload(webhooks: WebhooksResource, body: bytes) -> None:
    assert rejected(webhooks, body, headers(body)) == "invalid_payload"


def test_data_may_be_null_or_a_scalar_and_the_timestamp_a_float(webhooks: WebhooksResource) -> None:
    body = b'{"delivery_id":"d-2","timestamp":1700000000.0,"event":"alert.status","data":null}'
    event = webhooks.verify(body, headers(body), SECRET)
    assert event.data is None
    assert event.timestamp == 1700000000
    assert event.event == WebhookEventName.ALERT_STATUS


def test_unusable_arguments_are_refused(webhooks: WebhooksResource, transport: FakeTransport) -> None:
    given = headers(BODY)
    value_errors: dict[str, Callable[[], object]] = {
        "rawBody must be the received body, not empty": lambda: webhooks.verify(b"", given, SECRET),
        "secret must be a non-empty string": lambda: webhooks.verify(BODY, given, ""),
        "tolerance must be a number of seconds >= 0": lambda: webhooks.verify(BODY, given, SECRET, -1),
    }
    for message, call in value_errors.items():
        with pytest.raises(ValueError, match=f"^{message}$"):
            call()
    for tolerance in (math.nan, math.inf, -math.inf):
        with pytest.raises(ValueError):
            webhooks.verify(BODY, given, SECRET, tolerance)
    type_errors: dict[str, Callable[[], object]] = {
        "rawBody must be the received body: bytes or str": lambda: webhooks.verify(json.loads(BODY), given, SECRET),
        "headers must be a mapping of the received headers, or a list of \\(name, value\\) pairs": lambda: (
            webhooks.verify(
                BODY,
                "X-BITGEN-Signature: x",  # type: ignore[arg-type]
                SECRET,
            )
        ),
        "secret must be a non-empty string": lambda: webhooks.verify(BODY, given, SECRET.encode()),  # type: ignore[arg-type]
        "tolerance must be a number of seconds >= 0": lambda: webhooks.verify(BODY, given, SECRET, "300"),  # type: ignore[arg-type]
    }
    for message, call in type_errors.items():
        with pytest.raises(TypeError, match=f"^{message}$"):
            call()
    with pytest.raises(TypeError):
        webhooks.verify(BODY, given, SECRET, True)  # a bool is an int for the type checker, not for the SDK
    with pytest.raises(TypeError):
        webhooks.verify(BODY, None, SECRET)  # type: ignore[arg-type]
    with pytest.raises(TypeError):
        webhooks.verify(BODY, [("X-BITGEN-Signature", "x", "extra")], SECRET)  # type: ignore[list-item]
    with pytest.raises(TypeError, match=r"^headers must be a mapping"):
        webhooks.verify(BODY, ItemsOnly(["X-BITGEN-Signature: x"]), SECRET)  # type: ignore[list-item]
    with pytest.raises(
        ValueError, match=r"^rawBody must be the received body: bytes, or a text that encodes to UTF-8$"
    ):
        webhooks.verify("\ud800", given, SECRET)  # a lone surrogate is not a text that came from bytes
    # a text decoded with surrogateescape gives back the exact bytes: the signature over the raw bytes matches, and
    # only then is the body — not UTF-8 — refused as a payload
    raw = BODY.replace(b'"w-1"', b'"w-\xff1"')
    assert rejected(webhooks, raw.decode("utf-8", "surrogateescape"), headers(raw)) == "invalid_payload"
    assert rejected(webhooks, raw.decode("utf-8", "replace"), headers(raw)) == "invalid_signature"
    assert transport.requests == []
