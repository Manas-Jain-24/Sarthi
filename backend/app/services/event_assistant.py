"""Event-Scoped Assistant Service.

Provides an isolated conversational interrogation layer for any specific event card.
Allows the user to probe the reasoning chain, challenge the historical analogy,
and ask about sector exposure.
"""

from typing import Dict, Any, List
from ..pipeline.orchestrator import pipeline


class EventAssistantService:
    @staticmethod
    def answer_query(event_id: str, user_query: str, history: List[Dict[str, str]] = None) -> Dict[str, Any]:
        """Provides grounded educational and analytical responses strictly scoped to the event."""
        # Find the card from the pipeline
        data = pipeline.run_morning_pipeline()
        all_cards = data["morning_brief"] + data["explore_feed"]
        card = next((c for c in all_cards if c.id == event_id), None)

        if not card:
            return {
                "event_id": event_id,
                "response": "Event not found in today's verified brief.",
                "grounded_in_curated_data": False
            }

        q = user_query.lower()
        chain = card.reasoning_chain

        if any(term in q for term in ["buy", "sell", "tip", "price target"]):
            response = "This demo cannot recommend trades or price targets. The analysis is an illustrative hypothesis, not a validated investment conclusion."
        elif "why" in q or "reason" in q or "logic" in q:
            response = (
                f"**First-Principles Reasoning for {card.canonical_title[:50]}...**:\n\n"
                f"• **Transmission Channel**: {chain.transmission_chain}\n"
                f"• **Economic Rationale**: {chain.why_it_matters}\n"
                f"• **Current Assessment**: Classified as **{chain.impact_vector.value}** "
                f"as an illustrative, unvalidated hypothesis. Evidence status: {chain.evidence_status}."
            )
        elif "analogy" in q or "history" in q or "past" in q or "precedent" in q:
            response = (
                f"**Historical Grounding: {chain.historical_analogy_name}**\n\n"
                f"• **Historical Similarity**: {chain.historical_similarity}\n\n"
                f"• **Mandatory Counter-Analogy (Key Differences Today)**: {chain.counter_analogy_differences}\n\n"
                "*(Note: Sarthi strictly forbids numeric historical forecasts. Analogies are qualitative only.)*"
            )
        elif "risk" in q or "caveat" in q or "downside" in q or "uncertainty" in q:
            response = (
                f"**Explicit Uncertainties & Caveats**:\n\n"
                f"• {chain.explicit_caveat}\n"
                f"• Sarthi maintains that the input is synthetic and not independently verified ({chain.source_verification}), "
                "market reaction timing depends on quarterly earnings realization and broader macro liquidity."
            )
        else:
            response = (
                f"Regarding **{card.canonical_title}**:\n\n"
                f"{chain.why_it_matters}\n\n"
                f"**Historical Precedent**: Grounded in {chain.historical_analogy_name}.\n"
                f"**Key Caveat**: {chain.explicit_caveat}"
            )

        return {
            "event_id": event_id,
            "response": "Demo response from a reviewed sample; no AI model or live verification.\n\n" + response,
            "grounded_in_curated_data": False,
            "impact_vector": chain.impact_vector.value,
            "impact_status": chain.impact_status
        }


event_assistant = EventAssistantService()
