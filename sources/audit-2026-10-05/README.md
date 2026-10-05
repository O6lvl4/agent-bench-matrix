# Public source audit — 2026-10-05

Base: `ddbc61d98dbe484078655f129086acc30ca8fa8d`.

- Re-fetched and compared all 161 existing tables across all nine categories, grouped into 91 shared first-source URLs/request descriptions.
- Added two **separate OSWorld release-v2.1** tables (full 108 tasks and offline 82 tasks, 500 steps). The original v2.0 tables are not merged into these.
- Final measured data: **163 tables, 4,369 rows** (net +168), **501 registered models** (+15), **22 gaps**.
- New registry entries use `open_weights: null` when a public weights distribution has not been independently established.
- The separate Sakana Fugu claims layer was rechecked against arXiv v2: all 55 source-table numeric cells and 17 retained figures are unchanged. Claims remain outside measured tables and the fit.

## Material changes

- Coding: seven rows added (GSO +4, SWE-bench Live Lite +2, Live TS/JS +1); five DeepSWE GPT-6 Astra cost rows corrected using current frontend pricing. SWE-bench absent verification markers are null; explicit false text markers retain their note.
- Terminal: Terminal-Bench 4.0 adds nine configurations; Science adds three. All 70 × 3 = 210 Science trials remain distinct from an API `n_trials: 0` field; the latter is retained separately where inconsistent. Grok 4.7's partial-cost qualifier is retained.
- Tools: four APEX tables now have 53 configurations each (from 24), retaining effort distinctions and separate Mean Score / Pass@1. Current job-specific task counts are 80. MCP-Atlas adds three rows, with source renames preserved. One custom GPT Live banking submission added.
- General: GAIA's current top 100 re-extracted. Ambiguous multi-model systems cannot become single-model fit observations. Explicit GPT Live → GPT-6 Astra backend configurations are likewise represented as composite systems; simulators and reviewers are not scoring-agent model IDs.
- Web/computer use: MobileWorld adds Wuying-Mobile-27B; AndroidWorld adds Kirk Engine and replaces the source's DroidRun row with MobileRun/GPT6 Astra; OSWorld v2.1 remains separate.
- Research/security/horizon: BrowseComp-Plus, CyberGym, SWE-Marathon v1.1, and Vending-Bench 2 refreshed. These include source corrections as well as new rows; source versions and model mixtures are preserved.

## Evidence and preservation

`summary.json` inventories every table, row counts, shared-source groups, and final snapshot hashes. Per-source provenance is in the table directories, `sources/research-audit-2026-10-05/`, and this directory. `tool-general-fetches.json` retains response hashes and URLs for the grouped terminal/tool/general fetches. The dated Python scripts contain the data-only extraction recipes; raw JavaScript/Python from sources is parsed, never executed.

Unchanged snapshots are retained byte-for-byte. Rotated frontend assets were resolved from official pages. All 22 pre-existing gaps were rechecked; source errors remain gaps and never erase good table data. Existing deliberately excluded inactive boards retain that policy, rather than claiming they are unreadable. The HUD leaderboard now returns 404; the deprecated Scale board remains inaccessible. Raw source CSV whitespace is retained as evidence.

The existing pinned Almide compiler, fit tests, strict builder, and exact-bundle check are unchanged. The published bundle is regenerated from source data; UI, authentication, secrets, permissions, and deployment settings are not modified.
