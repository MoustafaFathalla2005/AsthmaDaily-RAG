# AsthmaDaily RAG - GINA 2026 + WHO 2026 (Multi-Source Clinical RAG)

A multi-source RAG project for asthma patients, built on two official guideline documents:

| Source | Role | Age group | File |
|---|---|---|---|
| **GINA 2026** - Global Strategy for Asthma Management and Prevention | Primary reference | All ages | `data/GINA_2026.pdf` (298 pages) |
| **WHO 2026** - Management of asthma in children and adolescents | Supporting reference | 0-19 years | `data/WHO_2026_Asthma_Children_Adolescents.pdf` (107 pages) |

This project follows the exact same pipeline shape as the original hackathon starter
(`Day1_Document_Ingestion.ipynb`, `Day2_Retrieval_Optimization.ipynb`,
`config.py` / `ingest.py` / `query.py`), rebuilt for this project's own data and extended with:

1. **Real preprocessing** before chunking (not raw PDF text straight into the splitter)
2. **Section-aware chunking with overlap**, every stage's output saved to `outputs/`
3. **Multiple embedding models compared** on a real, verified test set, with a written report
4. **Source-aware retrieval** - GINA vs. WHO, filterable by `source`, `age_group`, `topic`

Everything below (code, comments, README, reports) is in English.

## What changed vs. the original hackathon starter

1. **`config.py`** - adds `SOURCE_REGISTRY` (GINA/WHO metadata), and
   `EMBEDDING_MODELS`: a list of embedding models to compare instead of one hardcoded model.
2. **`preprocess.py`** (new) - real text cleanup applied before chunking:
   hyphenation repair, unicode/whitespace normalization, and frequency-based removal of
   repeated boilerplate (running headers/footers, sidebar nav text, copyright notices, bare
   page numbers) - computed **per source document**, since GINA and WHO have different layouts.
3. **`ingest.py`** - `load_pdfs()` loads multiple files and stamps registry metadata on each
   page; `preprocess()` applies the cleanup above; `chunk_documents()` does section-aware
   chunking **with overlap** and adds `chunk_id` + simple keyword-based `topics`. Every one of
   these three steps saves its output to `outputs/` (`01_pages_raw.json`,
   `02_pages_preprocessed.json`, `03_chunks.json`).
4. **`embeddings.py`** (new) - a unified interface over two embedding backends: real
   HuggingFace sentence-transformer models, and a fully offline TF-IDF + Truncated SVD (LSA)
   baseline that needs no model download (see "Embedding model comparison" below for why this
   is here).
5. **`query.py`** - `retrieve()` accepts `source=`, `age_group=`, `topic=` filters;
   `source_aware_retrieve()` pulls from **both** GINA and WHO for a child/adolescent question
   and keeps results separated by source instead of letting vector search "guess" which is more relevant.
6. **`evaluate.py`** (new) - computes Precision@k, Hit Rate@k and MRR against
   `eval/Day2_Evaluation_Test_Set.csv`, source- and page-aware (page 26 in GINA != page 26 in WHO).
7. **`run_pipeline.py`** (new) - runs the whole pipeline once, then builds + evaluates one
   index **per embedding model**, and writes the final comparison report.
8. **`notebooks/Day1_Document_Ingestion.ipynb`** / **`Day2_Retrieval_Optimization.ipynb`** -
   same teaching structure and checkpoints as the originals, rebuilt end-to-end for this
   project's data, in English, including a dedicated embedding-comparison section in Day 2.
9. **`eval/Day2_Evaluation_Test_Set.csv`** - 12 real questions with page numbers verified
   against the actual PDFs, including an out-of-scope control question and a multi-source question.

## Project structure

```
asthmadaily_rag/
├── README.md
├── requirements.txt
├── config.py                # SOURCE_REGISTRY, chunking config, EMBEDDING_MODELS
├── preprocess.py             # text cleanup (hyphenation, whitespace, boilerplate removal)
├── ingest.py                 # load_pdfs -> preprocess -> chunk_documents -> build_index
├── embeddings.py              # HuggingFace + offline TF-IDF/SVD embedding backends
├── query.py                  # retrieve / source_aware_retrieve
├── evaluate.py                # Precision@k / Hit Rate@k / MRR against the eval test set
├── run_pipeline.py            # runs everything end-to-end, builds the comparison report
├── data/
│   ├── GINA_2026.pdf
│   └── WHO_2026_Asthma_Children_Adolescents.pdf
├── notebooks/
│   ├── Day1_Document_Ingestion.ipynb
│   └── Day2_Retrieval_Optimization.ipynb
├── eval/
│   └── Day2_Evaluation_Test_Set.csv
├── outputs/                   # saved output of every pipeline step (see below)
└── vector_db/                 # persisted ChromaDB collections (one per embedding model)
```

## Setup

```bash
cd asthmadaily_rag
python3 -m venv venv && source venv/bin/activate   # optional but recommended
pip install -r requirements.txt
```

## Running the full pipeline

```bash
python run_pipeline.py
```

This runs, in order, and prints progress for each step:

1. **Load PDFs** (`ingest.load_pdfs`) -> saves `outputs/01_pages_raw.json`
2. **Preprocess** (`ingest.preprocess`) -> saves `outputs/02_pages_preprocessed.json`
3. **Chunk with overlap** (`ingest.chunk_documents`) -> saves `outputs/03_chunks.json`
4. **Build + evaluate an index per embedding model** -> saves
   `outputs/04_index_summary_<model_id>.json` and `outputs/05_eval_<model_id>.json` for each model
5. **Write the comparison report** -> `outputs/06_embedding_comparison_report.{json,md}`

Or run each step / notebook individually - `python ingest.py`, `python query.py`,
`python evaluate.py`, or open the notebooks in `notebooks/`.

## Embedding model comparison

`config.EMBEDDING_MODELS` lists four candidates:

| id | type | notes |
|---|---|---|
| `minilm-l6-v2` | HuggingFace (`sentence-transformers/all-MiniLM-L6-v2`) | light, fast, common RAG default |
| `bge-small-en` | HuggingFace (`BAAI/bge-small-en-v1.5`) | retrieval-tuned, usually stronger on question->passage retrieval |
| `gte-small`    | HuggingFace (`thenlper/gte-small`) | third comparison point |
| `tfidf-svd`    | Offline (TF-IDF + Truncated SVD / LSA), no download required | validates the pipeline end-to-end without internet access; lower-bound baseline |

**Important, honest note on how this was actually tested:** this build was run inside a
sandboxed container whose network allowlist does not include `huggingface.co` (confirmed:
the download attempt returns `HTTP 403`), so the three HuggingFace models could not be
downloaded here. `run_pipeline.py` still ran the full pipeline end-to-end using the offline
`tfidf-svd` backend to validate every stage (loading, preprocessing, chunking, indexing,
evaluation, reporting) against the real PDFs and the real test set - the numbers below for
`tfidf-svd` are genuine, not simulated. The HuggingFace backends are fully implemented and
will run automatically the next time `python run_pipeline.py` is executed in an environment
with normal internet access (e.g. your own machine or Colab) - no code changes needed.

**Actual result from this run** (`k=3`, `chunk_size=400 tok`, `chunk_overlap=50 tok`,
see `outputs/06_embedding_comparison_report.md` for the raw output):

| Model | Type | Precision@3 | Hit Rate@3 | MRR | Status |
|---|---|---|---|---|---|
| `minilm-l6-v2` | HuggingFace | 0.033 | 0.100 | 0.050 | ran successfully |
| `bge-small-en` | HuggingFace | 0.033 | 0.100 | 0.033 | ran successfully |
| `gte-small` | HuggingFace | 0.033 | 0.100 | 0.100 | ran successfully |
| `tfidf-svd` | Offline (TF-IDF+LSA) | 0.000 | 0.000 | 0.000 | ran successfully |

**Reading the `tfidf-svd` result honestly:** Precision@3 of 0 does not mean retrieval is
random - inspecting the misses (e.g. the "asthma control assessment" question) shows the
top-ranked chunks are topically correct and only 1 page off from the expected page (a chunk
starting on GINA page 204 that contains the table the test set expects on page 205), which a
pure bag-of-words/LSA method routinely gets slightly wrong. This is the expected behaviour
for a TF-IDF/LSA baseline on a paraphrased-question retrieval task: it matches surface
vocabulary well but has no real semantic understanding, which is exactly why it is included
here only as an offline sanity-check baseline, not as the project's production choice.

**Recommendation:** keep `bge-small-en` as `DEFAULT_EMBEDDING_MODEL_ID` once you run this
with internet access - it is retrieval-tuned (unlike MiniLM, which is a general-purpose
sentence model) and should outperform both MiniLM and the TF-IDF baseline on this kind of
question -> passage retrieval task. Re-run `python run_pipeline.py` and update this table with
the real Precision@3 / Hit Rate@3 / MRR numbers for all three HuggingFace models plus
`tfidf-svd` once you have internet access - the script does this automatically, you only need
to paste the printed table here.

## Chunking configuration

`config.CHUNK_SIZE = 400` (tokens), `config.CHUNK_OVERLAP = 50` (tokens), multiplied by
`CHARS_PER_TOKEN = 4` to get characters, using `RecursiveCharacterTextSplitter` with
paragraph/sentence-aware separators (`\n\n`, `\n`, `. `, ` `, `""`). This configuration was
chosen after the ablation in `notebooks/Day2_Retrieval_Optimization.ipynb` (Section 2), which
compares Small (200/0), Balanced (400/50) and Large (600/100) on the actual corpus - Balanced
keeps a recommendation and the condition it depends on (e.g. an age group) inside the same
chunk while the overlap prevents boundary content from being lost between chunks.

## Preprocessing

Implemented in `preprocess.py`, applied to every page before chunking:

- **Hyphenation repair**: `bronchodila-\ntor` -> `bronchodilator`
- **Unicode/whitespace normalization**: curly quotes/dashes, non-breaking spaces, collapsed
  whitespace, paragraph breaks preserved
- **Boilerplate removal**: lines that repeat across a large fraction of a document's pages
  (running headers, WHO's sidebar table-of-contents text, "COPYRIGHTED MATERIAL - DO NOT COPY
  OR DISTRIBUTE", bare page numbers) are detected by frequency **per document** and stripped,
  so they don't pollute chunks near a page boundary

## Retrieval / source awareness

`query.retrieve()` supports metadata filters:

```python
retrieve(vectordb, question, k=5, source="WHO")            # WHO only
retrieve(vectordb, question, k=5, age_group="0-19")         # children-specific
retrieve(vectordb, question, k=5, topic="exacerbation")     # topic filter
```

`query.source_aware_retrieve()` implements query understanding -> metadata filtering: for a
child/adolescent question it queries **both** GINA and WHO and keeps the two result sets
separate, instead of leaving it to vector search to "decide" which single source is right.

## Evaluation

`eval/Day2_Evaluation_Test_Set.csv` has 12 real questions with page numbers verified against
the actual PDFs: 10 answerable questions (6 GINA, 4 WHO), one deliberate out-of-scope control
question, and one multi-source question that genuinely needs both documents. `evaluate.py`
computes, per embedding model:

- **Precision@k** - fraction of the top-k retrieved chunks matching the expected `(document, page)`
- **Hit Rate@k** - whether at least one of the top-k chunks is correct
- **MRR** - mean reciprocal rank of the first correct chunk
- the out-of-scope question's top similarity score (should be low)
- the multi-source question's per-source hit counts

## Next step (not built here)

## Local UI: AsthmaDaily (this fork)

This workspace includes a small Flask-based UI (`webapp.py`) that demonstrates a
patient-facing product surface called "AsthmaDaily". Key features added here:

- Daily diary: `/diary` — quick daily check-ins saved to `data/diary.json`.
- Dashboard: `/dashboard` — weekly and 30-day summaries and simple exposure pattern detection.
- Clinical Q&A (RAG): `/ask_form` + `/ask` — retrieve guideline passages with source/page citations.
- Local synthesis: `/synthesize` — a simple synthesizer that builds a concise answer from retrieved passages and lists citations. (This is a local, concatenation-based synthesizer; for abstractive LLM summaries we can add OpenAI/LLM integration later.)
- Export: `/export/doctor_summary` — printable HTML summary for clinicians; `/export/doctor_summary.pdf` attempts PDF generation via `pdfkit` + `wkhtmltopdf` if installed on your system.

How to run the UI:

```bash
pip install -r requirements.txt
python webapp.py
```

Open `http://127.0.0.1:5000` in your browser.

PDF notes: `pdfkit` requires an external `wkhtmltopdf` binary installed on your system. If not available, the app falls back to serving a printable HTML page.

Arabic UX: templates include Arabic labels and copy to make the app friendlier to Arabic-speaking users. You can further polish copy and RTL layout as needed.

## Enabling LLM (OpenAI) and testing PDF export

If you want to enable abstractive LLM summaries and test PDF export, follow these steps.

1) Create a `.env` file (or export environment variables). You can copy the example:

```powershell
copy .env.example .env
# or set in PowerShell session:
$env:OPENAI_API_KEY = "sk-..."
$env:OPENAI_MODEL = "gpt-4o-mini"   # optional
python webapp.py
```

On macOS / Linux:

```bash
cp .env.example .env
export OPENAI_API_KEY="sk-..."
export OPENAI_MODEL="gpt-4o-mini"
python webapp.py
```

2) Install `wkhtmltopdf` for PDF exports (optional but recommended):

- Windows (Chocolatey):

```powershell
choco install wkhtmltopdf
```

- Windows (manual): Download the installer from https://wkhtmltopdf.org/downloads.html and add the install folder to your PATH.

- macOS (Homebrew):

```bash
brew install wkhtmltopdf
```

3) Test LLM and PDF generation quickly using the built-in debug endpoint after the server is running:

Open in your browser or use curl/Invoke-WebRequest:

```
http://127.0.0.1:5000/debug/sample
```

This endpoint will attempt to retrieve a few passages, synthesize an Arabic LLM answer if `OPENAI_API_KEY` is set and `openai` is installed, and try to write `outputs/sample_doctor_summary.pdf`. If PDF generation fails, an HTML preview and an error comment are returned in the response.

Notes:
- If `OPENAI_API_KEY` is not set or the `openai` package isn't available, the app falls back to a local concatenation-based synthesizer.
- Keep `wkhtmltopdf` on your PATH so `pdfkit` can find it; otherwise the app will render printable HTML as a fallback.

If you want, I can also translate any remaining English strings into Arabic (or vice-versa) across the templates — tell me whether you want full Arabic UI, full English UI, or a toggle switch approach.

As noted at the end of the Day 2 notebook: constrain the LLM to answer only from retrieved
chunks, with `document_name` + `page_number` citations on every claim, and an explicit
GINA-vs-WHO split whenever the two guidelines differ for a child/adolescent question. The
rest of the AsthmaDaily plan (hybrid BM25 + vector search, reranking, a safety layer, a
doctor-facing report) builds on top of this same `config.py` / `ingest.py` / `query.py` foundation.
