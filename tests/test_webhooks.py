"""The `webhooks` resource against the fake transport: exact requests, mapping of the answers, errors, refusals —
`verify` has its own file, `tests/test_webhooks_verify.py`."""

from __future__ import annotations

import json
from typing import Any

import pytest

from bitgen import BitgenError
from bitgen._http.client import HttpClient
from bitgen.models import Created, SubscriberState, WebhookEventName
from bitgen.resources.webhooks import WebhooksResource
from tests.fake_transport import FakeTransport

# An event of the catalogue (contract § 10)
TYPE: dict[str, Any] = {
    "uuid": "wh-1",
    "state": "ENABLED",
    "name": "custody.sent",
    "label": '{"fr":"Envoi","en":"Sent"}',
    "data": "{}",
    "somethingNew": True,
}
# A realistic `GET /webhooks/{organization}` body
SUBSCRIPTIONS: dict[str, Any] = {
    "secret": "whsec_0123456789abcdef",
    "endpoint": "https://example.com/bitgen",
    "items": [
        {"uuid": "sub-1", "state": "ENABLED", "updatedAt": 1700000000, "webhook": TYPE},
        {
            "uuid": "sub-2",
            "state": "ARCHIVED",
            "updatedAt": 1700003600,
            "webhook": {
                "uuid": "wh-2",
                "state": "ARCHIVED",
                "name": "trading.buy",
                "label": '{"fr":"Achat","en":"Buy"}',
                "data": '{"legacy":true}',
            },
        },
    ],
}


@pytest.fixture
def transport() -> FakeTransport:
    return FakeTransport()


@pytest.fixture
def webhooks(transport: FakeTransport) -> WebhooksResource:
    return WebhooksResource(HttpClient(transport, "org-uuid", "k", "https://api.test", 1.0, "ua"))


def test_security_routes_carry_the_scope_and_the_endpoint(webhooks: WebhooksResource, transport: FakeTransport) -> None:
    transport.will_answer(201, "[]")
    webhooks.activate("https://example.com/bitgen")
    assert (transport.last().method, transport.last().url) == (
        "POST",
        "https://api.test/webhook/security/org-uuid/activate",
    )
    assert transport.last().body == b'{"endpoint":"https://example.com/bitgen"}'
    transport.will_answer(200, "[]")
    webhooks.updateEndpoint("example.com/bitgen/v2")
    assert (transport.last().method, transport.last().url) == ("PATCH", "https://api.test/webhook/security/org-uuid")
    assert transport.last().body == b'{"endpoint":"example.com/bitgen/v2"}'
    transport.will_answer(200, "[]")
    webhooks.regenerate()
    assert (transport.last().method, transport.last().url) == (
        "PATCH",
        "https://api.test/webhook/security/org-uuid/regenerate",
    )
    assert transport.last().body is None  # no body: the secret is read with list()


def test_the_scope_is_encoded_as_a_path_segment(transport: FakeTransport) -> None:
    webhooks = WebhooksResource(HttpClient(transport, "org/1 2", "k", "https://api.test", 1.0, "ua"))
    webhooks.regenerate()
    assert transport.last().url == "https://api.test/webhook/security/org%2F1%202/regenerate"
    transport.will_answer(200, json.dumps(SUBSCRIPTIONS))
    webhooks.list()
    assert transport.last().url == "https://api.test/webhooks/org%2F1%202"
    transport.will_answer(201, '{"uuid":"sub-1"}')
    webhooks.subscribe(WebhookEventName.CUSTODY_SENT)
    assert (
        transport.last().body == b'{"organization":"org/1 2","event":"custody.sent"}'
    )  # the body carries the scope as is


def test_list_maps_the_secret_the_endpoint_and_the_subscriptions(
    webhooks: WebhooksResource, transport: FakeTransport
) -> None:
    transport.will_answer(200, json.dumps(SUBSCRIPTIONS))
    subscriptions = webhooks.list(includeArchived=True)
    assert (transport.last().method, transport.last().url) == (
        "GET",
        "https://api.test/webhooks/org-uuid?includeArchived=true",
    )
    assert subscriptions.secret == "whsec_0123456789abcdef"
    assert subscriptions.endpoint == "https://example.com/bitgen"
    assert len(subscriptions.items) == 2
    first = subscriptions.items[0]
    assert (first.uuid, first.state, first.updatedAt) == ("sub-1", SubscriberState.ENABLED, 1700000000)
    assert (first.webhook.uuid, first.webhook.state, first.webhook.name) == (
        "wh-1",
        SubscriberState.ENABLED,
        WebhookEventName.CUSTODY_SENT,
    )
    assert first.webhook.label == '{"fr":"Envoi","en":"Sent"}'
    assert first.webhook.data == "{}"
    assert subscriptions.items[1].state == SubscriberState.ARCHIVED
    assert subscriptions.items[1].webhook.name == WebhookEventName.TRADING_BUY
    transport.will_answer(200, json.dumps({"secret": "s", "endpoint": "https://example.com", "items": []}))
    fresh = webhooks.list()
    assert transport.last().url == "https://api.test/webhooks/org-uuid"
    assert fresh.items == []
    transport.will_answer(200, json.dumps(SUBSCRIPTIONS))
    webhooks.list(includeArchived=False)
    assert transport.last().url == "https://api.test/webhooks/org-uuid?includeArchived=false"


def test_subscribe_archive_and_reactivate(webhooks: WebhooksResource, transport: FakeTransport) -> None:
    transport.will_answer(201, '{"uuid":"sub-1"}')
    created = webhooks.subscribe(WebhookEventName.CUSTODY_SENT)
    assert isinstance(created, Created)
    assert created.uuid == "sub-1"
    assert (transport.last().method, transport.last().url) == ("POST", "https://api.test/webhooks")
    assert transport.last().body == b'{"organization":"org-uuid","event":"custody.sent"}'
    transport.will_answer(201, '{"uuid":"sub-3"}')
    webhooks.subscribe("wh-3")  # by uuid of the catalogue, or any name: the catalogue may grow
    assert transport.last().body == b'{"organization":"org-uuid","event":"wh-3"}'
    transport.will_answer(200, "[]")
    webhooks.archive("sub-1")
    assert (transport.last().method, transport.last().url) == ("DELETE", "https://api.test/webhooks/sub-1")
    assert transport.last().body is None
    transport.will_answer(201, "[]")
    webhooks.reactivate("sub-1")
    assert (transport.last().method, transport.last().url) == ("POST", "https://api.test/webhooks/sub-1")
    assert transport.last().body is None  # no body: the transport sends Content-Length: 0


def test_logs_map_the_delivery_attempts(webhooks: WebhooksResource, transport: FakeTransport) -> None:
    items = [
        {
            "date": 1700000000,
            "webhook": "custody.sent",
            "url": "https://example.com/bitgen",
            "status": "SENT",
            "http_code": 204,
            "duration_ms": 87,
            "attempts": 1,
            "payload": {"delivery_id": "d-1", "event": "custody.sent"},
            "error": None,
        },
        {
            "date": 1700000060,
            "webhook": "custody.sent",
            "url": "https://example.com/bitgen",
            "status": "FAILED",
            "http_code": None,
            "duration_ms": None,
            "attempts": 2,
            "payload": {},
            "error": "connection refused",
        },
    ]
    transport.will_answer(200, json.dumps({"count": 2, "items": items}))
    page = webhooks.logs("sub-1", offset=0, limit=50)
    assert transport.last().url == "https://api.test/webhooks/sub-1/logs?offset=0&limit=50"
    assert page.count == 2
    first = page.items[0]
    assert (first.date, first.webhook, first.url, first.status) == (
        1700000000,
        WebhookEventName.CUSTODY_SENT,
        "https://example.com/bitgen",
        "SENT",
    )
    assert (first.http_code, first.duration_ms, first.attempts) == (204, 87, 1)
    assert first.payload == {"delivery_id": "d-1", "event": "custody.sent"}
    assert first.error is None
    assert page.items[1].http_code is None
    assert page.items[1].duration_ms is None
    assert page.items[1].payload == {}
    assert page.items[1].error == "connection refused"
    transport.will_answer(200, json.dumps({"count": 0, "items": []}))
    webhooks.logs("sub-1")
    assert transport.last().url == "https://api.test/webhooks/sub-1/logs"


def test_catalog_and_catalog_item(webhooks: WebhooksResource, transport: FakeTransport) -> None:
    transport.will_answer(200, json.dumps({"count": 1, "items": [TYPE]}))
    catalog = webhooks.catalog()
    assert transport.last().url == "https://api.test/webhook"
    assert catalog.count == 1
    assert catalog.items[0].name == WebhookEventName.CUSTODY_SENT
    transport.will_answer(200, json.dumps(TYPE))
    item = webhooks.catalogItem("wh-1")
    assert transport.last().url == "https://api.test/webhook/wh-1"
    assert (item.uuid, item.state, item.label, item.data) == (
        "wh-1",
        SubscriberState.ENABLED,
        '{"fr":"Envoi","en":"Sent"}',
        "{}",
    )


def test_the_event_names_of_the_contract() -> None:
    assert len(WebhookEventName.VALUES) == 33
    assert WebhookEventName.USER_IDENTITY_STEP_VALIDATED == "user.identity.step.validated"
    assert WebhookEventName.ORGANIZATION_IDENTITY_REQUEST == "organization.identity.request"
    assert WebhookEventName.ALERT_STATUS == "alert.status"
    assert WebhooksResource.DEFAULT_TOLERANCE == 300


@pytest.mark.parametrize(
    ("status", "code", "call"),
    [
        (400, "webhook_security_https_required", lambda webhooks: webhooks.activate("http://example.com")),
        (404, "unknown_webhook_security", lambda webhooks: webhooks.regenerate()),
        (404, "unknown_webhook_subscriber", lambda webhooks: webhooks.archive("sub-x")),
        (404, "unknown_webhook", lambda webhooks: webhooks.catalogItem("wh-x")),
        (
            409,
            "webhook_subscription_already_exists",
            lambda webhooks: webhooks.subscribe(WebhookEventName.CUSTODY_SENT),
        ),
        (412, "organization_not_enabled", lambda webhooks: webhooks.updateEndpoint("https://example.com")),
        (429, "webhook_security_already_enabled", lambda webhooks: webhooks.activate("https://example.com")),
        (403, "forbidden_permission", lambda webhooks: webhooks.list()),
    ],
)
def test_api_errors_become_bitgen_errors(
    webhooks: WebhooksResource, transport: FakeTransport, status: int, code: str, call: Any
) -> None:
    transport.will_answer(status, json.dumps({"error": True, "message": code, "code": status}))
    with pytest.raises(BitgenError) as caught:
        call(webhooks)
    assert (caught.value.status, caught.value.code) == (status, code)


def test_invalid_arguments_are_refused_before_any_request(webhooks: WebhooksResource, transport: FakeTransport) -> None:
    for call in (
        lambda: webhooks.archive(""),
        lambda: webhooks.reactivate(".."),
        lambda: webhooks.logs("."),
        lambda: webhooks.catalogItem(""),
        lambda: webhooks.subscribe(" "),
    ):
        with pytest.raises(ValueError):
            call()
    with pytest.raises(TypeError, match=r"^endpoint must be a string$"):
        webhooks.activate(None)  # type: ignore[arg-type]
    with pytest.raises(TypeError, match=r"^includeArchived must be a boolean$"):
        webhooks.list(includeArchived="yes")  # type: ignore[arg-type]
    with pytest.raises(TypeError, match=r"^offset must be an integer$"):
        webhooks.logs("sub-1", offset="0")  # type: ignore[arg-type]
    assert transport.requests == []


def test_models_are_accepted_for_the_subscription_and_the_event(
    webhooks: WebhooksResource, transport: FakeTransport
) -> None:
    transport.will_answer(200, json.dumps(SUBSCRIPTIONS))
    subscription = webhooks.list().items[0]
    transport.will_answer(200, "[]")
    webhooks.archive(subscription)
    assert transport.last().url == "https://api.test/webhooks/sub-1"
    transport.will_answer(201, "[]")
    webhooks.reactivate(subscription)
    assert transport.last().url == "https://api.test/webhooks/sub-1"
    transport.will_answer(200, json.dumps({"count": 0, "items": []}))
    webhooks.logs(subscription)
    assert transport.last().url == "https://api.test/webhooks/sub-1/logs"
    transport.will_answer(200, json.dumps(TYPE))
    webhooks.catalogItem(subscription.webhook)
    assert transport.last().url == "https://api.test/webhook/wh-1"
    transport.will_answer(201, '{"uuid":"sub-9"}')
    webhooks.subscribe(subscription.webhook)  # an event of the catalogue, by model: its uuid is sent
    assert transport.last().body == b'{"organization":"org-uuid","event":"wh-1"}'
    sent = len(transport.requests)
    with pytest.raises(TypeError, match=r"^subscriber must be a uuid string, or a Subscriber model$"):
        webhooks.archive(subscription.webhook)  # type: ignore[arg-type]
    with pytest.raises(TypeError, match=r"^webhook must be a uuid string, or a WebhookType model$"):
        webhooks.catalogItem(subscription)  # type: ignore[arg-type]
    with pytest.raises(TypeError, match=r"^event must be a uuid string, or a WebhookType model$"):
        webhooks.subscribe(subscription)  # type: ignore[arg-type]
    assert len(transport.requests) == sent
