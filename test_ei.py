import sys
from pathlib import Path
BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

from core.config import config
from core.state import state_manager, AssistantState
from brain.local_replies import check_local_reply, get_wake_ack
from brain.dispatcher import dispatcher
from tools.registry import tool_registry
import tools

def run_tests():
    print("=== TEST 1: Config ===")
    print(f"Assistant Name: {config.get('assistant_name')}")
    print(f"User Name: {config.get('user_name')}")
    assert config.get('assistant_name') == "EI"
    print("Config OK!")

    print("\n=== TEST 2: Local Replies ===")
    g1 = check_local_reply("bonjour")
    print(f"'bonjour' -> {g1}")
    assert g1 is not None

    h1 = check_local_reply("quelle heure est-il")
    print(f"'quelle heure est-il' -> {h1}")
    assert h1 is not None

    m1 = check_local_reply("calcule 25 * 4")
    print(f"'calcule 25 * 4' -> {m1}")
    assert "100" in m1
    print("Local Replies OK!")

    print("\n=== TEST 3: Tools Registry ===")
    tools_list = tool_registry.list_tools()
    print(f"Outils enregistrés: {[t.name for t in tools_list]}")
    assert len(tools_list) >= 5

    w_res = tool_registry.execute("get_weather", {"city": "Paris"})
    print(f"Météo Paris: {w_res['speech']}")
    assert w_res["success"] is True

    mem_res = tool_registry.execute("remember_fact", {"key": "couleur", "value": "bleu"})
    print(f"Mémoire: {mem_res['speech']}")
    assert mem_res["success"] is True

    recall_res = tool_registry.execute("recall_fact", {"key": "couleur"})
    print(f"Rappel: {recall_res['speech']}")
    assert "bleu" in recall_res["speech"]
    print("Tools OK!")

    print("\n=== TEST 4: Dispatcher match deterministic ===")
    match_app = dispatcher._match_deterministic_tools("ouvre le bloc-notes")
    print(f"Match app: {match_app}")
    assert match_app is not None and match_app["action"] == "open_app"

    match_vol = dispatcher._match_deterministic_tools("mets le volume à 40")
    print(f"Match volume: {match_vol}")
    assert match_vol is not None and match_vol["params"]["level"] == 40
    print("Dispatcher matching OK!")

    print("\n==========================================")
    print(" TOUS LES TESTS D'INTÉGRATION SONT VALIDÉS !")
    print("==========================================")

if __name__ == "__main__":
    run_tests()
