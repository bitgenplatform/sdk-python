"""The resources of the API, hung off `BitgenClient` (`client.customer`, `client.bank`, `client.custody`,
`client.trading`, `client.transaction`, `client.staking`, `client.core`, `client.webhooks`, `client.apikeys`,
`client.asset`). Importable for type annotations."""

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

__all__ = [
    "ApikeysResource",
    "AssetResource",
    "BankResource",
    "CoreResource",
    "CustodyResource",
    "CustomerResource",
    "StakingResource",
    "TradingResource",
    "TransactionResource",
    "WebhooksResource",
]
