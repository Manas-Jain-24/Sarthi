"""Script to launch Sarthi FastAPI server with Uvicorn."""

import sys
from pathlib import Path
import uvicorn

# Ensure project root is in sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

def start():
    print("=" * 65)
    print("SARTHI: AI-ASSISTED INVESTMENT DECISION SUPPORT SYSTEM (v2.0)")
    print("Institutional Noise-Cancellation · SEBI-Compliant Decision Support")
    print("=" * 65)
    print("Running on http://localhost:8000")
    print("Open http://localhost:8000 in your browser to view the application.")
    print("=" * 65)
    uvicorn.run("backend.app.main:app", host="0.0.0.0", port=8000, reload=True)

if __name__ == "__main__":
    start()
