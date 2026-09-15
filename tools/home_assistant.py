import os
import requests
from typing import Dict, Any
from tools.registry import tool_registry

HA_URL = os.getenv("HA_URL", "").rstrip("/")
HA_TOKEN = os.getenv("HA_TOKEN", "")

@tool_registry.register(
    name="ha_control",
    description="Contrôle une lumière, prise ou scène Home Assistant",
    parameters={
        "entity_id": "str (ex: light.salon, switch.bureau)",
        "action": "str (turn_on, turn_off, toggle)",
        "brightness": "optional int (1 à 100)"
    }
)
def ha_control(entity_id: str, action: str = "toggle", brightness: int = None) -> Dict[str, Any]:
    if not HA_URL or not HA_TOKEN:
        return {
            "speech": "Home Assistant n'est pas configuré dans le fichier d'environnement.",
            "data": {"configured": False}
        }

    domain = entity_id.split(".")[0]
    url = f"{HA_URL}/api/services/{domain}/{action}"
    headers = {
        "Authorization": f"Bearer {HA_TOKEN}",
        "Content-Type": "application/json"
    }
    payload = {"entity_id": entity_id}
    if brightness and domain == "light":
        payload["brightness_pct"] = brightness

    try:
        res = requests.post(url, json=payload, headers=headers, timeout=5)
        if res.status_code in (200, 201):
            return {
                "speech": f"Ordre exécuté sur {entity_id}.",
                "data": {"status": "ok"}
            }
        else:
            return {
                "speech": "Erreur de communication avec Home Assistant.",
                "data": {"status": res.status_code}
            }
    except Exception as e:
        return {
            "speech": "Impossible de joindre Home Assistant.",
            "data": {"error": str(e)}
        }

@tool_registry.register(
    name="ha_get_state",
    description="Lit l'état d'une entité Home Assistant (ex: light.salon)",
    parameters={"entity_id": "str (ex: light.salon)"},
    requires_confirmation=False,
    category="home",
)
def ha_get_state(entity_id: str) -> Dict[str, Any]:
    if not HA_URL or not HA_TOKEN:
        return {
            "speech": "Home Assistant n'est pas configuré dans le fichier d'environnement.",
            "data": {"configured": False}
        }
    url = f"{HA_URL}/api/states/{entity_id}"
    headers = {
        "Authorization": f"Bearer {HA_TOKEN}",
        "Content-Type": "application/json"
    }
    try:
        res = requests.get(url, headers=headers, timeout=5)
        if res.status_code == 200:
            payload = res.json()
            return {
                "speech": f"L'état de {entity_id} est {payload.get('state')}.",
                "data": {"entity_id": entity_id, "state": payload.get("state"), "attributes": payload.get("attributes", {})}
            }
        else:
            return {
                "speech": "Erreur de communication avec Home Assistant.",
                "data": {"status": res.status_code}
            }
    except Exception as e:
        return {
            "speech": "Impossible de joindre Home Assistant.",
            "data": {"error": str(e)}
        }
