# Public-source refresh — 2026-10-10 (JST)

Base: `5ba249becaeb5d5ef04a6cbef3513408330246d8`.

All **164 tables in nine categories** were inventoried and freshly checked: **7 changed**, **156 verified unchanged**, and **1 source unavailable**. The 24 incomplete checks from October 9 were all recovered today. AssistantBench's live Space configuration instead returned HTTP 503 twice and its public Space API reports `RUNTIME_ERROR`; its existing table, snapshot and retrieval date remain unchanged.

## Changes

- SWE-bench Live Go: AMI Agent + Qwen 3.8-27B adds 41/138 resolved (29.7%), verified, dated October 9. The 22 prior rows retain all non-rank fields
- AndroidWorld: `agent-qa by Vostride AI` adds self-reported 100% with GPT-6-Sol, one trial, memory and self-improvement off. The AGI-0 row's current model-column string is `AGI-AW`, but its disclosure describes trained models in the plural without a specific single-model identity. The exact source label is retained and empty model IDs prevent attributing the whole system to a single model
- SWE-Marathon v1.1: Claude Haiku 5.5 / Claude Code, max reasoning, 80/160 successful trials (50%, 20 tasks × 8). Published partial scores, cost and token aggregates remain distinct
- Vending-Bench 2: Claude Sonnet 5.5 and Claude Haiku 5.5 add six runs each, with mean balances of $11,165.28 and $3,602.46 respectively. Version, release dates, costs, variability and trial counts follow the source
- GAIA's top-100 projection has four new and four displaced entries. Retained entries have no numeric changes. New mixed or ambiguous systems remain outside single-model attribution
- APEX overall and management-consulting tables each have 21 display-label typography changes only; scores, errors, configuration and other numeric values are unchanged
- Two existing gap records reflect current primary-source behavior. The prior 24-table incomplete-refresh gap is replaced by the single AssistantBench outage

Result: **164 tables, 4,403 rows, 505 registered model IDs, 23 gaps**. No new model registration, guessed weights, purchased benchmark run or claimed original measurement.

## Coverage

| Category | Changed | Verified unchanged | Unavailable, preserved |
|---|---:|---:|---:|
| coding | 1 | 49 | 0 |
| terminal | 0 | 5 | 0 |
| tool-use | 2 | 30 | 0 |
| web | 0 | 22 | 1 |
| computer-use | 1 | 19 | 0 |
| research | 0 | 9 | 0 |
| security | 0 | 13 | 0 |
| long-horizon | 2 | 5 | 0 |
| general | 1 | 4 | 0 |

Sakana's latest report is still v2. All 55 numeric source cells and 17 retained vendor-claim figures match; the claims layer, mappings and retrieval date are preserved. Claims remain excluded from measured data and fit. All unchanged and unavailable tables preserve prior bytes and dates.

## Evidence and publication safety

`summary.json` provides a complete table-by-table index. Category audits, extraction results and compact response archives retain current primary-source evidence and hashes. Fetched JavaScript/Python is parsed as data, not executed. Models, agents, reasoning settings, benchmark subsets, verification and costs remain separate.

Transient signed redirects, cookie/header material, irrelevant public analytics tokens, public example credential fixtures and attachment-access endpoints and ancillary contact addresses are omitted from newly published evidence. Original and retained hashes and redaction details are documented in the category safety records. Agent-Visco's optional attachment row URL is null; the canonical public AndroidWorld source remains available. Contact-only omissions retain all model, score and benchmark-condition fields. Two nonessential, undecoded GAIA Parquet responses are not included in the public archive; canonical source URLs and fetched hashes remain recorded, and the live leaderboard JSON supplies the score evidence. No signing/access material is required to reproduce the numeric comparisons.

The public SWE-bench Pro leaderboard's “Private Dataset” label describes its held-out task set. Retained provenance is the publicly served aggregate leaderboard, not private benchmark task contents.

## Validation boundary

Independent source review checked all changed rows, all 157 nonchanged tables and snapshots, the unchanged registry/claims and archive integrity. Pinned fit tests, strict validation and exact bundle rebuild equality use Almide `e706ba8c4e32eb39983bd125cec1890d17094300` and Rust `1.94.0`. Final-head CI must pass before merge; independent Pages deployment and public bundle bytes are verified afterward. No UI, builder, fit algorithm, workflow, permission or deployment-setting changes are included.

Only data and provenance records are published. Temporary collection, extraction and validation programs remain outside the repository; the recorded checks were executed locally before publication.
