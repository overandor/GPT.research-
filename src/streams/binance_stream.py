import json
from typing import Any, Callable, Dict

from config.settings import settings
from .stream_manager import StreamManager


class BinanceStream:
    """Ingest trade data from Binance public websocket feed."""

    def __init__(self, manager: StreamManager) -> None:
        self.manager = manager

    async def start(self, handler: Callable[[Dict[str, Any]], None]) -> None:
        async def _handle(message: str) -> None:
            payload = json.loads(message)
            handler(payload)

        self.manager.start()
        await self.manager.managed_websocket_stream(settings.ws_binance, _handle)

    def stop(self) -> None:
        self.manager.stop()
