import time
from typing import Dict, Any
from tools.registry import tool_registry
from core.database import db

def load_memories() -> Dict[str, Any]:
    """Charge toutes les mémoires pour l'injection dans le system prompt."""
    facts = db.get_all_facts(limit=100)
    return {k: {"value": v} for k, v in facts.items()}

@tool_registry.register(
    name="remember_fact",
    description="Mémorise une information, préférence ou note personnelle de manière permanente",
    parameters={
        "key": "str (sujet, mot-clé ou titre du souvenir, ex: 'code portail', 'anniversaire Sophie')",
        "value": "str (ce qu'il faut mémoriser, ex: 'Le code est 4242')",
        "category": "str (catégorie optionnelle, défaut: 'general')"
    },
    category="memory"
)
def remember_fact(key: str, value: str, category: str = "general") -> Dict[str, Any]:
    db.remember_fact(key, value, category=category)
    return {
        "speech": f"C'est noté, j'ai mémorisé cela pour {key}.",
        "data": {"key": key, "value": value, "category": category}
    }

@tool_registry.register(
    name="recall_fact",
    description="Rappelle une information mémorisée par recherche exacte, sémantique ou plein texte",
    parameters={"key": "str (sujet, question ou mot-clé pour retrouver l'information)"},
    category="memory"
)
def recall_fact(key: str) -> Dict[str, Any]:
    fact = db.recall_fact(key)
    if fact:
        val = fact["value"]
        found_key = fact["key"]
        return {
            "speech": f"D'après mes souvenirs concernant {found_key} : {val}.",
            "data": fact
        }
    return {
        "speech": f"Je n'ai aucun souvenir enregistré correspondant à « {key} ».",
        "data": {"found": False}
    }

@tool_registry.register(
    name="forget_fact",
    description="Oublie ou supprime une information précédemment mémorisée (droit à l'oubli / RGPD)",
    parameters={"key": "str (sujet ou mot-clé du souvenir à effacer)"},
    category="memory"
)
def forget_fact(key: str) -> Dict[str, Any]:
    deleted_key = db.forget_fact(key)
    if deleted_key:
        return {
            "speech": f"C'est fait, j'ai effacé l'information concernant {deleted_key} de ma mémoire.",
            "data": {"deleted": True, "key": deleted_key}
        }
    return {
        "speech": f"Je n'ai trouvé aucun souvenir correspondant à « {key} » à effacer.",
        "data": {"deleted": False}
    }

