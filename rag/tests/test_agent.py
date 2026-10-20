import os
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import faq_agent

CONTRACT_KEYS = ["status", "answer", "source_faq_id", "confidence", "handoff_summary"]
STATUSES = ["answered", "needs_clarification", "handoff"]
FAQ_TEXT = "El plazo es de 30 dias y la comision es del 2 %."


class ContractTest(unittest.TestCase):
    def setUp(self):
        patcher_log = patch.object(faq_agent, "CONFIG_LOG_ENABLED", False)
        patcher_llm = patch.object(faq_agent, "CONFIG_USE_LLM", False)
        patcher_log.start()
        patcher_llm.start()
        self.addCleanup(patcher_log.stop)
        self.addCleanup(patcher_llm.stop)

    def _check_contract(self, result):
        self.assertEqual(sorted(result.keys()), sorted(CONTRACT_KEYS))
        self.assertIn(result["status"], STATUSES)
        self.assertGreaterEqual(result["confidence"], 0.0)
        self.assertLessEqual(result["confidence"], 1.0)

    def test_covered_question_is_answered_with_source(self):
        result = faq_agent.answer_faq("¿Me explicas qué es una hipoteca?", [])
        self._check_contract(result)
        self.assertEqual(result["status"], "answered")
        self.assertEqual(result["source_faq_id"], "FAQ_01")
        self.assertIsNone(result["handoff_summary"])
        self.assertTrue(result["answer"].endswith(faq_agent.CONFIG_FOLLOWUP_TEXT))

    def test_banco_route_is_answered(self):
        result = faq_agent.answer_faq("¿Qué hace falta para abrir una cuenta?", [])
        self._check_contract(result)
        self.assertEqual(result["status"], "answered")
        self.assertEqual(result["source_faq_id"], "FAQ_31")

    def test_urgent_question_goes_to_a_human_with_summary(self):
        result = faq_agent.answer_faq("He perdido mi tarjeta de crédito", [])
        self._check_contract(result)
        self.assertEqual(result["status"], "handoff")
        self.assertEqual(result["answer"], "")
        self.assertIn("operador humano", result["handoff_summary"])

    def test_unknown_question_clarifies_once_then_hands_off(self):
        first = faq_agent.answer_faq("¿Cuál es la capital de Francia?", [])
        self._check_contract(first)
        self.assertEqual(first["status"], "needs_clarification")
        self.assertIsNone(first["source_faq_id"])

        history = [
            {"role": "user", "content": "¿Cuál es la capital de Francia?"},
            {"role": "assistant", "content": first["answer"], "status": first["status"], "source_faq_id": None},
        ]
        second = faq_agent.answer_faq("¿Cuál es la capital de Francia?", history)
        self._check_contract(second)
        self.assertEqual(second["status"], "handoff")
        self.assertIsNone(second["source_faq_id"])


class ShortQuestionContextTest(unittest.TestCase):
    def setUp(self):
        patcher_log = patch.object(faq_agent, "CONFIG_LOG_ENABLED", False)
        patcher_llm = patch.object(faq_agent, "CONFIG_USE_LLM", False)
        patcher_log.start()
        patcher_llm.start()
        self.addCleanup(patcher_log.stop)
        self.addCleanup(patcher_llm.stop)

    def test_clear_short_question_ignores_the_previous_topic(self):
        history = [
            {"role": "user", "content": "¿Qué es el euríbor y cómo afecta a mi hipoteca?"},
            {"role": "assistant", "content": "x", "status": "answered", "source_faq_id": "FAQ_07"},
        ]
        result = faq_agent.answer_faq("he perdido mi tarjeta", history)
        self.assertEqual(result["status"], "handoff")
        self.assertNotEqual(result["source_faq_id"], "FAQ_07")
        self.assertIn("urgente", result["handoff_summary"])

    def test_unclear_new_topic_is_not_glued_to_the_previous_answer(self):
        history = [
            {"role": "user", "content": "¿Qué es el euríbor y cómo afecta a mi hipoteca?"},
            {"role": "assistant", "content": "x", "status": "answered", "source_faq_id": "FAQ_07"},
        ]
        result = faq_agent.answer_faq("me han robado la cartera", history)
        self.assertNotEqual(result["source_faq_id"], "FAQ_07")
        self.assertNotEqual(result["status"], "answered")

    def test_followup_detection(self):
        self.assertTrue(faq_agent._looks_like_followup("¿Y si es a 30 años?"))
        self.assertTrue(faq_agent._looks_like_followup("¿Cómo funciona eso?"))
        self.assertTrue(faq_agent._looks_like_followup("Entonces cuánto tarda"))
        self.assertFalse(faq_agent._looks_like_followup("me han robado la cartera"))
        self.assertFalse(faq_agent._looks_like_followup(""))

    def test_unclear_short_question_uses_the_previous_message_when_it_scores_higher(self):
        class FakeRetriever:
            def search(self, query, top_k=3):
                faq_low = {"id": "FAQ_99", "route": "FAQ", "question": "q", "answer": "a"}
                faq_high = {"id": "FAQ_01", "route": "FAQ", "question": "q", "answer": "a"}
                if "hipoteca" in query:
                    return [{"faq": faq_high, "score": 0.95}]
                return [{"faq": faq_low, "score": 0.5}]

        history = [{"role": "user", "content": "¿Qué es una hipoteca?"}]
        with patch.object(faq_agent, "_get_retriever", return_value=FakeRetriever()):
            result = faq_agent.answer_faq("¿y eso cuánto cuesta?", history)
        self.assertEqual(result["source_faq_id"], "FAQ_01")

    def test_long_question_never_uses_the_previous_message(self):
        class FakeRetriever:
            def __init__(self):
                self.queries = []

            def search(self, query, top_k=3):
                self.queries.append(query)
                faq = {"id": "FAQ_99", "route": "FAQ", "question": "q", "answer": "a"}
                return [{"faq": faq, "score": 0.5}]

        fake = FakeRetriever()
        history = [{"role": "user", "content": "¿Qué es una hipoteca?"}]
        question = "esta es una pregunta bastante larga sobre algo distinto del tema anterior"
        with patch.object(faq_agent, "_get_retriever", return_value=fake):
            faq_agent.answer_faq(question, history)
        self.assertEqual(fake.queries, [question])


class RephraseGuardTest(unittest.TestCase):
    def test_clean_rephrase_is_used(self):
        with patch.object(faq_agent, "CONFIG_USE_LLM", True):
            with patch.object(faq_agent, "generate", return_value="Tienes 30 dias y la comision es del 2 %."):
                self.assertEqual(faq_agent._rephrase("pregunta", FAQ_TEXT), "Tienes 30 dias y la comision es del 2 %.")

    def test_new_number_falls_back_to_literal_text(self):
        with patch.object(faq_agent, "CONFIG_USE_LLM", True):
            with patch.object(faq_agent, "generate", return_value="Tienes 45 dias."):
                self.assertEqual(faq_agent._rephrase("pregunta", FAQ_TEXT), FAQ_TEXT)

    def test_mention_of_faq_falls_back_to_literal_text(self):
        with patch.object(faq_agent, "CONFIG_USE_LLM", True):
            with patch.object(faq_agent, "generate", return_value="La FAQ habla de 30 dias."):
                self.assertEqual(faq_agent._rephrase("pregunta", FAQ_TEXT), FAQ_TEXT)

    def test_api_failure_falls_back_to_literal_text(self):
        with patch.object(faq_agent, "CONFIG_USE_LLM", True):
            with patch.object(faq_agent, "generate", side_effect=RuntimeError("down")):
                self.assertEqual(faq_agent._rephrase("pregunta", FAQ_TEXT), FAQ_TEXT)

    def test_empty_reply_falls_back_to_literal_text(self):
        with patch.object(faq_agent, "CONFIG_USE_LLM", True):
            with patch.object(faq_agent, "generate", return_value=""):
                self.assertEqual(faq_agent._rephrase("pregunta", FAQ_TEXT), FAQ_TEXT)

    def test_llm_disabled_returns_literal_text_without_calling_the_api(self):
        with patch.object(faq_agent, "CONFIG_USE_LLM", False):
            with patch.object(faq_agent, "generate", side_effect=AssertionError("must not be called")):
                self.assertEqual(faq_agent._rephrase("pregunta", FAQ_TEXT), FAQ_TEXT)


if __name__ == "__main__":
    unittest.main()
