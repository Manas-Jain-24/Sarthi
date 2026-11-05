"""Step 7: Output Packaging.

Packages verified reasoning chains into clean MorningBriefCard objects
with full auditable reasoning chain, explicit caveats, and illustrative Impact Vectors.
"""

from typing import List
from ..models.schemas import MorningBriefCard, AuditableReasoningChain
from .step3_deduplicate import ClusteredEvent


class OutputFormatter:
    @staticmethod
    def format_card(cluster: ClusteredEvent, chain: AuditableReasoningChain, passed_gate: bool) -> MorningBriefCard:
        event = cluster.primary_event
        sectors = event.sectors
        primary_sector = sectors[0] if sectors else "Macro"

        source_attribution = f"{event.source_name} (Tier {cluster.highest_tier.value})"
        if cluster.source_count > 1:
            source_attribution += f" + {cluster.source_count - 1} corroborating source(s)"

        summary_insight = (
            f"{chain.impact_vector.value} · {chain.why_it_matters[:130]}... "
            f"Grounding: [{chain.historical_analogy_name}]."
        )

        return MorningBriefCard(
            id=event.id,
            canonical_title=event.title,
            category=cluster.category,
            highest_tier=cluster.highest_tier,
            source_attribution=source_attribution,
            primary_sector=primary_sector,
            impacted_tickers=event.related_tickers,
            impact_vector=chain.impact_vector,
            evidence_status=chain.evidence_status,
            impact_status=chain.impact_status,
            is_sample=event.is_sample,
            sectors=sectors,
            evidence_excerpt=event.content,
            source_url=event.source_url,
            reference_url=event.reference_url,
            summary_insight=summary_insight,
            reasoning_chain=chain,
            published_at=event.published_at,
            is_confirmed=False,
            passed_constraint_gate=passed_gate
        )
