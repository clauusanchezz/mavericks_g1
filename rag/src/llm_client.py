import os

import anthropic
from dotenv import load_dotenv

CONFIG_MODEL_NAME = "claude-haiku-5-5"
CONFIG_EFFORT = "low"
CONFIG_ENV_PATH = os.path.join(os.path.dirname(__file__), "..", ".env")
CONFIG_MAX_TOKENS = 400

load_dotenv(CONFIG_ENV_PATH)

_client = None


def _get_client():
    global _client
    if _client is None:
        _client = anthropic.Anthropic()
    return _client


def generate(system_prompt, user_prompt):
    response = _get_client().messages.create(
        model=CONFIG_MODEL_NAME,
        max_tokens=CONFIG_MAX_TOKENS,
        output_config={"effort": CONFIG_EFFORT},
        thinking={"type": "disabled"},
        system=system_prompt,
        messages=[{"role": "user", "content": user_prompt}],
    )
    if response.stop_reason != "end_turn":
        return ""
    text = ""
    for block in response.content:
        if block.type == "text":
            text += block.text
    return text.strip()
