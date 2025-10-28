import asyncio
import random

import pytest

from src.kpi_engine.economic_singularity import (
    EconomicSingularity,
    FreeTierOrchestrator,
    GDPImpactTracker,
    ZeroBudgetWealthEngine,
)


@pytest.mark.asyncio
async def test_process_economic_idea_is_deterministic():
    singularity = EconomicSingularity(rng=random.Random(123))
    result = await singularity.process_economic_idea(
        "Automated business process optimization system"
    )
    assert result["prompt_asset"]["id"] == "9c0eb3ec11405fa7"
    assert result["deployment_url"].startswith("https://")
    assert result["deployment_number"] == 1
    assert result["intellectual_wealth"] > 0


def test_calculate_gdp_impact_values():
    engine = ZeroBudgetWealthEngine(rng=random.Random(0))
    report = engine.calculate_gdp_impact("code_infrastructure", executions=10)
    assert report["executions"] == 10
    assert pytest.approx(report["total_cost"], rel=1e-6) == 0.02
    assert pytest.approx(report["gdp_impact"], rel=1e-6) == 9000.0
    assert report["effective_roi"] > 0


def test_tracker_records_and_aggregates():
    tracker = GDPImpactTracker()
    asset = {"id": "asset123"}
    record = tracker.record_impact(asset, {"gdp_impact": 1000.0})
    assert record["asset_id"] == "asset123"
    assert record["reported_impact"] == 1000.0
    dashboard = tracker.get_economic_dashboard()
    assert dashboard["assets_deployed"] == 1
    assert dashboard["total_verified_impact_usd"] > 0


@pytest.mark.asyncio
async def test_mass_deploy_round_robin():
    orchestrator = FreeTierOrchestrator()
    assets = [
        {"id": f"asset{i}"} for i in range(6)
    ]
    urls = await orchestrator.mass_deploy(assets)
    assert len(urls) == 6
    assert urls[0].startswith("https://huggingface.co/")
    assert urls[-1].startswith("https://huggingface.co/") or urls[-1].startswith(
        "https://economic-engine.github.io/"
    )

