"""Step 2: Classify.

Places each event into one of four specific categories:
- Policy / Regulatory
- Earnings / Corporate Action
- Macro / Economic
- Geopolitical
"""

from typing import List, Tuple
from ..models.schemas import RawEvent, EventCategory


class EventClassifier:
    @staticmethod
    def classify_event(event: RawEvent) -> EventCategory:
        """Determines the structural category of an incoming event."""
        # If pre-tagged correctly, validate or re-verify based on content
        content_lower = f"{event.title} {event.content}".lower()

        if any(w in content_lower for w in ["excise", "nccd", "gst", "sebi", "notification", "ministry of finance", "tax", "rbi circular"]):
            return EventCategory.POLICY_REGULATORY
        elif any(w in content_lower for w in ["demerger", "merger", "nclt", "capex", "ebitda", "quarterly results", "dividend"]):
            return EventCategory.EARNINGS_CORPORATE
        elif any(w in content_lower for w in ["repo rate", "mpc", "cpi", "inflation", "gdp", "iip", "monetary policy"]):
            return EventCategory.MACRO_ECONOMIC
        elif any(w in content_lower for w in ["freight", "red sea", "crude oil", "shipping", "sanction", "war", "bunker"]):
            return EventCategory.GEOPOLITICAL

        return event.category

    def classify_batch(self, events: List[RawEvent]) -> List[Tuple[RawEvent, EventCategory]]:
        return [(event, self.classify_event(event)) for event in events]
