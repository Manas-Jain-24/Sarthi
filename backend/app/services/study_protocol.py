"""Frozen public materials: later refreshes cannot change an ongoing pilot."""
import json
from .rbi_source import DATA, digest, utc_now, load_documents
from .gemini_analysis import cached_analysis, validate_analysis
from .rbi_brief import baseline_paragraph
from ..models.rbi import AnalysisRecord

MANIFEST = DATA / "study_manifest.json"
PROTOCOL = "rbi-comprehension-v2"


def briefing_text(analysis):
    return "\n\n".join([f"{claim.kind.title()}: {claim.text}" for claim in analysis.claims]+
                        ["Uncertainty: "+s for s in analysis.uncertainties]+
                        ["Counterargument: "+s for s in analysis.counterarguments])


def fingerprint(payload):
    return digest(json.dumps({k:v for k,v in payload.items() if k != "manifest_sha256"},
                             sort_keys=True,separators=(",",":"),ensure_ascii=False).encode())


def prepare(document_ids, path=MANIFEST):
    if path.exists():
        raise ValueError("A frozen pilot already exists. Use a new manifest path for a new cohort.")
    if len(document_ids) not in {2,4} or len(set(document_ids)) != len(document_ids):
        raise ValueError("Select two or four distinct documents with accepted analyses.")
    documents={d.id:d for d in load_documents()}
    cases=[]
    for document_id in document_ids:
        document=documents[document_id]
        record=cached_analysis(document)
        if not record or record.analysis.abstain:
            raise ValueError(f"No accepted analysis for {document_id}.")
        analysis=record.analysis
        cases.append({"document_id":document.id,"title":document.title,"source_url":document.source_url,
                      "source_text_sha256":document.text_sha256,"model":record.resolved_model,
                      "prompt_version":record.prompt_version,"record":record.model_dump(),
                      "baseline":baseline_paragraph(document).text,
                      "briefing":briefing_text(analysis)})
    payload={"protocol":PROTOCOL,"pilot_id":"rbi-pilot-"+utc_now()[:10],"created_at":utc_now(),
             "review_status":"Implementation checks passed; independent human entailment review pending.","cases":cases}
    payload["manifest_sha256"]=fingerprint(payload)
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(payload,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    return payload


def load_manifest(path=MANIFEST):
    if not path.exists():
        return None
    payload=json.loads(path.read_text(encoding="utf-8"))
    if payload.get("protocol") != PROTOCOL or payload.get("manifest_sha256") != fingerprint(payload):
        raise ValueError("Study manifest integrity check failed.")
    documents={d.id:d for d in load_documents()}
    ids=[c["document_id"] for c in payload["cases"]]
    if len(ids) not in {2,4} or len(set(ids)) != len(ids):
        raise ValueError("Invalid study cohort.")
    for case in payload["cases"]:
        document=documents[case["document_id"]]
        record=AnalysisRecord.model_validate(case["record"])
        if case["source_text_sha256"] != document.text_sha256 or record.text_sha256 != document.text_sha256:
            raise ValueError("Study source revision changed; prepare a new cohort.")
        if record.document_id != document.id or record.analysis.abstain:
            raise ValueError("Invalid frozen analysis.")
        validate_analysis(document,record.analysis)
        if (case["baseline"] != baseline_paragraph(document).text or case["briefing"] != briefing_text(record.analysis)
                or case["model"] != record.resolved_model or case["prompt_version"] != record.prompt_version
                or case["title"] != document.title or case["source_url"] != document.source_url):
            raise ValueError("Displayed study material differs from its evidence or frozen analysis.")
    return payload


def public_material():
    payload=load_manifest()
    if payload is None:
        return {"cases":[],"minimum_cases":2,"notice":"The researcher must freeze pilot materials before enrollment."}
    return {"protocol":payload["protocol"],"pilot_id":payload["pilot_id"],"manifest_sha256":payload["manifest_sha256"],
            "cases":[{k:v for k,v in case.items() if k != "record"} for case in payload["cases"]],
            "minimum_cases":2,"notice":"Fixed public-document materials. Responses stay in this browser until downloaded."}
