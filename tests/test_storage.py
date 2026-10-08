import json
import tempfile
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import patch

from riftsense.core.storage import (
    load_json,
    read_json,
    update_json,
    write_json_atomic,
)


class StorageTests(unittest.TestCase):
    def test_round_trip(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "x.json"
            ok, error = write_json_atomic(path, {"x": 1})
            self.assertTrue(ok, error)
            self.assertEqual(load_json(path), {"x": 1})

    def test_failed_replace_preserves_previous_valid_file(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "x.json"
            self.assertTrue(write_json_atomic(path, {"version": 1})[0])

            with patch(
                "riftsense.core.storage.os.replace",
                side_effect=OSError("simulated interruption"),
            ):
                ok, error = write_json_atomic(path, {"version": 2})

            self.assertFalse(ok)
            self.assertIn("simulated interruption", error)
            self.assertEqual(read_json(path), {"version": 1})
            self.assertEqual(list(Path(d).glob(".*.tmp")), [])

    def test_concurrent_updates_do_not_lose_independent_changes(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "state.json"
            self.assertTrue(write_json_atomic(path, {"a": 0, "b": 0})[0])
            start = threading.Barrier(12)

            def increment(key):
                start.wait()

                def apply(state):
                    state[key] = int(state.get(key, 0)) + 1

                ok, error = update_json(path, apply, {"a": 0, "b": 0})
                self.assertTrue(ok, error)

            with ThreadPoolExecutor(max_workers=12) as pool:
                futures = [
                    pool.submit(increment, "a" if index % 2 == 0 else "b")
                    for index in range(12)
                ]
                for future in futures:
                    future.result()

            self.assertEqual(read_json(path), {"a": 6, "b": 6})

    def test_invalid_default(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "x.json"
            path.write_text("{broken", encoding="utf-8")
            self.assertEqual(load_json(path, []), [])
            preserved = list(Path(d).glob("x.json.corrupt-*"))
            self.assertEqual(len(preserved), 1)
            self.assertEqual(preserved[0].read_text(encoding="utf-8"), "{broken")
            self.assertFalse(path.exists())

    def test_missing_file_keeps_default_behavior(self):
        with tempfile.TemporaryDirectory() as d:
            default = {"items": []}
            loaded = read_json(Path(d) / "missing.json", default)
            self.assertEqual(loaded, default)
            self.assertIsNot(loaded, default)

    def test_representative_schema_round_trips_without_changes(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "settings.json"
            payload = {
                "appearance": "DARK",
                "champion_pool_by_role": {"JUNGLE": ["Wukong", "Vi"]},
                "auto_import_runes": False,
                "nested": {"number": 1.25, "none": None},
            }
            ok, error = write_json_atomic(path, payload)
            self.assertTrue(ok, error)
            self.assertEqual(json.loads(path.read_text(encoding="utf-8")), payload)
            self.assertEqual(read_json(path), payload)
