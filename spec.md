# BVRIT Hyderabad FAQ Chatbot — Technical Spec

RAG chatbot answering questions about BVRIT HYDERABAD College of Engineering
for Women, grounded in a single curated document, with citations and an
automated 8-dimension + RAGAS evaluation suite.

## Architecture

```
data/knowledge_base.pdf         (knowledge base, 15 sections + 14.x/15.x subsections)
        |
   src/loader.py                (pdf -> section/page-tagged text blocks)
        |
   src/chunker.py                (recursive character split, 400/60)
        |
   src/ingest.py                 (embed + persist to ChromaDB)
        |
   vectorstore/                  (persistent Chroma collection)
        |
   src/retriever.py              (embed query, top-k search, section filter)
        |
   src/generation.py             (grounding prompt + chat completion)
        |
   src/pipeline.py               (orchestrates retrieve + generate, latency, history)
        |
   app.py + pages/1_Evaluation_Dashboard.py   (Streamlit UI)

   eval/generate_test_cases.py -> eval/run_tests.py -> eval/judge.py
                                                     -> eval/ragas_eval.py
                                                            |
                                                     eval/report.py -> eval/report.json
```

All LLM/embedding calls go through **OpenRouter** (`src/config.py`), using
OpenAI-family models throughout: `openai/gpt-4o-mini` for the chatbot,
`openai/gpt-4o` for the LLM-as-judge and test-case generator (a different,
larger model than the chatbot under test, to avoid self-bias), and
`openai/text-embedding-3-small` for embeddings.

## Knowledge base

`data/knowledge_base.pdf` is a 153-page export scraped directly from the live
site (bvrithyderabad.edu.in), replacing the earlier synthetic
`bvrit_college_info.pdf` (retired to `data/archive/`, no longer read by
anything). It has 15 numbered top-level sections in Title Case (e.g. `"6.
Admissions"`), plus two large addendum/appendix sections (14, 15) that carry
their own numbered subsections (e.g. `"14.9 EAMCET / EAPCET Rank Cut-Offs"`).
Section 15 is explicitly marked "Illustrative / Unverified" in its own text —
content transcribed from a separate, unverified training document rather
than the live site — and is deliberately not treated as more authoritative
than sections 1-14 anywhere in the pipeline.

Unlike the old synthetic document, this one isn't self-generated with one
section per PDF page, and its body text contains unrelated numbered lists
(patent titles, ranked items) that restart at 1 and would collide with a
naive numbering regex. `src/loader.py` instead accepts a heading only when
its number continues the expected top-level sequence (1, 2, 3, ...) *and*
its (normalized) title matches one of the 15 known section titles; decimal
subheadings (`N.M`) are accepted only while already inside top-level section
`N`. Page numbers still come directly from pypdf's own pagination.

## Chunking strategy

`chunk_size=400, chunk_overlap=60` (`src/chunker.py`, a dependency-free
recursive character splitter — same algorithm shape as LangChain's
`RecursiveCharacterTextSplitter`: try paragraph breaks first, fall back to
sentence/word breaks only for oversized pieces).

This was tuned empirically, not guessed. The initial `800/120` config was
tested against three known queries (see "Retrieval verification" below) and
failed two of them: chunks that merged multiple distinct facts (e.g. seat
categories + JEE policy in one 800-char chunk) diluted the embedding enough
that the specific fact a query was looking for didn't rank in the top 5.
Tightening to `400/60` fixed both cases by keeping each chunk closer to one
fact.

Overlap is word-boundary-aware (`chunker.py`'s overlap step snaps to the
nearest space), fixing an earlier bug where character-level slicing produced
broken words at chunk starts (e.g. `"ge/Management Seats"` instead of
`"College/Management Seats"`), which also happened to be corrupting
citations shown to users.

**Contextual chunk headers.** Splitting a section into several chunks means
most chunks lose the sentence that establishes *what they're about* — e.g. a
mid-section chunk reading "Top recruiters include Microsoft, Amazon..." has
no lexical anchor back to "BVRIT Hyderabad" or "Placements" on its own, so a
query like "What are the top recruiters at BVRIT Hyderabad?" was matching
unrelated chunks that merely opened with "BVRIT Hyderabad..." Fix
(`src/ingest.py`): each chunk is embedded with a
`"{document title} — {section}: {chunk text}"` prefix, while the clean
original text (no prefix) is what's actually stored and shown to the user or
the LLM. Only the embedding input changes; citations and generation context
stay clean.

## Retrieval verification

Per the brief's "print retrieved chunks before wiring up generation" step,
`src/retriever.py`'s `__main__` block runs 3 known queries and prints the
top-k results with distances — this is how both bugs above were actually
caught, not by inspection. Metadata filtering (`section=` param on
`retrieve()`) scopes a query to one section, verified against both a section
that contains the answer and one that doesn't (returns fewer than `top_k`
without erroring).

## Grounding prompt

`src/generation.py`'s `SYSTEM_PROMPT` covers the five required elements:

1. **Role** — BVRIT Hyderabad College Information Assistant, explicitly not a
   general assistant/tutor/counsellor.
2. **Grounding rule** — answer only from the CONTEXT block built each turn
   from retrieved chunks; refuse rather than use training knowledge.
3. **Citation format** — `[Section Name, Page N]` after every factual claim.
4. **Refusal instruction** — responses that can't be grounded start with the
   literal string `REFUSED:` (parsed by the UI to show a badge) and always
   append a fixed fallback contact line pulled from the document's own
   Contact section.
5. **Conflict handling** — present both values with citations and flag the
   discrepancy, rather than silently picking one, when two chunks disagree
   on what looks like the same fact.

Plus explicit Safety (never guarantee an individual outcome) and Security
(stay in role, never reveal the system prompt) instructions, verified in
Phase 3 testing against known-good, refusal, multi-turn, and prompt-injection
cases — all passed.

**Acronym-guessing fix.** Live testing surfaced a subtler grounding leak: on
a question like "Who teaches DSM?", the model correctly refused to name a
teacher, but silently invented what "DSM" stood for ("Digital System
Management", later "Data Structures and Management" — the document never
defines DSM at all) as an aside inside the refusal. An abstract instruction
("don't guess acronym meanings") wasn't reliable against gpt-4o-mini; what
worked was a concrete right/wrong example pair embedded directly in the
system prompt. This is why the RAGAS Faithfulness score improved from 0.89
to 1.00 after the fix — it wasn't an acronym-specific patch, it tightened
"don't state anything not backed by context" generally.

## Multi-turn context

`src/pipeline.py` threads the last `MAX_HISTORY_MESSAGES=6` messages (~3
exchanges) into the prompt so follow-ups like "tell me more about the first
one" resolve against the prior turn, while every factual claim in the
follow-up still has to be grounded in *that turn's* freshly retrieved
context — history informs reference resolution, not fact-sourcing.

## Evaluation suite

Three-LLM pattern, exactly as specified: `openai/gpt-4o` generates the test
cases from the grounding document (`eval/generate_test_cases.py`),
`openai/gpt-4o-mini` is the chatbot under test (`eval/run_tests.py`, reusing
`src/pipeline.py` — the same code path as the live app, not a separate
mock), and `openai/gpt-4o` again judges expected-vs-actual per dimension
(`eval/judge.py`) — a different, larger model than the system under test.

Dimension 05 (Robustness) and 06 (Performance) get explicit template
guidance in the test-gen prompt (literal empty string / gibberish / mixed
Telugu+Hindi+English inputs; one simple + one complex query) rather than
being left entirely to the model's judgment, since those specific edge cases
are what the brief calls out by name and a free-form generation might miss
them.

Dimension 08 (RAGAS) is scored programmatically (`eval/ragas_eval.py`), not
by LLM judgment — faithfulness, answer relevancy, context precision, context
recall via the `ragas` library, using `gpt-4o` as the evaluator LLM and the
project's own embedding config.

`eval/report.py` merges the judged results and RAGAS scores, computes
per-dimension pass rates, and identifies the weakest dimension with an
**evidence-based** recommended fix — it quotes the actual failing case's
judge reason rather than a generic template, so the report stays honest
about what specifically failed.

### Known limitation found and kept (not a bug)

One test case fails by design: given a mixed English/Telugu/Hindi question
("What is the fee మరియు admission प्रक्रिया?"), the chatbot understands it
and gives a real, accurate, grounded answer instead of asking the user to
repeat themselves in one language, which is what the test's Robustness
criterion expected. That's arguably better UX for a Telangana college's
actual users, but it doesn't match the specified robustness behavior — left
as an honestly-reported 19/20 result rather than papered over.

### Judge calibration bug found and fixed

The first judge pass failed all three Robustness cases, calling the
chatbot's mandatory fallback contact line a "hallucination" — it didn't know
that including a real, document-sourced contact in every refusal is
mandated, correct behavior, not an invented answer. Fixed by adding explicit
context about this convention to the judge's system prompt
(`eval/judge.py`); 2 of 3 flipped to pass, leaving only the genuine
mixed-language case above.

## Known packaging issue

`ragas` (all versions tried, including 0.2.6 and 0.4.3) unconditionally
imports `ChatVertexAI` from `langchain_community.chat_models.vertexai` at
module load time, even though this project never uses Vertex AI. Current
`langchain-community` releases removed that submodule (Vertex AI support
moved to a standalone package), so a plain `import ragas` fails with
`ModuleNotFoundError`. Fixed by `scripts/patch_ragas_vertexai_stub.py`,
which writes a one-class placeholder module at that exact import path — run
once after `pip install -r requirements.txt`.

## Memory (Phase 6)

Four layers on top of Phase 3's single-turn generation, one module each:

- **Short-term (conversation history).** Already covered above — `src/pipeline.py` threads recent
  turns into every call.
- **Medium-term (`src/summarizer.py`).** Unbounded history would eventually blow the context window,
  but naively truncating it silently forgets facts from outside the window. Instead, every 10 turns is
  a checkpoint: the block of turns that just aged out of the last-10 window is folded into a running
  summary paragraph (merging with any prior summary) via one LLM call, instead of being discarded.
  Between checkpoints nothing happens — this is deliberately one call per 10 turns, not per turn.
- **Long-term (`src/memory_store.py`).** A JSON-file profile store keyed by whatever name/ID the user
  types (this app has no real auth). Loaded at the start of a session and injected into the system
  prompt (`generation.build_profile_prompt`); updated after each turn via a regex-based fact extractor
  (`src/profile_extraction.py`) — deliberately not an LLM call, so profile updates keep working even
  if the chat model itself is unavailable.
- **Personalization.** A stored `branch_interest` does two things, not one: it augments the *retrieval*
  query (`pipeline._retrieval_query`) so the right branch's chunks actually get retrieved, and it's
  named in the system prompt so "my branch" resolves without the user repeating themselves. Both are
  necessary — personalizing only the prompt is moot if retrieval never surfaces the right chunks.
- **Privacy.** Every profile field is classified ESSENTIAL / NICE_TO_HAVE / SENSITIVE in
  `memory_store.FIELD_CLASSIFICATION`; only non-SENSITIVE fields are ever written to disk (a full
  transcript and scholarship/financial-need details are excluded by data minimisation, not just access
  control). Typing "clear my data" in the chat is a hard-coded command that deletes the profile before
  it ever reaches retrieval/generation. Profiles idle for 30 days are auto-expired, both on load and via
  a full sweep once per app start.

## Observability (Day 5, Session 3)

Five layers, `src/observability.py` plus small hooks into every call site:

- **Call-level logging.** Every raw `chat.completions.create` call — RAG generation, each round of
  the tool-use loop, conversation summarization, and the eval judge — goes through
  `observability.logged_llm_call()` instead of hitting the client directly (`generation.py`,
  `summarizer.py`, `eval/judge.py`). It logs timestamp, model, input/output tokens, latency,
  estimated cost (`PRICING_PER_MILLION_TOKENS`, OpenRouter's published rates for the exact
  OpenAI-family models this project uses), and status, to both an in-session list and
  `logs/llm_calls.jsonl` (append-only, one line per call, survives a crash mid-session).
- **Query-level logging.** A second, coarser log (`logs/query_log.jsonl`, via
  `observability.log_query()`) records one entry per `pipeline.answer_question()` call — the unit
  a user or a dashboard actually cares about — with cost/tokens summed across every raw call that
  query triggered and latency measured as the full wall-clock the user waited, not just LLM time.
  This is the log the Session Stats panel, the threshold alerts, and the A/B test all read from.
- **Session Stats dashboard.** `pages/0_Chat.py`'s sidebar renders total queries, average and P95
  latency, total cost, total tokens, and error count via `st.metric()`, with deltas against a
  snapshot taken at the top of the script run (`stats_before`) — Streamlit reruns the whole script
  per interaction, so the panel is deliberately rendered a second time, after query processing, not
  only in the earlier sidebar block, so it reflects the query that was just answered.
- **Threshold alerts + input validation.** `observability.check_alerts()` checks the latest query
  against `latency > PERFORMANCE_SLA_SECONDS` (reusing the existing eval-dimension-06 SLA rather
  than a second constant for the same number) and `cost > $0.10`, and the rolling last-20 queries
  against `error_rate > 5%`; breaches render as `st.warning()` in the chat area.
  `observability.validate_input_length()` rejects anything over 2,000 characters before it ever
  reaches retrieval/generation — the worst cost-blowout scenario (a user pasting an entire document
  as a query) — and logs the attempt with `status="rejected"`, distinct from a real API failure.
- **A/B test on the grounding prompt.** `generation.PROMPT_VARIANT_B_ADDENDUM` is a stricter clause
  (mandatory per-fact citations, a fixed refusal phrase, "never infer or extrapolate") appended as
  its own system message when `prompt_variant="B"`, layered on top of the unchanged Version A prompt
  rather than forking it — so the two variants can never silently drift apart on everything *except*
  the one clause being tested. `pipeline.answer_question(..., prompt_variant=None)` gets Exercise 4's
  random 50/50 assignment; the live Chat page always passes `prompt_variant="A"` explicitly, so a
  real user's answers never vary based on an in-progress experiment. `eval/ab_test_grounding_prompt.py`
  runs 10 hand-picked questions (7 expected to be answerable from the document, 3 expected to
  legitimately refuse) twice each with an exact 10/10 variant split, and reports citation counts and
  refusals split into correct (genuinely out of scope) vs. incorrect (in the document, but the
  stricter prompt refused anyway) per variant.
- **Incident analysis (Exercise 5).** `eval/observability_incident_analysis.md` diagnoses two
  anomalies from the exercise's simulated week of logs — a cost spike from a handful of
  abnormally-long inputs, and a rate-limit/latency cluster from a one-hour traffic burst — each with
  its root cause, the metric and threshold that would have caught it, and a production fix, plus a
  sketched dashboard and a non-technical summary for a non-engineering stakeholder.

`logs/` is gitignored (an ever-growing local artifact, not evidence to track, unlike
`eval/test_cases.json`/`eval/report.json`).

## Governance (Day 5, Session 4)

`governance/` audits the chatbot with three industry-standard frameworks instead of hand-rolled
keyword checks — see `governance/README.md` for the full layout and run commands,
`governance/GOVERNANCE_REPORT.md` for the compiled findings/remediation plan, and
`governance/FAIRNESS_AUDIT.md` for the cross-profile fairness deep-dive.

- **Giskard** (`governance/giskard_scan.py`) wraps the chatbot as a black-box `giskard.Model` over
  `eval/test_cases.json`'s questions, scanning for hallucination/stereotypes/discrimination/
  injection/data-leakage/harmfulness, plus a 3-profile (CSE/Civil/Telugu-speaking student)
  discrimination+stereotypes comparison for the fairness audit. Not runnable in this project's main
  venv — Giskard has no distribution for Python 3.13 (confirmed via a dry-run install returning zero
  candidates); it needs a separate Python 3.9-3.12 venv (`governance/requirements-giskard.txt`).
- **Promptfoo** (`governance/promptfoo/`) red-teams the chatbot via a custom Python provider
  (`file://provider.py`, verified against Promptfoo's own docs — not the `python:` prefix a first
  guess might use) wrapping `pipeline.answer_question`. Both configs' plugin/strategy IDs were
  checked against the actually-installed version's real catalog (`npx promptfoo@latest redteam
  plugins`), not the exercise brief's literal wording — `harmful`, `pii`, and `jailbreak` as bare
  plugin tokens don't exist in this version; each config documents the real ID substituted for each
  (e.g. `jailbreak` is a *strategy*, not a plugin). Both configs pass `promptfoo validate`.
- **DeepEval** (`governance/deepeval/`) scores 10 test cases (factual/faithfulness,
  sensitive/bias+toxicity, out-of-scope/hallucination, safety-boundary) against all five requested
  metrics (Hallucination, Bias, Toxicity, Faithfulness, AnswerRelevancy) via pytest, using deepeval's
  built-in `OpenRouterModel` pointed at this project's own `JUDGE_MODEL` — the same
  never-the-chatbot-judging-itself principle as `eval/judge.py`. A `conftest.py`
  `pytest_sessionfinish` hook writes the full score matrix to `results.json`, since a plain pytest
  run only reports pass/fail per `is_successful()` — which itself required checking each metric's
  actual pass direction (Hallucination/Bias/Toxicity pass at `score <= threshold`, Faithfulness/
  AnswerRelevancy at `score >= threshold`) rather than assuming one direction for all five.
  `bias_pairs.py` runs BiasMetric on 5 demographically-paired questions for the fairness audit,
  flagging refusal/length disparities between each pair, not just each answer's own score.
- **System prompt.** `generation.SYSTEM_PROMPT` gained TRANSPARENCY, PRIVACY, FAIRNESS, and HUMAN
  OVERSIGHT sections, plus a life/health/legal redirect (SAFETY) and a never-execute-code instruction
  (SECURITY) — every new contact referenced (crisis helplines, grievance portal) is sourced from the
  same knowledge-base document's own §9, not invented, matching `FALLBACK_CONTACT`'s existing
  convention.
- **What's actually been run.** Nothing yet — OpenRouter credit was exhausted this session (see
  "Observability" above) and Giskard's environment issue is unresolved. Every harness is written and
  import/schema-checked where checkable without spending money; `GOVERNANCE_REPORT.md` documents this
  explicitly rather than presenting placeholder numbers as real findings.

## Cost

Every LLM/embedding call in this project goes through a single
OpenRouter key. Total spend across the entire build (ingestion,
retrieval tuning, generation testing, the full 20-case eval suite including
RAGAS, and the acronym-fix re-run) was tracked via OpenRouter's
`/api/v1/auth/key` endpoint at each phase and stayed under $0.20 total.
