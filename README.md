# Sarthi (सारथी)

A college-project prototype for explaining how financial events might affect Indian sectors and portfolio exposure.

**Demo mode:** all incoming events are synthetic fixtures, dated for a walkthrough. They are not current news. The application does not fetch source documents or call an AI model. Analysis is manually authored for exact sample inputs, and unknown or changed inputs receive no conclusion.

## What works

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

Open http://localhost:8000. No API keys, paid services, database, or Node build step are required.

## Three-minute demonstration

1. Open the dashboard and read the demo-data notice. An empty portfolio starts with an empty brief.
2. In **My Portfolio**, click **Load example portfolio**. This explicitly replaces the current browser entries with fictional allocations.
3. Open the tobacco-duty sample. Compare the synthetic evidence excerpt with the proposed tax/pricing mechanism and the stated unknowns.
4. Open the monetary-policy sample. Explain why a neutral stance does not establish future cuts or higher bank earnings.
5. Open the demerger sample. Inspect why the bank-merger analogy is weak and why separation does not guarantee value creation.
6. Inspect the audit log to see the uncorroborated rumor excluded. Explore also includes the optional shipping scenario with two assigned media names.
7. Clear holdings and confirm that the personal brief becomes empty again.

## Verification

```sh
python tests/run_tests.py
node tests/test_edge_matcher.cjs
node --check frontend/js/app.js
```

Node is only needed for frontend checks. The checks cover abstention on changed or unknown inputs, duplicate-source counting, date/category clustering boundaries, forecast blocking across explanation fields, blocked-card exclusion, API provenance labels, fixed-assistant boundaries, local relevance and exclusions, allocation validation, and empty portfolios. They do not establish factual correctness, investment performance, or legal compliance.

## Privacy and limitations

localStorage is persistent browser storage, not encryption or a cryptographic zero-knowledge system. Scripts running on the same origin can access it; clearing site data removes it. Portfolio matching does not transmit holdings, but free-text assistant messages are sent to the backend. There is no cross-device sync or formal privacy audit.

This is an educational prototype. No claim of SEBI approval or regulatory compliance is made. Renaming a recommendation does not establish a legal exemption. No trade execution, validated forecasts, live ingestion, database integration, or general conversational AI is implemented. The Next.js, Supabase, and Claude integrations described in the original proposal remain future work; the PDF is preserved as the original proposal, not the implementation specification.

## Structure

- `backend/app/pipeline/`: seven processing stages and orchestration
- `backend/app/data/sample_events.json`: synthetic event inputs
- `backend/app/data/demo_scenarios.json`: exact-input analysis and counterarguments
- `backend/app/data/curated_analogies.json`: illustrative historical library
- `frontend/`: static dashboard, local matcher, and onboarding
- `tests/`: backend/API and frontend regression checks
- `docs/sarthi_full_implementation_plan.md`: current scope and remaining research work

Licensed under MIT. See LICENSE.
