"""FastAPI application entry point for Sarthi.

Exposes REST APIs for the 7-step reasoning pipeline, curated historical dataset,
behavioral risk calibration, and event-scoped scrutiny assistant.
Mounts the static frontend for the client-side edge-matching web app.
"""

from pathlib import Path
from typing import Dict, Any, List
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from .models.schemas import (
    MorningBriefCard,
    CuratedAnalogy,
    ChatRequest,
    ChatResponse
)
from .pipeline.orchestrator import pipeline
from .services.analogy_service import analogy_service
from .services.risk_profiler import RiskProfiler
from .services.event_assistant import event_assistant

BASE_DIR = Path(__file__).resolve().parent.parent.parent
FRONTEND_DIR = BASE_DIR / "frontend"

app = FastAPI(
    title="Sarthi: AI-Assisted Investment Decision Support System",
    description=(
        "Institutional-grade noise-cancellation engine for Indian retail investors. "
        "Conservative by default. Reasoning-first always. Silence is a feature."
    ),
    version="2.0.0"
)

# Enable CORS for edge clients
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/v1/health")
def health_check() -> Dict[str, str]:
    return {
        "status": "healthy",
        "system": "Sarthi Decision Support Engine",
        "version": "2.0.0"
    }


@app.get("/api/v1/pipeline/run")
def trigger_pipeline() -> Dict[str, Any]:
    """Manually triggers the full 7-step pipeline and returns execution telemetry."""
    return pipeline.run_morning_pipeline()


@app.get("/api/v1/brief/daily", response_model=List[MorningBriefCard])
def get_daily_brief() -> List[MorningBriefCard]:
    """Returns today's verified Morning Brief cards.

    These cards are broadcasted to the client. The client-side edge engine
    matches them against the user's local Level 3 portfolio without sending
    portfolio holdings to the server.
    """
    result = pipeline.run_morning_pipeline()
    return result["morning_brief"]


@app.get("/api/v1/brief/explore", response_model=List[MorningBriefCard])
def get_explore_feed() -> List[MorningBriefCard]:
    """Returns events that did not cross the Morning Brief priority threshold.

    Available for broad macro exploration without personal ranking.
    """
    result = pipeline.run_morning_pipeline()
    return result["explore_feed"]


@app.get("/api/v1/events/{event_id}", response_model=MorningBriefCard)
def get_event_detail(event_id: str) -> MorningBriefCard:
    """Returns the full event card and its 6-stage auditable reasoning chain."""
    result = pipeline.run_morning_pipeline()
    all_cards = result["morning_brief"] + result["explore_feed"]
    card = next((c for c in all_cards if c.id == event_id), None)
    if not card:
        raise HTTPException(status_code=404, detail="Event not found in daily records.")
    return card


@app.get("/api/v1/analogies", response_model=List[CuratedAnalogy])
def get_curated_analogies() -> List[CuratedAnalogy]:
    """Returns the curated dataset of 20 milestone Indian economic and policy precedents."""
    return analogy_service.get_all()


@app.get("/api/v1/analogies/{analogy_id}", response_model=CuratedAnalogy)
def get_analogy(analogy_id: str) -> CuratedAnalogy:
    analogy = analogy_service.get_by_id(analogy_id)
    if not analogy:
        raise HTTPException(status_code=404, detail=f"Analogy {analogy_id} not found.")
    return analogy


@app.post("/api/v1/onboarding/calibrate")
def calibrate_risk_profile(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Performs Kahneman-Tversky behavioral risk calibration.

    Cross-checks stated risk against revealed behavior in a simulated rupee loss.
    """
    base_portfolio = float(payload.get("portfolio_size_inr", 1000000))
    scenario_response = payload.get("scenario_response", "hold_patient")
    stated_tolerance = payload.get("stated_risk_tolerance", "moderate")
    horizon = payload.get("investment_horizon", "long_term_5yr_plus")

    return RiskProfiler.calculate_revealed_profile(
        base_portfolio_inr=base_portfolio,
        scenario_response=scenario_response,
        stated_tolerance=stated_tolerance,
        investment_horizon=horizon
    )


@app.post("/api/v1/chat/event-assistant", response_model=ChatResponse)
def query_event_assistant(req: ChatRequest) -> ChatResponse:
    """Interrogates an event card with context-bound analytical reasoning.

    Refuses stock tips or price targets under SEBI analytical guidelines.
    """
    res = event_assistant.answer_query(
        event_id=req.event_id,
        user_query=req.user_query,
        history=req.conversation_history
    )
    return ChatResponse(
        event_id=res["event_id"],
        response=res["response"],
        grounded_in_curated_data=res["grounded_in_curated_data"]
    )


# Serve Static Frontend Files
if FRONTEND_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")

    @app.get("/")
    def serve_index():
        return FileResponse(FRONTEND_DIR / "index.html")

    @app.get("/onboarding")
    def serve_onboarding():
        return FileResponse(FRONTEND_DIR / "onboarding.html")
