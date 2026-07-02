"""Phase 5, Step C (Dimension 08) — RAGAS scoring, run as code, not an LLM prompt.

Scores the 3 RAGAS test cases with faithfulness, answer relevancy, context
precision, and context recall, using JUDGE_MODEL as the RAGAS evaluator LLM
(same anti-self-bias reasoning as judge.py: a different model than the
chatbot under test) and the project's own embedding model/endpoint.

Run directly:
    python eval/ragas_eval.py
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from ragas import EvaluationDataset, SingleTurnSample, evaluate
from ragas.embeddings import LangchainEmbeddingsWrapper
from ragas.llms import LangchainLLMWrapper
from ragas.metrics import AnswerRelevancy, ContextPrecision, ContextRecall, Faithfulness

import config

JUDGED_RESULTS_PATH = Path(__file__).resolve().parent / "judged_results.json"
OUTPUT_PATH = Path(__file__).resolve().parent / "ragas_results.json"

PASS_THRESHOLD = 0.7  # average of the 4 metrics, for a per-case pass/fail rollup


def build_dataset(cases: list[dict]) -> EvaluationDataset:
    samples = []
    for case in cases:
        contexts = [c["text"] for c in case["retrieved_chunks"]] or [""]
        samples.append(SingleTurnSample(
            user_input=case["question"],
            response=case["actual_answer"],
            retrieved_contexts=contexts,
            reference=case["expected_answer"],
        ))
    return EvaluationDataset(samples=samples)


def run_ragas(cases: list[dict]) -> list[dict]:
    llm = ChatOpenAI(
        model=config.JUDGE_MODEL,
        api_key=config.OPENROUTER_API_KEY,
        base_url=config.OPENROUTER_BASE_URL,
        temperature=0,
    )
    embeddings = OpenAIEmbeddings(
        model=config.EMBEDDING_MODEL,
        api_key=config.EMBEDDING_API_KEY,
        base_url=config.EMBEDDING_BASE_URL,
    )
    wrapped_llm = LangchainLLMWrapper(llm)
    wrapped_embeddings = LangchainEmbeddingsWrapper(embeddings)

    dataset = build_dataset(cases)
    result = evaluate(
        dataset=dataset,
        metrics=[Faithfulness(), AnswerRelevancy(), ContextPrecision(), ContextRecall()],
        llm=wrapped_llm,
        embeddings=wrapped_embeddings,
    )

    df = result.to_pandas()
    scored = []
    for case, (_, row) in zip(cases, df.iterrows()):
        metrics = {
            "faithfulness": float(row["faithfulness"]),
            "answer_relevancy": float(row["answer_relevancy"]),
            "context_precision": float(row["context_precision"]),
            "context_recall": float(row["context_recall"]),
        }
        avg = sum(metrics.values()) / len(metrics)
        scored.append({
            **case,
            "ragas_metrics": metrics,
            "ragas_average": avg,
            "verdict": "pass" if avg >= PASS_THRESHOLD else "fail",
            "judge_reason": f"RAGAS average {avg:.2f} (threshold {PASS_THRESHOLD})",
        })
    return scored


if __name__ == "__main__":
    all_cases = json.loads(JUDGED_RESULTS_PATH.read_text(encoding="utf-8"))
    ragas_cases = [c for c in all_cases if c["dimension_code"] == "08"]

    print(f"Scoring {len(ragas_cases)} RAGAS test cases (this makes several evaluator-LLM calls)...")
    scored = run_ragas(ragas_cases)

    OUTPUT_PATH.write_text(json.dumps(scored, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Saved -> {OUTPUT_PATH}\n")
    for c in scored:
        m = c["ragas_metrics"]
        print(f"  {c['id']}: {c['verdict']} (avg={c['ragas_average']:.2f}) "
              f"faithfulness={m['faithfulness']:.2f} relevancy={m['answer_relevancy']:.2f} "
              f"precision={m['context_precision']:.2f} recall={m['context_recall']:.2f}")
