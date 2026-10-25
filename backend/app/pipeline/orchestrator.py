"""The complete 7-step Sarthi Decision Support Pipeline Orchestrator."""

import logging
from typing import Dict, List, Any
from .step1_scan import EventScanner
from .step2_classify import EventClassifier
from .step3_deduplicate import EventDeduplicator
from .step4_confirm import EventConfirmationGate
from .step5_reason import EventReasoner
from .step6_constrain import ConstraintGate
from .step7_output import OutputFormatter
from ..models.schemas import MorningBriefCard

logger = logging.getLogger("sarthi.pipeline")


class SarthiPipeline:
    def __init__(self):
        self.scanner = EventScanner()
        self.classifier = EventClassifier()
        self.deduplicator = EventDeduplicator()
        self.confirmation_gate = EventConfirmationGate()
        self.reasoner = EventReasoner()
        self.constraint_gate = ConstraintGate()
        self.formatter = OutputFormatter()

    def run_morning_pipeline(self) -> Dict[str, Any]:
        """Executes the complete 7-step processing pipeline."""
        stats = {
            "scanned": 0,
            "classified": 0,
            "clustered": 0,
            "confirmed": 0,
            "dropped_at_confirm": 0,
            "passed_constraint": 0,
            "downgraded_at_constraint": 0,
            "final_morning_cards": 0
        }

        # Step 1: Scan
        raw_events = self.scanner.scan_sources()
        stats["scanned"] = len(raw_events)

        # Step 2: Classify
        classified_events = self.classifier.classify_batch(raw_events)
        stats["classified"] = len(classified_events)

        # Step 3: Deduplicate & Cluster
        clusters = self.deduplicator.cluster_events(classified_events)
        stats["clustered"] = len(clusters)

        # Step 4: Confirm (Gate 1)
        confirmed_clusters, dropped_unconfirmed = self.confirmation_gate.filter_confirmed(clusters)
        stats["confirmed"] = len(confirmed_clusters)
        stats["dropped_at_confirm"] = len(dropped_unconfirmed)

        morning_brief_cards: List[MorningBriefCard] = []
        explore_feed_cards: List[MorningBriefCard] = []

        # Step 5, 6, 7: Reason, Constrain, Output
        for cluster in confirmed_clusters:
            # Step 5: Reason
            chain = self.reasoner.reason_through_event(cluster)

            # Step 6: Constrain (Gate 2)
            passed_gate, gate_msg = self.constraint_gate.apply_constraints(cluster, chain)

            # Step 7: Output
            card = self.formatter.format_card(cluster, chain, passed_gate)

            if passed_gate:
                morning_brief_cards.append(card)
                stats["passed_constraint"] += 1
            else:
                explore_feed_cards.append(card)
                stats["downgraded_at_constraint"] += 1

        stats["final_morning_cards"] = len(morning_brief_cards)

        return {
            "stats": stats,
            "morning_brief": morning_brief_cards,
            "explore_feed": explore_feed_cards,
            "dropped_events_audit": [
                {"title": item[0].primary_event.title, "reason": item[1]}
                for item in dropped_unconfirmed
            ]
        }


# Global singleton instance
pipeline = SarthiPipeline()
