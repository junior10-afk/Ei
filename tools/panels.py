from typing import Dict, Any
from tools.registry import tool_registry
from core.bus import bus

PANEL_ALIASES = {
    "settings": "settings",
    "paramètres": "settings",
    "parametres": "settings",
    "réglages": "settings",
    "reglages": "settings",
    "configuration": "settings",
    "chat": "chat",
    "historique": "chat",
    "console": "chat",
    "messages": "chat",
    "journal": "chat",
    "orbs": "orbs",
    "orbe": "orbs",
    "orbes": "orbs",
    "galerie": "orbs",
    "galerie des orbes": "orbs"
}

@tool_registry.register(
    name="open_panel",
    description="Ouvre un panneau dans l'interface HUD (settings, chat ou orbs)",
    parameters={"panel": "str ('settings', 'chat' ou 'orbs')"}
)
def open_panel(panel: str) -> Dict[str, Any]:
    target = PANEL_ALIASES.get(panel.lower().strip(), panel.lower().strip())
    bus.broadcast_threadsafe({
        "type": "action",
        "action": "open_panel",
        "params": {"panel": target}
    })
    panel_labels = {
        "settings": "des paramètres",
        "chat": "de la console",
        "orbs": "de la galerie des orbes"
    }
    panel_name = panel_labels.get(target, target)
    return {
        "speech": f"J'affiche le panneau {panel_name}.",
        "data": {"panel": target}
    }

@tool_registry.register(
    name="close_panel",
    description="Ferme un panneau dans l'interface HUD (settings ou chat)",
    parameters={"panel": "str ('settings' ou 'chat')"}
)
def close_panel(panel: str = "all") -> Dict[str, Any]:
    target = PANEL_ALIASES.get(panel.lower().strip(), panel.lower().strip())
    bus.broadcast_threadsafe({
        "type": "action",
        "action": "close_panel",
        "params": {"panel": target}
    })
    return {
        "speech": "Panneau masqué.",
        "data": {"panel": target}
    }
