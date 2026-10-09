# Public-source refresh — 2026-10-09 (JST)

Base commit: `af0325ce49fdeb5200bd9730b195cc0537c63f05`.

This is a **partial refresh**. All 164 tables in all nine categories were inventoried. Current primary-source responses verify 140 tables: 12 changed and 128 unchanged. The remaining 24 tables retain their prior good data and retrieval dates because source acquisition was interrupted before their complete evidence was available. No cancelled acquisition was retried or bypassed.

## Source-backed changes

- SWE-bench Live Java: one new Slingshot-v3.4.0 + GPT-5.6-Sol row, 67.5% (108/160), dated 2026-10-08
- SWE-bench Live Lite: TianxiCode + Deepseek-v4.1-Flash changes from 68.0% to 71.0% (213/300), dated 2026-10-08
- Terminal-Bench 4.0: eight added configurations, 27 → 35 rows, with model, agent, reasoning, cost, trial and verification fields retained
- APEX: three new configurations in each of the overall and three domain tables, 53 → 56 rows each. Two exact source-named model products are added to the registry with unknown public-weight status (`null`): MiMo V2.6 Flash RL and Claude Haiku 5.5. They are not merged into other model versions
- GAIA: current top-100 projection includes six new Shadow mixed-model system entries. The original mixed/ambiguous model description is retained and `model_ids: []` prevents attribution to one model in the matrix or fit
- SWE-bench Pro public/private and MCP-Atlas: native source rank changes are retained. Static frontend evidence shows that the rendered rank consumes those fields; the old Rank (UB) page explanation is disclosed as stale. This is not a browser execution claim
- Terminal-Bench Science 0.1: the successful, already-retained official GET response resolves five obsolete zero `n_trials` qualifiers to 210 (70 tasks × 3 trials); overall scores and costs are unchanged. Package, leaderboard identity and configuration scope are unchanged

The result contains **164 tables, 4,398 rows, 505 model IDs and 23 gaps**. Unchanged tables retain their exact bytes and retrieval dates. The previous run's incomplete-refresh gap is replaced by this run's current 24-table gap; historical audit records remain intact.

## Coverage

| Category | Changed | Verified unchanged | Incomplete, retained |
|---|---:|---:|---:|
| coding | 4 | 46 | 0 |
| terminal | 2 | 3 | 0 |
| tool-use | 5 | 13 | 14 |
| web | 0 | 16 | 7 |
| computer-use | 0 | 20 | 0 |
| research | 0 | 9 | 0 |
| security | 0 | 13 | 0 |
| long-horizon | 0 | 4 | 3 |
| general | 1 | 4 | 0 |

Incomplete numeric rechecks are 14 Tau tables (missing submission bodies), seven BrowserGym tables (missing immutable result bodies), both SWE-Marathon versions and Vending-Bench (missing current JavaScript modules). Current BrowserGym manifest membership matches the prior immutable commit, but this is not represented as a complete new numeric comparison.

Sakana Fugu vendor claims and six research/security-related existing gaps were not re-fetched after acquisition interruption. Their prior values, mappings, snapshots and retrieval dates are preserved. Claims are never mixed into measured data or fit. No benchmark was run or purchased.

## Evidence and reproduction

- `summary.json` is the all-table coverage index; category audits link URLs, response outcomes, hashes and preservation decisions
- Changed tables point to current snapshots; compact response archives retain successful source bytes with indexed SHA-256 hashes. Ephemeral signed redirect parameters are omitted; one response has only unrelated social-preview signatures removed, with original and retained hashes explicitly recorded in `publication-safety.json`
- Dated extraction recipes parse fetched content as data. They do not execute fetched JavaScript or Python
- Failed HTTP requests, denied/cancelled connections and not-attempted sources are distinguished from successful complete responses
- `coding-rank-review.json` and `tool-general-rank-review.json` retain Scale source-renderer evidence

## Validation boundary

Only data, provenance/audit evidence and the generated `docs/data.json` bundle are in scope. UI, builder, fit implementation, workflow pins, permissions, secrets and deployment settings are unchanged. Validation must use Almide `e706ba8c4e32eb39983bd125cec1890d17094300` built with Rust `1.94.0`, including fit tests, strict build, and exact equality of the committed bundle. Required CI is checked on the final PR head; Pages deployment and the public bundle are checked independently after merge.
