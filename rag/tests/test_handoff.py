import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from handoff import build_handoff_summary


class HandoffSummaryTest(unittest.TestCase):
    def test_summary_names_destination_reason_and_question(self):
        summary = build_handoff_summary("He perdido mi tarjeta", [], "URGENTE", "FAQ_39")
        self.assertIn("operador humano", summary)
        self.assertIn("urgente", summary)
        self.assertIn("He perdido mi tarjeta", summary)
        self.assertIn("FAQ_39", summary)

    def test_unknown_question_has_unknown_reason(self):
        summary = build_handoff_summary("capital de Francia", [], None, "FAQ_17")
        self.assertIn("ninguna FAQ cubre la pregunta", summary)

    def test_simulation_route_mentions_the_router_missed_it(self):
        summary = build_handoff_summary("cuanto pagaria al mes", [], "SIMULAR", "FAQ_12")
        self.assertIn("router", summary)

    def test_previous_messages_and_clarification_are_included(self):
        history = [
            {"role": "user", "content": "Hola"},
            {"role": "assistant", "content": "x", "status": "needs_clarification"},
        ]
        summary = build_handoff_summary("capital de Francia", history, None, None)
        self.assertIn("Hola", summary)
        self.assertIn("aclaracion", summary)
        self.assertNotIn("FAQ mas parecida", summary)

    def test_only_the_last_customer_messages_are_kept(self):
        history = []
        for index in range(6):
            history.append({"role": "user", "content": "mensaje" + str(index)})
        summary = build_handoff_summary("ultima", history, None, None)
        self.assertNotIn("mensaje0", summary)
        self.assertIn("mensaje5", summary)


if __name__ == "__main__":
    unittest.main()
