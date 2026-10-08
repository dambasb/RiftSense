import importlib.util
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
    local_data = tempfile.mkdtemp(prefix="riftsense-icon-data-")
    fake_home = Path(tempfile.mkdtemp(prefix="riftsense-icon-home-"))
    (fake_home / "Downloads").mkdir()
    (fake_home / "Desktop").mkdir()
    os.environ["LOCALAPPDATA"] = local_data
    with patch("pathlib.Path.home", return_value=fake_home):
        spec = importlib.util.spec_from_file_location(
            "riftsense_async_icon_test",
            APP_PATH,
        )
        module = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        spec.loader.exec_module(module)
        return module


class _FakeWidget:
    def __init__(self):
        self.exists = True
        self.configurations = []
        self.canvas_operations = []

    def winfo_exists(self):
        return self.exists

    def configure(self, **kwargs):
        self.configurations.append((threading.get_ident(), kwargs))

    def delete(self, tag):
        self.canvas_operations.append(("delete", tag))

    def create_image(self, *args, **kwargs):
        self.canvas_operations.append(("image", args, kwargs))


class _FakeDataDragon:
    version = "99.1.1"
    champion_name_to_key = {}

    def __init__(self, owner):
        self.owner = owner

    def cached_champion_icon_path(self, asset_id):
        return self.owner.cache.get(("champion", str(asset_id)))

    def cached_item_icon_path(self, asset_id):
        return self.owner.cache.get(("item", str(asset_id)))

    def champion_icon_path(self, asset_id):
        return self.owner.remote_acquire("champion", asset_id)

    def item_icon_path(self, asset_id):
        return self.owner.remote_acquire("item", asset_id)


class _IconHarness:
    _icon_worker_loop = None
    _icon_request_key = None
    _apply_widget_icon = None
    _request_widget_icon = None
    _watch_icon_results = None

    def __init__(self, module):
        cls = type(self)
        cls._icon_worker_loop = module.App._icon_worker_loop
        cls._icon_request_key = module.App._icon_request_key
        cls._apply_widget_icon = module.App._apply_widget_icon
        cls._request_widget_icon = module.App._request_widget_icon
        cls._watch_icon_results = module.App._watch_icon_results

        self.cache = {}
        self.remote_calls = []
        self.remote_threads = []
        self.remote_fail = set()
        self._icon_work_queue = queue.Queue()
        self._icon_result_queue = queue.Queue()
        self._icon_pending = {}
        self._icon_failures = {}
        self._icon_watch_job = None
        self._icon_shutdown = False
        self.after_calls = []
        self.photo_threads = []
        self.dd = _FakeDataDragon(self)

    def after(self, delay, callback):
        self.after_calls.append((delay, callback))
        return f"after-{len(self.after_calls)}"

    def _cached_icon_path(self, icon_kind, asset_id):
        return self.cache.get((icon_kind, str(asset_id)))

    def cached_current_item_icon_path(self, asset_id):
        return self.cache.get(("item", str(asset_id)))

    def current_item_icon_path(self, asset_id):
        return self.remote_acquire("item", asset_id)

    def remote_acquire(self, icon_kind, asset_id):
        identity = str(asset_id)
        self.remote_calls.append((icon_kind, identity))
        self.remote_threads.append(threading.get_ident())
        if (icon_kind, identity) in self.remote_fail:
            return None
        path = Path(f"cached-{icon_kind}-{identity}.png")
        self.cache[(icon_kind, identity)] = path
        return path

    def load_photo(self, path, target_px=None, **_kwargs):
        self.photo_threads.append(threading.get_ident())
        return ("photo", str(path), target_px)

    def load_circle_photo(self, path, target_px=None, **_kwargs):
        self.photo_threads.append(threading.get_ident())
        return ("circle", str(path), target_px)

    def start_worker(self):
        worker = threading.Thread(target=self._icon_worker_loop, daemon=True)
        worker.start()
        return worker

    def wait_for_result(self):
        return self.wait_for_results(1)[0]

    def wait_for_results(self, count):
        results = [
            self._icon_result_queue.get(timeout=2.0)
            for _index in range(count)
        ]
        for result in results:
            self._icon_result_queue.put_nowait(result)
        return results

    def stop_worker(self, worker):
        self._icon_work_queue.put_nowait(None)
        worker.join(timeout=2.0)
        if worker.is_alive():
            raise AssertionError("icon worker did not stop")


class AsyncIconTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.m = load_app_module()

    def make_app(self):
        return _IconHarness(self.m)

    def test_cached_champion_and_item_icons_do_not_queue_network_fetch(self):
        main_thread = threading.get_ident()
        for icon_kind, asset_id in (("champion", "Ahri"), ("item", "1001")):
            with self.subTest(icon_kind=icon_kind):
                app = self.make_app()
                app.cache[(icon_kind, asset_id)] = Path("already-cached.png")
                widget = _FakeWidget()

                loaded = app._request_widget_icon(
                    widget, icon_kind, asset_id, 32
                )

                self.assertTrue(loaded)
                self.assertEqual(app.remote_calls, [])
                self.assertTrue(app._icon_work_queue.empty())
                self.assertEqual(widget.configurations[0][0], main_thread)

    def test_missing_icon_keeps_placeholder_and_returns_immediately(self):
        app = self.make_app()
        widget = _FakeWidget()

        loaded = app._request_widget_icon(widget, "champion", "Ahri", 32)

        self.assertFalse(loaded)
        self.assertEqual(widget.configurations, [])
        self.assertEqual(app._icon_work_queue.qsize(), 1)

    def test_remote_fetch_runs_outside_main_thread(self):
        app = self.make_app()
        widget = _FakeWidget()
        worker = app.start_worker()
        try:
            app._request_widget_icon(widget, "champion", "Ahri", 32)
            app.wait_for_result()
        finally:
            app.stop_worker(worker)

        self.assertEqual(app.remote_calls, [("champion", "Ahri")])
        self.assertNotEqual(app.remote_threads[0], threading.get_ident())

    def test_simultaneous_requests_for_same_icon_are_deduplicated(self):
        app = self.make_app()
        first = _FakeWidget()
        second = _FakeWidget()

        app._request_widget_icon(first, "item", "3157", 32)
        app._request_widget_icon(second, "item", "3157", 48)

        self.assertEqual(app._icon_work_queue.qsize(), 1)
        request_key = app._icon_request_key("item", "3157")
        self.assertEqual(len(app._icon_pending[request_key]), 2)
        worker = app.start_worker()
        try:
            app.wait_for_result()
            app._watch_icon_results()
        finally:
            app.stop_worker(worker)
        self.assertEqual(app.remote_calls, [("item", "3157")])
        self.assertTrue(first.configurations)
        self.assertTrue(second.configurations)

    def test_successful_completion_updates_live_widget_on_main_thread(self):
        app = self.make_app()
        widget = _FakeWidget()
        worker = app.start_worker()
        try:
            app._request_widget_icon(widget, "item", "1001", 28)
            app.wait_for_result()
            app._watch_icon_results()
        finally:
            app.stop_worker(worker)

        self.assertEqual(widget.configurations[0][0], threading.get_ident())
        self.assertEqual(app.photo_threads, [threading.get_ident()])
        self.assertTrue(hasattr(widget, "_riftsense_icon_photo"))

    def test_destroyed_widget_is_not_updated(self):
        app = self.make_app()
        widget = _FakeWidget()
        app._request_widget_icon(widget, "champion", "Ahri", 32)
        widget.exists = False
        key = app._icon_request_key("champion", "Ahri")
        app._icon_result_queue.put_nowait((key, Path("ahri.png"), ""))

        app._watch_icon_results()

        self.assertEqual(widget.configurations, [])
        self.assertNotIn(key, app._icon_pending)

    def test_widget_reuse_ignores_stale_completion(self):
        app = self.make_app()
        widget = _FakeWidget()
        app._request_widget_icon(widget, "champion", "Ahri", 32)
        app._request_widget_icon(widget, "champion", "Lux", 32)
        stale_key = app._icon_request_key("champion", "Ahri")
        app._icon_result_queue.put_nowait((stale_key, Path("ahri.png"), ""))

        app._watch_icon_results()

        self.assertEqual(widget.configurations, [])

    def test_failed_download_leaves_placeholder_and_sets_retry_cooldown(self):
        app = self.make_app()
        widget = _FakeWidget()
        app.remote_fail.add(("item", "9999"))
        worker = app.start_worker()
        try:
            app._request_widget_icon(widget, "item", "9999", 32)
            app.wait_for_result()
            app._watch_icon_results()
        finally:
            app.stop_worker(worker)
        key = app._icon_request_key("item", "9999")

        self.assertEqual(widget.configurations, [])
        self.assertGreater(app._icon_failures[key], 0.0)
        queued_before = app._icon_work_queue.qsize()
        app._request_widget_icon(_FakeWidget(), "item", "9999", 32)
        self.assertEqual(app._icon_work_queue.qsize(), queued_before)

    def test_shutdown_ignores_late_completion(self):
        app = self.make_app()
        widget = _FakeWidget()
        app._request_widget_icon(widget, "champion", "Ahri", 32)
        key = app._icon_request_key("champion", "Ahri")
        app._icon_result_queue.put_nowait((key, Path("ahri.png"), ""))
        app._icon_shutdown = True

        app._watch_icon_results()

        self.assertEqual(widget.configurations, [])

    def test_champion_and_item_both_use_async_worker_path(self):
        app = self.make_app()
        champion = _FakeWidget()
        item = _FakeWidget()
        worker = app.start_worker()
        try:
            app._request_widget_icon(champion, "champion", "Ahri", 32)
            app._request_widget_icon(item, "item", "1001", 32)
            app.wait_for_results(2)
        finally:
            app.stop_worker(worker)

        self.assertCountEqual(
            app.remote_calls,
            [("champion", "Ahri"), ("item", "1001")],
        )

    def test_populated_cache_prevents_duplicate_download(self):
        app = self.make_app()
        first = _FakeWidget()
        worker = app.start_worker()
        try:
            app._request_widget_icon(first, "champion", "Ahri", 32)
            app.wait_for_result()
            app._watch_icon_results()
            second = _FakeWidget()
            app._request_widget_icon(second, "champion", "Ahri", 32)
        finally:
            app.stop_worker(worker)

        self.assertEqual(app.remote_calls, [("champion", "Ahri")])
        self.assertTrue(second.configurations)


if __name__ == "__main__":
    unittest.main()
