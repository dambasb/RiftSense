import json
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from unittest.mock import patch
from urllib.parse import urlparse

from riftsense.core.security import require_riot_api_url
from riftsense.riot.http import RiotPublicClient


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
