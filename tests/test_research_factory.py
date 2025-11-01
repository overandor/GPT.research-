from pathlib import Path
from typing import Dict, List

import pytest

from src.api.research_factory import (
    ResearchFactory,
    fetch_recent_papers,
)

EXPECTED_REFERENCES = [
    {
        "title": "Deterministic Reference",
        "year": 2024,
        "authors": "Researcher One, Researcher Two",
        "link": "https://example.com/paper",
        "provider": "Test",
        "source_id": "test-ref",
        "accessed": "2024-01-01T00:00:00+00:00",
    }
]


def _stub_references(query: str, max_items: int) -> List[Dict[str, str]]:
    return list(EXPECTED_REFERENCES)


def test_research_factory_generates_real_metrics() -> None:
    dataset_path = Path(__file__).resolve().parents[1] / "data" / "real_experiment.csv"
    factory = ResearchFactory(dataset_path=dataset_path, reference_fetcher=_stub_references)

    papers = factory.generate_research_with_verification([
        "Vehicle weight inversely correlates with MPG",
    ])

    assert len(papers) == 1
    paper = papers[0]

    metrics = paper["metrics"]
    assert pytest.approx(metrics["effect_size"], rel=1e-6) == -5.344472
    assert pytest.approx(metrics["p_value"], rel=1e-6) == 1.293959e-10
    assert pytest.approx(metrics["r_squared"], rel=1e-6) == 0.7528327936582646
    assert metrics["sample_size"] == 32

    assert paper["verification"]["replicated"] is True
    assert paper["references"] == EXPECTED_REFERENCES


def test_fetch_recent_papers_deduplicates_and_orders(monkeypatch: pytest.MonkeyPatch) -> None:
    class MockResponse:
        def __init__(self, *, ok: bool = True, json_data=None, text: str = "") -> None:
            self.ok = ok
            self._json = json_data or {}
            self.text = text

        def json(self):
            return self._json

    def fake_get(url: str, timeout: int):  # type: ignore[override]
        if "crossref" in url:
            return MockResponse(
                json_data={
                    "message": {
                        "items": [
                            {
                                "title": ["Crossref Study"],
                                "DOI": "10.1000/crossref",
                                "author": [
                                    {"given": "Ada", "family": "Lovelace"}
                                ],
                                "published-print": {"date-parts": [[2024]]},
                            }
                        ]
                    }
                }
            )
        if "arxiv" in url:
            return MockResponse(
                text=(
                    "<?xml version='1.0' encoding='UTF-8'?>\n"
                    "<feed xmlns='http://www.w3.org/2005/Atom'>\n"
                    "  <entry>\n"
                    "    <id>http://arxiv.org/abs/1234.5678v1</id>\n"
                    "    <title>Arxiv Study</title>\n"
                    "    <published>2024-02-01T00:00:00Z</published>\n"
                    "    <author><name>Arxiv Author</name></author>\n"
                    "    <link rel='alternate' type='text/html' href='https://arxiv.org/abs/1234.5678v1'/>\n"
                    "  </entry>\n"
                    "</feed>\n"
                )
            )
        return MockResponse(
            json_data={
                "data": [
                    {
                        "title": "Duplicate Semantic",
                        "year": 2024,
                        "authors": [{"name": "Semantic Author"}],
                        "url": "https://example.com/duplicate",
                        "externalIds": {"DOI": "10.1000/crossref"},
                    },
                    {
                        "title": "Unique Semantic",
                        "year": 2023,
                        "authors": [{"name": "Unique Author"}],
                        "url": "https://example.com/unique",
                        "externalIds": {},
                    },
                ]
            }
        )

    monkeypatch.setattr("src.api.research_factory.requests.get", fake_get)

    results = fetch_recent_papers("weight efficiency", max_items=3)
    assert len(results) == 3
    assert results[0]["provider"] == "Crossref"
    assert results[1]["provider"] == "arXiv"
    assert results[2]["provider"] == "Semantic Scholar"
    assert results[0]["authors"] == "Ada Lovelace"
    assert results[2]["authors"] == "Unique Author"
