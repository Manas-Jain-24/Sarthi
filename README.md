# Sarthi (सारथी)

A college-project prototype for explaining how financial events might affect Indian sectors and portfolio exposure.

**Synthetic demo mode:** all incoming events are synthetic fixtures, dated for a walkthrough. They are not current news. The application does not fetch source documents or call an AI model. Analysis is manually authored for exact sample inputs, and unknown or changed inputs receive no conclusion.

## Interface

Four primary sections: **Overview**, **Research**, **Journal**, and **Holdings**. Policy timeline, reference library, source checks and the profile are under **More**. Source selection, model status and verification details are in **Sources & settings**.

The interface uses neutral surfaces, system fonts and a single green accent. Scenario planning, journal editing, backup tools and detailed evidence open when needed. The announcement drawer supports Escape, keyboard focus containment and focus restoration. No external font service is used.

## Portfolio review workspace

The default screen is **Overview**: entered allocation, sector breakdown, a user-chosen concentration review threshold, notes due for review, and three hypothetical policy worksheets. These prompts support reflection; they do not calculate returns or recommend trades.

- **Holdings:** add holdings or import a CSV with `ticker,sector,allocation_pct`. A preview validates the entire file before replacing anything. Undo is available on the same page until another holdings edit or reload. Imported files never leave the browser.
- **Journal:** write a thesis, evidence that would change your mind, your own decision label, and a review date. Attach a dated source snapshot from the event drawer or Policy Timeline. Editing appends a revision; follow-up reviews record what you learned and schedule the next review. Archiving is reversible.
- **More → Policy timeline:** inspect the dated repo-rate observations, filter the actual wording, and link an event to a note. Dots are discrete observations; missing meetings are not filled. Differences compare adjacent archived observations, not necessarily adjacent RBI meetings.
- **Export:** download a self-contained printable HTML review or JSON, including holdings, the selected scenario comparison, journal history, and loaded real-source references. Journal backups can be validated and restored locally, with a backup of the previous journal downloaded before replacement.

No portfolio, journal or scenario worksheet is sent to Gemini or a backend journal service. They use persistent localStorage, which is not encrypted or tamper-proof. Exported reports contain private financial notes; keep backups yourself. Clearing site data removes local records. The app does not measure whether a thesis is correct or whether the journal improves decisions.

See `docs/portfolio_review.md` for a complete demonstration and recovery guide.

## RBI evidence and Gemini path

The dashboard defaults to the review workspace with **Real RBI documents** selected as its evidence source. Eleven original MPC resolutions (December 2023 to February 2026) are archived in `backend/app/data/rbi/`, with their publication/retrieval dates, original HTML, SHA-256 hashes and numbered evidence paragraphs. These are historical publications, not current news. Switch to Synthetic demo to use the original scenarios.

Two recorded, real Gemini Flash-Lite outputs are included, tied to the exact source hashes, model and prompt version. They work without a key. Their factual sections render validated source quotes; interpretations cite their premises and remain hypotheses requiring human review. Quote occurrence does not prove that an interpretation follows from the evidence.

To generate new analysis, copy `.env.example` to `.env`, add `GEMINI_API_KEY`, and optionally set `GEMINI_MODEL` (default `gemini-3.5-flash-lite`). Restart the server after changing configuration. Open an announcement in **Research**, then use **Generate analysis** to request a new interpretation. No provider call occurs on page load or GET requests. Only the selected public RBI document goes to Gemini; local holdings are not sent. Accepted analyses are cached by document hash, model, and prompt version. The configurable daily attempt budget includes failed requests. `.env` and `.cache` are ignored by Git.

Use **Source only** to compare the source text, and **Read source / Read analysis** to inspect an announcement. Supporting passages and detailed reasoning expand on demand. Portfolio relevance displays the allocation overlapping the mapped sectors; this is a heuristic exposure measure, not a prediction of gains or losses.

**Sources → Check for new announcements** explicitly reads [RBI's rolling press-release RSS feed](https://www.rbi.org.in/pressreleases_rss.xml), selects MPC resolutions, and downloads at most three original RBI HTML documents. A rolling feed can contain no matching resolutions; a successful check with zero matches does not mean that the historical archive is current. Retrieval errors preserve the archive. Refresh never invokes Gemini. The service runs locally on `127.0.0.1`; mutation endpoints reject non-local and cross-origin actions.

```sh
python scripts/refresh_rbi.py
python scripts/evaluate_rbi.py --split holdout
# Explicit provider requests for missing accepted outputs (uses quota):
python scripts/evaluate_rbi.py --split holdout --generate
```

The four-document holdout evaluation on 15 November 2026 produced two accepted Gemini analyses, one rejected citation and one provider service failure: **50% accepted coverage**. Both accepted answers matched the annotated repo rate and passed literal citation checks; the source-only extractor matched all four rates. These results do not establish semantic entailment or improved comprehension. See `docs/evaluation/rbi_holdout_2026-11-15.json` and `docs/rbi_evaluation.md` for the complete denominators and limitations.

The **More → Research study** link opens a voluntary adult consent flow comparing source passages and recorded AI briefings across different documents. It uses anonymous local JSON export, with no automatic submission. No student study has been conducted yet.

```sh
python scripts/analyze_study.py path/to/voluntarily-shared-files
```

Implementation references: [Gemini generateContent](https://ai.google.dev/api/generate-content), [structured output](https://ai.google.dev/gemini-api/docs/structured-output), and [model names](https://ai.google.dev/gemini-api/docs/models). The initial corpus was retrieved directly from RBI, including the [December 2024 resolution](https://www.rbi.org.in/Scripts/BS_PressReleaseDisplay.aspx?prid=59244).

## What works in the synthetic demo

- A FastAPI backend runs classification, clustering, source-tier rules, reviewed scenario lookup, explanation checks, and output packaging.
- The static HTML/CSS/JavaScript frontend displays evidence separately from interpretation, mechanisms, historical comparisons, limitations, and caveats.
- Holdings are saved in browser localStorage and matched locally against tickers and all affected sectors. The matcher does not send holdings to the backend.
- The brief includes up to five relevant, non-excluded samples that passed the explanation gate. It does not fill empty slots with unrelated or failed cards.
- Explore contains other eligible sample cards and inputs with analysis withheld. Blocked forecasts are withheld from both feeds and recorded in the audit log.
- The historical library contains 20 manually authored reference summaries. Comparisons are illustrative and are not independently verified evidence.
- Onboarding offers a heuristic response label from a hypothetical loss scenario. This does not measure a psychological coefficient, validate suitability, or establish actual behavior.
- The event assistant returns fixed responses for reasoning, historical comparison, or uncertainty. Questions are transmitted to the server; avoid entering private information.

## Evidence and uncertainty

Cards carry two separate labels:

- **Evidence:** sample input, not independently verified. The displayed excerpt is quoted from the fixture, not an external document.
- **Impact:** illustrative hypothesis, not validated; or unknown when reviewed coverage is missing.

There is no numerical confidence or rigour score. Local ranking reflects portfolio exposure only. A source-tier check cannot establish the correctness of an economic interpretation or predict a stock return.

The demo's institution/publisher links are homepages for background reading. They are explicitly not citations supporting the synthetic announcements. The original placeholder document URLs were removed to avoid implying verification.

A Tier 1 label passes the source rule; two distinct Tier 2 publisher names can also pass. Repeated names and domains do not count twice. Different publishers can syndicate one report, so these basic checks do not prove independent confirmation. Clustering is token based and restricted to the same category and day.

## Run locally

Requires Python 3.10+ and a modern browser.

```sh
python -m pip install -r requirements.txt
python scripts/run_server.py
```

Open http://localhost:8000. The source archive, recorded analyses, synthetic demo and study materials need no key or database. New Gemini generation requires a local key and may use provider quota. No Node build step is required.

## Three-minute demonstration

1. Open **Sources & settings**, choose **Synthetic examples**, then open **Research**. An empty portfolio starts with an empty brief.
2. In **Holdings**, click **Load example portfolio**. This explicitly replaces the current browser entries with fictional allocations.
3. Open the tobacco-duty sample. Compare the synthetic evidence excerpt with the proposed tax/pricing mechanism and the stated unknowns.
4. Open the monetary-policy sample. Explain why a neutral stance does not establish future cuts or higher bank earnings.
5. Open the demerger sample. Inspect why the bank-merger analogy is weak and why separation does not guarantee value creation.
6. Inspect the audit log to see the uncorroborated rumor excluded. Explore also includes the optional shipping scenario with two assigned media names.
7. Clear holdings and confirm that the personal brief becomes empty again.

## Verification

```sh
python tests/run_tests.py
node tests/test_edge_matcher.cjs
node tests/test_review.cjs
node --check frontend/js/app.js
```

Node is only needed for frontend checks. The checks cover abstention on changed or unknown inputs, duplicate-source counting, date/category clustering boundaries, forecast blocking across explanation fields, blocked-card exclusion, API provenance labels, fixed-assistant boundaries, local relevance and exclusions, allocation validation, and empty portfolios. They do not establish semantic entailment, investment performance, or legal compliance. Real-source tests use mocked provider transports; the separately recorded holdout report documents real Gemini calls.

## Privacy and limitations

localStorage is persistent browser storage, not encryption or a cryptographic zero-knowledge system. Scripts running on the same origin can access it; clearing site data removes it. Portfolio matching does not transmit holdings, but free-text assistant messages are sent to the backend. There is no cross-device sync or formal privacy audit.

This is an educational prototype. No claim of SEBI approval or regulatory compliance is made. Renaming a recommendation does not establish a legal exemption. No trade execution, validated forecasts, database integration, or general conversational AI is implemented. The real-source path supports only RBI MPC resolutions. The Next.js, Supabase, and Claude integrations described in the original proposal remain unimplemented; Gemini is the implemented provider. The PDF is preserved as the original proposal, not the implementation specification.

## Structure

- `backend/app/pipeline/`: seven processing stages and orchestration
- `backend/app/data/sample_events.json`: synthetic event inputs
- `backend/app/data/demo_scenarios.json`: exact-input analysis and counterarguments
- `backend/app/data/curated_analogies.json`: illustrative historical library
- `frontend/`: static dashboard, local matcher, and onboarding
- `tests/`: backend/API and frontend regression checks
- `docs/sarthi_full_implementation_plan.md`: current scope and remaining research work

Licensed under MIT. See LICENSE.
