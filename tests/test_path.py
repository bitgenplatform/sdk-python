from __future__ import annotations

import pytest

from bitgen._support import path


def test_segments_are_encoded() -> None:
    assert path.segment("eth", "asset") == "eth"
    assert path.segment("ed1a19bb-1", "user") == "ed1a19bb-1"
    assert path.segment("jean@valjean.fr", "user") == "jean%40valjean.fr"
    assert path.segment("a/b?c#d e", "reference") == "a%2Fb%3Fc%23d%20e"
    assert path.segment("é~", "x") == "%C3%A9~"


def test_empty_and_dot_segments_are_refused() -> None:
    for value in ["", "  "]:
        with pytest.raises(ValueError, match=r"^asset must be a non-empty string$"):
            path.segment(value, "asset")
    for value in [".", ".."]:
        with pytest.raises(ValueError, match=r'^user must not be "\." or "\.\."$'):
            path.segment(value, "user")
    with pytest.raises(TypeError, match=r"^user must be a string$"):
        path.segment(42, "user")
