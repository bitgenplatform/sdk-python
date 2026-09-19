from __future__ import annotations

import re

import bitgen
from bitgen import VERSION


def test_the_version_is_semver_and_the_only_one() -> None:
    assert re.fullmatch(r"\d+\.\d+\.\d+", VERSION)
    assert bitgen.__version__ == VERSION
