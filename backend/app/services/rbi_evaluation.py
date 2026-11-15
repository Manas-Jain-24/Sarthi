"""Compare extractive source baseline and cached/generated AI against held-out labels."""
import json
from .rbi_source import DATA, load_documents, utc_now
from .gemini_analysis import repo_rate, cached_analysis, analyze_and_cache, validate_analysis, PROMPT_VERSION, model_name
from ..models.rbi import AnalysisUnavailable


def evaluate(split="all", generate=False):
    labels = json.loads((DATA / "annotations.json").read_text(encoding="utf-8"))
    selected = [d for d in load_documents() if split == "all" or labels[d.id]["split"] == split]
    rows = []
    for document in selected:
        label = labels[document.id]
        record, error = cached_analysis(document), None
        if generate and not record:
            try:
                record = analyze_and_cache(document)
            except AnalysisUnavailable as exc:
                error = str(exc)
        analysis = record.analysis if record else None
        rows.append({
            "document_id": document.id, "source_url": document.source_url,
            "published_on": document.published_on, "text_sha256": document.text_sha256,
            "split": label["split"], "expected_repo_rate_pct": label["repo_rate_pct"],
            "baseline_repo_rate_pct": repo_rate(document),
            "baseline_correct": repo_rate(document) == label["repo_rate_pct"],
            "ai_status": "abstained" if analysis and analysis.abstain else ("generated" if analysis else "not_generated"),
            "ai_repo_correct": analysis.repo_rate_pct == label["repo_rate_pct"] if analysis and not analysis.abstain else None,
            "citation_occurrence_valid": bool(validate_analysis(document, analysis)) if analysis else None,
            "ai_claims": [c.model_dump() for c in analysis.claims] if analysis else [],
            "resolved_model": record.resolved_model if record else None,
            "generated_at": record.generated_at if record else None,
            "error": error,
            "human_factual_error_count": None, "human_citation_entailment_score": None,
            "human_relevance_score": None, "human_comprehension_score": None
        })
    generated = [r for r in rows if r["ai_status"] == "generated"]
    return {"evaluated_at": utc_now(), "split": split, "model": model_name(),
            "prompt_version": PROMPT_VERSION, "document_count": len(rows),
            "annotation_notice": "Initial author-reviewed factual labels, not independent gold-standard annotation. No labels are sent to Gemini.",
            "baseline": {"repo_rate_exact_matches": sum(r["baseline_correct"] for r in rows), "total": len(rows)},
            "ai": {"generated": len(generated), "abstained": sum(r["ai_status"] == "abstained" for r in rows),
                   "not_generated": sum(r["ai_status"] == "not_generated" for r in rows),
                   "repo_rate_exact_matches": sum(r["ai_repo_correct"] is True for r in generated),
                   "citation_occurrence_checks_passed": sum(r["citation_occurrence_valid"] is True for r in generated)},
            "human_study": {"participants": 0, "status": "not_collected", "finding": None},
            "limitations": "Quote occurrence and rate extraction are mechanical checks, not factual entailment, relevance, comprehension or investment-performance evidence. Rejected generations are not included as accepted answers.",
            "cases": rows}
