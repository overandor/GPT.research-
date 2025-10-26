from dataclasses import dataclass
from typing import Iterable

import numpy as np


def rolling_sharpe(returns: Iterable[float]) -> float:
    data = np.array(list(returns), dtype=float)
    if data.size == 0:
        return 0.0
    mean = float(data.mean())
    std = float(data.std(ddof=1)) if data.size > 1 else 0.0
    return mean / std if std else 0.0


@dataclass
class EconometricsReport:
    sharpe: float
    volatility: float


def build_report(returns: Iterable[float]) -> EconometricsReport:
    data = np.array(list(returns), dtype=float)
    volatility = float(data.std(ddof=1)) if data.size > 1 else 0.0
    return EconometricsReport(sharpe=rolling_sharpe(data), volatility=volatility)
