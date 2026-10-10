# Web and computer-use source refresh — 2026-10-10 JST

- All 43 existing tables have explicit outcomes: 41 fully compared and unchanged, AndroidWorld changed, AssistantBench unavailable with prior good data preserved
- All 82 current BrowserGym result bodies were freshly obtained at the live manifest's immutable revision. This closes all seven October 9 acquisition gaps; every result record is unchanged
- AndroidWorld grows from 47 to 48 rows. The new `agent-qa by Vostride AI` row reports 100%, one trial, `gpt-6-sol`, and memory/self-improvement switched off. Its source says community self-reported with no independent verification; `verified=false` is retained. The model ID was already registered
- AndroidWorld's source-provided competition ranks shift for 42 existing rows. No existing score changes. AGI-0's model column changes to `AGI-AW`, and its note replaces the older Qwen3.5-specific training disclosure with “trained open source models.” The exact new name/disclosure are retained; `model_ids=[]` stays empty because a single foundation-model identity is not established. The official provider homepage and previously linked article returned 403, with no bypass attempted
- The whole AndroidWorld source sheet was compared column by column, including model identity, size, type, screen representation, date, openness, trial count, pass@k, links and notes. The raw source and normalized data both contain all 48 current main-board rows; human baseline remains separate
- AssistantBench's live config returned 503 twice. Its public Space API reports `RUNTIME_ERROR`; immutable source code loads `Ori/results`, whose public API returns 401. Its 184 prior rows, source snapshot and October 5 retrieval date are preserved
- OSWorld JSON, renderer JavaScript and HTML are unchanged. The 51 result records retain v2.0/v2.1 release, full/offline taskset, step-budget, Foundation E2E GUI/public-agent, cost, verification, and single-/mixed-system distinctions
- Nine existing gaps were rechecked. Computer Agent Arena now returns 522 for both its leaderboard and root, so its failure description/date are updated. The other eight gap files/dates are byte-preserved; none became mechanically extractable
- No model-registry changes or new-model proposals. No UI, build, workflow or application-code changes

## Evidence and reproduction

`webcomputer.json` covers every table, `webcomputer-gaps.json` covers all nine gaps, and `webcomputer-androidworld-review.json` records full-cell deltas and identity decisions. The acquisition made 132 public read-only requests across 131 unique URLs, with 122 successful response bodies archived in `webcomputer-responses.tar.gz`. No cancelled or reviewer-denied tool request occurred.

Local offline replay reproduced all 43 outcomes from the archive and validated retained hashes against the published audit, using baseline `5ba249becaeb5d5ef04a6cbef3513408330246d8`. All 42 unchanged/unavailable tables and their snapshots preserve their prior bytes. Temporary execution scripts are excluded from this data-only update.

## Publication safety

All cookie/authentication headers and transient response redirect URLs are omitted from published metadata. The entire Aliyun attachment-access URL on Agent-Visco's source row and the nonessential submission contact email in the sheet footer are removed from the newly retained CSV/archive; the optional normalized `row_url` remains null. All source cells were inspected for contact/access details. The canonical public board, original response SHA-256, redacted stored SHA-256, and explicit redaction disclosure remain recorded. Six further archived responses omit nonessential WebArena/VisualWebArena submission contacts, OSWorld-MCP maintainer contacts, and HUD sales contact metadata. In total, seven response bodies contain 13 contact-address omissions plus the one attachment URL omission. REAL benchmark/example addresses and retrieved answers, source-code examples, and Git SSH references are intentionally preserved. No scores or evaluation conditions were changed by these redactions.

AndroidWorld original response SHA-256: `fa55b5154926e6027efa02dda6a07d15e008b3e314adbc20d0980ce537aca8f0`

AndroidWorld retained response SHA-256: `2932158ec655c99282b9e273e9756d71b5269eb5b361a397e70b30598f751b34`

Parent handles the pinned strict aggregate build, PR, CI and publication gates.
