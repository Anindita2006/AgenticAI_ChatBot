"""Phase 5, Step D — Generate the evaluation report.

Merges judged_results.json (dimensions 01-07) with ragas_results.json
(dimension 08) into one final scored set, computes per-dimension pass/fail
counts, identifies the weakest dimension with an evidence-based recommended
fix (quoting the actual judge reason, not a generic template), and reports
RAGAS metric averages with a diagnosis of the weakest metric.

Run directly:
    python eval/report.py
"""

import json
from pathlib import Path

JUDGED_RESULTS_PATH = Path(__file__).resolve().parent / "judged_results.json"
RAGAS_RESULTS_PATH = Path(__file__).resolve().parent / "ragas_results.json"
OUTPUT_PATH = Path(__file__).resolve().parent / "report.json"

DIMENSION_ORDER = ["01", "02", "03", "04", "05", "06", "07", "08"]
DIMENSION_NAMES = {
    "01": "Functional", "02": "Quality", "03": "Safety", "04": "Security",
    "05": "Robustness", "06": "Performance", "07": "Context", "08": "RAGAS",
}


def merge_results() -> list[dict]:
    judged = json.loads(JUDGED_RESULTS_PATH.read_text(encoding="utf-8"))
    ragas = {c["id"]: c for c in json.loads(RAGAS_RESULTS_PATH.read_text(encoding="utf-8"))}
    return [ragas.get(c["id"], c) if c["dimension_code"] == "08" else c for c in judged]


def build_report(cases: list[dict]) -> dict:
    by_dim: dict[str, list[dict]] = {code: [] for code in DIMENSION_ORDER}
    for c in cases:
        by_dim[c["dimension_code"]].append(c)

    dimensions = []
    for code in DIMENSION_ORDER:
        dim_cases = by_dim[code]
        passed = sum(1 for c in dim_cases if c["verdict"] == "pass")
        total = len(dim_cases)
        dimensions.append({
            "code": code,
            "name": DIMENSION_NAMES[code],
            "total": total,
            "passed": passed,
            "failed": total - passed,
            "pass_rate": passed / total if total else 0.0,
            "cases": [
                {
                    "id": c["id"],
                    "question": c["question"],
                    "expected_answer": c["expected_answer"],
                    "actual_answer": c["actual_answer"],
                    "verdict": c["verdict"],
                    "reason": c["judge_reason"],
                    "latency": c.get("latency"),
                }
                for c in dim_cases
            ],
        })

    total_cases = len(cases)
    total_passed = sum(1 for c in cases if c["verdict"] == "pass")
    total_failed = total_cases - total_passed

    weakest = min(dimensions, key=lambda d: d["pass_rate"])
    failing_examples = [c for c in weakest["cases"] if c["verdict"] == "fail"]
    if failing_examples:
        example = failing_examples[0]
        recommended_fix = (
            f"{weakest['name']} ({weakest['passed']}/{weakest['total']} passed). "
            f"Worst case {example['id']}: {example['reason']}"
        )
    else:
        recommended_fix = "All dimensions passed — no fix required this run."

    ragas_cases = [c for c in by_dim["08"] if "ragas_metrics" in c]
    ragas_scores = {}
    ragas_diagnosis = "No RAGAS cases scored."
    if ragas_cases:
        metric_names = ["faithfulness", "answer_relevancy", "context_precision", "context_recall"]
        for m in metric_names:
            ragas_scores[m] = sum(c["ragas_metrics"][m] for c in ragas_cases) / len(ragas_cases)
        weakest_metric = min(ragas_scores, key=ragas_scores.get)
        diagnosis_hints = {
            "faithfulness": "the answer states things not supported by the retrieved context — "
                             "tighten the grounding prompt's 'answer ONLY from context' instruction.",
            "answer_relevancy": "the answer drifts from the question — consider a stricter system "
                                 "prompt or lowering temperature.",
            "context_precision": "retrieval returns some irrelevant chunks alongside relevant ones "
                                  "— consider reducing chunk_size or adding metadata filters.",
            "context_recall": "retrieval is missing part of the answer — consider increasing top_k "
                               "or chunk_overlap.",
        }
        ragas_diagnosis = (
            f"{weakest_metric.replace('_', ' ').title()} is the lowest RAGAS metric "
            f"({ragas_scores[weakest_metric]:.2f}) — {diagnosis_hints[weakest_metric]}"
        )

    return {
        "summary": {
            "total": total_cases,
            "passed": total_passed,
            "failed": total_failed,
            "pass_rate": total_passed / total_cases if total_cases else 0.0,
        },
        "dimensions": dimensions,
        "weakest_dimension": {"code": weakest["code"], "name": weakest["name"]},
        "recommended_fix": recommended_fix,
        "ragas_scores": ragas_scores,
        "ragas_diagnosis": ragas_diagnosis,
    }


def print_report(report: dict) -> None:
    s = report["summary"]
    print(f"Summary\nTotal test cases: {s['total']} | Passed: {s['passed']} | "
          f"Failed: {s['failed']} | Pass rate: {s['pass_rate']*100:.0f}%\n")

    print("Per-dimension breakdown")
    for d in report["dimensions"]:
        print(f"  {d['code']} {d['name']}: {d['passed']}/{d['total']} passed")

    print(f"\nWeakest dimension: {report['weakest_dimension']['name']} "
          f"({report['weakest_dimension']['code']})")
    print(f"Recommended fix: {report['recommended_fix']}")

    if report["ragas_scores"]:
        print("\nRAGAS scores")
        for k, v in report["ragas_scores"].items():
            print(f"  {k.replace('_', ' ').title()}: {v:.2f}")
        print(f"\nRAGAS diagnosis: {report['ragas_diagnosis']}")


if __name__ == "__main__":
    merged = merge_results()
    report = build_report(merged)
    OUTPUT_PATH.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print_report(report)
    print(f"\nFull report saved -> {OUTPUT_PATH}")
