import threading
import time
import uuid
from typing import List, Dict, Any, Optional
from core.database import db

COMPACT_THRESHOLD = 20  # déclenche la compaction background (Phase 2)
COMPACT_KEEP_LAST = 10  # messages récents conservés tels quels


class SessionMemory:
    """
    Mémoire de travail (court terme) persistée en base SQLite :
    - Conserve le contexte multi-tours des échanges, pensées et outils
    - Survit aux redémarrages de l'application
    - Compaction Phase 2 : résumé LLM en thread background + swap atomique
      (double-buffer) — le thread voix ne bloque jamais sur la compaction.
    """
    def __init__(self, max_history_items: int = 25):
        self.max_history_items = max_history_items
        self._lock = threading.Lock()
        self._compacting = False
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
        """Déclenche la compaction en background si le seuil est atteint.
        Non-bloquant : snapshot + thread daemon, swap atomique à la fin.
        Le thread voix continue sur l'ancien contexte pendant ce temps."""
        with self._lock:
            if len(self._history) < COMPACT_THRESHOLD or self._compacting:
                return
            self._compacting = True
            snapshot = list(self._history)
        t = threading.Thread(target=self._compact_in_background,
                             args=(snapshot,), daemon=True)
        t.start()

    def _compact_in_background(self, snapshot: List[Dict[str, Any]]):
        """Résume (LLM, repli troncation) puis swap. Jamais sur le thread voix."""
        try:
            old_part = snapshot[:-COMPACT_KEEP_LAST] if len(snapshot) > COMPACT_KEEP_LAST else []
            keep_part = snapshot[-COMPACT_KEEP_LAST:]
            summary = self._llm_summary(old_part) if old_part else None
            if summary:
                db.compact_session(self.session_id, keep_last=COMPACT_KEEP_LAST,
                                   summary=summary)
                new_history = ([{"role": "system", "text": summary,
                                 "timestamp": time.time()}] + keep_part)
            else:
                # Repli : compaction synchrone historique (troncation) + recharge
                db.compact_session(self.session_id, keep_last=8)
                new_history = None
            with self._lock:
                if new_history is not None:
                    self._history = new_history
                    self._trim()
                else:
                    self._history.clear()
                    self._load_recent_history()
            print(f"[SessionMemory] Compaction background terminée "
                  f"({'LLM' if summary else 'troncation'}).")
        except Exception as e:
            print(f"[SessionMemory] Compaction background ignorée: {e}")
        finally:
            with self._lock:
                self._compacting = False

    def _llm_summary(self, old_part: List[Dict[str, Any]]) -> Optional[str]:
        """Résume les vieux échanges via le tiers léger. None si indisponible."""
        try:
            from brain.llm import llm_cascade  # import tardif : évite cycle
            from core.config import config
            tiers = (config.get("models", {}) or {}).get("tiers", {}) or {}
            light_ref = str(tiers.get("light", "") or "")
            if "/" in light_ref:
                prov, mod = light_ref.split("/", 1)
            else:
                prov, mod = "gemini", light_ref or "gemini-2.5-flash"
            key_env = {"gemini": "GEMINI_API_KEY", "groq": "GROQ_API_KEY",
                       "openai": "OPENAI_API_KEY",
                       "mistral": "MISTRAL_API_KEY", "xai": "XAI_API_KEY",
                       "anthropic": "ANTHROPIC_API_KEY",
                       "openrouter": "OPENROUTER_API_KEY"}.get(prov.lower(), "")
            convo = "\n".join(
                f"{m.get('role', '?')}: {str(m.get('text', '') or m.get('observation', ''))[:300]}"
                for m in old_part)
            summary = llm_cascade.ask_with_model(
                f"Échanges à résumer :\n{convo[:6000]}",
                {"provider": prov.lower(), "model": mod, "key_env": key_env,
                 "max_tokens": 512},
                "Résume ces échanges en 10 lignes max (faits, décisions, contexte "
                "utilisateur). Français, texte brut, sans markdown.",
                include_history=False,  # résumé autonome : pas de pollution croisée
            )
            return summary.strip()[:2000] if summary else None
        except Exception as e:
            print(f"[SessionMemory] Résumé LLM impossible ({e}), repli troncation.")
            return None

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

