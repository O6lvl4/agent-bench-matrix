# Coding source audit: 2026-10-10 (Asia/Tokyo)

- Scope: all 50 coding tables, 1,543 prior rows. The reviewed source recipes made 29 grouped current primary HTTP requests, including current DeepSWE frontend price-transform support; all returned 200. Native JSON/YAML/CSV/HTML/RSC projections cover complete comparable result sets.
- Result: one changed table, 49 unchanged tables, no coding refresh gaps, 1,544 rows. All 49 unchanged table/source/provenance groups are byte-identical to baseline and keep their prior retrieval dates. No model registry additions or edits are needed.
- SWE-bench Live Go: one added `AMI Agent + Qwen 3.8-27B` row, dated Oct 9, with 41/138 resolved = 29.7%, source verification true, at rank 13. The ten lower rows advance one rank; all other fields of the 22 prior rows are unchanged. The literal source model name maps to existing registry name `Qwen 3.8 27B` by dash/space formatting only. No reasoning setting, organization, or open-source status is inferred.
- DeepSWE: each table's declared JSON primary source is selected before the shared homepage. Both current datasets and frontend pricing literal/formula were checked; scores, provider price rescaling, configurations, and dates remain unchanged.
- SWE-bench Pro: current public and private aggregate variants are separately projected from the unified public page. Both remain unchanged, including native rank. No task corpus or gated data is accessed.
- Related gap: the official unified page still links to the deprecated capped-run results. The scale.com deprecated URL, labs.scale.com deprecated URL, and former commercial URL all now return HTTP 404 rather than the previously recorded HTTP 403. The gap record is updated with these actual responses; current public/private results are not substituted for the old capped runs.

## Evidence and replay

`coding.json` records all 50 table outcomes, actual URLs/statuses, original response hashes, projection outcomes, and snapshot hashes. `coding-fetch-index.json` contains the 29 grouped requests. `coding-gaps.json` records the three additional HTTP 404 responses and the official linking page. `coding-row-deltas.json` records exact row changes. `coding-files.json` records before/after hashes for every protected table/source/provenance file.

`coding-responses.tar.gz` retains compact indexed response evidence for all 32 requests. `coding-response-archive.json` records each member hash, archive hash, scan patterns, and redaction disclosure. The publication scan found no signed credential-like URL query values or private credential literals. One public frontend analytics token is redacted as a precaution; original and stored response hashes are retained. Empty token query templates in library code contain no values. Response headers, cookies, and authorization headers were not stored. No fetched JavaScript was executed.

The local extraction replay used the acquired coding cache and baseline `5ba249becaeb5d5ef04a6cbef3513408330246d8`, preserving existing reviewed projections, explicit source identities and unchanged files/dates. The retained archive and row-delta records document its inputs and results. Temporary execution scripts are not included in this data-only update.

## Verification

All 50 tables passed registry identity, source/row date, newest-row-date, and snapshot-hash checks. The 49 unchanged table/source/provenance groups are byte-identical to baseline. All prior Go row fields other than rank are preserved. The model registry is byte-identical to baseline. All 32 archived response hashes verify. An offline replay from the sanitized archive reproduces all 50 delivered row sets, including both DeepSWE pricing checks. The coding-scoped `git diff --check` passes. `coding-verification.json` records these checks. The parent task owns pinned build, bundle, and repository-level gates.
