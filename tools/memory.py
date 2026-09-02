import json
import time
from pathlib import Path
from typing import Dict, Any
from tools.registry import tool_registry

MEMORY_FILE = Path(__file__).resolve().parent.parent / "memory.json"

def load_memories() -> Dict[str, Any]:
    if MEMORY_FILE.exists():
        try:
            with open(MEMORY_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}

def save_memories(data: Dict[str, Any]):
    try:
        with open(MEMORY_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"[Memory] Erreur sauvegarde: {e}")

@tool_registry.register(
    name="remember_fact",
    description="Mémorise une information ou une note personnelle",
    parameters={
        "key": "str (sujet ou mot-clé)",
        "value": "str (ce qu'il faut mémoriser)"
    }
)
def remember_fact(key: str, value: str) -> Dict[str, Any]:
    memories = load_memories()
    memories[key.lower().strip()] = {
        "value": value.strip(),
        "timestamp": time.time()
    }
    save_memories(memories)
    return {
        "speech": f"C'est noté, j'ai mémorisé cela pour {key}.",
        "data": {"key": key, "value": value}
    }

@tool_registry.register(
    name="recall_fact",
    description="Rappelle une information mémorisée",
    parameters={"key": "str (sujet ou mot-clé)"}
)
def recall_fact(key: str) -> Dict[str, Any]:
    memories = load_memories()
    k = key.lower().strip()
    if k in memories:
        val = memories[k]["value"]
        return {
            "speech": f"D'après ma mémoire, {val}.",
            "data": {"key": key, "value": val}
        }
    return {
        "speech": f"Je n'ai aucun souvenir enregistré pour {key}.",
        "data": {"found": False}
    }
