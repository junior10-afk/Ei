import sys, unittest
from pathlib import Path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from unittest.mock import patch
from brain.dispatcher import Dispatcher
from core.config import config

class TestLLMFirst(unittest.TestCase):
    def test_ouvre_chrome_passe_par_agent_engine(self):
        d = Dispatcher()
        with patch("brain.dispatcher.agent_engine.run", return_value=("C'est fait.", "C'est fait.")) as m_run, \
             patch("brain.dispatcher.tts_engine.speak") as m_speak, \
             patch("brain.dispatcher.tool_registry.execute") as m_exec:
            d._process_sync("ouvre chrome", is_voice=False)
            m_run.assert_called_once()          # le LLM décide
            m_exec.assert_not_called()          # pas d'exécution directe

    def test_repli_hors_ligne_si_pas_de_cle(self):
        d = Dispatcher()
        with patch("brain.dispatcher.os.getenv", return_value=""), \
             patch.object(type(config), "gemini_api_key", property(lambda self: "")), \
             patch("brain.dispatcher.tool_registry.execute", return_value={"speech": "Voilà."}) as m_exec, \
             patch("brain.dispatcher.agent_engine.run") as m_run, \
             patch("brain.dispatcher.tts_engine.speak"):
            d._process_sync("ouvre chrome", is_voice=False)
            m_exec.assert_called_once()         # règle de secours
            m_run.assert_not_called()           # pas de LLM (indisponible)

if __name__ == "__main__":
    unittest.main()
