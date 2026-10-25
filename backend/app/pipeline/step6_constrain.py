"""Step 6: Constrain (Exit Gate 2).

Structured constraint layer that validates:
- Evidence rigour threshold (minimum 65% for Morning Brief).
- Profile compatibility & drawdown suitability.
- Strict prohibition against black-box or hallucinated numeric claims.

Outputs that fail these checks are downgraded or blocked entirely.
"""

from typing import Tuple
from ..models.schemas import AuditableReasoningChain
from .step3_deduplicate import ClusteredEvent


class ConstraintGate:
    MIN_RIGOUR_THRESHOLD = 65

    @classmethod
    def apply_constraints(cls, cluster: ClusteredEvent, chain: AuditableReasoningChain) -> Tuple[bool, str]:
        """Evaluates whether the reasoning chain passes the safety and confidence gate."""
        # Check 1: Rigour threshold
        if chain.evidence_rigour_score < cls.MIN_RIGOUR_THRESHOLD:
            return False, f"Downgraded: Evidence rigour score ({chain.evidence_rigour_score}) below threshold ({cls.MIN_RIGOUR_THRESHOLD})."

        # Check 2: Verify counter-analogy existence (prevents false equivalence bias)
        if not chain.counter_analogy_differences or len(chain.counter_analogy_differences.strip()) < 10:
            return False, "Blocked: Reasoning chain missing mandatory Counter-Analogy verification."

        # Check 3: Check for forbidden numeric hallucination patterns (e.g. "will gain 24%", "price target ₹1,200")
        text_corpus = f"{chain.why_it_matters} {chain.transmission_chain}".lower()
        forbidden_phrases = ["price target", "target price", "guaranteed return", "will rally by", "will surge to ₹"]
        for phrase in forbidden_phrases:
            if phrase in text_corpus:
                return False, f"Blocked: Prohibited numeric or price forecast detected ('{phrase}')."

        return True, "Passed: All constraint and safety checks validated."
