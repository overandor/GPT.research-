import asyncio
from typing import Callable, Dict


class SolanaStream:
    """Placeholder stream for Solana signals."""

    def __init__(self, poll_interval: float = 5.0) -> None:
        self.poll_interval = poll_interval
        self._running = False

    async def start(self, handler: Callable[[Dict[str, float]], None]) -> None:
        self._running = True
        while self._running:
            handler({"tips": 0.0, "whales": 0.0})
            await asyncio.sleep(self.poll_interval)

    def stop(self) -> None:
        self._running = False
