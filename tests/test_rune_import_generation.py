import importlib.util
import os
import queue
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
APP_PATH = ROOT / "RiftSense.py"
SELECTION = {
    "primaryStyleId": 8000,
    "subStyleId": 8300,
    "selectedPerkIds": [1, 2, 3, 4, 5, 6, 5008, 5008, 5001],
}


def load_app_module():
    local_data = tempfile.mkdtemp(prefix="riftsense-rune-generation-data-")
    fake_home = Path(tempfile.mkdtemp(prefix="riftsense-rune-generation-home-"))
    (fake_home / "Downloads").mkdir()
    (fake_home / "Desktop").mkdir()
    os.environ["LOCALAPPDATA"] = local_data
    with patch("pathlib.Path.home", return_value=fake_home):
        spec = importlib.util.spec_from_file_location(
            "riftsense_rune_generation_test",
            APP_PATH,
        )
        module = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        spec.loader.exec_module(module)
        return module


class _FakeDataDragon:
    version = "test"
    rune_name_to_id = {"loaded": 1}

    def __init__(self):
        self.champions = {
            1: "Wukong",
            2: "Nocturne",
        }

    def champion_name(self, champion_id):
        return self.champions.get(int(champion_id or 0), "")


class _ControlledLCU:
    def __init__(self):
        self.pages_reached = threading.Event()
        self.release_pages = threading.Event()
        self.release_pages.set()
        self.write_reached = threading.Event()
        self.release_write = threading.Event()
        self.release_write.set()
        self.session = self.make_session(1, "JUNGLE", game_id=1001)
        self.session_status = 200
        self.writes = []

    @staticmethod
    def make_session(champion_id, role, game_id=1001, cell_id=7):
        return {
            "gameId": game_id,
            "localPlayerCellId": cell_id,
            "myTeam": [
                {
                    "cellId": cell_id,
                    "championId": champion_id,
                    "assignedPosition": role,
                }
            ],
        }

    def block_pages(self):
        self.release_pages.clear()

    def block_write(self):
        self.release_write.clear()

    def get(self, endpoint, timeout=None):
        if endpoint == "/lol-perks/v1/pages":
            self.pages_reached.set()
            if not self.release_pages.wait(timeout=2.0):
                raise AssertionError("test did not release rune page lookup")
            return [], 200
        if endpoint == "/lol-champ-select/v1/session":
            return self.session, self.session_status
        if endpoint == "/lol-perks/v1/currentpage":
            return {"selectedPerkIds": SELECTION["selectedPerkIds"]}, 200
        raise AssertionError(f"unexpected LCU GET: {endpoint}")

    def write_json(self, endpoint, payload, method="PUT", timeout=None):
        self.write_reached.set()
        if not self.release_write.wait(timeout=2.0):
            raise AssertionError("test did not release rune page write")
        self.writes.append(
            {
                "endpoint": endpoint,
                "payload": dict(payload),
                "method": method,
            }
        )
        return {}, 201, ""


class RuneImportGenerationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.m = load_app_module()

    def make_app(self, champion="Wukong", role="JUNGLE", generation=1):
        app = object.__new__(self.m.App)
        app.dd = _FakeDataDragon()
        app.lcu = _ControlledLCU()
        app._rune_import_queue = queue.Queue()
        app._rune_import_generation = generation
        app._rune_import_draft_active = True
        app._rune_import_shutdown = False
        app._rune_import_session_identity = self.m.App._champ_select_session_identity(
            app.lcu.session
        )
        app.current_rune_champion = champion
        app.current_rune_role = role
        app.current_rune_choices = self.m.rune_choices_for_role(champion, role)
        return app

    def start_worker(
        self,
        app,
        champion="Wukong",
        role="JUNGLE",
        generation=1,
        session_identity=None,
    ):
        if session_identity is None:
            session_identity = app._rune_import_session_identity
        worker = threading.Thread(
            target=self.m.App._rune_import_worker,
            args=(
                app,
                champion,
                role,
                "recommended",
                (champion, role, generation),
                generation,
                session_identity,
            ),
        )
        worker.start()
        return worker

    @staticmethod
    def finish_worker(worker, app):
        app.lcu.release_pages.set()
        app.lcu.release_write.set()
        worker.join(timeout=2.0)
        if worker.is_alive():
            raise AssertionError("rune worker did not finish")

    @staticmethod
    def events(app):
        result = []
        while True:
            try:
                result.append(app._rune_import_queue.get_nowait())
            except queue.Empty:
                return result

    def run_with_selection(self, callback):
        with patch.object(
            self.m,
            "build_rune_page_selection",
            return_value=(SELECTION, ""),
        ):
            callback()

    def test_normal_valid_rune_import_still_writes(self):
        app = self.make_app()

        def exercise():
            worker = self.start_worker(app)
            self.finish_worker(worker, app)

        self.run_with_selection(exercise)

        self.assertEqual(len(app.lcu.writes), 1)
        self.assertEqual(app.lcu.writes[0]["method"], "POST")
        self.assertEqual(app.lcu.writes[0]["payload"]["name"], "RiftSense - Wukong")
        self.assertIn("success", [event["type"] for event in self.events(app)])

    def test_champion_change_while_worker_runs_prevents_write(self):
        app = self.make_app()
        app.lcu.block_pages()

        def exercise():
            worker = self.start_worker(app)
            self.assertTrue(app.lcu.pages_reached.wait(timeout=2.0))
            app.current_rune_champion = "Nocturne"
            app.lcu.session = app.lcu.make_session(2, "JUNGLE", game_id=1001)
            self.finish_worker(worker, app)

        self.run_with_selection(exercise)

        events = self.events(app)
        self.assertEqual(app.lcu.writes, [])
        self.assertNotIn("success", [event["type"] for event in events])

    def test_role_change_while_worker_runs_prevents_write(self):
        app = self.make_app()
        app.lcu.block_pages()

        def exercise():
            worker = self.start_worker(app)
            self.assertTrue(app.lcu.pages_reached.wait(timeout=2.0))
            app.current_rune_role = "MID"
            app.lcu.session = app.lcu.make_session(1, "MIDDLE", game_id=1001)
            self.finish_worker(worker, app)

        self.run_with_selection(exercise)

        self.assertEqual(app.lcu.writes, [])
        self.assertNotIn("success", [event["type"] for event in self.events(app)])

    def test_champion_select_end_before_write_prevents_write(self):
        app = self.make_app()
        app.lcu.block_pages()

        def exercise():
            worker = self.start_worker(app)
            self.assertTrue(app.lcu.pages_reached.wait(timeout=2.0))
            app._rune_import_draft_active = False
            app.lcu.session = None
            app.lcu.session_status = 404
            self.finish_worker(worker, app)

        self.run_with_selection(exercise)

        self.assertEqual(app.lcu.writes, [])
        self.assertNotIn("success", [event["type"] for event in self.events(app)])

    def test_new_request_generation_supersedes_running_request(self):
        app = self.make_app()
        app.lcu.block_pages()

        def exercise():
            worker = self.start_worker(app)
            self.assertTrue(app.lcu.pages_reached.wait(timeout=2.0))
            app._rune_import_generation = 2
            self.finish_worker(worker, app)

        self.run_with_selection(exercise)

        self.assertEqual(app.lcu.writes, [])
        self.assertNotIn("success", [event["type"] for event in self.events(app)])

    def test_old_completion_cannot_replace_newest_success(self):
        app = self.make_app()
        app.lcu.block_pages()

        def exercise():
            old_worker = self.start_worker(app)
            self.assertTrue(app.lcu.pages_reached.wait(timeout=2.0))
            app._rune_import_generation = 2
            app.current_rune_champion = "Nocturne"
            app.current_rune_choices = self.m.rune_choices_for_role("Nocturne", "JUNGLE")
            app.lcu.session = app.lcu.make_session(2, "JUNGLE", game_id=1001)
            self.finish_worker(old_worker, app)

            app.lcu.pages_reached.clear()
            new_worker = self.start_worker(
                app,
                champion="Nocturne",
                generation=2,
            )
            self.finish_worker(new_worker, app)

        self.run_with_selection(exercise)

        events = self.events(app)
        successes = [event for event in events if event["type"] == "success"]
        self.assertEqual(len(app.lcu.writes), 1)
        self.assertEqual(app.lcu.writes[0]["payload"]["name"], "RiftSense - Nocturne")
        self.assertEqual([event["generation"] for event in successes], [2])

    def test_shutdown_before_mutation_prevents_write(self):
        app = self.make_app()
        app.lcu.block_pages()

        def exercise():
            worker = self.start_worker(app)
            self.assertTrue(app.lcu.pages_reached.wait(timeout=2.0))
            app._rune_import_shutdown = True
            app._rune_import_generation += 1
            self.finish_worker(worker, app)

        self.run_with_selection(exercise)

        self.assertEqual(app.lcu.writes, [])
        self.assertNotIn("success", [event["type"] for event in self.events(app)])

    def test_each_pending_request_gets_a_new_generation(self):
        app = self.make_app(generation=0)
        app._rune_import_thread = type(
            "AliveThread",
            (),
            {"is_alive": lambda self: True},
        )()
        app._pending_rune_import_request = None
        app.last_rune_import_signature = None

        self.m.App._start_rune_import(
            app,
            "Wukong",
            "JUNGLE",
            "recommended",
        )
        first_pending = app._pending_rune_import_request
        self.m.App._start_rune_import(
            app,
            "Nocturne",
            "JUNGLE",
            "recommended",
        )
        second_pending = app._pending_rune_import_request

        self.assertEqual(first_pending[-2], 1)
        self.assertEqual(second_pending[-2], 2)
        self.assertEqual(second_pending[0], "Nocturne")

    def test_superseded_during_lcu_write_does_not_report_success(self):
        app = self.make_app()
        app.lcu.block_write()

        def exercise():
            worker = self.start_worker(app)
            self.assertTrue(app.lcu.write_reached.wait(timeout=2.0))
            app._rune_import_generation = 2
            self.finish_worker(worker, app)

        self.run_with_selection(exercise)

        events = self.events(app)
        self.assertEqual(len(app.lcu.writes), 1)
        self.assertNotIn("success", [event["type"] for event in events])

    def test_replacement_session_with_same_context_rejects_old_request(self):
        app = self.make_app()
        app.lcu.block_pages()
        session_a_identity = app._rune_import_session_identity

        def exercise():
            worker = self.start_worker(
                app,
                session_identity=session_a_identity,
            )
            self.assertTrue(app.lcu.pages_reached.wait(timeout=2.0))
            app.lcu.session = app.lcu.make_session(
                1,
                "JUNGLE",
                game_id=1002,
                cell_id=7,
            )
            self.finish_worker(worker, app)

        self.run_with_selection(exercise)

        events = self.events(app)
        self.assertEqual(app.lcu.writes, [])
        self.assertNotIn("success", [event["type"] for event in events])
        self.assertNotIn("error", [event["type"] for event in events])

    def test_new_request_in_replacement_session_succeeds(self):
        app = self.make_app()
        app.lcu.block_pages()
        session_a_identity = app._rune_import_session_identity

        def exercise():
            old_worker = self.start_worker(
                app,
                session_identity=session_a_identity,
            )
            self.assertTrue(app.lcu.pages_reached.wait(timeout=2.0))
            app.lcu.session = app.lcu.make_session(
                1,
                "JUNGLE",
                game_id=1002,
                cell_id=7,
            )
            self.finish_worker(old_worker, app)

            app._rune_import_generation = 2
            app._rune_import_session_identity = (
                self.m.App._champ_select_session_identity(app.lcu.session)
            )
            app.lcu.pages_reached.clear()
            new_worker = self.start_worker(
                app,
                generation=2,
            )
            self.finish_worker(new_worker, app)

        self.run_with_selection(exercise)

        events = self.events(app)
        successes = [event for event in events if event["type"] == "success"]
        self.assertEqual(len(app.lcu.writes), 1)
        self.assertEqual([event["generation"] for event in successes], [2])

    def test_session_change_during_write_cannot_report_success(self):
        app = self.make_app()
        app.lcu.block_write()

        def exercise():
            worker = self.start_worker(app)
            self.assertTrue(app.lcu.write_reached.wait(timeout=2.0))
            app.lcu.session = app.lcu.make_session(
                1,
                "JUNGLE",
                game_id=1002,
                cell_id=7,
            )
            self.finish_worker(worker, app)

        self.run_with_selection(exercise)

        events = self.events(app)
        self.assertEqual(len(app.lcu.writes), 1)
        self.assertNotIn("success", [event["type"] for event in events])
        self.assertNotIn("error", [event["type"] for event in events])

    def test_missing_session_identity_fails_closed(self):
        app = self.make_app()
        app.lcu.session = app.lcu.make_session(
            1,
            "JUNGLE",
            game_id=None,
        )
        app._rune_import_session_identity = None

        def exercise():
            worker = self.start_worker(app, session_identity=("gameId", 1001))
            self.finish_worker(worker, app)

        self.run_with_selection(exercise)

        self.assertEqual(app.lcu.writes, [])
        self.assertNotIn("success", [event["type"] for event in self.events(app)])


if __name__ == "__main__":
    unittest.main()
