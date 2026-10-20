import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "tests"))

import numpy as np

import faq_agent
from faq_agent import answer_faq, _get_retriever, CONFIG_ANSWER_ROUTES
from testset import CASES

CONFIG_THRESHOLDS = [0.78, 0.80, 0.82, 0.84, 0.85, 0.86, 0.87, 0.88, 0.89, 0.90, 0.91, 0.92]
CONFIG_TOP_K_VALUES = [1, 3]
CONFIG_MARGINS = [0.0, 0.01, 0.02, 0.03]


def retrieval_hit_rates(rows):
    for k in CONFIG_TOP_K_VALUES:
        hits = 0
        total = 0
        for row in rows:
            if row["faq_id"] is None:
                continue
            total += 1
            ids = []
            for result in row["results"][:k]:
                ids.append(result["faq"]["id"])
            if row["faq_id"] in ids:
                hits += 1
        print("Retrieval hit@" + str(k) + ": " + str(hits) + "/" + str(total) + " = " + format(hits / total, ".2f"))


def decide(row, threshold, margin):
    best = row["results"][0]
    second = row["results"][1]
    if best["score"] < threshold:
        return None
    if best["score"] - second["score"] < margin:
        return None
    if best["faq"]["route"] not in CONFIG_ANSWER_ROUTES:
        return None
    return best["faq"]["id"]


def threshold_table(rows, margin):
    print("margin >= " + str(margin))
    print("threshold | wrongful answers | wrongful handoffs | correct answers")
    covered = 0
    not_covered = 0
    for row in rows:
        if row["expected"] == "answer":
            covered += 1
        else:
            not_covered += 1
    for threshold in CONFIG_THRESHOLDS:
        wrong_answers = 0
        wrong_handoffs = 0
        correct = 0
        for row in rows:
            predicted = decide(row, threshold, margin)
            if row["expected"] == "handoff" and predicted is not None:
                wrong_answers += 1
            if row["expected"] == "answer" and predicted is None:
                wrong_handoffs += 1
            if row["expected"] == "answer" and predicted is not None and predicted != row["faq_id"]:
                wrong_answers += 1
            if row["expected"] == "answer" and predicted == row["faq_id"]:
                correct += 1
        print(
            format(threshold, ".2f") + "      | "
            + str(wrong_answers) + "/" + str(len(rows)) + " (" + str(not_covered) + " should hand off) | "
            + str(wrong_handoffs) + "/" + str(covered) + " | " + str(correct) + "/" + str(covered)
        )


def latency():
    times = []
    for case in CASES[:20]:
        start = time.perf_counter()
        answer_faq(case[0], [])
        times.append(time.perf_counter() - start)
    print("Latency median " + format(float(np.median(times)) * 1000, ".0f") + " ms, max " + format(max(times) * 1000, ".0f") + " ms")


def main():
    faq_agent.CONFIG_LOG_ENABLED = False
    retriever = _get_retriever()
    rows = []
    for question, expected, faq_id, kind in CASES:
        rows.append(
            {"question": question, "expected": expected, "faq_id": faq_id, "kind": kind, "results": retriever.search(question, 3)}
        )
    retrieval_hit_rates(rows)
    for margin in CONFIG_MARGINS:
        threshold_table(rows, margin)
    print("Score ranges by kind (best score):")
    for kind in ["paraphrase", "banco", "other_route", "uncovered"]:
        scores = []
        for row in rows:
            if row["kind"] == kind:
                scores.append(row["results"][0]["score"])
        print(kind + ": min " + format(min(scores), ".3f") + " median " + format(float(np.median(scores)), ".3f") + " max " + format(max(scores), ".3f"))
    latency()


main()
