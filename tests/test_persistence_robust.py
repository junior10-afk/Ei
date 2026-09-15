import sys, time, unittest
from pathlib import Path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from core.database import db
from core.scheduler import is_routine_due
from core.task_manager import task_manager

class TestRemindersPersistence(unittest.TestCase):
    def test_reminder_survit(self):
        rid = "rem_test_persist_001"
        db.add_reminder_persisted(rid, "Test", "arroser les plantes", time.time() + 3600)
        rows = {r["id"] for r in db.get_pending_reminders()}
        self.assertIn(rid, rows)
        db.mark_reminder_fired(rid)
        rows2 = {r["id"] for r in db.get_pending_reminders()}
        self.assertNotIn(rid, rows2)

    def test_reminder_champs_roundtrip(self):
        rid = "rem_test_persist_002"
        trigger = time.time() + 7200
        db.add_reminder_persisted(rid, "TestChamps", "vérifier les plantes", trigger)
        rows = {r["id"]: r for r in db.get_pending_reminders()}
        self.assertIn(rid, rows)
        self.assertEqual(rows[rid]["label"], "TestChamps")
        self.assertEqual(rows[rid]["message"], "vérifier les plantes")
        self.assertAlmostEqual(rows[rid]["trigger_time"], trigger, places=3)

    def tearDown(self):
        with db._db_lock, db._get_connection() as conn:
            conn.execute("DELETE FROM reminders WHERE id LIKE 'rem_test_%'")
            conn.commit()

class TestRoutineDue(unittest.TestCase):
    def _dt(self, h, m):
        from datetime import datetime
        return datetime(2026, 9, 11, h, m, 0)

    def test_due_maintenant(self):
        self.assertTrue(is_routine_due("08:00", None, self._dt(8, 0)))

    def test_rattrapage_heure_passee(self):
        self.assertTrue(is_routine_due("08:00", None, self._dt(9, 30)))

    def test_pas_encore_due(self):
        self.assertFalse(is_routine_due("08:00", None, self._dt(7, 0)))

    def test_deja_lance_aujourdhui(self):
        self.assertFalse(is_routine_due("08:00", "2026-09-11", self._dt(9, 30)))

    def test_format_invalide(self):
        self.assertFalse(is_routine_due("invalid", None, self._dt(9, 30)))

class TestStaleTasks(unittest.TestCase):
    def test_purge_taches_orphelines(self):
        db.save_task("task_test_stale_001", "test", status="running")
        n = db.fail_stale_tasks()
        self.assertGreaterEqual(n, 1)
        saved = {t["task_id"]: t for t in db.list_saved_tasks(50)}
        self.assertEqual(saved["task_test_stale_001"]["status"], "failed")

    def test_stale_ne_touche_pas_les_terminees(self):
        db.save_task("task_test_stale_002", "test", status="completed")
        db.fail_stale_tasks()
        saved = {t["task_id"]: t for t in db.list_saved_tasks(50)}
        self.assertEqual(saved["task_test_stale_002"]["status"], "completed")

    def tearDown(self):
        with db._db_lock, db._get_connection() as conn:
            conn.execute("DELETE FROM tasks WHERE task_id LIKE 'task_test_%'")
            conn.commit()

if __name__ == "__main__":
    unittest.main()
