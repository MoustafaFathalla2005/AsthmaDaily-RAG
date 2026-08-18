"""
AsthmaDaily RAG - Embedding backends
=====================================
Two kinds of embedding function, both exposing the same interface LangChain /
Chroma expect: .embed_documents(list[str]) -> list[list[float]] and
.embed_query(str) -> list[float].

1. HuggingFace sentence-transformer models (real deliverable) - require
   downloading model weights from huggingface.co the first time they run.
2. An offline TF-IDF + Truncated SVD (LSA) baseline - no downloads, always
   runnable, used to validate the pipeline end-to-end in network-restricted
   environments and as a lower-bound comparison point.
"""
import pickle
from pathlib import Path

import config


def get_embedding_function(model_config: dict, corpus_texts=None, fit_dir: Path = None):
    """Dispatch to the right backend based on model_config['type'].

    corpus_texts / fit_dir are only used by the tfidf_svd backend, which has
    to be *fit* on a corpus (unlike a pretrained transformer model).
    """
    if model_config["type"] == "huggingface":
        from langchain_huggingface import HuggingFaceEmbeddings
        return HuggingFaceEmbeddings(model_name=model_config["model_name"])

    if model_config["type"] == "tfidf_svd":
        return TfidfSvdEmbeddings(
            dim=model_config.get("dim", 384),
            fit_dir=fit_dir or (config.OUTPUTS_DIR / "tfidf_svd_model"),
            corpus_texts=corpus_texts,
        )

    raise ValueError(f"Unknown embedding model type: {model_config['type']}")


class TfidfSvdEmbeddings:
    """Offline embedding backend: TF-IDF vectorization followed by Truncated
    SVD (i.e. classic Latent Semantic Analysis) to get dense fixed-size
    vectors comparable in shape to a real sentence-transformer output.

    Must be *fit* once on the project's own corpus (all chunk texts) before
    use. The fitted vectorizer/SVD are persisted to disk so query-time calls
    reuse the exact same fit instead of re-fitting per query.
    """

    def __init__(self, dim: int = 384, fit_dir: Path = None, corpus_texts=None):
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.decomposition import TruncatedSVD

        self.dim = dim
        self.fit_dir = Path(fit_dir) if fit_dir else Path("tfidf_svd_model")
        self.fit_dir.mkdir(parents=True, exist_ok=True)
        vec_path = self.fit_dir / "vectorizer.pkl"
        svd_path = self.fit_dir / "svd.pkl"

        if corpus_texts is not None:
            self.vectorizer = TfidfVectorizer(
                max_features=20000, ngram_range=(1, 2), stop_words="english",
                sublinear_tf=True,
            )
            tfidf_matrix = self.vectorizer.fit_transform(corpus_texts)
            n_components = min(dim, tfidf_matrix.shape[1] - 1, tfidf_matrix.shape[0] - 1)
            self.svd = TruncatedSVD(n_components=n_components, random_state=42)
            self.svd.fit(tfidf_matrix)
            with open(vec_path, "wb") as f:
                pickle.dump(self.vectorizer, f)
            with open(svd_path, "wb") as f:
                pickle.dump(self.svd, f)
        elif vec_path.exists() and svd_path.exists():
            with open(vec_path, "rb") as f:
                self.vectorizer = pickle.load(f)
            with open(svd_path, "rb") as f:
                self.svd = pickle.load(f)
        else:
            raise FileNotFoundError(
                f"No fitted TF-IDF/SVD model found at {self.fit_dir}. "
                "Pass corpus_texts the first time to fit it."
            )

    def _embed(self, texts):
        tfidf_matrix = self.vectorizer.transform(texts)
        vectors = self.svd.transform(tfidf_matrix)
        return vectors.tolist()

    def embed_documents(self, texts):
        return self._embed(texts)

    def embed_query(self, text):
        return self._embed([text])[0]
