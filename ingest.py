"""
AsthmaDaily RAG - Ingestion
============================
Pipeline: load_pdfs -> preprocess_pages -> chunk_documents -> build_index,
same shape as the original hackathon ingest.py, extended to:
  - handle multiple source PDFs (GINA + WHO) with source-aware metadata
  - apply real text preprocessing before chunking (see preprocess.py)
  - support several embedding backends (see embeddings.py)
  - save the output of every step to outputs/ so each stage is inspectable
    and reproducible without re-running the whole pipeline.
"""
import json
from pathlib import Path

from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter

import config
from preprocess import preprocess_pages


def _save_pages_json(pages, out_path: Path):
    data = [
        {"metadata": p.metadata, "content": p.page_content, "n_chars": len(p.page_content)}
        for p in pages
    ]
    out_path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def _save_chunks_json(chunks, out_path: Path):
    data = [
        {"metadata": c.metadata, "content": c.page_content, "n_chars": len(c.page_content)}
        for c in chunks
    ]
    out_path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def load_pdfs(data_dir: Path = config.DATA_DIR, save_output: bool = True):
    """Loads every PDF in data/, stamps source-registry metadata onto each
    page (document_name, source, year, role, age_group, 1-indexed page_number),
    and optionally saves the raw (pre-cleaning) pages to
    outputs/01_pages_raw.json for inspection.
    """
    all_pages = []
    pdf_files = sorted(data_dir.glob("*.pdf"))
    if not pdf_files:
        raise FileNotFoundError(f"No PDFs found in {data_dir}")

    for pdf_path in pdf_files:
        meta = config.SOURCE_REGISTRY.get(pdf_path.name)
        if meta is None:
            print(f"  WARNING: {pdf_path.name} is not registered in SOURCE_REGISTRY "
                  f"(config.py) - it will be loaded without accurate source metadata.")
            meta = {"document_name": pdf_path.stem, "source": "UNKNOWN", "year": None,
                     "role": "unknown", "age_group": "all", "full_title": pdf_path.stem}

        loader = PyPDFLoader(str(pdf_path))
        raw_pages = loader.load()

        for page in raw_pages:
            zero_indexed_page = page.metadata.get("page", 0)
            page.metadata.update({
                "document_name": meta["document_name"],
                "source": meta["source"],
                "year": meta["year"],
                "role": meta["role"],
                "age_group": meta["age_group"],
                "page_number": zero_indexed_page + 1,
                "file_name": pdf_path.name,
            })

        all_pages.extend(raw_pages)
        print(f"  loaded {meta['document_name']} ({meta['source']}, {meta['role']}): "
              f"{len(raw_pages)} pages")

    if save_output:
        _save_pages_json(all_pages, config.OUTPUTS_DIR / "01_pages_raw.json")
        print(f"  saved -> outputs/01_pages_raw.json ({len(all_pages)} pages)")

    return all_pages


def preprocess(pages, save_output: bool = True):
    """Applies preprocess.preprocess_pages (hyphenation fix, unicode
    normalization, whitespace cleanup, boilerplate/header-footer removal)
    and saves the cleaned pages to outputs/02_pages_preprocessed.json.
    """
    pages = preprocess_pages(pages)
    if save_output:
        _save_pages_json(pages, config.OUTPUTS_DIR / "02_pages_preprocessed.json")
        print(f"  saved -> outputs/02_pages_preprocessed.json ({len(pages)} pages)")
    return pages


def _classify_topics(text: str):
    text_lower = text.lower()
    hits = []
    for topic, keywords in config.TOPIC_KEYWORDS.items():
        if any(kw.lower() in text_lower for kw in keywords):
            hits.append(topic)
    return hits or ["general"]


def chunk_documents(pages, chunk_size: int = config.CHUNK_SIZE,
                     chunk_overlap: int = config.CHUNK_OVERLAP, save_output: bool = True):
    """Section-aware chunking with overlap (RecursiveCharacterTextSplitter,
    paragraph/sentence-aware separators), then attaches a stable chunk_id and
    a simple keyword-based topic tag to every chunk. Saves the result to
    outputs/03_chunks.json.

    chunk_size / chunk_overlap are in approximate tokens and multiplied by
    CHARS_PER_TOKEN to get characters (same convention as the original
    hackathon notebooks, kept for compatibility).
    """
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size * config.CHARS_PER_TOKEN,
        chunk_overlap=chunk_overlap * config.CHARS_PER_TOKEN,
        separators=["\n\n", "\n", ". ", " ", ""],
    )
    chunks = splitter.split_documents(pages)

    for i, chunk in enumerate(chunks):
        chunk.metadata["chunk_id"] = (
            f"{chunk.metadata.get('source', 'UNK')}_"
            f"p{chunk.metadata.get('page_number', 0)}_{i}"
        )
        topics = _classify_topics(chunk.page_content)
        # ChromaDB metadata must be scalar -> store topics as a comma-separated string
        chunk.metadata["topics"] = ",".join(topics)

    if save_output:
        _save_chunks_json(chunks, config.OUTPUTS_DIR / "03_chunks.json")
        print(f"  saved -> outputs/03_chunks.json ({len(chunks)} chunks, "
              f"chunk_size={chunk_size} tokens, overlap={chunk_overlap} tokens)")

    return chunks


def get_embedding_function(model_config: dict = None, corpus_texts=None):
    """Thin wrapper around embeddings.get_embedding_function so existing
    callers (and the original notebooks) that just want "the" embedding
    function keep working without knowing about the multi-model registry.
    """
    from embeddings import get_embedding_function as _get
    if model_config is None:
        model_config = next(
            m for m in config.EMBEDDING_MODELS if m["id"] == config.DEFAULT_EMBEDDING_MODEL_ID
        )
    fit_dir = config.OUTPUTS_DIR / f"fitted_{model_config['id']}"
    return _get(model_config, corpus_texts=corpus_texts, fit_dir=fit_dir)


def build_index(chunks, model_config: dict = None, persist_directory: Path = None,
                 save_output: bool = True):
    """Embeds every chunk with the given embedding model and stores it in a
    persisted ChromaDB collection (one collection per embedding model, so
    several models' indexes can coexist for comparison).
    """
    from langchain_chroma import Chroma

    if model_config is None:
        model_config = next(
            m for m in config.EMBEDDING_MODELS if m["id"] == config.DEFAULT_EMBEDDING_MODEL_ID
        )
    collection_name = f"{config.COLLECTION_NAME_PREFIX}_{model_config['id']}"
    persist_directory = persist_directory or (config.VECTOR_DB_DIR / model_config["id"])

    corpus_texts = [c.page_content for c in chunks]
    embed_fn = get_embedding_function(model_config, corpus_texts=corpus_texts)

    vectordb = Chroma.from_documents(
        documents=chunks,
        embedding=embed_fn,
        collection_name=collection_name,
        persist_directory=str(persist_directory),
    )
    print(f"  indexed {len(chunks)} chunks into ChromaDB collection "
          f"'{collection_name}' (model={model_config['id']})")

    if save_output:
        summary = {
            "embedding_model_id": model_config["id"],
            "model_name": model_config["model_name"],
            "n_chunks_indexed": len(chunks),
            "collection_name": collection_name,
            "persist_directory": str(persist_directory),
        }
        out_path = config.OUTPUTS_DIR / f"04_index_summary_{model_config['id']}.json"
        out_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    return vectordb


if __name__ == "__main__":
    print("1/4 - Loading PDFs (GINA + WHO) ...")
    pages = load_pdfs()

    print("\n2/4 - Preprocessing (hyphenation fix, cleanup, boilerplate removal) ...")
    pages = preprocess(pages)

    print("\n3/4 - Chunking with overlap + metadata enrichment ...")
    chunks = chunk_documents(pages)
    from collections import Counter
    by_source = Counter(c.metadata["source"] for c in chunks)
    print(f"  total: {len(chunks)} chunks | by source: {dict(by_source)}")

    print("\n4/4 - Building the index (default embedding model) ...")
    vectordb = build_index(chunks)

    print("\nDone. Try: python query.py")
