from dataclasses import dataclass
from datetime import datetime
from typing import Dict

from ..metrics.impact_engine import ImpactEngine
from ..metrics.novelty_engine import NoveltyEngine
from ..metrics.research_kpis import ResearchKPIEngine, ResearchSignal


@dataclass
class ResearchScore:
    novelty: float
    impact: float
    publication: float


class ResearchScoringService:
    def __init__(self) -> None:
        self.novelty_engine = NoveltyEngine()
        self.impact_engine = ImpactEngine()
        self.kpi_engine = ResearchKPIEngine()

    def score(self, model: str, track: str, text: str) -> ResearchScore:
        novelty = self.novelty_engine.score(text)
        impact = self.impact_engine.score(text)
        signal = ResearchSignal(
            timestamp=datetime.utcnow(),
            model=model,
            novelty_score=novelty.score,
            impact_score=impact.score,
            text=text,
            track=track,
        )
        self.kpi_engine.add_signal(signal)
        return ResearchScore(
            novelty=novelty.score,
            impact=impact.score,
            publication=signal.publication_score,
        )

    def metrics_snapshot(self) -> Dict[str, float]:
        return self.kpi_engine.get_signal_discovery_rate()
