import os
import re

import numpy as np

from embeddings import embed_passages, embed_query

CONFIG_FAQ_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "FAQs_Asistente_Bancario_Mavericks.txt")
CONFIG_TOP_K = 3
CONFIG_BLOCK_SEPARATOR = "\n---\n"


def _field(block, name):
    match = re.search(r"^" + name + r": (.*)$", block, re.M)
    if match is None:
        return ""
    return match.group(1).strip()


def load_faqs(path=CONFIG_FAQ_PATH):
    with open(path, encoding="utf-8") as handle:
        text = handle.read()
    faqs = []
    for block in text.split(CONFIG_BLOCK_SEPARATOR):
        if not block.strip():
            continue
        faqs.append(
            {
                "id": _field(block, "ID"),
                "question": _field(block, "PREGUNTA"),
                "answer": _field(block, "RESPUESTA"),
                "route": _field(block, "RUTA"),
                "internal_note": _field(block, "NOTA_INTERNA_PARA_EL_EQUIPO"),
            }
        )
    return faqs


class Retriever:
    def __init__(self, faqs=None):
        if faqs is None:
            faqs = load_faqs()
        self.faqs = faqs
        questions = []
        for faq in faqs:
            questions.append(faq["question"])
        self.matrix = embed_passages(questions)

    def search(self, query, top_k=CONFIG_TOP_K):
        scores = self.matrix @ embed_query(query)
        order = np.argsort(-scores)[:top_k]
        results = []
        for index in order:
            results.append({"faq": self.faqs[index], "score": float(scores[index])})
        return results
