from __future__ import annotations

import json
import socket
import time
from dataclasses import dataclass
from datetime import timezone
from email.utils import parsedate_to_datetime
from enum import Enum
from typing import Any, Callable, Iterator
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import HTTPRedirectHandler, Request, build_opener

from riftsense.core.security import require_riot_api_url


class RiotErrorCategory(str, Enum):
    SUCCESS = "SUCCESS"
    RATE_LIMITED = "RATE_LIMITED"
    TRANSIENT_SERVER_ERROR = "TRANSIENT_SERVER_ERROR"
    NETWORK_ERROR = "NETWORK_ERROR"
    TIMEOUT = "TIMEOUT"
    AUTH_ERROR = "AUTH_ERROR"
    NOT_FOUND = "NOT_FOUND"
    FORBIDDEN = "FORBIDDEN"
    BAD_REQUEST = "BAD_REQUEST"
    OTHER_PERMANENT_ERROR = "OTHER_PERMANENT_ERROR"
    CANCELLED = "CANCELLED"


@dataclass(frozen=True)
class RiotRetryPolicy:
    request_timeout: float = 12.0
    maximum_attempts: int = 3
    base_backoff: float = 0.5
    maximum_backoff: float = 2.0
    retry_after_cap: float = 10.0

    def __post_init__(self) -> None:
        if self.request_timeout <= 0:
            raise ValueError("Riot request timeout must be positive.")
        if self.maximum_attempts < 1:
            raise ValueError("Riot maximum attempts must be at least one.")
        if min(self.base_backoff, self.maximum_backoff, self.retry_after_cap) < 0:
            raise ValueError("Riot retry delays cannot be negative.")


@dataclass(frozen=True)
class RiotApiResponse:
    data: Any
    status: int | None
    headers: dict[str, str]
    category: RiotErrorCategory
    attempts: int
    message: str = ""

    def __iter__(self) -> Iterator[Any]:
        """Preserve the historical three-value response unpacking API."""
        yield self.data
        yield self.status
        yield self.headers

    def __len__(self) -> int:
        return 3

    def __getitem__(self, index):
        return (self.data, self.status, self.headers)[index]


# Preserve the existing public type name for callers that import it.
JsonResponse = RiotApiResponse


class _RiotApiRedirectHandler(HTTPRedirectHandler):
    """Validate every Riot API redirect before urllib follows it."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        require_riot_api_url(newurl)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def _response_message(data: Any, fallback: str = "") -> str:
    if isinstance(data, dict):
        status = data.get("status")
        if isinstance(status, dict) and status.get("message"):
            return str(status["message"])
        if data.get("message"):
            return str(data["message"])
    return str(fallback or "")


def _classify_http(status: int, data: Any) -> RiotErrorCategory:
    if 200 <= status < 300:
        return RiotErrorCategory.SUCCESS
    if status == 429:
        return RiotErrorCategory.RATE_LIMITED
    if status in {500, 502, 503, 504}:
        return RiotErrorCategory.TRANSIENT_SERVER_ERROR
    if status == 401:
        return RiotErrorCategory.AUTH_ERROR
    if status == 403:
        message = _response_message(data).casefold()
        if message.strip() == "forbidden" or any(
            marker in message
            for marker in ("unauthorized", "api key", "token", "expired")
        ):
            return RiotErrorCategory.AUTH_ERROR
        return RiotErrorCategory.FORBIDDEN
    if status == 404:
        return RiotErrorCategory.NOT_FOUND
    if status == 400:
        return RiotErrorCategory.BAD_REQUEST
    return RiotErrorCategory.OTHER_PERMANENT_ERROR


def _is_timeout(exc: BaseException) -> bool:
    if isinstance(exc, (TimeoutError, socket.timeout)):
        return True
    return isinstance(exc, URLError) and isinstance(
        getattr(exc, "reason", None),
        (TimeoutError, socket.timeout),
    )


def _endpoint_category(url: str) -> str:
    parts = [part for part in urlparse(url).path.split("/") if part]
    if len(parts) >= 3 and parts[0] in {"lol", "riot"}:
        return f"{parts[1]}-{parts[2]}"
    return "riot-api"


def _final_message(
    category: RiotErrorCategory,
    message: str,
) -> str:
    stable_messages = {
        RiotErrorCategory.RATE_LIMITED: "Riot API rate-limit retry budget exhausted.",
        RiotErrorCategory.TRANSIENT_SERVER_ERROR: (
            "Riot API transient server failure retry budget exhausted."
        ),
        RiotErrorCategory.NETWORK_ERROR: (
            "Riot API network failure retry budget exhausted."
        ),
        RiotErrorCategory.TIMEOUT: "Riot API request timed out after bounded retries.",
        RiotErrorCategory.AUTH_ERROR: "Riot API key is invalid or expired.",
        RiotErrorCategory.CANCELLED: "Riot API request cancelled.",
    }
    return stable_messages.get(category, message or category.value)


class RiotPublicClient:
    """Whitelist-enforced Riot public API client with bounded retry policy."""

    def __init__(
        self,
        user_agent: str = "RiftSense/v1-beta",
        *,
        policy: RiotRetryPolicy | None = None,
        sleep: Callable[[float], None] = time.sleep,
        clock: Callable[[], float] = time.time,
        log: Callable[[str], None] | None = None,
    ) -> None:
        self.user_agent = user_agent
        self.policy = policy or RiotRetryPolicy()
        self._sleep = sleep
        self._clock = clock
        self._log = log or (lambda _message: None)
        self._opener = build_opener(_RiotApiRedirectHandler())

    @staticmethod
    def _cancelled(cancel_event: Any) -> bool:
        return bool(cancel_event is not None and cancel_event.is_set())

    def _wait(self, delay: float, cancel_event: Any) -> bool:
        delay = max(0.0, float(delay))
        if self._cancelled(cancel_event):
            return False
        if cancel_event is not None:
            return not bool(cancel_event.wait(delay))
        self._sleep(delay)
        return True

    def _retry_after(self, headers: dict[str, str]) -> float | None:
        value = next(
            (
                str(header_value).strip()
                for name, header_value in headers.items()
                if str(name).casefold() == "retry-after"
            ),
            "",
        )
        if not value:
            return None
        try:
            delay = float(value)
        except ValueError:
            try:
                parsed = parsedate_to_datetime(value)
                if parsed.tzinfo is None:
                    parsed = parsed.replace(tzinfo=timezone.utc)
                delay = parsed.timestamp() - self._clock()
            except (TypeError, ValueError, OverflowError):
                return None
        return min(max(0.0, delay), self.policy.retry_after_cap)

    def _backoff(self, attempt: int) -> float:
        return min(
            self.policy.base_backoff * (2 ** max(0, attempt - 1)),
            self.policy.maximum_backoff,
        )

    @staticmethod
    def _annotated_data(data: Any, category: RiotErrorCategory, message: str) -> Any:
        if category == RiotErrorCategory.SUCCESS:
            return data
        if isinstance(data, dict):
            annotated = dict(data)
            status = annotated.get("status")
            status = dict(status) if isinstance(status, dict) else {}
            original_message = status.get("message")
            if original_message and original_message != message:
                status["riot_message"] = original_message
            status["message"] = message
            status["category"] = category.value
            annotated["status"] = status
            return annotated
        return {
            "status": {
                "message": message,
                "category": category.value,
            }
        }

    def _perform_once(
        self,
        url: str,
        api_key: str,
        timeout: float,
    ) -> tuple[Any, int | None, dict[str, str], RiotErrorCategory, str]:
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
            with self._opener.open(request, timeout=timeout) as response:
                require_riot_api_url(str(response.geturl() or url))
                raw = response.read().decode("utf-8")
                data = json.loads(raw) if raw else {}
                status = int(response.status)
                category = _classify_http(status, data)
                return data, status, dict(response.headers), category, _response_message(data)
        except HTTPError as exc:
            try:
                raw = exc.read().decode("utf-8")
                data = json.loads(raw) if raw else {}
            except (OSError, UnicodeDecodeError, json.JSONDecodeError):
                data = {}
            finally:
                exc.close()
            status = int(exc.code)
            category = _classify_http(status, data)
            return (
                data,
                status,
                dict(exc.headers or {}),
                category,
                _response_message(data, f"HTTP {status}"),
            )
        except (URLError, TimeoutError, socket.timeout, OSError) as exc:
            category = (
                RiotErrorCategory.TIMEOUT
                if _is_timeout(exc)
                else RiotErrorCategory.NETWORK_ERROR
            )
            return {}, None, {}, category, str(exc)
        except (ValueError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            return (
                {},
                None,
                {},
                RiotErrorCategory.OTHER_PERMANENT_ERROR,
                str(exc),
            )

    def get_json(
        self,
        url: str,
        api_key: str,
        timeout: float | None = None,
        *,
        cancel_event: Any = None,
    ) -> RiotApiResponse:
        require_riot_api_url(url)
        request_timeout = self.policy.request_timeout if timeout is None else float(timeout)
        if request_timeout <= 0:
            raise ValueError("Riot request timeout must be positive.")

        endpoint = _endpoint_category(url)
        for attempt in range(1, self.policy.maximum_attempts + 1):
            if self._cancelled(cancel_event):
                return RiotApiResponse(
                    self._annotated_data({}, RiotErrorCategory.CANCELLED, "Request cancelled."),
                    None,
                    {},
                    RiotErrorCategory.CANCELLED,
                    attempt - 1,
                    "Request cancelled.",
                )

            data, status, headers, category, message = self._perform_once(
                url,
                api_key,
                request_timeout,
            )
            retryable = category in {
                RiotErrorCategory.RATE_LIMITED,
                RiotErrorCategory.TRANSIENT_SERVER_ERROR,
                RiotErrorCategory.NETWORK_ERROR,
                RiotErrorCategory.TIMEOUT,
            }
            if not retryable or attempt >= self.policy.maximum_attempts:
                message = _final_message(category, message)
                if category != RiotErrorCategory.SUCCESS:
                    self._log(
                        f"Riot request final outcome • endpoint={endpoint} • "
                        f"category={category.value} • status={status or '-'} • "
                        f"attempt={attempt}/{self.policy.maximum_attempts}"
                    )
                return RiotApiResponse(
                    self._annotated_data(data, category, message),
                    status,
                    headers,
                    category,
                    attempt,
                    message,
                )

            delay = (
                self._retry_after(headers)
                if category == RiotErrorCategory.RATE_LIMITED
                else None
            )
            if delay is None:
                delay = self._backoff(attempt)
            self._log(
                f"Riot request retry • endpoint={endpoint} • "
                f"category={category.value} • status={status or '-'} • "
                f"attempt={attempt}/{self.policy.maximum_attempts} • delay={delay:.3g}s"
            )
            if not self._wait(delay, cancel_event):
                return RiotApiResponse(
                    self._annotated_data({}, RiotErrorCategory.CANCELLED, "Request cancelled."),
                    None,
                    {},
                    RiotErrorCategory.CANCELLED,
                    attempt,
                    "Request cancelled.",
                )

        raise AssertionError("unreachable Riot retry state")
