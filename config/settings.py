from typing import Any, List, Tuple

from pydantic import BaseSettings, Field


class Settings(BaseSettings):
    """Runtime configuration for the CHAMP research engine."""

    symbol: str = Field(default="btcusdt", env="SYMBOL")
    ws_binance: str = Field(default="", env="WS_BINANCE")
    batch_seconds: int = Field(default=30, env="BATCH_SEC")
    hist_points: int = Field(default=360, env="HIST_POINTS")

    model_endpoints: List[Tuple[str, str]] = Field(default_factory=list)
    max_retries: int = Field(default=3, env="MAX_RETRIES")
    retry_backoff: float = Field(default=1.5, env="RETRY_BACKOFF")
    circuit_breaker_failures: int = Field(default=5, env="CB_FAILURES")
    circuit_breaker_timeout: int = Field(default=60, env="CB_TIMEOUT")

    data_root: str = Field(default="/data", env="DATA_ROOT")
    archive_cap: int = Field(default=12_000, env="ARCHIVE_CAP")
    max_text_length: int = Field(default=2000, env="MAX_TEXT")

    research_sources: List[str] = Field(default_factory=list)
    significance_threshold: float = Field(default=0.05, env="SIGNIFICANCE_THRESHOLD")
    novelty_threshold: float = Field(default=0.7, env="NOVELTY_THRESHOLD")

    health_check_interval: int = Field(default=30, env="HEALTH_CHECK_INTERVAL")
    metrics_port: int = Field(default=9090, env="METRICS_PORT")
    alert_webhook: str = Field(default="", env="ALERT_WEBHOOK")

    class Config:
        env_file = ".env"

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.ws_binance = f"wss://stream.binance.com:9443/ws/{self.symbol}@trade"
        if not self.model_endpoints:
            self.model_endpoints = [
                ("llama3_8b", "http://llama3-8b:8001/generate"),
                ("mistral_7b", "http://mistral-7b:8002/generate"),
            ]


def load_settings() -> Settings:
    return Settings()


settings = load_settings()
