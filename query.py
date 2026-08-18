"""
AsthmaDaily RAG - Query / Retrieval
=====================================
load_index() + retrieve() like the original, extended to accept a metadata
filter (source / age_group / topic) for source-aware retrieval, and to work
against any of the embedding models in config.EMBEDDING_MODELS (each model
gets its own persisted collection - see ingest.build_index).

    retrieve(vectordb, question, k=5, source="WHO")           # WHO only
    retrieve(vectordb, question, k=5, age_group="0-19")        # children-specific
    retrieve(vectordb, question, k=5, topic="exacerbation")    # topic filter
"""
from pathlib import Path

import config
from ingest import get_embedding_function


def load_index(model_config: dict = None, persist_directory: Path = None):
    from langchain_chroma import Chroma

    if model_config is None:
        model_config = next(
            m for m in config.EMBEDDING_MODELS if m["id"] == config.DEFAULT_EMBEDDING_MODEL_ID
        )
    collection_name = f"{config.COLLECTION_NAME_PREFIX}_{model_config['id']}"
    persist_directory = persist_directory or (config.VECTOR_DB_DIR / model_config["id"])
    embed_fn = get_embedding_function(model_config)  # loads the already-fitted backend

    return Chroma(
        collection_name=collection_name,
        embedding_function=embed_fn,
        persist_directory=str(persist_directory),
    )


def _build_where(source=None, age_group=None):
    """Builds a simple ChromaDB filter. Note: the 'topics' field is stored as
    a comma-separated string, so topic filtering happens as a post-filter
    rather than inside the where clause itself."""
    clauses = []
    if source:
        clauses.append({"source": source})
    if age_group:
        clauses.append({"age_group": age_group})
    if not clauses:
        return None
    if len(clauses) == 1:
        return clauses[0]
    return {"$and": clauses}


def retrieve(vectordb, question: str, k: int = config.TOP_K_DEFAULT, source: str = None,
             age_group: str = None, topic: str = None):
    """Returns a list of (Document, score). If topic is given, results are
    post-filtered on chunk.metadata['topics']."""
    where = _build_where(source=source, age_group=age_group)
    fetch_k = k * 3 if topic else k  # fetch extra so post-filtering doesn't starve results

    results = vectordb.similarity_search_with_relevance_scores(question, k=fetch_k, filter=where)

    if topic:
        results = [(doc, score) for doc, score in results if topic in doc.metadata.get("topics", "")]

    return results[:k]


def source_aware_retrieve(vectordb, question: str, age_group: str = "all", k: int = config.TOP_K_DEFAULT):
    """Implements the 'query understanding -> metadata filtering' pattern:
    if the question concerns a child/adolescent (age_group='0-19'), pull from
    BOTH GINA and WHO and keep results separated by source. Otherwise GINA is
    the primary (and only) source."""
    if age_group == "0-19":
        gina_results = retrieve(vectordb, question, k=k, source="GINA")
        who_results = retrieve(vectordb, question, k=k, source="WHO")
        return {"GINA": gina_results, "WHO": who_results}
    return {"GINA": retrieve(vectordb, question, k=k, source="GINA")}


if __name__ == "__main__":
    vectordb = load_index()

    print("=== General question (adults) - GINA only as primary source ===")
    q1 = "What factors are used to assess asthma control?"
    for doc, score in retrieve(vectordb, q1, k=3, source="GINA"):
        print(f"  score={score:.3f} | {doc.metadata['document_name']} p.{doc.metadata['page_number']} "
              f"| topics={doc.metadata['topics']}")
        print(f"    {doc.page_content[:150].strip()}...")

    print("\n=== Children question - GINA + WHO fused ===")
    q2 = "What is the recommended treatment approach for asthma in children and adolescents?"
    fused = source_aware_retrieve(vectordb, q2, age_group="0-19", k=3)
    for src, results in fused.items():
        print(f"  -- {src} --")
        for doc, score in results:
            print(f"    score={score:.3f} | p.{doc.metadata['page_number']} | "
                  f"{doc.page_content[:120].strip()}...")
