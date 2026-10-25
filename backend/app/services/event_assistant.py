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

        if "why" in q or "reason" in q or "logic" in q:
            response = (
                f"**First-Principles Reasoning for {card.canonical_title[:50]}...**:\n\n"
                f"• **Transmission Channel**: {chain.transmission_chain}\n"
                f"• **Economic Rationale**: {chain.why_it_matters}\n"
                f"• **Current Assessment**: Classified as **{chain.impact_vector.value}** "
                f"with an evidence rigour score of {chain.evidence_rigour_score}/100."
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
                f"• Sarthi maintains that while the institutional announcement is verified ({chain.source_verification}), "
                "market reaction timing depends on quarterly earnings realization and broader macro liquidity."
            )
        elif "buy" in q or "sell" in q or "tip" in q or "price target" in q:
            response = (
                "**Regulatory & Design Notice**: Sarthi never issues Buy/Sell tips or price predictions. "
                f"Under SEBI analytical guidelines, our system provides decision support through "
                f"**{chain.impact_vector.value}** to help you evaluate your own long-term investment thesis."
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
            "response": response,
            "grounded_in_curated_data": True,
            "impact_vector": chain.impact_vector.value,
            "evidence_rigour_score": chain.evidence_rigour_score
        }


event_assistant = EventAssistantService()
