# Research, security, long-horizon, and vendor-claim refresh

Checked on **2026-10-10 (Asia/Tokyo)** against baseline `5ba249becaeb5d5ef04a6cbef3513408330246d8`.

## Outcome

- All **29 measured tables, 637 rows** were re-extracted successfully from fresh primary responses
- **2 tables changed; 27 tables and their primary snapshots remain byte-identical**, including their original retrieval dates
- No new model IDs are proposed; model registry was not edited
- The prior SWE-Marathon and Vending-Bench v1 current-JavaScript transport gaps are recovered
- All six related gaps were freshly rechecked; their original gap files/dates remain unchanged because the availability and comparability conclusions still hold
- Sakana Fugu report **v2 remains latest**. All **55 numeric cells** in Table 1 and all **17 existing claim figures** match the preserved source extracts and claim records. Claims remain separate from measured tables and the fit

## Actual additions

| Table | New row | Score | Runs / trials | Published cost |
|---|---|---:|---:|---:|
| SWE-Marathon v1.1 | Claude Haiku 5.5 / Claude Code, max reasoning | 50% full-pass rate; rank 3 | 160 trials over 20 tasks | $22.139151587125006 mean per trial |
| Vending-Bench 2 | Claude Sonnet 5.5 | $11,165.27833333333 mean final balance; rank 5 | 6 runs | $172.18 mean per run |
| Vending-Bench 2 | Claude Haiku 5.5 | $3,602.4633333333345 mean final balance; rank 46 | 6 runs | $11.13 mean per run |

All existing rows in these tables preserve their substantive values and conditions; only ranks shift to accommodate the additions. SWE-Marathon row dates remain null because the board does not publish row dates; the latest underlying trial start is October 8. Vending-Bench release-date labels are retained separately as the source provides them. The three benchmarks SWE-Marathon v1.0, v1.1, and Vending-Bench versions remain distinct.

The SWE-Marathon fallback-model row still has no single-model attribution. Vending-Bench arithmetic mean, geometric mean, standard error, number of runs, and published mean cost remain separate fields.

## Gap and claim evidence

`research-gaps.json` records current primary-source checks for BountyBench, BrowseComp-ZH, standalone CORE-Bench, RE-Bench, standalone BrowseComp, and Vending-Bench Arena. Arena's latest round remains #13. CORE-Bench still directs users to HAL. The separate 42-row Kaggle BrowseComp board was verified by this daily batch's web/computer audit and is not treated as a browsing-agent result under the standalone gap.

`research-claims.json` records exact Sakana report numeric comparisons, latest-version history, and source hashes. It does not alter measured rows or claim mappings.

## Evidence and replay

- `research-source-index.json`: each actual requested canonical URL, HTTP status, original response hash, retained-body hash, and archive member
- `research-source-responses.tar.gz`: sanitized response bodies, including current bundles and dependencies for offline extraction
- `research-security-horizon.json`: all-table outcomes and preservation hashes
- `research-row-deltas.json`: complete new rows and a distinction between rank-only and substantive changes
- `research-rank-review.json`: current display/filter/aggregation snippets and independent rank checks
- `research-verification.json`: preservation, archive integrity, full changed-table aggregate checks, and offline replay result

The archive omits headers, cookies, authentication state, and signed redirect URLs. Four embedded credential-query examples in the SWE-Marathon bundle were reduced to canonical URLs; the public RE-Bench archive password and two occurrences each of public AWS EXAMPLE access-key/secret-key fixtures were redacted. The AWS values are public example fixtures, not live credentials. Ancillary contact email values and mailto targets were also removed across the newly retained responses, including author links, metadata.contact, and unrelated trace/example contacts. These omissions are disclosed per archive member. The addresses omitted from 99affb3adf9dc7.source, f7c31360a2b1c8.source, and b18c67be3fe48e.source belong to simulated benchmark trajectories/examples and are not established actual personal contacts; only those address strings were omitted, while all scoring/model/configuration fields remain intact. Historical canonical snapshots were not changed for this cleanup. Those edits affect neither benchmark identity/score/configuration fields nor extracted results. Original and retained hashes disclose the exact redaction boundary. Obsolete recorded JS URLs return 404, but their current page-linked replacements were fetched and used successfully.

Local offline replay and verification were completed before publication. Temporary execution scripts are not included in this data-only update.

The verification checked all retained response hashes, independently recomputes all 25 SWE-Marathon v1.1 rows from task trials, checks all 69 Vending-Bench 2 rows against distinct run/date/cost maps, reruns the transactional parser from the sanitized archive, and confirms that all 29 table/snapshot files remain byte-identical after replay.

No UI, build logic, workflow, model registry, or executable script is changed by this batch. The parent task owns the pinned aggregate build and publication checks.
