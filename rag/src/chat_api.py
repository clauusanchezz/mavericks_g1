from faq_agent import answer_faq
from logging_store import mark_solved

CONFIG_MAX_MESSAGE_CHARS = 500
CONFIG_MAX_HISTORY_TURNS = 12
CONFIG_ALLOWED_ROLES = ["user", "assistant"]
CONFIG_TURN_KEYS = ["role", "content", "status", "source_faq_id"]


def clean_history(history):
    """Keep only well-formed turns with known keys and cap the length."""
    cleaned = []
    if not isinstance(history, list):
        return cleaned
    for turn in history:
        if not isinstance(turn, dict):
            continue
        if turn.get("role") not in CONFIG_ALLOWED_ROLES:
            continue
        if not isinstance(turn.get("content"), str):
            continue
        item = {}
        for key in CONFIG_TURN_KEYS:
            if key in turn:
                item[key] = turn[key]
        cleaned.append(item)
    return cleaned[-CONFIG_MAX_HISTORY_TURNS:]


def handle_chat(payload):
    """Validate the request body and call the agent. Returns (status_code, body)."""
    if not isinstance(payload, dict):
        return 400, {"error": "The body must be a JSON object."}
    message = payload.get("message")
    if not isinstance(message, str) or not message.strip():
        return 400, {"error": "Write a question first."}
    if len(message) > CONFIG_MAX_MESSAGE_CHARS:
        return 400, {"error": "The message is too long (maximum " + str(CONFIG_MAX_MESSAGE_CHARS) + " characters)."}
    history = clean_history(payload.get("history", []))
    return 200, answer_faq(message.strip(), history)


def handle_solved(payload):
    """Record whether the customer said the last answer solved the question."""
    if not isinstance(payload, dict) or not isinstance(payload.get("solved"), bool):
        return 400, {"error": "The body must be {\"solved\": true or false}."}
    mark_solved(payload["solved"])
    return 200, {"ok": True}
