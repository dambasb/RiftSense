import importlib.util
import os
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP_PATH = ROOT / "RiftSense.py"


def load_app_module():
    os.environ["LOCALAPPDATA"] = tempfile.mkdtemp(prefix="riftsense-rank-range-test-")
    spec = importlib.util.spec_from_file_location("riftsense_rank_range_test", APP_PATH)
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


class RankProgressRegressionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.m = load_app_module()

    def test_rank_range_filters_and_window_widths(self):
        m = self.m

        class Dummy:
            _general_progress_range_days = m.App._general_progress_range_days
            _general_progress_timestamp = m.App._general_progress_timestamp
            _filter_general_progress_range = m.App._filter_general_progress_range
            _general_progress_window_bounds = m.App._general_progress_window_bounds

            def __init__(self):
                self.general_progress_range_var = Value("7D")

        dummy = Dummy()
        newest = datetime(2026, 8, 23, 12, 0, 0)
        ages = [0, 3, 7, 8, 20, 30, 31, 60, 90, 91, 200, 365, 366, 500]
        rows = [
            {
                "captured_at": (newest - timedelta(days=age)).isoformat(),
                "age": age,
            }
            for age in ages
        ]
        expected = {
            "7D": [0, 3, 7],
            "30D": [0, 3, 7, 8, 20, 30],
            "90D": [0, 3, 7, 8, 20, 30, 31, 60, 90],
            "1Y": [0, 3, 7, 8, 20, 30, 31, 60, 90, 91, 200, 365],
            "ALL": ages,
        }
        expected_width = {"7D": 7, "30D": 30, "90D": 90, "1Y": 365, "ALL": 500}

        for range_name, expected_ages in expected.items():
            dummy.general_progress_range_var.set(range_name)
            filtered = dummy._filter_general_progress_range(rows)
            self.assertEqual([row["age"] for row in filtered], expected_ages)
            left, right = dummy._general_progress_window_bounds(rows)
            self.assertIsNotNone(left)
            self.assertIsNotNone(right)
            self.assertAlmostEqual((right - left) / 86400.0, expected_width[range_name])


if __name__ == "__main__":
    unittest.main()
