import asyncio
import time
from dataclasses import dataclass
from typing import Any, Awaitable, Callable, Dict, Optional

from websockets import connect


@dataclass
class StreamHealth:
    last_message: float = 0.0
    message_count: int = 0
    error_count: int = 0
    reconnect_count: int = 0
    total_downtime: float = 0.0


class CircuitBreaker:
    """Simple circuit breaker implementation to protect external services."""

    def __init__(self, max_failures: int = 5, timeout: int = 60) -> None:
        self.max_failures = max_failures
        self.timeout = timeout
        self.failures = 0
        self.last_failure = 0.0
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN

    def can_execute(self) -> bool:
        if self.state == "OPEN":
            if time.time() - self.last_failure > self.timeout:
                self.state = "HALF_OPEN"
                return True
            return False
        return True

    def on_success(self) -> None:
        self.state = "CLOSED"
        self.failures = 0

    def on_failure(self) -> None:
        self.failures += 1
        self.last_failure = time.time()
        if self.failures >= self.max_failures:
            self.state = "OPEN"


class StreamManager:
    """Manage resilient streaming connections with health metrics."""

    def __init__(self, circuit_breaker: Optional[CircuitBreaker] = None) -> None:
        self.health = StreamHealth()
        self.circuit_breaker = circuit_breaker or CircuitBreaker()
        self._is_running = False

    async def managed_websocket_stream(
        self, url: str, message_handler: Callable[[str], Awaitable[None]],
    ) -> None:
        backoff = 1
        max_backoff = 32

        while self._is_running:
            if not self.circuit_breaker.can_execute():
                await asyncio.sleep(5)
                continue

            try:
                async with connect(url, ping_interval=20, ping_timeout=10) as ws:
                    self.health.reconnect_count += 1
                    backoff = 1

                    async for message in ws:
                        if not self._is_running:
                            break

                        self.health.last_message = time.time()
                        self.health.message_count += 1

                        try:
                            await message_handler(message)
                            self.circuit_breaker.on_success()
                        except Exception:
                            self.health.error_count += 1
                            self.circuit_breaker.on_failure()
                            break

            except Exception:
                self.health.error_count += 1
                self.circuit_breaker.on_failure()
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2, max_backoff)

    def get_health_metrics(self) -> Dict[str, Any]:
        downtime = 0.0
        if self.health.last_message:
            downtime = max(0.0, time.time() - self.health.last_message - 30)
            self.health.total_downtime += downtime

        return {
            "message_count": self.health.message_count,
            "error_count": self.health.error_count,
            "reconnect_count": self.health.reconnect_count,
            "current_downtime": downtime,
            "total_downtime": self.health.total_downtime,
            "circuit_breaker_state": self.circuit_breaker.state,
        }

    def start(self) -> None:
        self._is_running = True

    def stop(self) -> None:
        self._is_running = False
