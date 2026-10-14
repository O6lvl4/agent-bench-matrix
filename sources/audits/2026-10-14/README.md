# Public-source refresh — 2026-10-14 (JST)

Base: `e51959f4006cb24b4c4b06659bd3ba02c6d0fb39`.

All 164 tables in nine categories received fresh primary-source checks: **2 changed, 161 verified unchanged, 1 unavailable source preserved**. Result: **4,412 rows, 508 model IDs, 23 gaps**. `summary.json` indexes every table and its category audit.

## Changes

- Vending-Bench 2 adds Muse Wonder and Muse Wonder Full, both with six runs and October 12 release dates. The published mean final balances are 9,432.18 and 12,291.558333333334. Ten existing mean cost fields are revised by the board; existing outcome scores are unchanged. The new models already exist in the registry, with unknown weight availability preserved. Missing Full cost/provider fields remain absent/null. This is the existing Vending-Bench 2 table, not the separately incomparable Arena rounds.
- GAIA's native top-100 projection adds work1.0, agent V1.0 and pdd, each with 91.69 overall on October 13. Three old cutoff entries leave the displayed projection. Generic `gpt`, `claude`, and misspelled `calude` model labels remain unmapped. All 97 shared rows retain their non-rank fields; native tied-row ordering is preserved.
- HUD's old OSWorld leaderboard remains HTTP 404. Its redesigned homepage and official Research/Environments pages were inspected; no current result table was found, so the gap description is updated without inventing measurements.

AssistantBench still returns HTTP 503 and its Space reports RUNTIME_ERROR. Its previous 184 rows, snapshot and retrieval date remain intact; the existing incomplete-refresh gap remains. This table is not represented as freshly verified. All 162 unchanged or unavailable table files retain their prior bytes. Existing model registry and claims remain unchanged.

## Evidence

Group audits distinguish changed, unchanged and unavailable outcomes. Shared sources were fetched once per acquisition group. Publication-safe response archives support coding, tool/general and web/computer comparisons. Research/security/long-horizon audits retain primary response URLs, hashes and outcomes; the changed Vending source snapshot retains the parsed score-bearing data with the unchanged display/aggregation rules. Six research gaps were rechecked. The vendor-claim report remains v2: all 55 numeric cells and 17 retained figures match.

No authenticated sources, paid evaluations, customer dependencies or private data were used. Incidental contact/access information was omitted from response archives, as disclosed in their publication-safety records. Source JavaScript was parsed as inert text, not executed.

## Validation

The fixed compiler is Almide `e706ba8c4e32eb39983bd125cec1890d17094300`, built with Rust 1.94.0. All four fit tests pass. Strict builds pass twice and generate byte-identical bundles, with zero unknown model IDs. All 71 Vending rows and all 100 GAIA rows were independently reconciled against their source snapshots. CI and the independently triggered Pages deployment must be verified for the final commit after this preparation.

UI, scripts, workflows, permissions and authentication remain unchanged.
