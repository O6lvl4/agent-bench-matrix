# Public source refresh — 2026-10-07

Base: `b02f0c0505f70d1a8a71456d2615a0ba299e506a`.

This is a **partial refresh**, not a claim that every table is current. All nine categories were inventoried. Fresh primary-source bytes verified **123 of the 163 existing tables**; **40 existing tables remain unchanged because source acquisition was interrupted before their complete evidence was available**. The incomplete tables retain their old retrieval dates and all prior good data. The explicit refresh gap should be removed after those sources are fully rechecked in a later run.

## Changes

- CyberGym: seven added rows across agent-focused (35→39), model-focused (45→46), and E2E (9→11) tables. Current source ranking semantics, stage scores, model/agent focus, dates, budgets, task populations and configurations are retained
- AndroidWorld: AGI-0 changes from 97.4 to 100. The board still dates the entry 2025-10; its note says the September 2026 revision trained on AndroidWorld tasks. Both distinctions are retained
- OSWorld: six existing tables are explicitly labeled Foundation E2E GUI. All 50 prior measured rows are unchanged. A separate public-agent subset of the All tab records Sai with Claude Opus 5 on release v2.1/full/500 steps: 41.67 binary, 79.38 partial, $14.34/task and $1,548.72 total. Its verification is unknown. Only a base planner is disclosed, so `model_ids: []` prevents attribution of the whole system to one model or entry into the fit
- Two exact new source model names are registered with `open_weights: null`: OrcaCyber-Zero-1.0 and Feyospace-v1.1. An undisclosed vendor is explicitly labeled unknown
- The Computer Agent Arena gap now records a missing leaderboard and an unrelated meta-refresh page. The BrowseComp introduction is reachable again, but it does not supply a current official leaderboard

Final source data: **164 tables, 4,377 rows, 503 models, 23 gaps**. The extra gap records the 40 incomplete refreshes; it does not erase existing measured data.

## Preservation and evidence

- Unchanged tables keep their prior bytes and retrieval dates. Source snapshots change only where required by changed data or the OSWorld scope clarification
- Sakana Fugu remains a separate vendor-claims layer. All 55 source-table numeric cells and 17 retained figures match arXiv v2; its claim values, mappings and retrieval date are unchanged
- No model is assigned public weights without evidence. No costs, scores, dates, identities or verification markers are guessed
- Each category JSON records checked tables, source URLs, available HTTP status, response hashes and failed/incomplete coverage. Missing response status/redirect evidence from the interrupted process is explicitly unknown
- AndroidWorld CSV bytes preserve the primary source's original CRLF and trailing whitespace; those raw-source bytes are not reformatted to satisfy whitespace lint
- The dated scripts contain extraction recipes. Source JavaScript/Python is parsed as data and is never executed

## Validation boundary

The repository's builder, fit algorithm, tests, CI pins, UI, permissions and deployment configuration are unchanged. A retained Almide 0.67.0 compiler was used for **provisional local generation only** via its wasm target. Its fit tests pass, and rebuilding untouched main reproduces the published baseline bundle byte-for-byte. This is not represented as exact pinned validation.

Merge requires the unchanged CI to pass on the final PR head with Almide `e706ba8c4e32eb39983bd125cec1890d17094300` and Rust `1.94.0`, including fit tests, strict source-data validation and exact equality of regenerated `docs/data.json`. Pages deployment and live bundle content must then be checked independently.
