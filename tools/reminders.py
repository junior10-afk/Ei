import re
from typing import Dict, Any
from tools.registry import tool_registry

_DELAY_RE = re.compile(r"^\s*(\d+)\s*([smh])\s*$", re.IGNORECASE)
_DELAY_MULT = {"s": 1, "m": 60, "h": 3600}


def parse_delai(delai: str) -> int:
    m = _DELAY_RE.match(str(delai or ""))
    if not m:
        raise ValueError("Format de délai invalide (ex: 10s, 5m, 2h)")
    return int(m.group(1)) * _DELAY_MULT[m.group(2).lower()]


@tool_registry.register(
    name="rappeler",
    description="Programme un rappel vocal après un délai (ex: 10s, 5m, 2h)",
    parameters={
        "texte": "str (message du rappel)",
        "delai": "str (délai avant rappel, ex: 10s, 5m, 2h)",
    },
    requires_confirmation=False,
    category="local",
)
def rappeler(texte: str, delai: str) -> Dict[str, Any]:
    try:
        delay_seconds = parse_delai(delai)
    except ValueError as e:
        return {
            "speech": "Délai invalide, utilisez un format comme 10s, 5m ou 2h.",
            "data": {"error": str(e)},
        }
    try:
        from core.scheduler import Scheduler
        import core.scheduler as sched_mod

        scheduler = getattr(sched_mod, "scheduler_instance", None)
        if scheduler is None:
            scheduler = Scheduler()
        reminder_id = scheduler.add_reminder(
            message=texte, delay_seconds=delay_seconds, label="Rappel"
        )
        return {
            "speech": f"Rappel programmé dans {delai}.",
            "data": {"id": reminder_id, "texte": texte, "delai": delai, "delay_seconds": delay_seconds},
        }
    except Exception as e:
        return {
            "speech": "Impossible de programmer le rappel.",
            "data": {"error": str(e)},
        }
