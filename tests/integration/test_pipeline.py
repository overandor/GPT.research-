import asyncio

import pytest

from src.llm.orchestrator import LLMOrchestrator, RoundContext


@pytest.mark.asyncio
async def test_orchestrator_handles_timeouts() -> None:
    orchestrator = LLMOrchestrator()

    class DummyClient:
        def __init__(self) -> None:
            self.name = "dummy"
            self.total_calls = 0
            self.successful_calls = 0
            self.error_count = 0
            self.avg_latency = 0.0

        async def initialize(self, session) -> None:
            return None

        async def generate(self, prompt: str, round_id: str):
            raise asyncio.TimeoutError

        def is_healthy(self) -> bool:
            return False

    orchestrator.clients = [DummyClient()]
    await orchestrator.initialize()

    context = RoundContext(
        symbol="BTCUSDT",
        price=100.0,
        sol_tips_proxy=1.0,
        sol_whales_proxy=2.0,
        trending_source="test",
        timestamp=0.0,
        round_id="round_test",
    )
    results = await orchestrator.execute_round(context)
    assert results[0]["success"] is False
    await orchestrator.close()
