#!/usr/bin/env python3
"""Offline, reproducible Oct 7 OSWorld scope extraction and AndroidWorld review.

Initial run: python scripts/refresh_osworld_scope_20261007.py --cache /tmp/abm-web-oct7
Reproduce:   python scripts/refresh_osworld_scope_20261007.py --check

Uses only fetched bytes, never executes upstream JavaScript, performs no network
requests, and does not build the UI or edit the model registry. The immutable
baseline b02f0c0 retains previously reviewed model normalization. Without --cache,
the checked-in source evidence is sufficient to reproduce every output.
"""

import argparse
import copy
import csv
import functools
import hashlib
import io
import json
import math
import pathlib
import re
import subprocess

ROOT = pathlib.Path(__file__).resolve().parents[1]
BASE = "b02f0c0"
DATE = "2026-10-07"
JSON_URL = "https://osworld-v2.xlang.ai/static/data/leaderboard/official-results.json"
JS_URL = "https://osworld-v2.xlang.ai/static/js/leaderboard.js?v=leaderboard-v21-v1"
HOME_URL = "https://osworld-v2.xlang.ai/"
AGENT_ID = "osworld-2-1-public-agents-full-500steps"
EVIDENCE = pathlib.Path("sources") / AGENT_ID
SOURCE_FILES = {
    JSON_URL: EVIDENCE / "official-results.json",
    JS_URL: EVIDENCE / "leaderboard.js",
    HOME_URL: EVIDENCE / "display-page.html",
}
EXISTING_IDS = [
    "osworld-2-1-full-500steps", "osworld-2-1-offline-500steps",
    "osworld-2-full-150steps", "osworld-2-full-300steps",
    "osworld-2-full-500steps", "osworld-2-offline-500steps",
]


def baseline(path):
    return json.loads(subprocess.check_output(["git", "show", BASE + ":" + str(path)], cwd=ROOT))


def serialize(value):
    return (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cache", type=pathlib.Path)
    parser.add_argument("--check", action="store_true", help="compare outputs without writing")
    args = parser.parse_args()
    index = json.loads((args.cache / "index.json").read_text()) if args.cache else None
    prior_manifest = None if index else json.loads((ROOT / EVIDENCE / "source-manifest-2026-10-07.json").read_text())
    outputs = []

    def emit(path, value):
        raw = value if isinstance(value, bytes) else serialize(value)
        path = ROOT / path
        if args.check:
            assert path.read_bytes() == raw, "Reproduction mismatch: " + str(path)
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(raw)
        outputs.append(str(path.relative_to(ROOT)))

    raw_sources = {}
    sources = []
    for url, path in SOURCE_FILES.items():
        if index:
            entry = index[url]
            assert entry["status"] == 200, (url, entry)
            raw = pathlib.Path(entry["path"]).read_bytes()
            metadata = {
                "url": url, "response_url": entry.get("url", url),
                "http_status": entry["status"], "bytes": len(raw),
                "sha256": hashlib.sha256(raw).hexdigest(), "snapshot": str(path),
                "response_date": entry.get("headers", {}).get("Date"),
            }
        else:
            raw = (ROOT / path).read_bytes()
            metadata = next(x for x in prior_manifest["sources"] if x["url"] == url)
            assert metadata["sha256"] == hashlib.sha256(raw).hexdigest()
            assert metadata["bytes"] == len(raw)
        raw_sources[url] = raw
        sources.append(metadata)
        emit(path, raw)
    emit(EVIDENCE / "source-manifest-2026-10-07.json", {"retrieved": DATE, "sources": sources})
    source = json.loads(raw_sources[JSON_URL])
    rendering = raw_sources[JS_URL].decode()
    rendering_assertions = [
        'modelScope: "e2e"',
        'state.modelScope === "all" || (row.modelType || "e2e") === "e2e"',
        'Foundation E2E GUI', 'data-model-scope="all"',
        'row.costPerTaskUsd.toFixed(2)', 'Offline set: 82 tasks',
    ]
    for assertion in rendering_assertions:
        assert assertion in rendering, assertion

    e2e = [x for x in source["results"] if x.get("modelType", "e2e") == "e2e"]
    agents = [x for x in source["results"] if x.get("modelType") == "agent"]
    assert len(e2e) + len(agents) == len(source["results"]), "Unreviewed model type"
    old_source = baseline("sources/osworld-2-1-full-500steps/official-results.json")
    assert [{k: v for k, v in x.items() if k != "modelType"} for x in e2e] == old_source["results"]
    assert all(x.get("official") is True for x in e2e)

    def release(x):
        return x.get("releaseVersion") or x.get("taskVersion") or source.get("defaultResultReleaseVersion") or source["taskVersion"]

    def scope(x):
        return x.get("datasetScope") or x.get("scope") or source.get("defaultResultDatasetScope", "full")

    def config(x):
        return f"reasoning={x['reasoning']}; tool_setting={x['toolSetting']}; step_budget={x['stepBudget']}; release={release(x)}"

    def sort_key(x):
        # Current renderer: binary desc, partial desc, cost asc, model asc.
        # Release-desc final tie is handled below. All current labels are ASCII.
        return (-x["binaryAccuracy"], -x["partialScore"], x.get("estimatedCostUsd") if x.get("estimatedCostUsd") is not None else math.inf, x["model"])

    def compare(a, b):
        ka, kb = sort_key(a), sort_key(b)
        if ka != kb:
            return -1 if ka < kb else 1
        return (release(a) < release(b)) - (release(a) > release(b))

    audits = []
    total_e2e = 0
    for table_id in EXISTING_IDS:
        old = baseline("data/tables/" + table_id + ".json")
        table = copy.deepcopy(old)
        dataset_scope = "offline" if "-offline-" in table_id else "full"
        steps = int(re.search(r"-(\d+)steps$", table_id)[1])
        v21 = table_id.startswith("osworld-2-1-")
        selected = sorted([x for x in e2e if scope(x) == dataset_scope and x["stepBudget"] == steps and (release(x) == "v2.1") == v21], key=functools.cmp_to_key(compare))
        assert len(selected) == len(old["rows"])
        normalized = []
        for rank, x in enumerate(selected, 1):
            matches = [r for r in old["rows"] if r["system"] == x["model"] and r["model_config"] == config(x)]
            assert len(matches) == 1, x
            row = copy.deepcopy(matches[0])
            row.update(rank=rank, score=x["binaryAccuracy"], verified=x["official"])
            row["score_extra"] = {"partial_score": x["partialScore"], "step_budget": x["stepBudget"]}
            for source_key, output_key in [("outputTokensPerTask", "output_tokens_per_task"), ("estimatedCostUsd", "estimated_cost_usd_total")]:
                if x.get(source_key) is not None:
                    row["score_extra"][output_key] = x[source_key]
            normalized.append(row)
        assert normalized == old["rows"], "Unexpected score, metric, identity, or rank change"
        table["rows"] = normalized
        table["name"] = table["name"].replace("(release v2.1, ", "(release v2.1, Foundation E2E GUI, ") if v21 else table["name"].replace("(", "(Foundation E2E GUI, ", 1)
        table["harness_ja"] = "公式ボードの Foundation E2E GUI タブに対応する modelType=e2e・official=true の行だけ。OSWorld 2.0 チームの公式実行。推論量・ツール設定は行ごとに異なる。All タブにのみ載る外部エージェントの結果は含めない。"
        table["notes_ja"] = re.sub(r"updatedAt は [\d-]+", "updatedAt は " + source["updatedAt"], table["notes_ja"])
        table["notes_ja"] += " 2026-10-07取得時点で従来の全50行に modelType=e2e が明示されたが、数値と順位は不変。外部エージェント行は All タブ由来の別表に保存。"
        table["retrieved"] = DATE
        table["fetched"] = [JSON_URL, JS_URL]
        emit(table["snapshot"], raw_sources[JSON_URL])
        emit(pathlib.Path(table["snapshot"]).parent / "leaderboard.js", raw_sources[JS_URL])
        emit("data/tables/" + table_id + ".json", table)
        audit = {
            "id": table_id, "retrieved": DATE, "status": "changed",
            "change_type": "source-schema-and-scope-clarification", "rows_changed": False,
            "old_rows": len(old["rows"]), "rows": len(normalized),
            "method": "Completed standalone extraction: explicit modelType=e2e and official=true; dataset scope, step budget and release boundary preserved. All old source fields match after removing newly explicit modelType; scores, extra metrics, ranks and identities reproduced exactly. Updated source date and scope labels only.",
            "sources": sources[:2],
        }
        emit("sources/" + table_id + "/audit-2026-10-07.json", audit)
        audits.append(audit)
        total_e2e += len(selected)
    assert total_e2e == len(e2e)

    # A separately labeled subset of the actual All tab, never an invented
    # official E2E result or an additional Claude Opus 5 matrix observation.
    assert agents and all(release(x) == "v2.1" and scope(x) == "full" and x["stepBudget"] == 500 for x in agents)
    all_rows = sorted([x for x in source["results"] if release(x) == "v2.1" and scope(x) == "full" and x["stepBudget"] == 500], key=functools.cmp_to_key(compare))
    agent_rows = []
    for x in agents:
        assert "official" not in x and "agentName" not in x
        agent_rows.append({
            "rank": all_rows.index(x) + 1, "system": x["model"], "agent": x.get("agentName"),
            "model_raw": [x["basePlannerModel"]] if x.get("basePlannerModel") else [],
            "model_ids": [],
            "model_config": "model_type=" + x["modelType"] + "; model_scope=all; base_planner_model=" + x.get("basePlannerModel", "") + "; " + config(x) + "; dataset_scope=" + scope(x),
            "score": x["binaryAccuracy"],
            "score_extra": {"partial_score": x["partialScore"], "step_budget": x["stepBudget"], "task_count": x["taskCount"], "cost_per_task_usd": x["costPerTaskUsd"], "estimated_cost_usd_total": x["estimatedCostUsd"]},
            "date": None, "verified": None, "open_source": None,
            "org": x.get("company"), "row_url": x.get("trajectoryUrl"),
        })
    table = baseline("data/tables/osworld-2-1-full-500steps.json")
    table.update(
        id=AGENT_ID, name="OSWorld 2.0 (release v2.1, public agents from All tab, full set, 500 steps)",
        tasks=agents[0]["taskCount"], tasks_note="公開JSONの taskCount。All タブのうち modelType=agent の行だけを抽出した別表。",
        harness_ja="公式サイトの All タブに掲載された外部エージェントの結果。modelType=agent の行のみ。Foundation E2E GUI の公式実行条件とは別扱いで、掲載行には official 検証フラグが無いため verified=null。",
        fetched=[JSON_URL, JS_URL, HOME_URL], retrieved=DATE, newest_row_date=None,
        snapshot=str(SOURCE_FILES[JSON_URL]), rows=agent_rows,
        notes_ja="releaseVersion=v2.1・datasetScope=full・stepBudget=500 に限定。専用の agent タブがあるわけではなく、All タブからエージェント行だけを分離している。rank は同条件の All タブを Binary accuracy 降順にした順位を保持する。basePlannerModel はプランナーの開示でありシステム全体の単一モデル構成を保証しないため、model_raw に原文を保持し model_ids=[] としてモデル別マトリクス・推定へ入れない。行の日付・検証マーク・オープン性は非掲載。toolSetting は空文字のまま、standard と推定しない。costPerTaskUsd と estimatedCostUsd を別々に保持。公開JSONの updatedAt は " + source["updatedAt"] + "。再現用リンクは原データに保持。",
    )
    assert all(x["taskCount"] == table["tasks"] for x in agents)
    emit("data/tables/" + AGENT_ID + ".json", table)
    audit = {
        "id": AGENT_ID, "retrieved": DATE, "status": "new", "old_rows": 0,
        "rows": len(agent_rows), "rows_changed": True,
        "method": "Mechanically extracted modelType=agent from the public All tab, v2.1/full/500-step conditions. Preserved All-tab rank, source taskCount, binary/partial scores and both cost fields. No official flag is inferred; planner-only disclosure is not attributed to a single normalized model.",
        "sources": sources,
    }
    emit(EVIDENCE / "audit-2026-10-07.json", audit)
    audits.append(audit)
    evidence = {
        "retrieved": DATE, "baseline_commit": BASE,
        "previous_updated_at": old_source["updatedAt"], "source_updated_at": source["updatedAt"],
        "e2e_source_rows": len(e2e), "agent_source_rows": len(agents),
        "e2e_rows_identical_except_new_model_type": True,
        "renderer_checks": rendering_assertions,
        "agent_source_rows_exact": agents,
        "all_tab_v21_full_500_order": [{"rank": i, "model": x["model"], "reasoning": x["reasoning"], "binaryAccuracy": x["binaryAccuracy"], "modelType": x["modelType"]} for i, x in enumerate(all_rows, 1)],
        "decision": "Preserve all six official Foundation E2E GUI tables; separately expose only public agent rows from All. Do not duplicate E2E observations into another matrix column. Keep model_ids empty because basePlannerModel identifies only the planner, and leave absent verification/date/open-source metadata null.",
        "extractor": "scripts/refresh_osworld_scope_20261007.py",
    }
    emit(EVIDENCE / "review-2026-10-07.json", evidence)

    # Independent comparison against the freshly fetched AndroidWorld CSV.
    android = json.loads((ROOT / "data/tables/androidworld.json").read_text())
    android_url = android["fetched"][0]
    if index:
        assert index[android_url]["status"] == 200
        android_raw = pathlib.Path(index[android_url]["path"]).read_bytes()
    else:
        android_raw = (ROOT / android["snapshot"]).read_bytes()
    assert android_raw == (ROOT / android["snapshot"]).read_bytes()
    csv_rows = list(csv.reader(io.StringIO(android_raw.decode("utf-8-sig"))))
    assert "No independent verification" in csv_rows[0][0]
    selected = [x for x in csv_rows[2:] if len(x) >= 13 and x[2] and (x[8] or x[10]) and x[2] != "Human" and x[6] != "Human" and re.match(r"^\d{1,2}/\d{4}$", x[1])]
    assert len(selected) == len(android["rows"])
    for x, row in zip(selected, android["rows"]):
        assert row["system"] == x[2].strip()
        assert row["rank"] == (int(x[0]) if x[0].isdigit() else None)
        assert row["score"] == (float(x[8]) if x[8] else None)
        month, year = x[1].split("/")
        assert row["date"] == f"{year}-{int(month):02}"
        assert row["verified"] is False and row["open_source"] == (x[4] == "✔")
        if x[12].strip():
            assert row["score_extra"]["note"] == x[12].strip()
        if x[9].strip():
            assert row["score_extra"]["trials"] == float(x[9])
    agi_source = next(x for x in selected if x[2] == "AGI-0")
    agi = next(x for x in android["rows"] if x["system"] == "AGI-0")
    old_agi = next(x for x in baseline("data/tables/androidworld.json")["rows"] if x["system"] == "AGI-0")
    assert "on AndroidWorld tasks" in agi["score_extra"]["note"]
    assert agi["model_ids"] == []
    emit("sources/androidworld/independent-review-2026-10-07.json", {
        "retrieved": DATE, "source": android_url, "sha256": hashlib.sha256(android_raw).hexdigest(),
        "rows_checked": len(selected), "status": "passed",
        "checks": "All main-board row names, ranks, pass@1 values, release months, self-report flags, open flags, notes and trial counts match the fresh CSV; existing table unchanged by this review.",
        "agi_0": {"previous_score": old_agi["score"], "current_score": agi["score"], "source_release_month": agi_source[1], "normalized_row_date": agi["date"], "source_note_exact": agi_source[12], "model_ids": agi["model_ids"], "verified": agi["verified"]},
        "interpretation": "The September 2026 note revises the score and explicitly discloses Qwen3.5-27B training on AndroidWorld tasks. It does not replace the row's separately published Release Date (10/2025) or establish independent verification, held-out generalization, or a single-model agent identity.",
        "extractor": "scripts/refresh_osworld_scope_20261007.py",
    })

    if args.cache and not args.check:
        audit_path = args.cache / "audit.json"
        combined = json.loads(audit_path.read_text())
        replacements = {x["id"]: x for x in audits}
        combined["tables"] = [replacements.pop(x["id"], x) for x in combined["tables"]]
        combined["tables"].extend(replacements.values())
        combined["parser_errors"] = [x for x in combined.get("parser_errors", []) if x.get("id") not in EXISTING_IDS]
        audit_path.write_bytes(serialize(combined))
    print(json.dumps({"mode": "checked" if args.check else "extracted", "e2e_rows_unchanged": total_e2e, "new_public_agent_rows": len(agent_rows), "androidworld_rows_reviewed": len(selected), "outputs": outputs}, indent=2))


if __name__ == "__main__":
    main()
