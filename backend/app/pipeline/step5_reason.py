"""Step 5: reviewed scenario analysis, separate from source evidence.

No LLM is connected. Unknown or changed inputs abstain rather than reuse
unrelated analysis. Demo prose is not a verified investment conclusion.
"""
import json
from pathlib import Path
from ..models.schemas import AuditableReasoningChain, ImpactVector
from ..services.analogy_service import analogy_service
from .step3_deduplicate import ClusteredEvent

SCENARIOS = Path(__file__).resolve().parent.parent / "data" / "demo_scenarios.json"


class EventReasoner:
    def __init__(self):
        self.scenarios = json.loads(SCENARIOS.read_text(encoding="utf-8"))

    def reason_through_event(self, cluster: ClusteredEvent) -> AuditableReasoningChain:
        event = cluster.primary_event
        scenario = self.scenarios.get(event.id)
        available = bool(scenario and event.is_sample and
                         scenario["input_title"] == event.title and
                         scenario["input_content"] == event.content)
        scenario = scenario if available else {}
        precedent = analogy_service.get_by_id(scenario.get("analogy_id", ""))
        return AuditableReasoningChain(
            event_detected=event.title,
            source_verification=(
                f"Sample fixture: {cluster.source_count} distinct named source(s), "
                f"highest assigned tier {cluster.highest_tier.value}. "
                "Rule demonstration only; no source document was fetched or verified."
            ),
            why_it_matters=scenario.get("interpretation", "No reviewed analysis is available for this input."),
            transmission_chain=scenario.get("mechanism", "Insufficient evidence to infer a mechanism."),
            historical_analogy_id=precedent.id if precedent else "",
            historical_analogy_name=precedent.name if precedent else "No supported comparison",
            historical_similarity=scenario.get("similarity", "No historical comparison proposed."),
            counter_analogy_differences=scenario.get("differences", "No validated analogy; abstain."),
            profile_relevance="Local sector and ticker matching does not establish investment suitability.",
            impact_vector=ImpactVector(scenario.get("impact", ImpactVector.INSUFFICIENT_EVIDENCE.value)),
            evidence_status="Sample input; not independently verified",
            impact_status="Illustrative hypothesis; not validated" if available else "Unknown; analysis unavailable",
            analysis_available=available,
            explicit_caveat=scenario.get("caveat", "No conclusion should be drawn from this unreviewed input.")
        )
