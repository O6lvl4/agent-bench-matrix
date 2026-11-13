// Hosted inference (提供 = 配信元 × モデル): observed list prices, kept apart from
// benchmark scores and from the fit. A price is what one source showed on one date.
// Speed is not collected; the page says so instead of showing an empty column.

const REPO = "https://github.com/O6lvl4/agent-bench-matrix";

function h(tag, attrs, ...kids) {
  const el = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs || {})) {
    if (v === null || v === undefined || v === false) continue;
    if (k === "class") el.className = v;
    else if (k === "on") for (const [ev, fn] of Object.entries(v)) el.addEventListener(ev, fn);
    else el.setAttribute(k, v === true ? "" : String(v));
  }
  for (const kid of kids.flat(Infinity)) {
    if (kid === null || kid === undefined || kid === false) continue;
    el.append(kid instanceof Node ? kid : document.createTextNode(String(kid)));
  }
  return el;
}
function link(url, text) {
  if (typeof url !== "string" || !/^https?:\/\//.test(url)) return null;
  return h("a", { href: url, target: "_blank", rel: "noopener noreferrer" }, text);
}

export function usd(value) {
  if (typeof value !== "number" || !Number.isFinite(value)) return "—";
  if (value === 0) return "$0";
  return "$" + (value >= 10 ? value.toFixed(2) : value >= 0.1 ? value.toFixed(3).replace(/0$/, "") : value.toPrecision(2));
}
function context(value) {
  return typeof value === "number" && value > 0 ? value.toLocaleString("en-US") : "—";
}

/** Offerings grouped by registry model id, in the order the bundle lists them. */
export function byModel(data) {
  const map = new Map();
  for (const o of data?.offerings || []) {
    if (!map.has(o.model_id)) map.set(o.model_id, []);
    map.get(o.model_id).push(o);
  }
  return map;
}

export function renderRuntime(main, { data, models, ratingOf, params, navigate }) {
  const groups = byModel(data);
  const name = (id) => models.get(id)?.name || id;
  const ids = [...groups.keys()].sort((a, b) => (ratingOf(b)?.rating ?? -Infinity) - (ratingOf(a)?.rating ?? -Infinity) || name(a).localeCompare(name(b)));
  const sources = new Map(data.sources.map((s) => [s.id, s]));
  const requested = params.get("model");
  const current = groups.has(requested) ? requested : null;
  const sourceFilter = sources.has(params.get("source")) ? params.get("source") : "";
  const sort = ["input", "output", "provider"].includes(params.get("sort")) ? params.get("sort") : "input";
  const update = (patch) => {
    const p = new URLSearchParams(params);
    for (const [k, v] of Object.entries(patch)) { if (!v) p.delete(k); else p.set(k, v); }
    navigate(p);
  };

  main.append(h("div", { class: "page-heading" },
    h("div", {}, h("span", { class: "eyebrow" }, "実行環境ごとの観測"), h("h2", {}, "提供・料金"),
      h("p", {}, `配信元 × モデルの掲載単価。${groups.size} モデル・${data.offerings.length} 件 ・ 取得 ${String(data.retrieved).slice(0, 10)}`))));
  main.append(h("p", { class: "note" },
    h("strong", {}, "ベンチマークの数字ではありません。"),
    "各公開元が取得時点で掲載していた単価の写しで、単位は 100 万トークンあたりの米ドルです。公式の料金表から取った行と、OpenRouter が中継時に掲載している単価の行は、出どころが違うので列で区別しています。"));

  main.append(h("div", { class: "controls" },
    h("label", {}, "モデル", h("select", { id: "runtime-model", on: { change: (e) => update({ model: e.target.value }) } },
      h("option", { value: "", selected: !current }, "モデルを選ぶ"),
      ids.map((id) => h("option", { value: id, selected: id === current }, `${name(id)}(${groups.get(id).length} 件)`)))),
    current ? h("label", {}, "出どころ", h("select", { on: { change: (e) => update({ source: e.target.value }) } },
      h("option", { value: "", selected: !sourceFilter }, "すべて"),
      [...sources.values()].map((s) => h("option", { value: s.id, selected: s.id === sourceFilter }, s.name)))) : null,
    current ? h("label", {}, "並び", h("select", { on: { change: (e) => update({ sort: e.target.value === "input" ? "" : e.target.value }) } },
      h("option", { value: "input", selected: sort === "input" }, "入力単価の安い順"),
      h("option", { value: "output", selected: sort === "output" }, "出力単価の安い順"),
      h("option", { value: "provider", selected: sort === "provider" }, "配信元の名前順"))) : null));

  if (requested && !current) {
    main.append(h("div", { class: "runtime-empty" },
      h("strong", {}, `${name(requested)} の提供は記録にありません。`),
      h("p", {}, "取得した料金表にこのモデルと完全一致する名前の行がなかった、という意味です。どこも提供していないことを示すものではありません。")));
  }

  if (current) {
    const rows = groups.get(current).filter((o) => !sourceFilter || o.source_id === sourceFilter);
    const key = (o) => (sort === "provider" ? 0 : sort === "output" ? o.output_per_mtok ?? Infinity : o.input_per_mtok ?? Infinity);
    rows.sort((a, b) => key(a) - key(b) || a.provider.localeCompare(b.provider) || a.source_model.localeCompare(b.source_model));
    const m = models.get(current);
    const r = ratingOf(current);
    main.append(h("div", { class: "table-head" },
      h("h2", {}, name(current)),
      m?.vendor ? h("span", { class: "chip" }, `開発元 ${m.vendor}`) : null,
      h("span", { class: "chip" }, m?.open_weights === true ? "オープンウェイト" : m?.open_weights === false ? "重み非公開" : "重みの公開は未確認"),
      r ? h("span", { class: "chip", title: "実測から当てはめた推定。ボードの数字ではない" }, `戦闘力 ~${r.rating.toFixed(1)} ± ${r.se.toFixed(1)}`) : null,
      m?.open_weights === true ? h("a", { href: "#/cost?model=" + encodeURIComponent(current) }, "ローカルで動かす費用 →") : null));
    main.append(h("div", { class: "plain-wrap" }, h("table", { class: "plain runtime-table" },
      h("thead", {}, h("tr", {},
        h("th", {}, "配信元"), h("th", {}, "出どころ"),
        h("th", { class: "num" }, "入力"), h("th", { class: "num" }, "キャッシュ入力"), h("th", { class: "num" }, "出力"),
        h("th", { class: "num" }, "コンテキスト長"), h("th", {}, "量子化"), h("th", {}, "区分"), h("th", {}, "出典"))),
      h("tbody", {}, rows.map((o) => {
        const s = sources.get(o.source_id);
        return h("tr", {},
          h("td", {}, h("strong", {}, o.provider), h("div", { class: "muted mono runtime-id" }, o.source_model)),
          h("td", {}, h("span", { class: "pill" + (s.kind === "official" ? "" : " alternate"), title: s.note_ja }, s.kind === "official" ? "公式の料金表" : `${s.name} 経由`)),
          h("td", { class: "num" }, usd(o.input_per_mtok), o.tiered ? h("span", { class: "muted", title: "入力長などで単価が変わる。基本区分の単価" }, " *") : null),
          h("td", { class: "num" + (o.cached_input_per_mtok === null ? " muted" : "") }, usd(o.cached_input_per_mtok)),
          h("td", { class: "num" + (o.output_per_mtok === null ? " muted" : "") }, usd(o.output_per_mtok)),
          h("td", { class: "num" + (o.context_length ? "" : " muted"), title: o.context_length ? null : "この出どころは載せていない" }, context(o.context_length)),
          h("td", { class: o.quantization ? "mono" : "muted", title: o.quantization ? null : "記載なし" }, o.quantization || "—"),
          h("td", {}, [o.tier, o.region].filter(Boolean).join(" · ") || h("span", { class: "muted" }, "—")),
          h("td", {}, link(s.url, "料金ページ"), " ", link(`${REPO}/blob/main/${s.snapshot}`, "取得データ")));
      })))));
    main.append(h("p", { class: "muted runtime-count" },
      `${rows.length} 件。単位は USD / 100 万トークン。「—」はその出どころが値を載せていないことを示します。`,
      rows.some((o) => o.tiered) ? " * は入力長などで単価が変わる提供で、基本区分の単価です。" : ""));
  } else {
    main.append(h("div", { class: "plain-wrap" }, h("table", { class: "plain runtime-index" },
      h("thead", {}, h("tr", {},
        h("th", {}, "モデル"), h("th", { class: "num" }, "提供"), h("th", { class: "num" }, "配信元"),
        h("th", { class: "num", title: "掲載された入力単価の最小と最大" }, "入力単価の幅"), h("th", { class: "num", title: "掲載された出力単価の最小と最大" }, "出力単価の幅"),
        h("th", { class: "num", title: "実測から当てはめた推定" }, "戦闘力"))),
      h("tbody", {}, ids.map((id) => {
        const list = groups.get(id);
        const span = (field) => {
          const values = list.map((o) => o[field]).filter((v) => typeof v === "number");
          if (!values.length) return "—";
          const lo = Math.min(...values), hi = Math.max(...values);
          return lo === hi ? usd(lo) : `${usd(lo)} – ${usd(hi)}`;
        };
        const r = ratingOf(id);
        return h("tr", {},
          h("td", {}, h("a", { href: "#/runtime?model=" + encodeURIComponent(id) }, name(id)), models.get(id)?.vendor ? h("span", { class: "vendor" }, models.get(id).vendor) : null),
          h("td", { class: "num" }, list.length),
          h("td", { class: "num" }, new Set(list.map((o) => o.provider)).size),
          h("td", { class: "num" }, span("input_per_mtok")),
          h("td", { class: "num" }, span("output_per_mtok")),
          h("td", { class: "num" + (r ? " est" : " muted") }, r ? "~" + r.rating.toFixed(1) : "—"));
      })))));
    main.append(h("p", { class: "muted runtime-count" }, "単価の幅は、配信元・量子化・区分の違う提供をまとめた最小と最大です。同じ条件の比較は、モデルを選んで行ごとに見てください。"));
  }

  main.append(h("section", { class: "runtime-speed" },
    h("span", { class: "eyebrow" }, "観測 · 速度計測"),
    h("h3", {}, "速度はまだ取得できていません"),
    h("p", {}, data.speed?.reason_ja || "速度の観測はありません。"),
    h("p", { class: "muted" }, "速度はモデル単体の値ではなく、配信元・地域・負荷を含む「提供」に対する観測です。取得できるまで、推測の値は入れません。"),
    (data.speed?.tried || []).length ? h("ul", {}, data.speed.tried.map((u) => h("li", { class: "mono" }, u))) : null));

  main.append(h("section", { class: "runtime-sources" },
    h("span", { class: "eyebrow" }, "出典"),
    h("h3", {}, "料金の出どころ"),
    h("dl", {}, data.sources.map((s) => [
      h("dt", {}, s.name, " ", h("span", { class: "pill" + (s.kind === "official" ? "" : " alternate") }, s.kind === "official" ? "公式" : "中継事業者")),
      h("dd", {}, s.note_ja, " ", h("span", { class: "mono muted" }, `取得 ${s.retrieved_at}`), " ", link(s.url, "料金ページ"), " ", link(`${REPO}/blob/main/${s.snapshot}`, "取得データ"),
        data.unmatched?.[s.id]?.unmatched ? h("div", { class: "muted" }, `${data.unmatched[s.id].rows} 行のうち ${data.unmatched[s.id].unmatched} 行は、登録簿のモデルと名前が一致しなかったので載せていません。`) : null)])),
    h("ul", { class: "muted" }, (data.limitations_ja || []).map((t) => h("li", {}, t)))));
}
