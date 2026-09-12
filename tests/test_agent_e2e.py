import sys, unittest
from pathlib import Path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

import brain.agent_loop as alo
from brain.agent_loop import agent_engine
from tools.registry import tool_registry


@tool_registry.register(name="test_counter", description="outil de test incrémental",
                        parameters={"n": "int (valeur du compteur)"})
def test_counter(n: int = 1):
    return {"result": f"ok-{n}", "speech": f"compteur à {n}"}


class FakeLLM:
    """LLM scripté : renvoie les tours prévus, mémorise les prompts reçus."""
    def __init__(self, script):
        self.script = list(script)
        self.calls = []

    def ask_with_model(self, user_text, model, system_prompt):
        self.calls.append(system_prompt)
        return self.script.pop(0) if self.script else "FINAL_ANSWER: Fin.\nVOICE_SUMMARY: Fin."

    def ask_with_system(self, user_text, system_prompt):
        return self.ask_with_model(user_text, model=None, system_prompt=system_prompt)


class TestAgentReActChain(unittest.TestCase):
    def setUp(self):
        self._real_cascade = alo.llm_cascade
        # Forcer le chemin ReAct textuel (neutralise les chemins FC natifs)
        agent_engine._run_native_gemini = lambda *a, **k: None
        agent_engine._run_native_openai = lambda *a, **k: None

    def tearDown(self):
        alo.llm_cascade = self._real_cascade
        tool_registry._tools.pop("test_counter", None)
        tool_registry._tools.pop("test_fail", None)

    def test_chainage_2_outils_avec_observations_reinjectees(self):
        fake = FakeLLM([
            'THOUGHT: je commence\nACTION: {"action": "test_counter", "params": {"n": 1}}',
            'THOUGHT: j\'enchaîne\nACTION: {"action": "test_counter", "params": {"n": 2}}',
            'THOUGHT: terminé\nFINAL_ANSWER: Compteurs 1 et 2 faits.\nVOICE_SUMMARY: Deux compteurs faits.',
        ])
        alo.llm_cascade = fake
        speech, detailed = agent_engine.run("chaîne de test multi-coups")
        self.assertIn("Deux compteurs", speech)
        # PREUVE d'agent : l'observation du tour 1 ("ok-1") est réinjectée au tour 2
        self.assertIn("ok-1", fake.calls[1])
        self.assertEqual(len(fake.calls), 3)

    def test_erreur_outil_renvoyee_au_llm(self):
        @tool_registry.register(name="test_fail", description="échoue exprès", parameters={})
        def test_fail():
            raise ValueError("boom")

        fake = FakeLLM([
            'THOUGHT: je tente\nACTION: {"action": "test_fail", "params": {}}',
            'THOUGHT: je corrige\nFINAL_ANSWER: Rattrapé.\nVOICE_SUMMARY: Rattrapé.',
        ])
        alo.llm_cascade = fake
        speech, detailed = agent_engine.run("test de récupération sur erreur")
        self.assertIn("Rattrapé", speech)
        # Le détail de l'erreur de l'outil est bien parvenu au LLM au tour suivant
        self.assertIn("boom", fake.calls[1])


if __name__ == "__main__":
    unittest.main()
