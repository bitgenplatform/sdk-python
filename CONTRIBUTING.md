# Contributing

Internal notes for working on `bitgen-sdk`. The client documentation lives in `README.md` and `readme/`; this file is not published.

## Prerequisites

Nothing installed locally: everything runs in throwaway containers mounted on the repository. The tools live in a virtual environment inside the repository (`.venv/<python version>/`, ignored by git), created once per Python version:

```bash
docker run --rm -v "$PWD":/app -w /app python:3.11-slim sh -c "python -m venv .venv/3.11 && .venv/3.11/bin/pip install --quiet -e '.[dev]'"
docker run --rm -v "$PWD":/app -w /app python:3.11-slim .venv/3.11/bin/ruff check
docker run --rm -v "$PWD":/app -w /app python:3.11-slim .venv/3.11/bin/ruff format --check
docker run --rm -v "$PWD":/app -w /app python:3.11-slim .venv/3.11/bin/mypy
docker run --rm -v "$PWD":/app -w /app python:3.11-slim .venv/3.11/bin/pytest          # same with python:3.12-slim, 3.13, 3.14 and their .venv/3.x
```

No network access is needed once the virtual environment exists: the tests work offline (`docker run --network none …`). The tools are pinned to a minor version in `pyproject.toml` (`[project.optional-dependencies] dev`): a new ruff or mypy can change what passes, so a bump is a deliberate change, followed by the full matrix.

## Commands

```bash
ruff check            # lint, src/ and tests/ — the security rules of bandit (`S`) included
ruff format --check   # formatting (`ruff format` rewrites)
mypy                  # strict, src/ and tests/
pytest                # the tests
python -m build       # the sdist and the wheel, in dist/
```

The `package` job of the CI builds the sdist and the wheel, checks them (`twine check`), installs the wheel in a blank environment and, there, type-checks `tests/package/consumer.py` in strict mode (what an integrator writes, with expected mistakes as `# type: ignore[...]` — an unused one fails) and runs `tests/package/smoke.py` (the wheel against the test server). Locally:

```bash
docker run --rm -v "$PWD":/app -w /app python:3.11-slim sh -c ".venv/3.11/bin/python -m build && python -m venv /tmp/blank && /tmp/blank/bin/pip install -q dist/*.whl 'mypy>=1.20,<1.21' && /tmp/blank/bin/mypy --strict tests/package/consumer.py && PYTHONPATH=/app /tmp/blank/bin/python tests/package/smoke.py"
```

`pytest` runs the HTTP layer against a fake transport, the real transport against a throwaway server in a thread of the test process (`tests/server/router.py`: echo, timeout, deadline on a slow answer, closed port, redirect, JSON and non-JSON answers, self-signed certificate refused), the argument validation, and the documentation (`tests/test_docs.py`: every ```` ```python ```` block of `README.md` and `readme/**/*.md` is executed against the package with `client` pointed at `tests/server/docs.py`, every relative link and anchor must resolve, the `README.md` title must carry `bitgen.VERSION`, and no API route or path may appear in the published documentation — `test_no_api_route_in_the_published_documentation`, with an explicit allow-list for data values that look like one; `tests/test_docs_resources.py` checks every `readme/resource/<r>.md` against the code by reflection: one `## <method>` section per public method in the order of the source, each listed in the Methods table, a signature block identical to the real signature, and every PascalCase name in backticks an export of the SDK; `tests/test_models_shape.py` builds the main model of every resource from the fixtures of its test and checks it is frozen down the tree, equal by value, and survives `pickle` and `copy.deepcopy`; `tests/test_webhooks_endpoint.py` runs a real `http.server` endpoint that verifies a delivery it receives over HTTP, with the bytes and the headers exactly as the standard library hands them over; `tests/test_client.py` checks by reflection that every exported resource hangs off `BitgenClient` in the order of the `README.md`). Warnings are errors (`filterwarnings`).

## Repository layout

- `src/bitgen/client.py` — the entry point: keyword-only constructor, validation, one attribute per resource
- `src/bitgen/constants.py` — `Env`, `Asset`: string constants on frozen classes (`ConstantsMeta` in `_support/constants.py`: no assignment, no instantiation, `VALUES` in the order of the contract); `src/bitgen/version.py` — the version (User-Agent, README title, package metadata through `pyproject.toml`)
- `src/bitgen/_http/` — `client.py` (`HttpClient`: URL, query, headers, JSON, error mapping), `transport.py` (`Transport` protocol, `HttpTransport` on `http.client` with one deadline for the whole request, `Response`, `TransportError`), `base_url.py`, `timeout.py`
- `src/bitgen/_support/` — argument validation: `path.py` (path segments), `user_id.py` (customers — the `UserRef` union: `str`, `Created`, `Customer`, `Account`, `UserSummary`, `OrderUser`), `asset_id.py` (assets: string, `Asset` or `AssetRef` model), `reference.py` (an object the SDK returns — an `Order`, a `StakingMovement`, a `Core`… — given as its uuid or as the model), `amount.py` (amounts: `str`, `int`, `float`, `Decimal`), `values.py` (`ensure()`: a string against a `VALUES` list, static message; `string` / `optional_string` / `optional_int` / `optional_bool` / `optional_choice`: the type of an argument, checked at runtime)
- `src/bitgen/models/` — one frozen dataclass per object the API returns (`from_dict(data)` reading through `_cast.py`: typed, tolerant reads, `answer` / `answer_list` for the top-level shape), the constant classes of the values the API lists (`AssetState`…, on `ConstantsMeta`), `history.py` (the shared `History`); `src/bitgen/resources/` — one class per resource, hung off `BitgenClient` (`asset.py`…) — `StakingResource` also takes the `CoreResource`: `providers()` is `core.list()` filtered on `STAKING`; `WebhooksResource.verify()` is the one method that sends nothing — HMAC over the raw bytes with `hmac.compare_digest`, then the freshness, then the envelope, and `ReceivedHeaders` (`HeaderItems`, a `Protocol` with `items()`, or a list of pairs) is what makes any framework's headers object acceptable
- `src/bitgen/page.py` — generic paginated list; `src/bitgen/errors.py` — `BitgenError`, `UnexpectedAnswerError`
- `src/bitgen/__init__.py` — the public surface; everything under `_http/` and `_support/` is internal
- `tests/` — pytest, mirrors `src/`; `tests/fake_transport.py` records requests and answers with queued responses; `tests/server/` holds the throwaway servers (`router.py` for the transport tests, `docs.py` for the documentation — realistic answers, route by route, extend it with every resource); `tests/package/` is the installed wheel seen by an integrator (`consumer.py` typed, `smoke.py` runtime), run by the `package` job of the CI
- `README.md`, `readme/` — client documentation, published with the source distribution; `CHANGELOG.md`

## Adding a resource

1. Read the API reference of the resource (ask BITGEN's API team). Write its models under `src/bitgen/models/<resource>.py` (one frozen dataclass per object the API returns, `from_dict(data)` reading every field through `_cast` tolerantly, fields named and typed as the API documents them — every `state` a plain `str`, with a constant class naming the known values —, unknown fields ignored), export them from `models/__init__.py`, then `src/bitgen/resources/<resource>.py` — required arguments positional, optional ones keyword-only defaulting to `None` (not sent), input strings validated against the `VALUES` of their constant class before any request (`_support.values.ensure`), path segments through `_support.path.segment`, customers through `_support.user_id.resolve`, assets through `_support.asset_id.resolve`, amounts through `_support.amount.normalize`, explicit request bodies, answers through `_cast.answer` / `_cast.answer_list` then the models and `Page.from_dict` — its attribute on `BitgenClient` and its export from `resources/__init__.py`.
2. Write `tests/test_<resource>.py` with the fake transport: for every method, the exact path, query and body sent, the mapping of the answer, and at least one error (`403 forbidden_permission` at minimum). The constant classes exported by `bitgen.models` are checked by reflection (`tests/test_models_constants.py`: frozen, `VALUES` complete and ordered) without touching that file; add the main model of the resource and its fixture to `tests/test_models_shape.py`. Extend `tests/package/consumer.py` (what an integrator writes, plus a few mistakes mypy must catch) and `tests/package/smoke.py` (one journey through the resource against the documentation server) — then re-read both: they are what the `package` job of the CI runs against the wheel.
3. Document it: `readme/resource/<resource>.md` on the template of the Node.js and PHP SDKs (introduction, methods, one section per method, errors, related), its routes in `tests/server/docs.py` (realistic answers), its line in `README.md`, `CHANGELOG.md` — then re-read `README.md` and `readme/` in full.
4. Run `ruff check`, `ruff format --check`, `mypy` and `pytest` on Python 3.11, 3.12, 3.13 and 3.14.

## Release

The package is published on [PyPI](https://pypi.org/project/bitgen-sdk/) by `.github/workflows/release.yml` on every `vX.Y.Z` tag, through **trusted publishing**: PyPI trusts the workflow of this repository (OpenID Connect), there is no token and no secret anywhere.

Once, before the first release:

1. Create an account on [pypi.org](https://pypi.org/) (two-factor authentication is mandatory).
2. On PyPI, *Your projects → Publishing → Add a new pending publisher*: PyPI project name `bitgen-sdk`, owner `bitgenplatform`, repository `sdk-python`, workflow `release.yml`, environment `pypi`. The project is created on the first publication.
3. On GitHub, *Settings → Environments → New environment* named `pypi` (required reviewers optional: the publication then waits for an approval).

Every release:

1. Set `VERSION` in `src/bitgen/version.py`, the `README.md` title (`# bitgen-sdk — vX.Y.Z`, checked by `tests/test_docs.py`) and the date of the `CHANGELOG.md` entry — the three always move together.
2. Commit on the main branch, then `git tag -a vX.Y.Z -m vX.Y.Z` and `git push origin <branch> vX.Y.Z` — the workflow refuses a tag that is not `v` + `VERSION`, runs the checks, builds the sdist and the wheel and publishes them.
3. Check the version on [pypi.org/project/bitgen-sdk](https://pypi.org/project/bitgen-sdk/) (a few minutes after the push), then install it in a blank container — it must print the version:

   ```bash
   docker run --rm python:3.11-slim sh -c "pip install --quiet bitgen-sdk==X.Y.Z && python -c 'import bitgen; print(bitgen.VERSION)'"
   ```

The wheel holds `src/bitgen` only; the source distribution adds `README.md`, `CHANGELOG.md` and `readme/`.

## Rules

- The BITGEN API v4 is the only source of truth: routes, fields, error codes and behaviours come from the API reference kept by BITGEN's API team (not part of this repository), nothing is invented. A point it does not cover is a question to the API team, not a guess.
- `README.md` and `readme/` are re-read in full on every change: nothing stale, nothing anticipated, nothing the API does not do; every Python example runs and every link resolves (`tests/test_docs.py`). The documentation never lists the permissions of a key (they are set by the platform, not by the integrator), nor API routes or paths: it documents the SDK, not the API — the errors an integrator receives stay.
- No dependency beyond the standard library; Python 3.11 syntax and library only.
- Nothing ever contains the API key: not a URL, not an exception message, not a log — including what a server sends back: the key is redacted from a raw error body that echoes it, and an `http.client` exception (whose message may carry the first line the server sent) is named, never chained.
- The names of the SDK are those of the API contract and of the Node.js and PHP SDKs — resources, methods, arguments, fields and constants keep their spelling (`apiKey`, `isSsl`, `targetAddress`, `Env.SANDBOX`): the three SDKs read the same, the documentation is one. Only what is specific to Python is Pythonic (modules, `from_dict`, `str(error)`), and a name that is a reserved word in Python takes a trailing underscore, the official idiom (`from_`, `pending.in_`) — the API still receives `from` and `in`.
- The constant classes mirror the Node.js SDK's `src/constants.ts` and the PHP SDK's `src/Model/`: same names, same keys, same values, same order — a set added on one side is added on the others. Never a string literal for an enumerated value in the documentation or the tests: always the constant (`Env.SANDBOX`, `Asset.ETH`); raw strings stay in the response fixtures and the expected request bodies only.
