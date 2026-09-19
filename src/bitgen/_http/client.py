"""The HTTP layer of the SDK: URL and query building, headers, JSON bodies, and the mapping of every answer to a decoded
value or a `BitgenError`. The wire itself is the Transport."""

from __future__ import annotations

import json
from collections.abc import Mapping
from typing import Any
from urllib.parse import quote

from bitgen._http.transport import Response, Transport, TransportError
from bitgen.errors import BitgenError

_REDACTABLE_KEY = 8
"""Shortest key that is redacted from an error — a real key is far longer, a shorter one is a placeholder"""

Query = Mapping[str, str | int | float | bool | None]
"""Query string entries — `None` entries are skipped, booleans travel as `true` / `false`"""


class HttpClient:
    """`scope` is the organization uuid of the key — resources use it where the API expects the organization."""

    def __init__(
        self, transport: Transport, scope: str, apiKey: str, baseUrl: str, timeout: float, userAgent: str
    ) -> None:
        self._transport = transport
        self.scope = scope
        self._apiKey = apiKey
        self._baseUrl = baseUrl
        self._timeout = timeout
        self._headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": userAgent,
            "BITGEN-Scope": scope,
            "Api-key": apiKey,
        }

    def get(self, path: str, query: Query | None = None) -> Any:
        return self.request("GET", path, query)

    def post(self, path: str, body: object = None) -> Any:
        return self.request("POST", path, None, body)

    def put(self, path: str, body: object = None) -> Any:
        return self.request("PUT", path, None, body)

    def patch(self, path: str, body: object = None) -> Any:
        return self.request("PATCH", path, None, body)

    def delete(self, path: str, body: object = None) -> Any:
        return self.request("DELETE", path, None, body)

    def request(self, method: str, path: str, query: Query | None = None, body: object = None) -> Any:
        """Sends the request and returns the decoded JSON answer — `None` on `204` or an empty body.
        Anything outside 2xx, a 2xx that is not JSON, or no HTTP answer at all → `BitgenError`."""
        url = self._baseUrl + path + _query_string(query)
        encoded = None if body is None else _encode(body)
        try:
            response = self._transport.send(method, url, self._headers, encoded, self._timeout)
        except TransportError as error:
            raise BitgenError(0, error.code) from error

        status = response.status
        text = "" if status == 204 else response.body.decode("utf-8", errors="replace")
        # v4 sends the real HTTP status: anything outside 2xx is an error, a redirect included
        if status < 200 or status > 299:
            code = _error_code(text)
            raise BitgenError(status, self._redact(code if code is not None else _raw_body(text, response)))
        if text.strip() == "":
            return None
        try:
            return _decode(text)
        except ValueError as error:
            # A 2xx that is not JSON is not an answer of the API (proxy page…): report it as an error
            raise BitgenError(status, self._redact(_raw_body(text, response))) from error

    def _redact(self, code: str) -> str:
        """A raw body that echoes the request (a debugging proxy page…) must not put the key in the error. A key shorter
        than a credential can be (a placeholder of a test) is left alone: replacing its every occurrence would garble
        the codes of the API (`unknown_asset` with the key `k`)."""
        return code.replace(self._apiKey, "[redacted]") if len(self._apiKey) >= _REDACTABLE_KEY else code


def _query_string(query: Query | None) -> str:
    if not query:
        return ""
    pairs: list[str] = []
    for key, value in query.items():
        if value is None:
            continue
        text = ("true" if value else "false") if isinstance(value, bool) else str(value)
        pairs.append(f"{quote(key, safe='')}={quote(text, safe='')}")
    return "?" + "&".join(pairs) if pairs else ""


def _encode(body: object) -> bytes:
    """Compact JSON, unicode and slashes kept as they are; `NaN` / `Infinity` are not JSON and are refused"""
    return json.dumps(body, ensure_ascii=False, separators=(",", ":"), allow_nan=False).encode("utf-8")


def _decode(text: str) -> Any:
    """Strict JSON: `NaN` / `Infinity`, which Python would accept, are not JSON"""
    return json.loads(text, parse_constant=_not_json)


def _not_json(constant: str) -> Any:
    raise ValueError(f"{constant} is not JSON")


def _error_code(text: str) -> str | None:
    """The stable `message` of an API error body `{ error, message, code }`, or `None` when the body is not one"""
    try:
        decoded = _decode(text)
    except ValueError:
        return None
    if not isinstance(decoded, dict):
        return None
    message = decoded.get("message")
    if not isinstance(message, str) or message == "":
        return None
    return message


def _raw_body(text: str, response: Response) -> str:
    """Raw body, or the reason phrase, or the status as text — never empty"""
    trimmed = text.strip()
    if trimmed != "":
        return trimmed
    return response.reason if response.reason != "" else str(response.status)
