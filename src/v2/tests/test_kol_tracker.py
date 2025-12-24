import unittest
from src.v2.monitoring.kol_tracker import track_kols

class TestKOLTracker(unittest.TestCase):
    def test_track_kols_runs(self):
        try:
            track_kols()
        except Exception as e:
            self.fail(f"track_kols() raised Exception unexpectedly: {e}")

if __name__ == "__main__":
    unittest.main()