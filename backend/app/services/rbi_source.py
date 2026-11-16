"""Bounded, RBI-only retrieval and reproducible HTML evidence extraction."""
import hashlib
import json
import re
import threading
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit, parse_qs, urljoin
import httpx
from ..models.rbi import RBIDocument, Paragraph

DATA = Path(__file__).resolve().parent.parent / "data" / "rbi"
FEED_URL = "https://www.rbi.org.in/pressreleases_rss.xml"
LISTING_URL = "https://www.rbi.org.in/Scripts/Annualpolicy.aspx"
PARSER_VERSION = "rbi-table-v1"
MAX_BYTES = 2_000_000
WRITE_LOCK = threading.RLock()


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def digest(value: bytes):
    return hashlib.sha256(value).hexdigest()


def document_url(value: str) -> str:
    """Do not accept arbitrary fetch targets, ports, credentials or redirects."""
    url = urlsplit(value)
    if (url.scheme != "https" or url.hostname not in {"rbi.org.in", "www.rbi.org.in"}
            or url.port not in {None, 443} or url.username or url.password
            or url.path.lower() != "/scripts/bs_pressreleasedisplay.aspx"):
        raise ValueError("Only RBI press-release document URLs are supported.")
    params = parse_qs(url.query)
    ids = next((v for k, v in params.items() if k.lower() == "prid"), [])
    if len(ids) != 1 or not ids[0].isdigit():
        raise ValueError("RBI document URL needs one numeric release ID.")
    return f"https://www.rbi.org.in/Scripts/BS_PressReleaseDisplay.aspx?prid={ids[0]}"


class RBIHTML(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.depth = 0
        self.parts = []
        self.skip = 0
        self.done = False

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "table":
            if self.depth:
                self.depth += 1
            elif not self.done and "tablebg" in attrs.get("class", "").split():
                self.depth = 1
        if self.depth:
            if tag in {"script", "style"}:
                self.skip += 1
            if tag in {"p", "tr", "li", "br", "h1", "h2", "h3"}:
                self.parts.append("\n")

    def handle_endtag(self, tag):
        if not self.depth:
            return
        if tag in {"script", "style"} and self.skip:
            self.skip -= 1
        if tag in {"p", "tr", "li", "h1", "h2", "h3"}:
            self.parts.append("\n")
        if tag == "table":
            self.depth -= 1
            self.done = not self.depth

    def handle_data(self, data):
        if self.depth and not self.skip:
            self.parts.append(data)


def parse_document(raw: bytes, url: str, retrieved_at=None) -> RBIDocument:
    url = document_url(url)
    parser = RBIHTML()
    parser.feed(raw.decode("utf-8-sig", errors="replace"))
    lines = [" ".join(line.split()) for line in "".join(parser.parts).splitlines()]
    lines = [line for line in lines if line]
    date_index = next((i for i, line in enumerate(lines) if re.fullmatch(r"Date\s*:\s*\w{3}\s+\d{1,2},\s+\d{4}", line)), None)
    if date_index is None or date_index + 2 >= len(lines):
        raise ValueError("No RBI announcement body/date found; challenge or changed markup rejected.")
    date_text = lines[date_index].split(":", 1)[1].strip()
    published = datetime.strptime(date_text, "%b %d, %Y").date().isoformat()
    title = lines[date_index + 1]
    if not ("Monetary Policy Statement" in title and "Resolution" in title):
        raise ValueError("Outside the supported scope: RBI MPC resolutions only.")
    body = lines[date_index + 2:]
    # Exclude large projections tables/footnotes from evidence? No: keep the entire body.
    if len(" ".join(body)) < 500:
        raise ValueError("RBI resolution is unexpectedly short.")
    paragraphs = [Paragraph(id=f"p{i+1}", text=text) for i, text in enumerate(body)]
    text_hash = digest("\n".join(p.text for p in paragraphs).encode("utf-8"))
    release_id = parse_qs(urlsplit(url).query)["prid"][0]
    return RBIDocument(id=f"RBI_{release_id}", title=title, source_url=url,
                       published_on=published, retrieved_at=retrieved_at or utc_now(),
                       raw_sha256=digest(raw), text_sha256=text_hash, paragraphs=paragraphs,
                       archive_file=f"{release_id}.{digest(raw)[:12]}.html")


def download(url: str, client=None, feed=False) -> bytes:
    target = url if url in {FEED_URL, LISTING_URL} else document_url(url)
    def fetch(session):
        with session.stream("GET", target) as response:
            response.raise_for_status()
            chunks, size = [], 0
            for chunk in response.iter_bytes():
                size += len(chunk)
                if size > MAX_BYTES:
                    raise ValueError("RBI response exceeds the size limit.")
                chunks.append(chunk)
            return b"".join(chunks)
    if client is not None:
        return fetch(client)
    with httpx.Client(timeout=15, follow_redirects=False, trust_env=False,
                      headers={"User-Agent": "SarthiCollegeResearch/1.0"}) as session:
        return fetch(session)


def load_documents(root=DATA):
    path = root / "documents.json"
    if not path.exists():
        return []
    docs = [RBIDocument.model_validate(row) for row in json.loads(path.read_text(encoding="utf-8"))]
    for doc in docs:
        if digest("\n".join(p.text for p in doc.paragraphs).encode("utf-8")) != doc.text_sha256:
            raise ValueError(f"Evidence hash mismatch for {doc.id}")
        archive = root / "originals" / doc.archive_file
        if not archive.is_file() or digest(archive.read_bytes()) != doc.raw_sha256:
            raise ValueError(f"Original document missing or modified for {doc.id}")
    return sorted(docs, key=lambda d: d.published_on, reverse=True)


def save_documents(documents, root=DATA):
    with WRITE_LOCK:
        root.mkdir(parents=True, exist_ok=True)
        path = root / "documents.json"
        temp = path.with_suffix(".tmp")
        temp.write_text(json.dumps([d.model_dump() for d in documents], ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
        temp.replace(path)


def retrieve_document(url, root=DATA, client=None):
    raw = download(url, client=client)
    document = parse_document(raw, url)
    with WRITE_LOCK:
        originals = root / "originals"
        originals.mkdir(parents=True, exist_ok=True)
        # Parse and validate before persisting. Keep archived revisions by content hash.
        path = originals / document.archive_file
        if not path.exists():
            temp = path.with_suffix(".tmp")
            temp.write_bytes(raw)
            temp.replace(path)
    return document


def discover_resolutions(feed: bytes):
    if len(feed) > MAX_BYTES or b"<!DOCTYPE" in feed.upper() or b"<!ENTITY" in feed.upper():
        raise ValueError("Invalid RSS payload.")
    items = ET.fromstring(feed).findall("./channel/item")
    found = []
    for item in items:
        title = item.findtext("title", "")
        if "Monetary Policy Statement" in title and "Resolution" in title:
            try:
                url = document_url(item.findtext("link", "").strip())
                if url not in found:
                    found.append(url)
            except ValueError:
                continue
    return found


class PolicyListing(HTMLParser):
    """Resolution links are sometimes labelled only 'Full Document'. Use row context."""
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.rows = []
        self.text = []
        self.links = []
        self.recognized = False

    def flush(self):
        text = " ".join(" ".join(self.text).split()).lower()
        if "resolution of the monetary policy committee" in text and "minutes of" not in text:
            for href in self.links:
                try:
                    url = document_url(urljoin(LISTING_URL, href))
                    if url not in self.rows:
                        self.rows.append(url)
                except ValueError:
                    continue
        self.text, self.links = [], []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if attrs.get("id") == "annualPolicy":
            self.recognized = True
        if tag == "tr":
            self.flush()
        if tag == "a" and attrs.get("href"):
            self.links.append(attrs["href"])

    def handle_endtag(self, tag):
        if tag == "tr":
            self.flush()

    def handle_data(self, value):
        self.text.append(value)


def discover_listing(raw):
    if len(raw) > MAX_BYTES:
        raise ValueError("Policy listing is too large.")
    parser = PolicyListing()
    parser.feed(raw.decode("utf-8-sig", errors="replace"))
    parser.flush()
    if not parser.recognized:
        raise ValueError("Official policy listing not recognized; challenge or changed markup rejected.")
    return parser.rows
