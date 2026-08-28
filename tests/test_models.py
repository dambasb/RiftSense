import unittest
from riftsense.core.models import DraftSuggestion, RankEntry
class ModelTests(unittest.TestCase):
    def test_rank_entry(self):
        r=RankEntry.from_mapping({"tier":"gold","rank":"ii","league_points":73}); self.assertEqual((r.tier,r.division,r.league_points),("GOLD","II",73))
    def test_draft_tuple_compat(self):
        d=DraftSuggestion(8.0,"Nocturne",["fit"],{}, {"source":"MY_POOL"}); self.assertEqual(d[1],"Nocturne"); self.assertEqual(tuple(d)[4]["source"],"MY_POOL")
