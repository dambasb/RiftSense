from __future__ import annotations

import base64
import json
import os
import ssl
from pathlib import Path
from typing import Any, Callable
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

from riftsense.core.security import is_allowed_local_https_url, require_local_https_url

LIVE_ENDPOINT = "https://127.0.0.1:2999/liveclientdata/allgamedata"
LIVE_PLAYER_SCORES_ENDPOINT = "https://127.0.0.1:2999/liveclientdata/playerscores"
LOCAL_SSL = ssl.create_default_context()
LOCAL_SSL.check_hostname = False
LOCAL_SSL.verify_mode = ssl.CERT_NONE
LogFn = Callable[[str], None]


def _noop_log(_message: str) -> None:
    return


class LCUClient:
    """Local League Client client with localhost-only reads and rune-page-only writes."""

    def __init__(self, settings: dict[str, Any] | None = None, *, user_agent: str = "RiftSense/v1-beta", log_warning: LogFn | None = None) -> None:
        self.settings = settings if isinstance(settings, dict) else {}
        self.user_agent = user_agent
        self._log_warning = log_warning or _noop_log
        self.lockfile_path: Path | None = None
        self.port: int | None = None
        self.password: str | None = None
        self.protocol = "https"

    def candidate_dirs(self) -> list[Path]:
        candidates: list[Path] = []
        configured = self.settings.get("league_dir")
        if configured:
            candidates.append(Path(str(configured)))
        env_dir = os.environ.get("LEAGUE_INSTALL_DIR")
        if env_dir:
            candidates.append(Path(env_dir))
        for drive in ("C", "D", "E", "F", "G"):
            candidates.extend([
                Path(f"{drive}:/Riot Games/League of Legends"),
                Path(f"{drive}:/Games/League of Legends"),
                Path(f"{drive}:/Program Files/Riot Games/League of Legends"),
            ])
        program_files = os.environ.get("ProgramFiles")
        if program_files:
            candidates.append(Path(program_files) / "Riot Games" / "League of Legends")
        program_files_x86 = os.environ.get("ProgramFiles(x86)")
        if program_files_x86:
            candidates.append(Path(program_files_x86) / "Riot Games" / "League of Legends")
        seen: set[str] = set()
        unique: list[Path] = []
        for path in candidates:
            key = str(path).lower()
            if key not in seen:
                seen.add(key)
                unique.append(path)
        return unique

    def find_lockfile(self) -> Path | None:
        for directory in self.candidate_dirs():
            path = directory / "lockfile"
            if path.exists():
                return path
        return None

    def connect(self) -> bool:
        path = self.find_lockfile()
        if not path:
            self.lockfile_path = None
            return False
        try:
            raw = path.read_text(encoding="utf-8").strip()
            parts = raw.split(":", 4)
            if len(parts) != 5:
                return False
            _process, _pid, port, password, protocol = parts
            parsed_port = int(port)
            if parsed_port <= 0 or parsed_port > 65535:
                return False
            self.lockfile_path = path
            self.port = parsed_port
            self.password = password
            self.protocol = protocol or "https"
            return True
        except (OSError, ValueError):
            return False

    def _base_url(self) -> str | None:
        if not self.port:
            return None
        base = f"https://127.0.0.1:{self.port}"
        if not is_allowed_local_https_url(base, allowed_ports={self.port}):
            self._log_warning("LCU URL blocked by local safety policy.")
            return None
        return base

    def _auth_header(self) -> str:
        if not self.password:
            return ""
        token = base64.b64encode(f"riot:{self.password}".encode("utf-8")).decode("ascii")
        return f"Basic {token}"

    def get(self, endpoint: str, timeout: float = 0.8) -> tuple[Any, int | None]:
        if not self.port or not self.password:
            if not self.connect():
                return None, None
        base = self._base_url()
        if not base:
            return None, None
        request = Request(base + str(endpoint), headers={"Authorization": self._auth_header(), "Accept": "application/json", "User-Agent": self.user_agent}, method="GET")
        try:
            with urlopen(request, timeout=timeout, context=LOCAL_SSL) as response:
                raw = response.read().decode("utf-8")
                return (json.loads(raw) if raw else {}), response.status
        except HTTPError as exc:
            return None, exc.code
        except (URLError, TimeoutError, OSError, UnicodeDecodeError, json.JSONDecodeError):
            self.port = None
            self.password = None
            return None, None

    def write_json(self, endpoint: str, payload: dict[str, Any] | None, method: str = "PUT", timeout: float = 1.2) -> tuple[Any, int | None, str]:
        method = str(method or "PUT").upper()
        if method not in {"POST", "PUT"}:
            return None, None, "LCU write method blocked."
        if not str(endpoint).startswith("/lol-perks/"):
            return None, None, "LCU write endpoint blocked."
        if not self.port or not self.password:
            if not self.connect():
                return None, None, "League Client is not connected."
        base = self._base_url()
        if not base:
            return None, None, "LCU safety check failed."
        body = json.dumps(payload if isinstance(payload, dict) else {}).encode("utf-8")
        request = Request(base + str(endpoint), data=body, headers={"Authorization": self._auth_header(), "Accept": "application/json", "Content-Type": "application/json", "User-Agent": self.user_agent}, method=method)
        try:
            with urlopen(request, timeout=timeout, context=LOCAL_SSL) as response:
                raw = response.read().decode("utf-8")
                if not raw:
                    return {}, response.status, ""
                try:
                    data = json.loads(raw)
                except (json.JSONDecodeError, TypeError, ValueError):
                    data = {"raw": raw}
                return data, response.status, ""
        except HTTPError as exc:
            try:
                raw = exc.read().decode("utf-8", errors="replace")
            except (OSError, UnicodeDecodeError):
                raw = ""
            message = raw
            try:
                parsed = json.loads(raw)
                message = str(parsed.get("message", parsed.get("errorCode", raw)))
            except (json.JSONDecodeError, TypeError, ValueError):
                pass
            return None, exc.code, message or f"HTTP {exc.code}"
        except (URLError, TimeoutError, OSError, ValueError) as exc:
            self.port = None
            self.password = None
            return None, None, str(exc)

    def get_bytes(self, endpoint: str, timeout: float = 2.0) -> tuple[bytes | None, int | None]:
        if not self.port or not self.password:
            if not self.connect():
                return None, None
        base = self._base_url()
        if not base:
            return None, None
        request = Request(base + str(endpoint), headers={"Authorization": self._auth_header(), "User-Agent": self.user_agent}, method="GET")
        try:
            with urlopen(request, timeout=timeout, context=LOCAL_SSL) as response:
                return response.read(), response.status
        except HTTPError as exc:
            return None, exc.code
        except (URLError, TimeoutError, OSError):
            self.port = None
            self.password = None
            return None, None


def get_live_game_data(endpoint: str = LIVE_ENDPOINT, timeout: float = 0.8, *, user_agent: str = "RiftSense/v1-beta") -> dict[str, Any] | None:
    require_local_https_url(endpoint, allowed_ports={2999})
    request = Request(endpoint, headers={"User-Agent": user_agent, "Accept": "application/json"}, method="GET")
    try:
        with urlopen(request, timeout=timeout, context=LOCAL_SSL) as response:
            return json.loads(response.read().decode("utf-8"))
    except (HTTPError, URLError, TimeoutError, OSError, UnicodeDecodeError, json.JSONDecodeError):
        return None


def get_live_player_scores(riot_id: str, timeout: float = 0.45, *, user_agent: str = "RiftSense/v1-beta") -> dict[str, Any] | None:
    """Fetch the freshest Live Client score row for one visible player.

    The dedicated endpoint is used as a narrow refresh for the enemy jungler so
    the role card does not depend solely on the larger /allgamedata snapshot.
    Riot IDs are URL-encoded because the `#TAG` delimiter must not become a URL
    fragment.
    """
    player_id = str(riot_id or "").strip()
    if not player_id:
        return None
    endpoint = f"{LIVE_PLAYER_SCORES_ENDPOINT}?riotId={quote(player_id, safe='')}"
    require_local_https_url(endpoint, allowed_ports={2999})
    request = Request(endpoint, headers={"User-Agent": user_agent, "Accept": "application/json"}, method="GET")
    try:
        with urlopen(request, timeout=timeout, context=LOCAL_SSL) as response:
            payload = json.loads(response.read().decode("utf-8"))
            return payload if isinstance(payload, dict) else None
    except (HTTPError, URLError, TimeoutError, OSError, UnicodeDecodeError, json.JSONDecodeError):
        return None
