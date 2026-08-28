import unittest
from riftsense.core.security import is_allowed_local_https_url, is_allowed_riot_api_url, require_riot_api_url

class SecurityPolicyTests(unittest.TestCase):
    def test_allows_real_riot_api_hosts(self):
        self.assertTrue(is_allowed_riot_api_url("https://eun1.api.riotgames.com/lol/league/v4/entries"))
        self.assertTrue(is_allowed_riot_api_url("https://europe.api.riotgames.com/lol/match/v5/matches/x"))
    def test_blocks_lookalikes(self):
        for url in ["http://eun1.api.riotgames.com/x","https://api.riotgames.com.evil.example/x","https://evil.example/x","https://eun1.api.riotgames.com:8443/x","https://eun1.api.riotgames.com:bad/x"]:
            with self.subTest(url=url):
                self.assertFalse(is_allowed_riot_api_url(url))
                with self.assertRaises(ValueError): require_riot_api_url(url)
    def test_localhost_only(self):
        self.assertTrue(is_allowed_local_https_url("https://127.0.0.1:2999/x",allowed_ports={2999}))
        self.assertFalse(is_allowed_local_https_url("https://192.168.1.5:2999/x",allowed_ports={2999}))
