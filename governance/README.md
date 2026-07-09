# Governance Audit (Day 5, Session 4)

Audits the BVRIT chatbot with three industry-standard frameworks instead of
hand-rolled keyword checks. See `GOVERNANCE_REPORT.md` for the compiled
findings/remediation plan and `FAIRNESS_AUDIT.md` for the cross-framework
fairness deep-dive (Exercise 4).

## Known blockers (read first)

1. **Giskard doesn't install in this project's main venv.** `pip install
   giskard` resolves zero candidate versions under Python 3.13 (this
   project's interpreter) — Giskard's latest release caps at <3.13. Run
   `giskard_scan.py` from a *separate* Python 3.9–3.12 venv; see that file's
   docstring and `requirements-giskard.txt` for setup. Do not touch the
   project's main `.venv` to work around this.
2. **Every script here makes real, billed LLM calls** (the chatbot under
   test, plus a separate judge model for DeepEval/Giskard scoring). Nothing
   in this directory ran end-to-end this session because the project's
   OpenRouter key was out of credit — everything is written and, where
   checkable without spending money, validated (`promptfoo validate` passed
   on both configs; all Python files import-check clean).

## Layout

```
giskard_scan.py                    Exercise 1 (+ Exercise 4's Giskard portion) -- separate venv only
requirements-giskard.txt           deps for that separate venv
deepeval/
  judge_model.py                   shared OpenRouter-backed judge model (deepeval's built-in OpenRouterModel)
  test_governance.py               Exercise 3 -- 10 cases x 5 metrics, pytest
  conftest.py                      collects every metric measurement into deepeval/results.json
  bias_pairs.py                    Exercise 4 -- BiasMetric on 5 demographic-framing question pairs
promptfoo/
  provider.py                      wraps pipeline.answer_question as a Promptfoo `file://` provider
  promptfooconfig.yaml             Exercise 2 -- main red-team (hijacking/hallucination/overreliance/PII/harmful + jailbreak strategies)
  promptfooconfig_fairness.yaml    Exercise 4 -- bias/PII red-team across 3 user profiles
FAIRNESS_AUDIT.md                  Exercise 4 deliverable
GOVERNANCE_REPORT.md               Exercise 5 deliverable
```

## Running each framework (once credit / a Giskard-compatible env exists)

```bash
# Exercise 1 + Exercise 4 (Giskard) -- separate Python 3.9-3.12 venv, see giskard_scan.py
python3.11 -m venv governance/.giskard_venv
governance/.giskard_venv/Scripts/pip install -r governance/requirements-giskard.txt
governance/.giskard_venv/Scripts/python governance/giskard_scan.py

# Exercise 2 (Promptfoo)
cd governance/promptfoo
npx promptfoo@latest redteam run --config promptfooconfig.yaml
npx promptfoo@latest redteam report --config promptfooconfig.yaml

# Exercise 3 (DeepEval)
pytest governance/deepeval/test_governance.py -v

# Exercise 4 (Promptfoo fairness config + DeepEval bias pairs; Giskard portion above)
cd governance/promptfoo
npx promptfoo@latest redteam run --config promptfooconfig_fairness.yaml
python governance/deepeval/bias_pairs.py
```

Both `promptfooconfig.yaml` and `promptfooconfig_fairness.yaml` were checked
against the actually-installed promptfoo version's real plugin/strategy
catalog (`npx promptfoo@latest redteam plugins`) rather than the exercise
brief's literal plugin names — two of those names (`harmful`, `pii` as bare
tokens, and `jailbreak` as if it were a plugin rather than a strategy) don't
exist in this version; each config's own comments document the real ID used
in place of each one, and both pass `promptfoo validate`.

## What changed in the chatbot itself

`src/generation.py`'s `SYSTEM_PROMPT` gained TRANSPARENCY, PRIVACY, FAIRNESS,
and HUMAN OVERSIGHT sections, and its existing SAFETY/SECURITY sections
gained a life/health/legal redirect (to real, document-sourced helpline
contacts) and a never-execute-code instruction, respectively — see
`GOVERNANCE_REPORT.md`'s executive summary for the plain-language version.
