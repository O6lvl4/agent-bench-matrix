# Public-source refresh — 2026-10-13 (JST)

Base: `5d5926f2c6195a39898503041ee81c2817ef11ce`.

All 164 tables in nine categories received a fresh primary-source check: **8 changed, 155 verified unchanged, and 1 unavailable source preserved**. Result: **4,410 rows, 508 registered model IDs, 23 gaps**.

## Changes

- CyberGym's agent-focused table adds four systems: Ostorlab Neutron / DeepSeek-V4-Flash (97.08), AiPy Mini / DeepSeek-V4.1-Flash (92.83), HiAUDIT Agent / DeepSeek-V4-Pro (90.64), and TriLane / DeepSeek-V4-Flash (88.92). The model-focused table adds Basin (basin1-0912-pre-dpo) with Codex CLI (80.03). The existing OrcaCyber source link is updated. These are board-reported results, with existing scores preserved and ranks following the current board
- SWE-Marathon v1.1 adds Muse Wonder (52.5) and Muse Wonder Full (53.125), each under Muse Code, `max` reasoning, 20 tasks and eight trials per task. The board's two distinct canonical model strings are retained as separate identities; reasoning effort stays in configuration
- GAIA's native top-100 projection adds six mixed-model Shadow Harness systems and displaces six entries at its cutoff. The leading new system V8.01 reports 94.02 and October 12. Mixed-model systems retain empty model IDs and are excluded from single-model comparisons. Native score ordering and tied-entry order are preserved
- All four APEX tables now supply release dates for Sonnet 5.5, Haiku 5.5 and MiniMax-M3. All numeric cells are unchanged
- HUD's old OSWorld-Verified public URL now returns HTTP 404, replacing its previous sign-in redirect. Its availability gap is updated

Three registry entries are added: Basin's explicitly named pre-DPO checkpoint, Muse Wonder and Muse Wonder Full. Their exact open-weight availability is unverified, so all three retain `open_weights: null` and `weights_url: null`. Existing identities and classifications are unchanged. Meta's official product page confirms that Wonder and Full are distinct products; no vendor-claimed scores are imported.

AssistantBench still returns HTTP 503 on repeated public requests and its Space reports a runtime failure. Its existing 184 rows, source snapshot and retrieval date remain intact. The existing incomplete-refresh gap is retained; today's evidence records the repeated failure without claiming freshness for that table. Every unchanged table keeps its prior bytes and retrieval date.

## Coverage

| Category | Changed | Verified unchanged | Unavailable, preserved |
|---|---:|---:|---:|
| coding | 0 | 50 | 0 |
| terminal | 0 | 5 | 0 |
| tool-use | 4 | 28 | 0 |
| web | 0 | 22 | 1 |
| computer-use | 0 | 20 | 0 |
| research | 0 | 9 | 0 |
| security | 2 | 11 | 0 |
| long-horizon | 1 | 6 | 0 |
| general | 1 | 4 | 0 |

`summary.json` indexes every table and its category audit. Sakana's report remains v2; all 55 source numeric cells and 17 retained figures match. Its claim data and retrieval date remain unchanged, outside measured tables and fit.

## Evidence and validation

Category records retain current public source URLs, retrieval dates, original response hashes, precise deltas and disclosed retained excerpts/redactions. Sanitized archives preserve score-bearing evidence; incidental contact, credential, signed-access and unrelated application content is omitted. Fetched frontend code is treated only as inert source text. No login, paid evaluation or gated dataset access is used.

The fixed toolchain is Almide `e706ba8c4e32eb39983bd125cec1890d17094300` with Rust 1.94.0. Local fit tests, strict build, deterministic bundle equality and independent evidence review are recorded in `validation.json` and `independent-review.json`. Exact-head CI is required before merge; merge CI, independent Pages deployment and public bundle bytes are checked afterward. UI, build logic and workflows are unchanged.
