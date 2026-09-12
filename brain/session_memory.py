import time
import uuid
from typing import List, Dict, Any, Optional
from core.database import db

class SessionMemory:
    """
    Mémoire de travail (court terme) persistée en base SQLite :
    - Conserve le contexte multi-tours des échanges, pensées et outils
    - Survit aux redémarrages de l'application
    """
    def __init__(self, max_history_items: int = 25):
        self.max_history_items = max_history_items
        self.session_id = f"session_{int(time.time())}_{uuid.uuid4().hex[:6]}"
        db.create_or_get_session(self.session_id, title=f"Session du {time.strftime('%d/%m/%Y %H:%M')}")
        self._history: List[Dict[str, Any]] = []
        self._load_recent_history()

    def _load_recent_history(self):
        """Charge les derniers messages de la base pour maintenir le fil conducteur après redémarrage."""
        try:
            recent = db.get_recent_messages(limit=10)
            for msg in recent:
                self._history.append({
                    "role": msg["role"],
                    "text": msg["content"],
                    "params": msg.get("metadata", {}).get("params"),
                    "action": msg.get("metadata", {}).get("action"),
                    "observation": msg.get("metadata", {}).get("observation"),
                    "timestamp": msg["timestamp"]
                })
        except Exception as e:
            print(f"[SessionMemory] Note: {e}")

    def add_user_message(self, text: str):
        clean = text.strip()
        self._history.append({
            "role": "user",
            "text": clean,
            "timestamp": time.time()
        })
        self._trim()
        db.save_message(self.session_id, "user", clean)
        self._check_auto_compaction()

    def add_assistant_message(self, text: str):
        clean = text.strip()
        self._history.append({
            "role": "assistant",
            "text": clean,
            "timestamp": time.time()
        })
        self._trim()
        db.save_message(self.session_id, "assistant", clean)
        self._check_auto_compaction()

    def _check_auto_compaction(self):
        """Vérifie et compacte la session si elle dépasse le seuil pour limiter les tokens."""
        if len(self._history) >= 16:
            compacted = db.compact_session(self.session_id, keep_last=8)
            if compacted:
                # Recharger l'historique compacté
                self._history.clear()
                self._load_recent_history()

    def add_tool_interaction(self, action: str, params: Dict[str, Any], observation: str):
        obs_clean = str(observation)[:500]
        self._history.append({
            "role": "tool",
            "action": action,
            "params": params,
            "observation": obs_clean,
            "timestamp": time.time()
        })
        self._trim()
        db.save_message(
            self.session_id,
            "tool",
            f"Outil {action} exécuté : {obs_clean}",
            metadata={"action": action, "params": params, "observation": obs_clean}
        )

    def _trim(self):
        if len(self._history) > self.max_history_items:
            self._history = self._history[-self.max_history_items:]

    def get_recent_pairs(self, limit: int = 4) -> List[Dict[str, str]]:
        """Fournit les derniers tours user/assistant pour alimenter la cascade LLM depuis SQLite."""
        pairs = []
        for item in self._history:
            if item.get("role") in ("user", "assistant"):
                pairs.append({"role": item["role"], "text": item.get("text", "")})
        return pairs[-limit:] if limit > 0 else pairs

    def get_history_context(self, max_items: int = 8) -> str:
        """Produit un résumé textuel des derniers échanges pour l'injection dans le prompt."""
        recent = self._history[-max_items:] if max_items > 0 else self._history
        if not recent:
            return "Aucun historique récent."

        lines = []
        for item in recent:
            role = item["role"]
            if role == "user":
                lines.append(f"Utilisateur: {item.get('text', '')}")
            elif role == "assistant":
                lines.append(f"Ei: {item.get('text', '')}")
            elif role == "tool":
                lines.append(f"[Outil: {item.get('action', '')} -> {item.get('observation', '')}]")
            elif role == "system":
                lines.append(f"[{item.get('text', '')}]")
        return "\n".join(lines)

    def clear(self):
        self._history.clear()

session_memory = SessionMemory()

