"""Offline regression coverage; no real model requests or external network."""
import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import httpx
from fastapi.testclient import TestClient
from backend.app.main import app, local_action
from backend.app.models.rbi import RBIAnalysis, EvidenceClaim, Citation, AnalysisUnavailable
from backend.app.services import gemini_analysis as gemini
from backend.app.services.rbi_source import (DATA, FEED_URL, load_documents, parse_document,
    document_url, discover_resolutions, download, retrieve_document, save_documents)
from backend.app.services.rbi_brief import build_rbi_brief
from backend.app.services.rbi_evaluation import evaluate
from scripts.analyze_study import aggregate


def example(document):
    paragraph = next(p for p in document.paragraphs[:6] if "policy repo rate" in p.text.lower())
    # Use a complete, verified sentence for the factual span.
    quote = paragraph.text[:paragraph.text.find("Consequently")].strip() if "Consequently" in paragraph.text else paragraph.text
    return RBIAnalysis(abstain=False, abstention_reason="", repo_rate_pct=gemini.repo_rate(document),
        claims=[EvidenceClaim(kind="fact", text=quote, citations=[Citation(paragraph_id=paragraph.id, quote=quote)]),
                EvidenceClaim(kind="interpretation", text="Funding conditions could affect lenders, depending on how loan and deposit rates adjust.", citations=[Citation(paragraph_id=paragraph.id, quote=quote)])],
        affected_sectors=["Banking"], uncertainties=["The announcement does not determine future company profits."],
        counterarguments=["Deposit and loan repricing can offset one another."])


def must_reject(call):
    try:
        call()
    except (ValueError, AnalysisUnavailable):
        return
    raise AssertionError("Expected evidence/provider rejection")


def test_real_archive_integrity_and_scope():
    docs = load_documents()
    assert len(docs) == 22
    labels = json.loads((DATA / "annotations.json").read_text())
    assert sum(l["split"] == "holdout" for l in labels.values()) == 4
    for doc in docs:
        raw = (DATA / "originals" / doc.archive_file).read_bytes()
        rebuilt = parse_document(raw, doc.source_url, doc.retrieved_at)
        assert rebuilt.model_dump() == doc.model_dump()
        assert gemini.repo_rate(doc) == labels[doc.id]["repo_rate_pct"]
        assert doc.text_sha256 == labels[doc.id]["text_sha256"]


def test_challenge_wrong_scope_and_fetch_targets_rejected():
    must_reject(lambda: parse_document(b"<html>Please enable JavaScript</html>", load_documents()[0].source_url))
    for url in ["http://rbi.org.in/Scripts/BS_PressReleaseDisplay.aspx?prid=12",
                "https://rbi.org.in.attacker.example/Scripts/BS_PressReleaseDisplay.aspx?prid=12",
                "https://user:secret@rbi.org.in/Scripts/BS_PressReleaseDisplay.aspx?prid=12",
                "https://127.0.0.1/private", "https://rbi.org.in:8443/Scripts/BS_PressReleaseDisplay.aspx?prid=12"]:
        must_reject(lambda: document_url(url))


def test_feed_discovers_only_supported_originals():
    feed = b'''<rss><channel><item><title>Monetary Policy Statement Resolution</title><link>https://rbi.org.in/Scripts/BS_PressReleaseDisplay.aspx?prid=12</link></item><item><title>Other announcement</title><link>https://attacker.example/</link></item></channel></rss>'''
    assert discover_resolutions(feed) == ["https://www.rbi.org.in/Scripts/BS_PressReleaseDisplay.aspx?prid=12"]
    assert discover_resolutions(b"<rss><channel/></rss>") == []
    must_reject(lambda: discover_resolutions(b'<!DOCTYPE a [<!ENTITY x "xx">]><rss/>'))


def test_source_download_and_archive_with_mock_transport():
    doc = load_documents()[0]
    raw = (DATA / "originals" / doc.archive_file).read_bytes()
    with TemporaryDirectory() as folder, httpx.Client(transport=httpx.MockTransport(lambda request: httpx.Response(200, content=raw))) as client:
        root = Path(folder)
        fetched = retrieve_document(doc.source_url, root=root, client=client)
        save_documents([fetched], root=root)
        assert load_documents(root)[0].text_sha256 == doc.text_sha256
        (root / "originals" / fetched.archive_file).write_bytes(b"changed")
        must_reject(lambda: load_documents(root))
    with httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(200, content=b"x"*2_000_001))) as client:
        must_reject(lambda: download(FEED_URL, feed=True, client=client))


def test_claims_quotes_numbers_and_abstention():
    doc = load_documents()[0]
    analysis = example(doc)
    gemini.validate_analysis(doc, analysis)
    for mutate in [lambda a: setattr(a.claims[0].citations[0], "paragraph_id", "missing"),
                   lambda a: setattr(a.claims[0].citations[0], "quote", "A fabricated quote that is not in the RBI document."),
                   lambda a: setattr(a.claims[0], "text", "An unsupported factual paraphrase."),
                   lambda a: setattr(a.claims[1], "text", "Lender profits will rise by 20 percent."),
                   lambda a: setattr(a, "repo_rate_pct", 99),
                   lambda a: setattr(a, "counterarguments", ["Guaranteed returns are assured."])]:
        invalid = analysis.model_copy(deep=True)
        mutate(invalid)
        must_reject(lambda: gemini.validate_analysis(doc, invalid))
    paraphrase = analysis.model_copy(deep=True)
    paraphrase.claims[0].text = "Discard this generated factual paraphrase."
    rebuilt = gemini.source_facts_only(doc, paraphrase)
    assert rebuilt.claims[0].text == analysis.claims[0].text
    gemini.validate_analysis(doc, rebuilt)
    abstention = analysis.model_copy(update={"abstain": True, "abstention_reason": "Not enough evidence.", "claims": [], "affected_sectors": []})
    gemini.validate_analysis(doc, abstention)


def test_gemini_transport_contract_and_safe_failures():
    doc = load_documents()[0]
    analysis = example(doc)
    requests = []
    def handler(request):
        payload = json.loads(request.content)
        requests.append(payload)
        assert request.headers["x-goog-api-key"] == "fake-key-for-offline-test"
        assert "holdings" not in payload and "annotations" not in payload
        assert "responseJsonSchema" in payload["generationConfig"]
        return httpx.Response(200, json={"modelVersion": "test-resolved-version", "candidates": [{"finishReason": "STOP", "content": {"parts": [{"text": analysis.model_dump_json()}]}}]})
    with patch.dict(os.environ, {"GEMINI_API_KEY": "fake-key-for-offline-test"}), httpx.Client(transport=httpx.MockTransport(handler)) as client:
        record = gemini.request_analysis(doc, client)
        assert record.resolved_model == "test-resolved-version" and len(requests) == 1
    with patch.dict(os.environ, {"GEMINI_API_KEY": ""}):
        must_reject(lambda: gemini.request_analysis(doc))
    with patch.dict(os.environ, {"GEMINI_API_KEY": "fake-key-for-offline-test"}), httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(429))) as client:
        try:
            gemini.request_analysis(doc, client)
        except AnalysisUnavailable as exc:
            assert "429" in str(exc) and "fake-key" not in str(exc)
        else:
            raise AssertionError("Quota error was not surfaced")


def test_cached_record_does_not_call_provider_again():
    doc = next(d for d in load_documents() if d.id == "RBI_55178")
    with TemporaryDirectory() as folder, patch.object(gemini, "CACHE", Path(folder)), patch.dict(os.environ, {"GEMINI_API_KEY": "fake-key-for-offline-test"}):
        record = gemini.AnalysisRecord(document_id=doc.id, text_sha256=doc.text_sha256,
            requested_model=gemini.model_name(), resolved_model="test-model", prompt_version=gemini.PROMPT_VERSION,
            generated_at="2026-11-15T00:00:00+00:00", analysis=example(doc))
        with patch.object(gemini, "request_analysis", return_value=record) as provider:
            assert gemini.analyze_and_cache(doc) == record
            assert gemini.analyze_and_cache(doc) == record
            assert provider.call_count == 1
        invalid = doc.model_copy(update={"text_sha256": "0"*64})
        assert gemini.cached_analysis(invalid) is None


def test_real_api_read_only_and_failure_fallback():
    with TestClient(app) as client, patch("backend.app.services.gemini_analysis.request_analysis", side_effect=AssertionError("GET must not call Gemini")):
        data = client.get("/api/v1/rbi/brief").json()
        assert data["mode"] == "rbi" and len(data["morning_brief"]) >= 11
        card = data["morning_brief"][0]
        assert not card["is_sample"] and card["source_url"].startswith("https://www.rbi.org.in/")
        assert card["baseline_text"] and card["evidence_paragraphs"]
        assert client.get("/study").status_code == 200
        assert client.post("/api/v1/rbi/analyze/UNKNOWN").status_code == 403
        app.dependency_overrides[local_action] = lambda: None
        try:
            with patch("backend.app.main.analyze_and_cache", side_effect=AnalysisUnavailable("Key unavailable")):
                assert client.post("/api/v1/rbi/analyze/"+card["id"]).status_code == 503
            assert client.post("/api/v1/rbi/analyze/UNKNOWN").status_code == 404
        finally:
            app.dependency_overrides.clear()


def test_evaluation_reports_no_invented_model_or_human_results():
    with patch("backend.app.services.rbi_evaluation.cached_analysis", return_value=None):
        report = evaluate("holdout")
    assert report["document_count"] == 4 and report["baseline"]["repo_rate_exact_matches"] == 4
    assert report["ai"]["not_generated"] == 4 and report["human_study"]["participants"] == 0
    assert all(case["human_relevance_score"] is None for case in report["cases"])


def test_study_empty_and_duplicate_participant_handling():
    labels = json.loads((DATA / "annotations.json").read_text())
    assert aggregate([], labels)["participants"] == 0
    doc_id = next(iter(labels))
    row = {"protocol": "rbi-comprehension-v1", "participant_id": "offline-test", "consent": True,
           "responses": [{"document_id": doc_id, "source_text_sha256": labels[doc_id]["text_sha256"], "condition": "source",
                           "repo_rate_pct": labels[doc_id]["repo_rate_pct"], "certainty": "no", "confidence": 5}]}
    with TemporaryDirectory() as folder:
        p = Path(folder)/"response.json"
        p.write_text(json.dumps(row), encoding="utf-8")
        result = aggregate([p], labels)
        assert result["participants"] == 1 and result["conditions"]["source"]["question_accuracy"] == 1
        must_reject(lambda: aggregate([p, p], labels))
