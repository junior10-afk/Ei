import threading
from typing import Callable, List, Optional

class AssistantState:
    IDLE = "idle"
    LISTENING = "listening"
    THINKING = "thinking"
    SPEAKING = "speaking"

class StateManager:
    def __init__(self):
        self._lock = threading.Lock()
        self._state: str = AssistantState.IDLE
        self._is_mic_muted: bool = False
        self._is_speaking: bool = False
        self._volume: float = 0.0
        self._listeners: List[Callable[[str, dict], None]] = []

    def subscribe(self, callback: Callable[[str, dict], None]):
        """Ajoute un listener pour les changements d'état."""
        with self._lock:
            self._listeners.append(callback)

    def _notify(self, event_type: str, data: dict):
        for cb in list(self._listeners):
            try:
                cb(event_type, data)
            except Exception as e:
                print(f"[StateManager] Erreur callback: {e}")

    @property
    def current_state(self) -> str:
        with self._lock:
            return self._state

    def set_state(self, new_state: str):
        with self._lock:
            if self._state == new_state:
                return
            self._state = new_state
            self._is_speaking = (new_state == AssistantState.SPEAKING)
            state_val = self._state
        self._notify("set_state", {"state": state_val})

    @property
    def is_mic_muted(self) -> bool:
        with self._lock:
            return self._is_mic_muted

    def set_mic_muted(self, muted: Optional[bool] = None) -> bool:
        with self._lock:
            if muted is None:
                self._is_mic_muted = not self._is_mic_muted
            else:
                self._is_mic_muted = muted
            val = self._is_mic_muted
        self._notify("mic_state", {"muted": val})
        return val

    @property
    def is_speaking(self) -> bool:
        with self._lock:
            return self._is_speaking

    def set_speaking(self, speaking: bool):
        with self._lock:
            self._is_speaking = speaking
            if speaking:
                self._state = AssistantState.SPEAKING
            elif self._state == AssistantState.SPEAKING:
                self._state = AssistantState.IDLE
            state_val = self._state
        self._notify("set_state", {"state": state_val})

    def set_volume(self, value: float):
        """Met à jour le volume instantané (0.0 à 1.0) pour l'orbe 3D."""
        clamped = max(0.0, min(1.0, float(value)))
        with self._lock:
            self._volume = clamped
        self._notify("volume", {"value": clamped})

state_manager = StateManager()
