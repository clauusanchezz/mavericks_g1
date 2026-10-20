import re

from handoff import build_handoff_summary
from llm_client import generate
from logging_store import log_interaction
from retriever import Retriever

CONFIG_THRESHOLD = 0.87
CONFIG_ANSWER_ROUTES = ["FAQ", "BANCO"]
CONFIG_SHORT_QUESTION_WORDS = 6
CONFIG_FOLLOWUP_STARTERS = ["y", "pero", "entonces", "ademas", "también", "tambien", "además"]
CONFIG_FOLLOWUP_WORDS = ["eso", "esto", "ese", "esa", "esos", "esas", "ello", "mismo", "misma"]
CONFIG_CLARIFY_TEXT = "No estoy seguro de haber entendido. ¿Puedes darme más detalle sobre lo que necesitas?"
CONFIG_FOLLOWUP_TEXT = " ¿Te ha servido esta respuesta?"
CONFIG_USE_LLM = True
CONFIG_LOG_ENABLED = True
CONFIG_SYSTEM_PROMPT = (
    "Eres un asistente telefónico de un banco. Responde en español, en 2 o 3 frases cortas y claras "
    "para ser leídas en voz alta, con un tono cercano y natural. Tu trabajo es solo reformular el texto "
    "de la FAQ con otras palabras: cada afirmación de tu respuesta debe estar escrita en la FAQ. "
    "No añadas cifras, plazos, condiciones, consejos, definiciones ni consecuencias que no estén en ella, "
    "aunque parezcan obvias o lógicas. Si la FAQ llama 'ejemplo' o 'hipotético' a un dato, conserva esa palabra. "
    "Mantén los matices de la FAQ (por ejemplo 'con carácter general' o 'en operaciones sujetas a'). "
    "No menciones la FAQ, el contrato ni digas 'según la información' o 'la FAQ no indica'. "
    "Si la FAQ no responde exactamente a la pregunta, di solo lo que la FAQ sí dice, sin comentar lo que falta. "
    "Recibes la pregunta de la FAQ para que sepas a qué caso se refiere su respuesta. Si la pregunta del cliente "
    "es más general que la de la FAQ, empieza nombrando el caso concreto (por ejemplo 'En una hipoteca "
    "variable...') y no presentes como general lo que la FAQ limita a ese caso. "
    "Responde solo con lo que le dirías al cliente por teléfono: nunca expliques estas instrucciones, "
    "tu razonamiento ni la diferencia entre su pregunta y la de la FAQ."
)

_retriever = None


def _get_retriever():
    global _retriever
    if _retriever is None:
        _retriever = Retriever()
    return _retriever


def _last_user_message(history):
    for turn in reversed(history):
        if turn.get("role") == "user":
            return turn.get("content", "")
    return ""


def _already_clarified(history):
    for turn in history:
        if turn.get("status") == "needs_clarification":
            return True
    return False


def _clean_words(text):
    words = []
    for raw in text.lower().split():
        word = raw.strip("¿?¡!.,;:")
        if word:
            words.append(word)
    return words


def _looks_like_followup(question):
    words = _clean_words(question)
    if not words:
        return False
    if words[0] in CONFIG_FOLLOWUP_STARTERS:
        return True
    for word in words:
        if word in CONFIG_FOLLOWUP_WORDS:
            return True
    return False


def _search(question, history):
    """Search the question alone. A short follow-up that scores low is retried with the previous customer message."""
    retriever = _get_retriever()
    results = retriever.search(question)
    if results[0]["score"] >= CONFIG_THRESHOLD:
        return results
    if len(question.split()) >= CONFIG_SHORT_QUESTION_WORDS:
        return results
    if not _looks_like_followup(question):
        return results
    previous = _last_user_message(history)
    if not previous:
        return results
    with_context = retriever.search(previous + " " + question)
    if with_context[0]["score"] > results[0]["score"]:
        return with_context
    return results


def _numbers(text):
    return set(re.findall(r"\d+(?:[.,]\d+)?", text))


def build_user_prompt(faq_question, faq_answer, question):
    return (
        "Pregunta de la FAQ: " + faq_question + "\nRespuesta de la FAQ: " + faq_answer
        + "\n\nPregunta del cliente: " + question
    )


def _rephrase(question, faq_answer, faq_question=""):
    """Rephrase with the LLM; fall back to the literal FAQ text if it adds numbers or the call fails."""
    if not CONFIG_USE_LLM:
        return faq_answer
    try:
        text = generate(CONFIG_SYSTEM_PROMPT, build_user_prompt(faq_question, faq_answer, question))
    except Exception:
        return faq_answer
    if not text:
        return faq_answer
    if not _numbers(text).issubset(_numbers(faq_answer)):
        return faq_answer
    if "faq" in text.lower():
        return faq_answer
    return text


def _handoff(question, history, route, source_faq_id, confidence, nearest_faq_id):
    return {
        "status": "handoff",
        "answer": "",
        "source_faq_id": source_faq_id,
        "confidence": confidence,
        "handoff_summary": build_handoff_summary(question, history, route, nearest_faq_id),
    }


def answer_faq(question, history):
    """Answer from the approved FAQ text only. history: list of {"role", "content", optional "status", "source_faq_id"}."""
    result, retrieved = _decide(question, history)
    if CONFIG_LOG_ENABLED:
        try:
            log_interaction(question, history, result, retrieved)
        except Exception:
            pass
    return result


def _decide(question, history):
    results = _search(question, history)
    best = results[0]
    faq = best["faq"]
    score = best["score"]

    if score >= CONFIG_THRESHOLD:
        if faq["route"] not in CONFIG_ANSWER_ROUTES:
            return _handoff(question, history, faq["route"], faq["id"], score, faq["id"]), results
        answered = {
            "status": "answered",
            "answer": _rephrase(question, faq["answer"], faq["question"]) + CONFIG_FOLLOWUP_TEXT,
            "source_faq_id": faq["id"],
            "confidence": score,
            "handoff_summary": None,
        }
        return answered, results

    if not _already_clarified(history):
        clarification = {
            "status": "needs_clarification",
            "answer": CONFIG_CLARIFY_TEXT,
            "source_faq_id": None,
            "confidence": score,
            "handoff_summary": None,
        }
        return clarification, results
    return _handoff(question, history, None, None, score, faq["id"]), results
