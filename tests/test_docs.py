"""Client documentation (README.md, readme/**/*.md): every ```python block runs against the package, every relative link
and anchor resolves, the README title carries the version, and no API route or path appears (it is the SDK's
documentation). What depends on the API contract (error codes) is not checked here: the contract is not in the
repository."""

from __future__ import annotations

import os
import re
import subprocess
import sys
import tomllib
from collections.abc import Iterator
from pathlib import Path

import pytest

from bitgen import VERSION
from tests.server import Server
from tests.server.docs import DocsHandler

ROOT = Path(__file__).resolve().parent.parent
with (ROOT / "pyproject.toml").open("rb") as pyproject:
    PACKAGE: str = tomllib.load(pyproject)["project"]["name"]

_BLOCK = re.compile(r"^```(\w*)\n(.*?)^```$", re.MULTILINE | re.DOTALL)
_INLINE_CODE = re.compile(r"`[^`\n]*`")
_LINK = re.compile(r"\]\(([^)\s]+)\)")
_HEADING = re.compile(r"^#{1,6} (.+)$", re.MULTILINE)
_ROUTE = re.compile(r"\b(GET|POST|PUT|PATCH|DELETE)\s+/[^\s`\"']*")
# a bare API path between backticks or quotes (prose, tables, code blocks alike)
_API_PATH = re.compile(
    r"[`\"']/(?:customer|account|bank|custody|trading|transaction|staking|applications|webhooks?|organization/|asset|ticker)(?:[/?{][^`\"']*)?[`\"']"
)
# the `path` of an ApikeyLog is a value the API returns ("GET /custody/…"), shown as such in apikeys.md
_ALLOWED = {"readme/resource/apikeys.md": ["GET /custody/…"]}


@pytest.fixture(scope="module")
def server() -> Iterator[Server]:
    """The documentation server (tests/server/docs.py) answers realistic bodies to the examples"""
    server = Server(DocsHandler).start()
    yield server
    server.close()


def prelude(port: int) -> str:
    """What every example can take for granted: `client` pointed at the documentation server (an example that builds
    its own client simply reassigns it) and `customer`, the `Created` of a customer."""
    return (
        "from bitgen import BitgenClient\n"
        "from bitgen.models import Created\n"
        'client = BitgenClient(scope="YOUR_SCOPE_UUID", apiKey="YOUR_API_KEY", '
        f'host="127.0.0.1", port={port}, isSsl=False)\n'
        'customer = Created("CUSTOMER_UUID")\n'
    )


def docs() -> list[Path]:
    return [ROOT / "README.md", *sorted((ROOT / "readme").rglob("*.md"))]


def page(doc: Path) -> str:
    return doc.relative_to(ROOT).as_posix()


def code_blocks(text: str) -> list[tuple[str, str]]:
    """[(lang, body)]"""
    return [(match.group(1), match.group(2)) for match in _BLOCK.finditer(text)]


def prose(text: str) -> str:
    """The text without fenced blocks and inline code — where headings and links live"""
    return _INLINE_CODE.sub("", _BLOCK.sub("", text))


def slug(heading: str) -> str:
    """GitHub's anchor of a heading: lowercase, punctuation dropped, spaces → `-`"""
    text = heading.replace("`", "").strip().lower()
    return re.sub(r"[^\w\- ]", "", text).replace(" ", "-")


def anchors(file: Path) -> list[str]:
    return [slug(heading) for heading in _HEADING.findall(prose(file.read_text(encoding="utf-8")))]


def test_every_python_example_runs(server: Server, tmp_path: Path) -> None:
    count = 0
    env = {**os.environ, "PYTHONWARNINGS": "default"}
    for doc in docs():
        n = 0
        for lang, body in code_blocks(doc.read_text(encoding="utf-8")):
            if lang != "python":
                continue
            n += 1
            count += 1
            file = tmp_path / f"{page(doc).replace('/', '_').replace('.', '_')}_{n}.py"
            file.write_text(prelude(server.port) + body, encoding="utf-8")
            result = subprocess.run(
                [sys.executable, str(file)], capture_output=True, text=True, env=env, timeout=60, check=False
            )
            assert result.returncode == 0, f"{page(doc)}, example {n} failed:\n{result.stdout}{result.stderr}"
            assert result.stderr == "", f"{page(doc)}, example {n} wrote on stderr:\n{result.stderr}"
    assert count > 0, "no Python example found in the documentation"


def test_relative_links_and_anchors_resolve() -> None:
    failures: list[str] = []
    for doc in [*docs(), ROOT / "CONTRIBUTING.md"]:
        for target in _LINK.findall(prose(doc.read_text(encoding="utf-8"))):
            if re.match(r"^[a-z]+:", target):
                continue  # absolute URL
            file, _, anchor = target.partition("#")
            destination = doc if file == "" else doc.parent / file
            if not destination.is_file():
                failures.append(f"{page(doc)}: broken link {target}")
            elif anchor and anchor not in anchors(destination):
                failures.append(f"{page(doc)}: unknown anchor {target}")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    failures += [f"README.md does not link {page(doc)}" for doc in docs()[1:] if f"]({page(doc)})" not in readme]
    # CONTRIBUTING.md is internal: the published documentation never links it
    failures += [
        f"{page(doc)} links CONTRIBUTING.md" for doc in docs() if "CONTRIBUTING.md" in doc.read_text(encoding="utf-8")
    ]
    assert failures == []


def test_no_api_route_in_the_published_documentation() -> None:
    """The published documentation is the SDK's, not the API's: no HTTP route (`GET /custody/{user}`) and no bare API
    path (`/customer`, `/bank`…) anywhere in it, code blocks included. The only tolerated occurrence is a data value the
    API returns, listed explicitly."""
    failures: list[str] = []
    for doc in docs():
        allowed = _ALLOWED.get(page(doc), [])
        for index, line in enumerate(doc.read_text(encoding="utf-8").split("\n"), start=1):
            for pattern in (_ROUTE, _API_PATH):
                failures += [
                    f"{page(doc)}:{index}: {match.group(0)}"
                    for match in pattern.finditer(line)
                    if match.group(0) not in allowed
                ]
    assert failures == [], "API routes and paths do not belong to the SDK documentation"


def test_the_readme_title_carries_the_version() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert readme.split("\n", 1)[0] == f"# {PACKAGE} — v{VERSION}"
