# Web and computer-use source refresh — 2026-10-14 JST

- 43 retained tables: 42 mechanically verified unchanged; AssistantBench remains unavailable (live config HTTP 503 twice, public Space RUNTIME_ERROR), so its 184 prior rows and source snapshot remain intact. All 964 retained rows, retrieval dates, identities and source files are byte-preserved.
- AndroidWorld: all 48 main-board rows and full CSV cell content match; ranks, dates, trials, verification and mixed-model distinctions independently checked.
- BrowserGym: current manifest and all 82 result bodies fetched at immutable revision `294ebe1dc36ba83c6916c64c64fb870af3dc8cee`; every source record/field matches.
- OSWorld: full 51-record official JSON, renderer and release/scope splits unchanged; old workbook sheets compared cell by cell. REAL task aggregates recomputed; Kaggle BrowseComp’s 42 scores, confidence intervals, dates and identities unchanged.
- Nine standing gaps rechecked. HUD’s homepage was redesigned, while `/leaderboards` still returns 404. Followed official Research and Environments links; no current public OSWorld-Verified score table was exposed. A proposed HUD gap description/date/URL update is the only data change. Other eight gaps remain unchanged.
- No model proposals. No table/source snapshot, model registry, UI, build or application changes. No paid evaluations, authentication, external mutations or denied-access bypass.

## Evidence and acquisition

`webcomputer.json`, `webcomputer-row-deltas.json` and `webcomputer-gaps.json` contain per-table/gap outcomes and exact zero row deltas. Unavailable AssistantBench explicitly has `current_source_verified: false`; zero applied deltas do not imply that live rows were verified.

The deduplicated main pass made 131 read-only requests across 129 unique canonical URLs, including second attempts for two HTTP 503 Gradio configs. One preliminary OSWorld connectivity read brings actual requests to 132. All 123 successful main-pass bodies are hashed and archived in `webcomputer-responses.tar.gz`; the initial connectivity response was not separately saved. Current public AssistantBench source revision is unchanged; its already access-denied backing dataset was not retried.

`webcomputer-verification.json` records source/table byte preservation and an offline replay that hashes all 123 archived bodies and reproduces 42 unchanged plus one unavailable outcome. No fetched code was executed.

## Publication safety

The archive omits cookies, authorization headers, transient response redirect destinations, 16 ancillary contact-email occurrences and two attachment/access URLs. 151 Google redirect links retain their canonical public destinations without tracking/signing parameters. Original/stored hashes and omission counts are disclosed in `webcomputer-publication-safety.json`. No scores or evaluation conditions were removed. Remaining email-like values are benchmark fixtures/source-code examples/Git references; both workbooks have no email matches. No credential-bearing query strings or attachment-access endpoints remain.

## Applying results

Copy the listed public audit files to `sources/audits/2026-10-14/`. The only proposed data file is `proposed/data/gaps/hud-osworld-verified.json`. Do not copy the raw directory, helper scripts, private fetch index, logs or replay workspace. Aggregate validation and publication remain the parent task’s responsibility.
