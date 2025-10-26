from dataclasses import dataclass


@dataclass
class ImpactResult:
    score: float
    rationale: str


class ImpactEngine:
    """Estimate potential impact for a research signal."""

    def score(self, text: str) -> ImpactResult:
        keywords = {"protocol", "deployment", "experiment", "backtest"}
        hits = sum(1 for word in text.lower().split() if word in keywords)
        score = min(hits / 4.0, 1.0)
        rationale = "Contains operational language" if hits else "Insufficient implementation detail"
        return ImpactResult(score=score, rationale=rationale)
