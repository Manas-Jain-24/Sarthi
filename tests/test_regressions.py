"""Behavioral checks for demo honesty, abstention, provenance and API output."""
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.models.schemas import EventCategory, SourceTier
from backend.app.pipeline.step1_scan import EventScanner
from backend.app.pipeline.step3_deduplicate import ClusteredEvent, EventDeduplicator
from backend.app.pipeline.step4_confirm import EventConfirmationGate
from backend.app.pipeline.step5_reason import EventReasoner
from backend.app.pipeline.step6_constrain import ConstraintGate
from backend.app.pipeline.orchestrator import SarthiPipeline


def test_unknown_and_changed_input_abstain():
    event = EventScanner().scan_sources()[0]
    for update in [{"id": "UNKNOWN"}, {"content": "Tax reduced instead of raised"}, {"is_sample": False}]:
        cluster = ClusteredEvent(event.model_copy(update=update), event.category)
        chain = EventReasoner().reason_through_event(cluster)
        assert not chain.analysis_available
        assert not ConstraintGate.apply_constraints(cluster, chain)[0]


def test_same_publisher_cannot_confirm_itself():
    event = EventScanner().scan_sources()[0].model_copy(update={
        "source_name": "Publisher", "source_tier": SourceTier.ENRICHMENT_MEDIA,
        "source_url": "https://publisher.example/a", "secondary_source_name": "Publisher",
        "secondary_source_tier": SourceTier.ENRICHMENT_MEDIA})
    cluster = ClusteredEvent(event, event.category)
    cluster.add_source("Other label", SourceTier.ENRICHMENT_MEDIA, "https://www.publisher.example/b")
    assert cluster.source_count == 1
    assert not EventConfirmationGate.verify_confirmation(cluster)[0]
    cluster.add_source("Second publisher", SourceTier.ENRICHMENT_MEDIA, "https://second.example/a")
    assert EventConfirmationGate.verify_confirmation(cluster)[0]


def test_dates_and_categories_do_not_merge():
    event = EventScanner().scan_sources()[0]
    changed_date = event.model_copy(update={"published_at": "2020-01-01T00:00:00Z"})
    clusters = EventDeduplicator().cluster_events([(event, event.category), (changed_date, event.category), (event, EventCategory.GEOPOLITICAL)])
    assert len(clusters) == 3


def test_forbidden_claim_in_caveat_is_blocked():
    event = EventScanner().scan_sources()[0]
    cluster = ClusteredEvent(event, event.category)
    chain = EventReasoner().reason_through_event(cluster)
    chain.explicit_caveat = "Guaranteed return next week"
    assert not ConstraintGate.apply_constraints(cluster, chain)[0]


def test_blocked_analysis_never_reaches_a_feed():
    pipeline = SarthiPipeline()
    original = pipeline.reasoner.reason_through_event
    def bad_analysis(cluster):
        chain = original(cluster)
        chain.explicit_caveat = "Guaranteed return"
        return chain
    pipeline.reasoner.reason_through_event = bad_analysis
    result = pipeline.run_morning_pipeline()
    assert not result["morning_brief"] and not result["explore_feed"]
    assert any("Blocked:" in entry["reason"] for entry in result["dropped_events_audit"])


def test_api_labels_evidence_and_serves_ui():
    with TestClient(app) as client:
        result = client.get("/api/v1/pipeline/run")
        assert result.status_code == 200
        body = result.json()
        assert body["mode"] == "demo" and "Synthetic" in body["data_notice"]
        for card in body["morning_brief"]:
            assert card["is_sample"] and card["evidence_excerpt"]
            assert not card["source_url"]  # No fabricated document citations.
            assert "evidence_rigour_score" not in card
            assert "not independently verified" in card["evidence_status"]
        event_id = body["morning_brief"][0]["id"]
        reply = client.post("/api/v1/chat/event-assistant", json={"event_id": event_id, "user_query": "Why should I buy this?"}).json()
        assert "cannot recommend trades" in reply["response"]
        assert reply["grounded_in_curated_data"] is False
        assert client.get("/").status_code == 200
        assert client.get("/onboarding").status_code == 200
        assert client.get("/static/js/edge_matcher.js").status_code == 200
