# Terminal / tool-use / general audit — 2026-10-10 JST

Scope: all 42 existing tables in these three categories, plus all seven related standing gaps. This worker changed data and source evidence only; no UI, build, workflow, or model-registry files.

## Outcome

- Three changed tables: APEX Agents and APEX Management Consultant each have 21 published display-label typography changes among the same 56 configurations. Their scores, ranks, model identities, effort, dates, providers, errors, and sample counts did not change. GAIA's current top-100 gained four entries and displaced four entries; retained entries have identical numeric results, while 84 retained entries have new source-order ranks
- GAIA additions: Shadow Harness V1.07, Shadow Harness V1.08, Shadow Harness V1.09, and SHAPARTNER V1.01. All have ambiguous multi-model labels and remain unassigned to a single model. Dates, level metrics, source labels and links are preserved
- 39 tables and their snapshots are byte-identical to baseline `5ba249becaeb5d5ef04a6cbef3513408330246d8`; their retrieval dates are not bumped
- All 14 Tau tables now have complete fresh primary coverage, including the manifest and all 67 current submission bodies. All comparison-relevant payloads are unchanged. The former acquisition gaps no longer apply to this run
- All seven standing gaps were rechecked from 22 complete successful current primary responses. Their existing data/gaps files remain byte-identical because their exclusion evidence/reasons did not change
- No new model-registry identities proposed

## Acquisition

The grouped main collector made 110 requests, with 109 complete successful responses and an HTTP 404 for the previously recorded Tau JavaScript URL. The current Tau homepage references `/assets/index-DiyUZzz_.js`; that exact discovered URL was fetched successfully as request 111. Thus the main index retains 110 successful bodies and one obsolete-URL 404. No table is acquisition-incomplete.

The seven-gap batch made 22 successful public-source requests. Two attempts to start this separate batch failed before execution with an environment mount error; normal execution then completed. These were infrastructure errors, not denied or cancelled access. No benchmark source body was fabricated or read from a prior audit in place of a current fetch.

`tool-general-fetch-index.json` and `tool-general-gaps-fetch-index.json` record every completed request outcome, canonical URL, retained response hash and byte count. `tool-general.json` supplies all 42 table-level decisions and the exact GAIA membership delta.

## Science endpoint discrepancy

The complete official site API at `https://www.terminal-bench-science.ai/api/leaderboard?package=terminal-bench-science%2Fterminal-bench-science&name=v0-1-eval` is identical to the saved good snapshot, including all 17 rows and domain metrics. The alternate Harbor POST returns the same leaderboard and overall metrics but omits domain metrics and reports `n_trials=0` on five rows while `metrics.tasks=210`. The site API reports 210 trials on every row. Both current responses are retained; the fuller, comparable site response is selected. The existing measured table and snapshot are unchanged. See `tool-general-science-endpoints.json`.

## Publication safety

`tool-general-responses.tar.gz` includes only sanitized current successful response bodies and portable indexes, under `tool-general/` and `tool-general-gaps/`. It contains 130 successful response bodies plus two indexes. Two ancillary binary Parquet bodies are deliberately withheld: the GAIA test and validation datasets. Their successful fetch status, canonical URLs, original byte counts/hashes, and omission reasons remain in the indexes. Current normalized GAIA scores use the retained live Gradio JSON; the validation gap recheck only requires the fetched hash. Ephemeral signing/access parameters were removed from HF redirect URLs and Toolathlon social-preview image URLs; the opaque Google CSV redirect was replaced by its canonical requested public URL. Canonical sources, original response hashes and published body hashes are retained, with explicit redaction notes. In addition, 116 actual contact-email occurrences were replaced with `[contact-email-redacted]` across 71 new bodies: 60 Tau submission contact records plus author/footer prose and commit metadata/payloads. All Tau changes are confined to `contact_info.email`; comparisons omit that field on both sides and preserve every benchmark/model/agent/config/numeric field. Historical snapshots are untouched. Actual contacts in the remaining text bodies were also scanned. Reserved example-domain placeholders, the public Git SSH transport account, and calendar UID filenames are retained as non-contact syntax. Modified Git commit signature payloads are privacy-redacted and no longer cryptographically verifiable; original whole-response hashes remain available. See `tool-general-contact-redaction.json`. No cookies or request/response headers were retained. The archive was reopened, response hashes verified, and signing/access URL parameters plus actual contact addresses scanned in every published member. See `tool-general-publication-safety.json`.

## Verification

Local offline extraction compared all 42 tables against the pre-refresh baseline, preserving unchanged tables and snapshots. Contact-only redaction comparisons exclude only the documented contact metadata; all benchmark fields remain intact. The verification checked normalized changed rows, full primary-source matches, dates, model IDs, unchanged bytes, seven gap files, the Science discrepancy and every retained archive hash. Temporary execution scripts are excluded from this data-only update. Results, source bodies and provenance remain available in the accompanying JSON records and archive.
