"""
AsthmaDaily RAG - Configuration
================================
Everything tunable lives here: file paths, chunking settings, the embedding
models under comparison, and the Source Registry that ties every PDF to its
metadata (source, year, age_group) so retrieval is source-aware from the
first step, not bolted on afterward.
"""
from pathlib import Path

BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
OUTPUTS_DIR = BASE_DIR / "outputs"
VECTOR_DB_DIR = BASE_DIR / "vector_db"
EVAL_DIR = BASE_DIR / "eval"

for d in (OUTPUTS_DIR, VECTOR_DB_DIR):
    d.mkdir(exist_ok=True)

# --------------------------------------------------------------- Source Registry
# Key = filename inside data/. Every source has an explicit role (primary /
# supporting), an age group, and a human-readable title. This is the metadata
# stamped onto every page/chunk that comes from that file.
SOURCE_REGISTRY = {
    "GINA_2026.pdf": {
        "document_name": "GINA 2026",
        "source": "GINA",
        "year": 2026,
        "role": "primary",          # main reference - comprehensive asthma management, all ages
        "age_group": "all",
        "full_title": "Global Strategy for Asthma Management and Prevention - 2026 Update",
    },
    "WHO_2026_Asthma_Children_Adolescents.pdf": {
        "document_name": "WHO 2026",
        "source": "WHO",
        "year": 2026,
        "role": "supporting",       # supporting reference - specific to children/adolescents
        "age_group": "0-19",
        "full_title": "WHO consolidated guidelines for the management of common childhood "
                       "illness: Management of asthma in children and adolescents and "
                       "bronchiolitis in infants and young children",
    },
}

# --------------------------------------------------------------- Chunking
# Values are in approximate "tokens" and multiplied by ~4 in ingest.py to
# convert to characters (same convention as the original hackathon notebooks).
CHUNK_SIZE = 400
CHUNK_OVERLAP = 50
CHARS_PER_TOKEN = 4

# --------------------------------------------------------------- Embedding models under comparison
# type="huggingface"  -> real sentence-transformer model, downloaded from the
#                         HuggingFace Hub the first time it runs (needs internet
#                         access to huggingface.co).
# type="tfidf_svd"     -> fully offline baseline (TF-IDF + Truncated SVD / LSA).
#                         No downloads required, always runnable, used here as
#                         a sanity-check / fallback so the pipeline can be
#                         executed end-to-end in network-restricted environments.
EMBEDDING_MODELS = [
    {
        "id": "minilm-l6-v2",
        "type": "huggingface",
        "model_name": "sentence-transformers/all-MiniLM-L6-v2",
        "dim": 384,
        "description": "Light, fast general-purpose sentence embedding model. "
                        "Good default baseline for RAG prototypes.",
    },
    {
        "id": "bge-small-en",
        "type": "huggingface",
        "model_name": "BAAI/bge-small-en-v1.5",
        "dim": 384,
        "description": "Retrieval-tuned embedding model (trained with contrastive "
                        "retrieval objectives). Usually stronger than MiniLM on "
                        "question-to-passage retrieval tasks like ours.",
    },
    {
        "id": "gte-small",
        "type": "huggingface",
        "model_name": "thenlper/gte-small",
        "dim": 384,
        "description": "General Text Embeddings model, competitive with bge-small "
                        "on retrieval benchmarks, included as a third comparison point.",
    },
    {
        "id": "tfidf-svd",
        "type": "tfidf_svd",
        "model_name": "tfidf+truncated_svd(384)",
        "dim": 384,
        "description": "Offline TF-IDF + LSA baseline (no internet/model download "
                        "required). Fit on the project's own corpus. Used to validate "
                        "the pipeline end-to-end and as a lower-bound comparison point "
                        "against the transformer-based models above.",
    },
]

# Which embedding model is currently "active" for query.py / plain retrieval
DEFAULT_EMBEDDING_MODEL_ID = "tfidf-svd"

COLLECTION_NAME_PREFIX = "asthmadaily_gina_who_2026"

# --------------------------------------------------------------- Retrieval defaults
TOP_K_DEFAULT = 5

# --------------------------------------------------------------- Simple topic classifier
# Lightweight keyword-based classifier (instead of loading a full classification
# model) - good enough for smarter metadata filtering than "treat every page
# the same way".
TOPIC_KEYWORDS = {
    "asthma_control":       ["asthma control", "symptom control", "well-controlled", "ACT", "ACQ"],
    "triggers":              ["trigger", "allergen", "air pollution", "smoke", "exercise-induced", "cold air"],
    "risk_factors":          ["risk factor", "risk of exacerbation"],
    "exacerbation":          ["exacerbation", "flare-up", "acute asthma", "emergency"],
    "medication":            ["ICS", "SABA", "LABA", "MART", "corticosteroid", "bronchodilator", "inhaler"],
    "monitoring":            ["peak flow", "spirometry", "FEV1", "PEF", "monitoring"],
    "prevention":            ["prevention", "avoidance", "vaccination"],
    "children_adolescents":  ["children", "adolescent", "pediatric", "paediatric", "infant"],
    "diagnosis":             ["diagnosis", "diagnostic", "wheeze", "differential"],
}
