import sys
import time
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

from core.database import db
from core.task_manager import task_manager
from core.scheduler import scheduler
from tools.registry import tool_registry
from brain.dispatcher import dispatcher
from brain.agent_loop import agent_engine
import tools

def run_tests():
    print("=== TEST 1: Base de Données SQLite & Mémoire Sémantique FTS5 ===")
    db.remember_fact("code_porte", "Le code du bureau est 9988", category="securite")
    exact = db.recall_fact("code_porte")
    print("Exact match:", exact["value"] if exact else "Non trouvé")
    assert exact and "9988" in exact["value"]

    # Test FTS5 / sémantique
    fuzzy = db.recall_fact("comment entrer dans le bureau ?")
    print("Fuzzy/Semantic match:", fuzzy["value"] if fuzzy else "Non trouvé")
    assert fuzzy and "9988" in fuzzy["value"]
    print("SQLite & FTS5 OK!")

    print("\n=== TEST 2: Tool Registry & Native Function Schemas ===")
    gemini_tools = tool_registry.get_gemini_tools()
    openai_tools = tool_registry.get_openai_tools()
    print(f"Outils enregistrés: {len(tool_registry.list_tools())}")
    print(f"Schémas OpenAI générés: {len(openai_tools)}")
    print(f"Schémas Gemini générés: {gemini_tools is not None}")
    assert len(openai_tools) >= 15
    assert gemini_tools is not None
    print("Tool Registry Native Schemas OK!")

    print("\n=== TEST 3: Gestionnaire de Tâches Asynchrones (TaskManager) ===")
    def dummy_task(x, y):
        time.sleep(0.3)
        return x + y

    t_id = task_manager.submit_task("Calcul Asynchrone Test", dummy_task, 40, 2)
    print(f"Tâche soumise avec ID: {t_id}")
    time.sleep(0.6)
    t_status = task_manager.get_task(t_id)
    print(f"Statut tâche: {t_status['status']}, Résultat: {t_status['result']}")
    assert t_status["status"] == "completed"
    assert t_status["result"] == 42
    print("TaskManager OK!")

    print("\n=== TEST 4: Planificateur Temporel & Rappels Proactifs (Scheduler) ===")
    rem_id = scheduler.add_reminder("Vérifier le serveur", 2, label="Serveur")
    active = scheduler.list_active()
    print(f"Rappels actifs: {len(active)}")
    assert len(active) >= 1
    scheduler.cancel_reminder(rem_id)
    print("Scheduler OK!")

    print("\n=== TEST 5: Dispatcher Intelligent (Repli hors-ligne vs Agent) ===")
    fallback = dispatcher._route_query("ouvre chrome")
    print(f"Repli hors-ligne ('ouvre chrome') -> règle: {fallback is not None}")
    assert fallback is not None and fallback["action"] == "open_app"

    no_route = dispatcher._route_query("prépare-moi un comparatif de licious vs stripe")
    print(f"Requête libre -> déléguée à l'agent (pas de règle): {no_route is None}")
    assert no_route is None
    print("Dispatcher LLM-first / Repli OK!")

    print("\n=== TEST 6: Double Restitution de l'AgentEngine (Voix / HUD Markdown) ===")
    voice_s, detailed_m = agent_engine._parse_dual_output("""
Voici le rapport complet :
### Analyse du système
- Point 1 : Performance optimale
- Point 2 : Tous les services actifs

```python
def health():
    return True
```
VOICE_SUMMARY: Tous les systèmes sont opérationnels et les services fonctionnent normalement.
""")
    print("Speech summary (Voix):", voice_s)
    print("Detailed markdown lines:", len(detailed_m.splitlines()))
    assert "Tous les systèmes" in voice_s
    assert "### Analyse" in detailed_m
    print("AgentEngine Dual Output OK!")

    print("\n========================================================")
    print(" TOUS LES TESTS D'AGENT IA V2 SONT VALIDÉS AVEC SUCCÈS !")
    print("========================================================")

if __name__ == "__main__":
    run_tests()
