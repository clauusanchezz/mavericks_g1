import os
import sys
import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import llm_client


def fake_response(stop_reason, text):
    return SimpleNamespace(stop_reason=stop_reason, content=[SimpleNamespace(type="text", text=text)])


class GenerateTest(unittest.TestCase):
    def _generate_with(self, response):
        client = MagicMock()
        client.messages.create.return_value = response
        with patch.object(llm_client, "_get_client", return_value=client):
            return llm_client.generate("system", "user"), client

    def test_complete_reply_is_returned_stripped(self):
        text, _ = self._generate_with(fake_response("end_turn", "  hola  "))
        self.assertEqual(text, "hola")

    def test_truncated_reply_is_discarded(self):
        text, _ = self._generate_with(fake_response("max_tokens", "En una hipoteca"))
        self.assertEqual(text, "")

    def test_thinking_is_disabled_so_it_cannot_use_up_the_token_budget(self):
        _, client = self._generate_with(fake_response("end_turn", "ok"))
        kwargs = client.messages.create.call_args.kwargs
        self.assertEqual(kwargs["thinking"], {"type": "disabled"})


if __name__ == "__main__":
    unittest.main()
