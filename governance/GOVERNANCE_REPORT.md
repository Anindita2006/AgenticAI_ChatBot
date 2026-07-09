# BVRIT Hyderabad FAQ Chatbot — Governance Report

Day 5, Session 4, Exercise 5. Compiles Exercises 1–4; see `FAIRNESS_AUDIT.md`
for the fuller Exercise 4 write-up this report's Fairness section summarizes.

## Status note (read before the rest of this report)

Two blockers prevented the scans/red-team/eval runs this report would
normally cite numbers from:

1. **OpenRouter credit was exhausted** partway through this session (see
   `spec.md` "Observability" for the same issue). Promptfoo red-teaming (50+
   real chatbot calls) and DeepEval metric scoring (10 cases x 5 LLM-judged
   metrics) both need a funded key.
2. **Giskard has no distribution for Python 3.13**, this project's
   interpreter (confirmed via a failed `pip install giskard` dry-run) — it
   needs a separate Python 3.9–3.12 environment (see `giskard_scan.py`'s
   docstring for setup).

Every harness (`giskard_scan.py`, `promptfoo/`, `deepeval/`) is written,
schema-validated where checkable (`promptfoo validate` passed on both
configs), and ready to run. This report's scan/red-team/metric sections are
therefore templates with the exact commands to fill them in, not fabricated
numbers — and the Remediation Plan below is a **manual expert-review pass**
against the current `SYSTEM_PROMPT`, marked as such, pending automated
confirmation once credit is available.

## Executive summary (for the dean)

The BVRIT chatbot answers student and parent questions about admissions,
fees, departments, and campus life from one curated document, and refuses
anything it can't ground in that document rather than guessing. This session
added a formal governance layer on top of it: the system prompt now
explicitly discloses that it's an AI (not staff), states plainly what
personal data it stores and how to delete it, redirects any life/health/legal
question to the college's real counselling and helpline contacts instead of
attempting to answer, and never compares BVRIT against other colleges or
lets one department appear favored over another. Three industry-standard
audit tools (Giskard, Promptfoo, DeepEval) are wired up to continuously
verify these commitments going forward; two of the three are blocked from
actually running today by an exhausted API budget and one by a Python
version mismatch, both are fixable, and this report tells you exactly what
to do once they are.

## System description

- **What it does.** A RAG (retrieval-augmented generation) FAQ chatbot for
  BVRIT Hyderabad. Answers are grounded in one curated PDF knowledge-base
  document (10 sections: about, departments, admissions, fees, placements,
  facilities, student support, contact); anything not in that document gets
  a refusal with a real fallback contact, never a guess.
- **Models used** (all via OpenRouter, see `src/config.py`): `openai/gpt-4o-mini`
  for chat/generation, `openai/gpt-4o` as the separate judge model for
  evaluation and governance scoring (never the same model judging itself),
  `openai/text-embedding-3-small` for retrieval embeddings.
- **Data stored.** Per-user profile (`src/memory_store.py`), keyed by a
  self-typed name/ID (no real authentication): name, stated branch of
  interest, language/detail-level preference. Explicitly never stored: full
  conversation transcripts, scholarship/financial-need details (see
  `FIELD_CLASSIFICATION` in `memory_store.py`). Profiles auto-expire after 30
  days of inactivity; a user can delete theirs anytime by typing "clear my
  data". Separately, `logs/` (gitignored) holds operational LLM-call and
  query logs (timestamps, token counts, cost, latency) — no user-identifying
  data beyond the question text itself.

## Risk classification

**EU AI Act.** Not a high-risk system under Annex III: Annex III's education
category covers systems used *to make or materially influence* admission,
assessment, or exam-proctoring decisions — this chatbot has no decision
authority over any of those; it answers informational questions about a
process, and every admission/placement decision is made by humans through
the college's normal process regardless of what the chatbot said. It
classifies as **limited risk**, triggering Article 50's transparency
obligation (users must be told they're interacting with an AI) — now
explicitly encoded in the system prompt's TRANSPARENCY section. (Caveat: the
Act is EU-territorial; it applies here only to the extent EU-based users
interact with the system. Included because the exercise asks for the
classification as a governance-maturity exercise regardless of actual
jurisdictional reach.)

**India's DPDP Act, 2023.** Squarely applicable — an Indian data fiduciary
processing personal data of Indian data principals. Mapping obligations to
what's actually implemented:

| DPDP principle | Implementation | Gap |
|---|---|---|
| Purpose limitation | Profile fields exist only to personalize answers (branch/language/detail-level) | none identified |
| Data minimisation | `FIELD_CLASSIFICATION` excludes transcripts and financial/scholarship details by design, not just access control | none identified |
| Storage limitation | 30-day auto-expiry, swept on every app start (`memory_store.purge_expired`) | none identified |
| Right to erasure | "clear my data" chat command + sidebar button, both delete immediately | none identified |
| Notice/consent | `PRIVACY_NOTICE` shown as an `st.info` banner on first message and inside a sidebar expander | **Gap:** shown, but not a blocking consent step — a user could start chatting (and have a profile saved once they type a name/ID) without necessarily reading it. See remediation. |
| Grievance/DPO contact | General student grievance path added this session (`GRIEVANCE_CONTACT`) | **Gap:** that's a *student affairs* grievance channel, not a *data-protection*-specific one; DPDP expects a discoverable way to raise a data-handling complaint specifically. See remediation. |

## Giskard scan results

**Not executed** (Python 3.13 incompatibility, see Status note). Harness:
`giskard_scan.py` (`run_scan()` for the general vulnerability scan over
`eval/test_cases.json`'s 20 questions across hallucination/stereotypes/
discrimination/injection/data-leakage/harmfulness; `run_fairness_scan()` for
the 3-profile discrimination/stereotypes comparison, Exercise 4). Run with:

```bash
governance/.giskard_venv/Scripts/python governance/giskard_scan.py
```

*True positive / false positive log: pending — fill in from `giskard_report.html`
after running.*

## Promptfoo red-team results

**Not executed** (credit exhausted). Harness: `promptfoo/promptfooconfig.yaml`
(main red-team: hijacking, hallucination, overreliance, PII x4, curated
harmful:* set, jailbreak strategies — see the config's own comments for why
the exercise's literal plugin names needed mapping to real IDs) and
`promptfoo/promptfooconfig_fairness.yaml` (Exercise 4: bias:* x4 + harmful:hate
+ PII, across 3 user-profile framings). Both pass `promptfoo validate`. Run
with:

```bash
cd governance/promptfoo
npx promptfoo@latest redteam run --config promptfooconfig.yaml
npx promptfoo@latest redteam report --config promptfooconfig.yaml
```

*Critical/Medium/Low severity log: pending — fill in from the report after running.*

## DeepEval metric scores

**Not executed** (credit exhausted). Harness: `deepeval/test_governance.py`
(10 cases x 5 metrics — Hallucination, Bias, Toxicity, Faithfulness,
AnswerRelevancy — every metric run against every case so the weakest metric
and worst case are both answerable from one matrix) and
`deepeval/bias_pairs.py` (Exercise 4: BiasMetric on 5 demographic-framing
question pairs). Run with:

```bash
pytest governance/deepeval/test_governance.py -v
python governance/deepeval/bias_pairs.py
```

*Per-metric / per-case scores, weakest metric, worst case: pending — both
scripts print and write a full score matrix (`results.json`,
`bias_pairs_results.json`) once run.*

## Fairness summary (full detail in FAIRNESS_AUDIT.md)

Manual review ahead of automated confirmation: no branch-specific asymmetry
expected in the current prompt (branch resolution is generic, see
`build_profile_prompt`). The one known, deliberate behavior difference is the
mixed-language refusal rule for Telugu/Hindi-mixed input (documented in
`spec.md`'s eval-suite section as an intentional, not-a-bug limitation) — a
scanner may flag this against the Telugu-speaking-student profile and it
needs to be interpreted with that context in mind rather than treated as a
raw finding, the same way `eval/judge.py` had to be taught the mandatory
refusal contact line isn't a hallucination.

## Remediation plan

| # | Finding | Fix | Owner | Timeline | Re-verify with |
|---|---|---|---|---|---|
| 1 | Privacy notice is informational, not a blocking consent step | Add a one-time consent checkbox/modal before the first profile-saving interaction, distinct from the existing passive `st.info` banner | App owner | Next sprint | Manual UX review |
| 2 | No DPDP-specific grievance/DPO contact, only general student grievance channel | Publish a named Data Protection contact (email) in the privacy notice and `GRIEVANCE_CONTACT`, distinct from the Dean (Student Affairs) student-affairs channel | App owner + college compliance office | Next sprint | Manual review |
| 3 | Giskard scan never executed in this environment | Stand up the separate Python 3.11/3.12 venv per `giskard_scan.py`'s docstring | App owner | Before first production deploy | Giskard (`run_scan`, `run_fairness_scan`) |
| 4 | Promptfoo red-team never executed | Top up OpenRouter credit, run both configs | App owner | Before first production deploy | Promptfoo (`redteam run`) |
| 5 | DeepEval metrics never executed, no quantitative faithfulness/bias/toxicity baseline yet | Top up OpenRouter credit, run `test_governance.py` + `bias_pairs.py` | App owner | Before first production deploy | DeepEval (`pytest`) |
| 6 | (Pending scan results) Any Critical Promptfoo finding | Fix in `SYSTEM_PROMPT` or `src/tools.py`, re-run the same config | App owner | Before deploy, per finding | Promptfoo |
| 7 | (Pending scan results) Any Giskard true positive | Fix in `SYSTEM_PROMPT`, re-run `giskard_scan.py` | App owner | Before deploy, per finding | Giskard |

## Before/after scores

Not available yet — the system prompt was rewritten *once*, directly to its
governance-encoded form, before any of the three frameworks got to run a
"before" pass (blocked per the Status note above). Once credit/environment
issues are resolved: check out the commit before this session's system-prompt
change, run all three frameworks, restore this session's version, run them
again, and record both sets of numbers here.

## Peer review — would I approve this for deployment?

**Not yet, conditionally.** The system prompt itself is in good shape — it
already encodes every governance requirement the exercise names as a
specific, testable instruction (transparency, privacy/DPDP, safety redirects
to real crisis contacts, fairness, security, human oversight/escalation) —
but "the prompt says the right things" and "three independent adversarial
tools confirm it holds up under attack" are different claims, and this report
can only make the first one right now. I'd approve deployment once items 3–5
in the remediation plan (actually running all three frameworks) come back
clean, or with only Low-severity findings — not before.
