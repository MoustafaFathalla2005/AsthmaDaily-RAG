"""
AsthmaDaily RAG - End-to-end pipeline runner
================================================
Runs every stage once, saving the output of each stage to outputs/, then
builds an index PER embedding model in config.EMBEDDING_MODELS, evaluates
each one against eval/Day2_Evaluation_Test_Set.csv, and writes a final
comparison report (JSON + Markdown) to outputs/.

HuggingFace-backed models require downloading weights from huggingface.co
the first time they run. If that network call fails (no internet access,
or the host is blocked), that model is recorded as SKIPPED in the report
instead of crashing the whole run - the rest of the pipeline still
completes and the report says exactly why.

Usage:  python run_pipeline.py
"""
import json
import time
import traceback

import config
import ingest
from evaluate import evaluate_model

EVAL_K = 3


def main():
    print("=" * 70)
    print("STEP 1/5 - Loading PDFs")
    print("=" * 70)
    pages = ingest.load_pdfs()

    print("\n" + "=" * 70)
    print("STEP 2/5 - Preprocessing")
    print("=" * 70)
    pages = ingest.preprocess(pages)

    print("\n" + "=" * 70)
    print(f"STEP 3/5 - Chunking (size={config.CHUNK_SIZE} tok, overlap={config.CHUNK_OVERLAP} tok)")
    print("=" * 70)
    chunks = ingest.chunk_documents(pages)

    print("\n" + "=" * 70)
    print("STEP 4/5 - Build + evaluate an index per embedding model")
    print("=" * 70)

    comparison = []
    for model_config in config.EMBEDDING_MODELS:
        model_id = model_config["id"]
        print(f"\n--- {model_id} ({model_config['model_name']}) ---")
        entry = {
            "id": model_id,
            "model_name": model_config["model_name"],
            "type": model_config["type"],
            "description": model_config["description"],
            "status": "ok",
        }
        try:
            t0 = time.time()
            vectordb = ingest.build_index(chunks, model_config=model_config)
            build_seconds = time.time() - t0

            t0 = time.time()
            metrics = evaluate_model(vectordb, k=EVAL_K, verbose=False)
            eval_seconds = time.time() - t0

            entry.update({
                "build_seconds": round(build_seconds, 2),
                "eval_seconds": round(eval_seconds, 2),
                "avg_precision_at_k": round(metrics["avg_precision_at_k"], 3),
                "hit_rate_at_k": round(metrics["hit_rate_at_k"], 3),
                "mrr": round(metrics["mrr"], 3),
                "n_scored_questions": metrics["n_scored_questions"],
                "out_of_scope_top_score": (
                    round(metrics["out_of_scope_control"]["top_score"], 3)
                    if metrics["out_of_scope_control"] else None
                ),
            })
            out_path = config.OUTPUTS_DIR / f"05_eval_{model_id}.json"
            out_path.write_text(json.dumps(metrics, indent=2), encoding="utf-8")
            print(f"  P@{EVAL_K}={entry['avg_precision_at_k']:.3f}  "
                  f"HitRate@{EVAL_K}={entry['hit_rate_at_k']:.3f}  MRR={entry['mrr']:.3f}  "
                  f"(build {build_seconds:.1f}s, eval {eval_seconds:.1f}s)")

        except Exception as e:
            entry["status"] = "skipped"
            entry["error"] = f"{type(e).__name__}: {e}"
            print(f"  SKIPPED - {entry['error']}")
            if model_config["type"] == "huggingface":
                print("  (This environment has no network access to huggingface.co - "
                      "this model will run normally in an environment with internet access.)")

        comparison.append(entry)

    print("\n" + "=" * 70)
    print("STEP 5/5 - Writing comparison report")
    print("=" * 70)
    write_report(comparison)


def write_report(comparison):
    json_path = config.OUTPUTS_DIR / "06_embedding_comparison_report.json"
    json_path.write_text(json.dumps(comparison, indent=2), encoding="utf-8")

    ok_rows = [c for c in comparison if c["status"] == "ok"]
    skipped_rows = [c for c in comparison if c["status"] != "ok"]
    best = max(ok_rows, key=lambda c: c["avg_precision_at_k"]) if ok_rows else None

    lines = []
    lines.append("# Embedding Model Comparison Report\n")
    lines.append(f"Evaluated on {config.EVAL_DIR / 'Day2_Evaluation_Test_Set.csv'} "
                  f"(k={EVAL_K}, chunk_size={config.CHUNK_SIZE} tok, "
                  f"overlap={config.CHUNK_OVERLAP} tok).\n")

    if ok_rows:
        lines.append("| Model | Type | Precision@3 | Hit Rate@3 | MRR | Build (s) | Eval (s) |")
        lines.append("|---|---|---|---|---|---|---|")
        for c in ok_rows:
            lines.append(
                f"| {c['id']} | {c['type']} | {c['avg_precision_at_k']:.3f} | "
                f"{c['hit_rate_at_k']:.3f} | {c['mrr']:.3f} | {c['build_seconds']} | {c['eval_seconds']} |"
            )
        lines.append("")
        if best:
            lines.append(f"**Best on this run: `{best['id']}`** "
                          f"(Precision@3 = {best['avg_precision_at_k']:.3f}).\n")

    if skipped_rows:
        lines.append("## Skipped models\n")
        for c in skipped_rows:
            lines.append(f"- `{c['id']}` ({c['model_name']}) - {c['error']}")
        lines.append("")

    report_path = config.OUTPUTS_DIR / "06_embedding_comparison_report.md"
    report_path.write_text("\n".join(lines), encoding="utf-8")

    print("\n".join(lines))
    print(f"\nSaved -> {json_path}\nSaved -> {report_path}")


if __name__ == "__main__":
    main()
