# Web and computer-use source refresh — 2026-10-13 JST

- All 43 retained tables have explicit mechanical outcomes: 42 fully compared and unchanged; AssistantBench remains unavailable with its prior good data preserved. All 964 retained rows, table retrieval dates, model identities and source snapshots are byte-identical to baseline `5d5926f2c6195a39898503041ee81c2817ef11ce`.
- BrowserGym: fetched all 82 current result bodies at immutable revision `294ebe1dc36ba83c6916c64c64fb870af3dc8cee`, discovered from the freshly fetched public manifest. Every source record and field matches.
- AndroidWorld: all 48 main-board rows and every CSV cell match. Published ranks, model names/sizes, type, screen representation, scores, months, openness, trial count, pass@k, links and notes remain unchanged. Self-reported verification and mixed-model distinctions remain intact.
- OSWorld: all 51 official result records, renderer and HTML match; v2.0/v2.1, full/offline taskset, step budget, Foundation E2E GUI/public-agent, cost, verification and single-/mixed-model scopes remain separate. Older workbook sheets were compared cell by cell.
- Kaggle BrowseComp: all 42 scores, confidence intervals, identities, dates and links match. The complete current response is byte-identical to the October 11 response; ancillary releaseDate/updateTime metadata already present there does not cause a table rewrite.
- AssistantBench: live config returned HTTP 503 on both attempts; public Space metadata reports RUNTIME_ERROR. Fresh immutable source identifies the backing `Ori/results` dataset, whose public API returns 401. Prior 184 rows, snapshot and October 5 table retrieval date are preserved.
- All nine standing gaps were rechecked. HUD's former leaderboard URL now returns HTTP 404, replacing the October 11 sign-in redirect; its homepage's visible text and links are unchanged. Only that gap's description and retrieval date changed. The other eight gap files remain byte-identical; no gap yielded a current public result table.
- No table, source snapshot, model registry, UI, build, workflow or application-code changes were made by this scoped refresh. No new model proposals.

## Acquisition and verification

133 read-only public requests covered 129 unique canonical URLs. The 122 successful response bodies are in `webcomputer-responses.tar.gz`; every stored body has a verified SHA-256 in `webcomputer-fetch-index.json`. The four requests beyond unique URLs are second attempts for AssistantBench and ST-WebAgentBench configs (both still 503), and successful retries of two Google CSV requests that initially timed out.

`webcomputer.json` records all 43 table outcomes and methods; `webcomputer-row-deltas.json` records explicit zero row deltas for each table. `webcomputer-gaps.json` covers all nine gaps. `webcomputer-verification.json` records byte-preservation checks and an offline replay that hashes all 122 archived bodies and reproduces all 43 outcomes. Temporary execution helpers remain outside the repository.

## Publication safety

Cookies, authentication headers and transient redirect destinations are excluded. Eight archived bodies omit 14 nonessential contact-email occurrences and two attachment/access URLs (AndroidWorld Aliyun and one OneDrive authkey-bearing link). Another 150 Google redirect links retain only their canonical public destinations, omitting tracking/signing query parameters. Original and stored hashes and redaction counts are disclosed in `webcomputer-publication-safety.json`; scores and evaluation conditions are unchanged.

Remaining address-like values are classified as REAL benchmark task/example data and retrieved answers, source-code examples, or a Git SSH reference. Both workbook ZIP/XML contents contain no email matches. No credential-like signed queries or attachment-access endpoints remain in newly archived bodies. A public Google Sites `authuser=0` account-selector parameter is explicitly classified as noncredential metadata.

Aggregate build, CI and publication checks are handled separately.
