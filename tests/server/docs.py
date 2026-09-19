"""The documentation server: the examples of README.md and readme/ run against it, it answers realistic bodies route by
route — extended with every resource. An unknown route is a `500` text, as the API answers."""

from __future__ import annotations

import json
from typing import Any
from urllib.parse import parse_qs, unquote, urlsplit

from tests.server import QuietHandler

NOW = 1_700_000_000


def ticker(price: float, marketcap: float, rank: int, change: float) -> dict[str, Any]:
    return {"price": price, "marketcap": marketcap, "rank": rank, "percentChange24h": change}


def history(current: float) -> dict[str, list[list[float]]]:
    def series(points: int, step: int) -> list[list[float]]:
        return [[NOW - (points - 1 - i) * step, round(current * (0.9 + i / points / 10), 2)] for i in range(points)]

    return {
        "d": series(24, 3600),
        "w": series(7, 86400),
        "m": series(30, 86400),
        "y": series(12, 2592000),
        "all": series(24, 2592000),
    }


def asset(
    uuid: str,
    iso: str,
    label: str,
    contract: str,
    baseUnit: int,
    gasUnit: int,
    caip2: str,
    family: str,
    price: float,
    marketcap: float,
    rank: int,
    change: float,
) -> dict[str, Any]:
    return {
        "uuid": uuid,
        "state": "AVAILABLE",
        "iso": iso,
        "label": label,
        "contractAddress": contract,
        "baseUnit": baseUnit,
        "gasUnit": gasUnit,
        "logo": None,
        "data": "{}",
        "fees": {"low": None, "medium": None, "high": None, "computed": {"gas": str(gasUnit), "native": "0.000021"}},
        "ticker": ticker(price, marketcap, rank, change),
        "history": history(price),
        "network": {
            "uuid": f"net-{iso.lower()}",
            "state": "ENABLED",
            "caip2": caip2,
            "label": label,
            "gasBase": 1,
            "data": "{}",
            "type": {"uuid": f"type-{family}", "code": family, "label": family, "data": "{}"},
        },
    }


ASSETS: dict[str, dict[str, Any]] = {
    "btc": asset(
        "asset-btc",
        "BTC",
        "Bitcoin",
        "",
        8,
        250,
        "bip122:000000000019d6689c085ae165831e93",
        "UTXO",
        61230.4,
        1.2e12,
        1,
        -1.2,
    ),
    "eth": asset("asset-eth", "ETH", "Ethereum", "", 18, 21000, "eip155:1", "EVM", 2031.5, 2.44e11, 2, 0.8),
    "usdc": asset(
        "asset-usdc",
        "USDC",
        "USD Coin",
        "0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48",
        6,
        65000,
        "eip155:1",
        "EVM",
        0.92,
        3.3e10,
        6,
        0.0,
    ),
    "sol": asset(
        "asset-sol",
        "SOL",
        "Solana",
        "",
        9,
        5000,
        "solana:5eykt4UsFv8P8NJdTREpY1vzqKqZKvdp",
        "SOLANA",
        128.4,
        5.6e10,
        5,
        2.1,
    ),
}


def identity(mode: str) -> dict[str, Any]:
    form: dict[str, Any] = (
        {"activity": "software", "submittedAt": 1699000000, "score": 8}
        if mode == "KYB"
        else {
            "european_residency": True,
            "ppe": False,
            "ppp": False,
            "source_income": "salary",
            "net_income": "30k-50k",
            "experience": "beginner",
            "submittedAt": 1699000000,
            "score": 12,
        }
    )
    steps = (
        ["info", "kbis", "status", "domiciliation", "rbe"]
        if mode == "KYB"
        else ["info", "selfie", "identity", "residency"]
    )
    return {
        "uuid": f"identity-{mode.lower()}",
        "state": "VALIDATED",
        "mode": mode,
        "form": form,
        "data": {
            "steps": {step: {"status": "VALIDATED", "submittedAt": 1699000000} for step in steps},
            "notifications": True,
            "verificationUrl": None,
            "hosted": False,
        },
        "validatedAt": 1699003600,
        "expiresAt": 1730539600,
        "renewalNotifiedAt": None,
    }


def customer_account() -> dict[str, Any]:
    return {
        "email": "jean@valjean.fr",
        "firstname": "Jean",
        "lastname": "Valjean",
        "fin": None,
        "birthdate": 315532800,
        "phoneNumber": 612345678,
        "phoneZone": "+33",
        "address": {"uuid": "address-1", "state": "VALIDATED", "address": "1 rue de Paris, 75001 Paris"},
        "referralCode": "JEAN42",
    }


def setup() -> dict[str, Any]:
    return {
        "theme": "light",
        "currency": "EUR",
        "locale": "FR",
        "choosenOrganization": "CUSTOMER",
        "needActivation": False,
        "notify": True,
        "onboarding": True,
    }


CUSTOMER: dict[str, Any] = {
    "uuid": "CUSTOMER_UUID",
    "state": "ENABLED",
    "isAvailable": True,
    "createdAt": 1699000000,
    "login": "jean@valjean.fr",
    "canLogin": True,
    "account": customer_account(),
    "client": {"roles": ["ROLE_USER"], "hasTfa": False, "hasPhishing": False, "isValid": True},
    "action": {"setup": setup()},
    "identity": identity("KYC"),
    "business": [],
    "collaborations": {
        "collaborator": [
            {
                "uuid": "collaboration-1",
                "state": "ENABLED",
                "roles": ["ROLE_USER"],
                "organization": "ACME",
                "organizationUuid": "YOUR_SCOPE_UUID",
                "manager": "MANAGER_UUID",
            }
        ],
        "manager": [],
    },
    "alert": [],
}
ACCOUNT: dict[str, Any] = {
    "uuid": "CUSTOMER_UUID",
    "identity": identity("KYC"),
    "business": [],
    "account": {**customer_account(), "address": {"uuid": "address-1", "address": "1 rue de Paris, 75001 Paris"}},
    "notifications": {"login": True, "newsletter": False},
    "setup": setup(),
}
BANK_ACCOUNT: dict[str, Any] = {
    "uuid": "bank-1",
    "message": "BTGN-4242",
    "iban": None,
    "bank": None,
    "bic": None,
    "balance": 150.0,
    "history": history(150.0),
    "pending": {"in": 0, "out": 0},
}
OPERATIONS: list[dict[str, Any]] = [
    {"txId": "op-1", "amount": 150.0, "direction": "DEPOSIT", "date": 1701000000, "info": None},
    {"txId": "op-2", "amount": 25.0, "direction": "PURCHASE", "date": 1701003600, "info": "ETH"},
]


def lookup(key: str) -> dict[str, Any] | None:
    """An asset by iso (any case) or uuid"""
    key = key.lower()
    for iso, item in ASSETS.items():
        if key in (iso, item["uuid"]):
            return item
    return None


def asset_ref(item: dict[str, Any]) -> dict[str, Any]:
    return {"uuid": item["uuid"], "iso": item["iso"], "label": item["label"]}


def wallet(uuid: str, item: dict[str, Any], address: str, balance: str, tag: str | None = None) -> dict[str, Any]:
    return {
        "uuid": uuid,
        "state": "CREATED",
        "type": "USER",
        "address": address,
        "addressLegacy": None,
        "tag": tag,
        "balance": balance,
        "asset": asset_ref(item),
    }


WALLETS: dict[str, dict[str, Any]] = {
    "eth": wallet("wallet-eth", ASSETS["eth"], "0xabc0000000000000000000000000000000000001", "0.5"),
    "btc": wallet("wallet-btc", ASSETS["btc"], "bc1qxy2kgdygjrsqtzq2n0yrf2493p83kkfjhx0wlh", "0.01"),
}
PORTFOLIO: dict[str, Any] = {"uuid": "custody-1", "type": "USER", "history": history(1628.0)}


def order(
    uuid: str,
    side: str,
    state: str,
    amount: str,
    reference: str | None,
    received: float | None,
    price: float | None,
    fee: float | None,
    completedAt: int | None,
    item: dict[str, Any],
) -> dict[str, Any]:
    return {
        "uuid": uuid,
        "state": state,
        "side": side,
        "amount": amount,
        "reference": reference,
        "received": received,
        "executedPrice": price,
        "fee": fee,
        "completedAt": completedAt,
        "createdAt": 1701000000,
        "user": {"uuid": "CUSTOMER_UUID", "login": "jean@valjean.fr"},
        "organization": {"uuid": "YOUR_SCOPE_UUID", "name": "ACME"},
        "asset": asset_ref(item),
    }


ORDERS: dict[str, dict[str, Any]] = {
    "ORDER_UUID": order(
        "ORDER_UUID", "BUY", "DONE", "25.00", "order-42", 0.0123, 2031.5, 0.25, 1701003600, ASSETS["eth"]
    ),
    "order-2": order("order-2", "SELL", "DONE", "0.01", None, 20.06, 2031.5, 0.25, 1701007200, ASSETS["eth"]),
}

OWNER: dict[str, Any] = {
    "uuid": "CUSTOMER_UUID",
    "state": "ENABLED",
    "login": "jean@valjean.fr",
    "account": {"firstname": "Jean", "lastname": "Valjean", "fin": None},
}
ORGANIZATION: dict[str, Any] = {"uuid": "YOUR_SCOPE_UUID", "state": "ENABLED", "name": "ACME", "hub": None}


def transaction(
    uuid: str,
    state: str,
    source: str,
    direction: str,
    iso: str,
    amount: float,
    eurValue: float | None,
    reference: str | None,
    credited: bool,
) -> dict[str, Any]:
    return {
        "uuid": uuid,
        "state": state,
        "source": source,
        "direction": direction,
        "asset": iso,
        "amount": amount,
        "eurValue": eurValue,
        "reference": reference,
        "credited": credited,
        "silent": False,
        "data": {},
        "createdAt": 1701000000,
        "updatedAt": 1701003600,
        "owner": OWNER,
        "assignee": None,
        "organization": ORGANIZATION,
        "alert": None,
    }


TRANSACTIONS: dict[str, dict[str, Any]] = {
    "transaction-1": transaction("transaction-1", "PENDING", "BANK", "OUT", "EUR", 50.0, None, None, False),
    "transaction-2": transaction(
        "transaction-2", "PENDING", "CUSTODY", "OUT", "ETH", 0.5, 1015.75, "withdraw-42", False
    ),
    "transaction-3": transaction(
        "transaction-3", "COMPLETED", "BANK", "IN", "EUR", 150.0, None, "BANK-TRANSFER-REF-42", True
    ),
}


def core(
    uuid: str,
    name: str,
    label: str,
    core_type: str,
    item: dict[str, Any] | None,
    fields: list[tuple[str, str, str, object]],
    state: str = "ENABLED",
) -> dict[str, Any]:
    config = [
        {
            "name": field,
            "label": {"fr": fr, "en": en},
            "data": {"type": "bool" if isinstance(value, bool) else "string", "value": value},
        }
        for field, fr, en, value in fields
    ]
    return {
        "uuid": uuid,
        "state": state,
        "name": name,
        "label": label,
        "type": core_type,
        "asset": None if item is None else asset_ref(item),
        "config": config,
    }


def staking_fields(connector: str, apr: str, min_deposit: str) -> list[tuple[str, str, str, object]]:
    return [
        ("connector", "Connecteur", "Connector", connector),
        ("apr", "Taux annuel", "Annual rate", apr),
        ("min_deposit", "Dépôt minimum", "Minimum deposit", min_deposit),
        ("deposit_locked_period", "Blocage du dépôt", "Deposit lock-up", "D@3"),
        ("rewards_locked_period", "Blocage des revenus", "Rewards lock-up", "D@7"),
        ("unstake_locked_period", "Blocage de sortie", "Unstake lock-up", "D@21"),
        ("can_choose_withdrawal", "Retrait partiel", "Partial withdrawal", True),
        ("can_choose_rewards", "Revenus partiels", "Partial rewards", True),
        ("min_rewards_eur", "Revenus minimum (EUR)", "Minimum rewards (EUR)", "5"),
    ]


CORES: dict[str, dict[str, Any]] = {
    "CORE_UUID": core(
        "CORE_UUID", "figment_sol", "Figment SOL", "STAKING", ASSETS["sol"], staking_fields("figment", "6.5", "1")
    ),
    "core-bitgen-eth": core(
        "core-bitgen-eth", "bitgen_eth", "BITGEN ETH", "STAKING", ASSETS["eth"], staking_fields("bitgen", "3.2", "0.1")
    ),
    "core-bank": core("core-bank", "manual_bank", "Manual bank", "RAMP", None, [("iban", "IBAN", "IBAN", "FR76…")]),
    "core-exchange": core(
        "core-exchange", "exchange", "Exchange", "TRADING", None, [("api_key", "Clé API", "API key", "")]
    ),
    "core-custodian": core(
        "core-custodian", "custodian", "Custodian", "CUSTODY", None, [("vault", "Coffre", "Vault", "main")]
    ),
}
MOVEMENT: dict[str, Any] = {
    "uuid": "MOVEMENT_UUID",
    "state": "COMPLETED",
    "kind": "STAKE",
    "provider": "figment_sol",
    "amount": "2",
    "createdAt": 1701000000,
    "updatedAt": 1701003600,
    "staking": {
        "uuid": "POSITION_UUID",
        "state": "ENABLED",
        "amount": "2",
        "error": None,
        "data": {"rewards": "0.0123", "lastRewardAt": 1701090000},
        "createdAt": 1701000000,
        "updatedAt": 1701090000,
        "core": {"uuid": "CORE_UUID", "name": "figment_sol", "label": "Figment SOL"},
    },
    "owner": OWNER,
    "asset": asset_ref(ASSETS["sol"]),
    "organization": {"uuid": "YOUR_SCOPE_UUID", "state": "ENABLED", "name": "ACME"},
}
STAKING_OPERATIONS: list[dict[str, Any]] = [
    {
        "txId": "stk-op-1",
        "movement": "MOVEMENT_UUID",
        "asset": "SOL",
        "kind": "STAKE",
        "amount": "2",
        "price": 128.4,
        "value": 256.8,
        "event": "validated",
        "provider": "figment_sol",
        "date": 1701003600,
    },
    {
        "txId": "stk-op-2",
        "movement": None,
        "asset": "SOL",
        "kind": "REWARD",
        "amount": "0.0123",
        "price": 130.0,
        "value": 1.6,
        "event": "reward",
        "provider": "figment_sol",
        "date": 1701090000,
    },
]
STAKING_PORTFOLIO: dict[str, Any] = {
    "uuid": "staking-1",
    "balances": {"capital": 256.8, "revenues": 1.6},
    "histories": {"capital": history(256.8), "revenues": history(1.6)},
}


def webhook_type(uuid: str, name: str, fr: str, en: str, state: str = "ENABLED") -> dict[str, Any]:
    return {
        "uuid": uuid,
        "state": state,
        "name": name,
        "label": json.dumps({"fr": fr, "en": en}, ensure_ascii=False),
        "data": "{}",
    }


WEBHOOK_TYPES: dict[str, dict[str, Any]] = {
    "WEBHOOK_UUID": webhook_type("WEBHOOK_UUID", "custody.sent", "Crypto envoyée", "Crypto sent"),
    "webhook-2": webhook_type("webhook-2", "bank.credited", "Compte crédité", "Account credited"),
    "webhook-3": webhook_type("webhook-3", "trading.buy", "Achat", "Purchase"),
    "webhook-4": webhook_type("webhook-4", "user.created", "Client créé", "Customer created"),
    "webhook-5": webhook_type(
        "webhook-5", "organization.created", "Organisation créée", "Organization created", "ARCHIVED"
    ),
}
SUBSCRIPTIONS: dict[str, Any] = {
    "secret": "whsec_9f2c6b1e4d8a7c3b5e0f1a2d4c6b8e9a",
    "endpoint": "https://example.com/bitgen",
    "items": [
        {
            "uuid": "SUBSCRIBER_UUID",
            "state": "ENABLED",
            "updatedAt": 1701000000,
            "webhook": WEBHOOK_TYPES["WEBHOOK_UUID"],
        },
        {"uuid": "subscriber-2", "state": "ARCHIVED", "updatedAt": 1700000000, "webhook": WEBHOOK_TYPES["webhook-5"]},
    ],
}
DELIVERIES: list[dict[str, Any]] = [
    {
        "date": 1701000000,
        "webhook": "custody.sent",
        "url": "https://example.com/bitgen",
        "status": "SENT",
        "http_code": 204,
        "duration_ms": 87,
        "attempts": 1,
        "payload": {
            "delivery_id": "delivery-1",
            "timestamp": 1701000000,
            "event": "custody.sent",
            "data": {"wallet": "wallet-eth", "amount": "0.5"},
        },
        "error": None,
    },
    {
        "date": 1701003600,
        "webhook": "custody.sent",
        "url": "https://example.com/bitgen",
        "status": "FAILED",
        "http_code": None,
        "duration_ms": None,
        "attempts": 1,
        "payload": {"delivery_id": "delivery-2", "timestamp": 1701003600, "event": "custody.sent", "data": {}},
        "error": "connection refused",
    },
]
APIKEYS: dict[str, dict[str, Any]] = {
    "APIKEY_UUID": {
        "uuid": "APIKEY_UUID",
        "state": "ENABLED",
        "name": "backend",
        "permissions": [
            "customer.read",
            "customer.write",
            "bank.read",
            "custody.read",
            "custody.write",
            "trading.read",
            "trading.write",
        ],
        "expireAt": 1735689600,
        "createdAt": 1699000000,
        "organization": {
            "uuid": "YOUR_SCOPE_UUID",
            "state": "ENABLED",
            "name": "ACME",
            "hub": None,
            "owner": {"uuid": "owner-1", "login": "ceo@acme.fr", "firstname": "Anne", "lastname": "Martin"},
        },
    },
}
APIKEY_LOGS: list[dict[str, Any]] = [
    {
        "date": 1701000000,
        "path": "GET /custody/CUSTOMER_UUID",
        "payload": '{"user":"CUSTOMER_UUID"}',
        "status": 200,
        "error": None,
    },
    {
        "date": 1701000060,
        "path": "PUT /bank/CUSTOMER_UUID",
        "payload": '{"amount":"50.00","iban":"****"}',
        "status": 416,
        "error": '{"error":true,"message":"requested_amount_error","code":416}',
    },
]


class DocsHandler(QuietHandler):
    def _route(self) -> None:  # noqa: PLR0912, PLR0915 - one branch per route of the documentation server, it grows with the resources
        parts = urlsplit(self.path)
        segments = [unquote(segment) for segment in parts.path.split("/") if segment]
        length = int(self.headers.get("Content-Length") or 0)
        if length:
            self.rfile.read(length)
        method = self.command

        if method == "GET" and segments == []:
            self._answer(200, {"ping": "HELO", "name": "bitgen-api", "version": "4.0.0"})
        elif method == "POST" and segments == ["customer"]:
            self._answer(201, {"uuid": "CUSTOMER_UUID"})
        elif method == "GET" and segments == ["customer"]:
            self._answer(200, {"count": 1, "items": [CUSTOMER]})
        elif len(segments) == 2 and segments[0] == "account":
            self._answer(200, []) if method == "PUT" else self._answer(200, ACCOUNT)
        elif method == "POST" and segments == ["bank"]:
            self._answer(201, {"uuid": "deposit-1"})
        elif method == "GET" and len(segments) == 2 and segments[0] == "bank":
            self._answer(200, BANK_ACCOUNT)
        elif method == "PUT" and len(segments) == 2 and segments[0] == "bank":
            self._answer(200, {"transaction": "transaction-1"})
        elif method == "GET" and len(segments) == 3 and segments[0] == "bank" and segments[2] == "operations":
            self._answer(200, {"count": len(OPERATIONS), "items": OPERATIONS})
        elif method == "GET" and len(segments) == 2 and segments[0] == "custody":
            self._answer(200, list(WALLETS.values()))
        elif method == "PUT" and len(segments) == 2 and segments[0] == "custody":
            self._answer(200, {"transaction": "transaction-2"})
        elif method == "GET" and len(segments) == 3 and segments[0] == "custody" and segments[2] == "portfolio":
            self._answer(200, PORTFOLIO)
        elif method == "GET" and len(segments) == 3 and segments[0] == "custody":
            found = lookup(segments[2])
            if found is None:
                self._error(404, "unknown_asset")
            else:
                iso = str(found["iso"]).lower()
                known = WALLETS.get(iso) or wallet(f"wallet-{iso}", found, f"address-{iso}", "0")
                self._answer(200, {**known, "history": history(1015.75)})
        elif method == "POST" and segments == ["trading"]:
            self._answer(201, {"tunnel": "ORDER_UUID", "state": "REGISTERED"})
        elif method == "GET" and segments == ["trading", "orders"]:
            self._answer(200, {"count": len(ORDERS), "items": list(ORDERS.values())})
        elif method == "GET" and len(segments) == 2 and segments[0] == "trading":
            found_order = ORDERS.get(segments[1])
            self._error(404, "unknown_order") if found_order is None else self._answer(200, found_order)
        elif method == "GET" and segments == ["transaction"]:
            self._answer(200, {"count": len(TRANSACTIONS), "items": list(TRANSACTIONS.values())})
        elif method == "GET" and len(segments) == 2 and segments[0] == "transaction":
            key = segments[1]
            found_tx = TRANSACTIONS.get(key)  # by uuid, or by reference
            for candidate in TRANSACTIONS.values():
                if candidate["reference"] == key:
                    found_tx = candidate
            self._error(404, "unknown_transaction") if found_tx is None else self._answer(200, found_tx)
        elif method == "GET" and segments == ["applications", "core"]:
            query = {name: value[-1] for name, value in parse_qs(parts.query).items()}
            wanted = lookup(query["asset"]) if "asset" in query else None
            if "asset" in query and wanted is None:
                self._error(404, "unknown_asset")
            else:
                items = [
                    item
                    for item in CORES.values()
                    if ("type" not in query or item["type"] == query["type"])
                    and ("state" not in query or item["state"] == query["state"])
                    and (wanted is None or (item["asset"] or {}).get("uuid") == wanted["uuid"])
                ]
                self._answer(200, {"count": len(items), "items": items})
        elif method == "GET" and len(segments) == 3 and segments[:2] == ["applications", "core"]:
            found_core = CORES.get(segments[2])
            self._error(404, "unknown_core") if found_core is None else self._answer(200, found_core)
        elif method == "POST" and segments == ["staking"]:
            self._answer(201, {"uuid": "MOVEMENT_UUID"})
        elif method == "GET" and segments == ["staking"]:
            self._answer(200, {"count": 1, "items": [MOVEMENT]})
        elif method == "GET" and segments == ["staking", "movements"]:
            self._answer(200, {"count": 0, "items": []})
        elif method == "GET" and len(segments) == 2 and segments[0] == "staking":
            self._answer(200, MOVEMENT) if segments[1] == "MOVEMENT_UUID" else self._error(
                404, "unknown_staking_movement"
            )
        elif (
            method == "PUT"
            and len(segments) == 3
            and segments[0] == "staking"
            and segments[2] in ("rewards", "unstake")
        ):
            self._answer(200, [])
        elif method == "GET" and len(segments) == 3 and segments[0] == "staking" and segments[2] == "operations":
            self._answer(200, {"count": len(STAKING_OPERATIONS), "items": STAKING_OPERATIONS})
        elif method == "GET" and len(segments) == 3 and segments[0] == "staking" and segments[2] == "portfolio":
            self._answer(200, STAKING_PORTFOLIO)
        elif (
            method == "POST"
            and len(segments) == 4
            and segments[:2] == ["webhook", "security"]
            and segments[3] == "activate"
        ):
            self._answer(201, [])
        elif method == "PATCH" and segments[:2] == ["webhook", "security"] and len(segments) in (3, 4):
            self._answer(200, [])  # the endpoint update, or `/regenerate`
        elif method == "GET" and segments == ["webhook"]:
            self._answer(200, {"count": len(WEBHOOK_TYPES), "items": list(WEBHOOK_TYPES.values())})
        elif method == "GET" and len(segments) == 2 and segments[0] == "webhook":
            found_type = WEBHOOK_TYPES.get(segments[1])
            self._error(404, "unknown_webhook") if found_type is None else self._answer(200, found_type)
        elif method == "POST" and segments == ["webhooks"]:
            self._answer(201, {"uuid": "SUBSCRIBER_UUID"})
        elif method == "GET" and len(segments) == 2 and segments[0] == "webhooks":
            self._answer(200, SUBSCRIPTIONS)
        elif method == "DELETE" and len(segments) == 2 and segments[0] == "webhooks":
            self._answer(200, [])
        elif method == "POST" and len(segments) == 2 and segments[0] == "webhooks":
            self._answer(201, [])
        elif method == "GET" and len(segments) == 3 and segments[0] == "webhooks" and segments[2] == "logs":
            self._answer(200, {"count": len(DELIVERIES), "items": DELIVERIES})
        elif method == "GET" and len(segments) == 3 and segments[0] == "organization" and segments[2] == "apikeys":
            self._answer(200, {"count": len(APIKEYS), "items": list(APIKEYS.values())})
        elif method == "GET" and len(segments) == 4 and segments[0] == "organization" and segments[2] == "apikeys":
            found_key = APIKEYS.get(segments[3])
            self._error(404, "unknown_apikey") if found_key is None else self._answer(200, found_key)
        elif (
            method == "GET"
            and len(segments) == 5
            and segments[0] == "organization"
            and segments[2] == "apikeys"
            and segments[4] == "logs"
        ):
            self._answer(200, {"count": len(APIKEY_LOGS), "items": APIKEY_LOGS})
        elif method == "GET" and segments == ["asset"]:
            self._answer(200, {"count": len(ASSETS), "items": list(ASSETS.values())})
        elif method == "GET" and len(segments) == 2 and segments[0] == "asset":
            found = lookup(segments[1])
            self._error(404, "unknown_asset") if found is None else self._answer(200, found)
        elif method == "GET" and segments == ["ticker"]:
            self._answer(
                200,
                {"count": len(ASSETS), "items": [{"iso": a["iso"], "ticker": a["ticker"]} for a in ASSETS.values()]},
            )
        elif method == "GET" and len(segments) == 2 and segments[0] == "ticker":
            found = lookup(segments[1])
            if found is None:
                self._error(404, "unknown_asset")
            else:
                self._answer(200, {"iso": found["iso"], "ticker": found["ticker"], "history": found["history"]})
        else:
            body = b"Internal Server Error"
            self.send_response(500)
            self.send_header("Content-Type", "text/plain")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    def _answer(self, status: int, body: object) -> None:
        encoded = json.dumps(body).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def _error(self, status: int, code: str) -> None:
        self._answer(status, {"error": True, "message": code, "code": status})

    do_GET = _route
    do_POST = _route
    do_PUT = _route
    do_PATCH = _route
    do_DELETE = _route
