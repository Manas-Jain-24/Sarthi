"""Unit tests for Kahneman-Thaler Behavioral Risk Profiler."""

from backend.app.services.risk_profiler import RiskProfiler


def test_rationality_gap_detection():
    # User claims 'aggressive' but panics and liquidates on a 22% drop
    result = RiskProfiler.calculate_revealed_profile(
        base_portfolio_inr=1000000,
        scenario_response="panic_sell",
        stated_tolerance="aggressive",
        investment_horizon="long_term_5yr_plus"
    )

    assert result["has_rationality_gap"] is True
    assert result["loss_aversion_lambda"] >= 2.5
    assert "recalibrated" in result["gap_explanation"].lower()


def test_consistent_patient_investor():
    result = RiskProfiler.calculate_revealed_profile(
        base_portfolio_inr=1000000,
        scenario_response="hold_patient",
        stated_tolerance="moderate",
        investment_horizon="long_term_5yr_plus"
    )

    assert result["has_rationality_gap"] is False
    assert result["loss_aversion_lambda"] == 1.6
    assert "Balanced" in result["calibrated_band"]
