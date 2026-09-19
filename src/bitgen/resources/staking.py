"""Staking positions of the customers: providers, movements, rewards, portfolio (`client.staking`)."""

from __future__ import annotations

from decimal import Decimal

from bitgen._http.client import HttpClient
from bitgen._support import amount as amount_
from bitgen._support import asset_id, path, reference, user_id, values
from bitgen.models import _cast
from bitgen.models.asset import Asset, AssetRef
from bitgen.models.core import Core, CoreType
from bitgen.models.customer import Created, UserRef
from bitgen.models.staking import (
    StakingMovement,
    StakingMovementKind,
    StakingOperation,
    StakingPortfolio,
    StakingPosition,
)
from bitgen.page import Page
from bitgen.resources.core import CoreResource


class StakingResource:
    """Providers, positions, movements, rewards, operations and EUR portfolio. Every method raises a `BitgenError`
    when the API answers an error or no HTTP answer is received; an invalid argument raises a `ValueError` (or a
    `TypeError`) before any request."""

    def __init__(self, http: HttpClient, core: CoreResource) -> None:
        self._http = http
        self._core = core

    def providers(self, asset: str | Asset | AssetRef | None = None) -> Page[Core]:
        """The staking providers: the `STAKING` connectors, optionally for one asset (uuid, ISO code or model) — their
        `uuid` or `name` is the `provider` of `stake`"""
        return self._core.list(type=CoreType.STAKING, asset=asset)

    def stake(
        self, user: UserRef, asset: str | Asset | AssetRef, amount: str | int | float | Decimal, provider: str
    ) -> Created:
        """Open a staking position — the amount is moved from the customer's custody wallet to the deposit address of
        the provider. `asset` by uuid or ISO code (`Asset.SOL`) or by model; `amount` the crypto quantity to stake, as a
        string, at least the `min_deposit` of the provider; `provider` the `uuid` or the `name` of a `STAKING` connector
        of the organization (`providers()`). Returns the uuid of the **movement**."""
        body = {
            "user": user_id.resolve(user),
            "asset": asset_id.resolve(asset),
            "amount": amount_.normalize(amount),
            "provider": values.string(provider, "provider"),
        }
        return Created.from_dict(_cast.answer(self._http.post("/staking", body)))

    def list(
        self,
        *,
        user: UserRef | None = None,
        direction: str | None = None,
        offset: int | None = None,
        limit: int | None = None,
    ) -> Page[StakingMovement]:
        """The movements of the organization, in every state — `user` keeps only the movements of this customer
        (unknown → `404 unknown_user`), `direction` only this kind of movement: `STAKE`, `UNSTAKE`, `WITHDRAW` or
        `REWARD` (a `StakingMovementKind` constant)"""
        return self._movements("/staking", user, direction, offset, limit)

    def movements(
        self,
        *,
        user: UserRef | None = None,
        direction: str | None = None,
        offset: int | None = None,
        limit: int | None = None,
    ) -> Page[StakingMovement]:
        """The movements still in progress: `REQUESTED`, `PENDING` and `FAILED` only — same arguments as `list`"""
        return self._movements("/staking/movements", user, direction, offset, limit)

    def get(self, movement: str | StakingMovement) -> StakingMovement:
        """One movement, by uuid (the one returned by `stake`) or by model, with its position"""
        segment = path.segment(reference.resolve(movement, StakingMovement, "movement"), "movement")
        return StakingMovement.from_dict(_cast.answer(self._http.get(f"/staking/{segment}")))

    def rewards(self, position: str | StakingPosition, amount: str | int | float | Decimal | None = None) -> None:
        """Claim the rewards of a position (`movement.staking`, or its uuid) — `amount` absent = all of them. Deducted
        immediately, the transfer is executed by compliance."""
        self._http.put(f"/staking/{_position(position)}/rewards", _amount_body(amount))

    def unstake(self, position: str | StakingPosition, amount: str | int | float | Decimal | None = None) -> None:
        """Leave a position (`movement.staking`, or its uuid) — `amount` absent = the whole position (a full exit
        ignores the minimums). Deducted immediately, the transfer is executed by compliance."""
        self._http.put(f"/staking/{_position(position)}/unstake", _amount_body(amount))

    def operations(
        self, user: UserRef, *, offset: int | None = None, limit: int | None = None
    ) -> Page[StakingOperation]:
        """The staking operations of a customer"""
        query = {"offset": values.optional_int(offset, "offset"), "limit": values.optional_int(limit, "limit")}
        return Page.from_dict(
            _cast.answer(self._http.get(f"/staking/{_user(user)}/operations", query)), StakingOperation.from_dict
        )

    def portfolio(self, user: UserRef) -> StakingPortfolio:
        """The EUR balances and curves (capital, revenues) of a customer's staking"""
        return StakingPortfolio.from_dict(_cast.answer(self._http.get(f"/staking/{_user(user)}/portfolio")))

    def _movements(
        self, target: str, user: UserRef | None, direction: str | None, offset: int | None, limit: int | None
    ) -> Page[StakingMovement]:
        """A `direction` outside `StakingMovementKind.VALUES` is refused before any request"""
        query = {
            "user": None if user is None else user_id.resolve(user),
            "direction": values.optional_choice(direction, StakingMovementKind.VALUES, "direction"),
            "offset": values.optional_int(offset, "offset"),
            "limit": values.optional_int(limit, "limit"),
        }
        return Page.from_dict(_cast.answer(self._http.get(target, query)), StakingMovement.from_dict)


def _amount_body(amount: str | int | float | Decimal | None) -> dict[str, str]:
    """`{ amount }` when given, `{}` otherwise — the API reads an absent amount as "everything\""""
    return {} if amount is None else {"amount": amount_.normalize(amount)}


def _position(position: str | StakingPosition) -> str:
    return path.segment(reference.resolve(position, StakingPosition, "position"), "position")


def _user(user: UserRef) -> str:
    return path.segment(user_id.resolve(user), "user")
