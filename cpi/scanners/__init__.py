from . import arxiv, funding, hn, rss  # noqa: F401

SCANNERS = {"arxiv": arxiv, "rss": rss, "hn": hn, "funding": funding}
