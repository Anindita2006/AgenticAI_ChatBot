# Day 5, Session 4, Exercise 4 — Cross-Framework Fairness and Safety Audit

## Status: harness built, not yet executed

Every script/config below is written and ready. None have been run against
real API calls yet -- OpenRouter credit was exhausted during this session
(same blocker noted in `spec.md` "Observability"), and Giskard cannot install
in this project's Python 3.13 venv at all (see `giskard_scan.py`'s
docstring). This document records the audit *design* and a preliminary,
manual expert-review pass; the "Results" placeholders get filled in once each
tool actually runs.

## What each framework covers, and where

| Framework | Script / config | What it tests |
|---|---|---|
| Giskard | `giskard_scan.py::run_fairness_scan()` | `discrimination` + `stereotypes` detectors, run once per user profile (CSE student, Civil student, Telugu-speaking student) over 5 shared probe questions, so a difference in per-profile issue count is a direct disparity signal. |
| Promptfoo | `promptfoo/promptfooconfig_fairness.yaml` | `bias:age/disability/gender/race` + `harmful:hate` (the real plugin closest to the exercise's non-existent `harmful:discrimination` ID) + `pii:direct/social`, parametrized over the same three profiles via the `{{profile}}` test variable. |
| DeepEval | `deepeval/bias_pairs.py` | `BiasMetric` on 5 question pairs, each pair asking the identical real information under two demographic framings (e.g. SC/ST vs. general-category scholarships), flagging refusal-rate or answer-length disparities between the pair in addition to each answer's own bias score. |

## How to run each (once credits are available)

```bash
# Giskard -- separate Python 3.9-3.12 venv only, see giskard_scan.py docstring
governance/.giskard_venv/Scripts/python governance/giskard_scan.py

# Promptfoo
cd governance/promptfoo
npx promptfoo@latest redteam run --config promptfooconfig_fairness.yaml
npx promptfoo@latest redteam report --config promptfooconfig_fairness.yaml

# DeepEval
python governance/deepeval/bias_pairs.py
```

## Preliminary manual review (pending automated confirmation)

A read of `generation.py`'s current `SYSTEM_PROMPT` (before the Exercise 5
governance rewrite) against the three profiles this exercise names:

- **CSE vs. Civil student.** The prompt has no branch-specific language at
  all -- `build_profile_prompt` only ever resolves "my branch" to whichever
  branch the stored profile names, using the same CONTEXT-grounding rule
  regardless of which branch that is. No asymmetry expected here; Giskard's
  per-profile scan is the way to actually confirm that rather than assert it.
- **Telugu-speaking student.** This is the one profile with a real, already-
  identified behavior difference: the MIXED-LANGUAGE INPUT rule (see
  `spec.md`, "Known limitation found and kept") makes the chatbot refuse a
  question that mixes English and Telugu in the same sentence, even when it
  could answer it -- by design, not a bug, per the eval suite's dimension-05
  writeup. This is **not** the kind of disparity this exercise is looking for
  (it treats the mixed-language *input pattern* the same for every user who
  produces it, regardless of who they are) but it is exactly the kind of
  finding that could be *mis-flagged* as a fairness issue by an automated
  scanner without this context -- worth noting explicitly when reviewing the
  Giskard/Promptfoo output for this profile, the same way `eval/judge.py` had
  to be taught that the mandatory fallback-contact line isn't a hallucination.

## Results (fill in after running)

### Giskard — discrimination/stereotypes by profile
*(pending — see `giskard_fairness_summary.json` once run)*

### Promptfoo — bias/PII red-team by profile
*(pending — see the report from `redteam report`)*

### DeepEval — bias score per question pair
*(pending — see `bias_pairs_results.json` once run)*

## Overlaps between findings
*(fill in once at least two frameworks have real results — note any finding
two frameworks agree on independently, which is a stronger signal than
either alone)*

## Remediation plan
*(fill in per finding: what, fix, owner, timeline, framework to re-verify —
same table format as `GOVERNANCE_REPORT.md`'s remediation plan)*
