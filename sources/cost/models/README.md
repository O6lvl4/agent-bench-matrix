# Model evidence snapshot, 2026-10-25

The generated `../model-research.json` contains five selected, public, downloadable GGUF artifacts. Three Qwen profiles are eligible for an explicitly assumption-based capacity budget in the bounded MVP. Two gpt-oss profiles are preserved as research-only; this is not a claim that their runtimes are unsupported.

## Reproduce

1. `python fetch_models.py` refreshes public Hugging Face repository metadata, commit-pinned trees, source configs, model cards and licenses. No model weight files are downloaded.
2. `python verify_artifacts.py` obtains a HEAD response for each exact commit-pinned artifact and checks its `x-linked-size` against the tree API and LFS object size. It does not follow the signed CDN redirect or download the full weights.
3. `python extract_profiles.py` regenerates the deliverable from saved inputs. Runtime documentation snapshots were separately retrieved from the pinned llama.cpp revision in `llamacpp-commit.json`.
4. `validation.json` records independent checks of formulas and referenced snapshot hashes.

Each `*.meta.json` contains the source URL, retrieval timestamp and SHA-256 of the retrieved public body. Repository metadata identifies immutable commit revisions. For ggml-org conversions, `.src_sha` matches the official source model revision used for dimensions.

## Important interpretation

- Artifact bytes are exact storage bytes from public metadata, independently corroborated by a download redirect's `x-linked-size`. They are not measured resident memory.
- KV bytes are the unpadded data payload for keys plus values at 4096 total cached tokens, one concurrent sequence and f16 elements. Token batch size for prompt processing is a different parameter and is not benchmarked here.
- Qwen3-8B: 36 layers × 8 KV heads × 128 head dimension → 603,979,776 bytes (0.5625 GiB).
- Qwen3-32B: 64 × 8 × 128 → 1,073,741,824 bytes (1 GiB).
- Qwen3-Coder-30B-A3B: 48 × 4 × 128 → 402,653,184 bytes (0.375 GiB).
- gpt-oss uses alternating full/sliding attention. Its shown unpadded full-context KV ceiling ignores the sliding-window saving but is not a bound on total allocations. Native MXFP4 is documented by the runtime maintainer for CPU, CUDA, Metal and Vulkan; no matched hardware allocation was validated here.
- The Coder Q4_K_M artifact retains attention/embedding tensors at Q8_0. Neither generic `parameters × 0.5 bytes` nor MoE active parameter count is a defensible memory substitute.
- A 2 GiB runtime buffer and 10%/25% margin, if used by the UI, are explicit planning assumptions, not sourced requirements. No tokens/s, measured minimum memory, or guaranteed fit is established.
- The 4K scenario intentionally restricts context and does not establish adequate output budget or comparable quality for long reasoning tasks.

All actions were public reads and local writes. No external content was changed.
