/* ============================================================
   Config-driven leaderboard for the CyberGym series.

   Usage (per page):
     CyberGymLeaderboard.render({
       dataUrl: "/assets/data/cybergym.json",
       rootId: "leaderboard",
       rows: (json) => json.level1,          // -> array of row objects
       columns: [ { header, cell(row, rank) } ],
       sort: (a, b) => b.score_10 - a.score_10,
       filters: [ ... ],                       // optional
       chart: { canvasId, ... },               // optional (CyberGym scatter)
     });
   ============================================================ */
(function () {
  "use strict";

  /* ---------- small helpers ---------- */
  function el(html) {
    const t = document.createElement("template");
    t.innerHTML = html.trim();
    return t.content.firstElementChild;
  }
  function rankClass(rank) {
    return "lb-rank";
  }
  // Caret button that folds/unfolds a parent row's attached sub-rows.
  const foldBtn = (g, expanded) =>
    `<button type="button" class="lb-fold" data-group="${g}" aria-expanded="${expanded ? "true" : "false"}" aria-label="Toggle variant"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path stroke-linecap="round" stroke-linejoin="round" d="m9 6 6 6-6 6"/></svg></button>`;

  /* Features allowed to render as a chip beside the entity name. Every other
     value in a row's `features` array stays data-only (used for grouping and
     analysis, not shown in the table). */
  const FEATURE_CHIPS = new Set(["test-time mem.", "dynamic"]);

  /* Shared cell renderers so pages stay declarative. */
  const cells = {
    rank: (row, rank) => (rank == null ? "" : `<span class="${rankClass(rank)}">${rank}</span>`),
    // Agent name with an optional "(note)" shown via the native title tooltip
    // (a styled ::after tooltip would be clipped by the table's scroll container).
    agentWithNote: (row) => {
      const a = row.agent || "-";
      const parts = splitNote(a);
      if (!parts) return esc(unescParens(a));
      return `<span class="note-cue" data-note="${esc(parts.note)}">${esc(parts.name)}</span>`;
    },
    // Model name; a trailing "(note)" (e.g. "GPT-5 (high)", "Multi-model (a, b)")
    // collapses to the name + a hover note, same as agentWithNote.
    model: (row) => {
      const m = row.model || "-";
      const parts = splitNote(m);
      if (!parts) return esc(unescParens(m));
      return `<span class="note-cue" data-note="${esc(parts.note)}">${esc(parts.name)}</span>`;
    },
    // Chips for a row's whitelisted features. Each feature string follows the
    // same "Name (note)" convention as agent/model, so a trailing parenthetical
    // becomes a hover note on the chip; a bare name renders as a plain chip.
    features: (row) => {
      const list = Array.isArray(row.features) ? row.features : row.features ? [row.features] : [];
      return list
        .map((f) => {
          const parts = splitNote(f);
          const name = parts ? parts.name : unescParens(f);
          if (!FEATURE_CHIPS.has(name)) return "";
          const note = parts ? parts.note : "";
          const attrs = note ? ` data-note="${esc(note)}"` : "";
          return `<span class="lb-feature${note ? " lb-feature-note" : ""}"${attrs}>${esc(name)}</span>`;
        })
        .join("");
    },
    source: (row) =>
      row.source_url
        ? `<a href="${esc(row.source_url)}" target="_blank" rel="noopener" class="inline-flex items-center gap-1 font-medium text-[color:var(--accent-strong)] underline-offset-2 hover:underline">${esc(row.source || "link")}<svg viewBox="0 0 24 24" class="h-3.5 w-3.5 opacity-70" fill="none" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M7 17 17 7M9 7h8v8"/></svg></a>`
        : `<span class="text-slate-400">${esc(row.source || "-")}</span>`,
    // Percentage score with a thin progress bar.
    percent: (value) => {
      const pct = (value * 100).toFixed(1);
      return `<div class="lb-score">${pct}%</div><div class="lb-bar"><span style="width:${pct}%"></span></div>`;
    },
    // Icon URL for a row, resolved the same way the scatter plot does: an explicit
    // per-row `icon` wins, else the name-based MODEL_ICON_MAP rules. Returns null if none.
    iconUrl: (row) => {
      const isAgent = (row.focus || "model") === "agent";
      const raw = (isAgent ? row.agent : row.model) || "";
      const label = unescParens((splitNote(raw) || { name: raw }).name);
      return row.icon || getModelIconUrl(label);
    },
  };

  function esc(s) {
    return String(s == null ? "" : s).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
  }

  // Strip \( and \) escapes, yielding literal parens that won't trigger note-collapsing.
  function unescParens(s) { return s.replace(/\\\(/g, "(").replace(/\\\)/g, ")"); }

  // Split on the first unescaped " (" to extract a note suffix; escaped \( is ignored.
  function splitNote(s) {
    const clean = s.replace(/\\\(/g, "\x00");
    const i = clean.indexOf(" (");
    if (i === -1) return null;
    return { name: unescParens(s.slice(0, i)), note: s.slice(s.indexOf("(", i) + 1, s.lastIndexOf(")")) };
  }

  /* ---------- note tooltip ----------
     One popup element on <body>, shown instantly on hover of any [data-note].
     Clamped to the viewport so it never goes out of bounds. */
  function initNoteTooltips() {
    if (window.__cgTooltipInit) return;
    window.__cgTooltipInit = true;
    const tip = document.createElement("div");
    tip.className = "cg-tooltip";
    tip.setAttribute("role", "tooltip");
    document.body.appendChild(tip);
    let current = null;

    function position(el) {
      const r = el.getBoundingClientRect();
      const t = tip.getBoundingClientRect();
      const margin = 8;
      let left = r.left + r.width / 2 - t.width / 2;
      left = Math.max(margin, Math.min(left, window.innerWidth - t.width - margin));
      let top = r.top - t.height - 8;
      if (top < margin) top = r.bottom + 8; // not enough room above → flip below
      tip.style.left = left + "px";
      tip.style.top = top + "px";
    }
    function show(el) {
      current = el;
      const html = el.getAttribute("data-note-html");
      if (html != null) tip.innerHTML = html;
      else tip.textContent = el.getAttribute("data-note") || "";
      position(el); // measure & place before fading in (avoids 0,0 flash)
      tip.classList.add("is-visible");
    }
    function hide() {
      current = null;
      tip.classList.remove("is-visible");
    }

    const SEL = "[data-note], [data-note-html]";
    document.addEventListener("mouseover", (e) => {
      const el = e.target.closest(SEL);
      if (el && el !== current) show(el);
    });
    document.addEventListener("mouseout", (e) => {
      const el = e.target.closest(SEL);
      if (el && (!e.relatedTarget || !el.contains(e.relatedTarget))) hide();
    });
    document.addEventListener("scroll", () => { if (current) position(current); }, true);
    window.addEventListener("resize", () => { if (current) position(current); });
  }

  /* ---------- table rendering ---------- */
  // Current filter selections, keyed by each filter's `key`.
  // Current value of a filter: a <select>'s value, a button group's tracked
  // value, or the declared default.
  function filterValue(f) {
    if (f.checkboxes) return f._set ? [...f._set] : [];
    if (f._select) return f._select.value;
    if (f._value != null) return f._value;
    return f.default;
  }
  function filterState(cfg) {
    const state = {};
    (cfg.filters || []).forEach((f) => {
      if (f.key) state[f.key] = filterValue(f);
    });
    return state;
  }
  // Columns visible for the current filter state (a column may define visible(state)).
  function visibleColumns(cfg) {
    const state = filterState(cfg);
    return cfg.columns.filter((c) => (c.visible ? c.visible(state) : true));
  }

  function renderTable(cfg, rows) {
    const tbody = document.getElementById(cfg._tbodyId);
    const thead = document.getElementById(cfg._theadId);
    if (!tbody) return;
    const cols = visibleColumns(cfg);
    if (thead) {
      thead.innerHTML = `<tr>${cols
        .map((c) => {
          const cls = c.thClass ? ` class="${c.thClass}"` : "";
          if (!c.sortBy) return `<th${cls}>${c.header}</th>`;
          const i = cfg.columns.indexOf(c);
          const active = cfg._sortCol === i;
          const caret = active
            ? (cfg._sortDir === 1
                ? `<svg viewBox="0 0 24 24" class="lb-caret" fill="none" stroke="currentColor" stroke-width="2.5"><path stroke-linecap="round" stroke-linejoin="round" d="m6 15 6-6 6 6"/></svg>`
                : `<svg viewBox="0 0 24 24" class="lb-caret" fill="none" stroke="currentColor" stroke-width="2.5"><path stroke-linecap="round" stroke-linejoin="round" d="m6 9 6 6 6-6"/></svg>`)
            : `<svg viewBox="0 0 24 24" class="lb-caret lb-caret-idle" fill="none" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="m8 10 4-4 4 4M8 14l4 4 4-4"/></svg>`;
          return `<th${cls}><button type="button" class="lb-sort${active ? " is-active" : ""}" data-col="${i}">${c.header}${caret}</button></th>`;
        })
        .join("")}</tr>`;
    }
    if (!rows.length) {
      tbody.innerHTML = `<tr><td colspan="${cols.length}" class="px-4 py-6 text-center text-slate-400">No results available</td></tr>`;
      return;
    }
    let sorted;
    const activeCol = cfg._sortCol != null ? cfg.columns[cfg._sortCol] : null;
    if (activeCol && activeCol.sortBy) {
      const dir = cfg._sortDir;
      sorted = [...rows].sort((a, b) => {
        const d = activeCol.sortBy(a) - activeCol.sortBy(b);
        return d !== 0 ? d * dir : 0;
      });
    } else {
      sorted = cfg.sort ? [...rows].sort(cfg.sort) : rows;
    }
    const rankOffset = cfg._rankOffset || 0;
    tbody.innerHTML = sorted
      .map((row, idx) => {
        const rank = idx + 1 + rankOffset;
        const hasSub = !!(row.subRows && row.subRows.length);
        const gid = "sub-" + idx;
        const subOpen = cfg.subRowsOpen !== false; // expanded by default; set subRowsOpen:false to collapse
        const tds = cols
          .map((c, ci) => {
            let content = c.cell(row, rank, sorted);
            if (ci === 0 && hasSub) content = content + foldBtn(gid, subOpen); // caret toggle right of rank
            return `<td${c.tdClass ? ` class="${c.tdClass}"` : ""}>${content}</td>`;
          })
          .join("");
        let html = `<tr${hasSub ? ` class="lb-parent" data-group="${gid}"` : ""}>${tds}</tr>`;
        // Sub-rows: attached beneath their parent, unranked, outside sorting.
        (row.subRows || []).forEach((s) => {
          const sr = Object.assign({}, row, s, { _sub: true, subRows: undefined });
          const std = cols
            .map((c) => `<td${c.tdClass ? ` class="${c.tdClass}"` : ""}>${c.cell(sr, null, sorted)}</td>`)
            .join("");
          html += `<tr class="lb-subrow" data-group="${gid}"${subOpen ? "" : " hidden"}>${std}</tr>`;
        });
        return html;
      })
      .join("");
  }

  /* ---------- leading-tier cards ----------
     Systems above a threshold are lifted out of the ranked table into a compact
     card grid, where ordering is not meant to read as a ranking. cfg.leadPredicate
     selects them, cfg.card(row) renders each, cfg.leadSort optionally orders them.
     The remaining rows stay in the table below, with ranks continuing past the
     lifted count (so they don't restart at 1). */
  function renderLead(cfg, leadRows) {
    const grid = document.getElementById(cfg._leadId);
    const section = document.getElementById(cfg._leadSectionId);
    if (section) section.style.display = leadRows.length ? "" : "none";
    if (!grid) return;
    grid.innerHTML = leadRows.map((r) => cfg.card(r)).join("");
  }

  /* ---------- filters ---------- */
  // Persist each filter's selection in localStorage so a chosen view survives
  // reloads. The stored value only wins if it's still a valid option; otherwise
  // the configured default applies (first visit, or an option that went away).
  // Scoped by benchmark: every page uses rootId "leaderboard", so without this the
  // CyberGym and ExploitGym tables would share one another's saved selections.
  function storeKey(cfg, f) {
    const scope = document.documentElement.getAttribute("data-benchmark") || location.pathname;
    return "cglb:" + scope + ":" + cfg.rootId + ":" + f.key + (f._scope ? ":" + f._scope : "");
  }
  function saveFilter(cfg, f, value) {
    if (!f.key) return;
    try { localStorage.setItem(storeKey(cfg, f), String(value)); } catch (e) {}
  }
  // Multi-select (checkbox) filters persist as a comma-joined list; unknown values
  // are dropped so a renamed/removed option can't resurrect a stale selection.
  function loadFilterSet(cfg, f, validValues) {
    if (!f.key) return null;
    try {
      const v = localStorage.getItem(storeKey(cfg, f));
      if (v == null) return null;
      return v.split(",").filter((x) => x && validValues.indexOf(x) !== -1);
    } catch (e) {}
    return null;
  }
  function loadFilter(cfg, f, validValues) {
    if (!f.key) return null;
    try {
      const v = localStorage.getItem(storeKey(cfg, f));
      if (v != null && validValues.indexOf(v) !== -1) return v;
    } catch (e) {}
    return null;
  }

  function buildFilters(cfg, allRows, onChange) {
    const bar = document.getElementById(cfg._filtersId);
    if (!bar || !cfg.filters || !cfg.filters.length) return;
    bar.innerHTML = "";
    cfg.filters.forEach((f) => {
      const wrap = el(`<label class="inline-flex items-center gap-2 text-sm text-slate-600"><span>${esc(f.label)}</span></label>`);
      const opts = f.options(allRows);
      const validValues = opts.map((o) => String(o.value));
      const saved = loadFilter(cfg, f, validValues);
      const initial = saved != null ? saved : (f.default != null ? String(f.default) : null);
      if (f.checkboxes) {
        // Inclusion toggles. `dependsOn` lets the group re-derive its default (and
        // its saved state) whenever the named filter changes — e.g. the settings
        // start ticked on the All/Agent tabs and unticked on Model.
        const group = el(`<div class="filter-checks"></div>`);
        f._render = () => {
          f._scope = f.dependsOn ? String(filterState(cfg)[f.dependsOn]) : "";
          const savedSet = loadFilterSet(cfg, f, validValues);
          const fallback = f.defaultFor ? f.defaultFor(filterState(cfg)) : (f.default || []);
          f._set = new Set(savedSet != null ? savedSet : fallback.map(String));
          group.innerHTML = "";
          opts.forEach((o) => {
            const box = el(`<label class="filter-check"><input type="checkbox" value="${esc(o.value)}"><span>${esc(o.label)}</span></label>`);
            const input = box.querySelector("input");
            input.checked = f._set.has(String(o.value));
            box.classList.toggle("is-on", input.checked);
            input.addEventListener("change", () => {
              if (input.checked) f._set.add(String(o.value));
              else f._set.delete(String(o.value));
              box.classList.toggle("is-on", input.checked);
              saveFilter(cfg, f, [...f._set].join(","));
              onChange();
            });
            group.appendChild(box);
          });
        };
        f._render();
        wrap.appendChild(group);
      } else if (f.buttons) {
        // Segmented button group instead of a dropdown.
        const group = el(`<div class="filter-seg" role="group" aria-label="${esc(f.label)}"></div>`);
        f._value = initial;
        opts.forEach((o) => {
          const btn = el(`<button type="button" class="filter-seg-btn" data-value="${esc(o.value)}">${esc(o.label)}</button>`);
          if (String(o.value) === String(f._value)) btn.classList.add("is-active");
          btn.addEventListener("click", () => {
            if (f._value === String(o.value)) return;
            f._value = String(o.value);
            group.querySelectorAll(".filter-seg-btn").forEach((b) => b.classList.toggle("is-active", b === btn));
            saveFilter(cfg, f, f._value);
            refreshDependents(cfg, f.key);
            onChange();
          });
          group.appendChild(btn);
        });
        wrap.appendChild(group);
      } else {
        const sel = el(`<select class="filter-select"></select>`);
        opts.forEach((o) => {
          const opt = el(`<option value="${esc(o.value)}">${esc(o.label)}</option>`);
          sel.appendChild(opt);
        });
        sel.value = initial != null ? initial : sel.value;
        sel.addEventListener("change", () => { saveFilter(cfg, f, sel.value); refreshDependents(cfg, f.key); onChange(); });
        f._select = sel;
        wrap.appendChild(sel);
      }
      bar.appendChild(wrap);
    });
  }

  /* A row may carry `visible_after` (an ISO timestamp) to schedule its reveal: it
     stays out of the table and the chart until that moment passes, and the page
     re-renders on its own when it does. Note this is a scheduled reveal, not an
     embargo — the data file is public — so it hides a result from the UI, not
     from anyone who opens the JSON. */
  function visibleNow(rows) {
    const now = Date.now();
    return rows.filter((r) => {
      const t = r.visible_after ? Date.parse(r.visible_after) : NaN;
      return isNaN(t) || now >= t;
    });
  }
  // Soonest future reveal, so we can re-render exactly when it lands.
  function nextRevealAt(rows) {
    const now = Date.now();
    const times = rows
      .map((r) => (r.visible_after ? Date.parse(r.visible_after) : NaN))
      .filter((t) => !isNaN(t) && t > now)
      .sort((a, b) => a - b);
    return times.length ? times[0] : null;
  }

  // Re-render filters whose options/defaults hang off the one that just changed.
  function refreshDependents(cfg, changedKey) {
    (cfg.filters || []).forEach((f) => {
      if (f.dependsOn === changedKey && typeof f._render === "function") f._render();
    });
  }

  function applyFilters(cfg, allRows) {
    let rows = visibleNow(allRows);
    (cfg.filters || []).forEach((f) => {
      const v = filterValue(f);
      if (f.checkboxes) {
        rows = rows.filter((r) => f.predicate(r, v));
        return;
      }
      if (v !== "all" && v != null) rows = rows.filter((r) => f.predicate(r, v));
    });
    return rows;
  }

  /* ---------- public entry ---------- */
  async function render(cfg) {
    const root = document.getElementById(cfg.rootId);
    if (!root) return;
    cfg._filtersId = cfg.rootId + "-filters";
    cfg._tbodyId = cfg.rootId + "-tbody";
    cfg._theadId = cfg.rootId + "-thead";
    cfg._leadId = cfg.rootId + "-lead";
    cfg._leadSectionId = cfg.rootId + "-leadsec";
    const leadHybrid = !!cfg.leadCards;

    // Scaffold: filter bar, an optional leading-tier card grid, then the table
    // (header filled in on each update so columns can track the active filter).
    const leadScaffold = leadHybrid
      ? `<div id="${cfg._leadSectionId}" class="lb-lead" style="display:none">
        ${cfg.leadTitle ? `<div class="lb-lead-title">${cfg.leadTitle}</div>` : ""}
        <div id="${cfg._leadId}" class="lb-lead-grid"></div>
      </div>`
      : "";
    root.innerHTML = `
      <div id="${cfg._filtersId}" class="mb-4 flex flex-wrap items-center gap-4"></div>
      ${leadScaffold}
      <div class="lb-wrap" style="max-height:${cfg.maxHeight || "70vh"}">
        <table class="lb-table">
          <thead id="${cfg._theadId}"></thead>
          <tbody id="${cfg._tbodyId}"><tr><td colspan="${cfg.columns.length}" class="px-4 py-6 text-center text-slate-400">Loading…</td></tr></tbody>
        </table>
      </div>`;

    let json;
    try {
      const res = await fetch(cfg.dataUrl);
      if (!res.ok) throw new Error("HTTP " + res.status);
      json = await res.json();
    } catch (e) {
      document.getElementById(cfg._tbodyId).innerHTML =
        `<tr><td colspan="${cfg.columns.length}" class="px-4 py-6 text-center text-rose-500">Failed to load data</td></tr>`;
      console.error("Leaderboard load error:", e);
      return;
    }

    const allRows = cfg.rows ? cfg.rows(json) || [] : json;

    // Stamp a per-load random key for the shuffled leading tier (see leadShuffle).
    if (cfg.leadShuffle) allRows.forEach((r) => { if (r._shuf == null) r._shuf = Math.random(); });

    // Initial sort: a column flagged defaultSort starts active (descending).
    if (cfg._sortCol === undefined) {
      const di = cfg.columns.findIndex((c) => c.defaultSort);
      cfg._sortCol = di >= 0 ? di : null;
      cfg._sortDir = -1;
    }

    const update = () => {
      const rows = applyFilters(cfg, allRows);
      if (leadHybrid) {
        const lead = rows.filter(cfg.leadPredicate);
        // leadShuffle: random order fixed per page load (a stable key per row,
        // stamped once, so toggling filters doesn't reshuffle) — a refresh gives
        // a new order. Otherwise fall back to leadSort, else data order.
        const leadSorted = cfg.leadShuffle
          ? [...lead].sort((a, b) => a._shuf - b._shuf)
          : cfg.leadSort ? [...lead].sort(cfg.leadSort) : lead;
        renderLead(cfg, leadSorted);
        cfg._rankOffset = leadSorted.length; // table ranks continue past the lifted cards
        renderTable(cfg, rows.filter((r) => !cfg.leadPredicate(r)));
      } else {
        cfg._rankOffset = 0;
        renderTable(cfg, rows);
      }
    };

    // Click a sortable header to sort by it; click again to flip direction.
    const thead = document.getElementById(cfg._theadId);
    if (thead) {
      thead.addEventListener("click", (e) => {
        const btn = e.target.closest("[data-col]");
        if (!btn) return;
        const i = parseInt(btn.dataset.col, 10);
        if (cfg._sortCol === i) cfg._sortDir = -cfg._sortDir;
        else { cfg._sortCol = i; cfg._sortDir = -1; }
        update();
      });
    }

    // Fold/unfold a parent's attached sub-rows (delegated; tbody persists across re-renders).
    const tbodyEl = document.getElementById(cfg._tbodyId);
    if (tbodyEl) {
      tbodyEl.addEventListener("click", (e) => {
        if (e.target.closest("a")) return; // let links (e.g. source) work normally
        const parent = e.target.closest("tr.lb-parent");
        if (!parent) return;
        const group = parent.dataset.group;
        const caret = tbodyEl.querySelector('.lb-fold[data-group="' + group + '"]');
        const expanded = caret ? caret.getAttribute("aria-expanded") === "true" : false;
        if (caret) caret.setAttribute("aria-expanded", expanded ? "false" : "true");
        tbodyEl.querySelectorAll('tr.lb-subrow[data-group="' + group + '"]').forEach((tr) => {
          tr.hidden = expanded;
        });
      });
    }

    // Leading-tier stacks: the "‹ k/N ›" arrows step through a system's
    // submissions (delegated; the grid container persists across re-renders).
    const leadEl = document.getElementById(cfg._leadId);
    if (leadEl) {
      leadEl.addEventListener("click", (e) => {
        const btn = e.target.closest(".lb-lcard-nav-prev, .lb-lcard-nav-next");
        if (!btn) return;
        const stack = btn.closest(".lb-lstack");
        if (!stack) return;
        const faces = [...stack.children].filter((c) => c.classList.contains("lb-lcard"));
        if (faces.length < 2) return;
        let cur = faces.findIndex((c) => c.classList.contains("is-active"));
        if (cur < 0) cur = 0;
        const delta = btn.classList.contains("lb-lcard-nav-prev") ? -1 : 1;
        faces[cur].classList.remove("is-active");
        faces[(cur + delta + faces.length) % faces.length].classList.add("is-active");
      });
    }

    buildFilters(cfg, allRows, update);
    update();

    // Re-render when the next scheduled reveal lands (setTimeout caps at ~24.8
    // days, so only arm it when the moment is within range).
    const reveal = nextRevealAt(allRows);
    if (reveal != null) {
      const delay = reveal - Date.now() + 500;
      if (delay > 0 && delay < 2147483647) setTimeout(update, delay);
    }

    if (cfg.chart) {
      try {
        await renderScatterChart(cfg.chart, visibleNow(allRows));
      } catch (e) {
        console.error("Chart error:", e);
      }
    }
  }

  /* ============================================================
     Time-vs-success scatter chart (CyberGym hero).
     Ported from the original load-leaderboard.js, parameterised.
     ============================================================ */
  const ICON_BASE = "https://cdn.jsdelivr.net/npm/@lobehub/icons-static-svg@1.86.0/icons/";
  const MODEL_ICON_MAP = [
    { match: (m) => /^Claude/i.test(m), icon: "claude-color.svg" },
    { match: (m) => /^GPT|^o\d/i.test(m), icon: "openai.svg" },
    { match: (m) => /^Gemini/i.test(m), icon: "gemini-color.svg" },
    { match: (m) => /^DeepSeek/i.test(m), icon: "deepseek-color.svg" },
    { match: (m) => /^GLM/i.test(m), icon: "zai.svg" },
    { match: (m) => /^Kimi/i.test(m), icon: "kimi.svg" },
    { match: (m) => /^Qwen/i.test(m), icon: "qwen-color.svg" },
    { match: (m) => /^Grok/i.test(m), icon: "grok.svg" },
    { match: (m) => /^Muse/i.test(m), icon: "https://upload.wikimedia.org/wikipedia/commons/2/2f/Meta_AI_Logo_%282026%29.svg" },
    { match: (m) => /^MDASH/i.test(m), icon: "microsoft-color.svg" },
  ];
  const FORCE_LABEL_SIDE = { "Kimi K2.5": "left", "Claude Mythos Preview": "left", "GPT-5.5": "right-down" };

  function getModelIconUrl(modelName) {
    for (const entry of MODEL_ICON_MAP) {
      if (entry.match(modelName)) return /^https?:/.test(entry.icon) ? entry.icon : ICON_BASE + entry.icon;
    }
    return null;
  }
  function loadIcon(url, size) {
    return new Promise((resolve) => {
      const img = new Image();
      img.crossOrigin = "anonymous";
      img.onload = () => {
        // Fit within `size` preserving the source aspect ratio (avoids squished non-square icons).
        const nw = img.naturalWidth || size;
        const nh = img.naturalHeight || size;
        const s = size / Math.max(nw, nh);
        img.width = Math.round(nw * s);
        img.height = Math.round(nh * s);
        resolve(img);
      };
      img.onerror = () => resolve(null);
      img.src = url;
    });
  }

  // Theme-aware chart colors (canvas can't be styled by CSS).
  function chartColors() {
    const dark = document.documentElement.getAttribute("data-theme") === "dark";
    return dark
      ? { tick: "#94a3b8", grid: "rgba(148,163,184,0.16)", title: "#cbd5e1", label: "#e2e8f0", line: "#64748b" }
      : { tick: "#666", grid: "rgba(0,0,0,0.08)", title: "#333", label: "#0f172a", line: "#aaa" };
  }

  // A point is "active" (fully opaque) on hover if it's the hovered icon or linked to/from it.
  function activeOnHover(chart, i) {
    const h = chart.hoverIndex;
    if (h == null) return true;
    const data = chart.data.datasets[0].data;
    const hLinks = data[h].links || [];
    const iLinks = data[i].links || [];
    return i === h || hLinks.includes(i) || iLinks.includes(h);
  }

  async function renderScatterChart(chartCfg, allRows) {
    const canvas = document.getElementById(chartCfg.canvasId);
    if (!canvas || typeof Chart === "undefined") return;

    const plotData = allRows.filter(chartCfg.include || ((d) => d.include_in_plot));
    if (!plotData.length) return;

    const ICON_SIZE = 17;
    // Model-focused points are labeled with the model; agent-focused with the agent name.
    // Icon resolution: a per-row `icon` (path/URL) wins; else the model-name rules. `icon_scale` resizes.
    const points = plotData.map((d) => {
      const isAgent = d.focus === "agent";
      const modelLabel = d.model && d.model.startsWith("Multi-model") ? `${unescParens(d.agent)} (Multi-model)` : unescParens((splitNote(d.model || "") || { name: d.model || "" }).name);
      const agentLabel = unescParens((splitNote(d.agent || "") || { name: d.agent || "" }).name);
      const label = isAgent ? agentLabel : modelLabel;
      const iconUrl = d.icon || getModelIconUrl(label);
      return {
        // Model-focused: model release date. Agent-focused: submission date.
        x: new Date(isAgent ? d.date : d[chartCfg.xField || "model_release_date"]),
        y: d[chartCfg.yField || "score_10"] * 100,
        label: label,
        focus: isAgent ? "agent" : "model",
        model: d.model,
        baseModel: d.base_model || d.model,
        icon: iconUrl,
        // Monochrome lobehub icons (currentColor/black) get inverted in dark mode.
        mono: !!iconUrl && /icons-static-svg/.test(iconUrl) && !/-color\.svg$/.test(iconUrl),
        size: Math.max(6, Math.round(ICON_SIZE * (d.icon_scale || 1))),
      };
    });
    // Agent-focused points link (dashed) to the model-focused point(s) they build on.
    // A row may list multiple base models via `plot_links` (e.g. a multi-model agent);
    // otherwise we fall back to its single `base_model`/`model`.
    points.forEach((p, idx) => {
      p.links = [];
      if (p.focus !== "agent") return;
      const names = plotData[idx].plot_links || [p.baseModel];
      names.forEach((name) => {
        const i = points.findIndex((q) => q.focus === "model" && q.model === name);
        if (i >= 0 && !p.links.includes(i)) p.links.push(i);
      });
    });

    const iconCache = {};
    await Promise.all(
      points.filter((p) => p.icon).map(async (p) => {
        const key = p.icon + "@" + p.size;
        if (!iconCache[key]) iconCache[key] = await loadIcon(p.icon, p.size);
      })
    );
    const pointImages = points.map((p) => (p.icon && iconCache[p.icon + "@" + p.size]) || "circle");
    const pointRadii = points.map((p) => p.size / 2);

    const PX_PER_MONTH = 56, PX_PER_10PCT = 56, AXIS_PADDING = 80;
    const minTime = Math.min(...points.map((p) => p.x.getTime()));
    const maxTime = Math.max(...points.map((p) => p.x.getTime()));
    const monthsSpan = (maxTime - minTime) / (30 * 86400000) + 3;
    const maxY = 100, minY = 0, ySpan = (maxY - minY) / 10;
    const chartWidth = Math.round(monthsSpan * PX_PER_MONTH + AXIS_PADDING);
    const chartHeight = Math.round(ySpan * PX_PER_10PCT + AXIS_PADDING);

    const container = canvas.parentElement;
    canvas.width = chartWidth;
    canvas.height = chartHeight;
    function scaleChart() {
      const availWidth = container.clientWidth;
      const scale = Math.min(1, availWidth / chartWidth);
      canvas.style.width = Math.round(chartWidth * scale) + "px";
      canvas.style.height = Math.round(chartHeight * scale) + "px";
    }
    scaleChart();
    window.addEventListener("resize", scaleChart);

    const col = chartColors();
    points.forEach((p, i) => { p.img = pointImages[i] === "circle" ? null : pointImages[i]; });
    const chart = new Chart(canvas, {
      type: "scatter",
      // Positions only — icons/labels/links are drawn by our plugins so we control per-point alpha.
      data: { datasets: [{ data: points, pointStyle: "circle", pointRadius: 0, pointHoverRadius: 0 }] },
      options: {
        responsive: false,
        animation: false,
        events: [],
        plugins: {
          legend: { display: false },
          tooltip: { enabled: false },
        },
        scales: {
          x: {
            type: "time",
            min: new Date(minTime - 30 * 86400000).toISOString(),
            max: new Date(maxTime + 60 * 86400000).toISOString(),
            time: { unit: "month", displayFormats: { month: "MMM yyyy" } },
            title: { display: true, text: chartCfg.xTitle || "Release Date", font: { size: 17 }, color: col.title },
            ticks: { color: col.tick, font: { size: 14 } },
            grid: { color: col.grid },
            border: { color: col.grid },
          },
          y: {
            min: minY, max: maxY,
            title: { display: true, text: chartCfg.yTitle || "Success Rate (%)", font: { size: 17 }, color: col.title },
            ticks: { color: col.tick, font: { size: 14 } },
            grid: { color: col.grid },
            border: { color: col.grid },
          },
        },
        layout: { padding: { top: 30, right: 20 } },
      },
      plugins: [linkPlugin(), iconPlugin(), labelPlugin(), hoverInfoPlugin()],
    });
    chart.hoverIndex = null;

    // Hover a point's icon → highlight it and the model it links to; dim the rest.
    function hitTest(mx, my) {
      const meta = chart.getDatasetMeta(0);
      let found = null, best = Infinity;
      meta.data.forEach((el, i) => {
        const img = points[i].img;
        const hw = (img ? img.width : points[i].size) / 2 + 3;
        const hh = (img ? img.height : points[i].size) / 2 + 3;
        if (Math.abs(mx - el.x) <= hw && Math.abs(my - el.y) <= hh) {
          const d = Math.hypot(mx - el.x, my - el.y);
          if (d < best) { best = d; found = i; }
        }
      });
      return found;
    }
    canvas.addEventListener("mousemove", (e) => {
      const rect = canvas.getBoundingClientRect();
      // Map display px → Chart.js logical space (chart.width/height), which is what
      // el.x/el.y use. Using canvas.width would be off by devicePixelRatio on HiDPI.
      const mx = (e.clientX - rect.left) * (chart.width / rect.width);
      const my = (e.clientY - rect.top) * (chart.height / rect.height);
      const idx = hitTest(mx, my);
      canvas.style.cursor = idx == null ? "" : "pointer";
      if (idx !== chart.hoverIndex) { chart.hoverIndex = idx; chart.draw(); }
    });
    canvas.addEventListener("mouseleave", () => {
      if (chart.hoverIndex != null) { chart.hoverIndex = null; chart.draw(); }
    });

    // Re-theme axes (and labels, via the plugin) when the user toggles theme.
    document.addEventListener("themechange", () => {
      const c = chartColors();
      ["x", "y"].forEach((ax) => {
        const s = chart.options.scales[ax];
        s.ticks.color = c.tick;
        s.grid.color = c.grid;
        s.border.color = c.grid;
        s.title.color = c.title;
      });
      chart.update();
    });
  }

  /* Draws the point icons (or a fallback dot), dimming non-active ones on hover. */
  function iconPlugin() {
    return {
      id: "iconPlugin",
      afterDatasetsDraw(chart) {
        const ctx = chart.ctx;
        const meta = chart.getDatasetMeta(0);
        const data = chart.data.datasets[0].data;
        const dot = chartColors().tick;
        const dark = document.documentElement.getAttribute("data-theme") === "dark";
        meta.data.forEach((el, i) => {
          const img = data[i].img;
          ctx.globalAlpha = activeOnHover(chart, i) ? 1 : 0.15;
          if (img) {
            const invert = dark && data[i].mono;
            if (invert) ctx.filter = "invert(1)";
            ctx.drawImage(img, el.x - img.width / 2, el.y - img.height / 2, img.width, img.height);
            if (invert) ctx.filter = "none";
          } else {
            ctx.fillStyle = dot;
            ctx.beginPath();
            ctx.arc(el.x, el.y, (data[i].size || 10) / 2, 0, Math.PI * 2);
            ctx.fill();
          }
        });
        ctx.globalAlpha = 1;
      },
    };
  }

  /* Dashed connector from an agent-focused point to the model-focused point it builds on. */
  function linkPlugin() {
    return {
      id: "linkPlugin",
      beforeDatasetsDraw(chart) {
        // Connector lines are only shown for the hovered icon (and its links).
        if (chart.hoverIndex == null) return;
        const ctx = chart.ctx;
        const meta = chart.getDatasetMeta(0);
        const data = chart.data.datasets[0].data;
        ctx.save();
        ctx.setLineDash([3, 3]);
        ctx.strokeStyle = chartColors().line;
        ctx.lineWidth = 1;
        data.forEach((p, i) => {
          const a = meta.data[i];
          if (!a || !p.links || !p.links.length || !activeOnHover(chart, i)) return;
          p.links.forEach((j) => {
            const b = meta.data[j];
            if (!b) return;
            ctx.beginPath();
            ctx.moveTo(a.x, a.y);
            ctx.lineTo(b.x, b.y);
            ctx.stroke();
          });
        });
        ctx.restore();
      },
    };
  }

  /* On hover, show the exact score (and date) for the hovered icon in a small box. */
  function hoverInfoPlugin() {
    return {
      id: "hoverInfoPlugin",
      afterDatasetsDraw(chart) {
        const h = chart.hoverIndex;
        if (h == null) return;
        const ctx = chart.ctx;
        const el = chart.getDatasetMeta(0).data[h];
        const d = chart.data.datasets[0].data[h];
        if (!el) return;
        const text = d.y.toFixed(1) + "%  ·  " + d.x.toISOString().slice(0, 10);
        ctx.save();
        ctx.font = "600 12px sans-serif";
        const pad = 6, bh = 22, tw = ctx.measureText(text).width, bw = tw + pad * 2;
        const area = chart.chartArea;
        let bx = el.x + 12, by = el.y - bh - 6;
        if (bx + bw > area.right) bx = el.x - bw - 12;
        if (bx < area.left) bx = area.left + 2;
        if (by < area.top) by = el.y + 8;
        ctx.fillStyle = "rgba(15,23,42,0.92)";
        if (ctx.roundRect) { ctx.beginPath(); ctx.roundRect(bx, by, bw, bh, 5); ctx.fill(); }
        else ctx.fillRect(bx, by, bw, bh);
        ctx.fillStyle = "#fff";
        ctx.textBaseline = "middle";
        ctx.textAlign = "left";
        ctx.fillText(text, bx + pad, by + bh / 2 + 1);
        ctx.restore();
      },
    };
  }

  /* Non-overlapping label placement plugin (unchanged logic). */
  function labelPlugin() {
    return {
      id: "labelPlugin",
      afterDatasetsDraw(chart) {
        const ctx = chart.ctx;
        const col = chartColors();
        const area = chart.chartArea;
        const meta = chart.getDatasetMeta(0);
        const data = chart.data.datasets[0].data;
        const GAP = 8; // point-to-label gap
        const LH = 19; // line height used for vertical de-overlap
        ctx.font = "16px sans-serif";
        ctx.textBaseline = "middle";

        const overlaps = (a, b) => a.l < b.r && a.r > b.l && a.t < b.b && a.b > b.t;
        // Every icon is an obstacle labels must dodge (not just their own point),
        // so labels don't land on top of neighbouring icons in dense clusters.
        const iconBoxes = meta.data.map((pt, i) => {
          const img = data[i].img;
          const half = (img ? Math.max(img.width, img.height) : (data[i].size || 12)) / 2 + 2;
          return { l: pt.x - half, r: pt.x + half, t: pt.y - half, b: pt.y + half };
        });

        // For each label try both sides and a range of vertical offsets, and take
        // the first position that clears every already-placed label and every icon.
        const offsets = [0];
        for (let k = 1; k <= 8; k++) { offsets.push(k * LH, -k * LH); }
        const placed = [];
        const order = meta.data.map((_, i) => i).sort((a, b) => meta.data[a].y - meta.data[b].y);
        order.forEach((i) => {
          const pt = meta.data[i];
          const text = data[i].label;
          if (!text) return;
          const w = ctx.measureText(text).width;
          const force = FORCE_LABEL_SIDE[text];
          const sides = force ? [force.startsWith("right")] : [true, false];
          let best = null, fallback = null;
          for (const right of sides) {
            const x = right ? pt.x + GAP : pt.x - GAP - w;
            if (x < area.left || x + w > area.right) continue; // keep inside the plot
            for (const dy of offsets) {
              const y = pt.y + dy;
              if (y < area.top + LH / 2 || y > area.bottom - LH / 2) continue;
              const box = { l: x, r: x + w, t: y - LH / 2, b: y + LH / 2 };
              if (!fallback) fallback = { x, y, w, right };
              if (placed.some((q) => overlaps(box, { l: q.x, r: q.x + q.w, t: q.y - LH / 2, b: q.y + LH / 2 }))) continue;
              if (iconBoxes.some((bx, j) => j !== i && overlaps(box, bx))) continue;
              best = { x, y, w, right };
              break;
            }
            if (best) break;
          }
          const c = best || fallback || { x: pt.x + GAP, y: pt.y, w, right: true };
          placed.push({ x: c.x, y: c.y, w, right: c.right, text, px: pt.x, py: pt.y, idx: i });
        });

        placed.forEach((l) => {
          ctx.globalAlpha = activeOnHover(chart, l.idx) ? 1 : 0.15;
          const anchorX = l.right ? l.x : l.x + l.w;
          if (Math.abs(l.y - l.py) > 3 || Math.abs(anchorX - l.px) > 12) {
            ctx.strokeStyle = col.line;
            ctx.lineWidth = 0.8;
            ctx.beginPath();
            ctx.moveTo(l.px, l.py);
            ctx.lineTo(anchorX, l.y);
            ctx.stroke();
          }
          ctx.fillStyle = col.label;
          ctx.textAlign = "left";
          ctx.fillText(l.text, l.x, l.y);
        });
        ctx.globalAlpha = 1;
      },
    };
  }

  window.CyberGymLeaderboard = { render, cells, esc };

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initNoteTooltips);
  } else {
    initNoteTooltips();
  }
})();
