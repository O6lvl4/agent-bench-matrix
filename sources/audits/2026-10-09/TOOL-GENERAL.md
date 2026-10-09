# Terminal / tool-use / general audit — 2026-10-09 JST

Scope: all 42 current tables in these three categories, plus 7 existing gaps. No UI, application code, or model-registry edits are part of this worker's changes.

## Outcome

- 8 changed tables: Terminal-Bench 4.0 (27 → 35 configurations), Terminal-Bench Science (17 unchanged overall scores; source trial-count inconsistency resolved), the four APEX tables (53 → 56 configurations each), GAIA (six new entries in the current top-100), and MCP-Atlas (34 unchanged scores with source rank corrections)
- 20 tables verified unchanged against retained current primary responses; their table bytes and retrieval dates are unchanged
- 14 Tau tables lack a complete submission response set; their table bytes, snapshots, and retrieval dates remain unchanged
- 7 existing gaps rechecked from 22 complete successful responses; all remain gaps under the existing inclusion policy
- Two proposed model IDs were supplied separately for parent registry handling: `mimo-v2.6-flash-rl` and `claude-haiku-5.5`. Both identities are explicit in Mercor's primary payload; weight availability remains unknown

## Acquisition boundary

The original collector's polling call reported that network approval was cancelled. The already-written index contains 110 request outcomes: 57 complete successful responses and 53 errors. These errors comprise 51 Tau submission tunnel-403 failures, an obsolete Tau JavaScript URL returning 404, and the Science Harbor POST returning 500. No network retry or alternate network route was used after cancellation. The Science site's official GET response was already retained successfully and contains the same leaderboard/package/version and 17 overall results.

`tool-general-fetch-index.json` identifies every attempted URL, response hash, byte count, HTTP result or error. `tool-general.json` contains table-level coverage and exact missing submission URLs. The parent owns the current-run aggregate gap.

## Source handling

Changed snapshots contain machine-extracted primary data. Effort, harness, model labels, source dates, costs, uncertainty, and score variants remain distinct. Ambiguous or multi-model GAIA submissions have no normalized single-model attribution. Science domain metrics remain in its snapshot and are not mixed into the overall score.

MCP-Atlas imports the same retained Scale renderer chunks inspected by the coding audit. Static code forwards and renders `entry.rank`; the source page's old Rank (UB) footnote contradicts the current sequential native ranks. Both this discrepancy and the unchanged stale top-score teaser are disclosed. No runtime browser verification was claimed.

## Reproduction and checks

`tool-general-responses.tar.gz` contains only already-retained successful primary and gap bodies plus complete response indexes, under `tool-general/` and `tool-general-gaps/`. Unpack outside the repository and set `ABM_TOOL_CACHE` / `ABM_TOOL_GAPS_CACHE` to those directories. The local-only `refresh-tool-general.py` and `audit-tool-general-gaps.py` parse these bodies without executing fetched code. Run on the pre-refresh checkout to reproduce the recorded before/after audit; rerunning on refreshed tables naturally reports them unchanged.

Checks passed: all 42 tables have valid dates, newest-row dates, and registered model IDs; all 28 complete current sources match their snapshots; all 8 changed normalized tables reproduce exactly; the other 34 table files remain byte-identical to the base checkout. Parent performs aggregate strict build, bundle parity, and final integration gates.
