import importlib.util, os, tempfile, unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; APP=ROOT/"RiftSense.py"
def load_app():
    os.environ["LOCALAPPDATA"]=tempfile.mkdtemp(prefix="rs-test-")
    spec=importlib.util.spec_from_file_location("rs_test",APP); m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m
class DD:
    def champion_tags(self,name): return ["Mage"] if name in {"Ahri","Annie","Orianna","Syndra","Viktor","Lux"} else ["Fighter"]
    def champion_name(self,v): return str(v or "")
class DraftTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.m=load_app(); cls.dd=DD()
    def setUp(self):
        self.m.SETTINGS["champion_pool"]=["Nocturne","Wukong","Jarvan IV","Amumu"]
        self.m.SETTINGS["champion_pool_by_role"]={"TOP":[],"JUNGLE":["Nocturne","Wukong","Jarvan IV","Amumu"],"MID":[],"ADC":[],"SUPPORT":[]}
    def test_banned_excluded(self):
        rows=self.m.rank_draft_picks("jungle",[],[],self.dd,excluded_names=["Nocturne"],pick_context={"key":"BLIND","label":"SAFE PICK","detail":"","enemy":""}); self.assertNotIn("Nocturne",[r.champion for r in rows]); self.assertEqual(len(rows),3)
    def test_fallback(self):
        rows=self.m.rank_draft_picks("middle",[],[],self.dd,excluded_names=[],pick_context={"key":"BLIND","label":"SAFE PICK","detail":"","enemy":""}); self.assertTrue(all(r.relationships["source"]=="ROLE_FALLBACK" for r in rows))
    def test_unknown_waits(self): self.assertEqual(self.m.rank_draft_picks("",[],[],self.dd,excluded_names=[]),[])

    def test_regional_riot_route_host(self):
        self.assertEqual(self.m.riot_route_host("EUROPE"), "europe")
        self.assertEqual(self.m.riot_route_host("AMERICAS"), "americas")
        self.assertEqual(self.m.riot_route_host("ASIA"), "asia")
        self.assertEqual(self.m.riot_route_host("SEA"), "sea")
        self.assertEqual(self.m.riot_route_host("unknown"), "europe")

    def test_off_role_loadout_never_suggests_smite(self):
        loadout = self.m.draft_loadout_for(
            "Ahri",
            [],
            self.dd,
            role="MID",
        )
        self.assertNotIn("Smite", loadout["summoners"])
        self.assertIn("role", loadout["note"].lower())

    def test_flat_rune_profiles_are_jungle_only(self):
        jungle = self.m.rune_choices_for_role("Nocturne", "JUNGLE")
        mid = self.m.rune_choices_for_role("Nocturne", "MID")
        self.assertTrue(jungle["recommended"])
        self.assertFalse(mid["recommended"])
        self.assertFalse(mid["alternative"])

    def test_meta_refresh_rejects_non_jungle_without_network(self):
        payload, errors = self.m.refresh_meta_consensus(
            "Ahri",
            self.dd,
            role="MID",
        )
        self.assertEqual(payload, {})
        self.assertTrue(errors)
        self.assertIn("jungle-only", errors[0].lower())

    def test_fresh_install_auto_rune_import_is_opt_in(self):
        self.assertFalse(self.m.DEFAULT_SETTINGS["auto_import_runes"])
    def test_duplicate_item_names_prefer_normal_summoners_rift_variant(self):
        dd = self.m.DataDragon()
        # Deliberately put the mode-specific duplicate last to reproduce the
        # ordering hazard present in current Data Dragon (for example BORK).
        dd.item_data = {
            "3153": {
                "name": "Blade of The Ruined King",
                "gold": {"purchasable": True, "total": 3200},
                "maps": {"11": True, "30": False},
            },
            "773153": {
                "name": "Blade of The Ruined King",
                "gold": {"purchasable": True, "total": 2900},
                "maps": {"11": False, "453": True},
            },
        }
        dd._rebuild_item_name_index()
        self.assertEqual(dd.item_id_for_name("Blade of The Ruined King"), "3153")
        self.assertEqual(
            self.m.current_sr_item_id(dd, "Blade of The Ruined King", require_completed=True),
            "3153",
        )

    def test_recommendation_candidates_contain_no_generic_boot_placeholder(self):
        candidates = self.m.recommendation_item_candidates()
        self.assertNotIn("defensive boots", {name.lower() for name in candidates})


    def test_localized_smite_uses_raw_riot_identifier(self):
        player = {
            "summonerSpells": {
                "summonerSpellOne": {
                    "displayName": "Localized Jungle Spell",
                    "rawDisplayName": "GeneratedTip_SummonerSpell_SummonerSmite_DisplayName",
                    "description": "Localized description",
                },
                "summonerSpellTwo": {"displayName": "Flash"},
            }
        }
        self.assertTrue(self.m.player_has_smite(player))

    def test_enemy_jungle_mapping_prefers_smite_not_array_order(self):
        top = {"championName": "Darius", "position": "TOP", "scores": {"creepScore": 121}, "summonerSpells": {}}
        mid = {"championName": "Ahri", "position": "MIDDLE", "scores": {"creepScore": 133}, "summonerSpells": {}}
        jungle = {
            "championName": "Lee Sin",
            "position": "",
            "scores": {"creepScore": 87},
            "summonerSpells": {
                "summonerSpellOne": {"displayName": "Flash"},
                "summonerSpellTwo": {
                    "displayName": "Localized",
                    "rawDisplayName": "GeneratedTip_SummonerSpell_SummonerSmite_DisplayName",
                },
            },
        }
        adc = {"championName": "Jinx", "position": "BOTTOM", "scores": {"creepScore": 140}, "summonerSpells": {}}
        support = {"championName": "Nautilus", "position": "UTILITY", "scores": {"creepScore": 21}, "summonerSpells": {}}
        mapping = self.m.lane_player_map([top, mid, adc, support, jungle])
        self.assertIs(mapping.get("JUNGLE"), jungle)
        self.assertEqual(self.m.score_line(mapping["JUNGLE"])[3], 87)

    def test_jungle_is_never_guessed_from_player_order(self):
        players = [
            {"championName": "A", "position": "TOP", "summonerSpells": {}},
            {"championName": "B", "position": "MIDDLE", "summonerSpells": {}},
            {"championName": "C", "position": "BOTTOM", "summonerSpells": {}},
            {"championName": "D", "position": "UTILITY", "summonerSpells": {}},
            {"championName": "E", "position": "", "summonerSpells": {}},
        ]
        mapping = self.m.lane_player_map(players)
        self.assertNotIn("JUNGLE", mapping)


    def test_poll_worker_refreshes_enemy_jungler_scores(self):
        m = self.m
        active = {
            "riotId": "Me#EUNE",
            "team": "ORDER",
            "championName": "Nocturne",
            "position": "JUNGLE",
            "scores": {"creepScore": 72},
            "summonerSpells": {
                "summonerSpellOne": {"rawDisplayName": "GeneratedTip_SummonerSpell_SummonerSmite_DisplayName"},
            },
        }
        enemy_jungle = {
            "riotId": "Enemy Jungler#EUNE",
            "team": "CHAOS",
            "championName": "Lee Sin",
            "position": "",
            "scores": {"creepScore": 41},
            "summonerSpells": {
                "summonerSpellTwo": {"rawDisplayName": "GeneratedTip_SummonerSpell_SummonerSmite_DisplayName"},
            },
        }
        enemy_top = {
            "riotId": "Enemy Top#EUNE",
            "team": "CHAOS",
            "championName": "Darius",
            "position": "TOP",
            "scores": {"creepScore": 121},
            "summonerSpells": {},
        }
        live_data = {
            "activePlayer": {"riotId": "Me#EUNE"},
            "allPlayers": [active, enemy_top, enemy_jungle],
        }

        class FakeLCU:
            def get(self, *_args, **_kwargs):
                return None, None

        class Dummy:
            _poll_sources_worker = m.App._poll_sources_worker
            def __init__(self):
                import queue
                self.lcu = FakeLCU()
                self._poll_queue = queue.Queue(maxsize=1)

        original_game = m.get_live_game_data
        original_scores = m.get_live_player_scores
        try:
            m.get_live_game_data = lambda: live_data
            m.get_live_player_scores = lambda riot_id, timeout=0.45: (
                {"kills": 3, "deaths": 2, "assists": 5, "creepScore": 88}
                if riot_id == "Enemy Jungler#EUNE"
                else None
            )
            dummy = Dummy()
            dummy._poll_sources_worker()
            _session, _status, refreshed, _completed = dummy._poll_queue.get_nowait()
            mapping = m.lane_player_map([
                player for player in refreshed["allPlayers"]
                if player.get("team") == "CHAOS"
            ])
            self.assertEqual(mapping["JUNGLE"]["scores"]["creepScore"], 88)
            self.assertEqual(mapping["JUNGLE"]["scores"]["kills"], 3)
        finally:
            m.get_live_game_data = original_game
            m.get_live_player_scores = original_scores

    def test_api_status_hint(self):
        self.assertIn("expired", self.m.riot_api_status_hint(403).lower())
        self.assertIn("rate limit", self.m.riot_api_status_hint(429).lower())
        self.assertEqual(self.m.riot_api_status_hint(200), "")
