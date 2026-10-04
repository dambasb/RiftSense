import importlib.util
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
APP_PATH = ROOT / "RiftSense.py"


def load_app_module():
    local_data = tempfile.mkdtemp(prefix="riftsense-migration-import-data-")
    fake_home = Path(tempfile.mkdtemp(prefix="riftsense-migration-home-"))
    (fake_home / "Downloads").mkdir()
    (fake_home / "Desktop").mkdir()
    os.environ["LOCALAPPDATA"] = local_data
    with patch("pathlib.Path.home", return_value=fake_home):
        spec = importlib.util.spec_from_file_location(
            "riftsense_legacy_migration_test",
            APP_PATH,
        )
        module = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        spec.loader.exec_module(module)
        return module


class LegacyMigrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.m = load_app_module()

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory(prefix="riftsense-migration-test-")
        self.root = Path(self.temp_dir.name)
        self.current = self.root / "current"
        self.legacy_one = self.root / "RiftBuildAssistant-old-one"
        self.legacy_two = self.root / "RiftBuildAssistant-old-two"
        self.legacy_one.mkdir()
        self.legacy_two.mkdir()

        names = (
            "DATA_DIR",
            "SETTINGS_PATH",
            "HISTORY_DIR",
            "CACHE_DIR",
            "LEGACY_MIGRATION_MARKER_PATH",
        )
        self.old_paths = {
            name: getattr(self.m, name)
            for name in names
        }
        self.m.DATA_DIR = self.current
        self.m.SETTINGS_PATH = self.current / "settings.json"
        self.m.HISTORY_DIR = self.current / "history"
        self.m.CACHE_DIR = self.current / "cache"
        self.m.LEGACY_MIGRATION_MARKER_PATH = self.current / "legacy_migration.json"

    def tearDown(self):
        for name, value in self.old_paths.items():
            setattr(self.m, name, value)
        self.temp_dir.cleanup()

    @staticmethod
    def write_json(path, payload):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload), encoding="utf-8")

    def marker(self):
        return json.loads(
            self.m.LEGACY_MIGRATION_MARKER_PATH.read_text(encoding="utf-8")
        )

    def test_missing_destination_file_is_migrated(self):
        source = self.legacy_one / "settings.json"
        self.write_json(source, {"theme": "legacy"})

        self.assertTrue(self.m.migrate_legacy_user_data([self.legacy_one]))

        self.assertEqual(
            json.loads(self.m.SETTINGS_PATH.read_text(encoding="utf-8")),
            {"theme": "legacy"},
        )
        self.assertTrue(self.m.LEGACY_MIGRATION_MARKER_PATH.exists())

    def test_existing_destination_file_is_not_overwritten(self):
        self.write_json(self.m.SETTINGS_PATH, {"theme": "current"})
        self.write_json(self.legacy_one / "settings.json", {"theme": "legacy"})

        self.assertTrue(self.m.migrate_legacy_user_data([self.legacy_one]))

        self.assertEqual(
            json.loads(self.m.SETTINGS_PATH.read_text(encoding="utf-8")),
            {"theme": "current"},
        )
        conflicts = self.marker()["skipped_conflicts"]
        self.assertEqual(conflicts[0]["path"], "settings.json")

    def test_nested_destination_file_is_not_overwritten(self):
        destination = self.m.HISTORY_DIR / "riot" / "match.json"
        source = self.legacy_one / "history" / "riot" / "match.json"
        self.write_json(destination, {"owner": "current"})
        self.write_json(source, {"owner": "legacy"})

        self.assertTrue(self.m.migrate_legacy_user_data([self.legacy_one]))

        self.assertEqual(
            json.loads(destination.read_text(encoding="utf-8")),
            {"owner": "current"},
        )
        self.assertIn(
            "history/riot/match.json",
            [row["path"] for row in self.marker()["skipped_conflicts"]],
        )

    def test_first_legacy_source_wins_when_both_have_same_file(self):
        first = self.legacy_one / "cache" / "shared.json"
        second = self.legacy_two / "cache" / "shared.json"
        self.write_json(first, {"source": "first"})
        self.write_json(second, {"source": "second"})

        self.assertTrue(
            self.m.migrate_legacy_user_data([self.legacy_one, self.legacy_two])
        )

        destination = self.m.CACHE_DIR / "shared.json"
        self.assertEqual(
            json.loads(destination.read_text(encoding="utf-8")),
            {"source": "first"},
        )
        conflicts = self.marker()["skipped_conflicts"]
        self.assertEqual(conflicts, [{"source": self.legacy_two.name, "path": "cache/shared.json"}])

    def test_current_destination_wins_over_all_legacy_sources(self):
        destination = self.m.CACHE_DIR / "shared.json"
        self.write_json(destination, {"source": "current"})
        self.write_json(
            self.legacy_one / "cache" / "shared.json",
            {"source": "first"},
        )
        self.write_json(
            self.legacy_two / "cache" / "shared.json",
            {"source": "second"},
        )

        self.assertTrue(
            self.m.migrate_legacy_user_data([self.legacy_one, self.legacy_two])
        )

        self.assertEqual(
            json.loads(destination.read_text(encoding="utf-8")),
            {"source": "current"},
        )
        self.assertEqual(len(self.marker()["skipped_conflicts"]), 2)

    def test_completed_marker_prevents_migration_from_running_again(self):
        first = self.legacy_one / "history" / "first.json"
        second = self.legacy_one / "history" / "second.json"
        self.write_json(first, {"value": 1})
        self.assertTrue(self.m.migrate_legacy_user_data([self.legacy_one]))
        self.write_json(second, {"value": 2})

        with patch.object(
            self.m,
            "_legacy_data_candidates",
            side_effect=AssertionError("discovery must not run after completion"),
        ):
            self.assertTrue(self.m.migrate_legacy_user_data())

        self.assertFalse((self.m.HISTORY_DIR / "second.json").exists())

    def test_partial_failure_does_not_write_completion_marker(self):
        good = self.legacy_one / "history" / "good.json"
        bad = self.legacy_one / "history" / "bad.json"
        self.write_json(good, {"value": "good"})
        self.write_json(bad, {"value": "bad"})
        original = self.m._copy_legacy_file_if_missing

        def fail_bad(source, destination):
            if Path(source).name == "bad.json":
                return "failed", "forced copy failure"
            return original(source, destination)

        with patch.object(
            self.m,
            "_copy_legacy_file_if_missing",
            side_effect=fail_bad,
        ):
            self.assertFalse(self.m.migrate_legacy_user_data([self.legacy_one]))

        self.assertTrue((self.m.HISTORY_DIR / "good.json").exists())
        self.assertFalse((self.m.HISTORY_DIR / "bad.json").exists())
        self.assertFalse(self.m.LEGACY_MIGRATION_MARKER_PATH.exists())

    def test_retry_after_partial_failure_is_safe(self):
        good = self.legacy_one / "history" / "good.json"
        retry = self.legacy_one / "history" / "retry.json"
        self.write_json(good, {"value": "first copy"})
        self.write_json(retry, {"value": "retry"})
        original = self.m._copy_legacy_file_if_missing

        def fail_retry(source, destination):
            if Path(source).name == "retry.json":
                return "failed", "forced copy failure"
            return original(source, destination)

        with patch.object(
            self.m,
            "_copy_legacy_file_if_missing",
            side_effect=fail_retry,
        ):
            self.assertFalse(self.m.migrate_legacy_user_data([self.legacy_one]))

        self.write_json(good, {"value": "changed legacy value"})
        self.assertTrue(self.m.migrate_legacy_user_data([self.legacy_one]))

        self.assertEqual(
            json.loads((self.m.HISTORY_DIR / "good.json").read_text(encoding="utf-8")),
            {"value": "first copy"},
        )
        self.assertEqual(
            json.loads((self.m.HISTORY_DIR / "retry.json").read_text(encoding="utf-8")),
            {"value": "retry"},
        )
        self.assertTrue(self.m.LEGACY_MIGRATION_MARKER_PATH.exists())

    def test_running_migration_twice_is_idempotent(self):
        source = self.legacy_one / "cache" / "value.json"
        self.write_json(source, {"value": 1})
        self.assertTrue(self.m.migrate_legacy_user_data([self.legacy_one]))
        destination = self.m.CACHE_DIR / "value.json"
        first_destination = destination.read_bytes()
        first_marker = self.m.LEGACY_MIGRATION_MARKER_PATH.read_bytes()

        self.assertTrue(self.m.migrate_legacy_user_data([self.legacy_one]))

        self.assertEqual(destination.read_bytes(), first_destination)
        self.assertEqual(self.m.LEGACY_MIGRATION_MARKER_PATH.read_bytes(), first_marker)

    def test_legacy_source_remains_untouched(self):
        source = self.legacy_one / "history" / "nested" / "source.json"
        self.write_json(source, {"preserve": True})
        before = source.read_bytes()

        self.assertTrue(self.m.migrate_legacy_user_data([self.legacy_one]))

        self.assertEqual(source.read_bytes(), before)
        self.assertTrue(source.exists())

    def test_malformed_json_is_not_migrated_or_marked_complete(self):
        current = self.m.HISTORY_DIR / "current.json"
        malformed = self.legacy_one / "history" / "broken.json"
        self.write_json(current, {"keep": True})
        malformed.parent.mkdir(parents=True, exist_ok=True)
        malformed.write_text("{broken", encoding="utf-8")

        self.assertFalse(self.m.migrate_legacy_user_data([self.legacy_one]))

        self.assertEqual(
            json.loads(current.read_text(encoding="utf-8")),
            {"keep": True},
        )
        self.assertFalse((self.m.HISTORY_DIR / "broken.json").exists())
        self.assertFalse(self.m.LEGACY_MIGRATION_MARKER_PATH.exists())


if __name__ == "__main__":
    unittest.main()
