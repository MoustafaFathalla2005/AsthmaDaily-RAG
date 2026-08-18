"""Run lightweight, offline-compatible measurements that mirror notebooks 1-4.

Writes a JSON report to `outputs/notebook_measurements.json` containing
ingestion counts, retrieval score ranges, calibration suggestions, and
basic evaluation metrics like precision@k and citation-match counts.
"""
import csv
import json
from pathlib import Path
from statistics import mean

from ingest import load_pdfs, chunk_documents, build_index
from query import retrieve
from tools.notebook_tools import parse_expected_source

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'outputs' / 'notebook_measurements.json'
OUT.parent.mkdir(parents=True, exist_ok=True)


def load_eval_set(path):
    rows = []
    with open(path, encoding='utf8') as f:
        reader = csv.DictReader(f)
        for r in reader:
            rows.append(r)
    return rows


def precision_at_k_for_eval(vectordb, eval_rows, k=3):
    precisions = []
    citation_matches = 0
    total = 0
    top_scores = []
    for r in eval_rows:
        q = r['Question']
        expected = r['Expected Source (Document / Section / Page)']
        doc_expected, page_expected = parse_expected_source(expected)
        try:
            results = retrieve(vectordb, q, k=k)
        except Exception:
            results = []
        total += 1
        if not results:
            precisions.append(0.0)
            continue
        top_scores.append(results[0][1])
        # compute precision@k: proportion of top-k that match expected document substring
        hits = 0
        for doc, score in results:
            docname = (doc.metadata.get('document_name') or '').lower()
            page = doc.metadata.get('page_number')
            if doc_expected and doc_expected in docname:
                hits += 1
                if page_expected and str(page_expected) == str(page):
                    citation_matches += 1
        precisions.append(hits / max(1, k))

    return {
        'precision_at_k_mean': mean(precisions) if precisions else 0.0,
        'top_score_mean': mean(top_scores) if top_scores else 0.0,
        'citation_match_count': citation_matches,
        'queries_evaluated': total,
    }


def main():
    print('Loading pages...')
    pages = load_pdfs(Path('data'))
    print('Chunking...')
    chunks = chunk_documents(pages)
    print('Building index...')
    vectordb = build_index(chunks)
    print('Index ready')

    eval_rows = load_eval_set(Path('eval') / 'Day2_Evaluation_Test_Set.csv')
    eval_metrics = precision_at_k_for_eval(vectordb, eval_rows, k=3)

    # Quick calibration ranges for a few answerable/unanswerable queries (as in Day4)
    answerable = [
        "What factors are used to assess the level of asthma symptom control?",
        "Can exercise trigger asthma symptoms?",
        "What is a written asthma action plan and who should have one?",
    ]
    unanswerable = [
        "What's the best diet plan for losing weight fast?",
        "What is the recommended antibiotic dose for pneumonia in adults?",
    ]
    def top_score(q):
        try:
            r = retrieve(vectordb, q, k=1)
            return r[0][1] if r else 0.0
        except Exception:
            return 0.0

    answerable_scores = [top_score(q) for q in answerable]
    unanswerable_scores = [top_score(q) for q in unanswerable]

    report = {
        'ingestion': { 'pages': len(pages), 'chunks': len(chunks) },
        'eval': eval_metrics,
        'calibration': {
            'answerable_scores': answerable_scores,
            'unanswerable_scores': unanswerable_scores,
            'suggested_threshold': (min(answerable_scores) + max(unanswerable_scores)) / 2 if answerable_scores and unanswerable_scores else None
        }
    }

    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf8')
    print('Wrote', OUT)


if __name__ == '__main__':
    main()
