"""The webhooks of the organization: endpoint and secret, subscriptions, delivery logs, catalogue — and `verify`, the
local check of a delivery received by the endpoint (`client.webhooks`)."""

from __future__ import annotations

import hashlib
import hmac
import math
import time
from typing import Final

from bitgen._http.client import HttpClient, _decode
from bitgen._support import path, reference, values
from bitgen.errors import BitgenError
from bitgen.models import _cast
from bitgen.models.customer import Created
from bitgen.models.webhooks import (
    DeliveryLog,
    ReceivedHeaders,
    Subscriber,
    WebhookEvent,
    WebhookSubscriptions,
    WebhookType,
)
from bitgen.page import Page

_SIGNATURE_HEADER = "x-bitgen-signature"
_TIMESTAMP_HEADER = "x-bitgen-timestamp"


class WebhooksResource:
    """The deliveries of the events of the organization to an endpoint of the integrator. Wherever the API expects the
    organization, the SDK sends the key's scope. Every method raises a `BitgenError` when the API answers an error or
    no HTTP answer is received; an invalid argument raises a `ValueError` (or a `TypeError`) before any request.
    `verify()` checks a delivery received by the endpoint, locally, without any request."""

    DEFAULT_TOLERANCE: Final = 300
    """Default freshness window of `verify()`, in seconds"""

    def __init__(self, http: HttpClient) -> None:
        self._http = http

    def activate(self, endpoint: str) -> None:
        """Activate the webhooks of the organization: sets the endpoint (`https://` is added when the scheme is missing)
        and generates the secret — read it with `list()`"""
        body = {"endpoint": values.string(endpoint, "endpoint")}
        self._http.post(f"/webhook/security/{self._organization()}/activate", body)

    def updateEndpoint(self, endpoint: str) -> None:
        """Change the delivery endpoint"""
        body = {"endpoint": values.string(endpoint, "endpoint")}
        self._http.patch(f"/webhook/security/{self._organization()}", body)

    def regenerate(self) -> None:
        """Generate a new secret — it is not returned: read it with `list()`; the previous one stops validating
        immediately"""
        self._http.patch(f"/webhook/security/{self._organization()}/regenerate")

    def list(self, *, includeArchived: bool | None = None) -> WebhookSubscriptions:
        """The secret, the endpoint and the subscriptions of the organization — `includeArchived` adds the `ARCHIVED`
        subscriptions"""
        query = {"includeArchived": values.optional_bool(includeArchived, "includeArchived")}
        return WebhookSubscriptions.from_dict(_cast.answer(self._http.get(f"/webhooks/{self._organization()}", query)))

    def subscribe(self, event: str | WebhookType) -> Created:
        """Subscribe the organization to an event of the catalogue, by name (a `WebhookEventName` constant, or any
        name), by uuid, or by model. Returns the uuid of the subscription."""
        body = {"organization": self._http.scope, "event": reference.resolve(event, WebhookType, "event")}
        return Created.from_dict(_cast.answer(self._http.post("/webhooks", body)))

    def archive(self, subscriber: str | Subscriber) -> None:
        """Archive a subscription: the event is no longer delivered"""
        self._http.delete(f"/webhooks/{_subscriber(subscriber)}")

    def reactivate(self, subscriber: str | Subscriber) -> None:
        """Reactivate an archived subscription"""
        self._http.post(f"/webhooks/{_subscriber(subscriber)}")

    def logs(
        self, subscriber: str | Subscriber, *, offset: int | None = None, limit: int | None = None
    ) -> Page[DeliveryLog]:
        """The delivery attempts of a subscription"""
        query = {"offset": values.optional_int(offset, "offset"), "limit": values.optional_int(limit, "limit")}
        answer = self._http.get(f"/webhooks/{_subscriber(subscriber)}/logs", query)
        return Page.from_dict(_cast.answer(answer), DeliveryLog.from_dict)

    def catalog(self) -> Page[WebhookType]:
        """The catalogue of events, all states (`ARCHIVED` included) — not paginated"""
        return Page.from_dict(_cast.answer(self._http.get("/webhook")), WebhookType.from_dict)

    def catalogItem(self, webhook: str | WebhookType) -> WebhookType:
        """One event of the catalogue, by uuid or by model"""
        segment = path.segment(reference.resolve(webhook, WebhookType, "webhook"), "webhook")
        return WebhookType.from_dict(_cast.answer(self._http.get(f"/webhook/{segment}")))

    def verify(
        self,
        rawBody: bytes | str,
        headers: ReceivedHeaders,
        secret: str,
        tolerance: int | float = DEFAULT_TOLERANCE,
    ) -> WebhookEvent:
        """Verify a delivery received by the endpoint and return its envelope — no request: the check runs locally.
        Recomputes `HMAC_SHA256(secret, "<timestamp>.<rawBody>")` on the raw bytes, compares it with `X-BITGEN-
        Signature` in constant time, then checks `X-BITGEN-Timestamp` against `tolerance`, then parses the JSON
        envelope. `rawBody` is the body exactly as received (bytes, or the same text) — never a re-serialized JSON;
        `headers` the headers as received: a `dict`, a WSGI `environ` (`HTTP_X_BITGEN_…` keys), the `headers` of a
        Django, Flask, Starlette or `http.server` request, or a plain list of `(name, value)` pairs (the raw headers of
        an ASGI scope) — names are matched case-insensitively, a multi-valued header keeps its first value; `secret` the
        secret of the organization (`list().secret`); `tolerance` the maximum distance, in seconds, between now and the
        timestamp of the delivery — `300` by default, `0` disables the check. A delivery that fails raises a
        `BitgenError` with `status` `0` and the code `missing_signature`, `invalid_signature`, `missing_timestamp`,
        `timestamp_expired` or `invalid_payload` — the secret never appears in it. An unusable argument (empty `rawBody`
        or `secret`, negative or non-finite `tolerance`) raises a `ValueError` (a `TypeError` on a wrong type)."""
        body = _raw_body(rawBody)
        pairs = _pairs(headers)
        if not isinstance(secret, str):
            raise TypeError("secret must be a non-empty string")
        if secret == "":
            raise ValueError("secret must be a non-empty string")
        if isinstance(tolerance, bool) or not isinstance(tolerance, int | float):
            raise TypeError("tolerance must be a number of seconds >= 0")
        if not math.isfinite(tolerance) or tolerance < 0:
            raise ValueError("tolerance must be a number of seconds >= 0")

        signature = _header(pairs, _SIGNATURE_HEADER)
        if signature is None or signature == "":
            raise _rejected("missing_signature")
        timestamp = _header(pairs, _TIMESTAMP_HEADER)
        if timestamp is None or timestamp == "":
            raise _rejected("missing_timestamp")

        # Signature first: nothing else is trusted before it matches
        digest = hmac.new(secret.encode("utf-8"), timestamp.encode("utf-8") + b"." + body, hashlib.sha256)
        expected = b"sha256=" + digest.hexdigest().encode("ascii")
        given = signature.strip().lower().encode("utf-8")
        if len(given) != len(expected) or not hmac.compare_digest(expected, given):
            raise _rejected("invalid_signature")

        issued_at = _number(timestamp)
        if issued_at is None:
            raise _rejected("missing_timestamp")
        if tolerance > 0 and abs(time.time() - issued_at) > tolerance:
            raise _rejected("timestamp_expired")
        return _envelope(body)

    def _organization(self) -> str:
        """The scope of the key, as the `{organization}` path segment"""
        return path.segment(self._http.scope, "scope")


def _subscriber(subscriber: str | Subscriber) -> str:
    return path.segment(reference.resolve(subscriber, Subscriber, "subscriber"), "subscriber")


def _raw_body(rawBody: object) -> bytes:
    """The received bytes — a text is encoded back to UTF-8 (`surrogateescape`: a text decoded that way gives back
    the exact bytes)"""
    if isinstance(rawBody, str):
        try:
            body = rawBody.encode("utf-8", "surrogateescape")
        except UnicodeEncodeError:
            raise ValueError("rawBody must be the received body: bytes, or a text that encodes to UTF-8") from None
    elif isinstance(rawBody, bytes):
        body = rawBody
    else:
        raise TypeError("rawBody must be the received body: bytes or str")
    if body == b"":
        raise ValueError("rawBody must be the received body, not empty")
    return body


def _pairs(headers: object) -> list[tuple[object, object]]:
    """The `(name, value)` pairs of the received headers, whatever object carries them"""
    items = getattr(headers, "items", None)
    if callable(items):
        candidates = list(items())
    elif isinstance(headers, list | tuple):
        candidates = list(headers)
    else:
        raise TypeError("headers must be a mapping of the received headers, or a list of (name, value) pairs")
    if not all(isinstance(pair, tuple) and len(pair) == 2 for pair in candidates):
        raise TypeError("headers must be a mapping of the received headers, or a list of (name, value) pairs")
    return [(key, value) for key, value in candidates]


def _header(pairs: list[tuple[object, object]], name: str) -> str | None:
    """Case-insensitive lookup, `HTTP_X_BITGEN_…` (WSGI) included; a multi-valued header keeps its first value"""
    for key, value in pairs:
        raw_key = key.decode("latin-1") if isinstance(key, bytes) else str(key)
        normalized = raw_key.lower().removeprefix("http_").replace("_", "-")
        if normalized != name:
            continue
        found: object = value
        if isinstance(value, list | tuple):
            found = value[0] if len(value) > 0 else None
        if isinstance(found, bytes):
            return found.decode("latin-1")
        if isinstance(found, str):
            return found
        if isinstance(found, int | float) and not isinstance(found, bool):
            return str(found)
        return None
    return None


def _number(text: str) -> float | None:
    """The epoch seconds of the header, `None` when it is not a finite number"""
    try:
        parsed = float(text.strip())
    except ValueError:
        return None
    return parsed if math.isfinite(parsed) else None


def _envelope(body: bytes) -> WebhookEvent:
    """The JSON envelope `{ delivery_id, timestamp, event, data }` — anything else is `invalid_payload`"""
    try:
        decoded = _decode(body.decode("utf-8"))
    except ValueError:
        raise _rejected("invalid_payload") from None
    timestamp = decoded.get("timestamp") if isinstance(decoded, dict) else None
    if (
        not isinstance(decoded, dict)
        or not isinstance(decoded.get("delivery_id"), str)
        or isinstance(timestamp, bool)
        or not isinstance(timestamp, int | float)
        or not isinstance(decoded.get("event"), str)
        or "data" not in decoded
    ):
        raise _rejected("invalid_payload")
    return WebhookEvent.from_dict(_cast.as_object(decoded))


def _rejected(code: str) -> BitgenError:
    """Verification failure — no HTTP status, and never the secret in it"""
    return BitgenError(0, code)
