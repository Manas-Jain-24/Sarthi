"""Read-only brief construction and explicit, bounded live refresh."""
from pathlib import Path
from ..models.schemas import AuditableReasoningChain, MorningBriefCard, EventCategory, ImpactVector, SourceTier
from .rbi_source import load_documents
from .gemini_analysis import cached_analysis, model_name

LIVE = Path(__file__).resolve().parents[3] / ".cache" / "rbi_live"


def all_documents():
    docs = {d.id: d for d in load_documents()}
    try:
        docs.update({d.id: d for d in load_documents(LIVE)})
    except (ValueError,OSError):
        # The status endpoint exposes this integrity failure; never serve bad live data.
        pass
    return sorted(docs.values(), key=lambda d: d.published_on, reverse=True)


def baseline_paragraph(document):
    return next((p for p in document.paragraphs[:6] if "policy repo rate" in p.text.lower()), document.paragraphs[0])


def make_card(document, record=None, attempt=None):
    baseline = baseline_paragraph(document)
    analysis = record.analysis if record else None
    generated = bool(analysis and not analysis.abstain)
    interpretations = [c.text for c in analysis.claims if c.kind == "interpretation"] if generated else []
    evidence = f"Archived RBI original; retrieved {document.retrieved_at[:10]}. Publication date shown separately."
    why = " ".join(interpretations) if generated else "Source-only baseline. AI interpretation has not been generated."
    if analysis and analysis.abstain:
        why = "Gemini abstained: " + analysis.abstention_reason
    elif not analysis and attempt:
        why = "Source-only. Latest Gemini request: " + (attempt.get("error_code") or attempt["status"]).replace("_"," ") + ". No interpretation was accepted."
    impact = "AI hypothesis; requires human review" if generated else "No AI conclusion; source-only baseline"
    chain = AuditableReasoningChain(
        event_detected=document.title, source_verification=evidence,
        why_it_matters=why, transmission_chain=why,
        historical_analogy_id="", historical_analogy_name="No historical analogy inferred",
        historical_similarity="This path uses the current document only.",
        counter_analogy_differences=" ".join(analysis.counterarguments) if generated else "Source text does not establish portfolio returns or company-level effects.",
        profile_relevance="Local exposure mapping is a heuristic; no holdings are sent to Gemini.",
        impact_vector=ImpactVector.MONITOR_VARIANCE if generated else ImpactVector.INSUFFICIENT_EVIDENCE,
        evidence_status=evidence, impact_status=impact, analysis_available=generated,
        explicit_caveat=" ".join(analysis.uncertainties) if generated else "The announcement alone does not establish future rates, profits, or stock returns."
    )
    return MorningBriefCard(
        id=document.id, canonical_title=document.title, category=EventCategory.MACRO_ECONOMIC,
        highest_tier=SourceTier.PRIMARY_INSTITUTIONAL, source_attribution="Reserve Bank of India · original MPC resolution",
        primary_sector="Banking", impacted_tickers=[], impact_vector=chain.impact_vector,
        evidence_status=evidence, impact_status=impact, is_sample=False,
        sectors=analysis.affected_sectors if generated else ["Banking", "NBFCs", "Real Estate", "Automotive"],
        evidence_excerpt=baseline.text, source_url=document.source_url,
        reference_url=document.source_url, gate_reason="Source archive integrity checked. Quote occurrence is checked for AI claims; entailment needs human review.",
        summary_insight=interpretations[0] if interpretations else baseline.text,
        reasoning_chain=chain, published_at=document.published_on,
        is_confirmed=True, passed_constraint_gate=True,
        evidence_paragraphs=[p.model_dump() for p in document.paragraphs],
        cited_claims=[c.model_dump() for c in analysis.claims] if generated else [],
        analysis_model=record.resolved_model if record else "",
        analysis_generated_at=record.generated_at if record else "",
        analysis_status="generated" if generated else ("abstained" if analysis else attempt["status"] if attempt else "not_generated"),
        baseline_text=baseline.text,
        source_text_sha256=document.text_sha256
    )


def build_rbi_brief():
    documents = all_documents()
    from .research_state import analysis_history
    from .gemini_analysis import PROMPT_VERSION
    attempts={}
    for attempt in analysis_history(200):
        if attempt["model"] == model_name() and attempt["prompt_version"] == PROMPT_VERSION:
            attempts.setdefault((attempt["document_id"],attempt["text_sha256"]),attempt)
    cards = [make_card(d, cached_analysis(d),attempts.get((d.id,d.text_sha256))) for d in documents]
    from .research_refresh import status
    freshness = status(documents)
    refresh = freshness["history"][0]["details"] if freshness["history"] else None
    return {"mode": "rbi", "data_notice": "Real archived RBI resolutions. Dates are publication dates, not today's news. Gemini runs only when you request analysis.",
            "stats": {"scanned": len(cards), "confirmed": len(cards), "dropped_at_confirm": 0,
                      "passed_constraint": sum(c.analysis_status == "generated" for c in cards)},
            "morning_brief": cards, "explore_feed": [], "dropped_events_audit": [],
            "model": model_name(), "last_refresh": refresh,
            "freshness": freshness}


def refresh_live(limit=6):
    from .research_refresh import refresh
    return refresh(limit=limit)
