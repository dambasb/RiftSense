import tempfile, unittest
from pathlib import Path
from riftsense.core.storage import load_json, write_json_atomic
class StorageTests(unittest.TestCase):
    def test_round_trip(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"x.json"; ok,err=write_json_atomic(p,{"x":1}); self.assertTrue(ok,err); self.assertEqual(load_json(p),{"x":1})
    def test_invalid_default(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"x.json"; p.write_text("{broken",encoding="utf-8"); self.assertEqual(load_json(p,[]),[])
