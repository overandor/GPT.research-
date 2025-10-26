import asyncio
import time
from dataclasses import dataclass
from typing import Optional

import aiohttp

from config.settings import settings


@dataclass
class ModelResponse:
    text: str
    latency_ms: float


class ModelClient:
    def __init__(self, name: str, url: str) -> None:
        self.name = name
        self.url = url
        self.total_calls = 0
        self.error_count = 0
        self.successful_calls = 0
        self.avg_latency = 0.0
        self._session: Optional[aiohttp.ClientSession] = None

    async def initialize(self, session: aiohttp.ClientSession) -> None:
        self._session = session

    async def generate(self, prompt: str, round_id: str) -> ModelResponse:
        if not self._session:
            raise RuntimeError("Client session not initialized")

        retries = 0
        backoff = settings.retry_backoff
        while True:
            start = time.perf_counter()
            self.total_calls += 1
            try:
                async with self._session.post(
                    self.url,
                    json={"prompt": prompt, "round_id": round_id},
                    timeout=aiohttp.ClientTimeout(total=30),
                ) as response:
                    response.raise_for_status()
                    data = await response.json()
                    latency_ms = (time.perf_counter() - start) * 1000
                    self._update_latency(latency_ms)
                    self.successful_calls += 1
                    text = data.get("text") or data.get("response") or ""
                    return ModelResponse(text=text, latency_ms=latency_ms)
            except Exception:
                self.error_count += 1
                if retries >= settings.max_retries:
                    raise
                retries += 1
                await asyncio.sleep(backoff)
                backoff *= settings.retry_backoff

    def is_healthy(self) -> bool:
        return self.error_count < settings.circuit_breaker_failures

    def _update_latency(self, latest_latency: float) -> None:
        self.avg_latency = (
            (self.avg_latency * (self.successful_calls - 1) + latest_latency)
            / max(self.successful_calls, 1)
        )
