"""Records every request and answers with the queued responses (a TransportError in the queue is raised)."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass

from bitgen._http.transport import Response, TransportError


@dataclass(frozen=True, slots=True)
class Request:
    method: str
    url: str
    headers: dict[str, str]
    body: bytes | None
    timeout: float


class FakeTransport:
    def __init__(self) -> None:
        self.requests: list[Request] = []
        self._queue: deque[Response | TransportError] = deque()

    def will_answer(self, status: int, body: str | bytes = "", reason: str = "") -> FakeTransport:
        self._queue.append(Response(status, reason, body.encode("utf-8") if isinstance(body, str) else body))
        return self

    def will_fail(self, error: TransportError) -> FakeTransport:
        self._queue.append(error)
        return self

    def send(self, method: str, url: str, headers: dict[str, str], body: bytes | None, timeout: float) -> Response:
        self.requests.append(Request(method, url, dict(headers), body, timeout))
        following = self._queue.popleft() if self._queue else Response(200, "OK", b"{}")
        if isinstance(following, TransportError):
            raise following
        return following

    def last(self) -> Request:
        if not self.requests:
            raise LookupError("no request was sent")
        return self.requests[-1]
