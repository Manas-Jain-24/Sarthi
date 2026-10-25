"""Step 3: Deduplicate & Cluster.

Clusters reports of the same event across multiple sources into a single
canonical event object. Tracks source count and highest credibility tier as confirmation signals.
"""

from typing import List, Dict, Any
from ..models.schemas import RawEvent, SourceTier, EventCategory


class ClusteredEvent:
    def __init__(self, canonical_event: RawEvent, category: EventCategory):
        self.primary_event = canonical_event
        self.category = category
        self.sources: List[Dict[str, Any]] = [
            {"source_name": canonical_event.source_name, "tier": canonical_event.source_tier}
        ]
        if canonical_event.secondary_source_name and canonical_event.secondary_source_tier:
            self.sources.append({
                "source_name": canonical_event.secondary_source_name,
                "tier": canonical_event.secondary_source_tier
            })

    @property
    def source_count(self) -> int:
        return len(self.sources)

    @property
    def highest_tier(self) -> SourceTier:
        tiers = [s["tier"] for s in self.sources]
        return min(tiers, key=lambda t: t.value)


class EventDeduplicator:
    def cluster_events(self, items: List[tuple[RawEvent, EventCategory]]) -> List[ClusteredEvent]:
        """Groups events into clustered representations."""
        clusters: List[ClusteredEvent] = []

        for raw_event, category in items:
            # Simple keyword / token similarity for clustering
            matched_cluster = None
            raw_tokens = set(raw_event.title.lower().split())

            for cluster in clusters:
                cluster_tokens = set(cluster.primary_event.title.lower().split())
                jaccard = len(raw_tokens.intersection(cluster_tokens)) / max(len(raw_tokens.union(cluster_tokens)), 1)
                if jaccard > 0.4:
                    matched_cluster = cluster
                    break

            if matched_cluster:
                matched_cluster.sources.append({
                    "source_name": raw_event.source_name,
                    "tier": raw_event.source_tier
                })
            else:
                clusters.append(ClusteredEvent(raw_event, category))

        return clusters
