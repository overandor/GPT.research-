from dataclasses import dataclass


@dataclass
class NoveltyResult:
    score: float
    rationale: str


class NoveltyEngine:
    """Score model outputs for novelty."""

    def score(self, text: str) -> NoveltyResult:
        tokens = len(text.split())
        score = min(tokens / 150.0, 1.0)
        rationale = "High token count implies richer signal" if score > 0.7 else "Limited detail"
        return NoveltyResult(score=score, rationale=rationale)
