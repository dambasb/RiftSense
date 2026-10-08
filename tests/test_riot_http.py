import json
import socket
import threading
import unittest
from io import BytesIO
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from unittest.mock import Mock, patch
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse

from riftsense.core.security import require_riot_api_url
from riftsense.riot.http import (
    RiotErrorCategory,
    RiotPublicClient,
    RiotRetryPolicy,
)


class _RecordingHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.server.requests.append(
            {
                "path": self.path,
                "riot_token": self.headers.get("X-Riot-Token"),
            }
        )
        status, headers, body = self.server.routes[self.path]
        self.send_response(status)
        for name, value in headers.items():
            self.send_header(name, value)
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, _format, *_args):
        return


class _RecordingServer:
    def __init__(self):
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), _RecordingHandler)
        self.server.routes = {}
        self.server.requests = []
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)

    @property
    def origin(self):
        host, port = self.server.server_address
        return f"http://{host}:{port}"

    def route(self, path, status=200, headers=None, payload=None):
        body = json.dumps(payload if payload is not None else {}).encode("utf-8")
        response_headers = dict(headers or {})
        if payload is not None:
            response_headers.setdefault("Content-Type", "application/json")
        self.server.routes[path] = (status, response_headers, body)

    def __enter__(self):
        self.thread.start()
        return self

    def __exit__(self, _exc_type, _exc, _traceback):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2.0)


def _test_validator(*allowed_origins):
    allowed = {
        urlparse(origin).netloc
        for origin in allowed_origins
    }

    def validate(url):
        parsed = urlparse(str(url))
        if parsed.scheme == "http" and parsed.netloc in allowed:
            return
        require_riot_api_url(url)

    return validate


class RiotPublicClientRedirectTests(unittest.TestCase):
    API_KEY = "RGAPI-REDIRECT-TEST"

    def test_normal_non_redirect_riot_request(self):
        with _RecordingServer() as riot:
            riot.route("/data", payload={"ok": True})
            with patch(
                "riftsense.riot.http.require_riot_api_url",
                side_effect=_test_validator(riot.origin),
            ):
                data, status, _headers = RiotPublicClient().get_json(
                    riot.origin + "/data",
                    self.API_KEY,
                )

        self.assertEqual(status, 200)
        self.assertEqual(data, {"ok": True})
        self.assertEqual(riot.server.requests[0]["riot_token"], self.API_KEY)

    def test_allowed_riot_to_allowed_riot_redirect(self):
        with _RecordingServer() as first, _RecordingServer() as second:
            first.route(
                "/start",
                status=302,
                headers={"Location": second.origin + "/final"},
            )
            second.route("/final", payload={"redirected": True})
            with patch(
                "riftsense.riot.http.require_riot_api_url",
                side_effect=_test_validator(first.origin, second.origin),
            ):
                data, status, _headers = RiotPublicClient().get_json(
                    first.origin + "/start",
                    self.API_KEY,
                )

        self.assertEqual(status, 200)
        self.assertEqual(data, {"redirected": True})
        self.assertEqual(first.server.requests[0]["riot_token"], self.API_KEY)
        self.assertEqual(second.server.requests[0]["riot_token"], self.API_KEY)

    def test_untrusted_redirect_never_receives_riot_token(self):
        with _RecordingServer() as riot, _RecordingServer() as untrusted:
            riot.route(
                "/start",
                status=302,
                headers={"Location": untrusted.origin + "/capture"},
            )
            untrusted.route("/capture", payload={"unexpected": True})
            with patch(
                "riftsense.riot.http.require_riot_api_url",
                side_effect=_test_validator(riot.origin),
            ):
                data, status, _headers = RiotPublicClient().get_json(
                    riot.origin + "/start",
                    self.API_KEY,
                )

        self.assertIsNone(status)
        self.assertIn("Blocked non-Riot", data["status"]["message"])
        self.assertEqual(untrusted.server.requests, [])


class _FakeResponse:
    def __init__(self, url, payload, status=200, headers=None):
        self._url = url
        self._body = json.dumps(payload).encode("utf-8")
        self.status = status
        self.headers = dict(headers or {})

    def __enter__(self):
        return self

    def __exit__(self, _exc_type, _exc, _traceback):
        return False

    def geturl(self):
        return self._url

    def read(self):
        return self._body


def _http_error(url, status, *, headers=None, message="failure"):
    payload = json.dumps({"status": {"message": message}}).encode("utf-8")
    return HTTPError(
        url,
        status,
        message,
        dict(headers or {}),
        BytesIO(payload),
    )


class _CancelDuringWait:
    def __init__(self):
        self.cancelled = False
        self.waits = []

    def is_set(self):
        return self.cancelled

    def wait(self, delay):
        self.waits.append(delay)
        self.cancelled = True
        return True


class RiotPublicClientRetryTests(unittest.TestCase):
    URL = "https://eun1.api.riotgames.com/lol/league/v4/entries/by-puuid/test"
    API_KEY = "RGAPI-SECRET-RETRY-TEST"

    def make_client(self, side_effect, *, attempts=3, logs=None):
        delays = []
        client = RiotPublicClient(
            policy=RiotRetryPolicy(
                request_timeout=7.0,
                maximum_attempts=attempts,
                base_backoff=0.5,
                maximum_backoff=2.0,
                retry_after_cap=10.0,
            ),
            sleep=delays.append,
            log=(logs if logs is not None else []).append,
        )
        client._opener = Mock()
        client._opener.open.side_effect = side_effect
        return client, delays

    def test_200_returns_without_retry(self):
        client, delays = self.make_client(
            [_FakeResponse(self.URL, {"ok": True})]
        )

        result = client.get_json(self.URL, self.API_KEY)

        self.assertEqual(result.category, RiotErrorCategory.SUCCESS)
        self.assertEqual(result.attempts, 1)
        self.assertEqual(result.data, {"ok": True})
        self.assertEqual(delays, [])
        self.assertEqual(client._opener.open.call_args.kwargs["timeout"], 7.0)

    def test_429_honors_retry_after_then_succeeds(self):
        client, delays = self.make_client(
            [
                _http_error(self.URL, 429, headers={"Retry-After": "3"}),
                _FakeResponse(self.URL, {"ok": True}),
            ]
        )

        result = client.get_json(self.URL, self.API_KEY)

        self.assertEqual(result.category, RiotErrorCategory.SUCCESS)
        self.assertEqual(result.attempts, 2)
        self.assertEqual(delays, [3.0])

    def test_repeated_429_is_bounded_and_classified(self):
        logs = []
        client, delays = self.make_client(
            [
                _http_error(self.URL, 429, headers={"Retry-After": "99"}),
                _http_error(self.URL, 429, headers={"Retry-After": "99"}),
                _http_error(self.URL, 429, headers={"Retry-After": "99"}),
            ],
            logs=logs,
        )

        result = client.get_json(self.URL, self.API_KEY)

        self.assertEqual(result.category, RiotErrorCategory.RATE_LIMITED)
        self.assertEqual(result.attempts, 3)
        self.assertEqual(delays, [10.0, 10.0])
        self.assertIn("retry budget exhausted", result.message)
        self.assertNotIn(self.API_KEY, "\n".join(logs))

    def test_500_retries_with_backoff_then_succeeds(self):
        client, delays = self.make_client(
            [_http_error(self.URL, 500), _FakeResponse(self.URL, {"ok": True})]
        )

        result = client.get_json(self.URL, self.API_KEY)

        self.assertEqual(result.category, RiotErrorCategory.SUCCESS)
        self.assertEqual(delays, [0.5])

    def test_repeated_5xx_exhausts_as_transient_server_error(self):
        client, delays = self.make_client(
            [_http_error(self.URL, status) for status in (500, 503, 504)]
        )

        result = client.get_json(self.URL, self.API_KEY)

        self.assertEqual(result.category, RiotErrorCategory.TRANSIENT_SERVER_ERROR)
        self.assertEqual(result.attempts, 3)
        self.assertEqual(delays, [0.5, 1.0])

    def test_timeout_retries_then_succeeds(self):
        client, delays = self.make_client(
            [socket.timeout("timed out"), _FakeResponse(self.URL, {"ok": True})]
        )

        result = client.get_json(self.URL, self.API_KEY)

        self.assertEqual(result.category, RiotErrorCategory.SUCCESS)
        self.assertEqual(delays, [0.5])

    def test_repeated_timeout_is_bounded(self):
        client, delays = self.make_client(
            [socket.timeout("timed out") for _ in range(3)]
        )

        result = client.get_json(self.URL, self.API_KEY)

        self.assertEqual(result.category, RiotErrorCategory.TIMEOUT)
        self.assertEqual(result.attempts, 3)
        self.assertEqual(delays, [0.5, 1.0])

    def test_connection_error_is_retried_and_classified(self):
        client, delays = self.make_client(
            [URLError(ConnectionRefusedError("refused")) for _ in range(3)]
        )

        result = client.get_json(self.URL, self.API_KEY)

        self.assertEqual(result.category, RiotErrorCategory.NETWORK_ERROR)
        self.assertEqual(result.attempts, 3)
        self.assertEqual(delays, [0.5, 1.0])

    def test_invalid_api_key_is_not_retried(self):
        client, delays = self.make_client(
            [_http_error(self.URL, 403, message="Forbidden")]
        )

        result = client.get_json(self.URL, self.API_KEY)

        self.assertEqual(result.category, RiotErrorCategory.AUTH_ERROR)
        self.assertEqual(result.attempts, 1)
        self.assertEqual(result.message, "Riot API key is invalid or expired.")
        self.assertEqual(delays, [])

    def test_unrelated_403_remains_forbidden_not_auth_error(self):
        client, delays = self.make_client(
            [_http_error(self.URL, 403, message="Product access denied")]
        )

        result = client.get_json(self.URL, self.API_KEY)

        self.assertEqual(result.category, RiotErrorCategory.FORBIDDEN)
        self.assertEqual(result.attempts, 1)
        self.assertEqual(delays, [])

    def test_404_is_not_retried(self):
        client, delays = self.make_client([_http_error(self.URL, 404)])

        result = client.get_json(self.URL, self.API_KEY)

        self.assertEqual(result.category, RiotErrorCategory.NOT_FOUND)
        self.assertEqual(result.attempts, 1)
        self.assertEqual(delays, [])

    def test_cancellation_interrupts_backoff(self):
        cancel = _CancelDuringWait()
        client, delays = self.make_client(
            [_http_error(self.URL, 503), _FakeResponse(self.URL, {"unexpected": True})]
        )

        result = client.get_json(self.URL, self.API_KEY, cancel_event=cancel)

        self.assertEqual(result.category, RiotErrorCategory.CANCELLED)
        self.assertEqual(result.attempts, 1)
        self.assertEqual(cancel.waits, [0.5])
        self.assertEqual(delays, [])
        self.assertEqual(client._opener.open.call_count, 1)


class RiotPublicClientRedirectContinuationTests(unittest.TestCase):
    API_KEY = "RGAPI-REDIRECT-TEST"

    def test_malformed_redirect_url_is_rejected_before_following(self):
        with _RecordingServer() as riot:
            riot.route(
                "/start",
                status=302,
                headers={"Location": "https://eun1.api.riotgames.com:bad/path"},
            )
            with patch(
                "riftsense.riot.http.require_riot_api_url",
                side_effect=_test_validator(riot.origin),
            ):
                data, status, _headers = RiotPublicClient().get_json(
                    riot.origin + "/start",
                    self.API_KEY,
                )

        self.assertIsNone(status)
        self.assertIn("Blocked non-Riot", data["status"]["message"])
        self.assertEqual(len(riot.server.requests), 1)

    def test_later_untrusted_redirect_hop_never_receives_riot_token(self):
        with (
            _RecordingServer() as first,
            _RecordingServer() as second,
            _RecordingServer() as untrusted,
        ):
            first.route(
                "/start",
                status=302,
                headers={"Location": second.origin + "/next"},
            )
            second.route(
                "/next",
                status=302,
                headers={"Location": untrusted.origin + "/capture"},
            )
            untrusted.route("/capture", payload={"unexpected": True})
            with patch(
                "riftsense.riot.http.require_riot_api_url",
                side_effect=_test_validator(first.origin, second.origin),
            ):
                data, status, _headers = RiotPublicClient().get_json(
                    first.origin + "/start",
                    self.API_KEY,
                )

        self.assertIsNone(status)
        self.assertIn("Blocked non-Riot", data["status"]["message"])
        self.assertEqual(first.server.requests[0]["riot_token"], self.API_KEY)
        self.assertEqual(second.server.requests[0]["riot_token"], self.API_KEY)
        self.assertEqual(untrusted.server.requests, [])


if __name__ == "__main__":
    unittest.main()
