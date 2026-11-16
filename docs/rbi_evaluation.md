# RBI path: evaluation and student-study protocol

## Corpus and split

Twenty-two original RBI MPC resolutions were retrieved directly from official RBI press-release pages on 15-17 November 2026 (India time). Each normalized document records the original URL, publication and retrieval dates, original-HTML hash, normalized-text hash, parser version and numbered evidence paragraphs. Original HTML is preserved byte-for-byte using .gitattributes. The expanded corpus contains seven hikes, twelve holds and three cuts between April 2022 and October 2026. It remains a selected archive with missing meetings.

Seven documents through June 2025 are the development split; four from August 2025 to February 2026 are the chronological holdout. Initial rate labels and their evidence-paragraph IDs were reviewed during implementation. They need independent second review before being described as a gold standard. Labels are not supplied to Gemini. This holdout is disjoint from development documents but remains a small convenience sample; repeated policies are highly similar.

## Real run on 15 November 2026

See `evaluation/rbi_holdout_2026-11-15.json` for individual cases, source hashes, actual model identifier and recorded errors.

| Measure | Result |
| --- | --- |
| Source-only repo-rate exact matches | 4 / 4 holdout documents |
| Accepted Gemini analyses | 2 / 4 documents (50% coverage) |
| Repo-rate exact matches among accepted analyses | 2 / 2 |
| Literal citation checks among accepted analyses | 2 / 2 |
| Rejected quote citation | 1 / 4 |
| Provider unavailable | 1 / 4 |
| Human participants | 0; no comprehension finding |

Gemini 3.8 produced provider errors/timeouts during setup. Gemini 3.5 Flash-Lite completed the recorded run. Generated factual paraphrases are discarded; only source-verified literal quotes appear as facts. Interpretations retain their generated text and cited premises. The rejected August case demonstrates that citation checking can withhold output. None of these checks establishes that an interpretation is causally valid, that sector mapping is suitable, or that users benefit.

Seven accepted public-document analyses are now bundled in `backend/app/data/rbi/recorded_analyses/` for reproducible demonstrations. They are labelled recorded, have their generation dates, and are invalidated when document hash, model or prompt version changes. Provider failures and failed checks are never replaced with invented model results.

## Reproduce and review

Run `python scripts/evaluate_rbi.py --split holdout` for the accepted cached/recorded outputs. Use `--generate --limit 6` explicitly to request missing outputs within the daily budget. Select `--split expanded` for the eleven new cases; the original four holdout assignments are unchanged. A rerun can differ from the recorded run because provider availability and model output can change; do not overwrite the historical report to imply the original run passed.

The runner writes `output/rbi_evaluation/report.json` and a blank manual-review CSV. The source-only baseline extracts the decision paragraph and current repo rate. AI review requires the following separate human judgments; the system does not auto-fill them:

- Factual error count: compare any factual assertion with the source. Quote occurrence alone is insufficient.
- Citation entailment: 0 = unrelated premise; 1 = partially supports interpretation; 2 = supports a clearly conditional mechanism.
- Relevance: 0 = unrelated to monetary-policy exposure; 1 = generic; 2 = explains the particular event and its limits.
- Comprehension: evaluated from participant answers, not inferred from the quality of prose.

A second reviewer should label without seeing which generation passed the automated checks. Record reviewer disagreements and resolutions alongside the CSV. No claim about improved investor behavior should be made from these metrics.

## Adult student study

Open `/study` from the local app. Four actual accepted outputs are frozen in `backend/app/data/rbi/study_manifest.json`, including hike, hold and cut cases. Source hashes, model/prompt versions and displayed text are verified. Materials do not change when the app refreshes or generates more analyses. Prepare a different manifest for a new cohort; never overwrite a pilot already in use. No fixed demo analysis is substituted. The consent screen explains voluntary participation, adult eligibility, local-memory responses, anonymous file download and the absence of automatic submission. Participants can leave before export. Ask volunteers separately; this implementation does not contact or enroll anyone.

The page shuffles document order and alternates source-only versus AI-briefing conditions from a randomized starting condition. A participant never sees the same document twice. Across a small convenience sample this is not guaranteed to balance documents or participants; record these limitations. Suggested initial sample: six to ten adult student volunteers. Follow the college's requirements for consent and research review.

Questions ask for the reported repo rate and whether the announcement establishes that banking shares must rise, followed by a confidence rating. This checks narrow factual recall and overconfidence, not broad financial literacy. Do not coach participants or reveal answers before completion. Participants choose whether to share their downloaded anonymous JSON with the researcher.

Run `python scripts/analyze_study.py DIRECTORY` on voluntarily shared files. The script checks protocol/consent, prevents duplicate participants and repeated documents, and verifies source revisions before reporting descriptive accuracy, confidence and confident incorrect answers by condition. Empty input produces zero participants and no invented averages. Do not commit participant files. Small samples and repeated observations do not support causal or investment-performance claims.

## Live retrieval limits

The official rolling feed was reachable but contained zero matching MPC resolutions. The official policy index exposed four 2026 resolutions, including October's hike, which RSS missed. Refresh now checks both sources, archives supported originals, records revisions and failures, and distinguishes a recent successful index check from an old publication date. Completed checks expire after 24 hours; failed, interrupted, empty-listing and partial checks are labelled explicitly. The index covers its displayed fiscal year and does not establish complete historical coverage.

Transient Gemini HTTP/transport errors can retry once by default. Evidence/schema failures are terminal. Every outgoing request is reserved atomically against a persistent daily budget, including retries and failures; the older budget is imported without resetting it. SQLite stores operational outcomes and hashes locally. Long Retry-After delays are respected by withholding the retry. Challenge pages, non-RBI targets, redirects, oversized responses and unsupported documents fail closed.

## Expanded run on 17 November 2026 (India time)

`evaluation/rbi_expanded_2026-11-17.json` preserves the actual run. Eleven new documents were eligible, and a six-document generation limit was set before requesting Gemini. Five of six requested analyses were accepted; one encountered provider failure. Eight HTTP requests were made, including two retries: a June hold recovered after HTTP 503, while the February 2023 case returned HTTP 503 twice. The report preserves each actual attempt. Five additional cases were not requested. Among accepted outputs, all five rate values and literal citation checks matched. Coverage is 5/6 requested, or 5/11 in the expanded split; neither denominator should be omitted. There were two accepted hike cases and three accepted hold cases in this new run. The original holdout remains separately reported with its failures intact.

A cache inventory across the full archive contains seven accepted outputs out of 22 documents: two hikes, four holds and one cut. This inventory is not a fresh 22-document model run. Source-only extraction matches 22/22 implementation-reviewed rate labels. Model acceptance is constrained by that extractor, so these are gate checks, not independent evidence that AI outperforms extraction. No independent entailment labels or real participant results have been collected. `evaluation/independent_review_template.csv` contains actual generated claims and source quotations with blank human judgments.

The frozen v2 pilot verifies the manifest, complete trial set, alternating conditions, model/prompt/source versions, finite answers and elapsed time, consent and adult eligibility. Duplicate participants, incomplete records and explicit test records are rejected. The aggregator adds a within-participant descriptive difference. Legacy v1 exports require CLI `--allow-legacy` and are labelled unfrozen. See `pilot/README.md` for the ready-to-run pilot.
