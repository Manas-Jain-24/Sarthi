# Sarthi (सारथी)

A college-project prototype for explaining how financial events might affect Indian sectors and portfolio exposure.

The default evidence source is an archive of real RBI monetary-policy resolutions, with optional Gemini analysis on request. A separate synthetic mode provides fixed walkthrough examples. Neither mode predicts returns or recommends trades.

## Interface

Four primary sections: **Overview**, **Research**, **Journal**, and **Holdings**. Policy timeline, reference library, source checks and the profile are under **More**. Source selection, model status and verification details are in **Sources: Check for new announcements** checks the [official policy listing](https://www.rbi.org.in/Scripts/Annualpolicy.aspx) alongside [RBI's rolling RSS feed](https://www.rbi.org.in/pressreleases_rss.xml). It downloads at most six resolutions per run, rotating older checks after unseen documents. Settings shows check time separately from the latest publication, incomplete checks, source revisions, and recent Gemini outcomes. A source check expires after 24 hours. The listing covers its displayed fiscal year; this is not a complete historical archive. Retrieval errors preserve existing evidence. Refresh never invokes Gemini. The local service rejects non-local and cross-origin mutations.

Transient Gemini failures retry once by default, with short backoff. Evidence/schema failures never retry automatically. Each outgoing request, including retries, consumes the persistent daily budget. `GEMINI_MAX_RETRIES` accepts zero to two; long provider retry delays return control instead of retrying early. Request history stores document hashes and outcome codes, never credentials, holdings, or response bodies.

```sh
python scripts/refresh_rbi.py
python scripts/evaluate_rbi.py --split holdout
# Explicit provider requests for missing accepted outputs (uses quota):
python scripts/evaluate_rbi.py --split holdout --generate
```

The four-document holdout evaluation on 15 November 2026 produced two accepted Gemini analyses, one rejected citation and one provider service failure: **50% accepted coverage**. Both accepted answers matched the annotated repo rate and passed literal citation checks; the source-only extractor matched all four rates. These results do not establish semantic entailment or improved comprehension. See `docs/evaluation/rbi_holdout_2026-11-15.json` and `docs/rbi_evaluation.md` for the complete denominators and limitations.

The expanded run on 17 November (India time) requested six new documents: **five accepted, one provider failure**. All five accepted rates and literal citations passed; the extractor matched all eleven new rate labels. The archive now covers seven hikes, twelve holds and three cuts. These are implementation-reviewed labels pending independent review. See `docs/evaluation/rbi_expanded_2026-11-17.json`.

The **More → Research study** link opens a voluntary adult consent flow comparing source passages and recorded AI briefings across different documents. It uses anonymous local JSON export, with no automatic submission. Four hash-bound cases are frozen for the pilot, so a later refresh cannot change participant materials. The recruitment text, scoring commands and independent-review form are in `docs/pilot/`. Actual volunteer responses and independent human review remain to be collected.

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

Open http://localhost:8000. The source archive, recorded analyses, synthetic demo and study materials need no key or external database. New Gemini generation requires a local key and may use provider quota. Operational history and atomic request budgets use a local SQLite file under ignored `.cache/`. No Node build step is required.

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
