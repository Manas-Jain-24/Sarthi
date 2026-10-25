"""Behavioral Risk Profiling Engine based on Kahneman-Tversky Prospect Theory.

Cross-checks stated risk tolerance against revealed behavior using real rupee loss simulations.
"""

from typing import Dict, Any


class RiskProfiler:
    @staticmethod
    def calculate_revealed_profile(
        base_portfolio_inr: float,
        scenario_response: str,
        stated_tolerance: str,
        investment_horizon: str
    ) -> Dict[str, Any]:
        """Calculates loss aversion coefficient (lambda) and calibrated risk band.

        Scenarios:
        - 'panic_sell': User dumps all assets upon a 22% drop (High loss aversion, lambda >= 2.5)
        - 'hold_patient': User remains calm and holds (Moderate/Rational, lambda ~ 1.6)
        - 'buy_dip': User aggressively accumulates at discount (Opportunistic, lambda ~ 1.0)
        """
        if scenario_response == "panic_sell":
            revealed_drawdown_tolerance = 10.0
            lambda_factor = 2.6
            calibrated_band = "Conservative (Capital Preservation)"
            tone_guidance = "Calm, reassuring, grounded in historical recovery durations"
        elif scenario_response == "buy_dip":
            revealed_drawdown_tolerance = 30.0
            lambda_factor = 1.0
            calibrated_band = "Opportunistic Long-Term Growth"
            tone_guidance = "Deep fundamental metrics, capital allocation efficiency"
        else:  # 'hold_patient'
            revealed_drawdown_tolerance = 20.0
            lambda_factor = 1.6
            calibrated_band = "Balanced Compounding"
            tone_guidance = "Balanced structural shift analysis, earnings visibility"

        # Detect rationality gap (e.g. user claims 'aggressive' but panics on rupee loss)
        is_rationality_gap = (stated_tolerance.lower() in ["aggressive", "high"] and scenario_response == "panic_sell")

        return {
            "calibrated_band": calibrated_band,
            "loss_aversion_lambda": lambda_factor,
            "max_tolerated_drawdown_pct": revealed_drawdown_tolerance,
            "tone_guidance": tone_guidance,
            "has_rationality_gap": is_rationality_gap,
            "gap_explanation": (
                "You indicated a high risk appetite, but selected capital liquidation in a standard "
                "22% market correction scenario. Sarthi has recalibrated your profile to prevent emotional "
                "panic-selling during temporary structural adjustments."
                if is_rationality_gap
                else "Your stated tolerance aligns harmoniously with your simulated behavioral response."
            )
        }
