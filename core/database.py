import os
import time
import json
import sqlite3
import threading
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DB_PATH = DATA_DIR / "ei_memory.db"
LEGACY_MEMORY_FILE = BASE_DIR / "memory.json"

class DatabaseManager:
    """
    Gestionnaire centralisé de persistance SQLite pour Ei :
    - Sessions et historique conversationnel complet (mémoire épisodique)
    - Faits et souvenirs avec indexation FTS5 plein texte & recherche sémantique floue
    - Thread-safe avec verrous de synchronisation
    """
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(DatabaseManager, cls).__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._db_lock = threading.Lock()
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        self._init_schema()
        self._migrate_legacy_json()
        self._initialized = True

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_schema(self):
        with self._db_lock, self._get_connection() as conn:
            cursor = conn.cursor()

            # 1. Sessions de conversation
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS sessions (
                    session_id TEXT PRIMARY KEY,
                    title TEXT,
                    summary TEXT,
                    created_at REAL,
                    updated_at REAL
                )
            """)

            # 2. Messages de conversation
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT,
                    role TEXT,
                    content TEXT,
                    metadata TEXT,
                    timestamp REAL,
                    FOREIGN KEY(session_id) REFERENCES sessions(session_id)
                )
            """)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_messages_session ON messages(session_id)")

            # 3. Faits & souvenirs à long terme
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS facts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    key TEXT UNIQUE COLLATE NOCASE,
                    value TEXT,
                    category TEXT DEFAULT 'general',
                    confidence REAL DEFAULT 1.0,
                    created_at REAL,
                    updated_at REAL
                )
            """)

            # 4. Table virtuelle FTS5 pour recherche plein texte et associative
            cursor.execute("""
                CREATE VIRTUAL TABLE IF NOT EXISTS facts_fts USING fts5(
                    key,
                    value,
                    category,
                    content='facts',
                    content_rowid='id'
                )
            """)

            # 5. Déclencheurs de synchronisation FTS5
            cursor.execute("""
                CREATE TRIGGER IF NOT EXISTS facts_ai AFTER INSERT ON facts BEGIN
                    INSERT INTO facts_fts(rowid, key, value, category)
                    VALUES (new.id, new.key, new.value, new.category);
                END;
            """)
            cursor.execute("""
                CREATE TRIGGER IF NOT EXISTS facts_ad AFTER DELETE ON facts BEGIN
                    INSERT INTO facts_fts(facts_fts, rowid, key, value, category)
                    VALUES('delete', old.id, old.key, old.value, old.category);
                END;
            """)
            cursor.execute("""
                CREATE TRIGGER IF NOT EXISTS facts_au AFTER UPDATE ON facts BEGIN
                    INSERT INTO facts_fts(facts_fts, rowid, key, value, category)
                    VALUES('delete', old.id, old.key, old.value, old.category);
                    INSERT INTO facts_fts(rowid, key, value, category)
                    VALUES (new.id, new.key, new.value, new.category);
                END;
            """)

            # 6. Tâches d'arrière-plan
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS tasks (
                    task_id TEXT PRIMARY KEY,
                    title TEXT,
                    status TEXT,
                    progress INTEGER DEFAULT 0,
                    result TEXT,
                    error TEXT,
                    created_at REAL,
                    started_at REAL,
                    completed_at REAL
                )
            """)

            # 7. Rappels programmés
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS reminders (
                    id TEXT PRIMARY KEY,
                    label TEXT,
                    message TEXT,
                    trigger_time REAL,
                    triggered INTEGER DEFAULT 0,
                    created_at REAL
                )
            """)

            # 8. Routines récurrentes (ex: briefing 08:00)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS routines (
                    id TEXT PRIMARY KEY,
                    name TEXT,
                    time_str TEXT,
                    action_type TEXT DEFAULT 'prompt',
                    payload TEXT,
                    enabled INTEGER DEFAULT 1,
                    last_run_date TEXT,
                    created_at REAL
                )
            """)

            conn.commit()

    def _migrate_legacy_json(self):
        """Importe automatiquement memory.json dans la base SQLite au premier démarrage."""
        if not LEGACY_MEMORY_FILE.exists():
            return
        try:
            with open(LEGACY_MEMORY_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            if not isinstance(data, dict) or not data:
                return

            with self._db_lock, self._get_connection() as conn:
                cursor = conn.cursor()
                now = time.time()
                for key, item in data.items():
                    val = item.get("value") if isinstance(item, dict) else str(item)
                    ts = item.get("timestamp", now) if isinstance(item, dict) else now
                    cursor.execute("""
                        INSERT OR IGNORE INTO facts (key, value, category, created_at, updated_at)
                        VALUES (?, ?, 'legacy', ?, ?)
                    """, (key.strip(), val.strip(), ts, ts))
                conn.commit()
            print("[Database] Migration des mémoires depuis memory.json effectuée.")
        except Exception as e:
            print(f"[Database] Avertissement migration legacy memory.json: {e}")

    # --- Gestion des Sessions & Messages ---

    def create_or_get_session(self, session_id: str, title: str = "Session Active") -> str:
        with self._db_lock, self._get_connection() as conn:
            cursor = conn.cursor()
            now = time.time()
            cursor.execute("SELECT session_id FROM sessions WHERE session_id = ?", (session_id,))
            row = cursor.fetchone()
            if not row:
                cursor.execute("""
                    INSERT INTO sessions (session_id, title, created_at, updated_at)
                    VALUES (?, ?, ?, ?)
                """, (session_id, title, now, now))
                conn.commit()
            return session_id

    def save_message(self, session_id: str, role: str, content: str, metadata: Optional[Dict[str, Any]] = None):
        with self._db_lock, self._get_connection() as conn:
            cursor = conn.cursor()
            now = time.time()
            meta_json = json.dumps(metadata or {}, ensure_ascii=False)
            cursor.execute("""
                INSERT INTO messages (session_id, role, content, metadata, timestamp)
                VALUES (?, ?, ?, ?, ?)
            """, (session_id, role, content, meta_json, now))
            cursor.execute("UPDATE sessions SET updated_at = ? WHERE session_id = ?", (now, session_id))
            conn.commit()

    def get_recent_messages(self, session_id: Optional[str] = None, limit: int = 15) -> List[Dict[str, Any]]:
        with self._db_lock, self._get_connection() as conn:
            cursor = conn.cursor()
            if session_id:
                cursor.execute("""
                    SELECT role, content, metadata, timestamp
                    FROM messages
                    WHERE session_id = ?
                    ORDER BY id DESC LIMIT ?
                """, (session_id, limit))
            else:
                cursor.execute("""
                    SELECT role, content, metadata, timestamp
                    FROM messages
                    ORDER BY id DESC LIMIT ?
                """, (limit,))
            rows = cursor.fetchall()
            results = []
            for r in reversed(rows):
                meta = {}
                try:
                    meta = json.loads(r["metadata"]) if r["metadata"] else {}
                except Exception:
                    pass
                results.append({
                    "role": r["role"],
                    "content": r["content"],
                    "metadata": meta,
                    "timestamp": r["timestamp"]
                })
            return results

    # --- Gestion des Faits & Souvenirs Long Terme ---

    def remember_fact(self, key: str, value: str, category: str = "general") -> bool:
        clean_key = key.strip()
        clean_val = value.strip()
        now = time.time()
        with self._db_lock, self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO facts (key, value, category, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(key) DO UPDATE SET
                    value = excluded.value,
                    category = excluded.category,
                    updated_at = excluded.updated_at
            """, (clean_key, clean_val, category, now, now))
            conn.commit()

        # Sauvegarde miroir pour compatibilité
        self._export_to_legacy_json()
        return True

    def recall_fact(self, query: str) -> Optional[Dict[str, Any]]:
        """
        Recherche intelligente :
        1. Correspondance exacte sur la clé
        2. Recherche plein texte FTS5 (sur clé ou valeur)
        3. Correspondance partielle LIKE
        """
        q = query.strip()
        if not q:
            return None

        with self._db_lock, self._get_connection() as conn:
            cursor = conn.cursor()

            # 1. Correspondance exacte insensible à la casse
            cursor.execute("SELECT key, value, category, updated_at FROM facts WHERE key = ? COLLATE NOCASE", (q,))
            row = cursor.fetchone()
            if row:
                return dict(row)

            # 2. Recherche plein texte via FTS5
            safe_terms = [t for t in q.replace('"', ' ').replace("'", ' ').split() if len(t) > 2]
            if safe_terms:
                fts_query = " OR ".join([f"{term}*" for term in safe_terms])
                try:
                    cursor.execute("""
                        SELECT f.key, f.value, f.category, f.updated_at, bm25(facts_fts) as rank
                        FROM facts_fts
                        JOIN facts f ON facts_fts.rowid = f.id
                        WHERE facts_fts MATCH ?
                        ORDER BY rank
                        LIMIT 1
                    """, (fts_query,))
                    row = cursor.fetchone()
                    if row:
                        return {
                            "key": row["key"],
                            "value": row["value"],
                            "category": row["category"],
                            "updated_at": row["updated_at"]
                        }
                except Exception:
                    pass

            # 3. Correspondance partielle LIKE (clé ou valeur)
            cursor.execute("""
                SELECT key, value, category, updated_at
                FROM facts
                WHERE key LIKE ? OR value LIKE ?
                ORDER BY updated_at DESC
                LIMIT 1
            """, (f"%{q}%", f"%{q}%"))
            row = cursor.fetchone()
            if row:
                return dict(row)

            # 4. Décomposition par mots
            for word in safe_terms:
                cursor.execute("""
                    SELECT key, value, category, updated_at
                    FROM facts
                    WHERE key LIKE ? OR value LIKE ?
                    ORDER BY updated_at DESC
                    LIMIT 1
                """, (f"%{word}%", f"%{word}%"))
                row = cursor.fetchone()
                if row:
                    return dict(row)

        return None

    def forget_fact(self, query: str) -> Optional[str]:
        """
        Supprime un souvenir ou fait mémorisé (droit à l'oubli / RGPD).
        Recherche le fait le plus pertinent puis le supprime de facts et FTS5.
        Retourne la clé du fait supprimé si trouvé, sinon None.
        """
        fact = self.recall_fact(query)
        if not fact:
            return None

        found_key = fact["key"]
        with self._db_lock, self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM facts WHERE key = ? COLLATE NOCASE", (found_key,))
            conn.commit()

        self._export_to_legacy_json()
        return found_key

    def compact_session(self, session_id: str, keep_last: int = 10) -> bool:
        """
        Compresse les anciens messages au-delà de keep_last pour préserver le fil conducteur
        sans saturer le budget tokens.
        """
        with self._db_lock, self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, role, content FROM messages
                WHERE session_id = ?
                ORDER BY id ASC
            """, (session_id,))
            rows = cursor.fetchall()
            if len(rows) <= keep_last + 4:
                return False

            old_rows = rows[:-keep_last]
            summary_lines = []
            for r in old_rows:
                role_label = "Utilisateur" if r["role"] == "user" else "Ei"
                summary_lines.append(f"{role_label}: {r['content'][:120]}")
            compacted_summary = "Résumé des échanges précédents :\n" + "\n".join(summary_lines[:8])

            old_ids = [r["id"] for r in old_rows]
            placeholders = ",".join("?" * len(old_ids))
            cursor.execute(f"DELETE FROM messages WHERE id IN ({placeholders})", old_ids)

            cursor.execute("""
                INSERT INTO messages (session_id, role, content, metadata, timestamp)
                VALUES (?, 'system', ?, ?, ?)
            """, (session_id, compacted_summary, json.dumps({"type": "compaction"}), time.time()))
            conn.commit()
            return True

    def get_all_facts(self, limit: int = 50) -> Dict[str, str]:
        with self._db_lock, self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT key, value FROM facts ORDER BY updated_at DESC LIMIT ?", (limit,))
            rows = cursor.fetchall()
            return {r["key"]: r["value"] for r in rows}

    def _export_to_legacy_json(self):
        try:
            facts = self.get_all_facts(limit=200)
            data = {k: {"value": v, "timestamp": time.time()} for k, v in facts.items()}
            with open(LEGACY_MEMORY_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception:
            pass

    # --- Persistance des Tâches ---

    def save_task(self, task_id: str, title: str, status: str = "queued", progress: int = 0,
                  created_at: Optional[float] = None) -> None:
        with self._db_lock, self._get_connection() as conn:
            cursor = conn.cursor()
            now = created_at or time.time()
            cursor.execute("""
                INSERT INTO tasks (task_id, title, status, progress, created_at)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(task_id) DO UPDATE SET
                    status = excluded.status,
                    progress = excluded.progress
            """, (task_id, title, status, progress, now))
            conn.commit()

    def update_task_status(self, task_id: str, status: str, progress: Optional[int] = None,
                           result: Optional[str] = None, error: Optional[str] = None,
                           started_at: Optional[float] = None, completed_at: Optional[float] = None) -> None:
        with self._db_lock, self._get_connection() as conn:
            cursor = conn.cursor()
            updates = ["status = ?"]
            params: list[Any] = [status]
            if progress is not None:
                updates.append("progress = ?")
                params.append(progress)
            if result is not None:
                updates.append("result = ?")
                params.append(result)
            if error is not None:
                updates.append("error = ?")
                params.append(error)
            if started_at is not None:
                updates.append("started_at = ?")
                params.append(started_at)
            if completed_at is not None:
                updates.append("completed_at = ?")
                params.append(completed_at)
            params.append(task_id)
            cursor.execute(f"UPDATE tasks SET {', '.join(updates)} WHERE task_id = ?", params)
            conn.commit()

    def list_saved_tasks(self, limit: int = 50) -> List[Dict[str, Any]]:
        with self._db_lock, self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT task_id, title, status, progress, result, error, created_at, completed_at
                FROM tasks ORDER BY created_at DESC LIMIT ?
            """, (limit,))
            return [dict(r) for r in cursor.fetchall()]

    # --- Persistance des Routines ---

    def save_routine(self, routine_id: str, name: str, time_str: str,
                     action_type: str = "prompt", payload: str = "", enabled: bool = True) -> None:
        with self._db_lock, self._get_connection() as conn:
            cursor = conn.cursor()
            now = time.time()
            cursor.execute("""
                INSERT INTO routines (id, name, time_str, action_type, payload, enabled, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    name = excluded.name,
                    time_str = excluded.time_str,
                    action_type = excluded.action_type,
                    payload = excluded.payload,
                    enabled = excluded.enabled
            """, (routine_id, name, time_str, action_type, payload, 1 if enabled else 0, now))
            conn.commit()

    def load_routines(self) -> List[Dict[str, Any]]:
        with self._db_lock, self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM routines ORDER BY time_str ASC")
            return [dict(r) for r in cursor.fetchall()]

    def update_routine_last_run(self, routine_id: str, date_str: str) -> None:
        with self._db_lock, self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE routines SET last_run_date = ? WHERE id = ?", (date_str, routine_id))
            conn.commit()

db = DatabaseManager()
