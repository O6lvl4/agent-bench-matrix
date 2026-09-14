# データの形

数字はすべて、各リーダーボードが公開しているデータを取得し、機械的に取り出したものです。
記憶や要約から書いた数字は入れません。取れなかった表は、取れなかったこととして
`data/gaps/` に残します。

## 表: `data/tables/<id>.json`

1ファイル = 1つのリーダーボードの表。同じベンチでも載っている場所(ボード)が違えば別の表です
(例: GAIA の公式ボードと HAL の GAIA は、走らせ方が違うので別の表)。

```json
{
  "id": "swe-bench-verified",
  "family": "swe-bench",
  "name": "SWE-bench Verified",
  "board": "swebench.com",
  "category": "coding",
  "measures_ja": "実在の GitHub issue に対し、隠されたテストを通すパッチを作れるか。",
  "tasks": 500,
  "tasks_note": null,
  "metric": "% Resolved",
  "unit": "%",
  "higher_is_better": true,
  "harness_ja": "提出者がそれぞれ自前の足場で走らせる。",
  "source": "https://www.swebench.com/",
  "fetched": ["https://raw.githubusercontent.com/..."],
  "retrieved": "2026-09-14",
  "newest_row_date": "2026-08-30",
  "snapshot": "sources/swe-bench-verified/leaderboards.json",
  "paper": "https://arxiv.org/abs/...",
  "repo": "https://github.com/...",
  "notes_ja": "飽和に近い。",
  "rows": [
    {
      "rank": 1,
      "system": "リーダーボード上の表記そのまま",
      "agent": "OpenHands",
      "model_raw": ["claude-opus-4-5-20251101"],
      "model_ids": ["claude-opus-4.5"],
      "model_config": "high reasoning",
      "score": 74.2,
      "score_extra": { "cost_usd": 12.3 },
      "date": "2026-08-30",
      "verified": true,
      "open_source": null,
      "org": "All Hands AI",
      "row_url": "https://..."
    }
  ]
}
```

| フィールド | 意味 |
|---|---|
| `category` | `coding` / `terminal` / `tool-use` / `web` / `computer-use` / `research` / `security` / `long-horizon` / `general` のいずれか |
| `unit` | `%` / `score` / `minutes` / `usd` / `elo` など。`score` の単位 |
| `harness_ja` | 行がどう走らされたか(提出者任せ / 固定の足場 / 公式が再実行 など)。列の数字を比べてよいかはここで決まる |
| `fetched` | 実際に取得したURL(機械可読なデータがあればそれ) |
| `snapshot` | 取得した中身のうち、行の出所になった部分の保存先 |
| `rows[].system` | ボードに書かれた名前をそのまま |
| `rows[].agent` | 足場(scaffold)の名前。分からない・非開示なら `null` |
| `rows[].model_raw` | ボードに書かれたモデル名をそのまま。非開示なら `[]` |
| `rows[].model_ids` | 正規化したモデルID(下の規則)。決められなければ `[]` |
| `rows[].model_config` | 推論量・thinking 予算など、IDに含めない設定 |
| `rows[].score_extra` | ボードが同じ行に出している他の数値列(費用・試行別の値など)。キーは snake_case |
| `rows[].score` | ボードの主指標の値。ボードが行を載せつつ値を N/A としているなら `null`(表には出し、マトリクスには入れない) |
| `rows[].date` | ボードがその行に付けている日付。`YYYY-MM-DD`、ボードが月までしか書いていなければ `YYYY-MM`。無ければ `null` |
| `rows[].verified` | ボード自身の検証マーク。ボードに無ければ `null` |
| `rows[].open_source` | ボード自身がオープンと示している場合だけ `true`/`false`。推測しない |

## モデルIDの規則

- 小文字。ベンダーが売っている名前とバージョンを、空白をハイフンにして並べる。
  例: `claude-opus-4.5`, `gpt-5.1`, `gpt-5-codex`, `o3`, `gemini-2.5-pro`, `grok-4`,
  `deepseek-v3.1`, `qwen3-coder-480b-a35b`, `glm-4.6`, `kimi-k2-thinking`, `minimax-m2`
- 日付の接尾辞は落とす。ただし日付が名前の一部として区別に使われているもの
  (`deepseek-r1-0528`, `kimi-k2-0905` など)は残す。
- 推論量・thinking・温度は ID に入れず `model_config` へ。
- 知らない名前でも、書かれているとおりに写す。直さない。

## モデルの登録簿: `data/models.json`

```json
{
  "models": [
    {
      "id": "glm-5.3",
      "name": "GLM-5.3",
      "vendor": "Z.ai",
      "open_weights": true,
      "weights_url": "https://huggingface.co/zai-org/GLM-5.3",
      "aliases": ["glm-5p3"]
    }
  ]
}
```

| フィールド | 意味 |
|---|---|
| `id` | 表の `model_ids` が使うID。表が使うIDはすべてここに無ければならない(`--strict`) |
| `name` / `vendor` | 表示名と、そのモデルを出した組織 |
| `open_weights` | 重みが公開されていれば `true`(`weights_url` に配布先が要る)、公開されていなければ `false`、確かめられなければ `null` |
| `aliases` | このIDにまとめた、表記だけが違う旧ID |

表記だけが違うID(並び順、`.` と `p`、ベンダー接頭辞の有無、日付の接尾辞、`-preview`、`-instruct`)は1つにまとめ、
推論量・thinking・コンテキスト長などは表の `model_config` に移します。サイズ・`mini`/`flash`/`codex` のような
別の製品は別のIDです。

## 取れなかった表: `data/gaps/<id>.json`

```json
{ "id": "browsecomp", "name": "BrowseComp", "tried": ["https://..."], "reason_ja": "公式のリーダーボードが無い。", "retrieved": "2026-09-14" }
```
