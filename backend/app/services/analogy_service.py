"""Service for loading and matching curated landmark Indian economic precedents."""

import json
from pathlib import Path
from typing import List, Optional
from ..models.schemas import CuratedAnalogy

DATA_FILE = Path(__file__).resolve().parent.parent / "data" / "curated_analogies.json"


class AnalogyService:
    def __init__(self):
        self._analogies: List[CuratedAnalogy] = []
        self._load_data()

    def _load_data(self):
        if not DATA_FILE.exists():
            raise FileNotFoundError(f"Curated analogies dataset missing at {DATA_FILE}")
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            self._analogies = [CuratedAnalogy(**item) for item in data]

    def get_all(self) -> List[CuratedAnalogy]:
        return self._analogies

    def get_by_id(self, analogy_id: str) -> Optional[CuratedAnalogy]:
        for a in self._analogies:
            if a.id.lower() == analogy_id.lower():
                return a
        return None

    def match_precedent(self, sectors: List[str], category: str, title: str) -> CuratedAnalogy:
        """Finds the most structurally sound historical precedent.

        Prioritizes sector overlap and regulatory similarity without making
        unverifiable numerical assumptions.
        """
        title_lower = title.lower()
        sectors_lower = {s.lower() for s in sectors}

        # 1. Exact theme / keyword matches for key historical policy levers
        if "tobacco" in sectors_lower or "cigarette" in title_lower or "nccd" in title_lower:
            match = self.get_by_id("IND_TOBACCO_2020")
            if match:
                return match

        if "demerger" in title_lower or "nclt" in title_lower or "consolidation" in title_lower:
            match = self.get_by_id("IND_BANK_MERGER_2019") or self.get_by_id("IND_CORP_TAX_2019")
            if match:
                return match

        if "repo rate" in title_lower or "mpc" in title_lower or "monetary policy" in title_lower:
            match = self.get_by_id("IND_RBI_HIKE_2022")
            if match:
                return match

        if "freight" in title_lower or "shipping" in title_lower or "crude" in title_lower or "oil" in title_lower:
            match = self.get_by_id("IND_CRUDE_SHOCK_2022")
            if match:
                return match

        if "steel" in sectors_lower or "metals" in sectors_lower or "export duty" in title_lower:
            match = self.get_by_id("IND_STEEL_DUTY_2022")
            if match:
                return match

        # 2. Score by sector intersection
        best_match = self._analogies[0]
        max_overlap = -1
        for a in self._analogies:
            overlap = len(set(s.lower() for s in a.sectors_impacted).intersection(sectors_lower))
            if overlap > max_overlap:
                max_overlap = overlap
                best_match = a

        return best_match


# Global singleton instance
analogy_service = AnalogyService()
