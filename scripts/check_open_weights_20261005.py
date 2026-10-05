"""Integrity check for the two evidence-backed 2026-10-05 classifications.

Run from the repository root after the normal pinned Almide strict build.
This dated audit intentionally compares against the pre-correction commit.
It does not change the builder, fit, or CI policy.
"""

import json
import pathlib
import re
import subprocess


ROOT = pathlib.Path(__file__).resolve().parents[1]
BASE = "efbe38ef8f8327c46cc84de82361e9bf373a7151"
EXPECTED = {
    "qwen3.8-27b": "https://huggingface.co/Qwen/Qwen3.8-27B",
    "qwen3.8-2.4t-a95b": "https://huggingface.co/Qwen/Qwen3.8-2.4T-A95B",
}


def load(path):
    return json.loads((ROOT / path).read_text())


def before(path):
    return json.loads(subprocess.check_output(
        ["git", "show", f"{BASE}:{path}"], cwd=ROOT, text=True
    ))


def normalize(name):
    return re.sub(r"[^a-z0-9]", "", name.lower())


def main():
    registry = load("data/models.json")
    old_registry = before("data/models.json")
    expected_registry = json.loads(json.dumps(old_registry))
    for model in expected_registry["models"]:
        if model["id"] in EXPECTED:
            assert model["open_weights"] is None
            assert model["weights_url"] is None
            model["open_weights"] = True
            model["weights_url"] = EXPECTED[model["id"]]
    assert registry == expected_registry, "Unexpected registry change"

    evidence = load("sources/model-registry/open-weights-2026-10-05.json")
    assert evidence["base_commit"] == BASE
    assert {entry["model_id"] for entry in evidence["models"]} == set(EXPECTED)
    for entry in evidence["models"]:
        assert entry["weights_url"] == EXPECTED[entry["model_id"]]
        assert entry["open_weights"] is True
        assert entry["private"] is False and entry["gated"] is False
        assert normalize(entry["model_id"]) == normalize(entry["repository"].split("/")[1])
        assert re.fullmatch(r"[0-9a-f]{40}", entry["revision"])
        assert entry["revision"] in entry["model_card"]["url"]
        assert entry["revision"] in entry["license"]["url"]
        assert entry["weight_index"]["referenced_shards"] == len(entry["weight_files"])
        assert entry["weight_files"]
        for shard in entry["weight_files"]:
            assert shard["path"].endswith(".safetensors") and shard["bytes"] > 0
            assert re.fullmatch(r"[0-9a-f]{64}", shard["lfs_sha256"])

    bundle = load("docs/data.json")
    old_bundle = before("docs/data.json")
    assert bundle["models"] == registry["models"]
    assert {k: v for k, v in bundle.items() if k != "models"} == {
        k: v for k, v in old_bundle.items() if k != "models"
    }, "Scores, claims, fit, counts, or dates changed"
    visible = {model["id"] for model in bundle["models"] if model["open_weights"] is True}
    assert set(EXPECTED) <= visible
    print("PASS: two exact checkpoint classifications; all scores/claims/fit unchanged")


if __name__ == "__main__":
    main()
