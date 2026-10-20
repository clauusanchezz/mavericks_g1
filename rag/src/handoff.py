CONFIG_DESTINATION_HUMAN = "operador humano"
CONFIG_REASON_TEXTS = {
    "SIMULAR": "el cliente pide un calculo o simulacion (el router no lo desvio al agente de simulacion)",
    "PERSONA": "el cliente necesita atencion personal",
    "URGENTE": "posible situacion urgente (fraude, perdida o bloqueo)",
    "UNKNOWN": "ninguna FAQ cubre la pregunta",
}
CONFIG_HISTORY_TURNS = 3


def _recent_customer_messages(history):
    messages = []
    for turn in history:
        if turn.get("role") == "user":
            messages.append(turn.get("content", ""))
    return messages[-CONFIG_HISTORY_TURNS:]


def _was_clarified(history):
    for turn in history:
        if turn.get("status") == "needs_clarification":
            return True
    return False


def build_handoff_summary(question, history, route, faq_id):
    """Short note for whoever receives the call. route is the matched FAQ route or None when nothing matched."""
    reason_key = route
    if route is None:
        reason_key = "UNKNOWN"
    reason = CONFIG_REASON_TEXTS.get(reason_key, CONFIG_REASON_TEXTS["UNKNOWN"])

    lines = []
    lines.append("Destino: " + CONFIG_DESTINATION_HUMAN)
    lines.append("Motivo: " + reason)
    lines.append("Ultima pregunta del cliente: " + question)
    previous = _recent_customer_messages(history)
    if previous:
        lines.append("Mensajes anteriores del cliente: " + " | ".join(previous))
    if faq_id is not None:
        lines.append("FAQ mas parecida: " + faq_id)
    if _was_clarified(history):
        lines.append("Ya se le pidio una aclaracion y sigue sin cubrirse.")
    return "\n".join(lines)
