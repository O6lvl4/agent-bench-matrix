// Local inference costs: estimates and observed prices never masquerade as measurements.
// Keep this module independent of app.js so the numerical model can be unit tested.
const GIB = 2 ** 30;
const MAX_CONTEXT = 32768;
const DEFAULTS = { context: 4096, watts: 300, hours: 2, days: 30, rate: 31 };
const number = (value) => (typeof value === "number" && Number.isFinite(value) ? value : null);
const within = (value, min, max) => number(value) !== null && value >= min && value <= max;

/** Single-sequence f16 KV cache. This is a capacity estimate, not measured allocation. */
export function computeMemory(profile, context) {
  const bytes = profile?.artifact?.bytes;
  const config = profile?.config;
  if (!within(bytes, 1, Number.MAX_SAFE_INTEGER) || !within(context, 1, MAX_CONTEXT) || !Number.isInteger(context)) return null;
  if (!config || ![config.layers, config.kv_heads, config.head_dim].every((n) => within(n, 1, 100000) && Number.isInteger(n))) return null;
  const limit = profile.max_context ?? config.max_context ?? config.max_position_embeddings_config;
  if (number(limit) !== null && context > limit) return null;
  const weightsGiB = bytes / GIB;
  // 2 (key and value) × 2 bytes (f16) × layers × KV heads × head dimension × tokens.
  const kvGiB = (2 * 2 * config.layers * config.kv_heads * config.head_dim * context) / GIB;
  const runtimeGiB = 2;
  const baseGiB = weightsGiB + kvGiB + runtimeGiB;
  return { weightsGiB, kvGiB, runtimeGiB, baseGiB, minimumGiB: baseGiB * 1.10, roomyGiB: baseGiB * 1.25, context };
}

/** Energy cost in JPY. Zero use is valid; invalid or unbounded input is not. */
export function electricity(watts, hours, days, rate) {
  if (!within(watts, 0, 100000) || !within(hours, 0, 24) || !within(days, 0, 366) || !within(rate, 0, 10000)) return null;
  return (watts / 1000) * hours * days * rate;
}

function runtimes(value) {
  return (Array.isArray(value) ? value : [value]).filter((v) => typeof v === "string" && v.trim()).map((v) => v.trim().toLowerCase());
}

/** Hardware compatibility is deliberately explicit. No cross-GPU memory pooling. */
export function candidateFit(profile, hardware, context) {
  const memory = computeMemory(profile, context);
  const capacity = hardware?.memory_gib;
  const reserve = hardware?.reserve_gib ?? (hardware?.kind === "computer" ? 8 : 0);
  const supported = runtimes(profile?.runtime);
  const available = runtimes(hardware?.runtime);
  const compatible = supported.length > 0 && available.some((r) => supported.includes(r));
  const validCapacity = within(capacity, 0, 100000) && within(reserve, 0, capacity);
  const availableGiB = validCapacity ? capacity - reserve : null;
  const known = Boolean(memory && validCapacity && compatible);
  const minimum = known && availableGiB >= memory.minimumGiB;
  const roomy = known && availableGiB >= memory.roomyGiB;
  return { memory, availableGiB, compatible, minimum, roomy, status: !known ? "unsupported" : roomy ? "roomy" : minimum ? "minimum" : "insufficient" };
}

function h(tag, attrs, ...children) {
  const el = document.createElement(tag);
  for (const [key, value] of Object.entries(attrs || {})) {
    if (value === null || value === undefined || value === false) continue;
    if (key === "class") el.className = value;
    else if (key === "on") for (const [event, listener] of Object.entries(value)) el.addEventListener(event, listener);
    else el.setAttribute(key, value === true ? "" : String(value));
  }
  for (const child of children.flat(Infinity)) {
    if (child !== null && child !== undefined && child !== false) el.append(child instanceof Node ? child : document.createTextNode(String(child)));
  }
  return el;
}
function safeLink(url, label, cls) {
  if (typeof url !== "string") return null;
  try {
    const parsed = new URL(url);
    if (!["https:", "http:"].includes(parsed.protocol)) return null;
    return h("a", { href: parsed.href, target: "_blank", rel: "noopener noreferrer", class: cls }, label || url);
  } catch { return null; }
}
const yen = (value) => number(value) === null ? "価格未確認" : new Intl.NumberFormat("ja-JP", { style: "currency", currency: "JPY", maximumFractionDigits: 0 }).format(value);
const gib = (value) => number(value) === null ? "—" : value.toLocaleString("ja-JP", { minimumFractionDigits: 1, maximumFractionDigits: 1 });
const list = (value) => Array.isArray(value) ? value : [];
const runtimeLabel = (value) => (Array.isArray(value) ? value : [value]).filter((v) => typeof v === "string").join(" / ") || "未確認";
const notes = (value) => (Array.isArray(value) ? value : [value]).filter((v) => typeof v === "string" && v);
const dateLabel = (value) => typeof value === "string" && /^\d{4}-\d{2}-\d{2}/.test(value) ? value.slice(0, 10) : "日付未確認";
const validDate = (value) => typeof value === "string" && /^\d{4}-\d{2}-\d{2}(?:T.*)?$/.test(value) && Number.isFinite(Date.parse(value));
const offerDate = (offer) => validDate(offer?.observed_at) ? offer.observed_at : "";
const offerPrice = (offer) => within(offer?.price_jpy, 0, 1e12) ? offer.price_jpy : null;
function taxLabel(offer) { return offer?.tax_included === true ? "税込" : offer?.tax_included === false ? "税別" : "税区分未確認"; }
function stockLabel(offer) {
  if (offer?.source_type === "historical_record") return "過去の価格記録・現在の在庫を示しません";
  const state = offer?.available === true ? offer.in_stock === false ? "観測時点で受注可・即納在庫なし" : "観測時点で注文可" : offer?.available === false ? "観測時点で購入不可" : "注文可否未確認";
  return offer?.lead_time_ja ? `${state} / ${offer.lead_time_ja}` : state;
}
function priceSeries(offer) {
  return offer?.source_type === "historical_record" ? "価格.com 掲載最安値（同一 SKU）" : "販売店の掲載価格";
}
function conditionLabel(value) { return ({ new: "新品", used: "中古", refurbished: "整備済み" })[value] || value || "状態未確認"; }
function shippingLabel(offer) {
  return within(offer?.shipping_jpy, 0, 1e9) ? offer.shipping_jpy === 0 ? "送料込・送料無料" : `送料 ${yen(offer.shipping_jpy)}` : "送料未確認";
}
function offersFor(data, hardwareId) {
  return list(data?.offers).filter((offer) => offer?.hardware_id === hardwareId && offerDate(offer) && offerPrice(offer) !== null).sort((a, b) => offerDate(b).localeCompare(offerDate(a)) || offerPrice(a) - offerPrice(b));
}
function currentOffer(data, hardwareId, availableOnly = false) {
  const all = offersFor(data, hardwareId).filter((offer) => offer.source_type !== "historical_record");
  if (!all.length) return null;
  const newestDay = offerDate(all[0]).slice(0, 10);
  // History is append-only. A later sold-out/unknown snapshot supersedes an
  // earlier orderable snapshot for that exact seller listing, even on one day.
  const latestListings = new Map();
  for (const offer of all) {
    const key = JSON.stringify([offer.seller, offer.sku, offer.url]);
    if (!latestListings.has(key)) latestListings.set(key, offer);
  }
  const today = [...latestListings.values()].filter((offer) => offerDate(offer).slice(0, 10) === newestDay);
  return today.find((offer) => offer.available === true) || (availableOnly ? null : today[0]) || null;
}
function offerTotal(offer) {
  if (!offer || offerPrice(offer) === null || offer.tax_included !== true) return Infinity;
  return offerPrice(offer) + (within(offer.shipping_jpy, 0, 1e9) ? offer.shipping_jpy : 0);
}
function sourceLinks(sources) {
  return list(sources).map((source, index) => typeof source === "string" ? safeLink(source, `資料 ${index + 1}`) : safeLink(source?.url, source?.label || source?.title || `資料 ${index + 1}`)).filter(Boolean);
}
function sectionTitle(step, title, description) {
  return h("div", { class: "cost-section-head" }, h("div", {}, h("span", { class: "cost-step" }, step), h("h3", {}, title)), description ? h("p", {}, description) : null);
}
function parseInput(params, key, fallback, min, max, integer = false) {
  const raw = params.get(key);
  if (raw === null || raw.trim() === "") return fallback;
  const value = Number(raw);
  return within(value, min, max) && (!integer || Number.isInteger(value)) ? value : fallback;
}

function renderMemory(profile, memory) {
  const parts = [
    { label: "重みファイル", value: memory.weightsGiB, cls: "weights", note: `${profile.artifact.quantization || "量子化方式未確認"}・配布物の実サイズ` },
    { label: "KV キャッシュ", value: memory.kvGiB, cls: "kv", note: `f16 / 1 系列 / ${memory.context.toLocaleString("ja-JP")} tokens` },
    { label: "実行時バッファ", value: memory.runtimeGiB, cls: "runtime", note: "一律 2 GiB と仮定" },
    { label: "最低限の余白", value: memory.baseGiB * 0.10, cls: "headroom", note: "小計の 10%" },
  ];
  return h("section", { class: "cost-section", "aria-labelledby": "cost-memory-title" },
    h("div", { class: "cost-section-head" }, h("div", {}, h("span", { class: "cost-step" }, "01"), h("h3", { id: "cost-memory-title" }, "まず、メモリはどのくらい？")), h("p", {}, "ファイルサイズを出発点にした概算。実際の使用量ではありません。")),
    h("div", { class: "cost-memory-summary" },
      h("div", {}, h("span", { class: "cost-eyebrow" }, "メモリ下限の試算"), h("p", { class: "cost-big-number" }, gib(memory.minimumGiB), h("span", {}, " GiB")), h("p", { class: "cost-small" }, "小計 ＋ 10% の余白")),
      h("div", { class: "cost-roomy-summary" }, h("span", { class: "cost-eyebrow" }, "メモリに余裕を持つなら"), h("p", { class: "cost-medium-number" }, gib(memory.roomyGiB), h("span", {}, " GiB")), h("p", { class: "cost-small" }, "小計 ＋ 25%。速度の保証ではありません。"))),
    h("div", { class: "cost-memory-bar", "aria-hidden": "true" }, parts.map((part) => h("span", { class: `cost-segment ${part.cls}`, style: `flex-grow:${part.value / memory.minimumGiB};` }))),
    h("dl", { class: "cost-breakdown" }, parts.map((part) => h("div", {}, h("dt", {}, h("span", { class: `cost-dot ${part.cls}`, "aria-hidden": "true" }), part.label), h("dd", {}, h("strong", {}, `${gib(part.value)} GiB`), h("small", {}, part.note))))),
    h("p", { class: "cost-small" }, "重みの全層を 1 台に載せる前提です。mmap、計算用バッファ、バックエンド、並列数で実使用量は変わります。CPU へのオフロードや複数 GPU のメモリ合算は含めません。"));
}

function candidateCard(candidate, tier, data) {
  const roomy = tier === "roomy";
  if (!candidate) return h("article", { class: `cost-tier ${roomy ? "roomy" : "minimum"}` }, h("p", { class: "cost-eyebrow" }, roomy ? "余裕あり / メモリ基準" : "メモリ下限の試算"), h("h4", {}, "掲載候補に該当なし"), h("p", {}, "この条件を満たす、対応ランタイム確認済みの機種はまだ掲載していません。"));
  const { hardware, fit } = candidate;
  const offer = currentOffer(data, hardware.id, true);
  return h("article", { class: `cost-tier ${roomy ? "roomy" : "minimum"}` },
    h("p", { class: "cost-eyebrow" }, roomy ? "余裕あり / メモリ基準" : "メモリ下限の試算"),
    h("h4", {}, hardware.name),
    h("p", { class: "cost-tier-spec" }, `${gib(hardware.memory_gib)} GiB`, h("span", {}, hardware.kind === "gpu" ? "単体 GPU" : "PC 本体")),
    h("p", { class: "cost-reference-price" }, offer ? yen(offerPrice(offer)) : "購入価格は未確認"),
    offer ? h("p", { class: "cost-small" }, `${taxLabel(offer)} / ${shippingLabel(offer)} / ${conditionLabel(offer.condition)}`) : h("p", { class: "cost-small" }, "直近の観測日に注文可能と確認した価格がありません。"),
    offer ? h("p", { class: "cost-small" }, `${dateLabel(offer.observed_at)} 観測・現在の在庫や価格は保証しません。`) : null,
    offer ? h("p", { class: "cost-small" }, stockLabel(offer)) : null,
    h("p", { class: "cost-small" }, hardware.kind === "gpu" ? "GPU 単体の費用です。ホスト PC・電源・冷却は別途必要。" : `OS・他アプリ用に ${gib(hardware.reserve_gib ?? 8)} GiB を確保し、残り ${gib(fit.availableGiB)} GiB で判定。`),
    offer ? safeLink(offer.url, `${offer.seller || "販売元"}で観測した商品`, "cost-text-link") : null);
}

function renderHardware(profile, context, data, selectedId, update) {
  const candidates = list(data.hardware).filter((hardware) => hardware && typeof hardware.id === "string").map((hardware) => ({ hardware, fit: candidateFit(profile, hardware, context) }));
  const rank = (a, b) => {
    const priceA = offerTotal(currentOffer(data, a.hardware.id, true));
    const priceB = offerTotal(currentOffer(data, b.hardware.id, true));
    if (priceA !== priceB) return priceA < priceB ? -1 : 1;
    return a.hardware.memory_gib - b.hardware.memory_gib;
  };
  const minimum = candidates.filter((c) => c.fit.minimum).sort(rank)[0];
  const roomy = candidates.filter((c) => c.fit.roomy).sort(rank)[0];
  const section = h("section", { class: "cost-section" }, sectionTitle("02", "どんなマシンが候補になる？", "容量とランタイムで絞り込み。動作・速度・応答の快適さを実測したおすすめではありません。"),
    h("div", { class: "cost-tiers" }, candidateCard(minimum, "minimum", data), candidateCard(roomy, "roomy", data)),
    h("p", { class: "cost-small" }, "販売ページの取得結果に基づく価格で、チェックアウトのライブ見積もりではありません。注文可能・税込の掲載価格がある候補を優先します。受注生産の納期は別途確認してください。送料不明は加算できず、PC 本体と GPU 単体の費用範囲も異なるため、最安の完成構成を保証するものではありません。"));
  if (!candidates.length) { section.append(h("p", { class: "note" }, "ハードウェアの確認済みデータはまだありません。")); return { section, hardware: null }; }
  const selected = candidates.find((c) => c.hardware.id === selectedId) || minimum || candidates[0];
  const statusLabels = { roomy: "余裕あり", minimum: "最低限", insufficient: "容量不足", unsupported: "対応未確認" };
  section.append(h("div", { class: "cost-table-wrap", tabindex: "0", "aria-label": "ハードウェア比較表。横にスクロールできます" },
    h("table", { class: "cost-table" }, h("caption", {}, "掲載ハードウェアと確認時点の参考価格"),
      h("thead", {}, h("tr", {}, ["ハードウェア", "容量判定", "観測した価格", "確認日・在庫", "価格履歴"].map((title) => h("th", { scope: "col" }, title)))),
      h("tbody", {}, candidates.map(({ hardware, fit }) => {
        const offer = currentOffer(data, hardware.id);
        return h("tr", {},
          h("th", { scope: "row" }, safeLink(hardware.url || hardware.source_url, hardware.name) || hardware.name, h("small", {}, `${hardware.kind === "gpu" ? "GPU 単体" : "PC 本体"} / ${gib(hardware.memory_gib)} GiB`), h("small", {}, runtimeLabel(hardware.runtime))),
          h("td", {}, h("span", { class: `cost-fit ${fit.status}` }, statusLabels[fit.status]), hardware.kind === "computer" ? h("small", {}, `OS 等の予約後 ${gib(fit.availableGiB)} GiB`) : null),
          h("td", {}, h("strong", {}, offer ? yen(offerPrice(offer)) : "価格未確認"), offer ? h("small", {}, `${taxLabel(offer)} / ${conditionLabel(offer.condition)}`) : null, offer ? h("small", {}, shippingLabel(offer)) : null),
          h("td", {}, offer ? dateLabel(offer.observed_at) : "—", h("small", { class: offer?.available === false ? "cost-warning" : "" }, offer ? stockLabel(offer) : "観測なし"), offer ? safeLink(offer.url, offer.seller || "販売元") : null),
          h("td", {}, h("button", { type: "button", class: "cost-button small", "aria-pressed": selected.hardware.id === hardware.id ? "true" : "false", on: { click: () => update({ hardware: hardware.id }, "cost-history-select") } }, "履歴を見る")));
      })))));
  return { section, hardware: selected.hardware };
}

function svg(tag, attrs, ...children) {
  const element = document.createElementNS("http://www.w3.org/2000/svg", tag);
  for (const [key, value] of Object.entries(attrs || {})) element.setAttribute(key, String(value));
  for (const child of children) element.append(child instanceof Node ? child : document.createTextNode(String(child)));
  return element;
}
function historyChart(offers, hardware) {
  const rows = [...offers].sort((a, b) => offerDate(a).localeCompare(offerDate(b)));
  const dates = [...new Set(rows.map((offer) => offerDate(offer).slice(0, 10)))];
  // Use the actual page width so mobile axes stay readable instead of scaling
  // a 780px diagram (and its labels) down to a few pixels.
  const width = Math.min(780, Math.max(260, document.querySelector('.cost-page')?.clientWidth || 780));
  const compact = width < 420;
  const height = 230, left = 84, right = 30, top = 25, bottom = 44;
  const values = rows.map(offerPrice);
  const min = Math.min(...values), max = Math.max(...values);
  const spread = Math.max(max - min, max * 0.12, 1);
  const low = Math.max(0, min - spread * 0.4), high = max + spread * 0.4;
  const start = Date.parse(dates[0]), end = Date.parse(dates[dates.length - 1]);
  const x = (value) => dates.length === 1 ? (width + left - right) / 2 : left + ((Date.parse(value.slice(0, 10)) - start) / (end - start)) * (width - left - right);
  const y = (value) => top + ((high - value) / (high - low)) * (height - top - bottom);
  const chart = svg("svg", { viewBox: `0 0 ${width} ${height}`, role: "img", "aria-label": `${hardware.name} の価格観測点。${dates.length} 日分、${rows.length} 件。詳しい価格は下の観測記録。`, class: "cost-chart" }, svg("title", {}, `${hardware.name} の出典つきの価格記録。点を線で結んだ補間はしません。`));
  for (let i = 0; i < 3; i++) {
    const value = low + (high - low) * i / 2;
    chart.append(svg("line", { x1: left, x2: width - right, y1: y(value), y2: y(value), class: "cost-chart-grid" }), svg("text", { x: left - 10, y: y(value) + 4, "text-anchor": "end", class: "cost-chart-label" }, yen(value)));
  }
  const tickDates = compact && dates.length > 1 ? [dates[0], dates[dates.length - 1]] : dates.length < 4 ? dates : [dates[0], dates[Math.floor(dates.length / 2)], dates[dates.length - 1]];
  for (const date of tickDates) chart.append(svg("text", { x: x(date), y: height - 12, "text-anchor": "middle", class: "cost-chart-label" }, compact ? date.slice(5) : date));
  for (const offer of rows) {
    const historical = offer.source_type === "historical_record";
    const pointSize = compact ? 3 : 7;
    const position = historical ? { x: x(offerDate(offer)) - pointSize / 2, y: y(offerPrice(offer)) - pointSize / 2, width: pointSize, height: pointSize } : { cx: x(offerDate(offer)), cy: y(offerPrice(offer)), r: compact ? 4 : 5.5 };
    chart.append(svg(historical ? "rect" : "circle", { ...position, class: `cost-chart-point ${historical ? "historical" : ""} ${offer.available === false ? "unavailable" : ""}` }, svg("title", {}, `${dateLabel(offer.observed_at)}: ${yen(offerPrice(offer))} / ${priceSeries(offer)} / SKU: ${offer.sku || "未確認"} / ${taxLabel(offer)} / ${conditionLabel(offer.condition)} / ${offer.seller || (historical ? "価格.com" : "販売元未確認")} / ${stockLabel(offer)}`)));
  }
  return chart;
}
function renderHistory(data, hardware, update) {
  if (!hardware) return null;
  const offers = offersFor(data, hardware.id);
  const historySkus = new Set(offers.filter((offer) => offer.source_type === "historical_record" && offer.sku).map((offer) => offer.sku));
  // A hardware family may contain multiple board SKUs. Only compare the exact historical SKU.
  const plotted = historySkus.size ? offers.filter((offer) => historySkus.has(offer.sku)) : offers;
  const dates = new Set(plotted.map((offer) => offerDate(offer).slice(0, 10)));
  const body = h("section", { class: "cost-section" }, sectionTitle("03", "価格は、実際の観測だけを並べる", "販売店の掲載価格と、価格比較サイトに記録された同一 SKU の過去価格を区別します。現在の在庫は保証しません。"),
    h("label", { class: "cost-history-control", for: "cost-history-select" }, "価格を見る機種", h("select", { id: "cost-history-select", on: { change: (event) => update({ hardware: event.target.value }, "cost-history-select") } }, list(data.hardware).map((item) => h("option", { value: item.id, selected: item.id === hardware.id }, item.name)))),
    plotted.length ? historyChart(plotted, hardware) : null,
    plotted.length ? h("div", { class: "cost-chart-legend" }, h("span", {}, h("i", { class: "cost-legend-dot", "aria-hidden": "true" }), "販売店の掲載価格"), historySkus.size ? h("span", {}, h("i", { class: "cost-legend-square", "aria-hidden": "true" }), "価格.com 掲載最安値（同一 SKU）") : null) : null,
    historySkus.size ? h("p", { class: "cost-small" }, `グラフの対象型番：${[...historySkus].join(" / ")}。過去の点は価格.com の日別掲載最安値、現在の点は特定販売店の掲載価格です。指標が異なるため連続した値動きとして扱いません。別型番の商品は下の観測記録にのみ掲載します。`) : null,
    dates.size < 2 ? h("p", { class: "cost-history-empty" }, h("strong", {}, "価格推移を判断するには観測日が不足しています。"), h("span", {}, dates.size === 1 ? " 現在は 1 日分の記録のみ。過去の価格や値動きを補間・推測して表示しません。" : " まだ日付つきの価格記録がありません。")) : h("p", { class: "cost-small" }, `${dates.size} 日分・${plotted.length} 件の出典つき価格記録。線でつながず、未観測期間の値動きは推定しません。販売元・状態・税・送料が異なる観測は同条件の価格比較には使えません。`));
  if (offers.length) body.append(h("details", { class: "cost-details" }, h("summary", {}, `観測記録と出典をすべて見る（${offers.length} 件）`), h("ul", { class: "cost-offer-list" }, offers.map((offer) => h("li", {}, h("div", {}, h("strong", {}, `${dateLabel(offer.observed_at)} · ${yen(offerPrice(offer))}`), ` / ${taxLabel(offer)} / ${shippingLabel(offer)} / ${conditionLabel(offer.condition)}`), h("div", {}, `${priceSeries(offer)} · SKU: ${offer.sku || "未確認"} · ${stockLabel(offer)} · `, safeLink(offer.url, offer.seller || (offer.source_type === "historical_record" ? "価格.com の価格履歴" : "販売元のページ"))))))));
  return body;
}

function renderElectricity(params, update) {
  const watts = parseInput(params, "watts", DEFAULTS.watts, 0, 100000);
  const hours = parseInput(params, "hours", DEFAULTS.hours, 0, 24);
  const days = parseInput(params, "days", DEFAULTS.days, 0, 31);
  const rate = parseInput(params, "rate", DEFAULTS.rate, 0, 10000);
  const total = electricity(watts, hours, days, rate);
  const fields = [
    ["watts", "平均システム消費電力", watts, "W", 100000, "1"],
    ["hours", "1 日の実行時間", hours, "時間", 24, "0.1"],
    ["days", "1 か月の実行日数", days, "日", 31, "1"],
    ["rate", "電力単価", rate, "円/kWh", 10000, "0.1"],
  ];
  return h("section", { class: "cost-section cost-energy" }, sectionTitle("04", "使う時間から、電気代を見積もる", "下の初期値は計算例です。選んだ機種の実測電力や、ご契約の電力単価ではありません。"),
    h("div", { class: "cost-energy-layout" },
      h("div", { class: "cost-energy-fields" }, fields.map(([key, title, value, unit, max, step]) => h("label", { for: `cost-${key}` }, title, h("span", { class: "cost-input-unit" }, h("input", { id: `cost-${key}`, type: "number", min: 0, max, step, value, inputmode: "decimal", "aria-describedby": "cost-energy-assumptions", on: { change: (event) => {
        const value = Number(event.target.value);
        const valid = event.target.value.trim() !== "" && within(value, 0, max);
        if (!valid) { event.target.value = String(DEFAULTS[key]); event.target.setCustomValidity(`0〜${max} の範囲で入力してください。既定値に戻しました。`); event.target.reportValidity(); }
        else event.target.setCustomValidity("");
        update({ [key]: valid ? String(value) : String(DEFAULTS[key]) }, `cost-${key}`);
      } } }), h("span", {}, unit))))),
      h("div", { class: "cost-energy-result", "aria-live": "polite", "aria-atomic": "true" }, h("span", { class: "cost-eyebrow" }, "この条件の電気代"), h("p", { class: "cost-big-number" }, yen(total), h("span", {}, " / 月")), h("p", {}, `${gib((watts / 1000) * hours * days)} kWh / 月`), h("p", { class: "cost-small" }, `同じ条件で 12 か月使うと ${yen(total * 12)}`))),
    h("p", { id: "cost-energy-assumptions", class: "cost-small" }, "計算式：W ÷ 1,000 × 時間/日 × 日数 × 円/kWh。初期値は 300 W・2 時間・30 日・31 円/kWh。GPU の TDP ではなく、PC 全体の壁コンセント側の平均電力を入力してください。待機電力・空調・基本料金・機材代は含みません。"));
}

function renderSources(profile, data) {
  const config = profile.config;
  return h("section", { class: "cost-section cost-method" }, h("h3", {}, "前提・ライセンス・出典"),
    h("dl", { class: "cost-source-facts" },
      h("div", {}, h("dt", {}, "配布物"), h("dd", {}, safeLink(profile.artifact.url, `${profile.artifact.quantization || "量子化方式未確認"} の重みファイル`) || "リンク未確認", ` · ${profile.artifact.bytes.toLocaleString("ja-JP")} bytes`)),
      h("div", {}, h("dt", {}, "ランタイム"), h("dd", {}, runtimeLabel(profile.runtime))),
      h("div", {}, h("dt", {}, "ライセンス"), h("dd", {}, safeLink(profile.license?.url, profile.license?.name || "ライセンス本文") || profile.license?.name || "未確認", "。オープンウェイトは用途・商用利用が無制限という意味ではありません。")),
      h("div", {}, h("dt", {}, "KV の仮定"), h("dd", {}, `${config.layers} layers × ${config.kv_heads} KV heads × ${config.head_dim} head dim。f16、同時実行 1 系列、全層・全トークン保持。`)),
      h("div", {}, h("dt", {}, "算定式"), h("dd", {}, "重み GiB = bytes ÷ 2³⁰。KV GiB = 2（K・V）× 2 bytes × layers × KV heads × head dim × tokens ÷ 2³⁰。小計 = 重み + KV + 2 GiB。メモリ下限 = 小計 × 1.10、余裕あり = 小計 × 1.25。")),
      h("div", {}, h("dt", {}, "データ確認"), h("dd", {}, dateLabel(data.retrieved)))),
    notes(profile.notes_ja).map((note) => h("p", { class: "cost-small" }, note)),
    h("p", { class: "cost-small" }, "メモリに収まっても、モデル形式、GPU 世代、ドライバ、ランタイムのバージョンや演算対応によって実行できないことがあります。トークン/秒・応答時間・量子化による精度低下は未測定です。"),
    h("div", { class: "cost-source-links" }, sourceLinks(profile.sources)),
    sourceLinks(data.sources).length ? h("div", { class: "cost-source-links" }, sourceLinks(data.sources)) : null);
}

/** Render into the app's main element. navigate receives a fresh URLSearchParams. */
export function renderCost(main, { models, data, params = new URLSearchParams(), navigate } = {}) {
  const registry = models instanceof Map ? models : new Map();
  const costs = data || {};
  const profiles = list(costs.profiles).filter((profile) => profile?.model_id && registry.has(profile.model_id));
  const profileMap = new Map(profiles.map((profile) => [profile.model_id, profile]));
  const defaultId = profileMap.has(costs.default_model) ? costs.default_model : profiles[0]?.model_id || registry.keys().next().value || "";
  const selectedId = params.get("model") || defaultId;
  const selectedModel = registry.get(selectedId);
  const profile = selectedModel?.open_weights === true ? profileMap.get(selectedId) : null;
  const context = parseInput(params, "context", DEFAULTS.context, 1, MAX_CONTEXT, true);
  const memory = profile ? computeMemory(profile, context) : null;
  const update = (patch, focusId) => {
    const next = new URLSearchParams(params);
    for (const [key, value] of Object.entries(patch)) {
      if (value === null || value === "") next.delete(key); else next.set(key, String(value));
    }
    if (typeof navigate === "function") navigate(next);
    else { main.replaceChildren(); renderCost(main, { models: registry, data: costs, params: next }); }
    if (focusId) document.getElementById(focusId)?.focus({ preventScroll: true });
  };
  const supported = [...registry.values()].filter((model) => model.open_weights === true && profileMap.has(model.id));
  const open = [...registry.values()].filter((model) => model.open_weights === true && !profileMap.has(model.id));
  const closed = [...registry.values()].filter((model) => model.open_weights !== true);
  const modelGroup = (label, items) => h("optgroup", { label }, items.sort((a, b) => (a.name || a.id).localeCompare(b.name || b.id)).map((model) => h("option", { value: model.id, selected: model.id === selectedId }, model.name || model.id)));
  const root = h("div", { class: "cost-page" },
    h("header", { class: "cost-hero" },
      h("div", {}, h("p", { class: "cost-kicker" }, "LOCAL INFERENCE / COST EXPLORER"), h("h2", {}, "このモデル、", h("span", {}, "いくらで動く？")), h("p", { class: "cost-hero-lede" }, "モデルを選んで、必要なメモリと機材の参考価格、毎月の電気代をひとつずつ。")),
      h("div", { class: "cost-hero-facts" }, h("span", {}, "国内価格・円表示"), h("span", {}, "実測と推定を分離"), h("span", {}, `${dateLabel(costs.retrieved)} 確認`))),
    h("section", { class: "cost-selector", "aria-label": "見積もり条件" },
      h("div", { class: "cost-model-field" }, h("label", { for: "cost-model" }, "調べたいモデル"),
        h("select", { id: "cost-model", on: { change: (event) => update({ model: event.target.value }, "cost-model") } },
          !selectedModel ? h("option", { value: selectedId, selected: true }, `未登録のモデル: ${selectedId.slice(0, 120)}`) : null,
          supported.length ? modelGroup(`算定データあり（${supported.length}）`, supported) : null,
          open.length ? modelGroup(`オープンウェイト・算定未対応（${open.length}）`, open) : null,
          closed.length ? modelGroup(`重み非公開・公開状況未確認（${closed.length}）`, closed) : null),
        h("p", { class: "cost-small" }, `全 ${registry.size} モデルから選択できます。算定データがないモデルを、近い別モデルで代用しません。`)),
      h("div", { class: "cost-context-field" }, h("label", { for: "cost-context" }, "コンテキスト（入力＋出力合計）"),
        h("div", { class: "cost-input-unit" }, h("input", { id: "cost-context", type: "number", min: 1, max: MAX_CONTEXT, step: 1, value: context, inputmode: "numeric", disabled: !profile, on: { change: (event) => {
          const value = Number(event.target.value);
          update({ context: within(value, 1, MAX_CONTEXT) && Number.isInteger(value) ? String(value) : String(DEFAULTS.context) }, "cost-context");
        } } }), h("span", {}, "tokens")),
        h("div", { class: "cost-context-presets", role: "group", "aria-label": "コンテキスト長の候補" }, [4096, 8192, 32768].map((value) => h("button", { type: "button", class: "cost-button small", disabled: !profile, "aria-pressed": value === context ? "true" : "false", on: { click: () => update({ context: value }, "cost-context") } }, `${value / 1024}k`))))));
  main.append(root);
  if (!selectedModel || !profile || !memory) {
    const closedModel = selectedModel?.open_weights === false;
    const knownOpen = selectedModel?.open_weights === true;
    const title = !selectedModel ? "登録されていないモデルです" : profile && !memory ? "この条件では算定できません" : closedModel ? "このモデルは、ローカル費用を算定しません" : "このモデルの算定データは未収録です";
    const researchReason = list(costs.research_only).find((item) => item.model_id === selectedId)?.reason_ja;
    const explanation = researchReason || (!selectedModel ? "モデル選択から、登録済みのモデルを選んでください。" : profile && !memory ? "モデルの確認済みコンテキスト上限を超えているか、必要な構成情報が不足しています。コンテキスト長を短くするか、別のモデルを選んでください。" : closedModel ? "重みが公開されていないモデルです。GPU を購入して自宅で実行できるものとして、価格や必要メモリを推定することはできません。API 利用料金はこのページの対象外です。" : knownOpen ? "重みは公開されていますが、配布ファイルのサイズ・構成・ランタイムの確認がまだ揃っていません。価格や必要メモリを推測では埋めません。" : "重みの公開状況を確認できていないため、ローカル実行できるとは扱いません。価格や必要メモリは未算定です。");
    root.append(h("section", { class: "cost-unsupported", role: "status" }, h("span", { class: "cost-eyebrow" }, selectedModel?.name || "MODEL NOT FOUND"), h("h3", {}, title), h("p", {}, explanation), safeLink(selectedModel?.weights_url, "公開ウェイトの参照先"), supported.length ? h("p", {}, "算定データがあるモデル：", supported.slice(0, 5).map((model) => h("button", { type: "button", class: "cost-button small", on: { click: () => update({ model: model.id, context: DEFAULTS.context }, "cost-model") } }, model.name || model.id))) : null));
    return;
  }
  root.append(h("div", { class: "cost-assumption-banner" }, h("strong", {}, "容量の概算です。動作確認や速度測定ではありません。"), h("span", {}, `${selectedModel.name} / ${profile.artifact.quantization || "量子化方式未確認"} / ${runtimeLabel(profile.runtime)} / 同時実行 1 系列`)), renderMemory(profile, memory));
  const result = renderHardware(profile, context, costs, params.get("hardware"), update);
  root.append(result.section);
  const history = renderHistory(costs, result.hardware, update);
  if (history) root.append(history);
  root.append(renderElectricity(params, update), renderSources(profile, costs));
}
