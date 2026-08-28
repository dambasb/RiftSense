import json
import unittest
from unittest.mock import patch
from riftsense.riot.local_client import LCUClient, get_live_player_scores
class LocalClientTests(unittest.TestCase):
    def test_blocks_non_perks_write(self):
        c=LCUClient({}); _d,_s,e=c.write_json("/lol-chat/v1/conversations",{},method="POST"); self.assertIn("endpoint blocked",e)
    def test_blocks_wrong_method(self):
        c=LCUClient({}); _d,_s,e=c.write_json("/lol-perks/v1/pages",{},method="PATCH"); self.assertIn("method blocked",e)


class _FakeResponse:
    status = 200
    def __enter__(self): return self
    def __exit__(self, *_args): return False
    def read(self): return json.dumps({"kills": 2, "deaths": 1, "assists": 4, "creepScore": 87}).encode("utf-8")


class LiveScoresTests(unittest.TestCase):
    @patch("riftsense.riot.local_client.urlopen", return_value=_FakeResponse())
    def test_player_scores_encodes_riot_id_fragment(self, mocked_urlopen):
        scores = get_live_player_scores("Enemy Jungler#EUNE")
        self.assertEqual(scores["creepScore"], 87)
        request = mocked_urlopen.call_args.args[0]
        self.assertIn("riotId=Enemy%20Jungler%23EUNE", request.full_url)
        self.assertNotIn("#EUNE", request.full_url)
