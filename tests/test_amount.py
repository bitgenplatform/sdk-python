from __future__ import annotations

import enum
import math
from decimal import Decimal

import pytest

from bitgen._support import amount


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        pytest.param("0.000000000000000001", "0.000000000000000001", id="18 decimals, intact"),
        pytest.param("25.00", "25.00", id="string as is"),
        pytest.param(" 1.5 ", "1.5", id="string trimmed"),
        pytest.param("1e-8", "1e-8", id="exponent string is sent as is (the API decides)"),
        pytest.param(25, "25", id="int"),
        pytest.param(0, "0", id="zero int"),
        pytest.param(0.5, "0.5", id="float"),
        pytest.param(123456.789, "123456.789", id="float with many digits"),
        pytest.param(25.0, "25", id="whole float"),
        pytest.param(0.0, "0", id="zero float"),
        pytest.param(-0.0, "0", id="negative zero float"),
        pytest.param(0.0001, "0.0001", id="smallest decimal float"),
        pytest.param(1234567890123456.0, "1234567890123456", id="large float, still decimal"),
        pytest.param(0.1 + 0.2, "0.30000000000000004", id="float, never rounded"),
        pytest.param(Decimal("0.000000000000000001"), "0.000000000000000001", id="Decimal, intact"),
        pytest.param(Decimal("25.00"), "25.00", id="Decimal as written"),
        pytest.param(Decimal("1E-8"), "0.00000001", id="Decimal, plain notation"),
        pytest.param(Decimal("1E+21"), "1000000000000000000000", id="large Decimal, plain notation"),
        pytest.param(Decimal("0"), "0", id="zero Decimal"),
        pytest.param(Decimal("-0"), "0", id="negative zero Decimal"),
    ],
)
def test_accepted_amounts_reach_the_api_as_strings(value: str | int | float | Decimal, expected: str) -> None:
    assert amount.normalize(value) == expected


@pytest.mark.parametrize(
    ("value", "message"),
    [
        pytest.param("", r"^amount must be a non-empty string", id="empty string"),
        pytest.param("   ", r"^amount must be a non-empty string", id="blank string"),
        pytest.param(-1, r"^amount must be a non-empty string", id="negative int"),
        pytest.param(-0.5, r"^amount must be a non-empty string", id="negative float"),
        pytest.param(math.inf, r"^amount must be a non-empty string", id="infinite"),
        pytest.param(math.nan, r"^amount must be a non-empty string", id="nan"),
        pytest.param(Decimal("-1"), r"^amount must be a non-empty string", id="negative Decimal"),
        pytest.param(Decimal("NaN"), r"^amount must be a non-empty string", id="nan Decimal"),
        pytest.param(Decimal("Infinity"), r"^amount must be a non-empty string", id="infinite Decimal"),
        pytest.param(1e-8, r"would be sent in exponent notation", id="tiny float, exponent notation"),
        pytest.param(0.00001, r"would be sent in exponent notation", id="below 1e-4, exponent notation"),
        pytest.param(1e16, r"would be sent in exponent notation", id="from 1e16, exponent notation"),
        pytest.param(1e21, r"would be sent in exponent notation", id="huge float, exponent notation"),
    ],
)
def test_refused_amounts_raise_before_any_request(value: str | int | float | Decimal, message: str) -> None:
    with pytest.raises(ValueError, match=message):
        amount.normalize(value)


class Cents(enum.IntEnum):
    TEN = 10


class Precise(float):
    def __repr__(self) -> str:
        return f"Precise({float(self)})"


def test_subclasses_of_int_and_float_write_the_plain_number() -> None:
    assert amount.normalize(Cents.TEN) == "10"
    assert amount.normalize(Precise(0.5)) == "0.5"


@pytest.mark.parametrize("value", [True, False, None, [1], b"1"])
def test_other_types_are_type_errors(value: object) -> None:
    with pytest.raises(TypeError, match=r"^amount must be a non-empty string"):
        amount.normalize(value)
