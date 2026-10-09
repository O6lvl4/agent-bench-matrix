# Coding source audit: 2026-10-09 (Asia/Tokyo)

- Scope: all 50 coding tables, 1,542 prior rows. Primary fetches were grouped by URL using the reviewed `scripts/refresh_coding_sources.py` source recipes: 29 HTTP responses, all 200. Nineteen current official Scale frontend chunks were additionally fetched to resolve a changed rank field; all returned 200. The source was parsed as text, never executed.
- Result: 4 changed tables, 46 unchanged tables, no remaining coding refresh gaps, 1,543 rows. The 46 unchanged table files, source snapshots, and provenance files match baseline bytes and retain their previous retrieval dates. Model registry is untouched; no additions are needed.
- SWE-bench Live Java: one added Oct 8 Slingshot-v3.4.0 + GPT-5.6-Sol row, 108/160 resolved = 67.5%. Existing ranks advance one place.
- SWE-bench Live Lite: TianxiCode + Deepseek-v4.1-Flash changes from 204/300 = 68.0% to 213/300 = 71.0%, with the source date advancing to Oct 8. Its rank swaps with Slingshot. All other score/configuration fields remain unchanged.
- SWE-bench Pro public/private: 14/8 rank changes respectively. Models, scores, confidence intervals, dates, and configurations are identical. Native `entry.rank` now holds sequential ranks. The current official `LeaderboardEntriesSection` passes entries directly to `LeaderboardScoreEntry`, which renders `entry.rank`. Exact reviewed source excerpts and hashes are retained beside this file. The page's old Rank (UB) explanation conflicts with its current native data and renderer; the data notes disclose this without inventing a replacement ranking calculation.
- DeepSWE v1: the generic refresh initially selected the shared homepage ahead of its JSON because of fetch-index insertion order. The reviewed replay chooses each table's declared primary URL before projection and checks the current frontend pricing transform. Both DeepSWE tables are unchanged and preserve all prior values and dates; this is not a source-access gap.

## Evidence and replay

`coding.json` contains per-table source URLs, actual HTTP outcomes, raw-response SHA-256, projection outcome, and current snapshot SHA-256. `coding-fetch-index.json` and `coding-frontend-fetch-index.json` record grouped requests. `coding-rank-review.json` and the two `swe-bench-pro-*-render.js` files retain the exact relevant frontend excerpts; character offsets identify their positions in the fetched response. `coding-row-deltas.json` records exact row changes.

`refresh_coding.py --cache <HTTP-cache>` replays the acquired cache against baseline `af0325ce49fdeb5200bd9730b195cc0537c63f05`. It imports the existing reviewed projections, fixes primary source selection for DeepSWE, permits SWE-bench Pro rank-only changes after asserting direct-render evidence, and preserves unchanged data. The cache index contains the request descriptions and body hashes; the canonical per-table snapshots retain the projected source data used for rows.

## Verification

All 50 coding tables passed registry identity, row-date, newest-row-date (changed tables), and snapshot-hash checks. All 46 unchanged table/snapshot/provenance file groups are byte-identical to baseline. `git diff --check` passed. The parent task owns full build, bundle, and repository gates.
