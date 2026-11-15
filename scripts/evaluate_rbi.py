"""python scripts/evaluate_rbi.py [--split holdout] [--generate]."""
import argparse
import csv
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from backend.app.services.rbi_evaluation import evaluate


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--split", choices=["all", "development", "holdout"], default="all")
    parser.add_argument("--generate", action="store_true", help="Explicitly make Gemini requests for missing analyses (uses quota).")
    args = parser.parse_args()
    result = evaluate(args.split, args.generate)
    out = Path("output/rbi_evaluation")
    out.mkdir(parents=True, exist_ok=True)
    (out / "report.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    with (out / "review.csv").open("w", newline="", encoding="utf-8") as f:
        fields = ["document_id", "source_url", "split", "ai_status", "human_factual_error_count",
                  "human_citation_entailment_score", "human_relevance_score", "human_comprehension_score"]
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(result["cases"])
    print(json.dumps({k: v for k, v in result.items() if k != "cases"}, indent=2))
    print("Report: output/rbi_evaluation/report.json; manual review: output/rbi_evaluation/review.csv")


if __name__ == "__main__":
    main()
