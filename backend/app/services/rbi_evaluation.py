"""Compare extractive source baseline and cached/generated AI against held-out labels."""
import json
from .rbi_source import DATA, load_documents, utc_now
from .gemini_analysis import repo_rate, cached_analysis, analyze_and_cache, validate_analysis, PROMPT_VERSION, model_name
from ..models.rbi import AnalysisUnavailable


def evaluate(split="all", generate=False, limit=6):
    started_at = utc_now()
    labels = json.loads((DATA / "annotations.json").read_text(encoding="utf-8"))
    selected = [d for d in load_documents() if split == "all" or labels[d.id]["split"] == split]
    rows = []
    requested = 0
    for document in selected:
        label = labels[document.id]
        record, error, error_code = cached_analysis(document), None, None
        if generate and not record and requested < max(0,limit):
            requested += 1
            try:
                record = analyze_and_cache(document)
            except AnalysisUnavailable as exc:
                error = str(exc)
                error_code = exc.code
        analysis = record.analysis if record else None
        rows.append({
            "document_id": document.id, "source_url": document.source_url,
            "published_on": document.published_on, "text_sha256": document.text_sha256,
            "split": label["split"], "expected_repo_rate_pct": label["repo_rate_pct"],
            "decision": label["decision"],
            "baseline_repo_rate_pct": repo_rate(document),
            "baseline_correct": repo_rate(document) == label["repo_rate_pct"],
            "ai_status": "abstained" if analysis and analysis.abstain else ("generated" if analysis else
                "rejected" if error_code in {"evidence_rejected","schema_rejected","incomplete","malformed"} else
                "unavailable" if error_code else "not_generated"),
            "ai_repo_correct": analysis.repo_rate_pct == label["repo_rate_pct"] if analysis and not analysis.abstain else None,
            "citation_occurrence_valid": bool(validate_analysis(document, analysis)) if analysis else None,
            "ai_claims": [c.model_dump() for c in analysis.claims] if analysis else [],
            "resolved_model": record.resolved_model if record else None,
            "generated_at": record.generated_at if record else None,
            "error": error,
            "error_code": error_code,
            "human_factual_error_count": None, "human_citation_entailment_score": None,
            "human_relevance_score": None, "human_comprehension_score": None
        })
    generated = [r for r in rows if r["ai_status"] == "generated"]
    from .research_state import analysis_history
    attempts = [{k:v for k,v in attempt.items() if k != "id"} for attempt in analysis_history(200)
                if generate and attempt["started_at"] >= started_at and attempt["model"] == model_name()
                and attempt["prompt_version"] == PROMPT_VERSION and attempt["document_id"] in {r["document_id"] for r in rows}]
    return {"evaluated_at": utc_now(), "split": split, "model": model_name(),
            "evaluation_mode":"generate_missing" if generate else "cache_inventory",
            "prompt_version": PROMPT_VERSION, "document_count": len(rows),
            "annotation_notice": "Initial author-reviewed factual labels, not independent gold-standard annotation. No labels are sent to Gemini.",
            "baseline": {"repo_rate_exact_matches": sum(r["baseline_correct"] for r in rows), "total": len(rows)},
            "ai": {"generated": len(generated), "abstained": sum(r["ai_status"] == "abstained" for r in rows),
                   "not_generated": sum(r["ai_status"] == "not_generated" for r in rows),
                   "rejected": sum(r["ai_status"] == "rejected" for r in rows),
                   "unavailable": sum(r["ai_status"] == "unavailable" for r in rows),
                   "accepted_coverage": len(generated)/len(rows) if rows else None,
                   "repo_rate_exact_matches": sum(r["ai_repo_correct"] is True for r in generated),
                   "citation_occurrence_checks_passed": sum(r["citation_occurrence_valid"] is True for r in generated)},
            "decision_coverage": {kind:{"documents":sum(r["decision"]==kind for r in rows),
                                       "accepted":sum(r["decision"]==kind for r in generated)} for kind in ("hike","hold","cut")},
            "generation_limit":limit,"generation_requests_started":requested,
            "http_request_count":len(attempts),"provider_attempts":list(reversed(attempts)),
            "human_study": {"participants": 0, "status": "not_collected", "finding": None},
            "limitations": "Quote occurrence and rate extraction are mechanical checks, not factual entailment, relevance, comprehension or investment-performance evidence. Rejected generations are not included as accepted answers.",
            "cases": rows}
