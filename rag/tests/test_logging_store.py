import os
import sqlite3
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from logging_store import followup_of, log_interaction, mark_solved

RETRIEVED = [
    {"faq": {"id": "FAQ_01", "route": "FAQ"}, "score": 0.9},
    {"faq": {"id": "FAQ_06", "route": "FAQ"}, "score": 0.8},
]
RESULT = {"status": "answered", "answer": "x", "source_faq_id": "FAQ_01", "confidence": 0.9, "handoff_summary": None}


class LoggingStoreTest(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.directory.name, "test.db")

    def tearDown(self):
        self.directory.cleanup()

    def _rows(self):
        connection = sqlite3.connect(self.db_path)
        rows = connection.execute(
            "SELECT question, retrieved_ids, best_route, status, source_faq_id, followup_of, solved FROM interactions"
        ).fetchall()
        connection.close()
        return rows

    def test_question_is_stored_masked(self):
        log_interaction("Mi DNI es 12345678Z, que es una hipoteca?", [], RESULT, RETRIEVED, self.db_path)
        rows = self._rows()
        self.assertEqual(len(rows), 1)
        self.assertNotIn("12345678", rows[0][0])
        self.assertIn("[DNI]", rows[0][0])

    def test_retrieved_ids_route_and_status_are_stored(self):
        log_interaction("que es una hipoteca?", [], RESULT, RETRIEVED, self.db_path)
        row = self._rows()[0]
        self.assertEqual(row[1], "FAQ_01,FAQ_06")
        self.assertEqual(row[2], "FAQ")
        self.assertEqual(row[3], "answered")
        self.assertEqual(row[4], "FAQ_01")
        self.assertIsNone(row[6])

    def test_mark_solved_updates_latest_answered(self):
        log_interaction("primera", [], RESULT, RETRIEVED, self.db_path)
        log_interaction("segunda", [], RESULT, RETRIEVED, self.db_path)
        mark_solved(False, self.db_path)
        rows = self._rows()
        self.assertIsNone(rows[0][6])
        self.assertEqual(rows[1][6], 0)

    def test_followup_of_reads_previous_answered_turn(self):
        history = [
            {"role": "user", "content": "hola"},
            {"role": "assistant", "content": "x", "status": "answered", "source_faq_id": "FAQ_07"},
        ]
        self.assertEqual(followup_of(history), "FAQ_07")

    def test_followup_of_is_none_after_a_handoff_or_empty_history(self):
        self.assertIsNone(followup_of([]))
        history = [{"role": "assistant", "content": "x", "status": "handoff", "source_faq_id": None}]
        self.assertIsNone(followup_of(history))


if __name__ == "__main__":
    unittest.main()
