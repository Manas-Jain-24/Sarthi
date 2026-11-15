# Portfolio Review, Decision Journal and Policy Timeline

## Product workflow

This upgrade supports a complete reflection cycle: enter holdings, inspect allocation, examine a source event, record a thesis and disconfirming evidence, return for a review, and export the reasoning. It adds no new paid model requests. The existing explicit Gemini analysis remains available in the event feed.

The initial view is Portfolio Review. The metrics describe entered holdings, allocation and unassigned allocation. The remainder is not assumed to be cash. Sector allocation is aggregated case-insensitively. A user can change the sector review threshold; this is a review preference, not a validated risk rule. That threshold and scenario controls are page preferences and reset on reload.

Three policy scenarios pose qualitative questions about rates falling, staying unchanged or rising. The mapped sectors are explicitly Banking, NBFCs, Real Estate and Automotive. Mapping is a declared heuristic; other holdings are labelled unmapped, not unaffected. The worksheet does not estimate returns, probabilities, losses or financial suitability. Comparing all three includes all three in the export.

## CSV import

Expected headers, in order:

```csv
ticker,sector,allocation_pct
HDFCBANK,Banking,30
INFY,IT Services,20
BAJFINANCE,NBFCs,10
```

The parser supports a UTF-8 BOM, CRLF, quoted fields and optional percent signs. The complete file is validated before any saved state changes. Duplicate tickers, extra columns, malformed quotes, invalid weights, totals above 100%, and empty files are rejected. Up to 300 holdings and a one-megabyte input are supported. Applying a preview explicitly replaces holdings. The previous holdings can be restored with Undo on that page until another edit or reload. Storage failures leave the earlier in-memory and saved portfolio unchanged.

CSV sectors are supplied by the user; spelling and classification matter for matching. The system does not infer a company's sector from its ticker. A template download is available. No import data is transmitted to the server.

## Journal model

A note contains a ticker, thesis, disconfirming evidence, a user-chosen decision label, a review date and an optional source snapshot. The snapshot records publication date, source URL, excerpt, source hash, and whether the input is synthetic. Current event revisions can be compared with the saved hash; a differing loaded revision is flagged. Saved snapshots are not independent proof that imported data is authentic.

Editing appends a new version. Reviews are separate records bound to the version that was reviewed, with a qualitative outcome, learning note and next review date. Editing a thesis after a review makes the new version's date the applicable date. Due dates use India Standard Time, including the local-day boundary. Archiving is reversible and removes the note from the due queue without deleting its history. At most 500 notes, 100 revisions per note and 100 reviews per note are supported, subject to browser storage quota.

This is a local editable journal, not an immutable or cryptographically attested audit ledger. No automated truth, decision-quality, or investment-performance score is assigned.

## Backup, restore and export

Download journal backups regularly. Import validates all entries, dates, revisions and reviews before presenting a replacement preview. Applying a restore downloads a copy of the current data before replacing it. A normally readable journal is backed up in the same importable envelope format. Corrupt data is preserved as a raw recovery file and requires manual investigation; new writes are blocked until an explicit valid restore.

The review report is a static, self-contained HTML document with print styling; open it in a browser and use its normal Print / Save as PDF controls if needed. No scripts or external fonts are embedded. JSON export is also available. Reports contain entered holdings, journal versions and reviews, the selected scenario comparison, and loaded real-source references. They do not include application credentials. Note text is rendered literally and escaped in HTML exports.

Exports and journal backups contain private financial notes. No automatic upload, cloud sync, account authentication, server persistence or encryption is implemented. All scripts on the same app origin can access localStorage. Clearing site data or switching browser profiles loses access to records unless backed up. Changing localhost ports also uses a different browser origin and therefore a different journal.

## Timeline semantics

`GET /api/v1/rbi/timeline` reads the verified archive without a provider request. Each observation includes the publication date, extracted repo rate, decision wording, evidence paragraph ID, source URL and text hash. The difference in basis points is relative to the previous archived observation; the response names it accordingly and includes the number of days between observations. For example, a difference spanning a missing meeting must not be labelled the size of one announced rate change. The scatter chart does not draw an interpolated policy path.

## Five-minute college demonstration

1. Open Portfolio Review, then use My Portfolio to preview the sample CSV. Apply it and show 60% entered and 40% unassigned allocation.
2. Compare all three policy scenarios and identify which entered sectors are outside the declared mapping.
3. Open Policy Timeline and inspect a date gap, its source passage, and its difference versus the previous archived observation.
4. Choose Write a linked note. Enter a thesis and what would change your mind, then save. Edit it and inspect both versions.
5. Record a follow-up review with a future date. Reload to show that the history and next date persist.
6. Download a review report, inspect its holdings, earlier reasoning and source snapshot, and demonstrate CSV import Undo on the same page.

Do not use demonstration notes as real participant study data. User comprehension and decision outcomes still require a separately consented evaluation.

## Validation

Run `python tests/run_tests.py`, `node tests/test_edge_matcher.cjs`, and `node tests/test_review.cjs`. The new checks exercise CSV edge cases, allocation semantics, scenario boundaries, date handling, revision preservation, atomic storage errors, corruption recovery, backup round trips, and safe HTML export. API checks verify source provenance, gaps and the absence of model calls during timeline reads. Browser verification covered event linking, saving, editing, follow-up review, persistence after reload, CSV preview/apply/undo, scenario comparison and the actual HTML download.
