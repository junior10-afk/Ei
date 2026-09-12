import sys, unittest
from pathlib import Path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

import brain.agent_loop as alo
from brain.agent_loop import AgentEngine

class TestAgentPlan(unittest.TestCase):
    def setUp(self):
        self.engine = AgentEngine(max_iterations=2)

    def test_is_complex_query(self):
        self.assertTrue(self.engine._is_complex_query("organise mon voyage à Lomé"))
        self.assertFalse(self.engine._is_complex_query("bonjour"))

    def test_build_llm_plan_json(self):
        alo.llm_cascade = type("F", (), {"ask_with_system": lambda self, t, s: '["Chercher les vols", "Comparer les prix", "Rédiger le récap"]'})()
        steps = self.engine._build_llm_plan("organise un voyage à Lomé", alo.ORCHESTRATOR)
        self.assertEqual(len(steps), 3)
        self.assertIn("vols", steps[0])

    def test_build_llm_plan_garbage_renvoie_liste_vide(self):
        alo.llm_cascade = type("F", (), {"ask_with_system": lambda self, t, s: "je ne sais pas"})()
        self.assertEqual(self.engine._build_llm_plan("compare X et Y", alo.ORCHESTRATOR), [])

    def test_build_llm_plan_llm_down_renvoie_liste_vide(self):
        alo.llm_cascade = type("F", (), {"ask_with_system": lambda self, t, s: None})()
        self.assertEqual(self.engine._build_llm_plan("compare X et Y", alo.ORCHESTRATOR), [])

if __name__ == "__main__":
    unittest.main()
