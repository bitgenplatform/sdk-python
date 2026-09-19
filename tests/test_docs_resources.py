"""Every resource page of the documentation (readme/resource/<r>.md) against the code, by reflection: one `## <method>`
section per public method of the resource, in the order of the code, listed in the Methods table; a signature block
identical to the real signature; every PascalCase name in backticks an export of the SDK. What the PHP SDK checked by
scripts is a test here: a resource added later is checked without touching this file."""

from __future__ import annotations

import builtins
import inspect
import re
from pathlib import Path
from typing import Any

import pytest

import bitgen
import bitgen.models
import bitgen.resources
from bitgen import BitgenClient

ROOT = Path(__file__).resolve().parent.parent
PAGES = sorted((ROOT / "readme" / "resource").glob("*.md"))

_BLOCK = re.compile(r"^```(\w*)\n(.*?)^```$", re.MULTILINE | re.DOTALL)
_SIGNATURE = re.compile(r"^client\.(\w+)\.(\w+)\((.*)\) -> (.+)$")
# a PascalCase name: starts with a capital, has a lowercase letter (`AssetRef` — not the constants `ETH`, `VALUES`)
_PASCAL = re.compile(r"`([A-Z][A-Za-z0-9]*[a-z][A-Za-z0-9]*)`")
_TYPING_NAMES = {"Any", "None", "Page", "Decimal"}
# sample values written in backticks that are not names of the SDK, listed explicitly
_SAMPLES = {"asset.md": {"Bitcoin"}}


def resource_of(page: Path) -> tuple[str, Any]:
    """The attribute of the client the page documents (`asset.md` → `client.asset`)"""
    name = page.stem
    client = BitgenClient(scope="s", apiKey="k")
    assert hasattr(client, name), f"{page.name}: BitgenClient has no attribute {name}"
    return name, getattr(client, name)


def public_methods(resource: Any) -> list[str]:
    """In the order of the source"""
    members = [
        name for name, member in inspect.getmembers(type(resource), inspect.isfunction) if not name.startswith("_")
    ]
    return sorted(members, key=lambda name: inspect.getsourcelines(getattr(type(resource), name))[1])


def sections(text: str) -> list[str]:
    return re.findall(r"^## (.+)$", text, re.MULTILINE)


def display(annotation: Any) -> str:
    """The type as the documentation writes it: the annotation as written in the source (aliases such as `UserRef`
    kept), with `models.Asset` for the model — in a resource, `Asset` is always the model, never the constants"""
    text = annotation if isinstance(annotation, str) else inspect.formatannotation(annotation)
    return re.sub(r"\bAsset\b", "models.Asset", text)


def documented_signature(resource_name: str, method: str, resource: Any) -> str:
    function = getattr(type(resource), method)
    signature = inspect.signature(function)
    parameters = []
    for parameter in list(signature.parameters.values())[1:]:
        text = parameter.name
        if parameter.annotation is not inspect.Parameter.empty:
            text += f": {display(parameter.annotation)}"
        if parameter.default is not inspect.Parameter.empty:
            text += f" = {parameter.default!r}"
        if parameter.kind is inspect.Parameter.KEYWORD_ONLY and "*" not in parameters:
            parameters.append("*")
        parameters.append(text)
    returns = display(signature.return_annotation)
    return f"client.{resource_name}.{method}({', '.join(parameters)}) -> {returns}"


@pytest.mark.parametrize("page", PAGES, ids=lambda page: str(page.name))
def test_sections_and_signatures_match_the_code(page: Path) -> None:
    text = page.read_text(encoding="utf-8")
    resource_name, resource = resource_of(page)
    methods = public_methods(resource)
    assert methods, resource_name

    headings = sections(text)
    assert headings[0] == "Methods", page.name
    # section titles start with a capital letter (`## Get`, `## UpdateEndpoint`), as in the PHP and Node.js SDKs
    titles = [method[0].upper() + method[1:] for method in methods]
    assert headings[1 : 1 + len(methods)] == titles, f"{page.name}: one section per method, in the order of the code"
    assert headings[1 + len(methods) :] == ["Errors", "Related"], page.name

    table = text.split("## Methods", 1)[1].split("\n## ", 1)[0]
    for method in methods:
        assert re.search(rf"^\| `{method}\(", table, re.MULTILINE), (
            f"{page.name}: {method} missing from the Methods table"
        )

    blocks = [body.strip() for lang, body in _BLOCK.findall(text) if lang == ""]
    signatures = {}
    for block in blocks:
        match = _SIGNATURE.match(block)
        assert match, f"{page.name}: untagged block that is not a signature: {block!r}"
        signatures[match.group(2)] = block
    assert list(signatures) == methods, f"{page.name}: one signature block per method, in order"
    for method in methods:
        expected = documented_signature(resource_name, method, resource)
        assert signatures[method] == expected, (
            f"{page.name}: {method}\n  documented: {signatures[method]}\n  code:       {expected}"
        )


def exported_names() -> set[str]:
    names = set(bitgen.__all__) | set(bitgen.models.__all__) | set(bitgen.resources.__all__)
    return names | _TYPING_NAMES | set(dir(builtins))


@pytest.mark.parametrize("page", [*PAGES, ROOT / "readme" / "concepts.md"], ids=lambda page: str(page.name))
def test_every_pascal_case_name_in_backticks_is_an_export(page: Path) -> None:
    text = _BLOCK.sub("", page.read_text(encoding="utf-8"))
    known = exported_names() | _SAMPLES.get(page.name, set())
    unknown = sorted({name for name in _PASCAL.findall(text) if name not in known})
    assert unknown == [], f"{page.name}: names in backticks that the SDK does not export: {unknown}"
