import importlib.util
import os
import queue
import tempfile
import threading
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from riftsense.riot.workers import RiotWorkerOutcome, RiotWorkerTerminal


ROOT = Path(__file__).resolve().parents[1]
APP_PATH = ROOT / "RiftSense.py"


def load_app_module():
    os.environ["LOCALAPPDATA"] = tempfile.mkdtemp(
        prefix="riftsense-riot-worker-data-"
    )
    spec = importlib.util.spec_from_file_location(
        "riftsense_riot_worker_test",
        APP_PATH,
    )
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
    def __init__(self):
        self.values = {}

    def configure(self, **kwargs):
        self.values.update(kwargs)


class DeadThread:
    @staticmethod
    def is_alive():
        return False


class FastEvent:
    def __init__(self, set_initially=False):
        self.value = set_initially

    def is_set(self):
        return self.value

    def set(self):
        self.value = True

    def clear(self):
        self.value = False

    def wait(self, _delay):
        return self.value


class RiotWorkerLifecycleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.m = load_app_module()

    def diagnostic_app(self, identity=None):
        app = SimpleNamespace(
            setting_riot_api_key_var=Value("RGAPI-TEST-NOT-REAL"),
            setting_riot_id_var=Value("Player#EUNE"),
            setting_riot_platform_var=Value("EUN1"),
            setting_riot_route_var=Value("EUROPE"),
            history_sync_status_var=Value(""),
            setting_test_api_button=Button(),
            _riot_api_test_job=None,
            _riot_api_test_generation=0,
            _riot_api_test_active_generation=None,
            _riot_request_cancel=FastEvent(),
        )
        app._history_local_identity = (
            identity
            if identity is not None
            else lambda _riot_id: {
                "puuid": "puuid-1",
                "riot_id": "Player#EUNE",
                "source": "test",
            }
        )
        app.after_cancel = lambda _job: None
        app.after = lambda _delay, _callback: "after-job"
        app._watch_riot_api_test_queue = lambda: None
        return app

    def test_terminal_publisher_accepts_exactly_one_outcome(self):
        results = queue.Queue()
        terminal = RiotWorkerTerminal(results, 7, "test")

        self.assertTrue(
            terminal.publish(RiotWorkerOutcome.SUCCESS, "complete", ok=True)
        )
        self.assertFalse(
            terminal.publish(RiotWorkerOutcome.FAILED, "late failure")
        )

        self.assertEqual(results.qsize(), 1)
        result = results.get_nowait()
        self.assertEqual(result["outcome"], "SUCCESS")
        self.assertEqual(result["generation"], 7)

    def test_terminal_preparation_failure_does_not_stick_publisher(self):
        results = queue.Queue()
        terminal = RiotWorkerTerminal(results, 3, "test")

        self.assertFalse(terminal.publish("NOT_A_STATE", "bad"))
        self.assertFalse(terminal.sent)
        self.assertTrue(
            terminal.publish(RiotWorkerOutcome.FAILED, "controlled failure")
        )
        self.assertEqual(results.get_nowait()["outcome"], "FAILED")

    def test_diagnostic_normal_success_is_one_terminal_result(self):
        app = self.diagnostic_app()
        with (
            patch.object(
                self.m,
                "riot_league_entries_by_puuid",
                return_value=([], 200, {}),
            ),
            patch.object(
                self.m,
                "riot_match_ids_page",
                return_value=([], 200, {}),
            ),
        ):
            self.m.App.test_riot_api_access(app)
            app._riot_api_test_thread.join(timeout=2.0)

        self.assertFalse(app._riot_api_test_thread.is_alive())
        self.assertEqual(app._riot_api_test_queue.qsize(), 1)
        self.assertEqual(
            app._riot_api_test_queue.get_nowait()["outcome"],
            "SUCCESS",
        )

    def test_known_riot_failure_is_one_failed_terminal_result(self):
        app = self.diagnostic_app()
        with patch.object(
            self.m,
            "riot_league_entries_by_puuid",
            return_value=(
                {"status": {"message": "Riot API key is invalid or expired."}},
                403,
                {},
            ),
        ):
            self.m.App.test_riot_api_access(app)
            app._riot_api_test_thread.join(timeout=2.0)

        result = app._riot_api_test_queue.get_nowait()
        self.assertEqual(result["outcome"], "FAILED")
        self.assertEqual(app._riot_api_test_queue.qsize(), 0)

    def test_unexpected_diagnostic_exception_is_controlled_failure(self):
        def explode(_riot_id):
            raise RuntimeError("processing boom")

        app = self.diagnostic_app(explode)
        self.m.App.test_riot_api_access(app)
        app._riot_api_test_thread.join(timeout=2.0)

        result = app._riot_api_test_queue.get_nowait()
        self.assertEqual(result["outcome"], "FAILED")
        self.assertIn("Unexpected diagnostic failure", result["message"])
        self.assertNotIn("processing boom", result["message"])

    def test_shutdown_cancellation_before_work_is_cancelled(self):
        app = self.diagnostic_app()
        app._riot_request_cancel.set()

        self.m.App.test_riot_api_access(app)
        app._riot_api_test_thread.join(timeout=2.0)

        result = app._riot_api_test_queue.get_nowait()
        self.assertEqual(result["outcome"], "CANCELLED")
        self.assertEqual(app._riot_api_test_queue.qsize(), 0)

    def test_cancellation_during_work_prevents_late_success(self):
        app = self.diagnostic_app()

        def cancel_during_rank(*_args, **_kwargs):
            app._riot_request_cancel.set()
            return [], 200, {}

        with (
            patch.object(
                self.m,
                "riot_league_entries_by_puuid",
                side_effect=cancel_during_rank,
            ),
            patch.object(
                self.m,
                "riot_match_ids_page",
                return_value=([], 200, {}),
            ),
        ):
            self.m.App.test_riot_api_access(app)
            app._riot_api_test_thread.join(timeout=2.0)

        result = app._riot_api_test_queue.get_nowait()
        self.assertEqual(result["outcome"], "CANCELLED")
        self.assertEqual(app._riot_api_test_queue.qsize(), 0)

    def test_stale_diagnostic_watcher_cannot_overwrite_new_run(self):
        old_queue = queue.Queue()
        old_queue.put_nowait({
            "outcome": "SUCCESS",
            "generation": 1,
            "message": "old success",
        })
        app = SimpleNamespace(
            _riot_api_test_active_generation=2,
            _riot_api_test_queue=queue.Queue(),
            _riot_api_test_thread=DeadThread(),
            _riot_api_test_job="new-job",
            history_sync_status_var=Value("new run active"),
            setting_test_api_button=Button(),
            last_riot_api_diagnostic="new diagnostic",
        )

        self.m.App._watch_riot_api_test_queue(
            app,
            1,
            old_queue,
            DeadThread(),
        )

        self.assertEqual(app._riot_api_test_active_generation, 2)
        self.assertEqual(app.history_sync_status_var.get(), "new run active")
        self.assertEqual(app.last_riot_api_diagnostic, "new diagnostic")

    def test_general_rank_terminal_consumption_cleans_active_state(self):
        result_queue = queue.Queue()
        result_queue.put_nowait({
            "outcome": "FAILED",
            "generation": 4,
            "message": "failed",
            "payload": {"kind": "none", "source": "", "payload": None},
            "status": None,
            "error": "known failure",
        })
        calls = []
        thread = DeadThread()
        app = SimpleNamespace(
            _general_rank_watch_job="job",
            _general_rank_active_generation=4,
            _general_rank_queue=result_queue,
            _general_rank_thread=thread,
            _general_rank_refresh_inflight=True,
            _general_rank_refresh_done=lambda *args: calls.append(args),
        )

        self.m.App._watch_general_rank_refresh(
            app,
            4,
            result_queue,
            thread,
        )

        self.assertFalse(app._general_rank_refresh_inflight)
        self.assertIsNone(app._general_rank_active_generation)
        self.assertIsNone(app._general_rank_thread)
        self.assertEqual(calls[0][2], "known failure")

    def test_stale_general_rank_watcher_cannot_clear_new_watch_job(self):
        app = SimpleNamespace(
            _general_rank_watch_job="new-job",
            _general_rank_active_generation=6,
            _general_rank_queue=queue.Queue(),
            _general_rank_thread=DeadThread(),
            _general_rank_refresh_inflight=True,
        )

        self.m.App._watch_general_rank_refresh(
            app,
            5,
            queue.Queue(),
            DeadThread(),
        )

        self.assertEqual(app._general_rank_watch_job, "new-job")
        self.assertTrue(app._general_rank_refresh_inflight)

    def test_verify_worker_unexpected_exception_is_failed_once(self):
        app = SimpleNamespace(
            setting_riot_api_key_var=Value("RGAPI-TEST-NOT-REAL"),
            setting_riot_id_var=Value("Player#EUNE"),
            setting_riot_platform_var=Value("EUN1"),
            setting_riot_route_var=Value("EUROPE"),
            history_sync_status_var=Value(""),
            setting_verify_sync_button=Button(),
            _riot_sync_thread=None,
            _verify_sync_generation=0,
            _verify_sync_active_generation=None,
            _verify_sync_job=None,
            _riot_request_cancel=FastEvent(),
            _selected_history_queue_ids=lambda: [420],
            _history_local_identity=lambda _riot_id: (_ for _ in ()).throw(
                RuntimeError("verify boom")
            ),
            after=lambda _delay, _callback: "after-job",
            after_cancel=lambda _job: None,
            _watch_verify_sync_queue=lambda: None,
        )

        self.m.App.verify_and_sync_ranked(app)
        app._verify_sync_thread.join(timeout=2.0)

        result = app._verify_sync_queue.get_nowait()
        self.assertEqual(result["outcome"], "FAILED")
        self.assertFalse(result["ok"])
        self.assertEqual(app._verify_sync_queue.qsize(), 0)

    def test_history_exception_preserves_partial_index_without_completion(self):
        app = SimpleNamespace(
            _riot_sync_queue=queue.Queue(),
            _riot_sync_cancel=FastEvent(),
            _riot_sync_active_generation=9,
            _riot_sync_context=threading.local(),
            _riot_sync_terminal_lock=threading.Lock(),
            _history_local_identity=lambda _riot_id: {
                "puuid": "puuid-1",
                "riot_id": "Player#EUNE",
                "source": "test",
            },
        )
        app._riot_sync_post = lambda payload: self.m.App._riot_sync_post(app, payload)
        account_updates = []
        saved_indexes = []
        detail_calls = {"count": 0}

        def update_account(mutator):
            current = {}
            mutator(current)
            account_updates.append(dict(current))
            return True, ""

        def match_detail(*_args, **_kwargs):
            detail_calls["count"] += 1
            if detail_calls["count"] == 1:
                return {"info": {}, "metadata": {}}, 200, {}
            raise RuntimeError("transform boom")

        summary = {
            "match_id": "M1",
            "queue_id": 420,
            "game_creation_ms": 10,
        }
        season = {
            "queues": {420: "Ranked Solo/Duo"},
        }
        scope = {
            "key": "2026_YEAR",
            "name": "2026 Ranked Year",
            "start_epoch": 1,
        }

        with tempfile.TemporaryDirectory() as temp_dir:
            with (
                patch.object(self.m, "RIOT_HISTORY_DIR", Path(temp_dir)),
                patch.object(self.m, "current_ranked_season", return_value=season),
                patch.object(
                    self.m,
                    "ranked_history_scope_info",
                    return_value=scope,
                ),
                patch.object(self.m, "load_json", return_value={}),
                patch.object(
                    self.m,
                    "riot_league_entries_by_puuid",
                    return_value=([], 200, {}),
                ),
                patch.object(self.m, "update_riot_account", side_effect=update_account),
                patch.object(
                    self.m,
                    "riot_match_ids_page",
                    return_value=(["M1", "M2"], 200, {}),
                ),
                patch.object(self.m, "load_riot_history_index", return_value=[]),
                patch.object(self.m, "riot_match_detail", side_effect=match_detail),
                patch.object(self.m, "riot_match_summary", return_value=summary),
                patch.object(self.m, "is_ranked_row_in_scope", return_value=True),
                patch.object(self.m, "write_json_atomic", return_value=(True, "")),
                patch.object(
                    self.m,
                    "save_riot_history_index",
                    side_effect=lambda rows: saved_indexes.append(list(rows)),
                ),
            ):
                self.m.App._riot_history_sync_worker(
                    app,
                    "Player#EUNE",
                    "EUROPE",
                    "EUN1",
                    "RGAPI-TEST",
                    [420],
                    "2026_YEAR",
                    9,
                    app._riot_sync_queue,
                )

        events = []
        while not app._riot_sync_queue.empty():
            events.append(app._riot_sync_queue.get_nowait())
        terminal_results = [event for event in events if event.get("outcome")]
        self.assertEqual(len(terminal_results), 1)
        self.assertEqual(terminal_results[0]["outcome"], "FAILED")
        self.assertTrue(any(summary in rows for rows in saved_indexes))
        self.assertFalse(
            any("last_sync_at" in update for update in account_updates)
        )


if __name__ == "__main__":
    unittest.main()
