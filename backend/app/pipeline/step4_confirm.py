"""Step 4: Confirm (Exit Gate 1).

Applies strict institutional credibility confirmation rules:
- Tier 1: Single source sufficient. These institutions ARE the event.
- Tier 2: At least two independent Tier 2 sources required.
- Tier 3: Never sole source. Held in quarantine / dropped.

Events failing this gate are dropped entirely. Staying quiet when evidence is weak is a feature.
"""

from typing import List, Tuple
from ..models.schemas import SourceTier
from .step3_deduplicate import ClusteredEvent


class EventConfirmationGate:
    @staticmethod
    def verify_confirmation(cluster: ClusteredEvent) -> Tuple[bool, str]:
        """Evaluates whether the clustered event satisfies institutional confirmation."""
        tier1_count = sum(1 for s in cluster.sources if s["tier"] == SourceTier.PRIMARY_INSTITUTIONAL)
        tier2_count = sum(1 for s in cluster.sources if s["tier"] == SourceTier.ENRICHMENT_MEDIA)
        tier3_count = sum(1 for s in cluster.sources if s["tier"] == SourceTier.CORROBORATING)

        # Rule 1: Single Tier 1 source is sufficient
        if tier1_count >= 1:
            return True, f"Confirmed via Tier 1 Institutional Primary Source ({cluster.primary_event.source_name})"

        # Rule 2: At least two Tier 2 sources required
        if tier2_count >= 2:
            source_names = ", ".join(s["source_name"] for s in cluster.sources if s["tier"] == SourceTier.ENRICHMENT_MEDIA)
            return True, f"Confirmed via 2 Tier 2 Media Outlets ({source_names})"

        # Rule 3: Tier 3 alone or single Tier 2 is insufficient -> DROP
        if tier1_count == 0 and tier2_count < 2:
            if tier3_count > 0:
                return False, f"Dropped: Unconfirmed event detected only via Tier 3 corroborating source ({cluster.primary_event.source_name}). Silence is a feature."
            return False, f"Dropped: Tier 2 story lacking independent secondary confirmation."

        return False, "Dropped: Did not satisfy credibility confirmation threshold."

    def filter_confirmed(self, clusters: List[ClusteredEvent]) -> Tuple[List[ClusteredEvent], List[Tuple[ClusteredEvent, str]]]:
        confirmed = []
        dropped = []
        for cluster in clusters:
            is_valid, reason = self.verify_confirmation(cluster)
            if is_valid:
                confirmed.append(cluster)
            else:
                dropped.append((cluster, reason))
        return confirmed, dropped
