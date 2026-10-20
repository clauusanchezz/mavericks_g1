import os
import sqlite3

from logging_store import CONFIG_DB_PATH

CONFIG_TOP_N = 10
CONFIG_EXAMPLES_PER_GAP = 3
CONFIG_MIN_ANSWERS_FOR_WEAK = 2


def _rows(connection, query, params=()):
    return connection.execute(query, params).fetchall()


def top_questions(connection):
    print("Top questions")
    rows = _rows(
        connection,
        "SELECT LOWER(TRIM(question)), COUNT(*) AS n FROM interactions GROUP BY LOWER(TRIM(question)) "
        "ORDER BY n DESC LIMIT ?",
        (CONFIG_TOP_N,),
    )
    for question, count in rows:
        print(str(count) + "  " + question)


def faq_gaps(connection):
    """Handoffs where no FAQ covered the question, grouped by the nearest FAQ as a rough topic."""
    print("FAQ gaps (unanswered questions grouped by nearest FAQ)")
    rows = _rows(
        connection,
        "SELECT SUBSTR(retrieved_ids, 1, INSTR(retrieved_ids || ',', ',') - 1) AS nearest, COUNT(*) AS n "
        "FROM interactions WHERE status = 'handoff' AND source_faq_id IS NULL "
        "GROUP BY nearest ORDER BY n DESC LIMIT ?",
        (CONFIG_TOP_N,),
    )
    for nearest, count in rows:
        print(str(count) + "  nearest " + nearest)
        examples = _rows(
            connection,
            "SELECT question FROM interactions WHERE status = 'handoff' AND source_faq_id IS NULL "
            "AND SUBSTR(retrieved_ids, 1, INSTR(retrieved_ids || ',', ',') - 1) = ? ORDER BY id DESC LIMIT ?",
            (nearest, CONFIG_EXAMPLES_PER_GAP),
        )
        for example in examples:
            print("      " + example[0])


def handoffs_by_route(connection):
    print("Handoffs by matched route")
    rows = _rows(
        connection,
        "SELECT best_route, COUNT(*) FROM interactions WHERE status = 'handoff' AND source_faq_id IS NOT NULL "
        "GROUP BY best_route ORDER BY COUNT(*) DESC",
    )
    for route, count in rows:
        print(str(count) + "  " + route)


def weak_faqs(connection):
    """FAQs that were answered but often led to a follow-up question or an 'it did not help' reply."""
    print("Weak FAQs (follow-ups and unsolved replies per answer)")
    answered = _rows(
        connection,
        "SELECT source_faq_id, COUNT(*), SUM(CASE WHEN solved = 0 THEN 1 ELSE 0 END) FROM interactions "
        "WHERE status = 'answered' GROUP BY source_faq_id",
    )
    followups = {}
    for faq_id, count in _rows(
        connection, "SELECT followup_of, COUNT(*) FROM interactions WHERE followup_of IS NOT NULL GROUP BY followup_of"
    ):
        followups[faq_id] = count

    scored = []
    for faq_id, total, unsolved in answered:
        if total < CONFIG_MIN_ANSWERS_FOR_WEAK:
            continue
        follow = followups.get(faq_id, 0)
        scored.append(((follow + unsolved) / total, faq_id, total, follow, unsolved))
    scored.sort(reverse=True)
    for rate, faq_id, total, follow, unsolved in scored[:CONFIG_TOP_N]:
        print(
            faq_id + "  answered " + str(total) + ", follow-ups " + str(follow)
            + ", unsolved " + str(unsolved) + ", rate " + format(rate, ".2f")
        )


def main():
    if not os.path.exists(CONFIG_DB_PATH):
        print("No interactions logged yet.")
        return
    connection = sqlite3.connect(CONFIG_DB_PATH)
    total = _rows(connection, "SELECT COUNT(*) FROM interactions")[0][0]
    print("Interactions logged: " + str(total))
    print("")
    top_questions(connection)
    print("")
    faq_gaps(connection)
    print("")
    handoffs_by_route(connection)
    print("")
    weak_faqs(connection)
    connection.close()


main()
