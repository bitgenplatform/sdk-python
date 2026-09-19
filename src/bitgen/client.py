"""The entry point of the SDK."""

from __future__ import annotations

import re

from bitgen._http import base_url
from bitgen._http import timeout as timeout_
from bitgen._http.client import HttpClient
from bitgen._http.transport import HttpTransport
from bitgen.constants import Env
from bitgen.resources.apikeys import ApikeysResource
from bitgen.resources.asset import AssetResource
from bitgen.resources.bank import BankResource
from bitgen.resources.core import CoreResource
from bitgen.resources.custody import CustodyResource
from bitgen.resources.customer import CustomerResource
from bitgen.resources.staking import StakingResource
from bitgen.resources.trading import TradingResource
from bitgen.resources.transaction import TransactionResource
from bitgen.resources.webhooks import WebhooksResource
from bitgen.version import VERSION

_PRINTABLE_ASCII = re.compile(r"[\x20-\x7E]+")


class BitgenClient:
    """One instance per API key; the resources hang off it (`client.customer`, `client.bank`, `client.custody`,
    `client.trading`, `client.transaction`, `client.staking`, `client.core`, `client.webhooks`, `client.apikeys`,
    `client.asset`). An invalid configuration raises a `ValueError` (or a `TypeError` on a wrong type) here, before
    any request is sent.

    ```python
    client = BitgenClient(scope="YOUR_SCOPE_UUID", apiKey="YOUR_API_KEY", env=Env.SANDBOX)
    ```
    """

    customer: CustomerResource
    """The customers of the organization: creation, listing, accounts"""
    bank: BankResource
    """The EUR account of each customer"""
    custody: CustodyResource
    """The crypto wallets of each customer, per asset: deposit addresses, balances, on-chain withdrawals"""
    trading: TradingResource
    """Purchases and sales of crypto for a customer, through the exchange of the platform"""
    transaction: TransactionResource
    """The journal of the fiat and crypto movements of the organization, read-only"""
    staking: StakingResource
    """Staking positions of the customers: providers, movements, rewards, portfolio"""
    core: CoreResource
    """The catalogue of the connectors of the platform, read-only"""
    webhooks: WebhooksResource
    """The webhooks of the organization: endpoint and secret, subscriptions, delivery logs, catalogue, `verify`"""
    apikeys: ApikeysResource
    """The API keys of the organization and the journal of their calls, read-only"""
    asset: AssetResource
    """The catalogue of assets, tickers and EUR price histories"""

    def __init__(
        self,
        *,
        scope: str,
        apiKey: str,
        env: str = Env.PRODUCTION,
        host: str | None = None,
        port: int | None = None,
        isSsl: bool = True,
        timeout: int | float = timeout_.DEFAULT,
    ) -> None:
        """
        :param scope: uuid of the organization that owns the key (`BITGEN-Scope` header)
        :param apiKey: the raw key (`Api-key` header)
        :param env: target environment, one of the `Env` constants — `Env.PRODUCTION` by default
        :param host: custom hostname (bare: no scheme, port or path), used instead of `env`
        :param port: port — with `host` (default 80) or `Env.LOCALHOST` (default 3002)
        :param isSsl: `https` (default) or `http`, with `host`
        :param timeout: request timeout in seconds, `30` by default, `0` = none
        """
        _require_header_value(scope, "scope")
        _require_header_value(apiKey, "apiKey")
        self._http = HttpClient(
            HttpTransport(),
            scope,
            apiKey,
            base_url.resolve(env, host, port, isSsl),
            timeout_.resolve(timeout),
            f"bitgen-sdk-python/{VERSION}",
        )
        self.customer = CustomerResource(self._http)
        self.bank = BankResource(self._http)
        self.custody = CustodyResource(self._http)
        self.trading = TradingResource(self._http)
        self.transaction = TransactionResource(self._http)
        core = CoreResource(self._http)  # built first: the staking providers are read from the core catalogue
        self.staking = StakingResource(self._http, core)
        self.core = core
        self.webhooks = WebhooksResource(self._http)
        self.apikeys = ApikeysResource(self._http)
        self.asset = AssetResource(self._http)


def _require_header_value(value: object, name: str) -> None:
    """Non-empty printable ASCII (a header value) — the value itself is never echoed"""
    if not isinstance(value, str):
        raise TypeError(f"{name} must be a non-empty string")
    if value == "":
        raise ValueError(f"{name} must be a non-empty string")
    if not _PRINTABLE_ASCII.fullmatch(value):
        raise ValueError(f"{name} contains invalid characters (printable ASCII expected)")
