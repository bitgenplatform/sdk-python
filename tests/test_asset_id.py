from __future__ import annotations

import pytest

from bitgen import Asset
from bitgen._support import asset_id
from bitgen.models import Asset as AssetModel
from bitgen.models import AssetRef


def test_a_string_is_sent_as_is_and_a_model_by_its_uuid() -> None:
    assert asset_id.resolve(Asset.ETH) == "eth"
    assert asset_id.resolve("ETH") == "ETH"
    assert asset_id.resolve("asset-uuid") == "asset-uuid"
    assert asset_id.resolve(AssetRef("asset-eth", "ETH", "Ethereum")) == "asset-eth"
    assert asset_id.resolve(AssetModel.from_dict({"uuid": "a1", "iso": "ETH"})) == "a1"


def test_a_model_without_uuid_and_other_objects_are_refused() -> None:
    with pytest.raises(ValueError, match=r"^asset must be a uuid or an ISO code, or a model with a non-empty uuid$"):
        asset_id.resolve(AssetRef(" ", "ETH", "Ethereum"))
    for value in [None, 42, {"uuid": "u"}, object(), AssetRef(None, "ETH", "Ethereum")]:  # type: ignore[arg-type]
        with pytest.raises(
            TypeError, match=r"^asset must be a uuid or an ISO code string, or an Asset / AssetRef model$"
        ):
            asset_id.resolve(value)
