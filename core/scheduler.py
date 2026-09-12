import time
import uuid
import threading
from typing import Dict, Any, List, Optional
from core.bus import bus
from core.database import db
from core.state import state_manager

class Scheduler:
    """
    Planificateur temporel, rappels et routines quotidiennes proactives pour Ei :
    - Programmation de rappels à délai relatif ou heure précise
    - Routines quotidiennes (ex: Briefing du matin à 08:00 avec météo et tâches)
    - Persistance SQLite
    - Notification proactive vocale (si non muté) et visuelle (HUD)
    - Thread d'arrière-plan résilient
    """
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(Scheduler, cls).__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._reminders: Dict[str, Dict[str, Any]] = {}
        self._routines: Dict[str, Dict[str, Any]] = {}
        self._rem_lock = threading.Lock()
        self._running = True
        
        self._load_routines_from_db()
        self._thread = threading.Thread(target=self._worker_loop, daemon=True)
        self._thread.start()
        self._initialized = True

    def _load_routines_from_db(self):
        """Charge ou initialise les routines quotidiennes depuis SQLite."""
        try:
            stored = db.load_routines()
            if not stored:
                # Routine par défaut : Briefing Matinal à 08:00
                default_prompt = "Fais un briefing matinal complet : salue l'utilisateur, donne la météo à Lomé et rappelle les priorités du jour."
                db.save_routine("morning_briefing", "Briefing Matinal", "08:00", "prompt", default_prompt, True)
                stored = db.load_routines()

            for r in stored:
                self._routines[r["id"]] = r
        except Exception as e:
            print(f"[Scheduler] Erreur chargement routines SQLite: {e}")

    def add_reminder(self, message: str, delay_seconds: float, label: str = "Rappel") -> str:
        reminder_id = f"rem_{int(time.time())}_{uuid.uuid4().hex[:6]}"
        trigger_time = time.time() + max(1.0, delay_seconds)

        with self._rem_lock:
            self._reminders[reminder_id] = {
                "id": reminder_id,
                "label": label,
                "message": message,
                "trigger_time": trigger_time,
                "triggered": False
            }

        bus.broadcast_threadsafe({
            "type": "reminder_scheduled",
            "id": reminder_id,
            "label": label,
            "message": message,
            "delay_sec": int(delay_seconds)
        })

        return reminder_id

    def cancel_reminder(self, reminder_id: str) -> bool:
        with self._rem_lock:
            if reminder_id in self._reminders:
                del self._reminders[reminder_id]
                return True
        return False

    def add_daily_routine(self, routine_id: str, name: str, time_str: str, prompt: str, enabled: bool = True):
        """Ajoute ou modifie une routine quotidienne (format time_str: HH:MM)."""
        with self._rem_lock:
            routine_data = {
                "id": routine_id,
                "name": name,
                "time_str": time_str,
                "action_type": "prompt",
                "payload": prompt,
                "enabled": 1 if enabled else 0,
                "last_run_date": None
            }
            self._routines[routine_id] = routine_data

        try:
            db.save_routine(routine_id, name, time_str, "prompt", prompt, enabled)
        except Exception as e:
            print(f"[Scheduler] Erreur sauvegarde routine: {e}")

    def list_active(self) -> List[Dict[str, Any]]:
        now = time.time()
        with self._rem_lock:
            return [
                {
                    "id": r["id"],
                    "label": r["label"],
                    "message": r["message"],
                    "remaining_sec": max(0, int(r["trigger_time"] - now))
                }
                for r in self._reminders.values()
                if not r["triggered"]
            ]

    def list_routines(self) -> List[Dict[str, Any]]:
        with self._rem_lock:
            return list(self._routines.values())

    def _worker_loop(self):
        while self._running:
            time.sleep(1.0)
            now = time.time()
            now_time_str = time.strftime("%H:%M")
            today_str = time.strftime("%Y-%m-%d")

            # 1. Vérification des rappels ponctuels
            to_trigger_reminders = []
            with self._rem_lock:
                for rem_id, rem in list(self._reminders.items()):
                    if not rem["triggered"] and now >= rem["trigger_time"]:
                        rem["triggered"] = True
                        to_trigger_reminders.append(rem)
                        del self._reminders[rem_id]

            for rem in to_trigger_reminders:
                self._trigger_reminder(rem)

            # 2. Vérification des routines quotidiennes
            to_trigger_routines = []
            with self._rem_lock:
                for r_id, routine in self._routines.items():
                    if bool(routine.get("enabled", True)):
                        if routine.get("time_str") == now_time_str:
                            if routine.get("last_run_date") != today_str:
                                routine["last_run_date"] = today_str
                                to_trigger_routines.append(routine)

            for routine in to_trigger_routines:
                self._trigger_routine(routine, today_str)

    def _trigger_reminder(self, reminder: Dict[str, Any]):
        label = reminder["label"]
        msg = reminder["message"]

        try:
            from core.utils import play_chime
            play_chime("timer")
        except Exception:
            pass

        bus.broadcast_threadsafe({
            "type": "reminder_triggered",
            "id": reminder["id"],
            "label": label,
            "message": msg
        })

        if not state_manager.is_mic_muted:
            try:
                from voice.tts import tts_engine
                alert_text = f"Monsieur, rappel pour {label} : {msg}" if label != "Rappel" else f"Monsieur, vous aviez un rappel : {msg}"
                tts_engine.speak(alert_text, priority=2)
            except Exception as e:
                print(f"[Scheduler] Erreur notification vocale rappel: {e}")

    def _trigger_routine(self, routine: Dict[str, Any], date_str: str):
        routine_id = routine["id"]
        name = routine["name"]
        prompt = routine.get("payload", "")

        try:
            db.update_routine_last_run(routine_id, date_str)
        except Exception:
            pass

        print(f"[Scheduler] Déclenchement de la routine quotidienne: « {name} »")

        try:
            from core.utils import play_chime
            play_chime("wake")
        except Exception:
            pass

        bus.broadcast_threadsafe({
            "type": "routine_triggered",
            "id": routine_id,
            "name": name,
            "time": routine.get("time_str")
        })

        # Exécuter l'action associée (ex: prompt briefing matinal)
        if prompt:
            from brain.dispatcher import dispatcher
            threading.Thread(
                target=dispatcher.process_text_input,
                args=(prompt,),
                kwargs={"is_voice": True},
                daemon=True
            ).start()

scheduler = Scheduler()
