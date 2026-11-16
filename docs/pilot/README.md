# Four-case adult student pilot

Status: materials prepared and mechanically checked. Zero volunteers enrolled, zero actual responses collected, independent human interpretation review pending. No participant finding is claimed.

The frozen v2 manifest uses real accepted Gemini outputs for October 2026 (hike), August 2026 (hold), December 2025 (cut), and December 2022 (hike). It binds all four cases to source hashes, exact displayed text, model versions and prompt versions. Keep this manifest for the entire cohort. Seven accepted recordings are bundled for reproducibility; no API key is needed to run this pilot.

## Before enrollment

1. Have a second person inspect the source quotations and interpretations using `../evaluation/independent_review_template.csv`. Entailment and relevance use 0–2 scales described in `../rbi_evaluation.md`. Leave ratings blank until a human makes them; record disagreements and adjudication. The automated checks cannot substitute for this review.
2. Use the college's research/consent requirements. Recruit six to ten adult volunteers using `invitation.md`. This is a convenience pilot; the software neither contacts nor enrolls anyone.
3. Run `python scripts/run_server.py` and open `/study` on the machine running Sarthi. Responses stay in page memory and leave only when the participant chooses to download and share the anonymous JSON. Do not expose this local development server publicly.

## Session procedure

For development checks, use `/study?test=1`. Its exports are visibly marked as tests and rejected by the response aggregator. Test runs never count as participants.

Allow roughly five to ten minutes per person. Use a fresh page for each participant. Let the person read the adult consent statement and choose whether to start. Do not show the answer key, coach, or look over their answers. Each person sees four different announcements; document order and starting condition are randomized, and conditions alternate. This balances the number of trials within a person, but does not guarantee a balanced assignment of each document across people.

At completion, the participant can download a file and independently choose whether to share it. Ask for no names, holdings or contact details in that file. Retain voluntarily shared files in a private directory with a deletion date agreed with participants and the college. Never commit them. The generated `sarthi-study-*.json` filenames are ignored by Git.

## Analyze voluntary responses

```powershell
python scripts/analyze_study.py C:\private\sarthi-pilot
```

The script verifies consent, adult eligibility, cohort hash, complete unique documents, alternating conditions, model/source versions, confidence and finite numeric answers. It rejects duplicates, incomplete exports, and records explicitly marked as tests. It cannot establish that a person is unique, adult, or honest; those are procedural limitations. Keep any development simulations separate and mark them `test_record: true`.

Report participant count, trials by condition, accuracy on the two narrow questions, mean confidence, high-confidence incorrect trials, and the mean within-person briefing-minus-source accuracy difference. Show document/condition imbalance. Do not claim causal improvement, statistical significance or better investment outcomes from this small sample. An empty directory produces zero participants and null averages.

## New cohorts

Use a new filename and pilot identifier when changing cases or wording. `python scripts/prepare_study.py RBI_ID ... --output PATH` accepts two or four different bundled documents with accepted analyses and refuses to overwrite an existing manifest. The local app serves its default manifest; changing that requires an intentional researcher edit before enrollment. Legacy v1 files require explicit `--allow-legacy` and lack frozen-cohort verification.
