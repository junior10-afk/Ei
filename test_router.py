import sys
from pathlib import Path
BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

from core.models import classify_task, default_model_for_tier, get_model, route_model_for_task, should_ask_user, TIER_CHAT, TIER_LIGHT, TIER_HEAVY

print("=== TEST routeur: classification ===")
cases = [
    ("bonjour, ça va ?", TIER_CHAT),
    ("quelle heure est-il", TIER_CHAT),
    ("crée moi un site pour mon restaurant à Lomé", TIER_HEAVY),
    ("développe une application complète de gestion", TIER_HEAVY),
    ("traduis ce texte en anglais", TIER_LIGHT),
    ("rédige un article complet sur l'IA en Afrique", TIER_HEAVY),
    ("explique-moi la photosynthèse", TIER_LIGHT),
    ("mets un minuteur de 5 minutes", None),  # déterministe, peu importe ici
]
fail = 0
for text, expected in cases:
    got = classify_task(text)
    ok = (expected is None) or (got == expected)
    print(f"  {'OK ' if ok else 'KO '} [{got:5s}] {text}")
    if not ok:
        fail += 1

print("\n=== TEST routeur: catalogue & tiers ===")
for tier in (TIER_CHAT, TIER_LIGHT, TIER_HEAVY):
    m = default_model_for_tier(tier)
    print(f"  tier {tier:5s} -> {m['id'] if m else 'AUCUN'} ({m['label'] if m else ''})")
    assert m is not None, f"aucun modèle pour le tier {tier}"

assert get_model("gemini-pro")["provider"] == "gemini"
assert get_model("inexistant") is None
print("  get_model OK")

print("\n=== TEST routeur: mode de sélection ===")
import core.models as cm
from core.config import config
config.config["model_choice_mode"] = "auto"
assert cm.should_ask_user(TIER_HEAVY) is False
config.config["model_choice_mode"] = "ask"
assert cm.should_ask_user(TIER_HEAVY) is True
assert cm.should_ask_user(TIER_CHAT) is False
config.config["model_choice_mode"] = "always"
assert cm.should_ask_user(TIER_CHAT) is True
print("  should_ask_user OK (auto/ask/always)")

print("\n=== TEST routeur: route sans HUD (repli auto) ===")
config.config["model_choice_mode"] = "ask"
route = route_model_for_task("crée moi un site vitrine pour mon agence")
assert route["tier"] == TIER_HEAVY
assert route["model"] and route["model"]["id"] == "gemini-pro"
print(f"  route heavy -> {route['model']['id']} (pas de HUD: pas de blocage)")

print("\n=== TEST llm: ask_with_model sans clé -> None (repli) ===")
import os
os.environ.pop("GROQ_API_KEY", None)
from brain.llm import llm_cascade
res = llm_cascade.ask_with_model("test", get_model("groq-llama-8b"), "prompt")
assert res is None
print("  ask_with_model -> None sans clé OK")

if fail:
    print(f"\nÉCHEC: {fail} cas de classification incorrects")
    sys.exit(1)
print("\nTOUS LES TESTS DU ROUTEUR PASSENT ✔")
