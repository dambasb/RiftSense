from __future__ import annotations

import json
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from riftsense.core.security import require_riot_api_url

JsonResponse = tuple[Any, int | None, dict[str, str]]


class RiotPublicClient:
    """Whitelist-enforced Riot public API client."""

    def __init__(self, user_agent: str = "RiftSense/v1-beta") -> None:
        self.user_agent = user_agent

    def get_json(self, url: str, api_key: str, timeout: float = 12.0) -> JsonResponse:
        require_riot_api_url(url)
        request = Request(
            url,
            headers={
                "X-Riot-Token": str(api_key or ""),
                "Accept": "application/json",
                "User-Agent": self.user_agent,
            },
            method="GET",
        )
        try:
            with urlopen(request, timeout=timeout) as response:
                require_riot_api_url(str(response.geturl() or url))
                raw = response.read().decode("utf-8")
                data = json.loads(raw) if raw else {}
                return data, response.status, dict(response.headers)
        except HTTPError as exc:
            try:
                raw = exc.read().decode("utf-8")
                data = json.loads(raw) if raw else {}
            except (OSError, UnicodeDecodeError, json.JSONDecodeError):
                data = {}
            return data, exc.code, dict(exc.headers or {})
        except (URLError, TimeoutError, OSError, ValueError, json.JSONDecodeError) as exc:
            return {"status": {"message": str(exc)}}, None, {}
