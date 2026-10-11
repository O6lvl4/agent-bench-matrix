# Web and computer-use source refresh — 2026-10-11 JST

- All 43 existing tables have explicit mechanical outcomes: 42 fully compared and unchanged; AssistantBench remains unavailable with its prior good data preserved. The 964 retained rows, table retrieval dates, model identities and source snapshots are unchanged.
- All 82 current BrowserGym result bodies were freshly fetched at the immutable revision from the live manifest. Every source record and field matches the retained snapshots.
- Kaggle BrowseComp's public POST response was parsed and all 42 scores, confidence intervals, model identities, dates and links were compared. Its complete response is unchanged.
- AndroidWorld's original CSV response is byte-identical to October 10. All 48 main-board rows and all columns match, including source ranks, model identity, model size, type, screen representation, dates, openness, trial count, pass@k, links and notes. Source self-report verification and mixed-model distinctions remain unchanged.
- OSWorld's complete JSON, renderer and HTML are unchanged. Release v2.0/v2.1, full/offline taskset, step budget, Foundation E2E GUI/public-agent, cost, verification and single-/mixed-model distinctions remain separate. The older workbook sheets were compared cell by cell.
- AssistantBench's live config returned HTTP 503 twice; its public Space API still reports `RUNTIME_ERROR`. Fresh immutable source identifies the backing `Ori/results` dataset, whose public API returned 401. The 184 prior rows, snapshot and October 5 table retrieval date remain untouched.
- All nine standing gaps were rechecked. HUD's former leaderboard URL now redirects to an HTTP 200 sign-in page with no public result table, replacing the prior 404. Only that gap's description and retrieval date are updated. The other eight gap files and dates are byte-preserved; none became mechanically extractable.
- No model-registry changes or new model proposals. No table, source snapshot, UI, build, workflow or application-code changes.

## Evidence and verification

`webcomputer.json` documents each table comparison; `webcomputer-gaps.json` documents all nine gaps. The acquisition made 131 public read-only requests across 129 unique URLs, with 123 successful response bodies archived in `webcomputer-responses.tar.gz`. Two extra requests are the second attempts for the unavailable AssistantBench and ST-WebAgentBench configs. No cancelled or reviewer-denied acquisition request occurred.

All 43 tables and their existing source files were checked byte for byte against baseline `034229f577e011a9f619ddf9bffd3bbc777130eb`. An offline replay validated every archived member's stored hash and reproduced all 43 table outcomes. Temporary execution helpers are kept outside the repository and excluded from this publication. The published audit includes canonical URLs, source metadata, hashes, methods and outcomes.

## Publication safety

Cookies, authentication headers and transient redirect destinations are excluded from published metadata. Eight archived response bodies omit 14 nonessential contact-address occurrences; one also omits the entire AndroidWorld Aliyun attachment-access URL. This includes the WebChoreArena submission-contact footer, in addition to WebArena, VisualWebArena, AndroidWorld, OSWorld-MCP and HUD contacts. Original and retained SHA-256 hashes and counts are disclosed in `webcomputer-publication-safety.json` and the fetch index. No score or evaluation-condition field is changed.

Remaining address-like values were individually classified as REAL benchmark task/example data and retrieved answers, source-code examples or a Git SSH reference. Both XLSX archives were also scanned internally and contained no email matches. No credential-like signed query values or attachment-access endpoints remain in newly published bodies.

Parent handles the strict aggregate build, PR, CI and publication gates.
