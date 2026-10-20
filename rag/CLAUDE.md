# Accenture Mavericks, Challenge 1: FAQ RAG agent (my part only)

## Context

Team challenge: a contact center system for a bank. A router classifies each call by the reason the customer states at the start, then sends it to one of two specialists. Teammates own the router and the mortgage simulation agent. My scope is ONLY the customer service assistant that answers frequently asked questions and general inquiries using RAG over the provided FAQ dataset.

Do not build the router, the mortgage agent, speech-to-text, or text-to-speech. Expose a clean interface so teammates can plug this agent in.

Business goal: answer simple queries correctly and cheaply, never invent information, and hand off to a human operator when the FAQs do not cover the question. Every handoff also reveals a gap in the FAQs.

## Why RAG, via API (decided)

- Answers must come only from approved bank content, be traceable to a source FAQ, and be updatable by editing text, without retraining.
- No model training. Use a pretrained embedding model (multilingual, the FAQs are probably in Spanish) and an LLM through an API for generation.
- Ask me before choosing a provider or using paid APIs. Keep the provider behind a small wrapper so it can be swapped.

## Flow

```
Customer question (text, plus optional short conversation history)
  -> retrieve the top-k most similar FAQs
  -> is there a reliable answer? (confidence threshold)
       yes -> answer in a few short sentences, cite the source FAQ id,
              then ask "did that solve it?"
       no  -> ask ONE clarifying question at most
              still no -> hand off to a human operator
                          with a short summary of the conversation
                          and log the question as an FAQ gap
```

Rules:
- Answers are for a phone call: short, clear, no long paragraphs.
- Never invent policy, fees, or deadlines. If the retrieved FAQ does not support the answer, do not answer.
- Use one FAQ per answer when possible. Do not mix FAQs in ways that can contradict each other.
- Beware near-miss questions that look like an FAQ but differ in a key detail (for example a different product). The threshold plus handoff is the mitigation.
- Do not store or forward personal data in logs. Mask obvious personal identifiers before logging.

## Interface contract (what teammates call)

A single function in `src/faq_agent.py`:

```
answer_faq(question: str, history: list) -> dict
```

Returned dict:
- `status`: one of `answered`, `needs_clarification`, `handoff`
- `answer`: text to say to the customer (empty only for handoff if the system prompt of the caller plays a fixed phrase)
- `source_faq_id`: id of the FAQ used, or `None`
- `confidence`: float between 0 and 1
- `handoff_summary`: short summary for the human operator, or `None`

Keep this contract stable. If I need to change it, tell me first.

## Data

Provided: an FAQ dataset and validation transcripts (the transcripts are mainly for the router, but use them as a source of realistic questions). First step is to inspect the data and report format, size, language, and quirks. Do not assume the structure.

## Evaluation (build my own, the router team measures routing)

- Build a small test set: real questions from the transcripts plus questions written in different words for each FAQ, plus questions that are deliberately NOT covered.
- Retrieval: hit rate of the correct FAQ in the top-k.
- Answer quality: LLM-as-judge on faithfulness to the source FAQ.
- Safety: rate of invented answers (target zero), rate of correct handoffs on uncovered questions, rate of wrongful handoffs on covered ones.
- Threshold tuning: show a table of threshold vs wrongful answers vs wrongful handoffs, and recommend a value with the trade-off explained in business terms.
- Latency to the first answer.

## Insights output (feeds the dashboard)

Log every interaction to a simple store (SQLite or JSONL): timestamp, question, retrieved FAQ ids, confidence, status, whether the customer confirmed it was solved. Provide a small script that reports: top questions, FAQ gaps (handoffs grouped by topic), and FAQs that trigger many follow-up questions (likely poorly written).

## Code style rules (follow strictly)

- All code, comments, and documentation in English.
- No argparse or CLI interfaces unless explicitly requested.
- CONFIG variables at the top of each file as plain assignments (model names, top-k, threshold, paths).
- No `====` separator comments.
- No list comprehensions and no inline `if`: use explicit `for` and `if` blocks.
- Any matplotlib figure must call `plt.show()` before `plt.close()`.
- No em dashes in any written output.

## Suggested structure

```
data/                  provided FAQ dataset and transcripts
src/llm_client.py      thin wrapper around the generation API
src/embeddings.py      embedding model wrapper
src/retriever.py       index build and top-k search
src/faq_agent.py       answer_faq and the decision logic
src/handoff.py         human operator summary
src/logging_store.py   interactions and FAQ gaps
src/evaluate.py        runs my test set and the threshold table
src/insights.py        top questions, gaps, weak FAQs
demo_faq.py            small standalone demo (text chat)
tests/
```

## Working order

1. Inspect the data, report findings, propose how to chunk and index the FAQs.
2. Retriever and a first version of `answer_faq` with a simple threshold.
3. Test set and evaluation, then tune the threshold.
4. Clarifying question and human handoff with summary.
5. Logging and insights.
6. Standalone text demo, then help the team integrate with the router.

Ask before making choices that are hard to undo.

## Project status (updated 2026-10-20)

### Decisions made by the user
- Scope: this agent answers FAQs with `RUTA` of `FAQ` or `BANCO` (31 of 50). `URGENTE`, `PERSONA` and unknown questions go to a human operator. The router decides before this agent whether a call goes to the mortgage simulation agent, so this agent knows nothing about that destination. A `SIMULAR` match here means the router missed it and is handed to a human with a note saying so.
- Everything free or very cheap, this is a hackathon MVP. Generation stays on Claude `claude-haiku-5-5` (effort `low`); Groq was considered and dropped.
- Embeddings: local `intfloat/multilingual-e5-small`. No vector database: 50 FAQs live in an in-memory numpy matrix.
- Conversational answers are wanted, so the LLM rephrases the FAQ text instead of returning it literally.
- Logging in SQLite (`data/interactions.db`, git-ignored data).
- API key lives in `rag/.env` as `ANTHROPIC_API_KEY` (git-ignored).

### Data findings
- `data/FAQs_Asistente_Bancario_Mavericks.txt`: 50 FAQs (`FAQ_01` to `FAQ_50`), Spanish (Spain), blocks separated by `---`.
- Fields: `ID`, `AMBITO`, `FECHA_DE_REVISION`, `PREGUNTA`, `RESPUESTA`, `RUTA`, `NOTA_INTERNA_PARA_EL_EQUIPO`, `FUENTES`, and `SUPUESTOS_DEL_EJEMPLO` in 5 FAQs.
- `RUTA` counts: FAQ 18, BANCO 13, SIMULAR 10, PERSONA 5, URGENTE 4. Answers are 38 to 64 words.
- No call transcripts were provided. The test set uses questions written by me.
- Quirks: SIMULAR FAQs contain hypothetical calculations; sources `[P1]` and `[C1]` are demo design or own calculations; FAQ_13 and FAQ_15 only make sense with conversation context; `NOTA_INTERNA` is a behavior rule, never read it to the customer. Several BANCO notes say the prototype must not perform the action (close an account, issue a certificate, quote rates).

### What is built
- `src/embeddings.py`, `src/retriever.py`, `src/llm_client.py` (provider isolated here).
- `src/faq_agent.py`: `answer_faq(question, history)` with the contract above, threshold `CONFIG_THRESHOLD = 0.87`. Answers when the best FAQ scores above the threshold and its route is in `CONFIG_ANSWER_ROUTES`; otherwise handoff (matched route not answerable) or one clarification and then handoff. The question is searched alone first. Only a short question (under 6 words) that scores below the threshold AND looks like a follow-up (starts with y, pero, entonces, or contains eso, esto, ese...) is retried with the previous customer message, and the context result is used only if it scores higher. Without this, an unrelated short question such as "he perdido mi tarjeta" got glued to a previous euribor question and was answered with the euribor FAQ (found on 2026-10-20 in the web demo). Every call is logged unless `CONFIG_LOG_ENABLED = False`.
- Rephrase safety: the LLM only rephrases. The literal FAQ text is returned if the API fails, if the reply has a number not in the FAQ, or if it mentions "FAQ". `CONFIG_USE_LLM = False` disables the LLM.
- `src/handoff.py`: operator summary (destination, reason, last question, previous customer messages, nearest FAQ, whether a clarification was already used). Text is in Spanish.
- `src/logging_store.py`: SQLite log (timestamp, masked question, retrieved ids, route, confidence, status, source FAQ, follow-up of, solved). Masks IBAN, email, DNI/NIE, card, phone and long numbers. Names cannot be masked. `mark_solved(solved)` must be called by the integrator when the customer answers "did that solve it?".
- `src/insights.py`: top questions, FAQ gaps (unknown handoffs grouped by nearest FAQ), handoffs by route, weak FAQs (follow-ups plus unsolved replies per answer).
- `src/judge_fidelity.py`: LLM-as-judge for rephrase fidelity. It measures the raw LLM output, before the guards in `_rephrase`.
- `src/chat_api.py`: request validation and history cleaning for the web demo (`handle_chat`, `handle_solved`).
- `demo_faq.py` and `web/index.html`: web chat demo on `http://127.0.0.1:8000`, standard library `http.server` only. Run with `.venv/bin/python demo_faq.py`. White page with one large orb as the assistant's presence (breathes at rest, waveform bars and faster swirl while thinking, pulse while the answer appears, shrinks to the top once the chat starts, gloss follows the pointer). Word-by-word reveal, source chip, "did that solve it?" buttons that call `mark_solved`, and a handoff card with a collapsible operator note. Optional read-aloud button (browser `speechSynthesis`, off by default, picks an `es` voice, reads the answer without the "did that solve it?" sentence; disabled when the browser has no Spanish voice; demo only, the team owns the real text-to-speech). No avatar or emoji next to the name or messages (the user disliked it). The embedding model is loaded at server start so the first answer is not slow.
- `tests/`: 47 `unittest` tests (parser, retriever, `answer_faq` contract, rephrase guards, PII masking, handoff summary, logging store, chat API). Run with `.venv/bin/python -m unittest discover -s tests -p "test_*.py"`. pytest is not installed.
- `src/evaluate.py` and `tests/testset.py` (82 cases: paraphrase, banco, other_route, uncovered).

### History convention for integrators
`history` is a list of turns: `{"role": "user", "content": ...}` and for the assistant the returned dict fields `{"role": "assistant", "content": answer, "status": ..., "source_faq_id": ...}`. `status` is how the agent knows a clarification was already used, and `status` plus `source_faq_id` is how a follow-up question is attributed to a FAQ in the insights.

### Fixes found by using the demo (2026-10-20)
- Truncated answers: Haiku 5.5 thinks by default and the thinking tokens counted against `CONFIG_MAX_TOKENS = 400`, so about 5 of 12 calls were cut mid-sentence (or empty). `llm_client.generate` now sends `thinking={"type": "disabled"}` (allowed on Haiku 5.5 at effort `low`) and returns an empty string when `stop_reason` is not `end_turn`, which makes `_rephrase` fall back to the literal FAQ text. Earlier fidelity numbers may have been inflated by truncated answers.
- Over-general answers: the LLM now receives the FAQ question as well as its answer (`build_user_prompt`), and the prompt tells it to name the concrete case when the customer's question is more general ("En una hipoteca variable..."). Example: "Como funcionan las hipotecas" retrieves FAQ_07 (variable rate) and used to be answered as if it applied to every mortgage.
- Short follow-up detection (see Flow notes above) and the `llm_client` truncation guard have tests.

### Measured results
- Retrieval hit@1 95% (59/62), hit@3 97% (60/62). Embedding search about 9 ms; answer with LLM about 1 to 1.5 s.
- Score ranges overlap (paraphrase 0.81 to 0.94, banco 0.87 to 0.92, other_route 0.83 to 0.94, uncovered 0.77 to 0.90), so no threshold separates cleanly. At 0.87: 3 wrongful answers out of 34 that should hand off, 9 wrongful handoffs out of 48 that should be answered. Threshold was tuned on the same set that measures it, and the questions are synthetic.
- Rephrase fidelity (judge on 48 covered questions, 3 runs on 2026-10-20 after the fixes below): 47, 45 and 46 faithful (mean 96%, range 94 to 98%). No invented numbers. Remaining flags are mostly nitpicks (the judge dislikes expanding the FEIN acronym or omitting a related detail). One real nuance error seen: "con carácter general" attached to a rule the FAQ limits to Ley 5/2019. The judge measures the raw LLM output, before the guards in `_rephrase`, and is noisy between runs.

### Open items and next steps
1. Get the user's feedback on the new front end (orb redesign done 2026-10-20).
2. Ask the team: whether URGENTE FAQs should give their safe text before handing off, and whether the router already diverts PERSONA and URGENTE.
3. Optional: literal answers (no rephrase) for sensitive FAQs such as FAQ_42, FAQ_46, FAQ_47.
4. `mark_solved` updates the latest answered interaction, not a specific call. Fine for one call at a time; a session id would fix it but changes the interface.
5. Integration with the router team: they call `answer_faq` and follow the history convention above.
6. Get real transcripts if they exist and rerun `src/evaluate.py` and `src/judge_fidelity.py` with them.
