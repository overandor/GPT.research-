from src.kpi_engine.econometrics import build_report, rolling_sharpe


def test_rolling_sharpe_handles_small_samples() -> None:
    assert rolling_sharpe([]) == 0.0
    assert rolling_sharpe([0.01]) == 0.0


def test_build_report_provides_metrics() -> None:
    report = build_report([0.01, -0.02, 0.03, 0.04])
    assert report.volatility > 0
    assert -5 < report.sharpe < 5
