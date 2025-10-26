from typing import Dict

from prometheus_client import Gauge


PIPELINE_STATUS = Gauge("pipeline_status", "Status of the research pipeline", ["stage"])
_state: Dict[str, float] = {}


def set_stage(stage: str, value: float) -> None:
    PIPELINE_STATUS.labels(stage=stage).set(value)
    _state[stage] = value


def snapshot() -> Dict[str, float]:
    return dict(_state)
