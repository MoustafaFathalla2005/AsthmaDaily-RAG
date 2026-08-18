"""
AsthmaDaily RAG - Evaluation / Embedding model comparison
============================================================
Loads eval/Day2_Evaluation_Test_Set.csv (real questions with verified
expected document + page) and, for a given already-built vector index,
computes:

  - Precision@k         : fraction of the top-k retrieved chunks that come
                           from the expected (document, page)
  - Hit Rate@k           : whether AT LEAST ONE of the top-k chunks matches
                           the expected (document, page)
  - MRR (Mean Reciprocal Rank) : 1/rank of the first correct chunk (0 if none)

The "Not covered" control question is scored separately (correct behaviour =
low/irrelevant similarity score, not a page match). The multi-source question
is scored by whether both GINA and WHO contributed at least one relevant hit.

Run standalone (`python evaluate.py`) to evaluate the currently-built default
index, or import `evaluate_model()` from run_pipeline.py to compare several
embedding models in one report.
"""
import csv
import json
import re

import config
from query import retrieve


def _load_test_set():
    rows = []
    with open(config.EVAL_DIR / "Day2_Evaluation_Test_Set.csv", newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            rows.append(row)
    return rows


def _parse_expected(expected_text: str):
    """Parses strings like 'GINA 2026, Page 205' into (document_name, page)."""
    m = re.search(r"(GINA 2026|WHO 2026).*?Page (\d+)", expected_text)
    if not m:
        return None, None
    return m.group(1), int(m.group(2))


def evaluate_model(vectordb, k: int = 3, verbose: bool = True):
    """Runs the full eval test set against the given vectordb and returns a
    metrics dict. Skips the deliberate out-of-scope and multi-source rows
    from the main Precision@k/MRR average, but reports on them separately.
    """
    test_set = _load_test_set()

    per_question = []
    precisions, hit_flags, reciprocal_ranks = [], [], []
    out_of_scope_row = None
    multi_source_row = None

    for row in test_set:
        expected_text = row["Expected Source (Document / Section / Page)"]

        if "Not covered" in expected_text:
            results = retrieve(vectordb, row["Question"], k=k)
            top_score = results[0][1] if results else 0.0
            out_of_scope_row = {"question": row["Question"], "top_score": top_score}
            continue

        if expected_text.strip().startswith("GINA 2026 + WHO"):
            fused_gina = retrieve(vectordb, row["Question"], k=k, source="GINA")
            fused_who = retrieve(vectordb, row["Question"], k=k, source="WHO")
            multi_source_row = {
                "question": row["Question"],
                "gina_hits": len(fused_gina),
                "who_hits": len(fused_who),
            }
            continue

        expected_doc, expected_page = _parse_expected(expected_text)
        if expected_doc is None:
            continue

        results = retrieve(vectordb, row["Question"], k=k)
        matches = [
            1 if (doc.metadata.get("document_name") == expected_doc
                  and doc.metadata.get("page_number") == expected_page) else 0
            for doc, _ in results
        ]

        precision = sum(matches) / k
        hit = 1 if any(matches) else 0
        rank = next((i + 1 for i, m in enumerate(matches) if m == 1), None)
        rr = 1.0 / rank if rank else 0.0

        precisions.append(precision)
        hit_flags.append(hit)
        reciprocal_ranks.append(rr)

        per_question.append({
            "question": row["Question"], "expected": expected_text,
            "precision_at_k": precision, "hit": hit, "rank": rank,
        })

        if verbose:
            status = f"rank={rank}" if rank else "MISS"
            print(f"  P@{k}={precision:.2f} [{status}] {row['Question'][:60]}")

    n = len(precisions)
    metrics = {
        "k": k,
        "n_scored_questions": n,
        "avg_precision_at_k": sum(precisions) / n if n else 0.0,
        "hit_rate_at_k": sum(hit_flags) / n if n else 0.0,
        "mrr": sum(reciprocal_ranks) / n if n else 0.0,
        "out_of_scope_control": out_of_scope_row,
        "multi_source_question": multi_source_row,
        "per_question": per_question,
    }
    return metrics


if __name__ == "__main__":
    from query import load_index

    vectordb = load_index()
    print(f"Evaluating default embedding model ({config.DEFAULT_EMBEDDING_MODEL_ID}) ...\n")
    metrics = evaluate_model(vectordb, k=3)

    print("\n" + "-" * 60)
    print(f"Avg Precision@{metrics['k']}: {metrics['avg_precision_at_k']:.3f}")
    print(f"Hit Rate@{metrics['k']}:      {metrics['hit_rate_at_k']:.3f}")
    print(f"MRR:                     {metrics['mrr']:.3f}")

    out_path = config.OUTPUTS_DIR / f"05_eval_{config.DEFAULT_EMBEDDING_MODEL_ID}.json"
    out_path.write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    print(f"\nSaved -> {out_path}")
