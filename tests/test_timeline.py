from unittest.mock import patch
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.services.rbi_source import load_documents
from backend.app.services.rbi_timeline import build_timeline


def test_timeline_provenance_dates_and_archive_gaps():
    timeline = build_timeline()
    rows = timeline["observations"]
    assert len(rows) >= 11
    assert [r["published_on"] for r in rows] == sorted(r["published_on"] for r in rows)
    assert rows[0]["change_since_previous_archived_bps"] is None
    assert any(r["days_since_previous_archived"] and r["days_since_previous_archived"] > 90 for r in rows)
    for previous, current in zip(rows, rows[1:]):
        assert current["change_since_previous_archived_bps"] == round((current["repo_rate_pct"]-previous["repo_rate_pct"])*100,6)
        assert current["source_text_sha256"] and current["paragraph_id"]
    assert "Missing meetings" in timeline["notice"]


def test_timeline_does_not_fill_missing_meetings_or_call_ai():
    documents = load_documents()
    with patch("backend.app.services.rbi_timeline.all_documents", return_value=[documents[-1], documents[0]]):
        result = build_timeline()
    assert len(result["observations"]) == 2
    assert result["observations"][1]["days_since_previous_archived"] > 600
    with TestClient(app) as client, patch("backend.app.services.gemini_analysis.request_analysis", side_effect=AssertionError("No model call expected")):
        response = client.get("/api/v1/rbi/timeline")
        assert response.status_code == 200
        assert "observations" in response.json()
