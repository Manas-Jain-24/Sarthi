"""Check the RBI policy listing and RSS; archive at most six supported resolutions."""
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from backend.app.services.rbi_brief import refresh_live

if __name__ == "__main__":
    print(json.dumps(refresh_live(), indent=2))
