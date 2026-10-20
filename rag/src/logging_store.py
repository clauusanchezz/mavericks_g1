import os
import re
import sqlite3
from datetime import datetime, timezone

CONFIG_DB_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "interactions.db")
CONFIG_PII_PATTERNS = [
    ("[IBAN]", r"\b[A-Za-z]{2}\d{2}(?:[ -]?\d{4}){4,6}\b"),
    ("[EMAIL]", r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+"),
    ("[DNI]", r"\b(?:\d{8}|[XYZxyz]\d{7})[ -]?[A-Za-z]\b"),
    ("[CARD]", r"\b\d{4}(?:[ -]?\d{4}){2,3}\b"),
    ("[PHONE]", r"(?:\+\d{2}[ -]?)?\b[6-9]\d{2}[ -]?\d{3}[ -]?\d{3}\b"),
    ("[NUMBER]", r"\b\d{9,}\b"),
]

_SCHEMA = (
    "CREATE TABLE IF NOT EXISTS interactions ("
    "id INTEGER PRIMARY KEY AUTOINCREMENT, "
    "timestamp TEXT NOT NULL, "
    "question TEXT NOT NULL, "
    "retrieved_ids TEXT NOT NULL, "
    "best_route TEXT, "
    "confidence REAL NOT NULL, "
    "status TEXT NOT NULL, "
    "source_faq_id TEXT, "
    "followup_of TEXT, "
    "solved INTEGER)"
)


def mask_personal_data(text):
    """Replace obvious personal identifiers (IBAN, email, DNI/NIE, card, phone, long numbers) with tags."""
    masked = text
    for tag, pattern in CONFIG_PII_PATTERNS:
        masked = re.sub(pattern, tag, masked)
    return masked


def _connect(db_path):
    connection = sqlite3.connect(db_path)
    connection.execute(_SCHEMA)
    return connection


def followup_of(history):
    """FAQ id the previous assistant turn answered, or None. Assistant turns carry status and source_faq_id."""
    for turn in reversed(history):
        if turn.get("role") == "assistant":
            if turn.get("status") == "answered":
                return turn.get("source_faq_id")
            return None
    return None


def log_interaction(question, history, result, retrieved, db_path=CONFIG_DB_PATH):
    """Store one interaction and return its id. retrieved is the list of search results (faq and score)."""
    ids = []
    for item in retrieved:
        ids.append(item["faq"]["id"])
    best_route = None
    if retrieved:
        best_route = retrieved[0]["faq"]["route"]

    connection = _connect(db_path)
    try:
        cursor = connection.execute(
            "INSERT INTO interactions (timestamp, question, retrieved_ids, best_route, confidence, status, "
            "source_faq_id, followup_of) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (
                datetime.now(timezone.utc).isoformat(timespec="seconds"),
                mask_personal_data(question),
                ",".join(ids),
                best_route,
                result["confidence"],
                result["status"],
                result["source_faq_id"],
                followup_of(history),
            ),
        )
        connection.commit()
        return cursor.lastrowid
    finally:
        connection.close()


def mark_solved(solved, db_path=CONFIG_DB_PATH):
    """Record the customer's answer to 'did that solve it?' on the most recent answered interaction."""
    connection = _connect(db_path)
    try:
        connection.execute(
            "UPDATE interactions SET solved = ? WHERE id = ("
            "SELECT id FROM interactions WHERE status = 'answered' ORDER BY id DESC LIMIT 1)",
            (int(solved),),
        )
        connection.commit()
    finally:
        connection.close()
