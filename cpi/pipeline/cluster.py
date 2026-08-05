"""Stage 4a - Cluster advanced signals into CandidateIdeas.

Embedding-based (semantic) when an OPENAI_API_KEY is available - measured to
group related signals far better than word overlap, at a cost of fractions of
a cent per cycle. Falls back to TF-IDF word overlap when keyless, offline, or
in dry-run mode, so no key is ever required.
"""

from __future__ import annotations

import os
from datetime import date

from .. import llm, store
from ..models import CandidateIdea

COSINE_DISTANCE_THRESHOLD = 0.8  # TF-IDF: merge below this distance (1 - similarity)
EMBED_DISTANCE_THRESHOLD = 0.6   # embeddings measure much tighter; 0.8 would over-merge
EMBED_MODEL = "text-embedding-3-small"  # measured as good as -large here, at 1/6 the price


def _embeddings(texts: list[str]) -> list[list[float]] | None:
    """One vector per text via the OpenAI embeddings API; None means fall back."""
    if llm.dry_run() or not os.environ.get("OPENAI_API_KEY"):
        return None
    try:
        from openai import OpenAI
    except ImportError:
        return None
    try:
        resp = OpenAI().embeddings.create(model=EMBED_MODEL, input=texts)
    except Exception as exc:  # any API failure - clustering must still work
        print(f"  embeddings unavailable ({exc.__class__.__name__}) - using TF-IDF")
        return None
    llm._log_usage("embed", EMBED_MODEL, resp.usage)
    return [d.embedding for d in resp.data]


def _cluster_texts(texts: list[str], threshold: float | None = None) -> list[int]:
    """Return a cluster label per text. Single text -> [0].

    Raise the threshold to merge more aggressively (fewer, broader ideas);
    lower it for tighter clusters. TF-IDF rarely merges at high volume - if
    you get almost one idea per signal, try `cpi cluster --threshold 0.9+`
    (or set an OPENAI_API_KEY to get semantic clustering).
    """
    if len(texts) == 1:
        return [0]
    from sklearn.cluster import AgglomerativeClustering

    vectors = _embeddings(texts)
    if vectors is not None:
        matrix, default = vectors, EMBED_DISTANCE_THRESHOLD
        print(f"  clustering by embeddings ({EMBED_MODEL})")
    else:
        from sklearn.feature_extraction.text import TfidfVectorizer

        matrix = TfidfVectorizer(stop_words="english", max_features=5000).fit_transform(texts).toarray()
        default = COSINE_DISTANCE_THRESHOLD
    model = AgglomerativeClustering(
        n_clusters=None,
        distance_threshold=threshold if threshold is not None else default,
        metric="cosine", linkage="average",
    )
    return list(model.fit_predict(matrix))


def run(threshold: float | None = None) -> list[CandidateIdea]:
    """Cluster advanced-but-unclustered signals; returns new ideas."""
    advanced = store.signals_by_disposition("advance")
    already = store.clustered_signal_ids()
    fresh = [s for s in advanced if s.id not in already]
    if not fresh:
        return []

    labels = _cluster_texts([f"{s.title}. {s.summary}" for s in fresh], threshold=threshold)

    existing = sum(1 for _ in store.iter_ideas())
    stamp = date.today().strftime("%Y%m")
    ideas: list[CandidateIdea] = []
    for label in sorted(set(labels)):
        members = [s for s, lab in zip(fresh, labels) if lab == label]
        rep = max(members, key=lambda s: len(s.summary))  # richest signal names the idea
        existing += 1
        idea = CandidateIdea(
            id=f"idea-{stamp}-{existing:03d}",
            title=rep.title[:120],
            summary=" | ".join(f"[{s.source_name}] {s.title}" for s in members[:6]),
            signal_ids=[s.id for s in members],
            created_date=date.today(),
        )
        store.save_idea(idea)
        ideas.append(idea)
        print(f"  {idea.id}: {len(members)} signal(s) - {idea.title[:60]}")
    return ideas
