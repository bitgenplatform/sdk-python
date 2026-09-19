"""The server of the transport tests: echo, slow answers, redirect, empty, text and error answers."""

from __future__ import annotations

import json
import time
from urllib.parse import urlsplit

from tests.server import QuietHandler


class RouterHandler(QuietHandler):
    def _route(self) -> None:
        path = urlsplit(self.path).path
        length = int(self.headers.get("Content-Length") or 0)
        body = self.rfile.read(length) if length else b""
        if path == "/ok":
            answer = {
                "method": self.command,
                "headers": {name: value for name, value in self.headers.items()},
                "body": body.decode("utf-8"),
            }
            self._json(200, json.dumps(answer).encode("utf-8"))
        elif path == "/hang":
            time.sleep(1)
            self._json(200, b'{"late":true}')
        elif path == "/drip":
            # headers right away, then one byte every 300 ms: only a deadline on the whole request can interrupt it
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", "10")
            self.end_headers()
            for byte in b'{"a":"bc"}':
                time.sleep(0.3)
                self.wfile.write(bytes([byte]))
                self.wfile.flush()
        elif path == "/reflect":
            # a broken server whose status line is the request's own key header: not an HTTP status line at all
            self.wfile.write(f"{self.headers.get('Api-key', '')} reflected\r\n\r\n".encode())
        elif path == "/leak":
            # a debugging proxy page that echoes the request headers in a non-JSON error body
            self._text(502, f"Bad gateway while sending Api-key: {self.headers.get('Api-key', '')}".encode())
        elif path == "/redirect":
            self.send_response(302)
            self.send_header("Location", "/ok")
            self.send_header("Content-Length", "0")
            self.end_headers()
        elif path == "/empty":
            self.send_response(204)
            self.end_headers()
        elif path == "/text":
            self._text(200, b"plain text")
        elif path == "/error":
            self._json(412, b'{"error":true,"message":"bank_rib_required","code":412}')
        else:
            self._text(500, b"Internal Server Error")

    def _json(self, status: int, body: bytes) -> None:
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _text(self, status: int, body: bytes) -> None:
        self.send_response(status)
        self.send_header("Content-Type", "text/plain")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    do_GET = _route
    do_POST = _route
    do_PUT = _route
    do_PATCH = _route
    do_DELETE = _route
