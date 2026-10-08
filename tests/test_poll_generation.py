import importlib.util
import os
import queue
import tempfile
import threading
import time
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
APP_PATH = ROOT / "RiftSense.py"


def load_app_module():
    local_data = tempfile.mkdtemp(prefix="riftsense-poll-generation-data-")
    fake_home = Path(tempfile.mkdtemp(prefix="riftsense-poll-generation-home-"))
    (fake_home / "Downloads").mkdir()
    (fake_home / "Desktop").mkdir()
    os.environ["LOCALAPPDATA"] = local_data
    with patch("pathlib.Path.home", return_value=fake_home):
        spec = importlib.util.spec_from_file_location(
            "riftsense_poll_generation_test",
            APP_PATH,
        )
        module = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        spec.loader.exec_module(module)
        return module


class _Value:
    def __init__(self):
        self.value = None

    def set(self, value):
        self.value = value


class PollGenerationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.m = load_app_module()

    def make_app(self, generation=1, *, started_at=None):
        app = SimpleNamespace()
        app._poll_queue = queue.Queue()
        app._poll_state_lock = threading.Lock()
        app._poll_generation = generation
        app._poll_active_generation = generation
        app._poll_shutdown = False
        app._poll_in_flight = True
        app._poll_started_at = (
            time.monotonic() if started_at is None else started_at
        )
        app._poll_watch_job = None
        app.scheduled = []
        app.draft_calls = []
        app.live_calls = []
        app.modes = []
        app.health_updates = 0
        app.header_updates = 0
        app.draft_status = _Value()
        app.live_status = _Value()
        app.global_status = _Value()

        def after(delay, callback):
            app.scheduled.append((delay, callback))
            return f"after-{len(app.scheduled)}"

        def refresh_draft(**kwargs):
            app.draft_calls.append(kwargs)
            session = kwargs.get("prefetched_session")
            return bool(session and session.get("draft"))

        def refresh_live(**kwargs):
            app.live_calls.append(kwargs)
            live_data = kwargs.get("prefetched_data")
            return bool(live_data and live_data.get("live"))

        app.after = after
        app.refresh_all = lambda: None
        app.refresh_draft = refresh_draft
        app.refresh_live = refresh_live
        app.apply_auto_mode = app.modes.append
        app.update_health_bar = lambda: setattr(
            app, "health_updates", app.health_updates + 1
        )
        app.refresh_dashboard_header = lambda: setattr(
            app, "header_updates", app.header_updates + 1
        )
        return app

    def queue_result(self, app, generation, *, draft=False, live=False):
        app._poll_queue.put_nowait(
            (
                generation,
                {"draft": True} if draft else None,
                200 if draft else None,
                {"live": True} if live else None,
                time.monotonic(),
            )
        )

    def watch(self, app, generation):
        self.m.App._watch_poll_result(app, generation)

    def test_normal_current_generation_result_is_accepted(self):
        app = self.make_app(4)
        self.queue_result(app, 4, draft=True)

        self.watch(app, 4)

        self.assertFalse(app._poll_in_flight)
        self.assertIsNone(app._poll_active_generation)
        self.assertEqual(app.modes, ["draft"])
        self.assertEqual(app.global_status.value, "Champion Select detected")
        self.assertEqual(app.scheduled[-1][0], self.m.DRAFT_REFRESH_MS)

    def test_timeout_invalidates_generation_and_rejects_late_result(self):
        app = self.make_app(1, started_at=time.monotonic() - 4.0)

        self.watch(app, 1)

        self.assertEqual(app._poll_generation, 2)
        self.assertIsNone(app._poll_active_generation)
        self.assertFalse(app._poll_in_flight)
        self.assertEqual(app.scheduled[-1][0], self.m.REFRESH_MS)

        self.queue_result(app, 1, draft=True)
        self.watch(app, 1)
        self.assertEqual(app.modes, [])

    def test_new_generation_succeeds_after_older_timeout(self):
        app = self.make_app(5, started_at=time.monotonic() - 4.0)
        self.watch(app, 5)

        app._poll_generation += 1
        app._poll_active_generation = app._poll_generation
        app._poll_in_flight = True
        app._poll_started_at = time.monotonic()
        current_generation = app._poll_active_generation
        self.queue_result(app, current_generation, live=True)

        self.watch(app, current_generation)

        self.assertEqual(app.modes, ["live"])
        self.assertEqual(app.global_status.value, "Live game detected")

    def test_old_result_before_new_result_cannot_overwrite_new_state(self):
        app = self.make_app(8)
        self.queue_result(app, 7, draft=True)
        self.queue_result(app, 8, live=True)

        self.watch(app, 8)

        self.assertEqual(app.modes, ["live"])
        self.assertIsNone(app.draft_calls[0]["prefetched_session"])
        self.assertEqual(app.live_calls[0]["prefetched_data"], {"live": True})

    def test_stale_watcher_does_not_clear_newer_in_flight_state(self):
        app = self.make_app(12)
        self.queue_result(app, 11, draft=True)

        self.watch(app, 11)

        self.assertTrue(app._poll_in_flight)
        self.assertEqual(app._poll_active_generation, 12)
        self.assertEqual(app.modes, [])

    def test_multiple_stale_results_are_ignored_before_current_result(self):
        app = self.make_app(20)
        self.queue_result(app, 17, draft=True)
        self.queue_result(app, 18, live=True)
        self.queue_result(app, 19, draft=True)
        self.queue_result(app, 20)

        self.watch(app, 20)

        self.assertEqual(app.modes, ["waiting"])
        self.assertEqual(app.global_status.value, "Waiting for draft or game")
        self.assertTrue(app._poll_queue.empty())

    def test_shutdown_ignores_late_current_generation_result(self):
        app = self.make_app(2)
        self.queue_result(app, 2, draft=True)
        app._poll_shutdown = True

        self.watch(app, 2)

        self.assertTrue(app._poll_in_flight)
        self.assertEqual(app.modes, [])
        self.assertEqual(app.scheduled, [])

    def test_queue_to_champion_select_transition_remains_draft(self):
        app = self.make_app(30)
        self.queue_result(app, 30, draft=True)

        self.watch(app, 30)

        self.assertEqual(app.modes[-1], "draft")
        self.assertEqual(app.scheduled[-1][0], self.m.DRAFT_REFRESH_MS)

    def test_champion_select_to_live_transition_remains_correct(self):
        app = self.make_app(40)
        self.queue_result(app, 40, draft=True)
        self.watch(app, 40)

        app._poll_generation = 41
        app._poll_active_generation = 41
        app._poll_in_flight = True
        app._poll_started_at = time.monotonic()
        self.queue_result(app, 41, live=True)
        self.watch(app, 41)

        self.assertEqual(app.modes, ["draft", "live"])
        self.assertEqual(app.global_status.value, "Live game detected")
        self.assertEqual(app.scheduled[-1][0], self.m.REFRESH_MS)

    def test_worker_finishing_after_invalidation_cannot_publish(self):
        entered_lcu = threading.Event()
        release_lcu = threading.Event()

        class BlockingLCU:
            def get(self, *_args, **_kwargs):
                entered_lcu.set()
                self.assert_released = release_lcu.wait(timeout=2.0)
                if not self.assert_released:
                    raise AssertionError("test did not release blocked poll worker")
                return {"draft": True}, 200

        app = self.make_app(50)
        app.lcu = BlockingLCU()
        thread = threading.Thread(
            target=self.m.App._poll_sources_worker,
            args=(app, 50),
            daemon=True,
        )

        with patch.object(self.m, "get_live_game_data", return_value=None):
            thread.start()
            self.assertTrue(entered_lcu.wait(timeout=2.0))
            with app._poll_state_lock:
                app._poll_generation = 51
                app._poll_active_generation = 51
            release_lcu.set()
            thread.join(timeout=2.0)

        self.assertFalse(thread.is_alive())
        self.assertTrue(app._poll_queue.empty())


if __name__ == "__main__":
    unittest.main()
