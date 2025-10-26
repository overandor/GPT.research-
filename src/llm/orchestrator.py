import asyncio
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import numpy as np
import aiohttp

from config.settings import settings
from .model_client import ModelClient, ModelResponse


@dataclass
class RoundContext:
    symbol: str
    price: float
    sol_tips_proxy: float
    sol_whales_proxy: float
    trending_source: str
    timestamp: float
    round_id: str


class LLMOrchestrator:
    def __init__(self) -> None:
        self.clients = [ModelClient(name, url) for name, url in settings.model_endpoints]
        self.round_history: List[Dict[str, Any]] = []
        self._session: Optional[aiohttp.ClientSession] = None

    async def initialize(self) -> None:
        self._session = aiohttp.ClientSession()
        for client in self.clients:
            await client.initialize(self._session)

    async def close(self) -> None:
        if self._session:
            await self._session.close()

    async def execute_round(self, context: RoundContext) -> List[Dict[str, Any]]:
        prompt = self._build_prompt(context)
        round_id = f"round_{int(time.time())}_{hash(prompt) % 10000:04d}"

        tasks = [client.generate(prompt, round_id) for client in self.clients]
        try:
            responses = await asyncio.wait_for(
                asyncio.gather(*tasks, return_exceptions=True),
                timeout=120,
            )
        except asyncio.TimeoutError:
            responses = [None] * len(tasks)

        results: List[Dict[str, Any]] = []
        for client, response in zip(self.clients, responses):
            if isinstance(response, Exception):
                results.append(self._handle_error(client.name, response))
            elif response is None:
                results.append(self._handle_timeout(client.name))
            else:
                results.append(self._process_successful_response(client.name, response))

        round_data = {
            "round_id": round_id,
            "timestamp": context.timestamp,
            "context": context.__dict__,
            "results": results,
        }
        self.round_history.append(round_data)
        if len(self.round_history) > 1000:
            self.round_history = self.round_history[-1000:]
        return results

    def _build_prompt(self, context: RoundContext) -> str:
        return (
            "You are competing in a public Novelty Championship.\n"
            "Respond with exactly ONE item starting with:\n"
            "TRADE: <pair, direction, entry, exit, expected X% profit, 3-line python stub>\n"
            "or\n"
            "PAPER: <Title> — 300 words abstract with a concrete mechanism and evaluation path.\n\n"
            f"Context JSON: {{\n    \"symbol\": \"{context.symbol}\",\n"
            f"    \"price\": {context.price},\n"
            f"    \"sol_tips_proxy\": {context.sol_tips_proxy},\n"
            f"    \"sol_whales_proxy\": {context.sol_whales_proxy},\n"
            f"    \"trending_source\": \"{context.trending_source}\",\n"
            f"    \"timestamp\": {context.timestamp}\n}}\n\n"
            "Rules: no filler, no preamble, one output only."
        )

    def _handle_error(self, model_name: str, error: Exception) -> Dict[str, Any]:
        return {
            "model": model_name,
            "text": f"ERROR: {type(error).__name__}: {error}",
            "lat_ms": 0,
            "error": str(error),
            "success": False,
        }

    def _handle_timeout(self, model_name: str) -> Dict[str, Any]:
        return {
            "model": model_name,
            "text": "ERROR: Request timeout",
            "lat_ms": 0,
            "error": "timeout",
            "success": False,
        }

    def _process_successful_response(self, model_name: str, response: ModelResponse) -> Dict[str, Any]:
        return {
            "model": model_name,
            "text": response.text,
            "lat_ms": response.latency_ms,
            "error": "",
            "success": True,
        }

    def get_performance_metrics(self) -> Dict[str, Any]:
        successful_calls = sum(client.successful_calls for client in self.clients)
        total_calls = sum(client.total_calls for client in self.clients)
        error_rate = 1.0 - (successful_calls / total_calls) if total_calls else 0.0
        avg_latency_values = [client.avg_latency for client in self.clients if client.avg_latency]
        avg_latency = float(np.mean(avg_latency_values)) if avg_latency_values else 0.0

        return {
            "active_clients": len([c for c in self.clients if c.is_healthy()]),
            "total_rounds": len(self.round_history),
            "success_rate": 1.0 - error_rate,
            "avg_latency": avg_latency,
            "total_errors": sum(client.error_count for client in self.clients),
        }
