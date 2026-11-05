# Sarthi: implementation status and college-project scope

The executable implementation is the reference for project status. The original PDF records the initial vision and contains superseded claims about scoring, privacy, and capabilities.

## Current scope

The prototype demonstrates financial-event explanations using synthetic fixtures, deterministic scenario lookup and local exposure matching. Its contribution is a transparent workflow that makes source-rule decisions, interpretation, counterarguments and abstention visible. It has not demonstrated improved investor rationality or investment outcomes.

Implemented: FastAPI, static HTML/CSS/JavaScript UI, keyword classification, day/category-limited token clustering, distinct publisher/domain checks, assigned-tier source rules, exact-input scenario coverage, explanation gates, local portfolio matching, historical reference library, hypothetical risk response labels, and fixed event-specific answers.

Not implemented: live source retrieval, verified source excerpts, AI API integration, Supabase, Next.js, general financial chatbot, CSV import, validated confidence scores, psychometric calibration, suitability checks, backtesting, and scheduling. Disclosure levels and risk labels are exploratory onboarding concepts; ranking currently uses local holding exposure and exclusions rather than a validated risk model.

## Evidence contract

Every card exposes the synthetic input excerpt, sample date, assigned source attribution, evidence status, impact status, mechanism, comparison limitations, explicit uncertainty and gate result. Background institution links do not substantiate sample claims. No numerical confidence is shown.

Only an exact sample ID/title/content match receives a manually authored scenario. Unknown inputs, changed content or non-sample inputs abstain. A future live path must not inherit demo verification labels or scenario conclusions.

Source tiers govern a demonstration rule, not certainty about economic impact. Different publisher names cannot establish reporting independence. Current clustering remains a heuristic and may miss paraphrases or merge similar reports.

## Demonstration scope

Use three main walkthroughs: tobacco duty, monetary-policy stance, and corporate separation. Show an uncorroborated rumor failing the source rule and the brief becoming empty when there is no relevant exposure. Shipping is an optional second-source illustration. The sample dates are never described as today's news.

## Next research steps

1. Collect a small, independently annotated set of historical announcements. Store actual document URLs, publication and retrieval dates, verbatim evidence spans, and provenance checks. Remove or flag unsupported claims in the historical library.
2. Define claim-level factual checks and an explicit unknown outcome. Separate confirmation of an announcement from the plausibility, magnitude, and timing of its effect.
3. Compare classification, clustering and relevance against human labels. Report precision, recall, coverage, and missed important events; do not impose an arbitrary target percentage of discarded news.
4. Compare the sourced explanations with a plain-news baseline in a small consented student study. Measure comprehension, ability to distinguish facts from hypotheses, and inappropriate confidence. Do not claim reduced panic-selling from a simulated answer.
5. If adding an LLM, require source-span citations, schema validation and abstention; evaluate against held-out events before exposing conclusions. Generated explanations are not automatically faithful reasoning traces.
6. Add broader data and features only after the narrow pipeline demonstrates reliable attribution and useful explanations.

## Technical follow-ups

Live ingestion requires source-specific parsing, provenance validation, independent-origin tracking, event identifiers, corrections handling and persistence. The current daily endpoints rerun the lightweight fixture pipeline; a live service would need cached, versioned runs. Browser holdings need validated imports, clearer disclosure handling, origin security and a defined persistence policy before real use.

## Presentation language

Describe a college prototype with local browser matching and illustrative scenario analysis. Avoid claims of institutional quality, hallucination immunity, cryptographic zero knowledge, measured loss-aversion coefficients, or regulatory approval. State which parts are implemented and which are proposed.
