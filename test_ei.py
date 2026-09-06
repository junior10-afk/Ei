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
    # Minuteur
    t_res = tool_registry.execute("set_timer", {"duration": 10, "unit": "secondes", "label": "test"})
    print(f"Minuteur: {t_res['speech']}")
    assert t_res["success"] is True

    c_res = tool_registry.execute("cancel_timer", {"label": "test"})
    print(f"Annulation minuteur: {c_res['speech']}")
    assert c_res["success"] is True

    # Panneaux
    p_res = tool_registry.execute("open_panel", {"panel": "settings"})
    print(f"Panneau: {p_res['speech']}")
    assert p_res["success"] is True

    # Orbes 3D
    orb_res = tool_registry.execute("set_orb", {"preset_name": "gargantua"})
    print(f"Orbe: {orb_res['speech']}")
    assert orb_res["success"] is True
    assert orb_res["result"]["preset_id"] == "gargantua"

    print("Tools OK!")

    print("\n=== TEST 4: Dispatcher match deterministic ===")
    match_app = dispatcher._match_deterministic_tools("ouvre le bloc-notes")
    print(f"Match app: {match_app}")
    assert match_app is not None and match_app["action"] == "open_app"

    match_vol = dispatcher._match_deterministic_tools("mets le volume à 40")
    print(f"Match volume: {match_vol}")
    assert match_vol is not None and match_vol["params"]["level"] == 40

    match_timer = dispatcher._match_deterministic_tools("mets un minuteur de 5 minutes")
    print(f"Match timer: {match_timer}")
    assert match_timer is not None and match_timer["action"] == "set_timer"
    assert match_timer["params"]["duration"] == 5

    match_panel = dispatcher._match_deterministic_tools("ouvre les réglages")
    print(f"Match panel: {match_panel}")
    assert match_panel is not None and match_panel["action"] == "open_panel"
    assert match_panel["params"]["panel"] == "settings"

    match_orbs_panel = dispatcher._match_deterministic_tools("affiche la galerie des orbes")
    print(f"Match orbs panel: {match_orbs_panel}")
    assert match_orbs_panel is not None and match_orbs_panel["action"] == "open_panel"
    assert match_orbs_panel["params"]["panel"] == "orbs"

    match_set_orb = dispatcher._match_deterministic_tools("mets l'orbe Arc Reactor")
    print(f"Match set orb: {match_set_orb}")
    assert match_set_orb is not None and match_set_orb["action"] == "set_orb"
    assert "arc reactor" in match_set_orb["params"]["preset_name"].lower()

    print("Dispatcher matching OK!")

    print("\n=== TEST 5: Sound Feedback Chimes ===")
    from core.utils import play_chime
    play_chime("wake")
    play_chime("ack")
    print("Chimes generated OK!")

    print("\n==========================================")
    print(" TOUS LES TESTS D'INTÉGRATION SONT VALIDÉS !")
    print("==========================================")

if __name__ == "__main__":
    run_tests()

