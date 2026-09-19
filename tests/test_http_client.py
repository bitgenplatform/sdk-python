"""The HTTP layer against the fake transport: headers, URL, query, bodies, answers and errors."""

from __future__ import annotations

import json

import pytest

from bitgen import VERSION, BitgenError
from bitgen._http.client import HttpClient
from bitgen._http.transport import TransportError
from tests.fake_transport import FakeTransport


@pytest.fixture
def transport() -> FakeTransport:
    return FakeTransport()


@pytest.fixture
def http(transport: FakeTransport) -> HttpClient:
    return HttpClient(
        transport, "org-uuid", "SECRET-KEY", "https://api.example.test", 30.0, f"bitgen-sdk-python/{VERSION}"
    )


def test_sends_the_exact_headers_and_url(http: HttpClient, transport: FakeTransport) -> None:
    transport.will_answer(200, '{"ok":true}')
    assert http.get("/asset") == {"ok": True}

    request = transport.last()
    assert request.method == "GET"
    assert request.url == "https://api.example.test/asset"
    assert request.headers == {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "User-Agent": f"bitgen-sdk-python/{VERSION}",
        "BITGEN-Scope": "org-uuid",
        "Api-key": "SECRET-KEY",
    }
    assert request.body is None
    assert request.timeout == 30.0
    assert http.scope == "org-uuid"


def test_query_string_skips_nones_and_writes_booleans_as_words(http: HttpClient, transport: FakeTransport) -> None:
    http.get(
        "/customer", {"offset": 0, "limit": 50, "includeClosed": True, "strict": False, "manager": None, "q": "a b&c"}
    )
    assert (
        transport.last().url
        == "https://api.example.test/customer?offset=0&limit=50&includeClosed=true&strict=false&q=a%20b%26c"
    )

    http.get("/customer", {"manager": None})
    assert transport.last().url == "https://api.example.test/customer"

    http.get("/custody/u/portfolio", {"asset": "a/b"})
    assert transport.last().url == "https://api.example.test/custody/u/portfolio?asset=a%2Fb"


def test_bodies_are_compact_json_with_unicode_and_slashes_kept(http: HttpClient, transport: FakeTransport) -> None:
    transport.will_answer(201, '{"uuid":"u"}')
    assert http.post("/bank", {"amount": "100.00", "message": "BTGN/42 é", "user": None}) == {"uuid": "u"}
    assert transport.last().method == "POST"
    assert transport.last().body == '{"amount":"100.00","message":"BTGN/42 é","user":null}'.encode()

    http.put("/staking/p/rewards", {})
    assert transport.last().body == b"{}"

    http.patch("/webhook/security/o/regenerate")
    assert transport.last().method == "PATCH"
    assert transport.last().body is None

    http.delete("/webhooks/s")
    assert transport.last().method == "DELETE"
    assert transport.last().body is None


def test_empty_body_and_204_give_none(http: HttpClient, transport: FakeTransport) -> None:
    transport.will_answer(204, "ignored")
    assert http.post("/webhooks/s") is None
    transport.will_answer(200, "  ")
    assert http.get("/x") is None
    transport.will_answer(200, "[]")
    assert http.put("/account/u", {"action": {}}) == []


def test_json_error_body_becomes_a_bitgen_error(http: HttpClient, transport: FakeTransport) -> None:
    transport.will_answer(416, '{"error":true,"message":"requested_amount_error","code":416}')
    with pytest.raises(BitgenError) as caught:
        http.put("/bank/u", {"amount": "50"})
    error = caught.value
    assert error.status == 416
    assert error.code == "requested_amount_error"
    assert str(error) == "requested_amount_error (HTTP 416)"
    assert error.__cause__ is None


@pytest.mark.parametrize(
    ("status", "body", "reason", "expected"),
    [
        pytest.param(
            502, "<html>Bad gateway</html>\n", "Bad Gateway", "<html>Bad gateway</html>", id="html error page"
        ),
        pytest.param(404, "", "Not Found", "Not Found", id="empty body with a reason"),
        pytest.param(404, "", "", "404", id="empty body, no reason"),
        pytest.param(302, "", "Found", "Found", id="redirect, never followed"),
        pytest.param(500, '{"error":true}', "Internal Server Error", '{"error":true}', id="json without message"),
        pytest.param(
            500,
            '{"error":true,"message":123}',
            "Internal Server Error",
            '{"error":true,"message":123}',
            id="json with a non-string message",
        ),
        pytest.param(
            500,
            '{"error":true,"message":""}',
            "Internal Server Error",
            '{"error":true,"message":""}',
            id="json with an empty message",
        ),
        pytest.param(200, "not json at all", "OK", "not json at all", id="2xx that is not json"),
    ],
)
def test_non_json_empty_and_redirect_answers_keep_the_raw_text_or_the_reason(
    http: HttpClient, transport: FakeTransport, status: int, body: str, reason: str, expected: str
) -> None:
    transport.will_answer(status, body, reason)
    with pytest.raises(BitgenError) as caught:
        http.get("/x")
    assert caught.value.status == status
    assert caught.value.code == expected


def test_error_code_is_capped_at_200_characters(http: HttpClient, transport: FakeTransport) -> None:
    transport.will_answer(400, json.dumps({"error": True, "message": "x" * 250, "code": 400}))
    with pytest.raises(BitgenError) as caught:
        http.get("/x")
    assert len(caught.value.code) == 200
    transport.will_answer(502, "é" * 250)
    with pytest.raises(BitgenError) as caught:
        http.get("/x")
    assert caught.value.code == "é" * 200


def test_the_key_is_redacted_from_a_code_that_echoes_it(http: HttpClient, transport: FakeTransport) -> None:
    transport.will_answer(502, "proxy error: Api-key: SECRET-KEY, BITGEN-Scope: org-uuid")
    with pytest.raises(BitgenError) as caught:
        http.get("/x")
    assert caught.value.code == "proxy error: Api-key: [redacted], BITGEN-Scope: org-uuid"
    transport.will_answer(400, '{"error":true,"message":"bad SECRET-KEY","code":400}')
    with pytest.raises(BitgenError) as caught:
        http.get("/x")
    assert caught.value.code == "bad [redacted]"
    transport.will_answer(200, "SECRET-KEY is not json")
    with pytest.raises(BitgenError) as caught:
        http.get("/x")
    assert caught.value.code == "[redacted] is not json"
    # a placeholder key (shorter than any credential) is not redacted: the codes of the API stay readable
    short = HttpClient(transport, "org-uuid", "k", "https://api.example.test", 30.0, "ua")
    transport.will_answer(404, '{"error":true,"message":"unknown_asset","code":404}')
    with pytest.raises(BitgenError) as caught:
        short.get("/x")
    assert caught.value.code == "unknown_asset"
    transport.will_answer(502, "proxy error: Api-key: 1234567")
    with pytest.raises(BitgenError) as caught:
        HttpClient(transport, "o", "1234567", "https://api.example.test", 30.0, "ua").get("/x")
    assert caught.value.code == "proxy error: Api-key: 1234567"
    transport.will_answer(502, "proxy error: Api-key: 12345678")
    with pytest.raises(BitgenError) as caught:
        HttpClient(transport, "o", "12345678", "https://api.example.test", 30.0, "ua").get("/x")
    assert caught.value.code == "proxy error: Api-key: [redacted]"


def test_json_is_strict_both_ways(http: HttpClient, transport: FakeTransport) -> None:
    # NaN and Infinity are Python extensions, not JSON: an answer made of them is not an answer of the API
    transport.will_answer(200, "NaN")
    with pytest.raises(BitgenError) as caught:
        http.get("/x")
    assert (caught.value.status, caught.value.code) == (200, "NaN")
    transport.will_answer(500, '{"error":true,"message":Infinity}')
    with pytest.raises(BitgenError) as caught:
        http.get("/x")
    assert caught.value.code == '{"error":true,"message":Infinity}'
    # and they are never sent
    with pytest.raises(ValueError):
        http.post("/x", {"amount": float("nan")})
    assert len(transport.requests) == 2


def test_invalid_utf8_in_a_body_is_replaced_never_raised(http: HttpClient, transport: FakeTransport) -> None:
    transport.will_answer(502, b"\xff\xfe bad bytes")
    with pytest.raises(BitgenError) as caught:
        http.get("/x")
    assert caught.value.status == 502
    assert caught.value.code == "�� bad bytes"


def test_no_http_answer_becomes_status_zero_with_the_transport_error_as_cause(
    http: HttpClient, transport: FakeTransport
) -> None:
    transport.will_fail(TransportError("request_timeout", "TimeoutError: timed out"))
    with pytest.raises(BitgenError) as caught:
        http.get("/hang")
    error = caught.value
    assert error.status == 0
    assert error.code == "request_timeout"
    assert str(error) == "request_timeout (HTTP 0)"
    assert isinstance(error.__cause__, TransportError)

    transport.will_fail(TransportError("network_error", "gaierror: [Errno -2] Name or service not known"))
    with pytest.raises(BitgenError) as caught:
        http.get("/x")
    assert caught.value.code == "network_error"
    assert "SECRET-KEY" not in str(caught.value) + str(caught.value.__cause__)
