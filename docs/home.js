// The designed front page (データ探索): the same sections and markup as the Figma
// Make design, filled from the real bundles. Nothing here invents a value: a
// section with no data says so, and speed is shown as not collected.

const SVG = "http://www.w3.org/2000/svg";
const ICONS = {
  book: [["path", { d: "M4 19.5A2.5 2.5 0 0 1 6.5 17H20" }], ["path", { d: "M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2Z" }]],
  server: [["rect", { x: 3, y: 4, width: 18, height: 6, rx: 2 }], ["rect", { x: 3, y: 14, width: 18, height: 6, rx: 2 }], ["path", { d: "M7 7h.01M7 17h.01" }]],
  chip: [["rect", { x: 6, y: 6, width: 12, height: 12, rx: 2 }], ["path", { d: "M9 1v3M15 1v3M9 20v3M15 20v3M20 9h3M20 14h3M1 9h3M1 14h3" }], ["rect", { x: 9, y: 9, width: 6, height: 6 }]],
  search: [["circle", { cx: 11, cy: 11, r: 7 }], ["path", { d: "m20 20-4-4" }]],
  sun: [["circle", { cx: 12, cy: 12, r: 4 }], ["path", { d: "M12 2v2M12 20v2M4.93 4.93l1.42 1.42M17.66 17.66l1.41 1.41M2 12h2M20 12h2M4.93 19.07l1.42-1.42M17.66 6.34l1.41-1.41" }]],
  moon: [["path", { d: "M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8Z" }]],
  external: [["path", { d: "M15 3h6v6M10 14 21 3" }], ["path", { d: "M18 13v7a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1V7a1 1 0 0 1 1-1h7" }]],
  chevron: [["path", { d: "m9 18 6-6-6-6" }]],
  check: [["path", { d: "m5 12 4 4L19 6" }]],
  warning: [["path", { d: "M10.3 3.7 2.2 18a2 2 0 0 0 1.7 3h16.2a2 2 0 0 0 1.7-3L13.7 3.7a2 2 0 0 0-3.4 0Z" }], ["path", { d: "M12 9v4M12 17h.01" }]],
  x: [["path", { d: "m6 6 12 12M18 6 6 18" }]],
  filter: [["path", { d: "M4 5h16M7 12h10M10 19h4" }]],
  info: [["circle", { cx: 12, cy: 12, r: 9 }], ["path", { d: "M12 11v5M12 8h.01" }]],
};
export function icon(name, size = 16) {
  const svg = document.createElementNS(SVG, "svg");
  for (const [k, v] of Object.entries({ width: size, height: size, viewBox: "0 0 24 24", fill: "none", stroke: "currentColor", "stroke-width": 1.7, "stroke-linecap": "round", "stroke-linejoin": "round", "aria-hidden": "true" })) svg.setAttribute(k, v);
  for (const [tag, attrs] of ICONS[name] || []) {
    const el = document.createElementNS(SVG, tag);
    for (const [k, v] of Object.entries(attrs)) el.setAttribute(k, v);
    svg.append(el);
  }
  return svg;
}

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
const btn = (attrs, ...kids) => h("button", { type: "button", ...attrs }, ...kids);
const squash = (s) => String(s || "").toLowerCase().replace(/[^a-z0-9]/g, "");
const day = (s) => String(s || "").slice(0, 10) || "—";
const usd = (v) => (typeof v !== "number" || !isFinite(v) ? "—" : "$" + (v >= 10 ? v.toFixed(2) : v >= 0.1 ? v.toFixed(3).replace(/0$/, "") : v === 0 ? "0" : v.toPrecision(2)));
const gib = (v) => (typeof v === "number" && isFinite(v) ? v.toFixed(1) : "—");
const yen = (v) => (typeof v === "number" && isFinite(v) ? "¥" + Math.round(v).toLocaleString("en-US") : "価格未確認");

// ── facts about one model, read off the rows that ran it alone ──────────────
function modelFacts(ctx, id) {
  const rows = [];
  for (const t of ctx.state.tables) for (const r of ctx.cellRows(id, t.id)) rows.push({ t, r });
  const configs = new Map();
  const systems = new Set();
  for (const { r } of rows) {
    const key = r.model_config || "";
    const sys = (r.agent || "") + "\u0000" + key;
    systems.add(sys);
    if (!configs.has(key)) configs.set(key, { config: key, systems: new Set(), rows: 0 });
    const c = configs.get(key);
    c.systems.add(sys);
    c.rows++;
  }
  const tables = [...new Set(rows.map((x) => x.t))];
  const anchor = tables.sort((a, b) => (ctx.fitOf(b)?.n || 0) - (ctx.fitOf(a)?.n || 0) || b.rows.length - a.rows.length)[0] || null;
  return { rows, systems, anchor, configs: [...configs.values()].sort((a, b) => b.systems.size - a.systems.size || b.rows - a.rows) };
}
function offersOf(ctx, id) {
  const data = ctx.state.runtimeData;
  if (!data) return [];
  const kind = new Map(data.sources.map((s) => [s.id, s]));
  return [...(ctx.state.runtimeModels.get(id) || [])]
    .map((o) => ({ ...o, source: kind.get(o.source_id) }))
    .sort((a, b) => (a.source?.kind === "official" ? 0 : 1) - (b.source?.kind === "official" ? 0 : 1) || a.input_per_mtok - b.input_per_mtok || a.provider.localeCompare(b.provider));
}
function localOf(ctx, id) {
  const cost = ctx.state.costData;
  const m = ctx.state.models.get(id);
  if (!cost) return { profile: null, reason: "費用データを読み込めていません。" };
  const profile = (cost.profiles || []).find((p) => p.model_id === id) || null;
  if (profile) {
    const hardware = (cost.hardware || []).map((hw) => {
      const offers = (cost.offers || []).filter((o) => o.hardware_id === hw.id).sort((a, b) => String(b.observed_at).localeCompare(String(a.observed_at)));
      return { hw, fit: ctx.candidateFit(profile, hw, 4096), offer: offers[0] || null };
    });
    return { profile, hardware };
  }
  const research = (cost.research_only || []).find((p) => p.model_id === id);
  return { profile: null, reason: m?.open_weights === false ? "重み非公開のため構成なし" : research ? "量子化配布物を検証できておらず、試算の対象外" : m?.open_weights === true ? "重みは公開されているが、配布物を未調査" : "重みの公開を確認できていない" };
}
const FIT = { roomy: ["yes", "余裕あり"], minimum: ["yes", "下限は収まる"], insufficient: ["near", "不足"], unsupported: ["near", "対象外"] };

function fetchState(ctx, t) {
  return ctx.savedSource(t)
    ? h("span", { class: "source-ok", style: "color:var(--warn)" }, icon("warning", 11), "最新未確認")
    : h("span", { class: "source-ok" }, icon("check", 11), "取得済み");
}
function benchName(ctx, family) {
  return ctx.state.byId.get(family)?.name || family || "—";
}
function speedMissing(ctx) {
  return h("div", { class: "speed-missing" },
    h("strong", {}, "未取得"),
    ctx.state.runtimeData?.speed?.reason_ja || "この組み合わせの公開された速度の観測はありません。空欄ではなく、未取得として扱います。");
}

// ── データ探索 ──────────────────────────────────────────────────────────────
export function renderHomeTop(root, ctx) {
  const { state, ui } = ctx;
  const id = ctx.selectedModel;
  const families = [...new Set(state.tables.map((t) => t.family).filter(Boolean))];
  const old = root.querySelector(".catalog-list");
  const previous = { view: old?.dataset.view, top: old?.scrollTop || 0 };
  root.replaceChildren(
    h("section", { class: "page-heading" },
      h("div", {},
        h("div", { class: "eyebrow" }, "公開ベンチマーク・カタログ"),
        h("h1", {}, "データ探索"),
        h("p", {}, "モデル、評価、実行環境の3つの入口から、観測値とその関係を辿ります。")),
      h("div", { class: "heading-actions" },
        btn({ class: "button secondary", "aria-expanded": ui.controls ? "true" : "false", on: { click: ctx.toggleControls } }, icon("filter", 15), "表示を調整"),
        h("a", { class: "button primary", href: "data.json", download: "agent-bench-matrix.json" }, "データを書き出す"))),
    h("section", { class: "domain-explorer", "aria-label": "データ集約の探索" },
      h("div", { class: "explorer-tabs" },
        h("div", {}, h("span", { class: "eyebrow" }, "探索の起点"), h("strong", {}, "何を中心に見ますか")),
        [["model", "chip", "モデルから", state.modelIds.length],
         ["evaluation", "book", "評価から", `${families.length} / ${state.tables.length}`],
         ["runtime", "server", "実行環境から", state.runtimeData ? state.runtimeData.offerings.length : "—"]].map(([key, ic, label, count]) =>
          btn({ class: ui.ex === key ? "active" : "", on: { click: () => ctx.setUi({ ex: key }) } }, icon(ic, 15), label, h("small", {}, count)))),
      ui.ex === "evaluation" ? evaluationView(ctx) : ui.ex === "runtime" ? runtimeView(ctx, id) : modelView(ctx, id),
      lineage(ctx)),
    summary(ctx));
  // A repaint rebuilds the list; put it back where the reader had scrolled it.
  const list = root.querySelector(".catalog-list");
  if (list && previous.view === ui.ex + ui.rt) list.scrollTop = previous.top;
}

function modelView(ctx, id) {
  const { state } = ctx;
  const m = state.models.get(id);
  if (!id) return h("div", { class: "home-empty" }, h("strong", {}, "モデルがありません"), "条件に合うモデルが読み込まれていません。");
  const facts = modelFacts(ctx, id);
  const offers = offersOf(ctx, id);
  const local = localOf(ctx, id);
  const vendor = m?.vendor || "";
  const roles = [vendor ? "開発元" : null,
    vendor && (state.runtimeData?.offerings || []).some((o) => squash(o.provider) === squash(vendor)) ? "配信元" : null,
    vendor && facts.rows.some(({ r }) => squash(r.org) === squash(vendor)) ? "提出者" : null].filter(Boolean);
  const t = facts.anchor;
  return h("div", { class: "catalog-view model-view" }, modelList(ctx, id), h("div", { class: "aggregate-layout" },
    h("article", { class: "aggregate-root" },
      h("div", { class: "entity-kicker" }, h("span", {}, "モデル"), h("code", {}, "model")),
      h("div", { class: "aggregate-model" },
        h("div", { class: "model-avatar" }, icon("chip", 19)),
        h("div", {},
          h("h2", {}, ctx.modelName(id)),
          h("p", {}, "開発元 ", h("a", { href: "#organization" }, vendor || "不明"),
            h("span", {}, m?.open_weights === true ? "オープンウェイト" : m?.open_weights === false ? "重み非公開" : "重みの公開は未確認"))),
        h("a", { class: "text-link", href: "#/ability?q=" + encodeURIComponent(ctx.modelName(id)) }, "戦闘力の内訳 ", icon("chevron", 13))),
      h("div", { class: "aggregate-relations" },
        btn({ on: { click: () => ctx.filterModel(id) } }, h("span", {}, "モデル設定"), h("b", {}, facts.configs.length), h("small", {}, "推論量を区別")),
        h("i", {}, icon("chevron", 12)),
        btn({ on: { click: () => ctx.filterModel(id) } }, h("span", {}, "システム"), h("b", {}, facts.systems.size), h("small", {}, "足場 × 設定")),
        h("i", {}, icon("chevron", 12)),
        btn({ on: { click: () => ctx.filterModel(id) } }, h("span", {}, "掲載行"), h("b", {}, facts.rows.length), h("small", {}, "実測の原票"))),
      facts.configs.length
        ? h("div", { class: "configuration-list" }, facts.configs.slice(0, 3).map((c) => h("div", {},
            h("span", { class: "tree-line" }),
            h("p", {}, h("small", {}, "モデル設定"), h("strong", { title: c.config || "ボードに設定の記載なし" }, `${ctx.modelName(id)} · ${c.config || "標準"}`), h("em", {}, `掲載行 ${c.rows}`)),
            h("b", {}, `システム ${c.systems.size}`))))
        : h("div", { class: "home-empty" }, "このモデル単体で走らせた掲載行はありません(自己申告だけのモデル)。"),
      h("div", { id: "organization", class: "organization-rolebar" },
        h("div", {}, h("span", {}, "組織"), h("strong", {}, vendor || "不明")),
        h("p", {}, roles.map((r) => h("span", {}, h("small", {}, "役割"), " ", r))),
        offers.length ? h("a", { class: "text-link", href: "#/runtime?model=" + encodeURIComponent(id) }, "提供を見る ", icon("chevron", 12)) : null)),
    h("article", { class: "aggregate-sides" },
      h("div", { class: "relation-block" },
        h("div", { class: "entity-kicker" }, h("span", {}, "評価での集約"), h("code", {}, "evaluation")),
        t ? [h("div", { class: "relation-path" },
               btn({ on: { click: () => ctx.setUi({ ex: "evaluation", b: t.family, lb: t.id }) } }, h("small", {}, "分野"), h("strong", {}, ctx.CATEGORY_NAMES[t.category] || t.category), h("em", {}, `${ctx.CATEGORY_ORDER.length}分野`)),
               icon("chevron", 12),
               btn({ on: { click: () => ctx.setUi({ ex: "evaluation", b: t.family, lb: t.id }) } }, h("small", {}, "ベンチマーク"), h("strong", {}, benchName(ctx, t.family)), h("em", {}, "何を測るか")),
               icon("chevron", 12),
               btn({ on: { click: () => ctx.setUi({ ex: "evaluation", b: t.family, lb: t.id }) } }, h("small", {}, "リーダーボード"), h("strong", {}, t.name), h("em", {}, "公開元・問題集合"))),
             h("div", { class: "relation-detail" },
               h("span", {}, "公開元 ", h("b", {}, t.board)),
               h("span", {}, "指標 ", h("b", {}, `${ctx.unitLabel(t.unit)} ${t.higher_is_better ? "↑" : "↓"}`)),
               h("span", {}, "取得日 ", h("b", {}, t.retrieved)),
               fetchState(ctx, t))]
          : h("div", { class: "home-empty" }, "実測のあるリーダーボードがありません。")),
      h("div", { class: "relation-block" },
        h("div", { class: "entity-kicker" }, h("span", {}, "実行環境での集約"), h("code", {}, "runtime")),
        h("div", { class: "runtime-branches" },
          btn({ disabled: offers.length === 0, on: { click: () => ctx.setUi({ ex: "runtime", rt: "offer", o: "" }) } },
            h("span", { class: "branch-icon" }, icon("server", 14)),
            h("p", {}, h("small", {}, "提供"), h("strong", {}, "配信元 × モデル"), h("em", {}, offers.length ? "料金・文脈長・量子化" : "料金表に一致する行なし")),
            h("b", {}, offers.length ? `${offers.length}件` : "なし")),
          btn({ disabled: !local.profile, on: { click: () => ctx.setUi({ ex: "runtime", rt: "local", o: "" }) } },
            h("span", { class: "branch-icon" }, icon("chip", 14)),
            h("p", {}, h("small", {}, "ローカル構成"), h("strong", {}, "重み × ハードウェア"), h("em", {}, local.profile ? "メモリ試算・販売価格" : local.reason)),
            h("b", {}, local.profile ? `${local.hardware.length}件` : "なし")))))));
}

// Every model on the page, strongest first, so the centre of the explorer can be
// picked from a list as in the other two entry points.
function modelList(ctx, current) {
  const { state, ui } = ctx;
  const needle = (ui.mq || "").toLowerCase();
  const rated = state.modelIds.map((id) => ({ id, m: state.models.get(id), r: ctx.ratingOf(id) }))
    .filter((x) => !needle || x.id.includes(needle) || (x.m?.name || "").toLowerCase().includes(needle) || (x.m?.vendor || "").toLowerCase().includes(needle))
    .sort((a, b) => (b.r?.rating ?? -Infinity) - (a.r?.rating ?? -Infinity) || ctx.modelName(a.id).localeCompare(ctx.modelName(b.id)));
  return h("aside", { class: "catalog-list", "data-view": ctx.ui.ex + ctx.ui.rt },
    h("div", { class: "catalog-search" }, icon("search", 14),
      h("input", { placeholder: "モデル、開発元を検索", value: ui.mq || "", "aria-label": "モデル、開発元を検索", on: { change: (e) => ctx.setUi({ mq: e.target.value.trim() }) } })),
    h("div", { class: "catalog-list-head" }, h("span", {}, `${rated.length} / ${state.modelIds.length}モデル · 戦闘力(推定)の高い順`)),
    rated.length ? rated.map((x) => btn({ class: "runtime-item model-item" + (x.id === current ? " active" : ""), "data-model": x.id, on: { click: () => ctx.setUi({ m: x.id }) } },
      h("span", { class: "provider-logo" }, icon("chip", 15)),
      h("p", {}, h("strong", {}, ctx.modelName(x.id)), h("small", {}, x.m?.vendor || "開発元不明")),
      h("span", {}, h("b", {}, x.r ? "~" + x.r.rating.toFixed(1) : "—"), h("small", {}, x.r ? `実測 ${x.r.n}` : "推定なし")),
      icon("chevron", 12)))
      : h("div", { class: "home-empty" }, "条件に合うモデルがありません。"));
}

function evaluationView(ctx) {
  const { state, ui } = ctx;
  const byFamily = new Map();
  for (const t of state.tables) {
    if (!byFamily.has(t.family)) byFamily.set(t.family, []);
    byFamily.get(t.family).push(t);
  }
  const needle = (ui.cq || "").toLowerCase();
  const family = byFamily.has(ui.b) ? ui.b : state.tables[0]?.family;
  const tables = byFamily.get(family) || [];
  const current = tables.find((t) => t.id === ui.lb) || tables[0];
  const category = tables[0]?.category;
  const st = current ? ctx.fitOf(current) : null;
  const list = h("aside", { class: "catalog-list", "data-view": ctx.ui.ex + ctx.ui.rt },
    h("div", { class: "catalog-search" }, icon("search", 14),
      h("input", { placeholder: "ベンチマークを検索", value: ui.cq || "", "aria-label": "ベンチマークを検索", on: { change: (e) => ctx.setUi({ cq: e.target.value.trim() }) } })),
    h("div", { class: "catalog-list-head" }, h("span", {}, `${ctx.CATEGORY_ORDER.filter((c) => state.tables.some((t) => t.category === c)).length}分野 · ${byFamily.size}ベンチマーク`)),
    ctx.CATEGORY_ORDER.map((c) => {
      const fams = [...byFamily.entries()].filter(([f, ts]) => ts[0].category === c && (!needle || benchName(ctx, f).toLowerCase().includes(needle) || String(f).toLowerCase().includes(needle)));
      if (!fams.length) return null;
      const open = c === category || Boolean(needle);
      return h("div", { class: "benchmark-group" },
        btn({ class: "benchmark-group-title", "aria-expanded": open ? "true" : "false", on: { click: () => ctx.setUi({ b: fams[0][0], lb: "" }) } },
          icon("chevron", 11), h("strong", {}, ctx.CATEGORY_NAMES[c]), h("span", {}, fams.length)),
        open ? fams.map(([f, ts]) => btn({ class: "benchmark-item" + (f === family ? " active" : ""), on: { click: () => ctx.setUi({ b: f, lb: "" }) } },
          h("span", { class: "catalog-node" }),
          h("p", {}, h("strong", {}, benchName(ctx, f)), h("small", {}, `リーダーボード ${ts.length}件`)),
          h("span", { class: "catalog-state " + (ts.some(ctx.savedSource) ? "old" : "ok") }))) : null);
    }));
  if (!current) return h("div", { class: "catalog-view evaluation-view" }, list, h("article", { class: "catalog-detail" }, h("div", { class: "home-empty" }, "リーダーボードがありません。")));
  return h("div", { class: "catalog-view evaluation-view" }, list,
    h("article", { class: "catalog-detail" },
      h("div", { class: "catalog-breadcrumb" }, h("span", {}, `分野: ${ctx.CATEGORY_NAMES[category] || category}`), icon("chevron", 11), h("span", {}, "ベンチマーク")),
      h("div", { class: "catalog-detail-head" },
        h("div", {}, h("span", { class: "entity-type" }, "ベンチマーク"), h("h2", {}, benchName(ctx, family)),
          h("p", {}, current.measures_ja, " 同じ課題名でも、問題集合や公開元が異なる表は別のリーダーボードです。")),
        h("div", { class: "catalog-stats" },
          h("span", {}, "所属分野 ", h("b", {}, ctx.CATEGORY_NAMES[category] || category)),
          h("span", {}, "リーダーボード ", h("b", {}, tables.length)),
          h("span", {}, "掲載行 ", h("b", {}, tables.reduce((n, t) => n + t.rows.length, 0).toLocaleString("en-US"))))),
      h("div", { class: "subentity-heading" },
        h("div", {}, h("span", { class: "eyebrow" }, "子エンティティ"), h("h3", {}, "リーダーボード")),
        h("div", { class: "status-key" },
          h("span", {}, h("i", { class: "catalog-state ok" }), "取得済み"),
          h("span", {}, h("i", { class: "catalog-state old" }), "最新未確認"))),
      h("div", { class: "leaderboard-list" }, tables.map((t) => {
        const f = ctx.fitOf(t);
        return btn({ class: t.id === current.id ? "active" : "", on: { click: () => ctx.setUi({ b: family, lb: t.id }) } },
          h("div", { class: "leaderboard-name" }, h("span", { class: "catalog-state " + (ctx.savedSource(t) ? "old" : "ok") }),
            h("p", {}, h("strong", {}, t.name), h("small", {}, `公開元: ${t.board}`))),
          h("div", {}, h("small", {}, "指標"), h("b", {}, `${ctx.unitLabel(t.unit)} ${t.higher_is_better ? "↑" : "↓"}`)),
          h("div", {}, h("small", {}, "掲載行"), h("b", {}, t.rows.length)),
          h("div", {}, h("small", {}, "実測モデル"), h("b", {}, f ? f.n : "3未満")),
          f ? h("span", { class: "fit yes" }, "当てはめ採用") : h("span", { class: "fit near" }, "除外: 3未満"),
          icon("chevron", 13));
      })),
      h("div", { class: "selected-leaderboard" },
        h("div", {}, h("span", { class: "entity-type" }, "選択中のリーダーボード"), h("strong", {}, current.name)),
        h("div", { class: "leaderboard-property" },
          h("span", {}, "水準 ", h("b", {}, st ? st.b.toFixed(2) : "—")),
          h("span", {}, "広がり ", h("b", {}, st ? st.s.toFixed(2) : "—")),
          h("span", {}, "観測範囲 ", h("b", {}, st ? `${ctx.fmtScore(st.lo, current.unit)}–${ctx.fmtScore(st.hi, current.unit)}` : "—")),
          h("span", {}, "取得日 ", h("b", {}, current.retrieved))),
        h("a", { class: "button secondary", href: "#/table/" + encodeURIComponent(current.id) }, `掲載行 ${current.rows.length}件を見る`)),
      ctx.sourceStatus(current)));
}

function runtimeView(ctx, id) {
  const { ui } = ctx;
  const offers = offersOf(ctx, id);
  const local = localOf(ctx, id);
  const mode = ui.rt === "local" ? "local" : "offer";
  const index = Math.min(Math.max(parseInt(ui.o || "0", 10) || 0, 0), Math.max((mode === "offer" ? offers.length : local.hardware?.length || 0) - 1, 0));
  const list = h("aside", { class: "catalog-list", "data-view": ctx.ui.ex + ctx.ui.rt },
    h("div", { class: "runtime-switch" },
      btn({ class: mode === "offer" ? "active" : "", on: { click: () => ctx.setUi({ rt: "offer", o: "" }) } }, icon("server", 13), "提供 ", h("b", {}, offers.length)),
      btn({ class: mode === "local" ? "active" : "", on: { click: () => ctx.setUi({ rt: "local", o: "" }) } }, icon("chip", 13), "ローカル構成 ", h("b", {}, local.hardware?.length || 0))),
    h("div", { class: "catalog-list-head" }, h("span", {}, mode === "offer" ? `${ctx.modelName(id)} · 配信元 × モデル` : `${ctx.modelName(id)} · 重みファイル × ハードウェア`)),
    mode === "offer"
      ? offers.map((o, i) => btn({ class: "runtime-item" + (i === index ? " active" : ""), on: { click: () => ctx.setUi({ o: String(i) }) } },
          h("span", { class: "provider-logo" }, icon("server", 15)),
          h("p", {}, h("strong", {}, o.provider), h("small", {}, o.source?.kind === "official" ? "公式の料金表" : `${o.source?.name} 経由`)),
          h("span", {}, h("b", {}, usd(o.input_per_mtok)), h("small", {}, "未計測")),
          icon("chevron", 12)))
      : (local.hardware || []).map((x, i) => btn({ class: "runtime-item local-item" + (i === index ? " active" : ""), on: { click: () => ctx.setUi({ o: String(i) }) } },
          h("span", { class: "provider-logo" }, icon("chip", 15)),
          h("p", {}, h("strong", {}, x.hw.name), h("small", {}, `${local.profile.artifact?.quantization || ""} · ${x.hw.memory_gib} GiB`)),
          h("span", {}, h("b", { class: FIT[x.fit.status][0] === "yes" ? "good" : "warning" }, FIT[x.fit.status][1]), h("small", {}, x.fit.memory ? `${gib(x.fit.memory.minimumGiB)} GiB` : "—")),
          icon("chevron", 12))));
  let detail;
  if (mode === "offer") {
    const o = offers[index];
    detail = !o
      ? h("div", { class: "home-empty" }, h("strong", {}, `${ctx.modelName(id)} の提供は記録にありません`), "取得した料金表に、このモデルと名前が完全一致する行がなかったという意味です。どこも提供していないことを示すものではありません。")
      : [h("div", { class: "catalog-breadcrumb" }, h("span", {}, "提供"), icon("chevron", 11), h("span", {}, o.provider), icon("chevron", 11), h("span", {}, ctx.modelName(id))),
         h("div", { class: "offer-detail-head" },
           h("div", { class: "provider-logo large" }, icon("server", 21)),
           h("div", {}, h("span", { class: "entity-type" }, "提供 · 配信元 × モデル"), h("h2", {}, `${o.provider} × ${ctx.modelName(id)}`),
             h("p", {}, `配信元 ${o.provider} · 開発元 ${ctx.state.models.get(id)?.vendor || "不明"} · ${o.source_model}`)),
           h("span", { class: "pill" }, "トークン従量")),
         h("div", { class: "offer-properties" },
           h("div", {}, h("span", {}, "コンテキスト長"), h("b", {}, o.context_length ? o.context_length.toLocaleString("en-US") : "—"), h("small", {}, o.context_length ? "トークン" : "出どころに記載なし")),
           h("div", {}, h("span", {}, "量子化"), h("b", {}, o.quantization || "—"), h("small", {}, o.quantization ? "配信元表記" : "記載なし")),
           h("div", {}, h("span", {}, "区分・地域"), h("b", {}, [o.tier, o.region].filter(Boolean).join(" · ") || "—"), h("small", {}, o.tiered ? "入力長で単価が変わる" : "基本区分")),
           h("div", {}, h("span", {}, "出どころ"), h("b", {}, o.source?.kind === "official" ? "公式の料金表" : `${o.source?.name} 経由`), h("small", {}, `取得 ${day(o.source?.retrieved_at)}`))),
         h("div", { class: "observation-section" },
           h("div", { class: "subentity-heading" }, h("div", {}, h("span", { class: "eyebrow" }, "観測"), h("h3", {}, "API料金")), h("span", { class: "observation-rule" }, "料金体系内でのみ比較")),
           h("div", { class: "price-observation" },
             h("div", {}, h("span", {}, "入力"), h("strong", {}, usd(o.input_per_mtok)), h("small", {}, "/ 100万トークン", o.cached_input_per_mtok !== null ? ` · キャッシュ ${usd(o.cached_input_per_mtok)}` : "")),
             h("div", {}, h("span", {}, "出力"), h("strong", {}, usd(o.output_per_mtok)), h("small", {}, "/ 100万トークン")),
             h("div", { class: "observation-source" }, h("span", {}, "出典"),
               ctx.link(o.source?.url, [`${o.source?.name} 料金 `, icon("external", 11)]), h("small", {}, `取得日 ${day(o.source?.retrieved_at)}`)))),
         h("div", { class: "observation-section" },
           h("div", { class: "subentity-heading" }, h("div", {}, h("span", { class: "eyebrow" }, "観測"), h("h3", {}, "速度計測")), h("span", { class: "observation-rule" }, "提供に紐づく値")),
           speedMissing(ctx)),
         h("div", { class: "runtime-note" }, icon("info", 14),
           h("p", {}, h("strong", {}, "モデル単体の速度ではありません"), h("span", {}, "速度は配信元、地域、負荷、計測条件を含む「提供」に対する観測です。取得できるまで値は入れません。")))];
  } else {
    const x = local.hardware?.[index];
    const mem = x?.fit.memory;
    const a = local.profile?.artifact || {};
    detail = !x
      ? h("div", { class: "home-empty" }, h("strong", {}, `${ctx.modelName(id)} のローカル構成はありません`), local.reason)
      : [h("div", { class: "catalog-breadcrumb" }, h("span", {}, "ローカル構成"), icon("chevron", 11), h("span", {}, a.filename || ctx.modelName(id)), icon("chevron", 11), h("span", {}, x.hw.name)),
         h("div", { class: "offer-detail-head" },
           h("div", { class: "provider-logo large" }, icon("chip", 21)),
           h("div", {}, h("span", { class: "entity-type" }, "ローカル構成 · 重み × ハードウェア"), h("h2", {}, `${ctx.modelName(id)} × ${x.hw.name}`),
             h("p", {}, `重み ${a.quantization || "—"} · ${x.hw.kind === "gpu" ? "単体GPU" : "PC一式"} · ${x.hw.runtime}`)),
           h("span", { class: "fit " + FIT[x.fit.status][0] }, FIT[x.fit.status][1])),
         h("div", { class: "local-entities" },
           h("div", {}, h("span", { class: "entity-type" }, "重みファイル"), h("strong", {}, a.filename || "—"),
             h("p", {}, `量子化 ${a.quantization || "—"} · ${gib(a.gib)} GiB · 配布元 ${a.repository || "—"}`),
             ctx.link(a.url, [`配布出典 · ${day(a.retrieved_at_utc)} `, icon("external", 11)])),
           icon("chevron", 13),
           h("div", {}, h("span", { class: "entity-type" }, "ハードウェア"), h("strong", {}, x.hw.name),
             h("p", {}, `メモリ ${x.hw.memory_gib} GiB · ${x.hw.kind === "gpu" ? "単体GPU" : "統合メモリ機"} · 利用可能 ${gib(x.fit.availableGiB)} GiB`),
             ctx.link(x.offer?.url, [`販売店出典 · ${day(x.offer?.observed_at)} `, icon("external", 11)]))),
         h("div", { class: "observation-section" },
           h("div", { class: "subentity-heading" }, h("div", {}, h("span", { class: "eyebrow" }, "導出"), h("h3", {}, "メモリ試算")), h("span", { class: "observation-rule" }, "ローカル構成に紐づく値")),
           mem ? h("div", { class: "local-memory-detail" },
             h("div", {}, h("span", {}, "必要メモリ(下限)"), h("strong", {}, `${gib(mem.minimumGiB)} GiB`),
               h("small", {}, `利用可能 ${gib(x.fit.availableGiB)} GiB · ` + (x.fit.availableGiB >= mem.minimumGiB ? `${gib(x.fit.availableGiB - mem.minimumGiB)} GiB の空き` : `${gib(mem.minimumGiB - x.fit.availableGiB)} GiB 不足`))),
             h("div", { class: "memory-breakdown" },
               h("span", { style: `width:${(mem.weightsGiB / mem.minimumGiB * 100).toFixed(1)}%` }, `重み ${gib(mem.weightsGiB)}`),
               h("span", { style: `width:${(mem.kvGiB / mem.minimumGiB * 100).toFixed(1)}%` }, `KV ${gib(mem.kvGiB)}`),
               h("span", { style: `width:${((mem.minimumGiB - mem.weightsGiB - mem.kvGiB) / mem.minimumGiB * 100).toFixed(1)}%` }, `実行・余白 ${gib(mem.minimumGiB - mem.weightsGiB - mem.kvGiB)}`)),
             h("p", {}, "コンテキスト 4,096 · 同時実行 1 · 実行用 2 GiB と余白 10% は仮定。実測ではありません。"))
             : h("div", { class: "home-empty" }, "この組み合わせは試算できません(実行環境が対応していない、または設定値が不足)。")),
         h("div", { class: "local-observation-grid" },
           h("div", { class: "observation-section" },
             h("div", { class: "subentity-heading" }, h("div", {}, h("span", { class: "eyebrow" }, "観測"), h("h3", {}, "販売価格"))),
             h("strong", {}, yen(x.offer?.price_jpy)),
             h("span", {}, x.offer ? `${x.offer.availability_label_ja || ""} · ${x.offer.seller || ""}` : "販売価格の観測なし"),
             ctx.link(x.offer?.url, [`販売店出典 · ${day(x.offer?.observed_at)} `, icon("external", 11)])),
           h("div", { class: "observation-section" },
             h("div", { class: "subentity-heading" }, h("div", {}, h("span", { class: "eyebrow" }, "観測"), h("h3", {}, "速度計測"))),
             h("strong", {}, "未計測"),
             h("span", {}, "この構成の公開された速度の観測なし"),
             h("a", { href: `#/cost?model=${encodeURIComponent(id)}&hardware=${encodeURIComponent(x.hw.id)}` }, "詳しく試算する ", icon("chevron", 11)))),
         h("div", { class: "runtime-note" }, icon("info", 14),
           h("p", {}, h("strong", {}, "価格はハードウェアの観測です"), h("span", {}, "モデルや重みの価格ではありません。在庫と観測日を伴う販売価格として記録しています。")))];
  }
  return h("div", { class: "catalog-view runtime-view" }, list, h("article", { class: "catalog-detail" }, detail));
}

function lineage(ctx) {
  const { state } = ctx;
  const d = state.data;
  const cost = state.costData;
  const n = (v) => (typeof v === "number" ? v.toLocaleString("en-US") : "—");
  const go = (hash) => ({ click: () => ctx.goto(hash) });
  const profiles = cost?.profiles?.length || 0;
  return h("div", { class: "data-lineage" },
    h("div", { class: "lineage-label" }, h("span", { class: "eyebrow" }, "数字の系譜"), h("strong", {}, "観測と導出を分離")),
    h("div", { class: "lineage-group observed" },
      h("span", {}, "出典のある観測"),
      btn({ on: go("#/table") }, "掲載行 ", h("b", {}, n(d.tables.reduce((s, t) => s + t.rows.length, 0)))),
      btn({ on: go("#/claims") }, "自己申告 ", h("b", {}, n((d.claims || []).reduce((s, c) => s + c.figures.length, 0)))),
      btn({ on: go("#/gaps"), title: "取得できた表と、取得できなかった表" }, "取得確認 ", h("b", {}, n(d.tables.length + (d.gaps || []).length))),
      btn({ on: go("#/runtime") }, "API料金 ", h("b", {}, state.runtimeData ? n(state.runtimeData.offerings.length) : "—")),
      btn({ on: go("#/cost") }, "販売価格 ", h("b", {}, cost ? n((cost.offers || []).length) : "—")),
      btn({ on: go("#/runtime"), title: "認証なしで取得できる公開元がなく、未取得" }, "速度計測 ", h("b", {}, "0"))),
    icon("chevron", 14),
    h("div", { class: "lineage-group derived" },
      h("span", {}, "観測からの導出"),
      btn({ on: { click: ctx.scrollToMatrix } }, "セル値 ", h("b", {}, n(state.cells.size + state.claims.size))),
      btn({ on: go("#/ability") }, "戦闘力 ", h("b", {}, n(Object.values(d.fit || {}).reduce((s, f) => s + Object.keys(f.models || {}).length, 0)))),
      btn({ on: go("#/cost") }, "メモリ試算 ", h("b", {}, cost ? n(profiles * (cost.hardware || []).length) : "—"))));
}

function summary(ctx) {
  const { state } = ctx;
  const d = state.data;
  const saved = d.tables.filter(ctx.savedSource).length;
  return h("section", { class: "summary-strip", "aria-label": "データ概要" },
    h("div", {}, h("span", {}, "収録モデル"), h("strong", {}, state.modelIds.length.toLocaleString("en-US")),
      h("small", {}, `開発元 ${new Set(state.modelIds.map((id) => state.models.get(id)?.vendor).filter(Boolean)).size}組織`)),
    h("div", {}, h("span", {}, "リーダーボード"), h("strong", {}, d.tables.length), h("small", {}, `${new Set(d.tables.map((t) => t.family)).size}ベンチマーク`)),
    h("div", {}, h("span", {}, "実測掲載行"), h("strong", {}, d.tables.reduce((s, t) => s + t.rows.length, 0).toLocaleString("en-US")), h("small", {}, "出典確認済み")),
    h("div", {}, h("span", {}, "最新取得"), h("strong", {}, d.generated || "—"),
      h("small", { class: "status-ok", style: saved ? "color:var(--warn)" : null }, h("i", { style: saved ? "background:var(--warn)" : null }), saved ? `最新未確認 ${saved}表` : "正常")));
}

// ── 戦闘力・取得状況・提供・ローカル構成 ───────────────────────────────────
export function renderHomeBottom(root, ctx) {
  const { state } = ctx;
  const id = ctx.selectedModel;
  const d = state.data;
  const m = state.models.get(id);
  const overall = id ? ctx.ratingOf(id) : null;
  const scopes = ctx.CATEGORY_ORDER.map((c) => ({ c, r: id ? ctx.ratingOf(id, c) : null })).filter((x) => x.r).sort((a, b) => b.r.rating - a.r.rating);
  const meta = m ? `${m.vendor || "開発元不明"} · ${m.open_weights === true ? "オープンウェイト" : m.open_weights === false ? "重み非公開" : "重みの公開は未確認"}` : "";
  const saved = d.tables.filter(ctx.savedSource);
  const gaps = d.gaps || [];
  const excluded = d.tables.filter((t) => !ctx.fitOf(t));
  const total = d.tables.length + gaps.length;
  const offers = id ? offersOf(ctx, id) : [];
  const local = id ? localOf(ctx, id) : { profile: null, reason: "" };
  const roomy = local.profile ? local.hardware.find((x) => x.fit.memory)?.fit.memory : null;

  root.replaceChildren(
    h("section", { id: "power", class: "section-grid" },
      h("div", { class: "panel power-panel" },
        h("div", { class: "panel-title" },
          h("div", {}, h("span", { class: "eyebrow" }, "推定指標"), h("h2", {}, "分野別の戦闘力")),
          h("a", { class: "text-link", href: "#/about" }, "算出方法 ", icon("chevron", 13))),
        id ? h("div", { class: "power-feature" },
          h("div", { class: "model-avatar" }, icon("chip", 19)),
          h("div", {}, h("strong", {}, ctx.modelName(id)), h("span", {}, meta)),
          h("div", { class: "feature-score" }, h("b", {}, overall ? "~" + overall.rating.toFixed(1) : "—"),
            h("span", {}, overall ? `± ${overall.se.toFixed(1)} · 実測 ${overall.n}` : "当てはめに入る実測なし"))) : null,
        scopes.length
          ? h("div", { class: "bar-chart" }, scopes.map(({ c, r }) => h("div", { class: "bar-row" },
              h("span", {}, ctx.CATEGORY_NAMES[c]),
              h("div", { class: "bar-track", title: `${r.rating.toFixed(1)} ± ${r.se.toFixed(1)}` },
                h("i", { style: `width:${Math.min(100, Math.max(0, r.rating)).toFixed(1)}%` }),
                h("em", { style: `left:${Math.min(100, Math.max(0, r.rating - r.se)).toFixed(1)}%;width:${Math.max(0.6, Math.min(100, 2 * r.se)).toFixed(1)}%` })),
              h("b", {}, "~" + r.rating.toFixed(0)),
              h("small", {}, `± ${r.se.toFixed(1)} · ${r.n}件`))))
          : h("div", { class: "home-empty" }, "分野別の当てはめに入る実測がありません。"),
        h("p", { class: "method-note" }, icon("info", 14), "各分野は独立に当てはめています。分野間の数値を同じ軸として比較することはできません。")),
      h("div", { id: "quality", class: "panel quality-panel" },
        h("div", { class: "panel-title" },
          h("div", {}, h("span", { class: "eyebrow" }, "透明性"), h("h2", {}, "取得と採用状況")),
          h("span", { class: "update-time" }, d.generated || "")),
        h("div", { class: "quality-list" },
          h("div", {}, h("span", { class: "quality-icon ok" }, icon("check", 14)),
            h("p", {}, h("strong", {}, "取得済み"), h("small", {}, `${d.tables.length} リーダーボード`)), h("b", {}, total ? (d.tables.length / total * 100).toFixed(1) + "%" : "—")),
          h("div", {}, h("span", { class: "quality-icon failed" }, icon("x", 14)),
            h("p", {}, h("strong", {}, "取得できなかった"), h("small", {}, gaps.length ? `${gaps[0].name}${gaps.length > 1 ? ` ほか ${gaps.length - 1}件` : ""}` : "なし")), h("b", {}, `${gaps.length}件`)),
          h("div", {}, h("span", { class: "quality-icon old" }, icon("warning", 14)),
            h("p", {}, h("strong", {}, "最新未確認"), h("small", {}, saved.length ? `${saved[0].name}${saved.length > 1 ? ` ほか ${saved.length - 1}件` : ""}` : "なし")), h("b", {}, `${saved.length}件`))),
        excluded.length ? h("div", { class: "excluded" },
          h("span", { class: "excluded-label" }, `当てはめから除外 · ${excluded.length}件`),
          h("strong", {}, excluded[0].name),
          h("p", {}, "実測が3モデルに満たないため、順位を語るのに十分ではありません。"),
          h("a", { href: "#/table/" + encodeURIComponent(excluded[0].id) }, "出典・掲載行を見る ", icon("external", 12))) : null)),

    h("section", { id: "offers", class: "panel offers-panel" },
      h("div", { class: "panel-title" },
        h("div", {}, h("span", { class: "eyebrow" }, "実行環境ごとの観測"), h("h2", {}, "提供・料金・速度")),
        offers.length
          ? h("a", { class: "subtle", href: "#/runtime?model=" + encodeURIComponent(id) }, `${ctx.modelName(id)} の提供 ${offers.length}件をすべて見る`)
          : h("span", { class: "subtle" }, id ? `${ctx.modelName(id)} の提供` : "")),
      offers.length
        ? h("div", { class: "offers-grid" }, offers.slice(0, 3).map((o) => h("article", {},
            h("div", { class: "offer-head" },
              h("div", { class: "provider-logo" }, icon("server", 15)),
              h("div", {}, h("strong", {}, o.provider), h("span", {}, `${o.source?.kind === "official" ? "公式の料金表" : `${o.source?.name} 経由`} · トークン従量`)),
              h("span", { class: "pill" + (o.source?.kind === "official" ? "" : " alternate") }, "従量")),
            h("div", { class: "offer-metrics" },
              h("div", {}, h("span", {}, "入力 / 100万トークン"), h("b", {}, usd(o.input_per_mtok))),
              h("div", {}, h("span", {}, "出力 / 100万トークン"), h("b", {}, usd(o.output_per_mtok))),
              h("div", {}, h("span", {}, "速度"), h("b", { class: "none-text" }, "未計測"), h("em", {}, "実行環境の観測なし"))),
            ctx.link(o.source?.url, [`出典 · ${day(o.source?.retrieved_at)} `, icon("external", 12)]))))
        : h("div", { class: "home-empty" }, h("strong", {}, "提供の記録なし"), state.runtimeData ? "取得した料金表に、このモデルと名前が完全一致する行がありません。" : "料金データを読み込めていません。"),
      h("p", { class: "comparison-warning" }, icon("warning", 14),
        "公式の料金表と中継事業者経由の単価は出どころが異なるため、単一の単価順位にはしていません。速度は認証なしで取得できる公開元がなく、未取得です。")),

    h("section", { id: "local", class: "panel local-panel" },
      h("div", { class: "panel-title" },
        h("div", {}, h("span", { class: "eyebrow" }, "ローカル構成"), h("h2", {}, "自分のマシンで動かす")),
        h("span", { class: "subtle" }, local.profile ? `${ctx.modelName(id)} · 量子化 ${local.profile.artifact?.quantization || "—"}` : id ? ctx.modelName(id) : "")),
      local.profile && roomy
        ? h("div", { class: "local-layout" },
            h("div", { class: "memory-card" },
              h("span", {}, "メモリ試算(下限)"),
              h("strong", {}, gib(roomy.minimumGiB), " ", h("small", {}, "GiB")),
              h("div", { class: "memory-bar" },
                h("i", { style: `width:${(roomy.weightsGiB / roomy.minimumGiB * 100).toFixed(1)}%` }),
                h("i", { style: `width:${(roomy.kvGiB / roomy.minimumGiB * 100).toFixed(1)}%` }),
                h("i", { style: `width:${((roomy.minimumGiB - roomy.weightsGiB - roomy.kvGiB) / roomy.minimumGiB * 100).toFixed(1)}%` })),
              h("div", { class: "memory-legend" },
                h("span", {}, h("i", {}), `重み ${gib(roomy.weightsGiB)} GiB`),
                h("span", {}, h("i", {}), `KV ${gib(roomy.kvGiB)} GiB`),
                h("span", {}, h("i", {}), `実行・余白 ${gib(roomy.minimumGiB - roomy.weightsGiB - roomy.kvGiB)} GiB`))),
            h("div", { class: "hardware-list" }, local.hardware.slice(0, 4).map((x) => h("div", {},
              h("strong", {}, x.hw.name),
              h("span", { class: "fit " + FIT[x.fit.status][0] }, FIT[x.fit.status][1]),
              h("p", {}, x.fit.memory ? `利用可能 ${gib(x.fit.availableGiB)} GiB · ${x.hw.kind === "gpu" ? "単体GPU" : "統合メモリ"}` : "この実行環境は対象外"),
              h("b", {}, yen(x.offer?.price_jpy)),
              ctx.link(x.offer?.url, [`価格出典 · ${day(x.offer?.observed_at)} `, icon("external", 12)]) || h("a", { href: "#/cost?model=" + encodeURIComponent(id) }, "試算を見る")))))
        : h("div", { class: "home-empty" }, h("strong", {}, "ローカル構成なし"), local.reason, " ",
            h("a", { href: "#/cost", style: "color:var(--accent);font-weight:600" }, "試算できるモデルを見る →"))));
}
