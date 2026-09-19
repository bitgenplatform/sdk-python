"""The real transport against a throwaway server (tests/server/router.py): headers, bodies, answers, redirect, timeouts,
closed port, TLS."""

from __future__ import annotations

import json
import shutil
import ssl
import subprocess
import time
from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

from bitgen import BitgenError
from bitgen._http.client import HttpClient
from bitgen._http.transport import HttpTransport, TransportError
from tests.server import Server
from tests.server.router import RouterHandler

KEY = "SECRET-KEY-NEVER-SHOWN"


@pytest.fixture(scope="module")
def server() -> Iterator[Server]:
    server = Server(RouterHandler).start()
    yield server
    server.close()


def client(port: int, timeout: float = 5, secure: bool = False) -> HttpClient:
    scheme = "https" if secure else "http"
    return HttpClient(
        HttpTransport(), "org-uuid", KEY, f"{scheme}://127.0.0.1:{port}", timeout, "bitgen-sdk-python/test"
    )


def assert_key_is_nowhere(error: BaseException) -> None:
    """Neither the error, nor its causes, nor its contexts, nor their arguments carry the key"""
    seen: list[BaseException] = []
    pending: list[BaseException | None] = [error]
    while pending:
        current = pending.pop()
        if current is None or current in seen:
            continue
        seen.append(current)
        pending += [current.__cause__, current.__context__]
    for exception in seen:
        for text in (str(exception), repr(exception), repr(exception.args)):
            assert KEY not in text


def test_sends_headers_method_and_body_over_the_wire(server: Server) -> None:
    answer = client(server.port).post("/ok", {"amount": "1.5", "note": "a/b"})
    assert answer["method"] == "POST"
    assert answer["body"] == '{"amount":"1.5","note":"a/b"}'
    headers = {name.lower(): value for name, value in answer["headers"].items()}
    assert headers["content-type"] == "application/json"
    assert headers["accept"] == "application/json"
    assert headers["user-agent"] == "bitgen-sdk-python/test"
    assert headers["bitgen-scope"] == "org-uuid"
    assert headers["api-key"] == KEY
    assert headers["content-length"] == "29"
    assert "expect" not in headers

    # a body-less write still announces an empty body
    answer = client(server.port).post("/ok")
    assert answer["body"] == ""
    assert {name.lower(): value for name, value in answer["headers"].items()}["content-length"] == "0"
    answer = client(server.port).delete("/ok")
    assert answer["method"] == "DELETE"
    assert {name.lower(): value for name, value in answer["headers"].items()}["content-length"] == "0"

    answer = client(server.port).get("/ok")
    assert answer["method"] == "GET"
    assert "content-length" not in {name.lower(): value for name, value in answer["headers"].items()}


def test_error_empty_and_text_answers(server: Server) -> None:
    with pytest.raises(BitgenError) as caught:
        client(server.port).get("/error")
    assert (caught.value.status, caught.value.code) == (412, "bank_rib_required")
    assert client(server.port).get("/empty") is None
    with pytest.raises(BitgenError) as caught:
        client(server.port).get("/text")
    assert (caught.value.status, caught.value.code) == (200, "plain text")
    with pytest.raises(BitgenError) as caught:
        client(server.port).get("/nowhere")
    assert (caught.value.status, caught.value.code) == (500, "Internal Server Error")


def test_a_client_can_be_shared_between_threads(server: Server) -> None:
    shared = client(server.port)
    with ThreadPoolExecutor(max_workers=8) as pool:
        answers = list(pool.map(lambda n: shared.post("/ok", {"n": n}), range(40)))
    assert [json.loads(answer["body"])["n"] for answer in answers] == list(range(40))
    assert all(answer["headers"]["Api-key"] == KEY for answer in answers)


def test_a_server_reflecting_the_request_never_leaks_the_key(server: Server) -> None:
    # the status line is garbage made of the key: http.client reports the line, the SDK keeps the class name only
    with pytest.raises(BitgenError) as caught:
        client(server.port).get("/reflect")
    error = caught.value
    assert (error.status, error.code) == (0, "network_error")
    assert isinstance(error.__cause__, TransportError)
    assert str(error.__cause__) == "BadStatusLine"
    assert error.__cause__.__cause__ is None
    assert error.__cause__.__context__ is None
    assert_key_is_nowhere(error)
    # a non-JSON error body that echoes the request: the key is redacted from the code
    with pytest.raises(BitgenError) as caught:
        client(server.port).get("/leak")
    assert (caught.value.status, caught.value.code) == (502, "Bad gateway while sending Api-key: [redacted]")
    assert_key_is_nowhere(caught.value)


def test_the_tls_context_verifies_certificates_and_hostnames() -> None:
    context = HttpTransport()._context
    assert context.verify_mode == ssl.CERT_REQUIRED
    assert context.check_hostname is True
    assert context.minimum_version >= ssl.TLSVersion.TLSv1_2
    assert context.protocol == ssl.PROTOCOL_TLS_CLIENT


def test_redirects_are_never_followed(server: Server) -> None:
    with pytest.raises(BitgenError) as caught:
        client(server.port).get("/redirect")
    assert (caught.value.status, caught.value.code) == (302, "Found")


def test_timeout_gives_request_timeout_with_status_zero(server: Server) -> None:
    with pytest.raises(BitgenError) as caught:
        client(server.port, timeout=0.2).get("/hang")
    error = caught.value
    assert (error.status, error.code) == (0, "request_timeout")
    assert str(error) == "request_timeout (HTTP 0)"
    assert isinstance(error.__cause__, TransportError)
    # the socket timeout (a TimeoutError, kept as the cause) or the deadline timer (the server is then seen as gone:
    # an http.client exception, named only), whichever fired first
    cause = error.__cause__.__cause__
    assert cause is None or isinstance(cause, OSError)
    assert str(error.__cause__).split(":")[0] in ("RemoteDisconnected", "ConnectionResetError", "TimeoutError")
    assert_key_is_nowhere(error)


def test_the_timeout_bounds_the_whole_request_not_each_read(server: Server) -> None:
    # /drip sends a byte every 300 ms: every single read is fast, the whole answer takes 3 s
    started = time.monotonic()
    with pytest.raises(BitgenError) as caught:
        client(server.port, timeout=1).get("/drip")
    assert caught.value.code == "request_timeout"
    assert time.monotonic() - started < 2.5


def test_no_timeout_waits(server: Server) -> None:
    assert client(server.port, timeout=0).get("/hang") == {"late": True}


def test_closed_port_gives_network_error(server: Server) -> None:
    probe = Server(RouterHandler)
    port = probe.port
    probe.httpd.server_close()
    with pytest.raises(BitgenError) as caught:
        client(port).get("/ok")
    error = caught.value
    assert (error.status, error.code) == (0, "network_error")
    assert isinstance(error.__cause__, TransportError)
    assert isinstance(error.__cause__.__cause__, OSError)
    assert_key_is_nowhere(error)


@pytest.fixture(scope="module")
def tls(tmp_path_factory: pytest.TempPathFactory) -> Iterator[tuple[Server, Path]]:
    """The same server behind TLS, with a self-signed certificate for 127.0.0.1 — returned with the server"""
    openssl = shutil.which("openssl")
    if openssl is None:
        pytest.skip("openssl is needed to issue a self-signed certificate")
    directory = tmp_path_factory.mktemp("tls")
    key, cert = directory / "key.pem", directory / "cert.pem"
    request = ["req", "-x509", "-newkey", "rsa:2048", "-nodes", "-keyout", str(key), "-out", str(cert)]
    subject = ["-days", "1", "-subj", "/CN=127.0.0.1", "-addext", "subjectAltName=IP:127.0.0.1"]
    subprocess.run([openssl, *request, *subject], check=True, capture_output=True)
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.load_cert_chain(str(cert), str(key))
    server = Server(RouterHandler)
    server.httpd.socket = context.wrap_socket(server.httpd.socket, server_side=True)
    server.start()
    yield server, cert
    server.close()


def test_an_untrusted_certificate_is_refused(tls: tuple[Server, Path]) -> None:
    server, _ = tls
    with pytest.raises(BitgenError) as caught:
        client(server.port, secure=True).get("/ok")
    error = caught.value
    assert (error.status, error.code) == (0, "network_error")
    assert isinstance(error.__cause__, TransportError)
    assert isinstance(error.__cause__.__cause__, ssl.SSLCertVerificationError)
    assert_key_is_nowhere(error)


def test_a_trusted_certificate_serves_over_tls_and_the_deadline_holds(tls: tuple[Server, Path]) -> None:
    server, cert = tls
    transport = HttpTransport()
    transport._context.load_verify_locations(str(cert))  # the test trusts its own certificate
    https = HttpClient(transport, "org-uuid", KEY, f"https://127.0.0.1:{server.port}", 1, "bitgen-sdk-python/test")
    answer = https.post("/ok", {"a": 1})
    assert answer["method"] == "POST"
    assert answer["body"] == '{"a":1}'
    started = time.monotonic()
    with pytest.raises(BitgenError) as caught:
        https.get("/drip")
    assert caught.value.code == "request_timeout"
    assert time.monotonic() - started < 2.5
    assert_key_is_nowhere(caught.value)
