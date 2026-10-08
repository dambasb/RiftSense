import importlib.util
import os
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from riftsense.core.identity import (
    IdentityDecision,
    IdentityStrength,
    resolve_champion_select_player,
    resolve_player_identity,
)


ROOT = Path(__file__).resolve().parents[1]
APP_PATH = ROOT / "RiftSense.py"


def load_app_module():
    os.environ["LOCALAPPDATA"] = tempfile.mkdtemp(prefix="riftsense-identity-data-")
    spec = importlib.util.spec_from_file_location("riftsense_identity_test", APP_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class IdentityResolutionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.m = load_app_module()

    def test_exact_puuid_matches(self):
        candidate = {"puuid": "PUUID-A", "summonerName": "Current"}
        result = resolve_player_identity(
            {"puuid": "PUUID-A", "summonerName": "Old"},
            [candidate],
        )
        self.assertEqual(result.decision, IdentityDecision.MATCH)
        self.assertEqual(result.strength, IdentityStrength.PUUID)
        self.assertIs(result.candidate, candidate)

    def test_conflicting_puuid_beats_same_display_name(self):
        result = resolve_player_identity(
            {"puuid": "PUUID-A", "summonerName": "Player"},
            [{"puuid": "PUUID-B", "summonerName": "Player"}],
        )
        self.assertEqual(result.decision, IdentityDecision.NO_MATCH)
        self.assertEqual(result.reason, "PUUID_CONFLICT")

    def test_exact_complete_riot_id_matches_without_puuid(self):
        candidate = {"riotIdGameName": "Player", "riotIdTagLine": "EUW"}
        result = resolve_player_identity(
            {"riotId": " player # euw "},
            [candidate],
        )
        self.assertEqual(result.decision, IdentityDecision.MATCH)
        self.assertEqual(result.strength, IdentityStrength.RIOT_ID)
        self.assertIs(result.candidate, candidate)

    def test_different_tag_line_does_not_match(self):
        result = resolve_player_identity(
            {"riotId": "Player#EUW"},
            [{"riotId": "Player#EUNE"}],
        )
        self.assertEqual(result.decision, IdentityDecision.NO_MATCH)
        self.assertEqual(result.reason, "RIOT_ID_CONFLICT")

    def test_unique_weak_name_is_explicitly_weak(self):
        candidate = {"summonerName": "Player"}
        result = resolve_player_identity(
            {"summonerName": "player"},
            [candidate, {"summonerName": "Other"}],
        )
        self.assertEqual(result.decision, IdentityDecision.MATCH)
        self.assertEqual(result.strength, IdentityStrength.WEAK_NAME)
        self.assertEqual(result.reason, "UNIQUE_WEAK_NAME")

    def test_weak_name_collision_is_ambiguous(self):
        result = resolve_player_identity(
            {"summonerName": "Player"},
            [{"summonerName": "Player"}, {"displayName": "player"}],
        )
        self.assertEqual(result.decision, IdentityDecision.AMBIGUOUS)
        self.assertEqual(result.reason, "MULTIPLE_WEAK_NAME_MATCHES")

    def test_weak_game_name_collision_across_different_tags_is_ambiguous(self):
        result = resolve_player_identity(
            {"summonerName": "Player"},
            [{"riotId": "Player#EUW"}, {"riotId": "Player#EUNE"}],
        )
        self.assertEqual(result.decision, IdentityDecision.AMBIGUOUS)
        self.assertEqual(result.strength, IdentityStrength.WEAK_NAME)

    def test_puuid_selects_a_when_weak_name_points_to_b(self):
        player_a = {"puuid": "A", "summonerName": "Renamed"}
        player_b = {"puuid": "B", "summonerName": "OldName"}
        result = resolve_player_identity(
            {"puuid": "A", "summonerName": "OldName"},
            [player_b, player_a],
        )
        self.assertIs(result.candidate, player_a)
        self.assertEqual(result.reason, "PUUID_EXACT")

    def test_riot_id_rename_and_stale_name_remain_same_puuid(self):
        candidate = {"puuid": "A", "riotId": "NewName#TAG"}
        result = resolve_player_identity(
            {"puuid": "A", "riotId": "OldName#OLD"},
            [candidate],
        )
        self.assertEqual(result.decision, IdentityDecision.MATCH)
        self.assertIs(result.candidate, candidate)

    def test_champion_select_uses_unique_authoritative_local_cell(self):
        local = {"cellId": 7, "championId": 1}
        result = resolve_champion_select_player(
            {"localPlayerCellId": 7, "myTeam": [{"cellId": 1}, local]}
        )
        self.assertEqual(result.decision, IdentityDecision.MATCH)
        self.assertEqual(result.strength, IdentityStrength.SESSION)
        self.assertIs(result.candidate, local)

    def test_champion_select_duplicate_local_cell_is_ambiguous(self):
        result = resolve_champion_select_player(
            {"localPlayerCellId": 7, "myTeam": [{"cellId": 7}, {"cellId": 7}]}
        )
        self.assertEqual(result.decision, IdentityDecision.AMBIGUOUS)
        self.assertEqual(result.reason, "DUPLICATE_LOCAL_PLAYER_CELL")

    def test_live_game_weak_collision_never_selects_first_player(self):
        data = {
            "activePlayer": {"summonerName": "Player"},
            "allPlayers": [
                {"summonerName": "Player", "championName": "Wrong"},
                {"summonerName": "Player", "championName": "AlsoWrong"},
            ],
        }
        result = self.m.resolve_active_player(data)
        self.assertEqual(result.decision, IdentityDecision.AMBIGUOUS)
        self.assertIsNone(self.m.find_active_player(data))

    def test_player_score_endpoint_identifier_rejects_weak_name_only(self):
        self.assertEqual(
            self.m.player_live_identifier({"summonerName": "Player"}),
            "",
        )

    def test_history_identity_accepts_same_puuid_after_riot_id_rename(self):
        saved = {"puuid": "A", "riot_id": "OldName#TAG"}
        current = {"puuid": "A", "gameName": "NewName", "tagLine": "TAG"}
        app = SimpleNamespace(
            lcu=SimpleNamespace(get=lambda *_args, **_kwargs: (current, 200)),
        )
        with patch.object(self.m, "load_json", return_value=saved):
            result = self.m.App._history_local_identity(app, "OldName#TAG")
        self.assertEqual(result["puuid"], "A")
        self.assertEqual(result["riot_id"], "NewName#TAG")

    def test_history_weak_display_cannot_override_puuid_conflict(self):
        saved = {"puuid": "A", "riot_id": "Player#TAG"}
        current = {"puuid": "B", "displayName": "Player"}
        app = SimpleNamespace(
            lcu=SimpleNamespace(get=lambda *_args, **_kwargs: (current, 200)),
        )
        with patch.object(self.m, "load_json", return_value=saved):
            result = self.m.App._history_local_identity(app, "Player#TAG")
        self.assertIn("error", result)

    def test_match_history_uses_exact_puuid_despite_same_names(self):
        match = {
            "metadata": {"matchId": "TEST"},
            "info": {
                "participants": [
                    {"puuid": "B", "summonerName": "Player", "championName": "Wrong"},
                    {"puuid": "A", "summonerName": "Player", "championName": "Correct"},
                ]
            },
        }
        summary = self.m.riot_match_summary(match, "A")
        self.assertEqual(summary["champion"], "Correct")
        self.assertEqual(summary["account_puuid"], "A")

    def test_player_memory_without_current_puuid_fails_closed(self):
        app = SimpleNamespace()
        with patch.object(self.m, "load_json", return_value={}):
            rows = self.m.App._player_memory_source_rows(app)
        self.assertEqual(rows, [])

    def test_untagged_legacy_history_requires_recorded_owner(self):
        app = SimpleNamespace()
        loads = iter([
            {"puuid": "A"},
            {},
        ])
        with (
            patch.object(self.m, "load_json", side_effect=lambda *_args: next(loads)),
            patch.object(
                self.m,
                "load_riot_history_index",
                return_value=[{"queue_id": 420, "game_creation_ms": 1}],
            ),
            patch.object(self.m, "is_ranked_row_in_scope", return_value=True),
        ):
            rows = self.m.App._player_memory_source_rows(app)
        self.assertEqual(rows, [])

    def test_rank_progress_follows_puuid_across_riot_id_rename(self):
        rows = [
            {"riot_id": "OldName#TAG", "account_puuid": "A", "solo": {"tier": "GOLD"}},
            {"riot_id": "NewName#TAG", "account_puuid": "A", "solo": {"tier": "PLATINUM"}},
            {"riot_id": "NewName#TAG", "account_puuid": "B", "solo": {"tier": "SILVER"}},
            {"riot_id": "NewName#TAG", "solo": {"tier": "BRONZE"}},
        ]
        with patch.object(self.m, "load_json", return_value=rows):
            result = self.m.load_rank_progress("NewName#TAG", "A")
        self.assertEqual(
            [row["solo"]["tier"] for row in result],
            ["GOLD", "PLATINUM", "BRONZE"],
        )

    def test_performance_snapshot_carries_account_puuid(self):
        app = SimpleNamespace()
        snapshot = self.m.App._performance_snapshot(
            app,
            {"account": {"puuid": "A"}, "summary": {}},
        )
        self.assertEqual(snapshot["account_puuid"], "A")


if __name__ == "__main__":
    unittest.main()
