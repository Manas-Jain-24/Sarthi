"""Check RSS and the official policy listing, retaining evidence on any failure."""
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path
import httpx
from . import research_state as state
from .rbi_source import (DATA, FEED_URL, LISTING_URL, load_documents, save_documents,
                         download, discover_resolutions, discover_listing, retrieve_document, digest, utc_now)

LIVE = Path(__file__).resolve().parents[3] / ".cache" / "rbi_live"


def refresh(limit=6, client=None):
    run_id = state.start_refresh()
    sources, failures, results = [], [], []
    details = {"run_id":run_id,"checked_at":utc_now(),"sources":sources,"failures":failures,"documents":results}
    try:
        candidates = []
        for name, url, parser in [("policy_listing",LISTING_URL,discover_listing), ("rss",FEED_URL,discover_resolutions)]:
            source = {"name":name,"url":url,"status":"failed","matching_items":0}
            try:
                raw = download(url, client=client)
                urls = parser(raw)
                source.update(status="ok",matching_items=len(urls),sha256=digest(raw),document_ids=[u.rsplit("=",1)[-1] for u in urls])
                candidates.extend(u for u in urls if u not in candidates)
            except (httpx.HTTPError, ValueError, ET.ParseError) as exc:
                source["error"] = type(exc).__name__
                failures.append({"url":url,"stage":"discovery","error":type(exc).__name__})
            sources.append(source)
        current = {d.id:d for d in load_documents(LIVE)}
        known = {d.id:d for d in load_documents()}
        known.update(current)
        # Retrieve unseen sources first, then rotate the least recently fetched.
        candidates.sort(key=lambda url:known.get("RBI_"+url.rsplit("=",1)[-1]).retrieved_at
                        if "RBI_"+url.rsplit("=",1)[-1] in known else "")
        cap = max(1,min(int(limit),8))
        for url in candidates[:cap]:
            try:
                doc = retrieve_document(url,root=LIVE,client=client)
                previous = known.get(doc.id)
                kind = "new" if previous is None else "unchanged" if previous.text_sha256 == doc.text_sha256 else "revised"
                results.append({"id":doc.id,"url":url,"published_on":doc.published_on,"outcome":kind,
                                "text_sha256":doc.text_sha256,"raw_sha256":doc.raw_sha256,"archive_file":doc.archive_file,
                                "previous_text_sha256":previous.text_sha256 if previous else None})
                current[doc.id] = doc
            except (httpx.HTTPError,ValueError,OSError) as exc:
                failures.append({"url":url,"stage":"document","error":type(exc).__name__})
        # No network failure deletes or empties the previous archive.
        if results:
            save_documents(list(current.values()),LIVE)
        details.update(matching_items=len(candidates),retrieved=[r["id"] for r in results],
                       pending=max(0,len(candidates)-cap),feed_url=FEED_URL,listing_url=LISTING_URL)
        good_sources=sum(s["status"] == "ok" for s in sources)
        status="failed" if not good_sources else "partial" if failures or details["pending"] else "completed"
        details["status"]=status
        state.finish_refresh(run_id,status,details)
        return details
    except (OSError,ValueError,RuntimeError) as exc:
        details.update(status="failed",error=type(exc).__name__)
        state.finish_refresh(run_id,"failed",details)
        raise


def status(documents=None, now=None):
    if documents is None:
        from .rbi_brief import all_documents
        documents=all_documents()
    history=state.refresh_history(20)
    last=history[0] if history else None
    last_success=next((r for r in history if r["status"] == "completed"),None)
    current=now or datetime.now(timezone.utc)
    label="never_checked"
    if last:
        details=last["details"]
        listing=next((s for s in details.get("sources",[]) if s["name"] == "policy_listing"),{})
        if last["status"] == "running":
            age=(current-datetime.fromisoformat(last["started_at"])).total_seconds()
            label="checking" if age<300 else "interrupted"
        elif last["status"] == "failed": label="check_failed"
        elif last["status"] == "partial": label="partial"
        elif not listing.get("matching_items"): label="unverified"
        else:
            age=(current-datetime.fromisoformat(last["finished_at"])).total_seconds()
            label="checked" if age<=86400 else "outdated"
    archive_error=None
    try:
        load_documents(LIVE)
    except (ValueError,OSError):
        archive_error="Live archive integrity check failed. Bundled sources remain available."
        label="archive_error"
    return {"state":label,"checked_at":last["finished_at"] or last["started_at"] if last else None,
            "last_success_at":last_success["finished_at"] if last_success else None,
            "latest_publication":max((d.published_on for d in documents),default=None),
            "document_count":len(documents),"archive_error":archive_error,
            "history":history,"freshness_window_hours":24,
            "notice":"Check time and publication date are different. The policy listing covers its displayed fiscal year; neither a quiet RSS feed nor a successful fetch proves complete historical coverage."}
