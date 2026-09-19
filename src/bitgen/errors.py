"""The exceptions of the SDK."""

from __future__ import annotations

from typing import Any

MAX_CODE_LENGTH = 200
"""Longest `code` kept: the API sends short snake_case codes, anything longer is a foreign body (proxy page…)"""


class BitgenError(Exception):
    """Error answered by the API — or no HTTP answer at all.

    `status` is the HTTP status (`0` when no HTTP response was received: `request_timeout`, `network_error`),
    `code` the stable code of the API (`invalid_amount`, `unknown_asset`…) — or the raw response text, truncated to
    200 characters, when the body is not the API's JSON error. `str(error)` is `"<code> (HTTP <status>)"`; for
    `request_timeout` and `network_error`, `__cause__` holds the transport error. Nothing in it ever contains the API
    key.
    """

    def __init__(self, status: int, code: str) -> None:
        self.status = status
        self.code = code[:MAX_CODE_LENGTH]
        super().__init__(f"{self.code} (HTTP {status})")

    def __reduce__(self) -> tuple[type[BitgenError], tuple[int, str], dict[str, Any]]:
        """Pickled and copied by its two arguments (and whatever attributes were added to it) — an error raised in a
        worker process travels back intact"""
        return (type(self), (self.status, self.code), self.__dict__)


class UnexpectedAnswerError(Exception):
    """A 2xx answer of the API that is JSON but not the shape the SDK expects (not an object, not a list of objects
    where the API promises one, a page whose `items` is not a list…): not an error of the API, a contract violation to
    report to BITGEN. Never raised for an error answered by the API — that is a `BitgenError`."""
