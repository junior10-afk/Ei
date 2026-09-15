import os
import sys
import unittest
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from tools.web_search import is_safe_public_url
from tools.code_runner import validate_python_code_ast
from tools.registry import tool_confirmation_manager
from core.config import config, deep_merge, EiConfigSchema
from core.database import db
from core.task_manager import task_manager

class TestEiEvolutionSuite(unittest.TestCase):
    """Suite de tests automatisée pour la sécurité, l'agent et la persistance."""

    # 1. Tests Anti-SSRF
    def test_ssrf_protection(self):
        """Vérifie que les IP privées, loopback et cloud metadata sont strictement bloquées."""
        unsafe_urls = [
            "http://127.0.0.1",
            "http://127.0.0.1:8080/admin",
            "http://localhost",
            "http://localhost:5000",
            "http://169.254.169.254/latest/meta-data/",
            "http://192.168.1.1",
            "http://192.168.0.254",
            "http://10.0.0.1/api",
            "http://172.16.0.1",
            "ftp://ftp.google.com",
            "file:///C:/Windows/System32"
        ]
        for url in unsafe_urls:
            is_safe, reason = is_safe_public_url(url)
            self.assertFalse(is_safe, f"L'URL {url} aurait dû être bloquée ! (Raison: {reason})")

        safe_urls = [
            "https://www.google.com",
            "https://fr.wikipedia.org/wiki/Intelligence_artificielle",
            "https://duckduckgo.com"
        ]
        for url in safe_urls:
            is_safe, reason = is_safe_public_url(url)
            self.assertTrue(is_safe, f"L'URL publique {url} aurait dû être autorisée ! (Raison: {reason})")

    # 2. Tests Bac à Sable AST (Sandbox Python)
    def test_code_sandbox_ast_rejection(self):
        """Vérifie le blocage proactif par analyse statique AST des constructions malveillantes."""
        malicious_codes = [
            "import subprocess; subprocess.run(['calc'])",
            "import os; os.system('echo test')",
            "import ctypes; ctypes.windll.user32.MessageBoxW(0, 'x', 'x', 0)",
            "import socket; s = socket.socket()",
            "eval('1 + 1')",
            "exec('x = 2')",
            "__import__('os').system('dir')",
            "class X: pass\nX.__subclasses__()",
        ]
        for code in malicious_codes:
            err = validate_python_code_ast(code)
            self.assertIsNotNone(err, f"Le code malveillant « {code} » aurait dû être rejeté par l'AST !")

    def test_code_sandbox_ast_allowed(self):
        """Vérifie que les calculs purs et modules autorisés sont acceptés."""
        safe_codes = [
            "import math\nprint(math.sqrt(144))",
            "numbers = [1, 2, 3, 4, 5]\nprint([x**2 for x in numbers])",
            "import json\ndata = {'val': 42}\nprint(json.dumps(data))",
            "import datetime\nprint(datetime.datetime.now())"
        ]
        for code in safe_codes:
            err = validate_python_code_ast(code)
            self.assertIsNone(err, f"Le code sain « {code} » a été rejeté à tort : {err}")

    # 3. Tests Confirmation Manager
    def test_tool_confirmation_workflow(self):
        """Vérifie le mécanisme de garde par confirmation."""
        # Sans client HUD connecté, toute action sensible doit être bloquée par sécurité
        tool_confirmation_manager.bypass_all = False
        blocked = tool_confirmation_manager.request_confirmation("write_local_file", {}, "Test", timeout_sec=0.1)
        self.assertFalse(blocked, "L'action sensible sans HUD aurait dû être bloquée !")

        # Quand bypass_all est actif (mode auto ou autorisation globale), l'accès est accordé
        tool_confirmation_manager.bypass_all = True
        allowed = tool_confirmation_manager.request_confirmation("write_local_file", {}, "Test", timeout_sec=0.1)
        self.assertTrue(allowed, "L'action aurait dû être acceptée en mode bypass !")
        tool_confirmation_manager.bypass_all = False

    # 4. Tests Mémoire FTS5 & Droit à l'oubli
    def test_database_memory_and_forget(self):
        """Vérifie l'enregistrement, le rappel sémantique et la suppression définitive d'un fait."""
        key = "boisson_preferee"
        val = "Café espresso corsé"

        # Mémorisation
        self.assertTrue(db.remember_fact(key, val, "preferences"))

        # Rappel
        recalled = db.recall_fact("boisson")
        self.assertIsNotNone(recalled)
        self.assertEqual(recalled["key"], key)
        self.assertIn("espresso", recalled["value"])

        # Oubli (droit à l'oubli)
        forgotten_key = db.forget_fact("boisson")
        self.assertEqual(forgotten_key, key)

        # Vérification qu'il est bien effacé
        recalled_after = db.recall_fact(key)
        self.assertIsNone(recalled_after)

    # 5. Tests Compaction de Session
    def test_database_session_compaction(self):
        """Vérifie que les sessions de plus de 14 messages sont condensées."""
        import uuid
        test_session_id = f"session_test_{uuid.uuid4().hex[:8]}"
        db.create_or_get_session(test_session_id, "Test Compaction")

        # Insérer 16 messages
        for i in range(16):
            role = "user" if i % 2 == 0 else "assistant"
            db.save_message(test_session_id, role, f"Message de test numéro {i}")

        messages_before = db.get_recent_messages(test_session_id, limit=30)
        self.assertEqual(len(messages_before), 16)

        # Compacter (garder les 10 derniers)
        compacted = db.compact_session(test_session_id, keep_last=10)
        self.assertTrue(compacted)

        messages_after = db.get_recent_messages(test_session_id, limit=30)
        # 1 message système de résumé + 10 messages récents = 11
        self.assertEqual(len(messages_after), 11)

        # Vérifier qu'un message de compaction existe
        compaction_msg = next((m for m in messages_after if m.get("metadata", {}).get("type") == "compaction"), None)
        self.assertIsNotNone(compaction_msg)
        self.assertEqual(compaction_msg["role"], "system")
        self.assertIn("Résumé des échanges", compaction_msg["content"])

    # 6. Tests Deep Merge & Validation Pydantic
    def test_config_deep_merge_and_schema(self):
        """Vérifie que le deep merge ne détruit pas les sous-dictionnaires."""
        target = {
            "models": {
                "tiers": {
                    "chat": "model-a",
                    "light": "model-b",
                    "heavy": "model-c"
                }
            },
            "user_city": "Lomé"
        }
        update = {
            "models": {
                "tiers": {
                    "chat": "model-a-new"
                }
            }
        }
        merged = deep_merge(target, update)
        self.assertEqual(merged["models"]["tiers"]["chat"], "model-a-new")
        self.assertEqual(merged["models"]["tiers"]["light"], "model-b")
        self.assertEqual(merged["models"]["tiers"]["heavy"], "model-c")
        self.assertEqual(merged["user_city"], "Lomé")

        # Test validation schéma
        schema = EiConfigSchema(**merged)
        self.assertEqual(schema.user_city, "Lomé")
        self.assertEqual(schema.assistant_name, "EI")

    # 7. Tests Task Manager & Annulation
    def test_task_manager_cancellation(self):
        """Vérifie qu'une tâche longue peut être annulée sans bloquer le runtime."""
        import time

        def long_task():
            for _ in range(50):
                time.sleep(0.05)
            return "done"

        task_id = task_manager.submit_task("Tâche de calcul longue", long_task)
        self.assertIsNotNone(task_id)

        time.sleep(0.1)
        cancelled = task_manager.cancel_task(task_id)
        self.assertTrue(cancelled)

        task_data = task_manager.get_task(task_id)
        self.assertEqual(task_data["status"], "cancelled")

if __name__ == "__main__":
    unittest.main(verbosity=2)
