"""Step 3: Deduplicate & Cluster.

Clusters reports of the same event across multiple sources into a single
canonical event object. Tracks source count and highest credibility tier as confirmation signals.
"""

from typing import List, Dict, Any
from urllib.parse import urlsplit
from ..models.schemas import RawEvent, SourceTier, EventCategory


class ClusteredEvent:
    def __init__(self, canonical_event: RawEvent, category: EventCategory):
        self.primary_event = canonical_event
        self.category = category
        self.sources: List[Dict[str, Any]] = [
            {"source_name": canonical_event.source_name, "tier": canonical_event.source_tier,
             "url": canonical_event.source_url}
        ]
        if canonical_event.secondary_source_name and canonical_event.secondary_source_tier:
            self.add_source(canonical_event.secondary_source_name, canonical_event.secondary_source_tier)

    @property
    def source_count(self) -> int:
        return len(self.sources)

    def add_source(self, name, tier, url=""):
        """Repeated publisher names or domains cannot provide a second confirmation.

        Different publishers may still syndicate one report; this is only a basic check.
        """
        domain = urlsplit(url).hostname
        for source in self.sources:
            same_name = source["source_name"].strip().casefold() == name.strip().casefold()
            same_domain = domain and domain.removeprefix("www.") == (urlsplit(source.get("url", "")).hostname or "").removeprefix("www.")
            if same_name or same_domain:
                return
        self.sources.append({"source_name": name, "tier": tier, "url": url})

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
                if category == cluster.category and raw_event.published_at[:10] == cluster.primary_event.published_at[:10] and jaccard > 0.4:
                    matched_cluster = cluster
                    break

            if matched_cluster:
                matched_cluster.add_source(raw_event.source_name, raw_event.source_tier, raw_event.source_url)
                if raw_event.secondary_source_name and raw_event.secondary_source_tier:
                    matched_cluster.add_source(raw_event.secondary_source_name, raw_event.secondary_source_tier)
            else:
                clusters.append(ClusteredEvent(raw_event, category))

        return clusters
