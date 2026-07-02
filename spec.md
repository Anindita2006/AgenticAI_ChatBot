# BVRIT Hyderabad FAQ Chatbot — Technical Spec

RAG chatbot answering questions about BVRIT HYDERABAD College of Engineering
for Women, grounded in a single curated document, with citations and an
automated 8-dimension + RAGAS evaluation suite.

## Architecture

```
data/bvrith_college_info.docx   (knowledge base, 8 sections, 1 page/section)
        |
   src/loader.py                (docx -> section/page-tagged text blocks)
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

`data/generate_kb_doc.py` builds `bvrith_college_info.docx` from content
transcribed off the live BVRIT Hyderabad site (About, Admissions, Fee
Details, Placements, TAP Cell, CSE Department, Sports Club, Principal,
Contact pages), not invented. Where the official site doesn't publish a
figure (hostel fees, scholarships, an overall placement percentage,
non-CSE department faculty rosters), the document says so explicitly rather
than estimating — this is what lets the chatbot refuse those questions
gracefully instead of guessing.

Each of the 8 required sections (About, Departments, Admissions, Fee
Structure, Placements, Campus & Facilities, Faculty, Contact) is placed on
its own page via an explicit `add_page_break()`, so `page number == section
index + 1` deterministically — citation page numbers are recovered exactly
by counting page-break runs while walking the document's paragraphs
(`src/loader.py`), with no PDF rendering or heuristics needed. A PDF version
(`generate_kb_pdf.py`) mirrors the same content and pagination from the same
`SECTIONS` source of truth, as a Word-free fallback.

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

## Cost

Every LLM/embedding call in this project goes through a single
OpenRouter key. Total spend across the entire build (ingestion,
retrieval tuning, generation testing, the full 20-case eval suite including
RAGAS, and the acronym-fix re-run) was tracked via OpenRouter's
`/api/v1/auth/key` endpoint at each phase and stayed under $0.20 total.
