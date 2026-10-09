# Web and computer-use source refresh — 2026-10-09 JST

- All 43 existing tables (963 measured rows) have an explicit audit outcome
- 36 tables were fully compared with freshly fetched primary sources and are unchanged
- 7 BrowserGym tables remain incomplete after a network approval was cancelled: `browsergym-assistantbench`, `browsergym-miniwob`, `browsergym-webarena`, `browsergym-weblinx`, `browsergym-workarena-l1`, `browsergym-workarena-l2`, `browsergym-workarena-l3`
- The current BrowserGym manifest still identifies the same immutable commit and identical result membership. This supports revision continuity but is not represented as a fresh comparison of the missing result responses. `browsergym-visualwebarena` was fully acquired and compared
- All 43 table files, their original source files, and their retrieval dates remain byte-for-byte unchanged. There are no numeric changes, added rows, new tables or model proposals
- OSWorld JSON, renderer JavaScript and HTML are byte-identical to the October 7 evidence. All 51 source records retain release v2.0/v2.1, full/offline taskset, step budgets, and Foundation E2E GUI versus public-agent scope distinctions
- Nine existing web/computer gaps were rechecked using already acquired sources; no factual reason changed and none became mechanically extractable. Their existing files and dates are preserved
- No blocked request or alternate route was retried. The unrelated Computer Agent Arena meta-refresh destination was not visited

Evidence: `webcomputer.json` covers every table; `webcomputer-gaps.json` covers the nine existing gaps; `webcomputer-fetch-index.json` contains all 125 request outcomes. The 75 successful raw responses are losslessly retained in `webcomputer-responses.tar.gz` (about 1.01 MiB), with named archive members and per-response hashes in the index. SHA-256 values always refer to the original, uncompressed bytes.

Offline verification: `python sources/audits/2026-10-09/webcomputer-audit.py` reproduces the 36 unchanged / 7 incomplete outcomes without network access. The replay passed, all audit JSON parses, and a direct Git-baseline byte comparison confirmed that every table and original source file in this category is unchanged. Parent handles strict aggregate build and CI gates.
