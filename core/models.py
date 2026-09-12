"""Catalogue et routage des modèles LLM d'Ei.

Étages de décision :
  0. Outils déterministes (regex du dispatcher) -> 0 coût, 0 LLM.
  1. Classification LOCALE de la requête -> tier "chat" | "light" | "heavy".
  2. Sélection du modèle :
       - mode "auto"    : modèle par défaut du tier (config models.tiers).
       - mode "ask"     : fenêtre HUD de sélection uniquement pour "heavy".
       - mode "always"  : fenêtre HUD pour toute requête LLM.
  3. Exécution avec le modèle choisi ; repli sur la cascade si échec.

La fenêtre de sélection passe par le bus WebSocket :
  Runtime -> HUD : {"type": "model_select", task, tier, suggested, options}
  HUD -> Runtime  : {"type": "model_select_response", model_id}
"""
import os
import re
import threading
import time
from typing import Any, Dict, List, Optional

from core.config import config

TIER_CHAT = "chat"
TIER_LIGHT = "light"
TIER_HEAVY = "heavy"

# Catalogue par défaut (fusionné/écrasé par config.json -> models.catalog)
DEFAULT_CATALOG: List[Dict[str, Any]] = [
    {
        "id": "groq-llama-8b",
        "label": "Llama 3.1 8B (Groq)",
        "provider": "groq",
        "model": "llama-3.1-8b-instant",
        "key_env": "GROQ_API_KEY",
        "cost": "gratuit",
        "latency": "ultra-rapide",
        "description": "Réponses instantanées, chat et questions simples.",
        "tiers": [TIER_CHAT],
    },
    {
        "id": "gemini-flash",
        "label": "Gemini 2.5 Flash",
        "provider": "gemini",
        "model": "gemini-2.5-flash",
        "key_env": "GEMINI_API_KEY",
        "cost": "gratuit (quota)",
        "latency": "rapide",
        "description": "Polyvalent : chat avancé, petites tâches, résumés.",
        "tiers": [TIER_CHAT, TIER_LIGHT, TIER_HEAVY],
    },
    {
        "id": "groq-llama-70b",
        "label": "Llama 3.3 70B (Groq)",
        "provider": "groq",
        "model": "llama-3.3-70b-versatile",
        "key_env": "GROQ_API_KEY",
        "cost": "gratuit (quota)",
        "latency": "rapide",
        "description": "Raisonnement solide, rédaction, traduction, code léger.",
        "tiers": [TIER_LIGHT],
    },
    {
        "id": "gpt-4o-mini",
        "label": "GPT-4o mini",
        "provider": "openai",
        "model": "gpt-4o-mini",
        "key_env": "OPENAI_API_KEY",
        "cost": "faible",
        "latency": "rapide",
        "description": "Petites tâches fiables, bon rapport qualité/prix.",
        "tiers": [TIER_LIGHT],
    },
    {
        "id": "mistral-small",
        "label": "Mistral Small",
        "provider": "mistral",
        "model": "mistral-small-latest",
        "key_env": "MISTRAL_API_KEY",
        "cost": "faible",
        "latency": "rapide",
        "description": "Tâches courtes, très bon en français.",
        "tiers": [TIER_CHAT, TIER_LIGHT],
    },
    {
        "id": "ollama-local",
        "label": "Ollama (local)",
        "provider": "ollama",
        "model": "llama3.2",
        "key_env": "",
        "cost": "gratuit (local)",
        "latency": "variable",
        "description": "100 % hors-ligne sur ta machine, privé.",
        "tiers": [TIER_CHAT, TIER_LIGHT],
    },
    {
        "id": "gemini-pro",
        "label": "Gemini 3.1 Pro",
        "provider": "gemini",
        "model": "gemini-3.1-pro-preview",
        "key_env": "GEMINI_API_KEY",
        "cost": "élevé (payant)",
        "latency": "lente",
        "description": "Gros travaux : code complet, sites, longues rédactions. Nécessite un plan Gemini payant.",
        "tiers": [TIER_HEAVY],
    },
    {
        "id": "gpt-4o",
        "label": "GPT-4o",
        "provider": "openai",
        "model": "gpt-4o",
        "key_env": "OPENAI_API_KEY",
        "cost": "élevé",
        "latency": "moyenne",
        "description": "Tâches complexes, code de bout en bout.",
        "tiers": [TIER_HEAVY],
    },
]

DEFAULT_TIERS: Dict[str, str] = {
    TIER_CHAT: "gemini-flash",
    TIER_LIGHT: "groq-llama-70b",
    TIER_HEAVY: "gemini-pro",
}

# --- Classification locale (0 appel réseau, 0 coût) -------------------------

_HEAVY_PATTERNS = [
    r"\b(cr[ée]e|cr[ée]er|construis|construire|d[ée]veloppe|d[ée]velopper|programme|impl[ée]mente|g[ée]n[èe]re)\b.{0,40}\b(site|site web|application|app|jeu|logiciel|script|api|bot|interface|page|portfolio|landing|dashboard|outil|programme)\b",
    r"\b(refactor|optimise le code|d[ée]bogue|debug|corrige le code|architecture logicielle|base de donn[ée]es)\b",
    r"\b(r[ée]dige|écris|r[ée]daction)\b.{0,40}\b(article|rapport|m[ée]moire|livre|chapitre|plan complet|strat[ée]gie|dossier|cours complet)\b",
    r"\b(analyse|compare|audit)\b.{0,40}\b(complet|complète|approfondi|en d[ée]tail|document|code|projet)\b",
    r"\b(projet|programme|application)\b.{0,30}\b(complet|entier|de a à z|de z[ée]ro)\b",
]

_LIGHT_PATTERNS = [
    r"\b(traduis|traduction|corrige (?:la phrase|le texte|mon texte)|r[ée]sume|reformule|explique|d[ée]finition|que veut dire|comment faire)\b",
    r"\b(id[ée]es|liste|propose|sugg[èe]re|brouillon|email|message)\b",
    r"\b(code|fonction|script|regex|sql|excel|formule)\b",
]

_CHAT_PATTERNS = [
    r"^(bonjour|salut|coucou|bonsoir|merci|remercie|au revoir|[çc]a va|qui es[- ]tu|que sais[- ]tu faire)\b",
    r"\b(heure|date|jour(?:n[ée]e)?)\b",
    r"\b(pense[ée]?[ -]?tu|aime[z]?[- ]?tu|parle[- ]?(?:moi|de))\b",
]


def classify_task(text: str) -> str:
    """Classe une requête en tier 'chat' | 'light' | 'heavy' (heuristique locale)."""
    clean = text.lower().strip()

    # Requêtes très longues -> probablement une tâche complexe
    if len(clean) > 220:
        return TIER_HEAVY

    heavy_hits = sum(1 for p in _HEAVY_PATTERNS if re.search(p, clean))
    light_hits = sum(1 for p in _LIGHT_PATTERNS if re.search(p, clean))
    chat_hits = sum(1 for p in _CHAT_PATTERNS if re.search(p, clean))

    if heavy_hits >= 1:
        return TIER_HEAVY
    if chat_hits >= 1 and light_hits == 0:
        return TIER_CHAT
    if light_hits >= 1:
        return TIER_LIGHT
    # Questions ouvertes courtes -> chat ; questions ouvertes longues -> light
    return TIER_CHAT if len(clean) < 80 else TIER_LIGHT


# --- Catalogue ---------------------------------------------------------------

def get_catalog() -> List[Dict[str, Any]]:
    models_cfg = config.get("models", {}) or {}
    catalog = models_cfg.get("catalog")
    if not catalog:
        catalog = DEFAULT_CATALOG
    return catalog


def get_model(model_id: str) -> Optional[Dict[str, Any]]:
    for m in get_catalog():
        if m.get("id") == model_id:
            return m
    return None


# Références dynamiques 'fournisseur/nom-du-modele' (listées via brain/providers)
_KEY_ENV_BY_PROVIDER = {
    "gemini": "GEMINI_API_KEY",
    "groq": "GROQ_API_KEY",
    "openai": "OPENAI_API_KEY",
    "mistral": "MISTRAL_API_KEY",
    "ollama": "",
}


def parse_tier_ref(ref: str) -> Optional[Dict[str, Any]]:
    """Résilie une référence de tier : ID du catalogue d'abord, sinon une
    référence dynamique 'provider/model-name' renvoyée par l'API live du
    fournisseur (n'importe quel modèle Google/Groq/OpenAI/Mistral/Ollama).
    """
    if not ref:
        return None
    known = get_model(ref)
    if known:
        return known
    if "/" in ref:
        provider, _, model_name = ref.partition("/")
        provider = provider.lower().strip()
        model_name = model_name.strip()
        if provider in _KEY_ENV_BY_PROVIDER and model_name:
            return {
                "id": ref,
                "label": f"{model_name} ({provider})",
                "provider": provider,
                "model": model_name,
                "key_env": _KEY_ENV_BY_PROVIDER[provider],
                "cost": "",
                "latency": "",
                "description": "Modèle sélectionné directement chez le fournisseur.",
                "tiers": [],
            }
    return None


def is_model_available(model: Optional[Dict[str, Any]]) -> bool:
    """Vérifie si le modèle est utilisable (clé API présente ou local)."""
    if not model:
        return False
    provider = (model.get("provider") or "").lower()
    if provider == "ollama":
        return True
    key_env = model.get("key_env") or _KEY_ENV_BY_PROVIDER.get(provider, "")
    return bool(key_env and os.getenv(key_env, "").strip().strip('"\''))


def default_model_for_tier(tier: str) -> Optional[Dict[str, Any]]:
    models_cfg = config.get("models", {}) or {}
    tiers = {**DEFAULT_TIERS, **(models_cfg.get("tiers") or {})}
    preferred = tiers.get(tier)
    if preferred:
        model = parse_tier_ref(preferred)
        if model and is_model_available(model):
            return model
    # Repli 1 : modèle du catalogue qui couvre le tier ET dont la clé est configurée
    for m in get_catalog():
        if tier in (m.get("tiers") or []) and is_model_available(m):
            return m
    # Repli 2 : n'importe quel modèle du catalogue dont la clé est configurée
    for m in get_catalog():
        if is_model_available(m):
            return m
    # Repli 3 : modèle préféré sans vérification si aucune clé n'est encore enregistrée
    if preferred:
        model = parse_tier_ref(preferred)
        if model:
            return model
    for m in get_catalog():
        if tier in (m.get("tiers") or []):
            return m
    return None


def catalog_public_view() -> List[Dict[str, Any]]:
    """Vue sans secrets pour le HUD."""
    return [
        {
            "id": m.get("id"),
            "label": m.get("label", m.get("id")),
            "provider": m.get("provider", ""),
            "model": m.get("model", ""),
            "cost": m.get("cost", ""),
            "latency": m.get("latency", ""),
            "description": m.get("description", ""),
            "tiers": m.get("tiers", []),
        }
        for m in get_catalog()
    ]


# --- Demande de choix à l'utilisateur via le HUD -----------------------------

class ModelChoiceRequest:
    """Une seule demande de choix à la fois (le dispatcher sérialise déjà)."""

    def __init__(self):
        self._lock = threading.Lock()
        self._event: Optional[threading.Event] = None
        self._answer: Optional[str] = None

    def request(self, task_text: str, tier: str, suggested_id: Optional[str],
                options: List[Dict[str, Any]], timeout_sec: float = 120.0) -> Optional[str]:
        """Diffuse la fenêtre de sélection au HUD et bloque jusqu'à la réponse.

        Retourne le model_id choisi, 'auto' (laisser Ei décider), ou None si
        timeout / aucun HUD connecté.
        """
        from core.bus import bus  # import différé : évite une dépendance circulaire

        if not bus.clients:
            print("[Models] Aucun HUD connecté : choix automatique.")
            return None

        event = threading.Event()
        with self._lock:
            self._event = event
            self._answer = None

        bus.broadcast_threadsafe({
            "type": "model_select",
            "task": task_text,
            "tier": tier,
            "tier_label": {"chat": "Conversation", "light": "Tâche légère", "heavy": "Tâche complexe"}.get(tier, tier),
            "suggested": suggested_id,
            "options": options,
        })
        print(f"[Models] Sélection de modèle demandée à l'utilisateur (tier={tier}).")

        got = event.wait(timeout_sec)
        with self._lock:
            answer = self._answer
            self._event = None
        if not got or answer is None:
            print("[Models] Aucune réponse reçue : choix automatique.")
            return None
        if answer == "auto":
            return None
        return answer

    def resolve(self, model_id: Optional[str]):
        """Appelé par le handler WebSocket quand le HUD répond."""
        with self._lock:
            event = self._event
            if event is not None:
                self._answer = model_id
        if event is not None:
            event.set()


model_choice = ModelChoiceRequest()


def should_ask_user(tier: str) -> bool:
    mode = str(config.get("model_choice_mode", "auto")).lower()
    if mode == "always":
        return True
    if mode == "ask":
        return tier == TIER_HEAVY
    return False


def route_model_for_task(task_text: str) -> Dict[str, Any]:
    """Point d'entrée du dispatcher : classe la tâche et retourne le modèle retenu.

    Retourne {"tier", "model", "asked"} — model peut être None (repli cascade).
    """
    tier = classify_task(task_text)
    default = default_model_for_tier(tier)
    asked = False
    chosen_id = None

    if should_ask_user(tier):
        asked = True
        chosen_id = model_choice.request(
            task_text=task_text,
            tier=tier,
            suggested_id=(default or {}).get("id"),
            options=catalog_public_view(),
        )

    model = parse_tier_ref(chosen_id) if chosen_id else default
    if chosen_id and model is None:
        print(f"[Models] Modèle inconnu '{chosen_id}', repli sur le défaut du tier.")
        model = default
    return {"tier": tier, "model": model, "asked": asked}
