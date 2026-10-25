"""Pydantic schemas and models for Project Sarthi.

Strictly adheres to SEBI-compliant analytical taxonomy (Impact Vectors)
and zero-knowledge portfolio evaluation.
"""

from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class SourceTier(int, Enum):
    PRIMARY_INSTITUTIONAL = 1  # RBI, SEBI, Ministry of Finance, BSE/NSE
    ENRICHMENT_MEDIA = 2       # ET, Mint, BS, Reuters, Bloomberg
    CORROBORATING = 3          # Moneycontrol, small market portals


class EventCategory(str, Enum):
    POLICY_REGULATORY = "policy"
    EARNINGS_CORPORATE = "earnings"
    MACRO_ECONOMIC = "macro"
    GEOPOLITICAL = "geopolitical"


class ImpactVector(str, Enum):
    THESIS_TAILWIND = "Thesis Tailwind / Growth Acceleration"
    THESIS_HEADWIND = "Thesis Headwind / Margin Pressure"
    MONITOR_VARIANCE = "Monitor Fundamental Variance"
    NO_ACTION_CALM = "No Action / Transient Noise"


class RawEvent(BaseModel):
    id: str
    title: str
    source_name: str
    source_tier: SourceTier
    source_url: str
    category: EventCategory
    published_at: str
    content: str
    related_tickers: List[str] = Field(default_factory=list)
    sectors: List[str] = Field(default_factory=list)
    secondary_source_name: Optional[str] = None
    secondary_source_tier: Optional[SourceTier] = None


class CuratedAnalogy(BaseModel):
    id: str
    name: str
    period: str
    sectors_impacted: List[str]
    macro_context: str
    transmission_mechanism: str
    documented_outcome: str
    duration_months: int
    key_lessons: str
    counter_analogy_guidelines: str


class AuditableReasoningChain(BaseModel):
    event_detected: str
    source_verification: str
    why_it_matters: str
    transmission_chain: str
    historical_analogy_id: str
    historical_analogy_name: str
    historical_similarity: str
    counter_analogy_differences: str  # Mandatory guardrail against false equivalence
    profile_relevance: str
    impact_vector: ImpactVector
    evidence_rigour_score: int = Field(ge=0, le=100)
    explicit_caveat: str


class MorningBriefCard(BaseModel):
    id: str
    canonical_title: str
    category: EventCategory
    highest_tier: SourceTier
    source_attribution: str
    primary_sector: str
    impacted_tickers: List[str]
    impact_vector: ImpactVector
    evidence_rigour_score: int
    summary_insight: str
    reasoning_chain: AuditableReasoningChain
    published_at: str
    is_confirmed: bool = True
    passed_constraint_gate: bool = True


class UserProfile(BaseModel):
    user_id: str = "guest_user"
    display_name: str = "Prudent Investor"
    age_band: str = "30-45"
    investment_horizon: str = "long_term_5yr_plus"
    stated_risk_tolerance: str = "moderate"
    revealed_loss_tolerance_pct: float = 20.0
    disclosed_level: int = Field(default=3, ge=1, le=3)
    rough_sector_allocations: Dict[str, float] = Field(default_factory=lambda: {
        "FMCG": 20.0,
        "Banking": 30.0,
        "IT": 25.0,
        "Automotive": 15.0,
        "Metals": 10.0
    })
    avoided_sectors: List[str] = Field(default_factory=list)


class LocalHolding(BaseModel):
    ticker: str
    sector: str
    allocation_pct: float


class ChatRequest(BaseModel):
    event_id: str
    user_query: str
    conversation_history: List[Dict[str, str]] = Field(default_factory=list)


class ChatResponse(BaseModel):
    event_id: str
    response: str
    grounded_in_curated_data: bool = True
    compliance_disclaimer: str = (
        "Educational & Analytical Support Only. Sarthi does not execute trades "
        "or provide unregistered investment advice under SEBI regulations."
    )
