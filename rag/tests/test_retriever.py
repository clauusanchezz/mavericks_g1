import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from retriever import Retriever, load_faqs

VALID_ROUTES = ["FAQ", "BANCO", "SIMULAR", "PERSONA", "URGENTE"]


class ParserTest(unittest.TestCase):
    def test_fifty_faqs_are_parsed(self):
        self.assertEqual(len(load_faqs()), 50)

    def test_ids_are_unique_and_routes_valid(self):
        seen = []
        for faq in load_faqs():
            self.assertNotIn(faq["id"], seen)
            seen.append(faq["id"])
            self.assertIn(faq["route"], VALID_ROUTES)

    def test_every_faq_has_question_and_answer(self):
        for faq in load_faqs():
            self.assertTrue(faq["question"], faq["id"])
            self.assertTrue(faq["answer"], faq["id"])


class RetrieverTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.retriever = Retriever()

    def test_search_returns_top_k_sorted_by_score(self):
        results = self.retriever.search("¿Qué es una hipoteca?", 3)
        self.assertEqual(len(results), 3)
        self.assertGreaterEqual(results[0]["score"], results[1]["score"])
        self.assertGreaterEqual(results[1]["score"], results[2]["score"])

    def test_obvious_question_finds_its_faq(self):
        results = self.retriever.search("¿Me explicas qué es una hipoteca?", 3)
        self.assertEqual(results[0]["faq"]["id"], "FAQ_01")


if __name__ == "__main__":
    unittest.main()
