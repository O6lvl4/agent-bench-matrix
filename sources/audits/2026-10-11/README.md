# Public-source refresh — 2026-10-11 (JST)

Base: `034229f577e011a9f619ddf9bffd3bbc777130eb`.

All 164 tables in nine categories were checked against newly fetched primary sources: **3 changed, 160 verified unchanged, and 1 unavailable source preserved**. Result: **4,403 rows, 505 registered model IDs, 23 gaps**.

## Changes

- GAIA's current top-100 projection includes two October 10 mixed-model systems, Shadow Harness V2.01 (93.02) and SHAPARTNER V1.02 (92.36). They remain unattributed to a single model. Three entries at the tied 89.04 boundary replace other tied entries in the source's displayed ordering. The native board sorts average score descending and takes the first 100; no additional local tie sort is applied. All 95 retained systems have unchanged numeric cells. One newly displayed tail entry explicitly names GPT 5.5 and reuses its existing registry ID; other new ambiguous systems have empty model IDs
- APEX corporate-lawyer and investment-banking each have 21 display-label typography changes. Scores, errors, configuration and all other numeric values are unchanged
- HUD's old OSWorld-Verified leaderboard now redirects to a sign-in page (HTTP 200) rather than returning 404. It still exposes no public score table; its existing gap is updated accordingly

AssistantBench still returns HTTP 503 and reports `RUNTIME_ERROR`; its prior table, snapshot and retrieval date remain intact. The previous incomplete-refresh gap remains accurate. All unchanged tables preserve their bytes and dates.

## Coverage

| Category | Changed | Verified unchanged | Unavailable, preserved |
|---|---:|---:|---:|
| coding | 0 | 50 | 0 |
| terminal | 0 | 5 | 0 |
| tool-use | 2 | 30 | 0 |
| web | 0 | 22 | 1 |
| computer-use | 0 | 20 | 0 |
| research | 0 | 9 | 0 |
| security | 0 | 13 | 0 |
| long-horizon | 0 | 7 | 0 |
| general | 1 | 4 | 0 |

`summary.json` indexes every table and its category audit. Sakana's latest report remains v2; all 55 source numeric cells and 17 retained claim figures match. Claim data/date and model registry remain unchanged. Claims stay outside measured tables and fit.

## Evidence and publication scope

Category records retain canonical primary-source URLs, retrieval dates, response hashes, original/stored hashes for disclosed redactions, and mechanical comparison results. Compact archives retain sanitized current public evidence. Ancillary contacts, signing/access URLs and credential-like example literals are omitted with disclosures; benchmark scores and evaluation conditions are preserved. The current tracked October 10 tool/general response archive also receives a minimal correction to omit an incidental feedback-service credential literal, with original fetched hashes retained and stored hashes updated. This corrects the current tree; Git history is not rewritten, and the credential was not used or tested. Temporary collection, extraction and validation programs remain outside the repository. Fetched frontend code is parsed as source data, not executed.

SWE-bench Pro's “Private Dataset” label names the evaluated subset: the retained source is its publicly accessible aggregate leaderboard and contains no private task/code corpus. CAD-Bench's endpoint serves the public leaderboard without credentials. Their authentic public identifiers are retained as provenance.

## Validation

Independent source/privacy review and local pinned fit tests, strict build and exact bundle equality are recorded in `validation.json`. The pinned toolchain is Almide `e706ba8c4e32eb39983bd125cec1890d17094300` with Rust 1.94.0. Final-head CI must pass before merge; main CI, independent Pages deployment and the public bundle bytes are verified against the merge afterward. No UI, executable script, build logic, workflow or permission change is included.
