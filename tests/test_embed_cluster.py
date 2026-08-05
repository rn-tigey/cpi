"""Embedding-based clustering with TF-IDF fallback."""

from cpi.pipeline import cluster


def test_dry_run_never_calls_the_embeddings_api(monkeypatch):
    # conftest forces CPI_DRY_RUN=1 - even with a key set, no network.
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    assert cluster._embeddings(["a", "b"]) is None


def test_no_key_falls_back_to_tfidf(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    assert cluster._embeddings(["a", "b"]) is None
    # and clustering still works end to end on the TF-IDF path
    labels = cluster._cluster_texts(["anomaly detection paper", "unrelated bakery news"])
    assert len(labels) == 2


def test_embeddings_cluster_by_vector_similarity(monkeypatch):
    vectors = {
        "alpha topic one": [1.0, 0.0],
        "alpha topic two": [0.99, 0.01],
        "beta topic": [0.0, 1.0],
    }
    monkeypatch.setattr(cluster, "_embeddings", lambda texts: [vectors[t] for t in texts])
    labels = cluster._cluster_texts(list(vectors))
    assert labels[0] == labels[1]      # near-identical vectors merge
    assert labels[0] != labels[2]      # orthogonal vector stays separate


def test_explicit_threshold_overrides_embed_default(monkeypatch):
    vectors = {"a": [1.0, 0.0], "b": [0.8, 0.6]}  # distance ~0.2
    monkeypatch.setattr(cluster, "_embeddings", lambda texts: [vectors[t] for t in texts])
    assert cluster._cluster_texts(list(vectors), threshold=0.1)[0] != \
        cluster._cluster_texts(list(vectors), threshold=0.1)[1]
    merged = cluster._cluster_texts(list(vectors), threshold=0.5)
    assert merged[0] == merged[1]
