"""Step 6: check reviewed coverage, explanation completeness and forbidden forecasts.

These checks do not prove factual accuracy or regulatory compliance.
"""
from typing import Tuple
from ..models.schemas import AuditableReasoningChain
from .step3_deduplicate import ClusteredEvent


class ConstraintGate:
    @classmethod
    def apply_constraints(cls, cluster: ClusteredEvent, chain: AuditableReasoningChain) -> Tuple[bool, str]:
        if not chain.analysis_available:
            return False, "Downgraded: No reviewed scenario matches the exact input; analysis withheld."
        if not all((chain.why_it_matters.strip(), chain.transmission_chain.strip(), chain.explicit_caveat.strip())):
            return False, "Blocked: Missing interpretation, mechanism, or uncertainty."
        if len(chain.counter_analogy_differences.strip()) < 10:
            return False, "Blocked: Missing comparison limitations."
        text = " ".join(v for v in chain.model_dump().values() if isinstance(v, str)).lower()
        for phrase in ["price target", "target price", "guaranteed return", "will rally by", "will surge to"]:
            if phrase in text:
                return False, f"Blocked: Prohibited forecast detected ('{phrase}')."
        return True, "Passed: Reviewed demo coverage and explanation checks; factual impact remains unvalidated."
