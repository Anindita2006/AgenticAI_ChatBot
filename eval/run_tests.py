"""Phase 5, Step B — Run the test suite against the live chatbot.

Executes every generated test case through the real RAG pipeline (retrieval +
generation, same code path as the Streamlit app) and captures the question,
expected answer, actual response, retrieved chunks, and latency for each.
Context (dimension 07) cases run as two real turns with history threaded
through, exactly like a user follow-up in the chat UI.

Run directly:
    python eval/run_tests.py
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from pipeline import answer_question

TEST_CASES_PATH = Path(__file__).resolve().parent / "test_cases.json"
OUTPUT_PATH = Path(__file__).resolve().parent / "raw_results.json"


def _serialize_chunks(chunks) -> list[dict]:
    return [{"section": c.section, "page": c.page, "text": c.text} for c in chunks]


def run_single_turn(case: dict) -> dict:
    result = answer_question(case["question"], live_evaluate=False)
    return {
        **case,
        "actual_answer": result["answer"],
        "refused": result["refused"],
        "retrieved_chunks": _serialize_chunks(result["retrieved_chunks"]),
        "latency": result["latency"],
        "turn2_question": None,
        "turn2_actual_answer": None,
        "turn2_refused": None,
        "turn2_retrieved_chunks": None,
        "turn2_latency": None,
    }


def run_context_case(case: dict) -> dict:
    turn1 = answer_question(case["question"], live_evaluate=False)
    history = [
        {"role": "user", "content": case["question"]},
        {"role": "assistant", "content": turn1["answer"]},
    ]
    turn2 = answer_question(case["follow_up_question"], history=history, live_evaluate=False)
    return {
        **case,
        "actual_answer": turn1["answer"],
        "refused": turn1["refused"],
        "retrieved_chunks": _serialize_chunks(turn1["retrieved_chunks"]),
        "latency": turn1["latency"],
        "turn2_question": case["follow_up_question"],
        "turn2_actual_answer": turn2["answer"],
        "turn2_refused": turn2["refused"],
        "turn2_retrieved_chunks": _serialize_chunks(turn2["retrieved_chunks"]),
        "turn2_latency": turn2["latency"],
    }


def run_all() -> list[dict]:
    cases = json.loads(TEST_CASES_PATH.read_text(encoding="utf-8"))
    results = []
    for case in cases:
        print(f"Running {case['id']} ({case['dimension_name']}): {case['question'][:60]!r}")
        if case["dimension_code"] == "07":
            results.append(run_context_case(case))
        else:
            results.append(run_single_turn(case))
    return results


if __name__ == "__main__":
    results = run_all()
    OUTPUT_PATH.write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nRan {len(results)} test cases -> {OUTPUT_PATH}")
