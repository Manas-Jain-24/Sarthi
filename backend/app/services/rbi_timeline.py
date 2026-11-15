"""Dated observations from the archive; never interpolate missing meetings."""
from datetime import date
import re
from .rbi_brief import all_documents, baseline_paragraph
from .gemini_analysis import repo_rate


def build_timeline():
    documents = sorted(all_documents(), key=lambda d: (d.published_on, d.id))
    observations = []
    for document in documents:
        rate = repo_rate(document)
        paragraph = baseline_paragraph(document)
        decision = "unspecified"
        text = paragraph.text.lower()
        if re.search(r"\b(reduce|reduced)\b", text):
            decision = "cut"
        elif re.search(r"\b(increase|increased|raise|raised)\b", text):
            decision = "hike"
        elif re.search(r"\b(unchanged|maintain|keep)\b", text):
            decision = "unchanged"
        previous = observations[-1] if observations else None
        delta = round((rate - previous["repo_rate_pct"])*100, 6) if previous and rate is not None and previous["repo_rate_pct"] is not None else None
        observations.append({"id": document.id, "title": document.title,
                             "published_on": document.published_on, "repo_rate_pct": rate,
                             "decision_wording": decision,
                             "change_since_previous_archived_bps": delta,
                             "days_since_previous_archived": (date.fromisoformat(document.published_on)-date.fromisoformat(previous["published_on"])).days if previous else None,
                             "source_url": document.source_url, "paragraph_id": paragraph.id,
                             "evidence_excerpt": paragraph.text, "source_text_sha256": document.text_sha256})
    return {"observations": observations,
            "coverage": {"count": len(observations), "from": observations[0]["published_on"] if observations else None,
                         "through": observations[-1]["published_on"] if observations else None},
            "notice": "Observed archive snapshots only. Missing meetings are not filled. Differences compare consecutive archived observations and may span multiple policy meetings."}
