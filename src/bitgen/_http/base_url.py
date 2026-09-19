"""The base URL of the API for a configuration: `scheme://host[:port]`, no trailing slash, no version prefix."""

from __future__ import annotations

import re

from bitgen._support import values
from bitgen.constants import Env

LOCALHOST_PORT = 3002

_HOSTS = {
    Env.PRODUCTION: "https://api.bitgen.com",
    Env.SANDBOX: "https://api.sandbox.bitgen.com",
    Env.STAGING: "https://api.staging.btgn.dev",
}
# Letters, digits, dots, hyphens (and underscores of internal DNS names): a scheme, a port, a path, userinfo or a
# bracketed IPv6 are refused
_BARE_HOSTNAME = re.compile(r"[A-Za-z0-9._-]+")


def resolve(env: object, host: object, port: object, isSsl: object) -> str:
    """`ValueError` when `env` is unknown, `host` is not a bare hostname or `port` is out of range; `TypeError` on a
    wrong type. The values of `env` and `host` are never echoed."""
    environment = values.ensure(env, Env.VALUES, "env")
    if port is not None:
        if isinstance(port, bool) or not isinstance(port, int):
            raise TypeError("port must be an integer between 1 and 65535")
        if port < 1 or port > 65535:
            raise ValueError("port must be an integer between 1 and 65535")
    if not isinstance(isSsl, bool):
        raise TypeError("isSsl must be a boolean")
    # Custom host (a container, a tunnel): bare hostname, scheme and port come from isSsl / port
    if host is not None:
        if not isinstance(host, str):
            raise TypeError("host must be a string: a bare hostname (no scheme, port or path)")
        if not _BARE_HOSTNAME.fullmatch(host):
            raise ValueError("host must be a bare hostname (no scheme, port or path): use port and isSsl")
        return f"{'https' if isSsl else 'http'}://{host}:{port if port is not None else 80}"
    if environment == Env.LOCALHOST:
        return f"http://localhost:{port if port is not None else LOCALHOST_PORT}"
    return _HOSTS[environment]
