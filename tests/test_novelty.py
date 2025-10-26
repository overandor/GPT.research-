from src.metrics.novelty_engine import NoveltyEngine


def test_novelty_engine_scores_text() -> None:
    engine = NoveltyEngine()
    result = engine.score("This is a detailed experiment protocol with numerous specifics." * 5)
    assert 0.0 <= result.score <= 1.0
    assert result.rationale
