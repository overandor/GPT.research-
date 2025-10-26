import time
from collections import deque
from typing import Any, Deque, Dict, Tuple

from config.settings import settings
from ..llm.orchestrator import LLMOrchestrator, RoundContext
from ..metrics.research_kpis import ResearchKPIEngine
from ..monitoring.health import HealthMonitor
from ..storage.merkle_logger import MerkleLogger
from ..streams.stream_manager import StreamManager


class CHAMPDashboard:
    def __init__(self) -> None:
        self.stream_manager = StreamManager()
        self.orchestrator = LLMOrchestrator()
        self.research_kpis = ResearchKPIEngine()
        self.health_monitor = HealthMonitor(settings.metrics_port)
        self.merkle_logger = MerkleLogger(settings.data_root)

        self.price_buffer: Deque[Tuple[float, float]] = deque(maxlen=settings.hist_points)
        self.sol_buffer: Deque[Tuple[float, float, float]] = deque(maxlen=settings.hist_points)
        self.latest_outputs: Deque[str] = deque(maxlen=10)

    async def initialize(self) -> None:
        await self.orchestrator.initialize()
        self.health_monitor.start_metrics_server()
        self.health_monitor.register_health_check(
            "stream_manager", self.stream_manager.get_health_metrics
        )
        self.health_monitor.register_health_check(
            "orchestrator", self.orchestrator.get_performance_metrics
        )

    async def close(self) -> None:
        await self.orchestrator.close()

    async def run_round(self) -> None:
        if not self.price_buffer or not self.sol_buffer:
            return

        context = RoundContext(
            symbol=settings.symbol.upper(),
            price=self.price_buffer[-1][1],
            sol_tips_proxy=self.sol_buffer[-1][1],
            sol_whales_proxy=self.sol_buffer[-1][2],
            trending_source="https://arxiv.org/list/cs.AI/recent",
            timestamp=time.time(),
            round_id=f"round_{int(time.time())}",
        )
        results = await self.orchestrator.execute_round(context)

        merkle_root = self.merkle_logger.log_round(context, results)
        if results:
            top_output = max(results, key=lambda x: len(x.get("text", "")))
            self.latest_outputs.appendleft(top_output.get("text", ""))
        return merkle_root

    def get_dashboard_data(self) -> Dict[str, Any]:
        return {
            "system_health": self.health_monitor.health_check(),
            "research_kpis": self.research_kpis.get_signal_discovery_rate(),
            "ensemble_metrics": self.research_kpis.get_ensemble_metrics(),
            "stream_health": self.stream_manager.get_health_metrics(),
            "orchestrator_metrics": self.orchestrator.get_performance_metrics(),
            "latest_outputs": list(self.latest_outputs),
            "price_data": list(self.price_buffer),
            "merkle_root": self.merkle_logger.get_current_root(),
        }
