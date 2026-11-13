import { renderCost } from "./cost.js";
import { renderRuntime, byModel } from "./runtime.js";

// Agent Bench Matrix — reads data.json (written by tools/build.almd) and renders it.
// Every string on the page comes from a leaderboard someone else runs, so nothing is
// inserted as HTML: elements are built and text is assigned.

const REPO = "https://github.com/O6lvl4/agent-bench-matrix";

const CATEGORY_NAMES = {
  coding: "コーディング",
  terminal: "ターミナル",
  "tool-use": "ツール利用・業務",
  web: "ウェブ・ブラウザ",
  "computer-use": "コンピュータ操作",
  research: "研究・ML",
  security: "セキュリティ",
  "long-horizon": "長期タスク",
  general: "汎用アシスタント",
};
const CATEGORY_ORDER = Object.keys(CATEGORY_NAMES);

// ── tiny DOM helper ────────────────────────────────────────────────────────
function h(tag, attrs, ...kids) {
  const el = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs || {})) {
    if (v === null || v === undefined || v === false) continue;
    if (k === "class") el.className = v;
    else if (k === "on") for (const [ev, fn] of Object.entries(v)) el.addEventListener(ev, fn);
    else if (k === "style") el.setAttribute("style", v);
    else el.setAttribute(k, v === true ? "" : String(v));
  }
  for (const kid of kids.flat(Infinity)) {
    if (kid === null || kid === undefined || kid === false) continue;
    el.append(kid instanceof Node ? kid : document.createTextNode(String(kid)));
  }
  return el;
}
// Only http(s) links reach an href; anything else renders as nothing, so a label
// never promises a link that is not there.
function link(url, text, cls) {
  if (typeof url !== "string" || !/^https?:\/\//.test(url)) return null;
  return h("a", { href: url, target: "_blank", rel: "noopener noreferrer", class: cls }, text || url);
}

// Freshness belongs to the source table, not to a model or another board.
function savedSource(t) {
  return ["unavailable", "review_required"].includes(t.refresh?.status);
}
function sourceStatus(t, compact = false) {
  const r = t.refresh;
  if (!r) return null;
  const saved = savedSource(t);
  const dates = `保存データ取得 ${t.retrieved} ・ 最終成功確認 ${r.last_successful_check || "記録なし"} ・ 最終確認試行 ${r.checked}`;
  if (compact) return h("span", {
    class: "source-status-compact" + (saved ? " source-saved" : ""), title: dates,
  }, saved ? "最新未確認・保存データ" : `最終成功確認 ${r.last_successful_check || "記録なし"}`);
  return h("div", { class: "source-status" + (saved ? " source-saved" : ""), "data-source-table": t.id },
    saved ? h("strong", {}, "最新未確認・保存データ") : null,
    saved && r.reason_ja ? h("p", {}, r.reason_ja) : null,
    h("p", { class: "source-dates" }, dates),
    link(typeof r.audit === "string" && /^sources\/[a-zA-Z0-9_./-]+$/.test(r.audit) && !r.audit.split("/").includes("..")
      ? `${REPO}/blob/main/${r.audit}` : null, "確認記録"));
}

// ── formatting ─────────────────────────────────────────────────────────────
function fmtScore(v, unit) {
  if (typeof v !== "number" || !isFinite(v)) return "—";
  switch (unit) {
    case "%": return v.toFixed(1);
    case "usd": return "$" + (v >= 100 ? v.toFixed(0) : v.toFixed(2));
    case "elo": return v.toFixed(0);
    case "minutes":
      if (v >= 60) return (v / 60).toFixed(v >= 600 ? 0 : 1) + "h";
      return v.toFixed(v >= 10 ? 0 : 1) + "m";
    default:
      if (Math.abs(v) >= 100) return v.toFixed(0);
      if (Math.abs(v) >= 1) return String(Math.round(v * 100) / 100);
      return String(Math.round(v * 1000) / 1000);
  }
}
function unitLabel(unit) {
  return { "%": "%", usd: "USD", elo: "Elo", minutes: "分", score: "スコア" }[unit] || unit;
}
function fmtExtra(v) {
  if (typeof v === "number") return Math.abs(v) >= 10000 ? Math.round(v).toLocaleString("en-US") : String(Math.round(v * 1000) / 1000);
  if (v === null || v === undefined) return "—";
  if (typeof v === "object") return JSON.stringify(v);
  return String(v);
}

// ── data ───────────────────────────────────────────────────────────────────
const state = { runtimeData: null, runtimeError: null, runtimeModels: new Map(), costData: null, costError: null, data: null, models: new Map(), cells: new Map(), modelIds: [], tables: [], byId: new Map(), firstSeen: new Map(), claims: new Map(), claimOnly: new Set() };

function prepare(data) {
  state.data = data;
  state.tables = [...data.tables].sort((a, b) =>
    CATEGORY_ORDER.indexOf(a.category) - CATEGORY_ORDER.indexOf(b.category) || a.name.localeCompare(b.name));
  for (const t of state.tables) state.byId.set(t.id, t);
  for (const m of data.models) state.models.set(m.id, m);
  // A cell holds the rows that ran ONE model on that table. A system that combines
  // models is real, but no single model owns its score, so it stays in its table.
  const seen = new Set();
  for (const t of state.tables) {
    for (const r of t.rows) {
      if (r.model_ids.length !== 1 || typeof r.score !== "number") continue;
      const key = r.model_ids[0] + "\u0000" + t.id;
      if (!state.cells.has(key)) state.cells.set(key, []);
      state.cells.get(key).push(r);
      seen.add(r.model_ids[0]);
      const d = (r.date || "").slice(0, 10);
      const prev = state.firstSeen.get(r.model_ids[0]);
      if (d && (!prev || d < prev)) state.firstSeen.set(r.model_ids[0], d);
    }
  }
  // A vendor's own figures, kept apart from measured cells. They can put a
  // model on the page that no board has run, and fill a cell the boards left
  // empty, but they never enter the fit and never pass as a board's number.
  for (const doc of data.claims || []) {
    for (const f of doc.figures) {
      if (f.model_ids.length !== 1) continue;
      const id = f.model_ids[0];
      if (!seen.has(id)) { seen.add(id); state.claimOnly.add(id); }
      const d = (doc.published || "").slice(0, 10);
      const prev = state.firstSeen.get(id);
      if (d && (!prev || d < prev)) state.firstSeen.set(id, d);
      if (!f.table) continue;
      const key = id + "\u0000" + f.table;
      if (!state.claims.has(key)) state.claims.set(key, []);
      state.claims.get(key).push({ figure: f, doc });
    }
  }
  state.modelIds = [...seen];
}
function cellRows(modelId, tableId) { return state.cells.get(modelId + "\u0000" + tableId) || []; }
function claimsFor(modelId, tableId) { return state.claims.get(modelId + "\u0000" + tableId) || []; }

// ── 戦闘力 ─────────────────────────────────────────────────────────────────
//
// Everything below is ESTIMATED from the measured cells by tools/fit.almd, and
// is never shown as if a board had published it. A rating is where one model
// sits on the single axis that best explains the measured standings (mean 50,
// sd 10); a predicted cell is where that axis says the model would land on a
// table nobody ran it on.
function ratingOf(id, scope) {
  const fit = state.data.fit?.[scope || "overall"];
  return fit?.models?.[id] || null;
}
function predict(t, id) {
  for (const scope of [t.category, "overall"]) {
    const fit = state.data.fit?.[scope];
    const st = fit?.tables?.[t.id];
    const m = fit?.models?.[id];
    if (!st || !m) continue;
    const a = (m.rating - 50) / 10;
    // Outside the ability span this board has actually measured, the fit is
    // extrapolating; then all it can honestly say is "above/below what this
    // board has seen".
    const margin = 0.25;
    if (a > st.ahi + margin || a < st.alo - margin) {
      const above = a > st.ahi;
      const edge = t.higher_is_better === above ? st.hi : st.lo;
      return { scope, beyond: above ? "above" : "below", value: t.higher_is_better ? edge : -edge };
    }
    const z = st.b + st.s * a;
    let v = st.mean + st.sd * z;
    // Half a standard deviation beyond the best and worst that board has seen is
    // as far as an estimate may go, and a share can never leave its own scale.
    const ceiling = t.unit === "%" ? 100 : t.unit === "ratio" ? 1 : Infinity;
    const floor = t.unit === "%" || t.unit === "ratio" ? 0 : -Infinity;
    v = Math.min(Math.max(v, Math.max(st.lo - st.sd / 2, floor)), Math.min(st.hi + st.sd / 2, ceiling));
    return { value: t.higher_is_better ? v : -v, scope, se: st.sd * m.se / 10 };
  }
  return null;
}
function better(t, a, b) { return t.higher_is_better ? a.score > b.score : a.score < b.score; }
function best(t, rows) { return rows.reduce((acc, r) => (acc === null || better(t, r, acc) ? r : acc), null); }
function modelName(id) { return state.models.get(id)?.name || id; }

// ── routing ────────────────────────────────────────────────────────────────
function parseHash() {
  const raw = location.hash.replace(/^#\/?/, "");
  const [path, query] = raw.split("?");
  const parts = (path || "matrix").split("/");
  return { view: parts[0] || "matrix", arg: parts[1] ? decodeURIComponent(parts[1]) : null, params: new URLSearchParams(query || "") };
}
function setHash(view, arg, params) {
  const q = params && [...params.keys()].length ? "?" + params.toString() : "";
  const next = "#/" + view + (arg ? "/" + encodeURIComponent(arg) : "") + q;
  if (location.hash !== next) history.replaceState(null, "", next);
}

function render() {
  const { view, arg, params } = parseHash();
  for (const a of document.querySelectorAll("#tabs a")) {
    if (a.dataset.view === view) a.setAttribute("aria-current", "page"); else a.removeAttribute("aria-current");
  }
  const views = { runtime: viewRuntime, cost: viewCost, matrix: viewMatrix, ability: viewAbility, benchmarks: viewBenchmarks, table: viewTable, claims: viewClaims, gaps: viewGaps, about: viewAbout };
  const main = document.getElementById("view");
  main.replaceChildren();
  closeDrawer();
  const strip = document.getElementById("stats");
  if (strip) strip.hidden = (views[view] ? view : "matrix") !== "matrix";
  const search = document.getElementById("global-search");
  if (search) search.value = params.get("q") || "";
  (views[view] || viewMatrix)(main, arg, params);
}

// Local-run estimates are isolated from benchmark scores and their fit.
function viewCost(main, _arg, params) {
  if (!state.costData) {
    main.append(h("p", { class: "empty" }, "費用データを読み込めませんでした。", state.costError || ""));
    return;
  }
  renderCost(main, { models: state.models, data: state.costData, params,
    navigate: (p) => {
      setHash("cost", null, p);
      render();
    } });
}

// Hosted-inference prices are observations of a provider's price list, isolated
// from benchmark scores exactly like the local-run estimates above.
function viewRuntime(main, _arg, params) {
  if (!state.runtimeData) {
    main.append(h("p", { class: "empty" }, "料金データを読み込めませんでした。", state.runtimeError || ""));
    return;
  }
  renderRuntime(main, { data: state.runtimeData, models: state.models, ratingOf, params,
    navigate: (p) => {
      setHash("runtime", null, p);
      render();
    } });
}

// ── matrix ─────────────────────────────────────────────────────────────────
function viewMatrix(main, _arg, params) {
  const cats = new Set((params.get("cat") || "").split(",").filter(Boolean));
  const q = params.get("q") || "";
  const openOnly = params.get("open") === "1";
  const min = Math.max(1, parseInt(params.get("min") || "1", 10) || 1);
  const sort = params.get("sort") || "";
  const all = params.get("all") !== "0";
  const guess = params.get("guess") !== "0";

  const update = (patch) => {
    const p = new URLSearchParams(params);
    for (const [k, v] of Object.entries(patch)) { if (v === "" || v === null || v === false) p.delete(k); else p.set(k, v); }
    setHash("matrix", null, p);
    render();
  };

  // "Recent" is read off the data, not asserted: a model is recent when a board
  // first dated it within a year of the newest retrieval, and a table is shown
  // when it holds at least one recent model. All models, including undated ones,
  // appear by default; all=0 explicitly opts into the recent-only filter.
  const cutoff = (() => {
    const d = new Date((state.data.generated || "1970-01-01") + "T00:00:00Z");
    d.setUTCDate(d.getUTCDate() - 365);
    return d.toISOString().slice(0, 10);
  })();
  const isRecent = (id) => (state.firstSeen.get(id) || "") >= cutoff;

  const present = CATEGORY_ORDER.filter((c) => state.tables.some((t) => t.category === c));
  const panel = h("section", { class: "panel matrix-panel" },
    h("div", { class: "matrix-titlebar" },
      h("div", {}, h("span", { class: "eyebrow" }, "導出された代表値"), h("h2", {}, "モデル × リーダーボード")),
      h("p", {}, h("strong", {}, "列ごとに走らせ方が違います。"),
        "比べてよいのは同じ列の中だけです。セルはそのモデル単体で走らせた行のうち最良の値で、押すと全行と出典が出ます。複数のモデルを組み合わせた行はマトリクスに入れず、「表」タブにだけ出しています。")),
    h("div", { class: "panel-toolbar" },
      h("div", { class: "field-tabs cats", role: "group", "aria-label": "分野" },
        h("button", { type: "button", "aria-pressed": cats.size === 0 ? "true" : "false", on: { click: () => update({ cat: "" }) } }, "すべて"),
        present.map((c) => h("button", {
          type: "button", "aria-pressed": cats.has(c) ? "true" : "false",
          on: { click: () => { const s = new Set(cats); s.has(c) ? s.delete(c) : s.add(c); update({ cat: [...s].join(",") }); } },
        }, CATEGORY_NAMES[c]))),
      h("div", { class: "legend", "aria-label": "凡例" },
        h("span", {}, h("i", { class: "legend-dot measured" }), "実測"),
        h("span", {}, h("b", { class: "claim-text" }, "†"), "自己申告"),
        h("span", {}, h("b", {}, "~"), "推定"),
        h("span", {}, h("b", { class: "muted" }, "·"), "値なし"))),
    h("div", { class: "panel-toolbar controls" },
      h("label", {}, h("input", { type: "checkbox", checked: openOnly, on: { change: (e) => update({ open: e.target.checked ? "1" : "" }) } }), "オープンウェイトのみ"),
      h("label", { title: `既定では古いモデル・日付不明のモデルも表示。オフにすると ${cutoff} 以降にボードへ初めて載ったモデルと、それが載っている表だけを出す` },
        h("input", { type: "checkbox", checked: all, on: { change: (e) => update({ all: e.target.checked ? "1" : "0" }) } }), "古いモデル・表も出す"),
      h("label", { title: "実測のない枡に、当てはめから計算した推定値(~付き)を入れる" },
        h("input", { type: "checkbox", checked: guess, on: { change: (e) => update({ guess: e.target.checked ? "" : "0" }) } }), "空きを推定で埋める"),
      h("label", {}, "載っている表が", h("input", { type: "number", min: 1, value: min, on: { change: (e) => update({ min: e.target.value }) } }), "以上"),
      h("label", {}, "並び", h("select", { on: { change: (e) => update({ sort: e.target.value }) } },
        h("option", { value: "", selected: sort === "" }, "新しいモデル順(ボードに初めて載った日)"),
        h("option", { value: "coverage", selected: sort === "coverage" }, "載っている表の数"),
        state.tables.some((t) => t.id === sort) ? h("option", { value: sort, selected: true }, `列: ${state.byId.get(sort).name}`) : null))));
  main.append(panel);

  const needle = q.toLowerCase();
  const candidates = state.modelIds
    .filter((id) => all || isRecent(id))
    .filter((id) => !openOnly || state.models.get(id)?.open_weights === true)
    .filter((id) => !needle || id.includes(needle)
      || (state.models.get(id)?.name || "").toLowerCase().includes(needle)
      || (state.models.get(id)?.vendor || "").toLowerCase().includes(needle));
  // Columns keep their category, and inside it the table that holds the most of
  // the models on screen comes first, so the dense part of the matrix is on the left.
  const held = new Map(state.tables.map((t) => [t.id, candidates.filter((id) => cellRows(id, t.id).length > 0 || claimsFor(id, t.id).length > 0).length]));
  const tables = state.tables
    .filter((t) => cats.size === 0 || cats.has(t.category))
    .filter((t) => held.get(t.id) > 0)
    .sort((a, b) => CATEGORY_ORDER.indexOf(a.category) - CATEGORY_ORDER.indexOf(b.category)
      || held.get(b.id) - held.get(a.id) || a.name.localeCompare(b.name));
  let models = candidates.map((id) => {
    const m = state.models.get(id);
    const cells = tables.map((t) => best(t, cellRows(id, t.id)));
    // A vendor's figure counts as "on the page", so a claim-only model has a row;
    // it still does not count as measured anywhere else.
    const claimed = tables.filter((t, i) => !cells[i] && claimsFor(id, t.id).length > 0).length;
    return { id, m, cells, coverage: cells.filter(Boolean).length + claimed };
  }).filter((x) => x.coverage >= min);

  const sortIdx = tables.findIndex((t) => t.id === sort);
  if (sort === "coverage") {
    models.sort((a, b) => b.coverage - a.coverage || modelName(a.id).localeCompare(modelName(b.id)));
  } else if (sortIdx >= 0) {
    const t = tables[sortIdx];
    models.sort((a, b) => {
      const x = a.cells[sortIdx], y = b.cells[sortIdx];
      if (!x && !y) return b.coverage - a.coverage;
      if (!x) return 1; if (!y) return -1;
      return t.higher_is_better ? y.score - x.score : x.score - y.score;
    });
  } else {
    // Newest first, by the earliest date any board attaches to the model: that is
    // when it first showed up, which is the nearest thing to a release date the
    // data itself can vouch for. Models no board dates go last.
    models.sort((a, b) => (state.firstSeen.get(b.id) || "").localeCompare(state.firstSeen.get(a.id) || "")
      || b.coverage - a.coverage || modelName(a.id).localeCompare(modelName(b.id)));
  }

  if (models.length === 0 || tables.length === 0) {
    panel.append(h("p", { class: "empty" }, "条件に合うモデルがありません。"));
    return;
  }

  // Shade by rank within the column, over every model on that table (not just the
  // filtered view), so a cell's colour does not change when the filter does.
  const rankOf = new Map();
  for (const t of tables) {
    const scores = state.modelIds.map((id) => best(t, cellRows(id, t.id))).filter(Boolean).map((r) => r.score);
    scores.sort((a, b) => (t.higher_is_better ? a - b : b - a));
    rankOf.set(t.id, scores);
  }
  const shade = (t, score) => {
    const s = rankOf.get(t.id);
    if (!s || s.length < 2) return 0.35;
    let lo = 0, hi = s.length;
    while (lo < hi) { const mid = (lo + hi) >> 1; if (t.higher_is_better ? s[mid] < score : s[mid] > score) lo = mid + 1; else hi = mid; }
    return lo / (s.length - 1);
  };

  const groups = [];
  for (const t of tables) {
    const last = groups[groups.length - 1];
    if (last && last.cat === t.category) last.n++; else groups.push({ cat: t.category, n: 1 });
  }

  const direction = (t) => (t.higher_is_better ? "高いほど良い" : "低いほど良い");
  const thead = h("thead", {},
    h("tr", { class: "cat" },
      h("th", { class: "corner model-col", rowspan: 2 },
        h("div", { class: "th-main" }, "モデル ", h("span", {}, `${models.length} 件 × ${tables.length} 表`)),
        h("div", { class: "th-sub" }, "戦闘力は総合の推定値(~)。", sortIdx >= 0 ? "列名をもう一度押すと並べ替えを解除" : "列名を押すとその列で並べ替え")),
      groups.map((g) => h("th", { colspan: g.n }, CATEGORY_NAMES[g.cat]))),
    h("tr", { class: "col" },
      tables.map((t) => h("th", { scope: "col", title: `${t.name} — ${t.board}(${t.metric})` },
        h("div", { class: "board-head" },
          h("div", {
            class: "colhead" + (t.id === sort ? " sorted" : ""),
            role: "button", tabindex: 0,
            on: {
              click: () => update({ sort: t.id === sort ? "" : t.id }),
              keydown: (e) => { if (e.key === "Enter") update({ sort: t.id === sort ? "" : t.id }); },
            },
          }, h("span", { class: "colname" }, t.name), " ", h("small", {}, t.board)),
          h("span", { class: "board-meta" }, `${unitLabel(t.unit)}・${direction(t)}`),
          sourceStatus(t, true) || h("span", { class: "fetch-state ok" }, `取得 ${t.retrieved}`))))),
  );

  const tbody = h("tbody", {}, models.map((x, n) => h("tr", {},
    h("th", { scope: "row", title: x.id },
      h("div", { class: "model-cell" },
        h("span", { class: "rank" }, n + 1),
        h("div", { class: "model-info" },
          h("strong", {}, modelName(x.id)),
          h("span", {},
            [x.m?.vendor, x.m?.open_weights === true ? "オープンウェイト" : null, state.firstSeen.get(x.id)].filter(Boolean).join(" · "))),
        (() => {
          const r = ratingOf(x.id);
          return r ? h("div", { class: "power-score rating", title: `推定の戦闘力 ${r.rating.toFixed(1)} ± ${r.se.toFixed(1)}(実測 ${r.n} 表)` },
            h("b", {}, "~" + r.rating.toFixed(1)), h("span", {}, "± " + r.se.toFixed(1)), h("small", {}, `実測 ${r.n}`)) : h("div", { class: "power-score none", title: "当てはめに入る実測がない" }, h("b", {}, "—"));
        })())),
    x.cells.map((r, i) => {
      const t = tables[i];
      if (!r) {
        const cs = claimsFor(x.id, t.id);
        if (cs.length) {
          const c = cs[0];
          return h("td", { class: "claim claimed" },
            h("button", {
              type: "button",
              title: `自己申告(ボードの数字ではない): ${c.doc.vendor} が「${c.doc.title}」で出した ${c.figure.benchmark_raw} の値`,
              on: { click: () => openCell(x.id, t) },
            }, "†" + fmtScore(c.figure.value, t.unit)));
        }
        const p = guess ? predict(t, x.id) : null;
        if (!p) return h("td", { class: "none", title: "値なし: このボードにこのモデルの行はない" }, "·");
        const beyond = p.beyond ? (p.beyond === "above" ? "≳" : "≲") : "~";
        return h("td", { class: "guess estimated" },
          h("button", {
            type: "button",
            title: p.beyond
              ? `推定(実測ではない): ${modelName(x.id)} の実力は、この表が実際に測ったモデルの範囲の外。言えるのは「この表で見えている値より${p.beyond === "above" ? "上" : "下"}」まで`
              : `推定値(実測ではない): ${modelName(x.id)} を ${t.name} で走らせたらこのあたり、という当てはめの予測`,
            on: { click: () => openCell(x.id, t) },
          }, beyond + fmtScore(p.value, t.unit)));
      }
      const pct = Math.round(4 + shade(t, r.score) * 30);
      return h("td", { class: "measured", style: `background: color-mix(in srgb, var(--heat) ${pct}%, transparent)` },
        h("button", {
          type: "button",
          title: `${savedSource(t) ? "最新未確認・保存データ: " : ""}${modelName(x.id)} / ${t.name}: ${fmtScore(r.score, t.unit)} ${unitLabel(t.unit)}(${r.system})`,
          on: { click: () => openCell(x.id, t) },
        }, fmtScore(r.score, t.unit)));
    }))));

  panel.append(h("div", { class: "scroller table-scroller" }, h("table", { class: "matrix matrix-table" }, thead, tbody)),
    h("div", { class: "table-footer" },
      h("span", {}, `表示 ${models.length} / ${state.modelIds.length} モデル · ${tables.length} / ${state.tables.length} リーダーボード`),
      h("span", {}, "別のリーダーボード間でスコアを直接比較しないでください。")));
}

// ── drawer ─────────────────────────────────────────────────────────────────
function claimEntry(t, c) {
  const f = c.figure, d = c.doc;
  return h("div", { class: "entry" },
    h("div", { class: "score claim-text" }, "†" + fmtScore(f.value, t.unit), " ",
      h("span", { class: "muted", style: "font-size:12px" }, f.metric), " ", h("span", { class: "chip warn" }, "自己申告")),
    h("dl", {},
      h("dt", {}, "出した側"), h("dd", {}, d.vendor, " — ", d.title),
      h("dt", {}, "モデル表記"), h("dd", {}, f.model_raw, f.model_config ? h("span", { class: "muted" }, `(${f.model_config})`) : null),
      h("dt", {}, "ベンチ表記"), h("dd", {}, f.benchmark_raw),
      h("dt", {}, "走らせ方"), h("dd", {}, d.harness_ja),
      f.note_ja ? [h("dt", {}, "注"), h("dd", {}, f.note_ja)] : null,
      d.published ? [h("dt", {}, "公表"), h("dd", {}, d.published)] : null,
      h("dt", {}, "出典"), h("dd", {}, link(d.source, "元の文書"), " ", link(`${REPO}/blob/main/${d.snapshot}`, "取得データ"))),
    h("p", { class: "muted", style: "font-size:12.5px;margin:6px 0 0" }, "ボードの数字ではありません。", t.name, " のボードにこのモデルの行は無く、この値は出した側が自分で走らせたものです。"));
}
function openCell(modelId, t) {
  const rows = [...cellRows(modelId, t.id)].sort((a, b) => (better(t, a, b) ? -1 : 1));
  const cs = rows.length ? [] : claimsFor(modelId, t.id);
  const p = rows.length || cs.length ? null : predict(t, modelId);
  const r = ratingOf(modelId, p?.scope);
  const kind = rows.length ? "実測" : cs.length ? "自己申告" : p ? "推定" : "値なし";
  showDrawer(
    [h("span", { class: "eyebrow" }, "セル値の根拠 · ", kind),
     h("h3", {}, modelName(modelId), " × ", t.name),
     h("p", {}, `${t.board} ・ ${t.metric}(${t.higher_is_better ? "高いほど良い" : "低いほど良い"})`)],
    [h("div", { class: "drawer-path" },
       h("span", {}, "分野"), h("b", {}, CATEGORY_NAMES[t.category] || t.category), h("i", { "aria-hidden": "true" }, "›"),
       h("span", {}, "ベンチマーク"), h("b", {}, t.family), h("i", { "aria-hidden": "true" }, "›"),
       h("span", {}, "リーダーボード"), h("b", {}, t.name)),
     sourceStatus(t), h("p", { class: "note" }, h("strong", {}, "走らせ方 "), t.harness_ja),
     !rows.length && !cs.length && !p ? h("div", { class: "entry" }, h("p", { class: "muted" }, "このボードにこのモデルの行はなく、推定も出せません。空欄ではなく、値がないものとして扱います。")) : null,
     cs.map((c) => claimEntry(t, c)),
     p ? h("div", { class: "entry" },
       h("div", { class: "score guess-text" }, (p.beyond ? (p.beyond === "above" ? "≳" : "≲") : "~") + fmtScore(p.value, t.unit), " ",
         h("span", { class: "muted", style: "font-size:12px" }, unitLabel(t.unit)), " ", h("span", { class: "chip warn" }, "推定")),
       h("p", { class: "muted", style: "font-size:12.5px" },
         p.beyond
           ? `このボードは ${modelName(modelId)} を走らせておらず、その実力はこの表が実際に測ったモデルの範囲の外です。言えるのは「この表で見えている値より${p.beyond === "above" ? "上" : "下"}」までで、具体的な点数は出せません。根拠は、`
           : `このボードは ${modelName(modelId)} を走らせていません。これは実測値ではなく、`,
         `${p.scope === "overall" ? "全分野" : CATEGORY_NAMES[p.scope]}の実測から当てはめた1本の軸（戦闘力 ${r ? r.rating.toFixed(1) : "—"}`,
         r ? `、実測 ${r.n} 表` : "", `）を、この表の目盛りに戻した値です。`),
       h("p", {}, h("a", { href: "#/ability" }, "推定のしかた →"))) : null,
     rows.map((x) => entry(t, x)),
     h("div", { class: "source-box" },
       h("div", {}, h("span", {}, "出典"), h("b", {}, link(t.source, "リーダーボード"), " ", link(`${REPO}/blob/main/${t.snapshot}`, "取得データ"))),
       h("div", {}, h("span", {}, "取得日"), h("b", { class: "mono" }, t.retrieved)),
       h("div", {}, h("span", {}, "最新の行"), h("b", { class: "mono" }, t.newest_row_date || "行に日付なし"))),
     h("a", { class: "button secondary drawer-button", href: `#/table/${encodeURIComponent(t.id)}` }, "この表をすべて見る →")]);
}
function entry(t, r) {
  const extras = Object.entries(r.score_extra || {});
  return h("div", { class: "entry" },
    h("div", { class: "score" }, fmtScore(r.score, t.unit), " ", h("span", { class: "muted", style: "font-size:12px" }, unitLabel(t.unit))),
    h("dl", {},
      h("dt", {}, "ボード上の名前"), h("dd", {}, r.system),
      r.agent ? [h("dt", {}, "エージェント"), h("dd", {}, r.agent)] : null,
      h("dt", {}, "モデル表記"), h("dd", {}, r.model_raw.length ? r.model_raw.join(", ") : "非開示"),
      r.model_config ? [h("dt", {}, "設定"), h("dd", {}, r.model_config)] : null,
      r.rank !== null ? [h("dt", {}, "順位"), h("dd", {}, String(r.rank))] : null,
      h("dt", {}, "日付"), h("dd", {}, r.date || "ボードに記載なし"),
      r.verified !== null ? [h("dt", {}, "検証"), h("dd", {}, r.verified ? "ボードの検証済み" : "未検証")] : null,
      r.org ? [h("dt", {}, "提出者"), h("dd", {}, r.org)] : null,
      extras.map(([k, v]) => [h("dt", { class: "mono" }, k), h("dd", { class: "mono" }, fmtExtra(v))]),
      h("dt", {}, "出典"), h("dd", {}, link(r.row_url, r.row_url ? "この行のリンク" : null) || link(t.source, "リーダーボード"))));
}
function showDrawer(title, body) {
  document.getElementById("drawer-title").replaceChildren(...title.flat());
  document.getElementById("drawer-body").replaceChildren(...body.flat().filter(Boolean));
  const d = document.getElementById("drawer");
  d.hidden = false;
  const o = document.getElementById("drawer-overlay");
  if (o) o.hidden = false;
  document.getElementById("drawer-close").focus();
}
function closeDrawer() {
  document.getElementById("drawer").hidden = true;
  const o = document.getElementById("drawer-overlay");
  if (o) o.hidden = true;
}

// ── benchmarks ─────────────────────────────────────────────────────────────
function viewBenchmarks(main) {
  main.append(pageHeading("カタログ", "ベンチマーク", `${CATEGORY_ORDER.filter((c) => state.tables.some((t) => t.category === c)).length} 分野 · ${new Set(state.tables.map((t) => t.family)).size} ベンチマーク · ${state.tables.length} リーダーボード`));
  main.append(h("p", { class: "note" }, "1枚のカード = 1つのリーダーボードの表です。同じベンチでも、載っている場所が違えば走らせ方が違うので別のカードにしています。"));
  for (const c of CATEGORY_ORDER) {
    const ts = state.tables.filter((t) => t.category === c);
    if (!ts.length) continue;
    main.append(h("section", { class: "cat-group" },
      h("h2", {}, CATEGORY_NAMES[c], h("span", { class: "muted", style: "font-weight:400" }, `  ${ts.length} 表`)),
      h("div", { class: "cards" }, ts.map(card))));
  }
}
// Whether the fit uses a board, and what the fit learned about it. A board with
// fewer than three measured models says nothing about standings, so it is left out.
function fitOf(t) {
  for (const scope of [t.category, "overall"]) {
    const st = state.data.fit?.[scope]?.tables?.[t.id];
    if (st) return st;
  }
  return null;
}
function fitBadge(t) {
  return fitOf(t)
    ? h("span", { class: "fit yes", title: "戦闘力の当てはめに使っている" }, "当てはめ採用")
    : h("span", { class: "fit near", title: "実測が3モデルに満たない表は順位を語らないので、当てはめに使わない" }, "除外: 実測3モデル未満");
}
function pageHeading(eyebrow, title, sub) {
  return h("div", { class: "page-heading" },
    h("div", {}, h("span", { class: "eyebrow" }, eyebrow), h("h2", {}, title), sub ? h("p", {}, sub) : null));
}
function card(t) {
  const st = fitOf(t);
  return h("article", { class: "card" },
    h("div", { class: "card-kicker" }, h("span", { class: "entity-type" }, t.family), fitBadge(t)),
    h("h3", {}, h("a", { href: `#/table/${encodeURIComponent(t.id)}` }, t.name)),
    sourceStatus(t),
    h("div", { class: "meta" },
      h("span", { class: "chip" }, t.board),
      h("span", { class: "chip" }, `${t.rows.length} 行`),
      t.tasks !== null ? h("span", { class: "chip" }, `${t.tasks} タスク`) : null,
      t.newest_row_date ? h("span", { class: "chip" }, `最新の行 ${t.newest_row_date}`) : h("span", { class: "chip warn" }, "行に日付なし")),
    h("p", {}, t.measures_ja),
    h("dl", {},
      h("dt", {}, "指標"), h("dd", {}, `${t.metric}(${t.higher_is_better ? "高いほど良い" : "低いほど良い"})`),
      h("dt", {}, "走らせ方"), h("dd", {}, t.harness_ja),
      t.tasks_note ? [h("dt", {}, "タスク数"), h("dd", {}, t.tasks_note)] : null,
      t.notes_ja ? [h("dt", {}, "注意"), h("dd", {}, t.notes_ja)] : null),
    st ? h("div", { class: "leaderboard-property", title: "当てはめで決まった、この表の性質" },
      h("span", {}, "水準 ", h("b", {}, st.b.toFixed(2))),
      h("span", {}, "広がり ", h("b", {}, st.s.toFixed(2))),
      h("span", {}, "実測モデル ", h("b", {}, st.n)),
      h("span", {}, "観測範囲 ", h("b", {}, `${fmtScore(st.lo, t.unit)}–${fmtScore(st.hi, t.unit)}`))) : null,
    h("div", { class: "links" },
      link(t.source, "リーダーボード"),
      link(t.paper, "論文"),
      link(t.repo, "リポジトリ"),
      link(`${REPO}/blob/main/${t.snapshot}`, "取得データ")));
}

// ── one table ──────────────────────────────────────────────────────────────
function viewTable(main, arg, params) {
  const t = state.byId.get(arg) || state.tables[0];
  if (!t) { main.append(h("p", { class: "empty" }, "表がありません。")); return; }
  const q = (params.get("q") || "").toLowerCase();
  const sortKey = params.get("sort") || "score";
  const asc = params.get("dir") === "asc";

  const update = (patch) => {
    const p = new URLSearchParams(params);
    for (const [k, v] of Object.entries(patch)) { if (v === "" || v === null) p.delete(k); else p.set(k, v); }
    setHash("table", t.id, p);
    render();
  };

  main.append(h("div", { class: "controls" },
    h("label", {}, "表", h("select", { on: { change: (e) => { setHash("table", e.target.value, null); render(); } } },
      CATEGORY_ORDER.map((c) => {
        const ts = state.tables.filter((x) => x.category === c);
        return ts.length ? h("optgroup", { label: CATEGORY_NAMES[c] },
          ts.map((x) => h("option", { value: x.id, selected: x.id === t.id }, `${x.name}(${x.board})`))) : null;
      })))));

  main.append(h("div", { class: "table-head" },
    h("h2", {}, t.name),
    h("span", { class: "chip" }, t.board),
    h("span", { class: "chip" }, CATEGORY_NAMES[t.category]),
    fitBadge(t),
    h("span", { class: "muted" }, `取得 ${t.retrieved}`),
    link(t.source, "リーダーボード"),
    link(`${REPO}/blob/main/${t.snapshot}`, "取得データ")));
  if (t.refresh) main.append(sourceStatus(t));
  main.append(h("p", { class: "desc" }, t.measures_ja, " ", h("span", { class: "muted" }, t.harness_ja), t.notes_ja ? [" ", h("span", { class: "muted" }, t.notes_ja)] : null));

  const extraKeys = [...new Set(t.rows.flatMap((r) => Object.keys(r.score_extra || {})))];
  let rows = t.rows.filter((r) => !q || [r.system, r.agent, r.org, ...r.model_raw, ...r.model_ids].some((s) => (s || "").toLowerCase().includes(q)));
  const val = (r) => {
    if (sortKey === "score") return r.score;
    if (sortKey === "date") return r.date || "";
    if (sortKey === "rank") return r.rank ?? Infinity;
    if (sortKey === "system") return r.system.toLowerCase();
    const v = r.score_extra?.[sortKey];
    return typeof v === "number" ? v : -Infinity;
  };
  rows = [...rows].sort((a, b) => {
    const x = val(a), y = val(b);
    // A value the board shows as N/A goes last, whichever way the column runs.
    const xn = x === null || x === undefined, yn = y === null || y === undefined;
    if (xn || yn) return xn === yn ? 0 : xn ? 1 : -1;
    let c = x < y ? -1 : x > y ? 1 : 0;
    if (sortKey === "score") c = t.higher_is_better ? -c : c;
    else if (sortKey !== "rank" && sortKey !== "system") c = -c;
    return asc ? -c : c;
  });

  const th = (key, label, num) => h("th", {
    class: num ? "num" : null, scope: "col",
    on: { click: () => update({ sort: key, dir: key === sortKey && !asc ? "asc" : "" }) },
  }, label, key === sortKey ? (asc ? " ↑" : " ↓") : "");

  main.append(h("div", { class: "plain-wrap" }, h("table", { class: "plain" },
    h("thead", {}, h("tr", {},
      th("rank", "順位", true),
      th("system", "ボード上の名前"),
      h("th", {}, "エージェント"),
      h("th", {}, "モデル"),
      th("score", `${t.metric}`, true),
      extraKeys.map((k) => th(k, k, true)),
      th("date", "日付"),
      h("th", {}, "検証"),
      h("th", {}, "出典"))),
    h("tbody", {}, rows.map((r) => h("tr", {},
      h("td", { class: "num" }, r.rank ?? ""),
      h("td", { class: "sys" }, r.system, r.org ? h("div", { class: "muted", style: "font-size:12px" }, r.org) : null),
      h("td", {}, r.agent || h("span", { class: "muted" }, "—")),
      h("td", {}, h("div", { class: "models" },
        r.model_ids.length
          ? r.model_ids.map((id) => h("span", { class: "chip", title: r.model_raw.join(", ") }, modelName(id)))
          : (r.model_raw.length ? r.model_raw.map((s) => h("span", { class: "chip warn", title: "正規化できていない表記" }, s)) : h("span", { class: "muted" }, "非開示")),
        r.model_config ? h("span", { class: "muted", style: "font-size:12px" }, r.model_config) : null)),
      h("td", { class: "num" }, fmtScore(r.score, t.unit)),
      extraKeys.map((k) => h("td", { class: "num" }, fmtExtra(r.score_extra?.[k]))),
      h("td", { class: "mono", style: "white-space:nowrap" }, r.date || ""),
      h("td", {}, r.verified === null ? "" : r.verified ? "✓" : "—"),
      h("td", {}, link(r.row_url, "リンク"))))))));
  main.append(h("p", { class: "muted", style: "font-size:12px" }, `${rows.length} / ${t.rows.length} 行`));
}

// ── 戦闘力 ─────────────────────────────────────────────────────────────────
function viewAbility(main, _arg, params) {
  const minN = Math.max(1, parseInt(params.get("n") || "3", 10) || 1);
  const openOnly = params.get("open") === "1";
  const q = (params.get("q") || "").toLowerCase();
  const scope = state.data.fit?.[params.get("scope") || "overall"] ? (params.get("scope") || "overall") : "overall";
  const update = (patch) => {
    const p = new URLSearchParams(params);
    for (const [k, v] of Object.entries(patch)) { if (v === "" || v === null) p.delete(k); else p.set(k, v); }
    setHash("ability", null, p);
    render();
  };

  main.append(pageHeading("推定指標", "戦闘力", "実測から当てはめた推定です。リーダーボードが公表した数字ではありません。"));
  main.append(h("p", { class: "note" },
    h("strong", {}, "ここだけは実測ではなく推定です。"),
    "表ごとに標準化した実測値を z とし、", h("code", {}, "z(表, モデル) ≈ b(表) + s(表) × a(モデル)"),
    " を最小二乗で当てはめた a(モデル) を、平均50・標準偏差10に直したものです。実測の少ないモデルは、当てはめきれない分だけ真ん中へ寄せてあります。",
    `全体のばらつきのうち説明できなかった大きさは σ = ${(state.data.fit?.overall?.sigma ?? 0).toFixed(2)}(z の単位)で、これが誤差の元です。`,
    state.claimOnly.size ? ` ボードに載っておらず自己申告しかないモデル(${[...state.claimOnly].map(modelName).join("、")})は、当てはめに入れていないので、ここには出ません。` : ""));

  main.append(h("p", { class: "note" }, h("a", { href: "#/cost" }, "このモデル、いくらで動く？ → ローカル実行費用を調べる")));

  const scopes = ["overall", ...CATEGORY_ORDER.filter((c) => state.data.fit?.[c])];
  main.append(h("div", { class: "controls" },
    h("div", { class: "cats", role: "group", "aria-label": "軸" },
      scopes.map((s) => h("button", {
        type: "button", "aria-pressed": s === scope ? "true" : "false",
        on: { click: () => update({ scope: s === "overall" ? "" : s }) },
      }, s === "overall" ? "総合" : CATEGORY_NAMES[s]))),
    h("label", {}, h("input", { type: "checkbox", checked: openOnly, on: { change: (e) => update({ open: e.target.checked ? "1" : "" }) } }), "オープンウェイトのみ"),
    h("label", { title: "その軸で実測が何表あるか" }, "実測が", h("input", { type: "number", min: 1, value: minN, on: { change: (e) => update({ n: e.target.value }) } }), "表以上")));

  const fit = state.data.fit[scope];
  const rows = Object.entries(fit.models)
    .map(([id, r]) => ({ id, r, m: state.models.get(id) }))
    .filter((x) => x.r.n >= minN)
    .filter((x) => !openOnly || x.m?.open_weights === true)
    .filter((x) => !q || x.id.includes(q) || (x.m?.name || "").toLowerCase().includes(q) || (x.m?.vendor || "").toLowerCase().includes(q))
    .sort((a, b) => b.r.rating - a.r.rating);

  if (!rows.length) { main.append(h("p", { class: "empty" }, "条件に合うモデルがありません。")); return; }

  const cats = CATEGORY_ORDER.filter((c) => state.data.fit?.[c]);
  // The bar spans what is on screen, so differences at the top stay visible
  // instead of every frontier model filling the width.
  // The band is the rating ± its error on the same span, so a model measured
  // on few boards visibly carries a wider band.
  const lo = Math.min(...rows.map((x) => x.r.rating - x.r.se));
  const hi = Math.max(...rows.map((x) => x.r.rating + x.r.se));
  const at = (v) => (hi > lo ? Math.min(100, Math.max(0, ((v - lo) / (hi - lo)) * 100)) : 50);
  const bar = (r) => h("span", { class: "bar bar-track", title: `${r.rating.toFixed(1)} ± ${r.se.toFixed(1)}(表示範囲 ${lo.toFixed(1)} 〜 ${hi.toFixed(1)})` },
    h("span", { class: "bar-fill", style: `width:${Math.max(1, at(r.rating)).toFixed(1)}%` }),
    h("span", { class: "bar-band", style: `left:${at(r.rating - r.se).toFixed(1)}%;width:${Math.max(0.6, at(r.rating + r.se) - at(r.rating - r.se)).toFixed(1)}%` }));
  main.append(h("div", { class: "plain-wrap" }, h("table", { class: "plain ability" },
    h("thead", {}, h("tr", {},
      h("th", { class: "num" }, "順位"),
      h("th", {}, "モデル"),
      h("th", { class: "num" }, scope === "overall" ? "総合" : CATEGORY_NAMES[scope]),
      h("th", {}, ""),
      h("th", { class: "num", title: "その軸で実測のある表の数" }, "実測"),
      cats.map((c) => h("th", { class: "num", title: CATEGORY_NAMES[c] }, CATEGORY_NAMES[c].slice(0, 4))))),
    h("tbody", {}, rows.map((x, i) => h("tr", {},
      h("td", { class: "num" }, i + 1),
      h("td", {}, modelName(x.id),
        x.m?.open_weights ? h("span", { class: "chip ow" }, "open") : null,
        x.m?.vendor ? h("span", { class: "vendor" }, x.m.vendor) : null,
        state.runtimeModels.has(x.id) ? h("a", { href: "#/runtime?model=" + encodeURIComponent(x.id), class: "cost-model-link runtime-model-link", title: "配信元ごとの掲載単価" }, `提供 ${state.runtimeModels.get(x.id).length} 件 →`) : null,
        h("a", { href: "#/cost?model=" + encodeURIComponent(x.id), class: "cost-model-link" }, "実行費用 →")),
      h("td", { class: "num est" }, "~" + x.r.rating.toFixed(1), h("span", { class: "muted" }, " ±", x.r.se.toFixed(1))),
      h("td", {}, bar(x.r)),
      h("td", { class: "num" }, x.r.n),
      cats.map((c) => {
        const r = ratingOf(x.id, c);
        return h("td", { class: "num" + (r ? "" : " muted"), title: r ? `推定 ・ 実測 ${r.n} 表 ・ ±${r.se.toFixed(1)}` : "その分野の実測なし" }, r ? "~" + r.rating.toFixed(0) : "·");
      })))))));
  main.append(h("p", { class: "muted", style: "font-size:12px" }, `${rows.length} モデル。この数字はボードが公表したものではなく、実測から当てはめた推定です。`));
}

// ── 自己申告 ───────────────────────────────────────────────────────────────
function viewClaims(main) {
  const docs = [...(state.data.claims || [])].sort((a, b) => (b.published || "").localeCompare(a.published || ""));
  main.append(pageHeading("観測 · 開発元の公表", "自己申告", "リーダーボードの数字とは別の層です。† を付けて区別します。"));
  main.append(h("p", { class: "note" },
    h("strong", {}, "ここにある数字は、出した側が自分で走らせて公表したものです。"),
    "どのリーダーボードにも載っていないモデルを、それでも並べて見るための層で、ボードの数字とは書式(†)も置き場所も分けています。戦闘力の当てはめには入れません。数字は元の文書から機械的に取り出し、取り出した部分を保存しています。"));
  if (!docs.length) { main.append(h("p", { class: "empty" }, "ありません。")); return; }
  for (const d of docs) {
    main.append(h("section", { class: "cat-group" },
      h("h2", {}, d.vendor, " — ", d.title,
        h("span", { class: "muted", style: "font-weight:400" }, d.published ? `  公表 ${d.published}` : "", `  取得 ${d.retrieved}`)),
      h("p", { class: "desc" }, d.harness_ja, d.notes_ja ? [" ", h("span", { class: "muted" }, d.notes_ja)] : null),
      h("p", { class: "links", style: "display:flex;gap:12px;font-size:12px;margin:0 0 10px" }, link(d.source, "元の文書"), link(`${REPO}/blob/main/${d.snapshot}`, "取得データ")),
      h("div", { class: "plain-wrap" }, h("table", { class: "plain" },
        h("thead", {}, h("tr", {}, h("th", {}, "モデル(表記のまま)"), h("th", {}, "ベンチ(表記のまま)"), h("th", { class: "num" }, "値"), h("th", {}, "指標"), h("th", {}, "対応する表"), h("th", {}, "注"))),
        h("tbody", {}, d.figures.map((f) => h("tr", {},
          h("td", {}, f.model_raw, f.model_ids.length === 1 ? h("span", { class: "vendor" }, modelName(f.model_ids[0])) : null,
            f.model_config ? h("div", { class: "muted", style: "font-size:12px" }, f.model_config) : null),
          h("td", {}, f.benchmark_raw),
          h("td", { class: "num" }, "†", String(f.value)),
          h("td", {}, f.metric),
          h("td", {}, f.table && state.byId.get(f.table)
            ? h("a", { href: `#/table/${encodeURIComponent(f.table)}` }, state.byId.get(f.table).name)
            : h("span", { class: "muted" }, "なし")),
          h("td", { class: "muted", style: "font-size:12px" }, f.note_ja || ""))))))));
  }
}

// ── gaps ───────────────────────────────────────────────────────────────────
function viewGaps(main) {
  const gaps = [...state.data.gaps].sort((a, b) => a.name.localeCompare(b.name));
  main.append(pageHeading("取得状態", "取れなかった表", `${gaps.length} 件。空欄にせず、取れなかったこととして残しています。`));
  main.append(h("p", { class: "note" }, "機械的に取得できなかった表と、過去の取得失敗の記録です。各記録の日付時点の状態であり、保存済みの表がある場合は、その表の最新の確認状態も参照してください。数字を推測で埋めることはしません。"));
  if (!gaps.length) { main.append(h("p", { class: "empty" }, "ありません。")); return; }
  main.append(h("div", { class: "gaps" }, gaps.map((g) => h("article", { class: "gap" },
    h("h3", {}, g.name, h("span", { class: "muted", style: "font-weight:400" }, `  確認 ${g.retrieved}`)),
    h("p", {}, g.reason_ja),
    g.tried.length ? h("ul", {}, g.tried.map((u) => h("li", {}, link(u)))) : null))));
}

// ── about ──────────────────────────────────────────────────────────────────
function viewAbout(main) {
  const d = state.data;
  main.append(pageHeading("算出方法とデータ方針", "このデータについて"));
  main.append(h("div", { class: "prose" },
    h("h2", {}, "何をまとめたか"),
    h("p", {}, "エージェント(道具を使い、複数の手順で課題を解くAI)を測るベンチマークについて、各ベンチが自分で公開しているリーダーボードの表を集め、モデルごとに並べ直したものです。単発のコード生成(HumanEval など)や知識問題は入れていません。"),
    h("h2", {}, "数字の出どころ"),
    h("ul", {},
      h("li", {}, "数字はすべて、各リーダーボードが公開しているデータ(リポジトリ内の JSON/CSV/YAML、ページが読み込む公開データなど)を取得し、スクリプトで取り出したものです。記憶や要約から書いた数字はありません。"),
      h("li", {}, "取得した元データはリポジトリの ", h("code", {}, "sources/"), " に保存し、各表から辿れます。"),
      h("li", {}, "取れなかった表は推測で埋めず、「取れなかった表」に理由付きで残しています。"),
      h("li", {}, `最終取得日: ${d.generated}。リーダーボードは日々更新されるので、これは取得日時点の写しです。`)),
    h("h2", {}, "推定(戦闘力と、空きセルの ~ 付きの値)"),
    h("ul", {},
      h("li", {}, "「戦闘力」タブの数字と、マトリクスの薄い ", h("code", {}, "~"), " 付きの値だけは、ボードが公表した数字ではなく、実測から計算した推定です。実測値と混ざらないよう、書式も色も分けています。"),
      h("li", {}, "作り方: 表ごとに実測値を標準化し(高いほど良い向きに揃える)、", h("code", {}, "z(表, モデル) ≈ b(表) + s(表) × a(モデル)"), " を交互最小二乗で当てはめます。a がモデルの実力、s はその表が実力差をどれだけ広げて見せるか、b はその表の水準です。"),
      h("li", {}, "実測が3モデルに満たない表と、全員が同じ値の表は、順位を何も語らないので当てはめに使いません。"),
      h("li", {}, "実測の少ないモデルは、当てはめきれない残差の大きさに応じて真ん中へ寄せます。1つの表の1回の結果だけで上位に来ないのはこのためで、代わりに誤差(±)が大きく出ます。"),
      h("li", {}, "空きセルの推定は、その分野の当てはめ(無ければ総合)をその表の目盛りに戻したもので、そのボードが実際に見た最小値と最大値の外には出しません。"),
      h("li", {}, "分野をまたぐ1本の軸は、現実の乱暴な要約です。GUI操作が得意でコーディングが苦手なモデルは1つの数では表せないので、分野別の数字も併記しています。")),
    h("h2", {}, "自己申告(† 付きの値)"),
    h("ul", {},
      h("li", {}, "どのボードにも載っていないモデル(例: Sakana Fugu)は、出した側が公表した数字を「自己申告」として別の層に置いています。マトリクスでは † 付きの別色で出し、押すと出した側・走らせ方・元の文書が見えます。"),
      h("li", {}, "自己申告もボードと同じ規律で扱います。元の文書を取得して機械的に取り出し、取り出した部分を保存し、どの表に対応づけてよいかを1件ずつ決めます(集合や走らせ方が分からないものは対応づけません)。"),
      h("li", {}, "自己申告は戦闘力の当てはめに入れません。ボードの数字と混ざることはありません。")),
    h("h2", {}, "読むときの注意"),
    h("ul", {},
      h("li", {}, "スコアはモデル単体の性質ではなく、モデルと足場(エージェント・試行回数・推論量)の組の性質です。同じモデルでも足場次第で大きく動きます。"),
      h("li", {}, "比べてよいのは同じ表の中だけです。別の表の数字は、同じベンチの名前が付いていても走らせ方が違います。"),
      h("li", {}, "各ボードの検証マーク・日付・提出者は、ボード自身が示しているものだけを写しています。自己申告の行も含まれます。"),
      h("li", {}, "モデル名はボードごとに表記が違うため、正規化したIDで束ねています。束ね方の誤りは Issue で教えてください。")),
    h("h2", {}, "更新のしかた"),
    h("p", {}, h("code", {}, "data/tables/<id>.json"), " を更新し、", h("code", {}, "almide run tools/build.almd"), " を走らせます。欠けた出典・形の崩れた日付・取得日より後の日付などがあれば、ページ用の ", h("code", {}, "docs/data.json"), " は書かれません。形式は ", link(`${REPO}/blob/main/DATA.md`, "DATA.md"), " にあります。")));
}

// ── boot ───────────────────────────────────────────────────────────────────
function stats() {
  const d = state.data;
  const rows = d.tables.reduce((n, t) => n + t.rows.length, 0);
  const saved = d.tables.filter(savedSource).length;
  const item = (label, value, sub, warn) => h("div", {}, h("span", {}, label), h("strong", {}, value), h("small", { class: warn ? "status-warn" : null }, sub));
  document.getElementById("stats").replaceChildren(
    item("収録モデル", state.modelIds.length.toLocaleString(), `開発元 ${new Set(state.modelIds.map((id) => state.models.get(id)?.vendor).filter(Boolean)).size} 組織`),
    item("リーダーボード", d.tables.length, `${new Set(d.tables.map((t) => t.family)).size} ベンチマーク · 取得できず ${d.gaps.length} 件`),
    item("掲載行(実測)", rows.toLocaleString(), `自己申告 ${(d.claims || []).reduce((n, c) => n + c.figures.length, 0)} 件は別の層`),
    item("最終取得", d.generated || "—", saved ? `最新未確認 ${saved} 表` : "すべて確認済み", saved > 0));
  const g = document.getElementById("generated");
  if (g) g.textContent = `取得日 ${d.generated || "—"}`;
}

// The top bar search narrows whichever list is on screen; elsewhere it opens the matrix.
function wireChrome() {
  const search = document.getElementById("global-search");
  if (search) search.addEventListener("change", () => {
    const { view, arg, params } = parseHash();
    const target = ["matrix", "ability", "table"].includes(view) ? view : "matrix";
    const p = target === view ? new URLSearchParams(params) : new URLSearchParams();
    const q = search.value.trim();
    if (q) p.set("q", q); else p.delete("q");
    setHash(target, target === view ? arg : null, p);
    render();
  });
  const toggle = document.getElementById("theme-toggle");
  if (toggle) toggle.addEventListener("click", () => {
    const root = document.documentElement;
    const dark = root.dataset.theme ? root.dataset.theme === "dark" : window.matchMedia?.("(prefers-color-scheme: dark)").matches;
    root.dataset.theme = dark ? "light" : "dark";
    try { localStorage.setItem("abm-theme", root.dataset.theme); } catch (e) { /* private mode: the choice lasts for this page only */ }
  });
  const overlay = document.getElementById("drawer-overlay");
  if (overlay) overlay.addEventListener("click", closeDrawer);
}

async function boot() {
  try {
    const res = await fetch("data.json", { cache: "no-cache" });
    if (!res.ok) throw new Error(res.status + " " + res.statusText);
    prepare(await res.json());
  } catch (e) {
    document.getElementById("view").replaceChildren(h("p", { class: "empty" }, "data.json を読めませんでした: " + e.message));
    return;
  }
  try {
    const res = await fetch("cost-data.json", { cache: "no-cache" });
    if (!res.ok) throw new Error(String(res.status));
    state.costData = await res.json();
  } catch (e) { state.costError = e.message; }
  try {
    const res = await fetch("runtime-data.json", { cache: "no-cache" });
    if (!res.ok) throw new Error(String(res.status));
    state.runtimeData = await res.json();
    state.runtimeModels = byModel(state.runtimeData);
  } catch (e) { state.runtimeError = e.message; }
  stats();
  wireChrome();
  document.getElementById("drawer-close").addEventListener("click", closeDrawer);
  document.addEventListener("keydown", (e) => { if (e.key === "Escape") closeDrawer(); });
  window.addEventListener("hashchange", render);
  let viewportWidth = window.innerWidth;
  window.addEventListener("resize", () => {
    if (window.innerWidth === viewportWidth) return;
    viewportWidth = window.innerWidth;
    if (parseHash().view === "cost") render();
  });
  render();
}
boot();
