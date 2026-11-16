"""Aggregate voluntarily shared anonymous study JSON files; never invent participants."""
import argparse
import json
from pathlib import Path


def aggregate(paths, labels, manifest=None, allow_legacy=True):
    import math
    import uuid
    from statistics import mean
    groups = {"source": [], "briefing": []}
    participants, paired, legacy_count = set(), [], 0
    for path in paths:
        record = json.loads(path.read_text(encoding="utf-8"))
        protocol = record.get("protocol")
        legacy = protocol == "rbi-comprehension-v1"
        if protocol not in {"rbi-comprehension-v1","rbi-comprehension-v2"} or record.get("consent") is not True:
            raise ValueError(f"Invalid study protocol or missing consent: {path.name}")
        if record.get("test_record"):
            raise ValueError("Test records are not participant evidence.")
        if legacy:
            if not allow_legacy: raise ValueError("Legacy files require explicit --allow-legacy and cannot verify a frozen cohort.")
            legacy_count += 1
        else:
            if not manifest or record.get("pilot_id") != manifest["pilot_id"] or record.get("manifest_sha256") != manifest["manifest_sha256"]:
                raise ValueError("Response does not match the frozen pilot manifest.")
            if record.get("adult_eligible") is not True:
                raise ValueError("Adult eligibility declaration is missing.")
            uuid.UUID(record["participant_id"])
        participant = record["participant_id"]
        if not isinstance(participant,str) or not participant.strip() or participant in participants:
            raise ValueError("Missing or duplicate participant file; aggregation stopped.")
        participants.add(participant)
        responses=record.get("responses")
        if not isinstance(responses,list) or not responses:
            raise ValueError("Incomplete participant record.")
        if not legacy:
            cases={c["document_id"]:c for c in manifest["cases"]}
            if len(responses) != len(cases) or {r["document_id"] for r in responses} != set(cases):
                raise ValueError("Participant did not complete the frozen cohort.")
            if [r["order"] for r in responses] != list(range(1,len(responses)+1)):
                raise ValueError("Invalid trial order.")
            conditions=[r["condition"] for r in responses]
            if any(a == b for a,b in zip(conditions,conditions[1:])):
                raise ValueError("Conditions must alternate within the pilot.")
        seen, personal = set(), {"source":[],"briefing":[]}
        for response in responses:
            document_id=response["document_id"]
            label = labels[document_id]
            if document_id in seen:
                raise ValueError("Repeated document within participant.")
            seen.add(document_id)
            if response["source_text_sha256"] != label["text_sha256"]:
                raise ValueError("Study source revision differs from the annotation.")
            condition=response["condition"]
            if condition not in groups: raise ValueError("Invalid study condition.")
            confidence = response["confidence"]
            rate=response["repo_rate_pct"]
            if type(confidence) is not int or not 1 <= confidence <= 5:
                raise ValueError("Invalid confidence rating.")
            if type(rate) not in {int,float} or not math.isfinite(rate) or not 0 <= rate <= 30:
                raise ValueError("Invalid rate answer.")
            if response["certainty"] not in {"yes","no","unknown"}:
                raise ValueError("Invalid certainty answer.")
            if not legacy:
                case=cases[document_id]
                if any(response.get(k) != case[k] for k in ("source_text_sha256","model","prompt_version")):
                    raise ValueError("Study model or evidence version differs from the manifest.")
                elapsed=response.get("elapsed_ms")
                if type(elapsed) not in {int,float} or not math.isfinite(elapsed) or elapsed < 0:
                    raise ValueError("Invalid elapsed time.")
            correct = (rate == label["repo_rate_pct"], response["certainty"] == "no")
            score=sum(correct)/2
            result={"score":score,"confidence":confidence,"overconfident_error":confidence >= 4 and not all(correct)}
            groups[condition].append(result)
            personal[condition].append(score)
        if all(personal.values()):
            paired.append(mean(personal["briefing"])-mean(personal["source"]))
    return {"participants": len(participants),"legacy_unfrozen_records":legacy_count,
        "pilot_id":manifest["pilot_id"] if manifest else None,
        "conditions": {group: {"trials": len(rows),
                "question_accuracy": mean(r["score"] for r in rows) if rows else None,
                "mean_confidence": mean(r["confidence"] for r in rows) if rows else None,
                "high_confidence_incorrect_trials": sum(r["overconfident_error"] for r in rows)}
            for group, rows in groups.items()},
        "paired_participants":len(paired),"mean_within_participant_accuracy_difference":mean(paired) if paired else None,
        "limitation": "Small formative study; different documents and repeated observations introduce dependence. Legacy files cannot verify a frozen cohort. Descriptive results do not establish causality or investment performance."}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    parser.add_argument("--manifest",type=Path)
    parser.add_argument("--allow-legacy",action="store_true")
    args = parser.parse_args()
    root = Path(__file__).resolve().parent.parent
    labels = json.loads((root/"backend/app/data/rbi/annotations.json").read_text(encoding="utf-8"))
    import sys
    sys.path.insert(0,str(root))
    from backend.app.services.study_protocol import load_manifest, MANIFEST
    if not args.directory.is_dir():parser.error("Response directory does not exist.")
    try:
        manifest=load_manifest(args.manifest or MANIFEST)
        result=aggregate(sorted(args.directory.glob("sarthi-study-*.json")), labels, manifest,args.allow_legacy)
    except (ValueError,KeyError,TypeError) as exc:
        parser.error(str(exc))
    print(json.dumps(result,indent=2))
