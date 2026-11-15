"""Script to launch Sarthi FastAPI server with Uvicorn."""

import sys
from pathlib import Path
import uvicorn

# Ensure project root is in sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

def start():
    print("=" * 65)
    print("SARTHI: AI-ASSISTED INVESTMENT DECISION SUPPORT SYSTEM (v2.0)")
    print("RBI evidence, optional Gemini analysis, and local portfolio matching")
    print("=" * 65)
    print("Running on http://localhost:8000")
    print("Open http://localhost:8000 in your browser to view the application.")
    print("=" * 65)
    uvicorn.run("backend.app.main:app", host="127.0.0.1", port=8000, reload=True)

if __name__ == "__main__":
    start()
