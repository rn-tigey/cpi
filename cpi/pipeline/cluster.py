"""Stage 4a - Cluster advanced signals into CandidateIdeas (TF-IDF cosine)."""

from __future__ import annotations

from datetime import date

from .. import store
from ..models import CandidateIdea

COSINE_DISTANCE_THRESHOLD = 0.8  # merge below this distance (1 - similarity)


def _cluster_texts(texts: list[str]) -> list[int]:
    """Return a cluster label per text. Single text -> [0]."""
    if len(texts) == 1:
        return [0]
    from sklearn.cluster import AgglomerativeClustering
    from sklearn.feature_extraction.text import TfidfVectorizer

    matrix = TfidfVectorizer(stop_words="english", max_features=5000).fit_transform(texts)
    model = AgglomerativeClustering(
        n_clusters=None, distance_threshold=COSINE_DISTANCE_THRESHOLD,
        metric="cosine", linkage="average",
    )
    return list(model.fit_predict(matrix.toarray()))


def run() -> list[CandidateIdea]:
    """Cluster advanced-but-unclustered signals; returns new ideas."""
    advanced = store.signals_by_disposition("advance")
    already = store.clustered_signal_ids()
    fresh = [s for s in advanced if s.id not in already]
    if not fresh:
        return []

    labels = _cluster_texts([f"{s.title}. {s.summary}" for s in fresh])

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
