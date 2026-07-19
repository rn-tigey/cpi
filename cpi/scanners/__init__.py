from . import arxiv, crossref, funding, hn, rss  # noqa: F401

SCANNERS = {"arxiv": arxiv, "crossref": crossref, "rss": rss, "hn": hn, "funding": funding}
