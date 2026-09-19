"""Throwaway HTTP servers of the tests, in a thread of the test process."""

from __future__ import annotations

import ssl
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any


class QuietHandler(BaseHTTPRequestHandler):
    """No access log, no traceback when the client hangs up first (the timeout tests do)"""

    protocol_version = "HTTP/1.1"

    def log_message(self, format: str, *args: Any) -> None:
        pass


class QuietServer(ThreadingHTTPServer):
    daemon_threads = True

    def handle_error(self, request: Any, client_address: Any) -> None:
        """A client that hung up (the timeout tests) is expected; any other failure of a handler is a bug, printed"""
        error = sys.exc_info()[1]
        if not isinstance(error, BrokenPipeError | ConnectionResetError | ssl.SSLError):
            super().handle_error(request, client_address)


class Server:
    """Serves `handler` on a free port of 127.0.0.1 until `close()`"""

    def __init__(self, handler: type[BaseHTTPRequestHandler]) -> None:
        self.httpd = QuietServer(("127.0.0.1", 0), handler)
        self.port: int = self.httpd.server_address[1]
        self._thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)

    def start(self) -> Server:
        self._thread.start()
        return self

    def close(self) -> None:
        self.httpd.shutdown()
        self.httpd.server_close()
        self._thread.join(timeout=5)
