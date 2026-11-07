#!/usr/bin/env python3
"""Refresh the official AssistantBench test board without disguising an outage.

Only public GET requests are made. The Space health is checked before /config;
failed or changed-scope sources never replace the reviewed rows or snapshot.
Run this before the normal strict Almide build. No scheduler or publishing is
installed here; existing refresh jobs can call the same command or collector.
"""
import argparse
import collections
import copy
import datetime as dt
import hashlib
import json
import math
from pathlib import Path
import re
import sys
import urllib.error
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
SPACE_URL = "https://huggingface.co/api/spaces/AssistantBench/leaderboard"
CONFIG_URL = "https://assistantbench-leaderboard.hf.space/config"
SPACE_ID = "AssistantBench/leaderboard"
# Reviewed source: credential separation only; still Ori/results, default/test,
# Accuracy (%), 181 tasks. A new revision requires review before accepting data.
REVIEWED_REVISION = "6309f9b4d23c6ecdffb3964188574d092093b66e"
HEADERS = ["Model Name", "Accuracy", "Answer rate", "Precision", "EM",
           "Accuracy (easy)", "Accuracy (medium)", "Accuracy (hard)",
           "Base Model", "Organization"]
EXTRA_KEYS = ["answer_rate", "precision", "em", "accuracy_easy",
              "accuracy_medium", "accuracy_hard"]
TABLE_PATH = "data/tables/assistantbench.json"
MAX_RESPONSE = 8 * 1024 * 1024


class ReviewRequired(ValueError):
    """Fetched evidence needs review, rather than silently changing scope."""


def json_bytes(value):
    return (json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n").encode()


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_bytes(json_bytes(value))
    temporary.replace(path)


def fetch_url(url):
    """Return HTTP evidence and bytes, without cookies or authentication."""
    record = {"url": url, "method": "GET"}
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "AgentBenchMatrix/1.0"})
        with urllib.request.urlopen(req, timeout=45) as response:
            body = response.read(MAX_RESPONSE + 1)
            if len(body) > MAX_RESPONSE:
                return dict(record, error="Response exceeded 8 MiB safety limit"), b""
            record.update(status=response.status, final_url=response.url)
    except urllib.error.HTTPError as error:
        body = error.read(MAX_RESPONSE)
        record.update(status=error.code, error=str(error))
    except (OSError, TimeoutError) as error:
        return dict(record, error=str(error)), b""
    record.update(bytes=len(body), sha256=hashlib.sha256(body).hexdigest())
    return record, body


def collect_to_cache(cache, fetcher=fetch_url, now=None):
    """Health-gated collection, compatible with the web collector's index."""
    cache = Path(cache)
    cache.mkdir(parents=True, exist_ok=True)
    records = {}

    def get(url, filename):
        record, body = fetcher(url)
        if body:
            path = cache / filename
            path.write_bytes(body)
            record = dict(record, path=str(path))
        records[url] = record
        return record, body

    health, body = get(SPACE_URL, "assistantbench-space.json")
    reason = "公式Spaceの状態を取得できないため、現在の表を確認できません。"
    status, stage = "unavailable", None
    if health.get("status") == 200:
        try:
            meta = json.loads(body)
            candidate_stage = meta["runtime"]["stage"]
            if not isinstance(candidate_stage, str) or not candidate_stage:
                raise ReviewRequired("公式Spaceの稼働状態の形式が変わっています。")
            stage = candidate_stage
            if meta.get("id") != SPACE_ID or meta.get("host") != CONFIG_URL.removesuffix("/config"):
                raise ReviewRequired("公式SpaceのIDまたはホストが変わっています。")
            if not isinstance(stage, str) or not stage:
                raise ReviewRequired("公式Spaceの稼働状態の形式が変わっています。")
            if stage not in {"RUNNING", "SLEEPING"}:
                reason = f"公式Spaceが {stage} のため、保存データを表示しています。"
            elif meta.get("sha") != REVIEWED_REVISION:
                raise ReviewRequired("公式Spaceの実装が変更されています。同じtest集合・採点条件か確認が必要です。")
            else:
                # A sleeping Space may wake on an ordinary public page read.
                config, _ = get(CONFIG_URL, "assistantbench-config.json")
                if config.get("status") == 200:
                    status, reason = "collected", "公式test表を取得しました。全行を検証します。"
                else:
                    reason = "公式test表を取得できないため、保存データを表示しています。"
        except ReviewRequired as error:
            status, reason = "review_required", str(error)
        except (ValueError, KeyError, TypeError) as error:
            status, reason = "review_required", "公式Spaceの状態データを検証できません: " + str(error)
    if CONFIG_URL not in records:
        records[CONFIG_URL] = {"url": CONFIG_URL, "skipped": True, "reason": reason}
    write_json(cache / "assistantbench-collection.json", {
        "status": status, "runtime_stage": stage, "reason_ja": reason,
        "collected_at": (now or dt.datetime.now(dt.timezone.utc)).isoformat(), "sources": records,
    })
    return records


def numeric(value):
    if isinstance(value, str) and re.fullmatch(r"\*\*\d+(?:\.\d+)?\*\*", value):
        value = float(value[2:-2])
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or not 0 <= value <= 100:
        raise ReviewRequired("正答率・回答率などに0〜100の有限な数値でない値があります。")
    return value


def title_and_url(value):
    if not isinstance(value, str) or not value:
        raise ReviewRequired("モデル名が空か文字列ではありません。")
    match = re.fullmatch(r"\[(.*)\]\((.*)\)", value)
    if not match or not match[1]:
        raise ReviewRequired("モデル名・URLの表示形式が変わっています。")
    title, url = match.groups()
    if url and not re.match(r"^https?://", url):
        raise ReviewRequired("モデルのリンクがHTTP(S)ではありません。")
    return title, url or None


def validate_board(board):
    if not isinstance(board, dict) or board.get("headers") != HEADERS:
        raise ReviewRequired("test表の列構造が変わっています。")
    rows = board.get("data")
    if not isinstance(rows, list) or not rows:
        raise ReviewRequired("test表が空です。")
    identities = set()
    for row in rows:
        if not isinstance(row, list) or len(row) != len(HEADERS):
            raise ReviewRequired("test表の行の列数が一致しません。")
        title_and_url(row[0])
        for value in row[1:8]:
            numeric(value)
        if not isinstance(row[8], str) or not isinstance(row[9], str):
            raise ReviewRequired("ベースモデルまたは組織の形式が変わっています。")
        identity = (row[0], row[8], row[9])
        if identity in identities:
            raise ReviewRequired("同じ提出情報の重複行があります。")
        identities.add(identity)
    if any(numeric(a[1]) < numeric(b[1]) for a, b in zip(rows, rows[1:])):
        raise ReviewRequired("公式test表の正答率順を確認できません。")
    return rows


def extract_board(config):
    if not isinstance(config, dict) or not isinstance(config.get("components"), list):
        raise ReviewRequired("Gradio configの形式が変わっています。")
    frames = []
    for component in config["components"]:
        if isinstance(component, dict) and component.get("type") == "dataframe":
            props = component.get("props")
            if not isinstance(props, dict):
                raise ReviewRequired("公式test表のプロパティ形式が変わっています。")
            frames.append(props.get("value"))
    if len(frames) != 1:
        raise ReviewRequired("公式test表を一意に特定できません。")
    validate_board(frames[0])
    return frames[0]


def normalize(board, previous_board, table, registry):
    """Use reviewed model mappings, never infer new model identities."""
    current = validate_board(board)
    previous = validate_board(previous_board)
    if len(previous) != len(table["rows"]):
        raise ReviewRequired("保存snapshotと正規化済み行の数が一致しません。")
    old_ids = {(r[0], r[8], r[9]) for r in previous}
    new_ids = {(r[0], r[8], r[9]) for r in current}
    if not old_ids <= new_ids:
        raise ReviewRequired("既存投稿が削除または改名されています。集合の変更として確認が必要です。")
    mappings = collections.defaultdict(set)
    reviewed = {}
    for raw, row in zip(previous, table["rows"]):
        title, url = title_and_url(raw[0])
        expected = [row["score"], *[row["score_extra"][key] for key in EXTRA_KEYS]]
        if (title, url, raw[9] or None) != (row["system"], row["row_url"], row["org"]) or [numeric(x) for x in raw[1:8]] != expected:
            raise ReviewRequired("保存snapshotと正規化済み行の対応を確認できません。")
        mapping = {key: row[key] for key in ("model_raw", "model_ids", "model_config")}
        mappings[raw[8]].add(json.dumps(mapping, sort_keys=True))
        reviewed[(raw[0], raw[8], raw[9])] = row
    out = []
    for rank, raw in enumerate(current, 1):
        identity = (raw[0], raw[8], raw[9])
        if identity in reviewed:
            row = copy.deepcopy(reviewed[identity])
        else:
            if len(mappings[raw[8]]) != 1:
                raise ReviewRequired("新しいベースモデル表記の正規化が必要です: " + raw[8])
            mapping = json.loads(next(iter(mappings[raw[8]])))
            title, url = title_and_url(raw[0])
            row = dict(system=title, row_url=url, agent=None, date=None,
                       verified=None, open_source=None, org=raw[9] or None, **mapping)
        if any(model_id not in registry for model_id in row["model_ids"]):
            raise ReviewRequired("モデルIDが登録簿にありません。")
        row.update(rank=rank, score=numeric(raw[1]),
                   score_extra=dict(zip(EXTRA_KEYS, map(numeric, raw[2:8]))))
        out.append(row)
    return out


def refresh(root=ROOT, cache=None, fetcher=fetch_url, now=None):
    root = Path(root)
    now = now or dt.datetime.now(dt.timezone.utc)
    checked = now.date().isoformat()
    audit_dir = root / "sources/assistantbench/checks" / now.strftime("%Y-%m-%dT%H%M%S%fZ")
    audit_dir.mkdir(parents=True, exist_ok=False)
    own_cache = cache is None
    if own_cache:
        cache = audit_dir
        collect_to_cache(cache, fetcher, now)
    cache = Path(cache)
    collection = json.loads((cache / "assistantbench-collection.json").read_text())
    if collection["collected_at"][:10] != checked:
        raise ValueError("取得キャッシュが本日のものではありません。再取得してください。")
    table_path = root / TABLE_PATH
    table = json.loads(table_path.read_text())
    before = copy.deepcopy(table)
    status, reason = collection["status"], collection["reason_ja"]
    audit_path = str((audit_dir / "audit.json").relative_to(root))
    sources = []
    for record in collection["sources"].values():
        record = dict(record)
        if record.get("path"):
            source = Path(record.pop("path"))
            body = source.read_bytes()
            if hashlib.sha256(body).hexdigest() != record.get("sha256"):
                raise ValueError("Cached source digest mismatch")
            target = audit_dir / source.name
            if source.resolve() != target.resolve():
                target.write_bytes(body)
            record["snapshot"] = str(target.relative_to(root))
        sources.append(record)
    board, rows = None, None
    if status == "collected":
        try:
            if collection["collected_at"][:10] != checked:
                raise ReviewRequired("取得キャッシュが本日のものではありません。再取得が必要です。")
            if (table.get("id"), table.get("tasks"), table.get("metric"), table.get("unit")) != ("assistantbench", 181, "Accuracy", "%"):
                raise ReviewRequired("保存表の比較条件が公式test表と一致しません。")
            config_record = collection["sources"][CONFIG_URL]
            board = extract_board(json.loads(Path(config_record["path"]).read_bytes()))
            previous_board = json.loads((root / table["snapshot"]).read_bytes())
            registry = {m["id"] for m in json.loads((root / "data/models.json").read_text())["models"]}
            rows = normalize(board, previous_board, table, registry)
            status = "current"
            reason = "公式test表の全行を再取得し、同じ比較条件で確認しました。"
        except (ReviewRequired, ValueError, KeyError, TypeError) as error:
            status, reason = "review_required", str(error)
    changed = status == "current" and rows != before["rows"]
    if changed:
        table["rows"] = rows
        table["retrieved"] = checked
        # Keep the old snapshot; a changed board receives a new immutable path.
        table["snapshot"] = str((audit_dir / "board_test.json").relative_to(root))
        write_json(root / table["snapshot"], board)
    previous_success = before.get("refresh", {}).get("last_successful_check", before["retrieved"])
    success_evidence = None
    bootstrap = root / "sources/audits/2026-10-09/webcomputer.json"
    if "refresh" not in before and bootstrap.exists():
        historical = json.loads(bootstrap.read_text())
        for entry in historical.get("tables", []):
            if entry.get("id") == "assistantbench" and entry.get("status") == "unchanged" and entry.get("rows") == len(before["rows"]) and entry.get("rows_changed") is False:
                previous_success = max(previous_success, entry["retrieved"])
                success_evidence = str(bootstrap.relative_to(root))
    table["refresh"] = dict(status=status, checked=checked,
        last_successful_check=checked if status == "current" else previous_success,
        runtime_stage=collection["runtime_stage"], reason_ja=reason, audit=audit_path)
    report = dict(id="assistantbench", checked=checked, checked_at=now.isoformat(),
        status="changed" if changed else ("unchanged" if status == "current" else status),
        refresh=table["refresh"], old_rows=len(before["rows"]), rows=len(table["rows"]),
        previous_data_retrieved=before["retrieved"], data_retrieved_after=table["retrieved"],
        source_snapshot=table["snapshot"], sources=sources,
        previous_success_evidence=success_evidence,
        scope={"split": "test", "tasks": 181, "metric": "Accuracy", "unit": "%",
               "reviewed_space_revision": REVIEWED_REVISION})
    write_json(root / audit_path, report)
    write_json(table_path, table)
    if own_cache:
        (cache / "assistantbench-collection.json").unlink()
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cache", type=Path, help="Use today's health-gated web collector cache")
    args = parser.parse_args()
    report = refresh(cache=args.cache)
    print(json.dumps(report["refresh"], ensure_ascii=False, indent=2))
    # An upstream outage is an accurately recorded result, not a data failure.
    # A parser/scope change needs human review and must stop automated refreshes.
    return 2 if report["status"] == "review_required" else 0


if __name__ == "__main__":
    sys.exit(main())
