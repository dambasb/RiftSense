import importlib.util
import json
import os
import queue
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
APP_PATH = ROOT / "RiftSense.py"


def load_app_module():
    local_data = tempfile.mkdtemp(prefix="riftsense-static-data-import-")
    fake_home = Path(tempfile.mkdtemp(prefix="riftsense-static-home-"))
    (fake_home / "Downloads").mkdir()
    (fake_home / "Desktop").mkdir()
    os.environ["LOCALAPPDATA"] = local_data
    with patch("pathlib.Path.home", return_value=fake_home):
        spec = importlib.util.spec_from_file_location(
            "riftsense_static_data_test",
            APP_PATH,
        )
        module = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        spec.loader.exec_module(module)
        return module


def catalog_bundle(suffix=""):
    return (
        {
            "data": {
                "1001": {
                    "name": f"Boots{suffix}",
                    "gold": {"total": 300, "purchasable": True},
                    "maps": {"11": True},
                }
            }
        },
        {
            "data": {
                "Ahri": {
                    "key": "103",
                    "name": f"Ahri{suffix}",
                    "tags": ["Mage"],
                }
            }
        },
        [
            {
                "id": 8000,
                "name": "Precision",
                "slots": [
                    {
                        "runes": [
                            {"id": 8005, "name": f"Press the Attack{suffix}"}
                        ]
                    }
                ],
            }
        ],
    )


class _StaticHarness:
    def __init__(self, module, dd=None):
        cls = type(self)
        for name in (
            "_start_static_data_refresh",
            "_request_static_data_refresh",
            "_apply_static_data_candidate",
            "_watch_static_data_refresh",
            "_icon_request_key",
        ):
            setattr(cls, name, getattr(module.App, name))

        self.dd = dd or module.DataDragon()
        self._static_refresh_queue = queue.Queue()
        self._static_refresh_generation = 0
        self._static_refresh_active_generation = None
        self._static_refresh_in_flight = False
        self._static_refresh_pending = None
        self._static_refresh_watch_job = None
        self._static_refresh_shutdown = False
        self._static_refresh_game_version = ""
        self._static_refresh_last_failure = 0.0
        self._icon_pending = {}
        self._icon_failures = {}
        self._poll_in_flight = False
        self.patch_status_text = self.dd.version or "-"
        self.full_build_signature = "old"
        self.adaptive_signature = "old"
        self.build_signature = "old"
        self.draft_signature = "old"
        self.enemy_inventory_signature = "old"
        self.companion_signature = "old"
        self.after_calls = []
        self.health_threads = []
        self.refresh_calls = 0

    def after(self, delay, callback):
        self.after_calls.append((delay, callback))
        return f"after-{len(self.after_calls)}"

    def update_health_bar(self):
        self.health_threads.append(threading.get_ident())

    def refresh_all(self):
        self.refresh_calls += 1

    def wait_for_result(self):
        result = self._static_refresh_queue.get(timeout=3.0)
        self._static_refresh_queue.put_nowait(result)
        return result


class StaticDataAsyncTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.m = load_app_module()

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory(
            prefix="riftsense-static-data-test-"
        )
        self.old_meta_cache = self.m.META_CACHE_DIR
        self.m.META_CACHE_DIR = Path(self.temp_dir.name)

    def tearDown(self):
        self.m.META_CACHE_DIR = self.old_meta_cache
        self.temp_dir.cleanup()

    def write_bundle(self, version, bundle=None, *, complete_marker=None):
        items, champions, runes = bundle or catalog_bundle()
        paths = self.m.DataDragon._catalog_paths(version)
        for path, payload in zip(paths, (items, champions, runes)):
            path.write_text(json.dumps(payload), encoding="utf-8")
        (self.m.META_CACHE_DIR / "versions.json").write_text(
            json.dumps([version]), encoding="utf-8"
        )
        if complete_marker is not None:
            self.m.DataDragon._bundle_marker_path(version).write_text(
                json.dumps(
                    {"version": version, "complete": complete_marker}
                ),
                encoding="utf-8",
            )

    def remote_fetcher(self, version, *, calls=None, bundle=None):
        items, champions, runes = bundle or catalog_bundle(version)

        def fetch(url, timeout=4.0):
            if calls is not None:
                calls.append((threading.get_ident(), url))
            if url.endswith("/api/versions.json"):
                return [version]
            if url.endswith("/item.json"):
                return items
            if url.endswith("/champion.json"):
                return champions
            if url.endswith("/runesReforged.json"):
                return runes
            raise AssertionError(f"unexpected URL: {url}")

        return fetch

    def test_valid_local_cache_loads_without_remote_access(self):
        self.write_bundle("16.20.1")
        dd = self.m.DataDragon()

        with patch.object(
            self.m,
            "fetch_json",
            side_effect=AssertionError("cache load attempted network access"),
        ):
            loaded = dd.load_cached_static_data()

        self.assertEqual(loaded, "16.20.1")
        self.assertTrue(dd.has_complete_static_data("16.20.1"))

    def test_unreachable_data_dragon_keeps_startup_state_usable(self):
        app = _StaticHarness(self.m)
        with patch.object(self.m, "fetch_json", side_effect=OSError("offline")):
            app._request_static_data_refresh("")
            app.wait_for_result()
            app._watch_static_data_refresh()

        self.assertIsInstance(app.dd, self.m.DataDragon)
        self.assertIsNone(app.dd.version)
        self.assertEqual(app.patch_status_text, "-")
        self.assertGreater(app._static_refresh_last_failure, 0.0)

    def test_background_patch_check_never_fetches_on_main_thread(self):
        calls = []
        app = _StaticHarness(self.m)
        main_thread = threading.get_ident()
        with patch.object(
            self.m,
            "fetch_json",
            side_effect=self.remote_fetcher("16.21.1", calls=calls),
        ):
            app._request_static_data_refresh("")
            app.wait_for_result()
            app._watch_static_data_refresh()

        self.assertTrue(calls)
        self.assertTrue(all(thread_id != main_thread for thread_id, _url in calls))

    def test_new_patch_is_applied_on_main_thread(self):
        app = _StaticHarness(self.m)
        main_thread = threading.get_ident()
        with patch.object(
            self.m,
            "fetch_json",
            side_effect=self.remote_fetcher("16.22.1"),
        ):
            app._request_static_data_refresh("")
            app.wait_for_result()
            app._watch_static_data_refresh()

        self.assertEqual(app.dd.version, "16.22.1")
        self.assertEqual(app.health_threads, [main_thread])
        self.assertTrue(app.dd.has_complete_static_data())

    def test_duplicate_refresh_requests_share_one_worker(self):
        entered = threading.Event()
        release = threading.Event()
        calls = []
        fetch = self.remote_fetcher("16.23.1", calls=calls)

        def blocked_fetch(url, timeout=4.0):
            if url.endswith("/api/versions.json"):
                entered.set()
                if not release.wait(timeout=2.0):
                    raise AssertionError("test did not release version request")
            return fetch(url, timeout=timeout)

        app = _StaticHarness(self.m)
        with patch.object(self.m, "fetch_json", side_effect=blocked_fetch):
            first = app._request_static_data_refresh("16.23.9.1")
            self.assertTrue(entered.wait(timeout=2.0))
            second = app._request_static_data_refresh("16.23.9.1")
            release.set()
            app.wait_for_result()
            app._watch_static_data_refresh()

        self.assertEqual(first, second)
        version_calls = [url for _thread, url in calls if "versions.json" in url]
        self.assertEqual(len(version_calls), 1)

    def test_stale_generation_cannot_replace_newer_static_state(self):
        current = self.m.DataDragon()
        self.assertTrue(current._apply_static_bundle("16.24.1", *catalog_bundle("old")))
        stale = self.m.DataDragon()
        self.assertTrue(stale._apply_static_bundle("16.23.1", *catalog_bundle("stale")))
        app = _StaticHarness(self.m, current)
        app._static_refresh_generation = 2
        app._static_refresh_active_generation = 1
        app._static_refresh_in_flight = True
        app._static_refresh_queue.put_nowait(
            {
                "generation": 1,
                "candidate": stale,
                "version": stale.version,
                "unchanged": False,
                "error": "",
            }
        )

        app._watch_static_data_refresh()

        self.assertIs(app.dd, current)
        self.assertEqual(app.dd.version, "16.24.1")

    def test_failed_refresh_preserves_last_known_good_data(self):
        current = self.m.DataDragon()
        self.assertTrue(current._apply_static_bundle("16.24.1", *catalog_bundle("good")))
        app = _StaticHarness(self.m, current)
        with patch.object(self.m, "fetch_json", side_effect=OSError("offline")):
            app._request_static_data_refresh("16.25.1.1")
            app.wait_for_result()
            app._watch_static_data_refresh()

        self.assertIs(app.dd, current)
        self.assertEqual(app.dd.item_name("1001"), "Bootsgood")

    def test_corrupt_remote_catalog_rejected_without_cache_adoption(self):
        current = self.m.DataDragon()
        self.assertTrue(current._apply_static_bundle("16.24.1", *catalog_bundle("good")))
        corrupt = catalog_bundle("bad")
        corrupt = (corrupt[0], {"data": {}}, corrupt[2])
        app = _StaticHarness(self.m, current)
        with patch.object(
            self.m,
            "fetch_json",
            side_effect=self.remote_fetcher("16.25.1", bundle=corrupt),
        ):
            app._request_static_data_refresh("16.25.9.1")
            app.wait_for_result()
            app._watch_static_data_refresh()

        self.assertIs(app.dd, current)
        self.assertFalse(self.m.DataDragon._bundle_marker_path("16.25.1").exists())

    def test_incomplete_cache_marker_blocks_partial_catalog_set(self):
        self.write_bundle("16.26.1", complete_marker=False)
        dd = self.m.DataDragon()

        loaded = dd.load_cached_static_data()

        self.assertIsNone(loaded)
        self.assertIsNone(dd.version)

    def test_patch_changes_only_after_complete_coherent_bundle(self):
        dd = self.m.DataDragon()
        self.assertTrue(dd._apply_static_bundle("16.26.1", *catalog_bundle("old")))
        original_items = dd.item_data

        invalid = catalog_bundle("new")
        self.assertFalse(dd._apply_static_bundle("16.27.1", invalid[0], invalid[1], []))
        self.assertEqual(dd.version, "16.26.1")
        self.assertIs(dd.item_data, original_items)

        self.assertTrue(dd._apply_static_bundle("16.27.1", *invalid))
        self.assertEqual(
            {dd.version, dd.items_version, dd.champions_version, dd.runes_version},
            {"16.27.1"},
        )

    def test_explicitly_mixed_catalog_versions_are_rejected(self):
        dd = self.m.DataDragon()
        self.assertTrue(dd._apply_static_bundle("16.27.1", *catalog_bundle("old")))
        items, champions, runes = catalog_bundle("mixed")
        items["version"] = "16.28.1"
        champions["version"] = "16.27.1"

        applied = dd._apply_static_bundle(
            "16.28.1",
            items,
            champions,
            runes,
        )

        self.assertFalse(applied)
        self.assertEqual(dd.version, "16.27.1")

    def test_shutdown_ignores_late_refresh_completion(self):
        current = self.m.DataDragon()
        self.assertTrue(current._apply_static_bundle("16.27.1", *catalog_bundle("old")))
        newer = self.m.DataDragon()
        self.assertTrue(newer._apply_static_bundle("16.28.1", *catalog_bundle("new")))
        app = _StaticHarness(self.m, current)
        app._static_refresh_generation = 1
        app._static_refresh_active_generation = 1
        app._static_refresh_in_flight = True
        app._static_refresh_shutdown = True
        app._static_refresh_queue.put_nowait(
            {
                "generation": 1,
                "candidate": newer,
                "version": newer.version,
                "unchanged": False,
                "error": "",
            }
        )

        app._watch_static_data_refresh()

        self.assertIs(app.dd, current)
        self.assertEqual(app.after_calls, [])

    def test_cached_current_patch_does_not_redownload_catalogs(self):
        current = self.m.DataDragon()
        self.assertTrue(current._apply_static_bundle("16.28.1", *catalog_bundle()))
        app = _StaticHarness(self.m, current)
        calls = []
        with patch.object(
            self.m,
            "fetch_json",
            side_effect=self.remote_fetcher("16.28.1", calls=calls),
        ):
            app._request_static_data_refresh("")
            app.wait_for_result()
            app._watch_static_data_refresh()

        self.assertEqual(len(calls), 1)
        self.assertTrue(calls[0][1].endswith("/api/versions.json"))
        self.assertIs(app.dd, current)

    def test_patch_swap_invalidates_old_icon_waiters_and_uses_new_version_key(self):
        current = self.m.DataDragon()
        self.assertTrue(current._apply_static_bundle("16.28.1", *catalog_bundle("old")))
        newer = self.m.DataDragon()
        self.assertTrue(newer._apply_static_bundle("16.29.1", *catalog_bundle("new")))
        app = _StaticHarness(self.m, current)
        app._icon_pending[("champion", "16.28.1", "Ahri")] = [object()]
        app._icon_failures[("item", "16.28.1", "1001")] = time.monotonic()

        applied = app._apply_static_data_candidate(newer)

        self.assertTrue(applied)
        self.assertEqual(app._icon_pending, {})
        self.assertEqual(app._icon_failures, {})
        self.assertEqual(
            app._icon_request_key("item", "1001")[1],
            "16.29.1",
        )


if __name__ == "__main__":
    unittest.main()
