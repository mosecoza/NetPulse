import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))


class ProjectLayoutTests(unittest.TestCase):
    def test_daemon_packages_are_importable(self):
        import netpulse.api
        import netpulse.core
        import netpulse.diagnostics
        import netpulse.storage

    def test_dashboard_entry_exists(self):
        self.assertTrue((PROJECT_ROOT / "frontend" / "index.html").is_file())


if __name__ == "__main__":
    unittest.main()
