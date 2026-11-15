"""Aggregate voluntarily shared anonymous study JSON files; never invent participants."""
import argparse
import json
from pathlib import Path


def aggregate(paths, labels):
    groups = {"source": [], "briefing": []}
    participants = set()
    for path in paths:
        record = json.loads(path.read_text(encoding="utf-8"))
        if record.get("protocol") != "rbi-comprehension-v1" or record.get("consent") is not True:
            raise ValueError(f"Invalid study protocol or missing consent: {path.name}")
        participant = record["participant_id"]
        if participant in participants:
            raise ValueError("Duplicate participant file; aggregation stopped.")
        participants.add(participant)
        seen = set()
        for response in record["responses"]:
            label = labels[response["document_id"]]
            if response["document_id"] in seen:
                raise ValueError("Repeated document within participant.")
            seen.add(response["document_id"])
            if response["source_text_sha256"] != label["text_sha256"]:
                raise ValueError("Study source revision differs from the annotation.")
            confidence = response["confidence"]
            if not isinstance(confidence, int) or not 1 <= confidence <= 5:
                raise ValueError("Invalid confidence rating.")
            correct = (response["repo_rate_pct"] == label["repo_rate_pct"]) + (response["certainty"] == "no")
            groups[response["condition"]].append({"correct": correct, "confidence": confidence,
                                                  "overconfident_error": confidence >= 4 and correct < 2})
    return {"participants": len(participants), "conditions": {
        group: {"trials": len(rows), "question_accuracy": sum(r["correct"] for r in rows)/(2*len(rows)) if rows else None,
                "mean_confidence": sum(r["confidence"] for r in rows)/len(rows) if rows else None,
                "high_confidence_incorrect_trials": sum(r["overconfident_error"] for r in rows)}
        for group, rows in groups.items()},
        "limitation": "Small formative study; different documents and repeated participants introduce dependence. These descriptive results do not establish causality, reduced panic-selling, or investment performance."}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    args = parser.parse_args()
    root = Path(__file__).resolve().parent.parent
    labels = json.loads((root/"backend/app/data/rbi/annotations.json").read_text(encoding="utf-8"))
    print(json.dumps(aggregate(sorted(args.directory.glob("sarthi-study-*.json")), labels), indent=2))
