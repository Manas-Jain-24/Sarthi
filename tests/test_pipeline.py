"""Unit and integration tests for the Sarthi 7-step decision support pipeline."""

from backend.app.models.schemas import RawEvent, SourceTier, EventCategory, ImpactVector
from backend.app.pipeline.step1_scan import EventScanner
from backend.app.pipeline.step2_classify import EventClassifier
from backend.app.pipeline.step3_deduplicate import EventDeduplicator, ClusteredEvent
from backend.app.pipeline.step4_confirm import EventConfirmationGate
from backend.app.pipeline.step5_reason import EventReasoner
from backend.app.pipeline.step6_constrain import ConstraintGate
from backend.app.pipeline.step7_output import OutputFormatter
from backend.app.pipeline.orchestrator import SarthiPipeline


def test_step1_scanner():
    scanner = EventScanner()
    events = scanner.scan_sources()
    assert len(events) > 0
    # Tier 1 events should appear before Tier 2 or 3
    assert events[0].source_tier == SourceTier.PRIMARY_INSTITUTIONAL


def test_step2_classifier():
    classifier = EventClassifier()
    event = RawEvent(
        id="T1",
        title="Ministry of Finance issues circular on GST tax rationalization",
        source_name="PIB",
        source_tier=SourceTier.PRIMARY_INSTITUTIONAL,
        source_url="http://pib.gov.in",
        category=EventCategory.POLICY_REGULATORY,
        published_at="2026-10-25T10:00:00Z",
        content="Excise and tax rates adjusted."
    )
    cat = classifier.classify_event(event)
    assert cat == EventCategory.POLICY_REGULATORY


def test_step4_confirmation_gate():
    gate = EventConfirmationGate()

    # Case A: Single Tier 1 event -> Confirmed
    t1_event = RawEvent(
        id="T1",
        title="RBI cuts repo rate by 25 bps",
        source_name="Reserve Bank of India",
        source_tier=SourceTier.PRIMARY_INSTITUTIONAL,
        source_url="http://rbi.org.in",
        category=EventCategory.MACRO_ECONOMIC,
        published_at="2026-10-25T10:00:00Z",
        content="Official policy statement."
    )
    cluster1 = ClusteredEvent(t1_event, EventCategory.MACRO_ECONOMIC)
    confirmed, reason = gate.verify_confirmation(cluster1)
    assert confirmed is True
    assert "Tier 1" in reason

    # Case B: Unconfirmed Tier 3 rumor -> Dropped (Silence is a feature)
    t3_event = RawEvent(
        id="T3",
        title="Unverified blog claims SEBI will ban intraday trading",
        source_name="RumorBlog",
        source_tier=SourceTier.CORROBORATING,
        source_url="http://rumor.com",
        category=EventCategory.POLICY_REGULATORY,
        published_at="2026-10-25T10:00:00Z",
        content="Speculation only."
    )
    cluster3 = ClusteredEvent(t3_event, EventCategory.POLICY_REGULATORY)
    confirmed3, reason3 = gate.verify_confirmation(cluster3)
    assert confirmed3 is False
    assert "Dropped" in reason3


def test_step5_reasoner_anti_hallucination():
    reasoner = EventReasoner()
    t1_event = RawEvent(
        id="T1",
        title="Ministry of Finance notifies 16% escalation in cigarette excise duty",
        source_name="PIB",
        source_tier=SourceTier.PRIMARY_INSTITUTIONAL,
        source_url="http://pib.gov.in",
        category=EventCategory.POLICY_REGULATORY,
        published_at="2026-10-25T10:00:00Z",
        content="Official tax notification.",
        related_tickers=["ITC"],
        sectors=["FMCG", "Tobacco"]
    )
    cluster = ClusteredEvent(t1_event, EventCategory.POLICY_REGULATORY)
    chain = reasoner.reason_through_event(cluster)

    assert chain.historical_analogy_id == "IND_TOBACCO_2020"
    assert len(chain.counter_analogy_differences) > 0
    assert chain.impact_vector == ImpactVector.THESIS_HEADWIND
    assert chain.evidence_rigour_score >= 65


def test_step6_constraint_gate_blocks_forbidden_claims():
    reasoner = EventReasoner()
    t1_event = RawEvent(
        id="T1",
        title="Demerger announcement",
        source_name="BSE",
        source_tier=SourceTier.PRIMARY_INSTITUTIONAL,
        source_url="http://bse.in",
        category=EventCategory.EARNINGS_CORPORATE,
        published_at="2026-10-25T10:00:00Z",
        content="Demerger",
        related_tickers=["TATAMOTORS"],
        sectors=["Automotive"]
    )
    cluster = ClusteredEvent(t1_event, EventCategory.EARNINGS_CORPORATE)
    chain = reasoner.reason_through_event(cluster)

    # Valid chain passes
    passed, msg = ConstraintGate.apply_constraints(cluster, chain)
    assert passed is True

    # Artificially inject a forbidden price target -> Gate must block it
    chain.why_it_matters += " Target price ₹1,200 guaranteed return."
    passed2, msg2 = ConstraintGate.apply_constraints(cluster, chain)
    assert passed2 is False
    assert "Prohibited" in msg2


def test_full_pipeline_orchestration():
    pipeline = SarthiPipeline()
    result = pipeline.run_morning_pipeline()

    stats = result["stats"]
    assert stats["scanned"] >= 5
    assert stats["confirmed"] >= 3
    assert stats["dropped_at_confirm"] >= 1  # The Tier 3 rumor was dropped
    assert len(result["morning_brief"]) >= 3
    assert len(result["dropped_events_audit"]) >= 1

    # Check that Morning Brief cards contain all SEBI-compliant fields
    card = result["morning_brief"][0]
    assert card.evidence_rigour_score >= 65
    assert card.reasoning_chain.counter_analogy_differences != ""
    assert card.reasoning_chain.explicit_caveat != ""
