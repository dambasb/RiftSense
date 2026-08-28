from __future__ import annotations

from urllib.parse import urlparse

RIOT_PUBLIC_SUFFIX = ".api.riotgames.com"
ALLOWED_LOCAL_HOSTS = {"127.0.0.1", "localhost"}


def is_allowed_riot_api_url(url: str) -> bool:
    try:
        parsed = urlparse(str(url))
    except ValueError:
        return False
    host = (parsed.hostname or "").lower()
    if parsed.scheme.lower() != "https":
        return False
    if parsed.username or parsed.password:
        return False
    try:
        port = parsed.port
    except ValueError:
        return False
    if port not in (None, 443):
        return False
    return bool(host and host.endswith(RIOT_PUBLIC_SUFFIX))


def require_riot_api_url(url: str) -> None:
    if not is_allowed_riot_api_url(url):
        raise ValueError("Blocked non-Riot public API URL.")


def is_allowed_local_https_url(url: str, *, allowed_ports: set[int] | None = None) -> bool:
    try:
        parsed = urlparse(str(url))
    except ValueError:
        return False
    host = (parsed.hostname or "").lower()
    if parsed.scheme.lower() != "https":
        return False
    if parsed.username or parsed.password:
        return False
    if host not in ALLOWED_LOCAL_HOSTS:
        return False
    try:
        port = parsed.port
    except ValueError:
        return False
    if port is None:
        return False
    if allowed_ports is not None and port not in allowed_ports:
        return False
    return True


def require_local_https_url(url: str, *, allowed_ports: set[int] | None = None) -> None:
    if not is_allowed_local_https_url(url, allowed_ports=allowed_ports):
        raise ValueError("Blocked non-local League Client URL.")
