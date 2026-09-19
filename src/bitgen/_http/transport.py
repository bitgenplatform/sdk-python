"""The wire: one HTTP request, one raw response. TLS verified, redirects never followed, one deadline for the whole
request."""

from __future__ import annotations

import contextlib
import http.client
import socket
import ssl
import threading
from dataclasses import dataclass
from typing import Any, Protocol
from urllib.parse import urlsplit


@dataclass(frozen=True, slots=True)
class Response:
    """What a Transport got back: the status, the reason phrase of the status line (may be empty) and the raw body."""

    status: int
    reason: str
    body: bytes


class TransportError(Exception):
    """No HTTP response at all. `code` is `request_timeout` or `network_error`; the message is the operating system's
    words for an OSError (DNS, refused, TLS, timed out), the class name alone for an http.client exception — never
    anything the server sent, never the API key (which only travels in headers)."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code

    def __reduce__(self) -> tuple[type[TransportError], tuple[str, str], dict[str, Any]]:
        return (type(self), (self.code, str(self)), self.__dict__)


class Transport(Protocol):
    """Sends one HTTP request and returns the raw response. Never follows redirects."""

    def send(self, method: str, url: str, headers: dict[str, str], body: bytes | None, timeout: float) -> Response:
        """`body` is already serialized — `None` sends no body. `timeout` bounds the whole request, in seconds,
        `0` = none. Raises `TransportError` when no HTTP response was received (timeout, DNS, connection, TLS…)."""
        ...


class HttpTransport:
    """The transport of the SDK: `http.client` from the standard library, TLS verified against the certificates of the
    system, redirects never followed (a 3xx is answered as it is), and one deadline for the whole request — connection,
    request, headers and body — not one per network operation: a timer shuts the socket down when it passes."""

    def __init__(self) -> None:
        self._context = ssl.create_default_context()

    def send(self, method: str, url: str, headers: dict[str, str], body: bytes | None, timeout: float) -> Response:
        parts = urlsplit(url)
        host = parts.hostname or ""
        target = parts.path + (f"?{parts.query}" if parts.query else "")
        connection: http.client.HTTPConnection
        if parts.scheme == "https":
            connection = http.client.HTTPSConnection(host, parts.port, timeout=timeout or None, context=self._context)
        else:
            connection = http.client.HTTPConnection(host, parts.port, timeout=timeout or None)
        # A body-less POST / PUT / PATCH / DELETE still announces `Content-Length: 0`, as the other SDKs do
        payload = body if body is not None or method in ("GET", "HEAD") else b""
        # The deadline of the whole request: when it passes, the timer shuts the socket down and whatever blocking
        # read is in progress fails; `expired` tells such a failure from a genuine network error
        expired = threading.Event()
        timer = threading.Timer(timeout, _shutdown, (connection, expired)) if timeout > 0 else None
        failure: TransportError
        try:
            if timer is not None:
                timer.daemon = True
                timer.start()
            try:
                connection.request(method, target, body=payload, headers=headers)
                response = connection.getresponse()
                data = response.read()
                if expired.is_set():
                    raise TimeoutError("the request deadline has passed")
                return Response(response.status, response.reason, data)
            except (OSError, http.client.HTTPException) as error:
                # a socket timeout is a TimeoutError (an OSError); the timer's shutdown ends in an OSError or an
                # incomplete answer (an HTTPException)
                code = "request_timeout" if isinstance(error, TimeoutError) or expired.is_set() else "network_error"
                failure = _translate(code, error)
        finally:
            if timer is not None:
                timer.cancel()
            connection.close()
        # raised outside the `except`: an http.client exception is neither the cause nor the context of the failure
        raise failure


def _translate(code: str, error: Exception) -> TransportError:
    """The transport error to raise. An OSError (DNS, refused, TLS, timed out) is kept as the cause, with the operating
    system's words; an http.client exception is dropped and only named — a `BadStatusLine` carries the first line the
    server sent, and a server that reflects the request would put the key in it"""
    if isinstance(error, http.client.HTTPException):
        return TransportError(code, type(error).__name__)
    failure = TransportError(code, f"{type(error).__name__}: {error}")
    failure.__cause__ = error
    return failure


def _shutdown(connection: http.client.HTTPConnection, expired: threading.Event) -> None:
    """The deadline has passed: wake whatever blocking read is in progress on the socket"""
    expired.set()
    sock = connection.sock
    if sock is None:
        return
    with contextlib.suppress(OSError):
        sock.shutdown(socket.SHUT_RDWR)
