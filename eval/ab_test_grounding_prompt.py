"""Day 5, Session 3, Exercise 4 -- A/B test on the grounding prompt.

Version A is the existing (Day 4) grounding prompt, unchanged. Version B adds
one stricter clause on top of it (`generation.PROMPT_VARIANT_B_ADDENDUM`):
mandatory per-fact citations, a fixed refusal phrase, and "never infer or
extrapolate." The hypothesis (per the exercise brief): B should improve
faithfulness but may over-refuse on questions that ARE answerable from the
document, just not in the exact phrasing the strict prompt expects.

10 questions, each run twice (20 total calls), with the variant assigned
per-run from a shuffled 10xA/10xB deck -- an exact 50/50 split rather than
independent coin flips, so the two arms get equal sample size instead of
merely converging to it. Each question is pre-labeled `expect_in_doc` so a
refusal can be scored as CORRECT (question genuinely isn't grounded in the
knowledge base) or INCORRECT (question IS answerable, but the prompt refused
anyway -- exactly the over-refusal risk this test is checking for).

Requires a working OPENROUTER_API_KEY with available credit -- this script
makes 20 real chat completions.

Run directly:
    python eval/ab_test_grounding_prompt.py
"""

import json
import random
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from pipeline import answer_question

OUTPUT_PATH = Path(__file__).resolve().parent / "ab_test_results.json"

CITATION_PATTERN = re.compile(r"\[[^\[\]]+,\s*Page\s*\d+\]")

# expect_in_doc=True  -> a correct answer should NOT refuse (grounded fact exists)
# expect_in_doc=False -> a correct answer SHOULD refuse (out of scope / not in KB / unsafe to promise)
QUESTIONS = [
    {"question": "What is the annual tuition fee for CSE?", "expect_in_doc": True},
    {"question": "List all the undergraduate B.Tech programmes offered at BVRIT Hyderabad.", "expect_in_doc": True},
    {"question": "What are the placement statistics for CSE?", "expect_in_doc": True},
    {"question": "Who is the HOD of the ECE department?", "expect_in_doc": True},
    {"question": "What scholarships are available at BVRIT Hyderabad?", "expect_in_doc": True},
    {"question": "Tell me about hostel facilities at BVRIT Hyderabad.", "expect_in_doc": True},
    {"question": "When is the last date for EAMCET counselling?", "expect_in_doc": True},
    {"question": "What is the average salary of a professor at BVRIT Hyderabad?", "expect_in_doc": False},
    {"question": "Will I definitely get placed if I join BVRIT Hyderabad?", "expect_in_doc": False},
    {"question": "What is the capital of France?", "expect_in_doc": False},
]


def _assign_variants(n_questions: int, repeats: int) -> list[str]:
    total = n_questions * repeats
    deck = ["A"] * (total // 2) + ["B"] * (total // 2)
    random.shuffle(deck)
    return deck


def run_ab_test(repeats: int = 2) -> list[dict]:
    variants = _assign_variants(len(QUESTIONS), repeats)
    runs = [q for q in QUESTIONS for _ in range(repeats)]

    results = []
    for i, (variant, spec) in enumerate(zip(variants, runs)):
        print(f"[{i + 1}/{len(runs)}] variant {variant} -- {spec['question'][:60]!r}")
        result = answer_question(spec["question"], prompt_variant=variant)
        has_citation = bool(CITATION_PATTERN.search(result["answer"]))
        refused = result["refused"]
        refusal_correctness = None
        if refused:
            refusal_correctness = "correct" if not spec["expect_in_doc"] else "incorrect"
        results.append({
            "variant": variant,
            "question": spec["question"],
            "expect_in_doc": spec["expect_in_doc"],
            "answer": result["answer"],
            "has_citation": has_citation,
            "refused": refused,
            "refusal_correctness": refusal_correctness,
            "latency": result["latency"],
        })
    return results


def summarize(results: list[dict]) -> dict:
    summary = {}
    for variant in ("A", "B"):
        rows = [r for r in results if r["variant"] == variant]
        n = len(rows)
        summary[variant] = {
            "n": n,
            "citation_count": sum(1 for r in rows if r["has_citation"]),
            "refusal_count": sum(1 for r in rows if r["refused"]),
            "correct_refusals": sum(1 for r in rows if r["refusal_correctness"] == "correct"),
            "incorrect_refusals": sum(1 for r in rows if r["refusal_correctness"] == "incorrect"),
        }
    return summary


if __name__ == "__main__":
    results = run_ab_test()
    OUTPUT_PATH.write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")

    summary = summarize(results)
    print(f"\nWrote {len(results)} results -> {OUTPUT_PATH}\n")
    print(f"{'Metric':<22}{'Version A':<12}{'Version B':<12}")
    for metric, label in [
        ("citation_count", "Has citation"),
        ("refusal_count", "Refused"),
        ("correct_refusals", "  correct refusals"),
        ("incorrect_refusals", "  incorrect refusals"),
    ]:
        print(f"{label:<22}{summary['A'][metric]:<12}{summary['B'][metric]:<12}")
