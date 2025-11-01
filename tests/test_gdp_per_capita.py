from decimal import Decimal

import pytest

from src.kpi_engine.economic_singularity import (
    GDPPerCapitaAnalyzer,
    GDPPerCapitaDataset,
    GDPRecord,
    build_analyzer,
)


@pytest.fixture
def sample_records():
    return [
        GDPRecord(
            country="Exampleland",
            year=2020,
            gdp_usd=Decimal("1200000000000"),
            population=50000000,
        ),
        GDPRecord(
            country="Exampleland",
            year=2021,
            gdp_usd=Decimal("1260000000000"),
            population=50500000,
        ),
        GDPRecord(
            country="Exampleland",
            year=2022,
            gdp_usd=Decimal("1350000000000"),
            population=50900000,
        ),
        GDPRecord(
            country="Volatility Republic",
            year=2020,
            gdp_usd=Decimal("400000000000"),
            population=15000000,
        ),
        GDPRecord(
            country="Volatility Republic",
            year=2021,
            gdp_usd=Decimal("620000000000"),
            population=15200000,
        ),
    ]


def test_per_capita_series(sample_records):
    analyzer = build_analyzer(sample_records)
    series = analyzer.per_capita_series("Exampleland")
    assert series == [
        (2020, Decimal("24000.00")),
        (2021, Decimal("24950.50")),
        (2022, Decimal("26522.59")),
    ]


def test_growth_rates(sample_records):
    analyzer = build_analyzer(sample_records)
    growth = analyzer.growth_rates("Exampleland")
    assert growth == [
        (2021, Decimal("0.0396")),
        (2022, Decimal("0.0630")),
    ]


def test_average_per_capita(sample_records):
    dataset = GDPPerCapitaDataset(sample_records)
    analyzer = GDPPerCapitaAnalyzer(dataset)
    average = analyzer.average_per_capita("Exampleland")
    assert average == Decimal("25157.70")


def test_detect_unrealistic_growth(sample_records):
    analyzer = build_analyzer(sample_records)
    anomalies = analyzer.detect_unrealistic_growth("Volatility Republic", max_growth_rate=Decimal("0.30"))
    assert anomalies == [
        (2021, Decimal("0.5296")),
    ]


def test_summary_contains_expected_fields(sample_records):
    analyzer = build_analyzer(sample_records)
    summary = analyzer.summary("Exampleland")
    assert summary["country"] == "Exampleland"
    assert len(summary["per_capita_series"]) == 3
    assert len(summary["growth_rates"]) == 2
    assert isinstance(summary["average_per_capita"], Decimal)
    assert summary["unrealistic_growth_years"] == []


def test_profit_relay_plan_identifies_shortfalls(sample_records):
    analyzer = build_analyzer(sample_records)
    plan = analyzer.profit_relay_plan("Exampleland", target_growth_rate=Decimal("0.05"))
    assert plan == [
        (2021, Decimal("249.50")),
    ]


def test_profit_relay_total_sums_shortfalls(sample_records):
    analyzer = build_analyzer(sample_records)
    total = analyzer.profit_relay_total("Exampleland", target_growth_rate=Decimal("0.05"))
    assert total == Decimal("249.50")


def test_summary_includes_profit_relay_when_requested(sample_records):
    analyzer = build_analyzer(sample_records)
    summary = analyzer.summary(
        "Exampleland", profit_relay_target=Decimal("0.05"), safety_margin=Decimal("0.01")
    )
    assert summary["profit_relay_plan"] == [
        (2021, Decimal("489.50")),
    ]
    assert summary["profit_relay_total"] == Decimal("489.50")

