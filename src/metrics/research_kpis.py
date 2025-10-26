from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Optional

import numpy as np


@dataclass
class ResearchSignal:
    timestamp: datetime
    model: str
    novelty_score: float
    impact_score: float
    text: str
    track: str
    statistical_significance: Optional[float] = None
    confirmation_status: str = "PENDING"
    publication_score: float = 0.0


class ResearchKPIEngine:
    """Track ensemble performance for research discovery."""

    def __init__(self, significance_threshold: float = 0.05) -> None:
        self.significance_threshold = significance_threshold
        self.signals: List[ResearchSignal] = []
        self.confirmed_signals: List[ResearchSignal] = []

    def add_signal(self, signal: ResearchSignal) -> None:
        self.signals.append(signal)
        signal.publication_score = self._calculate_publication_score(signal)

        if (
            signal.novelty_score > 0.8
            and signal.impact_score > 0.7
            and len(signal.text) > 100
        ):
            signal.confirmation_status = "CONFIRMED"
            self.confirmed_signals.append(signal)

    def _calculate_publication_score(self, signal: ResearchSignal) -> float:
        novelty_weight = 0.4
        impact_weight = 0.3
        evidence_weight = 0.2
        specificity_weight = 0.1

        evidence_strength = min(len(signal.text) / 500, 1.0)

        buzzwords = {"mev", "zkp", "defi", "ai", "quantum"}
        words = signal.text.lower().split()
        buzzword_count = sum(1 for word in words if word in buzzwords)
        specificity = 1.0 - min(buzzword_count / max(len(words), 1), 0.5)

        return (
            novelty_weight * signal.novelty_score
            + impact_weight * signal.impact_score
            + evidence_weight * evidence_strength
            + specificity_weight * specificity
        )

    def get_signal_discovery_rate(self, window_hours: int = 24) -> Dict[str, float]:
        cutoff = datetime.now() - timedelta(hours=window_hours)
        recent_signals = [s for s in self.signals if s.timestamp >= cutoff]
        recent_confirmed = [s for s in self.confirmed_signals if s.timestamp >= cutoff]

        total_signals = len(recent_signals)
        confirmed_count = len(recent_confirmed)

        novelty_avg = (
            float(np.mean([s.novelty_score for s in recent_signals]))
            if recent_signals
            else 0.0
        )
        impact_avg = (
            float(np.mean([s.impact_score for s in recent_signals]))
            if recent_signals
            else 0.0
        )

        publication_ready = len(
            [s for s in recent_confirmed if s.publication_score > 0.8]
        )

        return {
            "signals_per_hour": total_signals / window_hours,
            "confirmation_ratio": confirmed_count / max(total_signals, 1),
            "novelty_avg": novelty_avg,
            "impact_avg": impact_avg,
            "publication_ready": publication_ready,
        }

    def get_ensemble_metrics(self) -> Dict[str, float]:
        if not self.signals:
            return {}

        recent = self.signals[-1000:]
        models = {signal.model for signal in recent}
        model_scores = {}
        for model in models:
            model_signals = [s for s in recent if s.model == model]
            if model_signals:
                model_scores[model] = float(
                    np.mean([s.novelty_score + s.impact_score for s in model_signals])
                )

        scores = list(model_scores.values())
        divergence = float(np.var(scores)) if scores else 0.0

        return {
            "ensemble_divergence": divergence,
            "top_performer": max(model_scores, key=model_scores.get) if model_scores else "",
            "active_models": len(models),
            "performance_gap": (max(scores) - min(scores)) if scores else 0.0,
        }

    def generate_research_abstract(self, signal: ResearchSignal) -> str:
        if signal.publication_score < 0.7:
            return ""

        return (
            f"RESEARCH ABSTRACT: {signal.timestamp:%Y-%m-%d %H:%M}\n\n"
            f"Title: Automated Discovery of {signal.track.upper()} Signal via LLM Ensemble\n\n"
            "Abstract: We present a novel {track} signal identified through large language model "
            "ensemble analysis. The signal demonstrates exceptional novelty and potential impact.\n"
        ).format(track=signal.track.lower())
