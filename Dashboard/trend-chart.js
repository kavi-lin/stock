/**
 * trend-chart.js — reusable 3-day sentiment-trend chart.
 *
 * Extracted from page-break-news.js so both break-news.html (full mode:
 * entity selector + legend + hover cursor) and index.html (compact mode:
 * market-wide line only) can mount it.
 *
 * Usage:
 *   const inst = TrendChart.mount({ root, compact, withSelector });
 *   inst.refresh();   // re-render text + chart (e.g. after a language toggle)
 *   inst.reload();    // re-fetch /api/break-news/trends
 *
 * Self-contained: injects its own CSS once, carries its own i18n. Only
 * external dependency is window.UI.currentLang (optional — defaults to en).
 */
window.TrendChart = (function () {
  'use strict';

  const ENDPOINT  = '/api/break-news/trends';
  const CACHE_MS  = 30000;                 // share one fetch across instances
  let _cache = null, _cacheTs = 0, _inflight = null;
  let _seq = 0;                            // instance counter → unique SVG ids

  function isZh() { return !!(window.UI && window.UI.currentLang === 'zh'); }
  function t(zh, en) { return isZh() ? zh : en; }
  function esc(s) {
    return String(s == null ? '' : s).replace(/[&<>"]/g, c =>
      ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
  }
  // Precise time — used by the hover tooltip only.
  function fmtTick(iso) {
    const d = new Date(iso);
    if (isNaN(d)) return '';
    return `${d.getMonth() + 1}/${d.getDate()} `
      + `${String(d.getHours()).padStart(2, '0')}:00`;
  }
  const _WD_ZH = ['日', '一', '二', '三', '四', '五', '六'];
  const _WD_EN = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
  // Date + weekday — clean x-axis label, no hour noise.
  function fmtDay(iso) {
    const d = new Date(iso);
    if (isNaN(d)) return '';
    const wd = isZh() ? _WD_ZH[d.getDay()] : _WD_EN[d.getDay()];
    return `${d.getMonth() + 1}/${d.getDate()} ${wd}`;
  }
  // x-axis ticks anchored to local calendar days: the first entry is the window
  // start, every later entry is a local-midnight boundary (gets a divider line).
  function _dayTicks(labels) {
    const out = [];
    let prevDay = null;
    for (let i = 0; i < labels.length; i++) {
      const d = new Date(labels[i]);
      if (isNaN(d)) continue;
      const key = `${d.getFullYear()}-${d.getMonth()}-${d.getDate()}`;
      if (key !== prevDay) {
        out.push({ i, label: fmtDay(labels[i]), boundary: prevDay !== null });
        prevDay = key;
      }
    }
    return out;
  }

  function injectCSS() {
    if (document.getElementById('trend-chart-css')) return;
    const arrow = "data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' "
      + "width='10' height='10' viewBox='0 0 10 10'><path d='M1 3l4 4 4-4' "
      + "stroke='%2371717a' stroke-width='1.6' fill='none'/></svg>";
    const css = `
      .trend-head{display:flex;align-items:center;gap:12px;flex-wrap:wrap;margin-bottom:8px;}
      .trend-title{font-size:12px;font-weight:800;letter-spacing:.08em;
        text-transform:uppercase;color:var(--text-main);}
      .trend-select{font-size:11px;font-weight:700;padding:4px 26px 4px 10px;
        border-radius:8px;cursor:pointer;background:rgba(255,255,255,0.04);
        border:1px solid rgba(255,255,255,0.12);color:var(--text-main);appearance:none;
        background-image:url("${arrow}");background-repeat:no-repeat;
        background-position:right 9px center;}
      .trend-now{font-family:'JetBrains Mono',monospace;font-size:13px;
        font-weight:800;letter-spacing:.02em;}
      .trend-meta{margin-left:auto;font-size:10px;color:var(--text-muted);
        font-family:'JetBrains Mono',monospace;}
      .trend-chart{position:relative;}
      .trend-svg{display:block;width:100%;height:auto;}
      .trend-cursor{position:absolute;top:0;pointer-events:none;
        background:rgba(9,9,11,0.94);border:1px solid rgba(161,161,170,0.4);
        border-radius:6px;padding:4px 8px;font-size:10px;
        font-family:'JetBrains Mono',monospace;color:var(--text-main);
        white-space:nowrap;transform:translateX(-50%);display:none;z-index:5;}
      .trend-legend{display:flex;gap:14px;margin-top:4px;font-size:9.5px;
        color:var(--text-muted);font-family:'JetBrains Mono',monospace;}
      .trend-empty{text-align:center;color:var(--text-muted);font-size:11px;padding:30px 20px;}
      /* x-axis labels rendered as HTML overlay so they stay a fixed px size
         regardless of how wide the SVG is scaled (SVG <text> would balloon). */
      .trend-xaxis{position:absolute;left:0;right:0;bottom:0;height:13px;pointer-events:none;}
      .trend-xlabel{position:absolute;bottom:0;font-size:9px;line-height:1;
        color:var(--text-muted);font-family:'JetBrains Mono',monospace;white-space:nowrap;}
      .trend-nowlabel{position:absolute;font-size:8px;font-weight:700;line-height:1;
        font-family:'JetBrains Mono',monospace;white-space:nowrap;pointer-events:none;
        transform:translate(-108%,-150%);}
      .trend-compact .trend-title{font-size:10px;}
      .trend-compact .trend-empty{padding:16px 20px;}`;
    const el = document.createElement('style');
    el.id = 'trend-chart-css';
    el.textContent = css;
    document.head.appendChild(el);
  }

  async function fetchData(force) {
    const now = Date.now();
    if (!force && _cache && (now - _cacheTs) < CACHE_MS) return _cache;
    if (_inflight) return _inflight;
    _inflight = (async () => {
      const r = await fetch(ENDPOINT);
      if (!r.ok) throw new Error(`${r.status} ${r.statusText}`);
      _cache = await r.json();
      _cacheTs = Date.now();
      _inflight = null;
      return _cache;
    })();
    try { return await _inflight; }
    catch (e) { _inflight = null; throw e; }
  }

  // Hand-rolled SVG area chart: one line crossing a zero baseline, green fill
  // above / red below. `H` controls height (compact uses a shorter chart).
  // All strokes use vector-effect:non-scaling-stroke so the line stays a fixed
  // pixel width however wide the SVG is scaled; x-axis + "now" labels are HTML
  // overlays (not SVG <text>) so their font size never balloons with scale.
  function buildSVG(values, labels, H, idn) {
    const W = 760, padL = 6, padR = 6, padT = 8, padB = 18;
    const plotW = W - padL - padR, plotH = H - padT - padB;
    const base = padT + plotH / 2;
    const n = values.length;
    const xAt = i => padL + (n <= 1 ? 0 : (i / (n - 1)) * plotW);
    const yAt = v => base - Math.max(-1, Math.min(1, v)) * (plotH / 2);
    const pctX = x => (x / W * 100).toFixed(2);
    const linePts = values.map((v, i) => `${xAt(i).toFixed(1)},${yAt(v).toFixed(1)}`).join(' ');
    const area = `${xAt(0).toFixed(1)},${base.toFixed(1)} ${linePts} `
      + `${xAt(n - 1).toFixed(1)},${base.toFixed(1)}`;
    const g1 = yAt(0.5).toFixed(1), g2 = yAt(-0.5).toFixed(1);
    const NS = 'vector-effect="non-scaling-stroke"';

    // x-axis: SVG day-boundary dividers + HTML date labels (collision-skipped).
    let dividers = '', dayLabels = '';
    let lastPct = -99;
    _dayTicks(labels).forEach(tk => {
      const x = xAt(tk.i), p = x / W * 100;
      if (tk.boundary) {
        dividers += `<line x1="${x.toFixed(1)}" x2="${x.toFixed(1)}" `
          + `y1="${padT}" y2="${(H - padB).toFixed(1)}" `
          + `stroke="rgba(128,128,128,0.16)" stroke-width="1" ${NS}/>`;
      }
      if (p - lastPct < 8) return;          // skip labels that would collide
      lastPct = p;
      const atEnd = p > 86;
      dayLabels += `<span class="trend-xlabel" style="left:${p.toFixed(2)}%;`
        + `${atEnd ? 'transform:translateX(-100%);' : ''}">${esc(tk.label)}</span>`;
    });

    const lastV = values[n - 1];
    const nowX = xAt(n - 1), nowY = yAt(lastV);
    const nowColor = lastV > 0.05 ? '#22c55e' : lastV < -0.05 ? '#ef4444' : '#a1a1aa';
    const cu = `trend-clip-up-${idn}`, cd = `trend-clip-dn-${idn}`;
    const svg = `<svg class="trend-svg" viewBox="0 0 ${W} ${H}">
      <defs>
        <clipPath id="${cu}"><rect x="0" y="0" width="${W}" height="${base}"/></clipPath>
        <clipPath id="${cd}"><rect x="0" y="${base}" width="${W}" height="${H - base}"/></clipPath>
      </defs>
      ${dividers}
      <line x1="${padL}" x2="${W - padR}" y1="${g1}" y2="${g1}" stroke="rgba(128,128,128,0.12)" ${NS}/>
      <line x1="${padL}" x2="${W - padR}" y1="${g2}" y2="${g2}" stroke="rgba(128,128,128,0.12)" ${NS}/>
      <polygon points="${area}" fill="#22c55e" opacity="0.16" clip-path="url(#${cu})"/>
      <polygon points="${area}" fill="#ef4444" opacity="0.16" clip-path="url(#${cd})"/>
      <polyline points="${linePts}" fill="none" stroke="#22c55e" stroke-width="1.3"
        stroke-linejoin="round" clip-path="url(#${cu})" ${NS}/>
      <polyline points="${linePts}" fill="none" stroke="#ef4444" stroke-width="1.3"
        stroke-linejoin="round" clip-path="url(#${cd})" ${NS}/>
      <line x1="${padL}" x2="${W - padR}" y1="${base}" y2="${base}"
        stroke="rgba(161,161,170,0.55)" stroke-width="1" stroke-dasharray="3 3" ${NS}/>
      <circle cx="${nowX.toFixed(1)}" cy="${nowY.toFixed(1)}" r="2.2" fill="${nowColor}"/>
    </svg>
    <span class="trend-nowlabel" style="left:${pctX(nowX)}%;top:${(nowY / H * 100).toFixed(2)}%;`
      + `color:${nowColor};">${esc(t('現在', 'now'))}</span>
    <div class="trend-xaxis">${dayLabels}</div>`;
    return svg;
  }

  function entityLabel(e) {
    if (!e) return '';
    if (e.kind === 'all') return t('市場共識', 'Market Consensus');
    if (e.kind === 'pulse') return t('即時脈搏', 'Raw Pulse');
    return e.label;
  }

  function Instance(opts) {
    this.id = ++_seq;
    this.root = opts.root;
    this.compact = !!opts.compact;
    this.withSelector = !!opts.withSelector && !this.compact;
    this.entity = '__ALL__';
    this.data = null;
    this._buildSkeleton();
  }

  Instance.prototype._q = function (sub) {
    return this.root.querySelector(`#trend-${sub}-${this.id}`);
  };

  Instance.prototype._buildSkeleton = function () {
    const idn = this.id;
    if (this.compact) this.root.classList.add('trend-compact');
    const selHtml = this.withSelector
      ? `<select class="trend-select" id="trend-sel-${idn}"></select>` : '';
    const legendHtml = this.compact ? '' :
      `<div class="trend-legend" id="trend-legend-${idn}" style="display:none;">
         <span>▲ <span id="trend-lgbull-${idn}"></span></span>
         <span>▼ <span id="trend-lgbear-${idn}"></span></span>
         <span id="trend-lghint-${idn}"></span>
       </div>`;
    this.root.innerHTML =
      `<div class="trend-head">
         <span class="trend-title" id="trend-title-${idn}"></span>
         ${selHtml}
         <span class="trend-now" id="trend-now-${idn}"></span>
         <span class="trend-meta" id="trend-meta-${idn}"></span>
       </div>
       <div class="trend-chart" id="trend-chart-${idn}">
         <div class="trend-empty">${t('載入中…', 'Loading…')}</div>
       </div>` + legendHtml;
    if (this.withSelector) {
      this._q('sel').addEventListener('change', (e) => {
        this.entity = e.target.value;
        this.renderChart();
      });
    }
  };

  Instance.prototype._populateSelect = function () {
    const sel = this._q('sel');
    if (!sel || !this.data) return;
    const ents = this.data.entities || [];
    if (!ents.some(e => e.key === this.entity))
      this.entity = ents.length ? ents[0].key : '__ALL__';
    const groups = { all: [], pulse: [], sector: [], theme: [] };
    ents.forEach(e => (groups[e.kind] || groups.all).push(e));
    const headOpts = groups.all.concat(groups.pulse).map(e =>
      `<option value="${esc(e.key)}">${esc(entityLabel(e))}</option>`).join('');
    const grp = (key, zh, en) => {
      if (!groups[key].length) return '';
      const opts = groups[key].map(e =>
        `<option value="${esc(e.key)}">${esc(e.label)} (${e.events})</option>`).join('');
      return `<optgroup label="${t(zh, en)}">${opts}</optgroup>`;
    };
    sel.innerHTML = headOpts + grp('sector', '產業', 'Sectors') + grp('theme', '主題', 'Themes');
    sel.value = this.entity;
  };

  Instance.prototype._wireCursor = function (series, labels) {
    const chart = this._q('chart');
    const svg = chart && chart.querySelector('svg');
    const cursor = chart && chart.querySelector('.trend-cursor');
    if (!svg || !cursor) return;
    const n = series.length;
    svg.addEventListener('mousemove', (ev) => {
      const r = svg.getBoundingClientRect();
      const fx = Math.max(0, Math.min(1, (ev.clientX - r.left) / r.width));
      const i = Math.max(0, Math.min(n - 1, Math.round(fx * (n - 1))));
      const v = series[i];
      const vc = v > 0.05 ? '#22c55e' : v < -0.05 ? '#ef4444' : '#a1a1aa';
      cursor.style.display = 'block';
      cursor.style.left = (fx * 100) + '%';
      cursor.innerHTML = `${esc(fmtTick(labels[i] || ''))} · `
        + `<strong style="color:${vc};">${v > 0 ? '+' : ''}${v.toFixed(2)}</strong>`;
    });
    svg.addEventListener('mouseleave', () => { cursor.style.display = 'none'; });
  };

  Instance.prototype.renderChart = function () {
    const idn = this.id;
    const titleEl = this._q('title');
    if (titleEl) titleEl.textContent = this.compact
      ? t('市場共識趨勢', 'Market Consensus')
      : t('3 日新聞情緒', '3-Day News Sentiment');
    const chart = this._q('chart');
    if (!chart || !this.data) return;
    const legend = this._q('legend');
    const nowEl = this._q('now');
    const meta = this._q('meta');
    // compact mode is locked to the whole-market series
    const key = this.compact ? '__ALL__' : this.entity;
    const series = (this.data.series || {})[key];
    const labels = this.data.series_labels || [];
    if (meta)
      meta.textContent = `${this.data.market_event_count || 0}/${this.data.log_count || 0} ${t('則共識', 'consensus')}`
        + ` · ${this.data.raw_pulse_count || 0} ${t('則脈搏', 'pulse')}`
        + ` · ½-life ${this.data.half_life_hours || 12}h`;
    if (!series || !series.length) {
      chart.innerHTML = `<div class="trend-empty">${t('資料不足', 'Not enough data')}</div>`;
      if (legend) legend.style.display = 'none';
      if (nowEl) nowEl.textContent = '';
      return;
    }
    const H = this.compact ? 92 : 150;
    chart.innerHTML = buildSVG(series, labels, H, idn)
      + '<div class="trend-cursor"></div>';
    const last = series[series.length - 1];
    if (nowEl) {
      nowEl.textContent = `${last > 0 ? '+' : ''}${last.toFixed(2)}`;
      nowEl.style.color = last > 0.05 ? '#22c55e' : last < -0.05 ? '#ef4444' : '#a1a1aa';
    }
    if (legend) {
      legend.style.display = 'flex';
      const lb = this._q('lgbull'), lr = this._q('lgbear'), lh = this._q('lghint');
      if (lb) lb.textContent = t('看多', 'bullish');
      if (lr) lr.textContent = t('看空', 'bearish');
      if (lh) lh.textContent = t('滑過看任一時點', 'hover for any point');
    }
    this._wireCursor(series, labels);
  };

  Instance.prototype.refresh = function () {
    if (this.withSelector) this._populateSelect();
    this.renderChart();
  };

  Instance.prototype.reload = async function () {
    try {
      this.data = await fetchData(true);
      this.refresh();
    } catch (e) {
      const chart = this._q('chart');
      if (chart) chart.innerHTML =
        `<div class="trend-empty">${t('趨勢載入失敗', 'Trend load failed')}</div>`;
    }
  };

  Instance.prototype.load = async function () {
    try {
      this.data = await fetchData(false);
      this.refresh();
    } catch (e) {
      const chart = this._q('chart');
      if (chart) chart.innerHTML =
        `<div class="trend-empty">${t('趨勢載入失敗', 'Trend load failed')}</div>`;
    }
  };

  return {
    mount(opts) {
      injectCSS();
      const inst = new Instance(opts);
      inst.load();
      return inst;
    },
  };
})();
