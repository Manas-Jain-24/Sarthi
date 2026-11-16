"""Offline failure, retry, budget, freshness and frozen-study regression tests."""
import json
import os
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import httpx
from backend.app.services import research_state as state, research_refresh as refresh, gemini_analysis as gemini
from backend.app.services.rbi_source import DATA,LISTING_URL,FEED_URL,load_documents,save_documents,discover_listing
from backend.app.services.study_protocol import load_manifest,public_material
from backend.app.models.rbi import AnalysisUnavailable
from scripts.analyze_study import aggregate
from tests.test_rbi import example,must_reject


def test_listing_context_and_untrusted_links():
    raw=b'''<div id="annualPolicy"><table><tr><td>Resolution of the Monetary Policy Committee</td><td><a href="BS_PressReleaseDisplay.aspx?prid=63742">Full Document</a><a href="https://evil.example/">Full Document</a></td></tr><tr><td>Minutes of the Monetary Policy Committee</td><td><a href="BS_PressReleaseDisplay.aspx?prid=99">Full Document</a></td></tr></table></div>'''
    assert discover_listing(raw) == ["https://www.rbi.org.in/Scripts/BS_PressReleaseDisplay.aspx?prid=63742"]
    must_reject(lambda:discover_listing(b"<html>Access denied</html>"))


def test_refresh_retains_archive_on_failure_and_reports_age():
    document=load_documents()[0]
    raw=(DATA/"originals"/document.archive_file).read_bytes()
    listing=f'<div id="annualPolicy"><tr><td>Resolution of the Monetary Policy Committee<a href="{document.source_url}">Full Document</a></td></tr></div>'.encode()
    def handler(request):
        return httpx.Response(200,content=listing if str(request.url)==LISTING_URL else b"<rss><channel/></rss>" if str(request.url)==FEED_URL else raw)
    with TemporaryDirectory() as folder,patch.object(refresh,"LIVE",Path(folder)),httpx.Client(transport=httpx.MockTransport(handler)) as client:
        report=refresh.refresh(client=client)
        assert report["status"] == "completed" and report["documents"][0]["outcome"] == "unchanged"
        assert refresh.status([document])["state"] == "checked"
        assert refresh.status([document],now=datetime.now(timezone.utc)+timedelta(hours=25))["state"] == "outdated"
        must_reject(state.start_refresh)
        with state.connection() as db:db.execute("UPDATE refresh_runs SET started_at=?",((datetime.now(timezone.utc)-timedelta(minutes=6)).isoformat(),))
        with httpx.Client(transport=httpx.MockTransport(lambda r:httpx.Response(503))) as broken:
            failed=refresh.refresh(client=broken)
        assert failed["status"] == "failed" and refresh.status([document])["state"] == "check_failed"
        assert load_documents(Path(folder))[0].text_sha256 == document.text_sha256
        assert len(state.refresh_history()) == 2


def test_retries_count_requests_and_rejections_never_retry():
    document=load_documents()[0]
    analysis=example(document)
    calls=[]
    def handler(request):
        calls.append(request)
        if len(calls)==1:return httpx.Response(429,headers={"Retry-After":"0"})
        return httpx.Response(200,json={"candidates":[{"finishReason":"STOP","content":{"parts":[{"text":analysis.model_dump_json()}]}}]})
    with patch.dict(os.environ,{"GEMINI_API_KEY":"offline-key","GEMINI_DAILY_LIMIT":"12"}),httpx.Client(transport=httpx.MockTransport(handler)) as client:
        record=gemini.request_analysis(document,client,sleeper=lambda _:None)
        assert not record.analysis.abstain and len(calls)==2
        rows=state.analysis_history()
        assert len(rows)==2 and {r["status"] for r in rows} == {"accepted","failed"}
        analysis.claims[0].citations[0].quote="This quotation is fabricated and absent from the source."
        calls.clear();calls.append(None) # Next response is a complete, invalid output.
        try:gemini.request_analysis(document,client,sleeper=lambda _:None)
        except AnalysisUnavailable as exc:assert exc.code == "evidence_rejected"
        else:raise AssertionError("Evidence mismatch accepted")
        assert len(calls)==2 and state.analysis_history()[0]["status"]=="rejected"
    with patch.dict(os.environ,{"GEMINI_API_KEY":"offline-key"}),httpx.Client(transport=httpx.MockTransport(lambda r:httpx.Response(429,headers={"Retry-After":"60"}))) as client:
        try:gemini.request_analysis(document,client,sleeper=lambda _:(_ for _ in ()).throw(AssertionError("Must not retry early")))
        except AnalysisUnavailable as exc:assert exc.code=="rate_limited"


def test_malformed_provider_payload_fails_without_retry():
    document=load_documents()[0]
    calls=[]
    def handler(request):calls.append(request);return httpx.Response(200,json=["unexpected response shape"])
    with patch.dict(os.environ,{"GEMINI_API_KEY":"offline-key"}),httpx.Client(transport=httpx.MockTransport(handler)) as client:
        try:gemini.request_analysis(document,client)
        except AnalysisUnavailable as exc:assert exc.code=="malformed"
        else:raise AssertionError("Malformed provider output accepted")
    assert len(calls)==1 and state.analysis_history()[0]["status"]=="rejected"


def test_budget_is_atomic_across_workers_and_imports_previous_count():
    document=load_documents()[0]
    def reserve(_):
        try:return state.reserve_attempt(document,"test-model","test-prompt",3)
        except AnalysisUnavailable as exc:
            assert exc.code=="budget_exhausted"
            return None
    with ThreadPoolExecutor(max_workers=6) as pool:results=list(pool.map(reserve,range(8)))
    assert sum(r is not None for r in results)==3 and len(state.analysis_history())==3
    legacy=state.DB.parent/"rbi_analysis"/"budget.json"
    legacy.parent.mkdir()
    legacy.write_text(json.dumps({"date":state.now()[:10],"attempts":2}))
    must_reject(lambda:state.reserve_attempt(document,"test-model","test-prompt",5))


def test_frozen_study_complete_balanced_and_version_checked():
    manifest=load_manifest()
    assert manifest and len(public_material()["cases"])==4
    labels=json.loads((DATA/"annotations.json").read_text())
    responses=[]
    for i,case in enumerate(manifest["cases"]):
        responses.append({k:case[k] for k in ("document_id","source_text_sha256","model","prompt_version")})
        responses[-1].update(condition="source" if i%2==0 else "briefing",order=i+1,elapsed_ms=1000,
                              repo_rate_pct=labels[case["document_id"]]["repo_rate_pct"],certainty="no",confidence=4)
    record={"protocol":manifest["protocol"],"pilot_id":manifest["pilot_id"],"manifest_sha256":manifest["manifest_sha256"],
            "participant_id":str(uuid.uuid4()),"consent":True,"adult_eligible":True,"responses":responses}
    with TemporaryDirectory() as folder:
        path=Path(folder)/"response.json"
        path.write_text(json.dumps(record))
        result=aggregate([path],labels,manifest,False)
        assert result["participants"]==1 and result["paired_participants"]==1 and result["mean_within_participant_accuracy_difference"]==0
        for change in (lambda r:r["responses"].pop(),lambda r:r["responses"][0].update(model="wrong-model"),
                       lambda r:r["responses"][0].update(repo_rate_pct=float("nan")),lambda r:r.update(test_record=True),
                       lambda r:r["responses"][1].update(condition="source")):
            invalid=json.loads(json.dumps(record));change(invalid);path.write_text(json.dumps(invalid))
            must_reject(lambda:aggregate([path],labels,manifest,False))
