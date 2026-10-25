"""Step 1: Scan & Ingestion.

Scans trusted Indian financial sources ordered top-down by credibility tier:
Tier 1: Institutional (RBI, SEBI, Ministry of Finance, BSE/NSE)
Tier 2: Enrichment (ET, Mint, BS, Reuters)
Tier 3: Corroboration (Moneycontrol)
"""

import json
from pathlib import Path
from typing import List
from ..models.schemas import RawEvent, SourceTier

SAMPLE_FILE = Path(__file__).resolve().parent.parent / "data" / "sample_events.json"


class EventScanner:
    def __init__(self, data_path: Path = SAMPLE_FILE):
        self.data_path = data_path

    def scan_sources(self) -> List[RawEvent]:
        """Loads and sorts raw events strictly by Source Tier priority."""
        if not self.data_path.exists():
            return []

        with open(self.data_path, "r", encoding="utf-8") as f:
            items = json.load(f)

        raw_events = [RawEvent(**i) for i in items]
        # Sort primary tier first (Tier 1 before Tier 2 before Tier 3)
        raw_events.sort(key=lambda e: e.source_tier.value)
        return raw_events
