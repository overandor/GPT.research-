import time
from typing import Any, Callable, Dict

import psutil
from prometheus_client import Counter, Gauge, Histogram, start_http_server

MODEL_CALLS = Counter("model_calls_total", "Total model calls", ["model", "status"])
REQUEST_LATENCY = Histogram("request_latency_seconds", "Request latency")
ACTIVE_STREAMS = Gauge("active_streams", "Number of active data streams")
MEMORY_USAGE = Gauge("memory_usage_bytes", "Memory usage in bytes")
CPU_USAGE = Gauge("cpu_usage_percent", "CPU usage percentage")


class HealthMonitor:
    def __init__(self, metrics_port: int = 9090) -> None:
        self.metrics_port = metrics_port
        self.start_time = time.time()
        self.health_checks: Dict[str, Callable[[], Dict[str, Any]]] = {}

    def start_metrics_server(self) -> None:
        start_http_server(self.metrics_port)

    def record_model_call(self, model: str, success: bool, latency: float) -> None:
        status = "success" if success else "error"
        MODEL_CALLS.labels(model=model, status=status).inc()
        REQUEST_LATENCY.observe(latency)

    def update_system_metrics(self) -> None:
        MEMORY_USAGE.set(psutil.Process().memory_info().rss)
        CPU_USAGE.set(psutil.cpu_percent())

    def health_check(self) -> Dict[str, Any]:
        uptime = time.time() - self.start_time
        return {
            "status": "healthy",
            "uptime_seconds": uptime,
            "timestamp": time.time(),
            "system": {
                "memory_usage": psutil.Process().memory_info().rss,
                "cpu_percent": psutil.cpu_percent(),
                "disk_usage": psutil.disk_usage("/").percent,
            },
            "services": {name: check() for name, check in self.health_checks.items()},
        }

    def register_health_check(self, name: str, check_func: Callable[[], Dict[str, Any]]) -> None:
        self.health_checks[name] = check_func
