import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "tests"))

from faq_agent import CONFIG_SYSTEM_PROMPT, build_user_prompt, _numbers, _get_retriever
from llm_client import generate
from testset import CASES

CONFIG_JUDGE_PROMPT = (
    "Eres un revisor estricto de un banco. Recibes el texto oficial de una FAQ y una respuesta que un "
    "asistente ha dado a un cliente. Decide si la respuesta es FIEL: todo lo que afirma esta apoyado por la "
    "FAQ, sin cifras, plazos, condiciones, garantias ni promesas nuevas, y sin volver absoluta una afirmacion "
    "que en la FAQ es matizada. Tampoco es FIEL si presenta como general algo que la pregunta de la FAQ limita a "
    "un caso concreto (por ejemplo solo la hipoteca variable). Omitir informacion de la FAQ es aceptable. "
    "Responde exactamente con dos lineas. Linea 1: solo FIEL o NO_FIEL. Linea 2: una razon de una frase."
)
CONFIG_KINDS = ["paraphrase", "banco"]
CONFIG_VERDICT_FAITHFUL = "FIEL"
CONFIG_JUDGE_RETRIES = 3


def judge(faq_question, faq_answer, reply):
    prompt = "Pregunta de la FAQ: " + faq_question + "\nRespuesta de la FAQ:\n" + faq_answer + "\n\nRespuesta del asistente:\n" + reply
    lines = []
    for attempt in range(CONFIG_JUDGE_RETRIES):
        text = generate(CONFIG_JUDGE_PROMPT, prompt)
        lines = text.splitlines()
        if lines:
            break
    if not lines:
        return "EMPTY", "the judge returned no text"
    verdict = ""
    for character in lines[0].upper():
        if character.isalpha() or character == "_":
            verdict += character
    reason = ""
    if len(lines) > 1:
        reason = lines[1].strip()
    return verdict, reason


def main():
    retriever = _get_retriever()
    faqs_by_id = {}
    for faq in retriever.faqs:
        faqs_by_id[faq["id"]] = faq

    total = 0
    faithful = 0
    number_fallbacks = 0
    failures = []
    for question, expected, faq_id, kind in CASES:
        if kind not in CONFIG_KINDS:
            continue
        faq_answer = faqs_by_id[faq_id]["answer"]
        faq_question = faqs_by_id[faq_id]["question"]
        reply = generate(CONFIG_SYSTEM_PROMPT, build_user_prompt(faq_question, faq_answer, question))
        total += 1
        if not _numbers(reply).issubset(_numbers(faq_answer)):
            number_fallbacks += 1
            continue
        verdict, reason = judge(faq_question, faq_answer, reply)
        if verdict == CONFIG_VERDICT_FAITHFUL:
            faithful += 1
        else:
            failures.append((question, reply, reason))

    print("Rephrase fidelity: " + str(faithful) + "/" + str(total) + " judged faithful")
    print("Caught by the number guard (literal FAQ text used instead): " + str(number_fallbacks))
    print("Unfaithful and not caught by the guard: " + str(len(failures)))
    for question, reply, reason in failures:
        print("")
        print("Question: " + question)
        print("Reply: " + reply)
        print("Reason: " + reason)


main()
