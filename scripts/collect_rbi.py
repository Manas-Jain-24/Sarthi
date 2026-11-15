"""Fetch a reproducible seed corpus of 11 original RBI MPC resolutions."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from backend.app.services.rbi_source import DATA, retrieve_document, save_documents

SEEDS = [56888, 57275, 58050, 58447, 59244, 59692, 60604, 60957, 61332, 61749, 62169]


def main():
    documents = []
    for release_id in SEEDS:
        document = retrieve_document(f"https://www.rbi.org.in/Scripts/BS_PressReleaseDisplay.aspx?prid={release_id}")
        documents.append(document)
        print(f"Saved {document.id} | {document.published_on} | {len(document.paragraphs)} evidence paragraphs", flush=True)
    save_documents(documents)
    print(f"Saved {len(documents)} RBI documents and originals to {DATA}")


if __name__ == "__main__":
    main()
