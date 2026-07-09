"""Collects every metric measurement across the governance test suite into one
score matrix and writes it to results.json when the pytest session ends --
`assert_test`/plain pytest only reports pass/fail, but the exercise asks to
report the actual numeric scores per metric and per test case, and to
identify the weakest metric and the worst-performing case across the whole
suite (mirrors eval/report.py's cross-dimension approach for the same reason).
"""

import json
from collections import defaultdict
from pathlib import Path

import pytest

RESULTS_PATH = Path(__file__).resolve().parent / "results.json"

_ROWS = []


@pytest.fixture
def record_governance_result():
    def _record(*, case_id, category, question, actual_output, metric_name, score, threshold, reason, success):
        _ROWS.append({
            "case_id": case_id, "category": category, "question": question,
            "actual_output": actual_output, "metric": metric_name,
            "score": score, "threshold": threshold, "reason": reason, "success": success,
        })
    return _record


def pytest_sessionfinish(session, exitstatus):
    if not _ROWS:
        return

    RESULTS_PATH.write_text(json.dumps(_ROWS, indent=2, ensure_ascii=False), encoding="utf-8")

    by_metric = defaultdict(list)
    by_case = defaultdict(list)
    for row in _ROWS:
        by_metric[row["metric"]].append(row["score"])
        by_case[row["case_id"]].append(row)

    print(f"\n\nGovernance metric matrix -> {RESULTS_PATH}\n")
    print(f"{'Metric':<18}{'Avg score':<12}{'Min':<8}{'Max':<8}")
    worst_metric, worst_avg = None, None
    for metric, scores in sorted(by_metric.items()):
        avg = sum(scores) / len(scores)
        print(f"{metric:<18}{avg:<12.3f}{min(scores):<8.3f}{max(scores):<8.3f}")
        # For Hallucination/Bias/Toxicity, LOWER is worse-case-worthy in the opposite
        # direction (higher score = worse); for Faithfulness/AnswerRelevancy, lower
        # score = worse. Reporting both ends lets a reader judge either way; the
        # printed table above is the actual deliverable, this just flags one metric
        # to call out by name.
        if worst_avg is None or avg > worst_avg:
            worst_metric, worst_avg = metric, avg

    print(f"\nHighest-average metric (worth a closer look): {worst_metric} (avg {worst_avg:.3f})")

    failure_counts = {cid: sum(1 for r in rows if not r["success"]) for cid, rows in by_case.items()}
    worst_case_id = max(failure_counts, key=failure_counts.get)
    print(
        f"Test case that failed the most metrics: {worst_case_id} "
        f"({failure_counts[worst_case_id]} of {len(by_case[worst_case_id])} metrics failed)"
    )
