import importlib.util
import os
import queue
import tempfile
import unittest
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP_PATH = ROOT / "RiftSense.py"


def load_app_module():
    os.environ["LOCALAPPDATA"] = tempfile.mkdtemp(prefix="riftsense-rune-api-test-")
    spec = importlib.util.spec_from_file_location("riftsense_rune_api_test", APP_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class Value:
    def __init__(self, value=""):
        self.value = value

    def get(self):
        return self.value

    def set(self, value):
        self.value = value


class Button:
    def configure(self, **_kwargs):
        return None


class RuneAndApiRegressionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.m = load_app_module()

    def test_strip_persisted_secrets_removes_every_legacy_key_name(self):
        m = self.m
        payload = {
            "api_key": "a",
            "riot_api_key": "b",
            "riotApiKey": "c",
            "riot_id": "Player#TAG",
        }
        self.assertTrue(m.strip_persisted_secrets(payload))
        self.assertEqual(payload, {"riot_id": "Player#TAG"})
        self.assertFalse(m.strip_persisted_secrets(payload))

    def test_save_settings_strips_legacy_api_secrets(self):
        m = self.m
        m.SETTINGS["api_key"] = "legacy-session-secret"
        m.SETTINGS["riot_api_key"] = "legacy-test"
        m.SETTINGS["riotApiKey"] = "legacy-test-2"
        self.assertTrue(m.save_settings())
        saved = m.load_json(m.SETTINGS_PATH, {})
        self.assertNotIn("api_key", saved)
        self.assertNotIn("riot_api_key", saved)
        self.assertNotIn("riotApiKey", saved)

    def test_backup_sanitizes_legacy_api_secrets(self):
        m = self.m
        with tempfile.TemporaryDirectory(prefix="riftsense-backup-secret-test-") as temp_dir:
            root = Path(temp_dir)
            settings_path = root / "settings.json"
            history_dir = root / "history"
            history_dir.mkdir(parents=True, exist_ok=True)
            riot_account_path = history_dir / "riot_account.json"
            player_memory_path = root / "player_memory.json"
            performance_history_path = root / "performance_history.json"
            rank_progress_path = root / "rank_progress.json"
            ai_reviews_dir = root / "ai_reviews"
            ai_reviews_dir.mkdir(parents=True, exist_ok=True)

            settings_path.write_text(
                '{"riot_id":"Player#TAG","api_key":"RGAPI-LEGACY-SETTINGS"}',
                encoding="utf-8",
            )
            riot_account_path.write_text(
                '{"puuid":"abc","riot_api_key":"RGAPI-LEGACY-ACCOUNT"}',
                encoding="utf-8",
            )

            names = (
                "SETTINGS_PATH",
                "HISTORY_DIR",
                "RIOT_ACCOUNT_PATH",
                "PLAYER_MEMORY_PATH",
                "PERFORMANCE_HISTORY_PATH",
                "RANK_PROGRESS_PATH",
                "AI_REVIEWS_DIR",
            )
            old_values = {name: getattr(m, name) for name in names}
            try:
                m.SETTINGS_PATH = settings_path
                m.HISTORY_DIR = history_dir
                m.RIOT_ACCOUNT_PATH = riot_account_path
                m.PLAYER_MEMORY_PATH = player_memory_path
                m.PERFORMANCE_HISTORY_PATH = performance_history_path
                m.RANK_PROGRESS_PATH = rank_progress_path
                m.AI_REVIEWS_DIR = ai_reviews_dir

                destination = root / "backup.zip"
                m.App._write_user_backup_zip(object(), destination)
                with zipfile.ZipFile(destination, "r") as archive:
                    settings_text = archive.read("settings.json").decode("utf-8")
                    account_text = archive.read("history/riot_account.json").decode("utf-8")

                self.assertNotIn("RGAPI-", settings_text)
                self.assertNotIn("api_key", settings_text)
                self.assertNotIn("RGAPI-", account_text)
                self.assertNotIn("riot_api_key", account_text)
                self.assertIn("Player#TAG", settings_text)
                self.assertIn("abc", account_text)
            finally:
                for name, value in old_values.items():
                    setattr(m, name, value)

    def test_dynamic_managed_rune_page_name(self):
        class Dummy:
            _managed_rune_page_name = self.m.App._managed_rune_page_name
            _find_managed_rune_page = self.m.App._find_managed_rune_page

        dummy = Dummy()
        self.assertEqual(
            dummy._managed_rune_page_name("Nocturne"),
            "RiftSense - Nocturne",
        )
        existing = dummy._find_managed_rune_page(
            [{"id": 7, "name": "RiftSense - Wukong"}],
            champion="Nocturne",
        )
        self.assertEqual(existing["id"], 7)

    def test_off_role_rune_worker_cannot_fall_back_to_jungle_profile(self):
        m = self.m
        champion = next(
            (name for name, profile in m.RUNE_PROFILES.items() if (profile or {}).get("recommended")),
            None,
        )
        self.assertIsNotNone(champion)
        self.assertTrue(m.rune_choices_for(champion)["recommended"])
        self.assertFalse(m.rune_choices_for_role(champion, "MID")["recommended"])

        class Dummy:
            current_rune_champion = champion
            current_rune_role = "MID"
            # Simulate a stale jungle choice still visible in memory. The
            # background worker must reject it for MID before touching LCU.
            current_rune_choices = m.rune_choices_for(champion)
            dd = type("DD", (), {"rune_name_to_id": {}, "version": None})()

            def __init__(self):
                self.events = []

            def _rune_import_post(self, payload):
                self.events.append(payload)

        dummy = Dummy()
        m.App._rune_import_worker(
            dummy,
            champion,
            "MID",
            "recommended",
            ("sig",),
        )
        messages = [event.get("message", "") for event in dummy.events]
        self.assertTrue(any("No recommended rune profile" in msg for msg in messages))
        self.assertTrue(any(event.get("type") == "finished" for event in dummy.events))

    def test_api_worker_exception_always_reaches_queue(self):
        m = self.m

        class Dummy:
            setting_riot_api_key_var = Value("RGAPI-TEST-NOT-REAL")
            setting_riot_id_var = Value("Player#EUNE")
            setting_riot_platform_var = Value("EUN1")
            setting_riot_route_var = Value("EUROPE")
            history_sync_status_var = Value("")
            setting_test_api_button = Button()
            _riot_api_test_job = None

            def _history_local_identity(self, _riot_id):
                raise RuntimeError("diagnostic boom")

            def after_cancel(self, _job):
                return None

            def after(self, _delay, _callback):
                return None

            def _watch_riot_api_test_queue(self):
                return None

        dummy = Dummy()
        m.App.test_riot_api_access(dummy)
        dummy._riot_api_test_thread.join(timeout=2.0)
        self.assertFalse(dummy._riot_api_test_thread.is_alive())
        result = dummy._riot_api_test_queue.get_nowait()
        self.assertIn("API TEST ERROR", result)
        self.assertIn("diagnostic boom", result)


if __name__ == "__main__":
    unittest.main()
