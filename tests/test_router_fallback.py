import sys, unittest
from pathlib import Path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from brain.dispatcher import Dispatcher

class TestRouteQuery(unittest.TestCase):
    def setUp(self):
        self.d = Dispatcher()

    def test_volume(self):
        r = self.d._route_query("mets le volume à 50")
        self.assertIsNotNone(r)
        self.assertEqual(r["action"], "set_system_volume")
        self.assertEqual(r["params"]["level"], 50)

    def test_open_app(self):
        r = self.d._route_query("ouvre chrome")
        self.assertEqual(r["action"], "open_app")
        self.assertEqual(r["params"]["app_name"], "chrome")

    def test_cancel_timer(self):
        r = self.d._route_query("annule le minuteur")
        self.assertEqual(r["action"], "cancel_timer")

    def test_phrase_normale_non_routee(self):
        self.assertIsNone(self.d._route_query("prépare-moi un comparatif de licious vs stripe"))
        self.assertIsNone(self.d._route_query("bonjour"))

if __name__ == "__main__":
    unittest.main()
