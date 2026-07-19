"""Crossref scanner: date parsing, JATS stripping, record building (network mocked)."""

from datetime import date

from cpi import pcm as pcm_mod
from cpi import store
from cpi.scanners import crossref


def test_pub_date_handles_partial_date_parts():
    assert crossref._pub_date({"published": {"date-parts": [[2026, 7, 18]]}}) == date(2026, 7, 18)
    assert crossref._pub_date({"published": {"date-parts": [[2026, 7]]}}) == date(2026, 7, 1)
    assert crossref._pub_date({"published": {"date-parts": [[2026]]}}) == date(2026, 1, 1)
    assert crossref._pub_date({"published": {"date-parts": [[None]]}}) is None
    assert crossref._pub_date({}) is None


def test_strip_jats_removes_xml_tags():
    jats = "<jats:p>Detecting <jats:italic>anomalies</jats:italic> in pipelines.</jats:p>"
    assert "anomalies" in crossref._strip_jats(jats)
    assert "<" not in crossref._strip_jats(jats)


class _FakeResponse:
    def raise_for_status(self):
        pass

    def json(self):
        return {"message": {"items": [
            {"title": ["Root cause analysis with  large language models"],
             "URL": "https://doi.org/10.1234/example.1",
             "abstract": "<jats:p>An abstract.</jats:p>",
             "published": {"date-parts": [[2026, 7, 10]]}},
            {"title": [], "URL": "https://doi.org/10.1234/untitled"},  # skipped
        ]}}


def test_scan_builds_records_from_api_items(cpi_home, monkeypatch):
    monkeypatch.setattr(crossref.httpx, "get", lambda *a, **k: _FakeResponse())
    monkeypatch.setattr(crossref.base, "polite_sleep", lambda: None)

    records = crossref.scan(pcm_mod.load(), {"crossref": {}}, use_llm=False)
    # one record per theme (same fake payload; URL dedupe collapses repeats)
    assert len(records) == 1
    rec = records[0]
    assert rec.source_name == "Crossref"
    assert rec.title == "Root cause analysis with large language models"
    assert rec.published_date == date(2026, 7, 10)
    assert store.get_signal(rec.id) is not None
    # scan health row written
    health = {h["source"]: h for h in store.source_health()}
    assert health["Crossref"]["last_new"] == 1
