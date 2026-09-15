import time
import threading
import uuid
from typing import Dict, Any, Optional
from tools.registry import tool_registry
from core.bus import bus
from core.config import config
from core.utils import play_chime

class TimerManager:
    def __init__(self):
        self.active_timers: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.Lock()

    def add_timer(self, total_seconds: int, label: str) -> Dict[str, Any]:
        timer_id = str(uuid.uuid4())[:8]
        cancel_event = threading.Event()

        timer_info = {
            "id": timer_id,
            "label": label,
            "duration": total_seconds,
            "start_time": time.time(),
            "end_time": time.time() + total_seconds,
            "cancel_event": cancel_event
        }

        with self._lock:
            self.active_timers[timer_id] = timer_info

        # Diffuser au HUD
        bus.broadcast_threadsafe({
            "type": "action",
            "action": "timer_start",
            "params": {
                "id": timer_id,
                "label": label,
                "duration": total_seconds,
                "end_time": timer_info["end_time"]
            }
        })

        # Démarrer le décompte en arrière-plan
        threading.Thread(target=self._run_timer, args=(timer_id, total_seconds, label, cancel_event), daemon=True).start()

        return timer_info

    def _run_timer(self, timer_id: str, duration: int, label: str, cancel_event: threading.Event):
        completed = not cancel_event.wait(timeout=duration)

        with self._lock:
            self.active_timers.pop(timer_id, None)

        if completed:
            print(f"[Timer] Minuteur '{label}' ({duration}s) terminé !")
            # Sonnerie
            if config.get("sound_feedback", True):
                play_chime("timer")

            # Notification au HUD
            bus.broadcast_threadsafe({
                "type": "action",
                "action": "timer_end",
                "params": {
                    "id": timer_id,
                    "label": label
                }
            })

            # Annonce vocale par l'assistant
            from voice.tts import tts_engine
            user = config.get("user_name", "Monsieur")
            tts_engine.speak(f"{user}, le minuteur de {label} est terminé.")

    def cancel(self, label: Optional[str] = None) -> bool:
        with self._lock:
            if not self.active_timers:
                return False

            cancelled = False
            for tid, t in list(self.active_timers.items()):
                if label is None or label.lower() in t["label"].lower():
                    t["cancel_event"].set()
                    self.active_timers.pop(tid, None)
                    bus.broadcast_threadsafe({
                        "type": "action",
                        "action": "timer_cancel",
                        "params": {"id": tid, "label": t["label"]}
                    })
                    cancelled = True
            return cancelled

timer_manager = TimerManager()

@tool_registry.register(
    name="set_timer",
    description="Lance un minuteur ou compte à rebours pour une durée donnée",
    parameters={
        "duration": "int (durée)",
        "unit": "str ('secondes', 'minutes', 'heures')",
        "label": "optional str (intitulé du minuteur, ex: cuisson, pause, réunion)"
    }
)
def set_timer(duration: int, unit: str = "minutes", label: str = "Minuteur") -> Dict[str, Any]:
    duration = int(duration)
    unit_lower = unit.lower().strip()

    if "heur" in unit_lower:
        total_seconds = duration * 3600
        speech_unit = f"{duration} heure{'s' if duration > 1 else ''}"
    elif "min" in unit_lower:
        total_seconds = duration * 60
        speech_unit = f"{duration} minute{'s' if duration > 1 else ''}"
    else:
        total_seconds = duration
        speech_unit = f"{duration} seconde{'s' if duration > 1 else ''}"

    if total_seconds <= 0:
        return {"speech": "La durée doit être supérieure à zéro.", "data": {"error": "invalid duration"}}

    timer_info = timer_manager.add_timer(total_seconds, label)
    return {
        "speech": f"C'est parti, minuteur de {speech_unit} activé pour {label}.",
        "data": {
            "id": timer_info["id"],
            "duration": total_seconds,
            "label": label
        }
    }

@tool_registry.register(
    name="cancel_timer",
    description="Annule un minuteur ou compte à rebours actif",
    parameters={"label": "optional str (nom ou laisser vide pour tous)"}
)
def cancel_timer(label: Optional[str] = None) -> Dict[str, Any]:
    success = timer_manager.cancel(label)
    if success:
        return {
            "speech": "Le minuteur a bien été annulé.",
            "data": {"cancelled": True}
        }
    else:
        return {
            "speech": "Aucun minuteur actif à annuler.",
            "data": {"cancelled": False}
        }

@tool_registry.register(
    name="schedule_reminder",
    description="Programme un rappel proactif vocal et visuel pour plus tard (ex: dans 10 minutes, dans 2 heures)",
    parameters={
        "message": "str (ce dont il faut se rappeler, ex: 'Prendre mes médicaments', 'Appeler le client')",
        "delay_minutes": "int (dans combien de minutes déclencher le rappel, défaut: 15)",
        "label": "optional str (intitulé court du rappel, ex: 'Santé', 'Projet')"
    },
    category="system"
)
def schedule_reminder(message: str, delay_minutes: int = 15, label: str = "Rappel") -> Dict[str, Any]:
    from core.scheduler import scheduler
    delay_sec = max(5, int(delay_minutes) * 60)
    rem_id = scheduler.add_reminder(message=message, delay_seconds=delay_sec, label=label)
    speech = f"C'est noté. Je vous rappellerai « {message} » dans {delay_minutes} minute{'s' if int(delay_minutes) > 1 else ''}."
    return {
        "speech": speech,
        "data": {"reminder_id": rem_id, "message": message, "delay_minutes": delay_minutes}
    }

