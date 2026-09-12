import time
import uuid
import threading
from typing import Callable, Dict, Any, Optional, List
from core.bus import bus
from core.database import db
from core.state import state_manager

class AgentTask:
    def __init__(self, task_id: str, title: str, func: Callable, args: tuple = (), kwargs: dict = None):
        self.task_id = task_id
        self.title = title
        self.func = func
        self.args = args
        self.kwargs = kwargs or {}
        self.status = "queued"  # queued, running, completed, failed, cancelled
        self.progress = 0  # 0 to 100
        self.result = None
        self.error = None
        self.created_at = time.time()
        self.started_at = None
        self.completed_at = None
        self.cancel_event = threading.Event()

class TaskManager:
    """
    Gestionnaire de tâches asynchrones en arrière-plan pour Ei :
    - Exécute des opérations longues sans bloquer la boucle vocale
    - Persistance SQLite dans ei_memory.db
    - Support de l'annulation proactive (cancel_task)
    - Émet les jalons de progression au HUD via WebSocket
    - Notifie l'utilisateur vocalement (si non muté) et visuellement
    """
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(TaskManager, cls).__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._tasks: Dict[str, AgentTask] = {}
        self._task_lock = threading.Lock()
        self._initialized = True

    def submit_task(self, title: str, func: Callable, *args, **kwargs) -> str:
        task_id = f"task_{int(time.time())}_{uuid.uuid4().hex[:6]}"
        task = AgentTask(task_id, title, func, args, kwargs)
        with self._task_lock:
            self._tasks[task_id] = task

        # Persistance SQLite
        try:
            db.save_task(task_id, title, status="queued", progress=0, created_at=task.created_at)
        except Exception as e:
            print(f"[TaskManager] Erreur sauvegarde SQLite tâche: {e}")

        bus.broadcast_threadsafe({
            "type": "task_status",
            "task_id": task_id,
            "title": title,
            "status": "queued",
            "progress": 0
        })

        thread = threading.Thread(target=self._run_task, args=(task,), daemon=True)
        thread.start()
        return task_id

    def cancel_task(self, task_id: str) -> bool:
        """Annule une tâche en file d'attente ou en cours."""
        with self._task_lock:
            task = self._tasks.get(task_id)
            if not task:
                return False
            if task.status in ["completed", "failed", "cancelled"]:
                return False

            task.cancel_event.set()
            task.status = "cancelled"
            task.completed_at = time.time()

        try:
            db.update_task_status(task_id, status="cancelled", completed_at=task.completed_at)
        except Exception:
            pass

        bus.broadcast_threadsafe({
            "type": "task_status",
            "task_id": task_id,
            "title": task.title,
            "status": "cancelled",
            "progress": task.progress
        })
        print(f"[TaskManager] Tâche {task_id} (« {task.title} ») annulée.")
        return True

    def _run_task(self, task: AgentTask):
        if task.cancel_event.is_set():
            return

        task.status = "running"
        task.started_at = time.time()
        try:
            db.update_task_status(task.task_id, status="running", progress=10, started_at=task.started_at)
        except Exception:
            pass

        bus.broadcast_threadsafe({
            "type": "task_status",
            "task_id": task.task_id,
            "title": task.title,
            "status": "running",
            "progress": 10
        })

        try:
            if task.cancel_event.is_set():
                task.status = "cancelled"
                return

            res = task.func(*task.args, **task.kwargs)

            if task.cancel_event.is_set():
                task.status = "cancelled"
                return

            task.result = res
            task.status = "completed"
            task.progress = 100
            task.completed_at = time.time()

            try:
                db.update_task_status(
                    task.task_id,
                    status="completed",
                    progress=100,
                    result=str(res)[:1000],
                    completed_at=task.completed_at
                )
            except Exception:
                pass

            bus.broadcast_threadsafe({
                "type": "task_status",
                "task_id": task.task_id,
                "title": task.title,
                "status": "completed",
                "progress": 100,
                "result": str(res)[:500]
            })

            # Notification vocale proactive si micro non muté
            if not state_manager.is_mic_muted:
                from voice.tts import tts_engine
                from core.utils import play_chime
                try:
                    play_chime("ack")
                except Exception:
                    pass
                tts_engine.speak(f"Monsieur, la tâche « {task.title} » est terminée.", priority=2)

        except Exception as e:
            if task.cancel_event.is_set():
                task.status = "cancelled"
                return

            task.error = str(e)
            task.status = "failed"
            task.completed_at = time.time()

            try:
                db.update_task_status(
                    task.task_id,
                    status="failed",
                    error=str(e),
                    completed_at=task.completed_at
                )
            except Exception:
                pass

            bus.broadcast_threadsafe({
                "type": "task_status",
                "task_id": task.task_id,
                "title": task.title,
                "status": "failed",
                "error": str(e)
            })

    def get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        with self._task_lock:
            t = self._tasks.get(task_id)
            if t:
                return {
                    "task_id": t.task_id,
                    "title": t.title,
                    "status": t.status,
                    "progress": t.progress,
                    "result": t.result,
                    "error": t.error,
                    "duration_sec": round((t.completed_at or time.time()) - (t.started_at or time.time()), 2)
                }

        # Fallback recherche SQLite
        try:
            saved = db.list_saved_tasks(limit=100)
            for row in saved:
                if row["task_id"] == task_id:
                    return row
        except Exception:
            pass
        return None

    def list_tasks(self) -> List[Dict[str, Any]]:
        with self._task_lock:
            active_ids = set(self._tasks.keys())
            results = [
                {
                    "task_id": t.task_id,
                    "title": t.title,
                    "status": t.status,
                    "progress": t.progress
                }
                for t in self._tasks.values()
            ]

        try:
            saved = db.list_saved_tasks(limit=30)
            for s in saved:
                if s["task_id"] not in active_ids:
                    results.append({
                        "task_id": s["task_id"],
                        "title": s["title"],
                        "status": s["status"],
                        "progress": s.get("progress", 0)
                    })
        except Exception:
            pass

        return results

task_manager = TaskManager()
