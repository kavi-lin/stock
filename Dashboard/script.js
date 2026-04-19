/**
 * script.js — index.html page presenter
 * Depends on: utils.js (window.UI), components.js (window.Components), i18n.js
 */

// ── Page-specific translations ────────────────────────────────────────────
function applyTranslations() {
  if (!window.i18n) return;
  const t = window.i18n[UI.currentLang];
  const o = t.overview || {};
  const keys = [
    'market_regime', 'hot_themes', 'sentiment', 'recent_audit', 'catalyst',
    'quick_launch', 'launch_desc', 'start_btn',
    // Action Posture / header keys added in v1.2.0
    'market_status', 'operator', 'conviction_title',
    'action_posture', 'action_posture_desc',
    'regime_label', 'exposure_label', 'exposure_hint',
    'view_all',
  ];
  keys.forEach(k => {
    const el = document.querySelector(`[data-i18n="${k}"]`);
    if (el && o[k]) el.textContent = o[k];
  });
}

// ── i18n helper ───────────────────────────────────────────────────────────
function sig() { return window.i18n?.[UI.currentLang]?.signals || {}; }
function ov()  { return window.i18n?.[UI.currentLang]?.overview || {}; }

// ── Composite Signal Score ─────────────────────────────────────────────────
function computeConviction(data) {
  const ftd = data.ftd        || {};
  const br  = data.breadth    || {};
  const mkt = data.market     || {};
  const mt  = data.market_top || {};

  let ftdComp = 45;
  const state = ftd.state || '';
  if (!ftd.invalidated) {
    if      (state === 'FTD_CONFIRMED')                    ftdComp = 55 + (ftd.quality_score || 50) * 0.45;
    else if (state === 'FTD_WINDOW')                       ftdComp = 62;
    else if (state === 'RALLY_ATTEMPT')                    ftdComp = 55;
    else if (state === 'CORRECTION' || state === 'RALLY_FAILED') ftdComp = 18;
    else if (state === 'FTD_INVALIDATED')                  ftdComp = 12;
  } else { ftdComp = 12; }

  const breadthComp = br.score          ?? 50;
  const sentComp    = 100 - (mkt.fear_greed ?? 50);
  const topRiskComp = 100 - (mt.composite_score ?? 50);
  const uptrendComp = (mkt.uptrend_ratio ?? 0.5) * 100;

  const score = Math.round(
    ftdComp      * 0.35 +
    breadthComp  * 0.25 +
    sentComp     * 0.15 +
    topRiskComp  * 0.15 +
    uptrendComp  * 0.10
  );

  const cv = sig().conviction || {};
  const label =
    score >= 80 ? (cv.STRONG_BULL || 'Strong Bull') :
    score >= 65 ? (cv.BULLISH     || 'Bullish')     :
    score >= 50 ? (cv.MIXED       || 'Mixed')       :
    score >= 35 ? (cv.CAUTIOUS    || 'Cautious')    :
    score >= 20 ? (cv.BEARISH     || 'Bearish')     : (cv.STRONG_BEAR || 'Strong Bear');

  const color =
    score >= 65 ? '#22c55e' :
    score >= 50 ? '#86efac' :
    score >= 35 ? '#eab308' :
    score >= 20 ? '#f97316' : '#ef4444';

  const dr = sig().drivers || {};
  const drivers = [
    { label: dr.ftd       || 'FTD',       val: ftdComp,     bull: ftdComp     >= 60 },
    { label: dr.breadth   || 'Breadth',   val: breadthComp, bull: breadthComp >= 55 },
    { label: dr.sentiment || 'Sentiment', val: sentComp,    bull: sentComp    >= 60 },
    { label: dr.top_risk  || 'Top Risk',  val: topRiskComp, bull: topRiskComp >= 60 },
    { label: dr.uptrend   || 'Uptrend',   val: uptrendComp, bull: uptrendComp >= 55 },
  ].sort((a, b) => Math.abs(b.val - 50) - Math.abs(a.val - 50));

  const topBull = drivers.filter(d => d.bull).slice(0, 2).map(d => d.label);
  const topBear = drivers.filter(d => !d.bull).slice(0, 2).map(d => d.label);

  let summary = '';
  if (topBull.length && topBear.length)
    summary = `↑ ${topBull.join(' + ')} 偏多；↓ ${topBear.join(' + ')} 仍偏弱。`;
  else if (topBull.length)
    summary = `多方動能明確：${topBull.join(' + ')}。`;
  else
    summary = `空方壓力來自：${topBear.join(' + ')}。`;

  const ftdExp = ftd.exposure_range  || '';
  const brExp  = br.exposure_ceiling || mkt.exposure_ceiling || '';
  const mtExp  = mt.risk_budget      || '';
  if (ftdExp || brExp || mtExp)
    summary += `  建議倉位參考：FTD ${ftdExp || '–'} · 廣度 ${brExp || '–'} · 頂部風控 ${mtExp || '–'}`;

  const comp = sig().components || {};
  const ftdStates = sig().ftd_states || {};
  const fgMap     = sig().fg_labels  || {};
  return {
    score, label, color,
    components: [
      { key: comp.ftd       || 'FTD Signal',      raw: Math.round(ftdComp),     pct: Math.round(ftdComp),     bull: ftdComp     >= 55, tag: ftdStates[ftd.state] || ftd.state || '–' },
      { key: comp.breadth   || 'Market Breadth',  raw: Math.round(breadthComp), pct: breadthComp,              bull: breadthComp >= 55, tag: br.zone   || '–' },
      { key: comp.sentiment || 'Sentiment (Ctr)', raw: Math.round(sentComp),    pct: sentComp,                 bull: sentComp    >= 60, tag: fgMap[mkt.fear_greed_label] || mkt.fear_greed_label || '–' },
      { key: comp.top_risk  || 'Top Risk (Inv)',  raw: Math.round(topRiskComp), pct: topRiskComp,              bull: topRiskComp >= 60, tag: mt.zone   || '–' },
      { key: comp.uptrend   || 'Uptrend Ratio',   raw: Math.round(uptrendComp), pct: uptrendComp,              bull: uptrendComp >= 55, tag: Math.round(uptrendComp) + '%' },
    ],
    summary,
  };
}

// ── Signal Angle Cards (Row 2) ─────────────────────────────────────────────
function renderSignalAngles(data) {
  const grid = document.getElementById('signal-angle-grid');
  if (!grid) return;
  const ftd = data.ftd || {}, br = data.breadth || {}, mkt = data.market || {}, mt = data.market_top || {};
  const fg = mkt.fear_greed ?? 50;
  const s  = sig();
  const fgRaw    = fg < 25 ? 'Extreme Fear' : fg < 45 ? 'Fear' : fg < 55 ? 'Neutral' : fg < 75 ? 'Greed' : 'Extreme Greed';
  const fgMap2   = s.fg_labels || {};
  const fgLabel  = fgMap2[fgRaw] || fgRaw;
  const fgSuffix = fgMap2.contrarian_suffix || ' (Ctr)';
  const fgColor  = fg < 25 ? '#22c55e' : fg < 45 ? '#86efac' : fg < 55 ? '#eab308' : fg < 75 ? '#f97316' : '#ef4444';

  const ftdStates2   = s.ftd_states   || {};
  const topZones     = s.top_zones    || {};
  const uptrendLbls  = s.uptrend_labels || {};
  const cards        = s.cards         || {};
  const topZoneClean = (mt.zone || '').replace(/\(.*\)/, '').trim();
  const topColor     = (mt.composite_score ?? 0) <= 20 ? '#22c55e' : (mt.composite_score ?? 0) <= 40 ? '#eab308'
                     : (mt.composite_score ?? 0) <= 60 ? '#f97316' : '#ef4444';
  const uptrendRatio = mkt.uptrend_ratio ?? 0;

  const angles = [
    {
      icon: 'signal', label: cards.ftd || 'FTD Signal', link: 'sector.html',
      val: ftd.quality_score != null ? ftd.quality_score : '–',
      sub: ftdStates2[ftd.state] || ftdStates2.default || 'No Signal',
      color: ftd.state === 'FTD_CONFIRMED' && !ftd.invalidated ? '#22c55e'
           : ftd.state === 'FTD_WINDOW' || ftd.state === 'RALLY_ATTEMPT' ? '#eab308' : '#ef4444',
      bar: ftd.quality_score ?? 0,
    },
    {
      icon: 'alert-triangle', label: cards.top_risk || 'Top Risk', link: 'sector.html',
      val: mt.composite_score != null ? mt.composite_score : '–',
      sub: topZones[topZoneClean] || topZoneClean || '–',
      color: topColor,
      bar: mt.composite_score ?? 0,
    },
    {
      icon: 'heart-pulse', label: cards.sentiment || 'Sentiment', link: 'news.html',
      val: fg,
      sub: fgLabel + fgSuffix,
      color: fgColor,
      bar: 100 - fg,
    },
    {
      icon: 'trending-up', label: cards.uptrend || 'Uptrend %', link: 'sector.html',
      val: Math.round(uptrendRatio * 100) + '%',
      sub: uptrendRatio >= 0.6 ? (uptrendLbls.healthy || 'Healthy')
         : uptrendRatio >= 0.4 ? (uptrendLbls.neutral || 'Neutral')
                                : (uptrendLbls.weak    || 'Weak'),
      color: uptrendRatio >= 0.6 ? '#22c55e' : uptrendRatio >= 0.4 ? '#eab308' : '#ef4444',
      bar: Math.round(uptrendRatio * 100),
    },
  ];

  grid.innerHTML = angles.map(a => `
    <a href="${a.link}" class="glass-card p-4 flex flex-col gap-2 hover:border-zinc-600/50 transition-all cursor-pointer group">
      <div class="flex items-center justify-between">
        <span class="text-[9px] font-black text-zinc-500 uppercase tracking-widest">${a.label}</span>
        <i data-lucide="${a.icon}" class="w-3.5 h-3.5 text-zinc-600 group-hover:text-zinc-400 transition-colors"></i>
      </div>
      <div class="text-2xl font-black tracking-tighter leading-none" style="color:${a.color}">${a.val}</div>
      <div class="w-full h-1.5 rounded-full bg-zinc-200 dark:bg-zinc-800">
        <div class="h-1.5 rounded-full transition-all duration-700" style="width:${Math.min(100, a.bar)}%;background-color:${a.color}"></div>
      </div>
      <div class="text-[9px] font-bold uppercase tracking-wide" style="color:${a.color}">${a.sub}</div>
    </a>
  `).join('');
}

// ── Dashboard Update ───────────────────────────────────────────────────────
async function updateDashboard() {
  UI.logToUI('Refreshing system synchronization...');
  UI.updateMarketStatus();
  let data = null;

  try {
    data = await DataStore.get(true);

    // 1. Composite Conviction Hero
    const conv      = computeConviction(data);
    const scoreEl   = document.getElementById('composite-score');
    const barEl     = document.getElementById('composite-bar');
    const labelEl   = document.getElementById('composite-label');
    const summaryEl = document.getElementById('conviction-summary');
    const compBars  = document.getElementById('component-bars');

    if (scoreEl)   { scoreEl.textContent = conv.score; scoreEl.style.color = conv.color; }
    if (barEl)     { barEl.style.width = conv.score + '%'; barEl.style.backgroundColor = conv.color; }
    if (labelEl)   { labelEl.textContent = conv.label; labelEl.style.color = conv.color; }
    if (summaryEl) summaryEl.textContent = conv.summary;

    if (compBars) {
      const comp2 = sig().components || {};
      const wt = {
        [comp2.ftd       || 'FTD Signal']:      35,
        [comp2.breadth   || 'Market Breadth']:  25,
        [comp2.sentiment || 'Sentiment (Ctr)']: 15,
        [comp2.top_risk  || 'Top Risk (Inv)']:  15,
        [comp2.uptrend   || 'Uptrend Ratio']:   10,
      };
      compBars.innerHTML = conv.components.map(c => {
        const col = c.bull ? '#22c55e' : (c.pct >= 40 ? '#eab308' : '#ef4444');
        return `
        <div class="flex items-center gap-3">
          <div class="w-28 shrink-0 flex items-center gap-1">
            <span class="text-[9px] font-bold text-zinc-500 uppercase tracking-wide truncate">${c.key}</span>
            <span class="text-[8px] text-zinc-700 shrink-0">${wt[c.key] || 0}%</span>
          </div>
          <div class="flex-1 h-1.5 rounded-full bg-zinc-200 dark:bg-zinc-800">
            <div class="h-1.5 rounded-full transition-all duration-700" style="width:${Math.min(100,c.pct)}%;background-color:${col}"></div>
          </div>
          <span class="text-[10px] font-black font-mono w-7 text-right shrink-0" style="color:${col}">${c.raw}</span>
          <span class="text-[9px] text-zinc-600 w-24 truncate shrink-0">${c.tag}</span>
        </div>`;
      }).join('');
    }

    // 2. Verdict Card
    const regimeEl = document.getElementById('regime-text');
    const expEl    = document.getElementById('exposure-ceiling-val');
    const flagsEl  = document.getElementById('flags-compact');

    if (regimeEl) {
      const regimeKey  = data.market?.regime || '';
      const regimeMap  = sig().regime || {};
      const rCol       = { RISK_ON: '#22c55e', RISK_OFF: '#ef4444', VOLATILE: '#eab308', NEUTRAL: '#71717a' };
      regimeEl.textContent = regimeMap[regimeKey] || regimeKey || '–';
      regimeEl.style.color = rCol[regimeKey] || 'var(--primary)';
      const regimeSubEl = document.getElementById('regime-sub');
      if (regimeSubEl) regimeSubEl.textContent = regimeKey;
    }
    const expOptions = [data.ftd?.exposure_range, data.breadth?.exposure_ceiling, data.market?.exposure_ceiling].filter(Boolean);
    if (expEl) expEl.textContent = expOptions[0] || '–';

    if (flagsEl) {
      const tw    = window.i18n?.[UI.currentLang]?.warnings || {};
      const flags = data.market?.warning_flags || [];
      if (flags.length) {
        flagsEl.innerHTML =
          `<p class="text-[9px] font-black text-zinc-600 uppercase tracking-widest mb-1.5 flex items-center gap-1">
             <i data-lucide="alert-triangle" class="w-3 h-3 text-yellow-500"></i> ${flags.length} ${ov().flags_active || 'Flag(s) Active'}
           </p>` +
          flags.slice(0, 3).map(f => Components.flagBadge(f, tw.flags)).join('');
      } else {
        flagsEl.innerHTML = `<div class="text-[9px] font-bold text-emerald-500 flex items-center gap-1"><i data-lucide="shield-check" class="w-3 h-3"></i> ${ov().no_flags || 'No Active Flags'}</div>`;
      }
    }

    // 3. Signal Angle Cards
    renderSignalAngles(data);

    // 4. Recent Analysis (compact list)
    const condensedGrid = document.getElementById('audit-grid-condensed');
    const fullGrid      = document.getElementById('audit-grid-full');
    if (condensedGrid) {
      condensedGrid.innerHTML = '';
      data.recent_analysis?.slice(0, 3).forEach(item => condensedGrid.appendChild(Components.renderAuditCard(item, true)));
    }
    if (fullGrid) {
      fullGrid.innerHTML = '';
      data.recent_analysis?.forEach(item => fullGrid.appendChild(Components.renderAuditCard(item, false)));
    }

  } catch (error) {
    UI.logToUI(error.message, 'error');
    console.error('Dashboard update failed:', error);
  } finally {
    UI.icons();
    const syncEl = document.getElementById('last-update');
    if (syncEl && data?.last_updated) syncEl.textContent = `SYNC: ${data.last_updated}`;
    UI.logToUI('System update cycle complete.');
  }
}

// ── Launch Engine (reverse-call to Claude via /api/run-protocol) ──────────
let _launchPollTimer = null;

function formatElapsed(sec) {
  const m = String(Math.floor(sec / 60)).padStart(2, '0');
  const s = String(sec % 60).padStart(2, '0');
  return `${m}:${s}`;
}

function setLaunchStatus(status, text) {
  const box  = document.getElementById('launch-status');
  const sbox = document.getElementById('launch-status-box');
  const icon = document.getElementById('launch-status-icon');
  const txt  = document.getElementById('launch-status-text');
  const hint = document.getElementById('launch-status-hint');
  if (!box) return;
  box.classList.remove('hidden');
  txt.textContent = text || status;
  const isZh = UI.currentLang === 'zh';
  if (status === 'running') {
    sbox.className = 'rounded-lg px-3 py-2.5 flex items-center justify-between gap-2 border border-emerald-500/40 bg-emerald-500/5';
    icon.innerHTML = '<span class="inline-block w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>';
    hint.textContent = isZh ? 'Claude 正在分析中，請稍候...' : 'Claude is analyzing, please wait...';
  } else if (status === 'done') {
    sbox.className = 'rounded-lg px-3 py-2.5 flex items-center justify-between gap-2 border border-emerald-500/40 bg-emerald-500/10';
    icon.innerHTML = '<span class="text-emerald-400">✓</span>';
    hint.textContent = isZh ? '分析完成，Dashboard 已更新' : 'Analysis complete, Dashboard refreshed';
  } else if (status === 'error') {
    sbox.className = 'rounded-lg px-3 py-2.5 flex items-center justify-between gap-2 border border-red-500/40 bg-red-500/5';
    icon.innerHTML = '<span class="text-red-400">✗</span>';
    hint.textContent = '';
  }
}

async function pollLaunchStatus() {
  try {
    const r = await fetch('/api/run-protocol/status');
    if (!r.ok) return;
    const s = await r.json();
    const isZh = UI.currentLang === 'zh';
    document.getElementById('launch-elapsed').textContent = formatElapsed(s.elapsed_sec || 0);
    // Invest protocols render inside the analyze-queue widget — suppress the
    // legacy launch-status banner to avoid duplicating "analyzing NVDA 07:30".
    if (s.name === 'invest') {
      document.getElementById('launch-status')?.classList.add('hidden');
      if (s.status !== 'running' && _launchPollTimer) {
        clearInterval(_launchPollTimer); _launchPollTimer = null;
      }
      return;
    }
    if (s.status === 'running') {
      setLaunchStatus('running', isZh ? `正在執行 ${s.name || ''}...` : `Running ${s.name || ''}...`);
    } else {
      if (_launchPollTimer) { clearInterval(_launchPollTimer); _launchPollTimer = null; }
      if (s.status === 'done') {
        setLaunchStatus('done', isZh ? '分析完成' : 'Done');
        setTimeout(() => document.getElementById('launch-status')?.classList.add('hidden'), 8000);
      } else if (s.status === 'error' || s.status === 'cancelled') {
        setLaunchStatus('error', s.error || s.status);
      }
    }
  } catch (e) { /* ignore */ }
}

async function launchAnalysis() {
  const input = document.getElementById('ticker-input');
  if (!input) return;
  const ticker = input.value.trim().toUpperCase();
  if (!ticker) return;
  const isZh = UI.currentLang === 'zh';
  const confirmMsg = isZh
    ? `加入個股分析佇列：${ticker}（risk=${UI.riskTolerance}）？\nV4.8 每檔約 10-15 分鐘，~$4 tokens。重複者（排隊中或分析中）會被忽略。`
    : `Enqueue invest analysis for ${ticker} (risk=${UI.riskTolerance})?\nV4.8 ~10-15 min per ticker, ~$4 tokens. Duplicates are abandoned.`;
  if (!confirm(confirmMsg)) return;

  try {
    if (window.AnalyzeQueue) {
      await window.AnalyzeQueue.enqueue(ticker);
      input.value = '';
      UI.logToUI(`Enqueued: invest ${ticker}`, 'info');
      return;
    }
    // Fallback: direct POST when queue module didn't load
    const res = await fetch('/api/run-protocol', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name: 'invest', ticker, risk_tolerance: UI.riskTolerance }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ error: res.statusText }));
      throw new Error(err.error || `HTTP ${res.status}`);
    }
    UI.logToUI(`Launched: invest ${ticker}`, 'info');
  } catch (e) {
    setLaunchStatus('error', e.message);
    UI.logToUI(`Launch failed: ${e.message}`, 'error');
  }
}

document.getElementById('launch-btn')?.addEventListener('click', launchAnalysis);
document.getElementById('ticker-input')?.addEventListener('keydown', e => { if (e.key === 'Enter') launchAnalysis(); });

// Resume banner on page load if a protocol is already running.
// For invest runs the analyze-queue widget handles the display; skip the banner.
(async () => {
  try {
    const r = await fetch('/api/run-protocol/status');
    const s = await r.json();
    if (s.status === 'running' && s.name !== 'invest') {
      const isZh = UI.currentLang === 'zh';
      setLaunchStatus('running', isZh ? `${s.name || ''} 執行中...` : `${s.name || ''} running...`);
      _launchPollTimer = setInterval(pollLaunchStatus, 2000);
      pollLaunchStatus();
    }
  } catch (e) { /* ignore */ }
})();

// ── Preflight Hover Tooltip ──────────────────────────────────────────────
let _tooltipTimer = null;
let _tooltipCache = null;
let _tooltipCacheAge = 0;

async function loadTooltipData() {
  const body = document.getElementById('preflight-tooltip-body');
  const summary = document.getElementById('preflight-tooltip-summary');
  if (!body) return;
  // Use cached data if < 30s old
  if (_tooltipCache && Date.now() - _tooltipCacheAge < 30000) {
    renderTooltip(_tooltipCache);
    return;
  }
  body.innerHTML = '<div class="animate-pulse text-zinc-500 text-center py-2">Loading...</div>';
  try {
    const r = await fetch('/api/preflight');
    const d = await r.json();
    _tooltipCache = d.items || [];
    _tooltipCacheAge = Date.now();
    renderTooltip(_tooltipCache);
  } catch (e) {
    body.innerHTML = `<div class="text-red-400 text-center">${e.message}</div>`;
  }
}

function renderTooltip(items) {
  const body = document.getElementById('preflight-tooltip-body');
  const summary = document.getElementById('preflight-tooltip-summary');
  const isZh = UI.currentLang === 'zh';
  if (!body) return;
  body.innerHTML = items.map(item => {
    const label = isZh ? item.label : item.label_en;
    const icon = item.status === 'FRESH' ? '✅' : item.status === 'STALE' ? '⚠️' : '❌';
    const color = item.status === 'FRESH' ? 'text-emerald-400' : item.status === 'STALE' ? 'text-amber-400' : 'text-red-400';
    return `<div class="flex items-center justify-between gap-2">
      <span>${icon} ${label}</span>
      <span class="font-mono ${color}">${item.age_str}</span>
    </div>`;
  }).join('');

  const stale = items.filter(i => i.status !== 'FRESH');
  const staleFree = stale.filter(i => i.free);
  const staleToken = stale.filter(i => !i.free);
  if (stale.length === 0) {
    summary.innerHTML = isZh ? '✅ 全部最新，無需更新' : '✅ All fresh, nothing to update';
  } else {
    const parts = [];
    if (staleFree.length) parts.push(isZh ? `${staleFree.length} 個免費項目` : `${staleFree.length} free`);
    if (staleToken.length) parts.push(isZh ? `${staleToken.length} 個需 token` : `${staleToken.length} need tokens`);
    summary.innerHTML = (isZh ? '點擊更新：' : 'Click to update: ') + parts.join(isZh ? '，' : ', ');
  }
}

const _preflightWrap = document.getElementById('preflight-wrap');
_preflightWrap?.addEventListener('mouseenter', () => {
  _tooltipTimer = setTimeout(() => {
    document.getElementById('preflight-tooltip')?.classList.remove('hidden');
    loadTooltipData();
  }, 300);
});
_preflightWrap?.addEventListener('mouseleave', () => {
  clearTimeout(_tooltipTimer);
  document.getElementById('preflight-tooltip')?.classList.add('hidden');
});

// ── Preflight Modal ──────────────────────────────────────────────────────
const _preflightModal = document.getElementById('preflight-modal');

function openPreflight() {
  if (!_preflightModal) return;
  _preflightModal.classList.remove('hidden');
  loadPreflightData();
}
function closePreflight() {
  if (_preflightModal) _preflightModal.classList.add('hidden');
}

document.getElementById('preflight-btn')?.addEventListener('click', openPreflight);
document.getElementById('preflight-close')?.addEventListener('click', closePreflight);
document.addEventListener('keydown', e => { if (e.key === 'Escape') closePreflight(); });

async function loadPreflightData() {
  const body = document.getElementById('preflight-body');
  const btnFree = document.getElementById('preflight-run-free');
  const btnAll  = document.getElementById('preflight-run-all');
  if (!body) return;
  body.innerHTML = '<div class="animate-pulse text-zinc-500 text-sm text-center py-8">Checking...</div>';
  btnFree?.classList.add('hidden');
  btnAll?.classList.add('hidden');
  try {
    const r = await fetch('/api/preflight');
    const d = await r.json();
    const items = d.items || [];
    const isZh = UI.currentLang === 'zh';
    const stale = items.filter(i => i.status !== 'FRESH');
    const staleFree = stale.filter(i => i.free);
    const staleToken = stale.filter(i => !i.free);

    body.innerHTML = items.map(item => {
      const label = isZh ? item.label : item.label_en;
      const icon = item.status === 'FRESH' ? '✅'
                 : item.status === 'STALE' ? '⚠️' : '❌';
      const statusColor = item.status === 'FRESH' ? 'text-emerald-400'
                        : item.status === 'STALE' ? 'text-amber-400' : 'text-red-400';
      const freeTag = item.free
        ? '<span class="text-[8px] px-1.5 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 font-bold">FREE</span>'
        : '<span class="text-[8px] px-1.5 py-0.5 rounded bg-violet-500/10 text-violet-400 border border-violet-500/20 font-bold">TOKEN</span>';
      return `
        <div class="flex items-center justify-between gap-3 px-3 py-2.5 rounded-lg border border-zinc-200 dark:border-zinc-800">
          <div class="flex items-center gap-2.5">
            <span class="text-base">${icon}</span>
            <span class="text-sm font-medium" style="color:var(--text-card-title)">${label}</span>
            ${freeTag}
          </div>
          <div class="flex items-center gap-2 shrink-0">
            <span class="text-[11px] font-mono ${statusColor}">${item.status}</span>
            <span class="text-[10px] font-mono text-zinc-500">${item.age_str}</span>
          </div>
        </div>`;
    }).join('');

    // Show action buttons based on stale items
    if (staleFree.length > 0) {
      btnFree?.classList.remove('hidden');
      const lbl = document.getElementById('preflight-free-label');
      if (lbl) lbl.textContent = isZh ? `更新 ${staleFree.length} 個免費項目` : `Update ${staleFree.length} free items`;
    }
    if (stale.length > 0) {
      btnAll?.classList.remove('hidden');
      const lbl = document.getElementById('preflight-all-label');
      if (lbl) lbl.textContent = isZh ? `更新全部 ${stale.length} 個過期` : `Update all ${stale.length} stale`;
    }
    if (stale.length === 0) {
      body.innerHTML += `<div class="text-center py-4 text-emerald-400 text-sm font-bold">${isZh ? '✅ 所有 cache 都是最新的！' : '✅ All caches are fresh!'}</div>`;
    }
  } catch (e) {
    body.innerHTML = `<div class="text-red-400 text-sm text-center py-4">${e.message}</div>`;
  }
}

// Run free caches
document.getElementById('preflight-run-free')?.addEventListener('click', async () => {
  const body = document.getElementById('preflight-body');
  const isZh = UI.currentLang === 'zh';
  try {
    const res = await fetch('/api/preflight/run-free', { method: 'POST' });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.error || `HTTP ${res.status}`);
    }
    document.getElementById('preflight-run-free')?.classList.add('hidden');
    // Poll preflight status
    const pollId = setInterval(async () => {
      try {
        const r = await fetch('/api/preflight/status');
        const s = await r.json();
        if (s.status !== 'running') {
          clearInterval(pollId);
          loadPreflightData(); // refresh the checklist
          updateDashboard();   // refresh main dashboard
          UI.showToast(isZh ? '免費項目更新完成' : 'Free caches updated', 'info', 4000);
        }
      } catch (e) { clearInterval(pollId); }
    }, 2000);
    body.innerHTML = `<div class="text-center py-8 animate-pulse text-blue-400 text-sm">${isZh ? '正在更新免費 cache...' : 'Updating free caches...'}</div>`;
  } catch (e) {
    UI.showToast(e.message, 'error');
  }
});

// Run all stale (free first, then token-based with confirm)
document.getElementById('preflight-run-all')?.addEventListener('click', async () => {
  const isZh = UI.currentLang === 'zh';
  // Step 1: run free caches
  try {
    await fetch('/api/preflight/run-free', { method: 'POST' });
  } catch (e) { /* ignore, may already be fresh */ }

  // Step 2: check which token-based items are stale and queue them
  const r = await fetch('/api/preflight');
  const d = await r.json();
  const staleToken = (d.items || []).filter(i => i.status !== 'FRESH' && !i.free);
  if (staleToken.length > 0) {
    const names = staleToken.map(i => isZh ? i.label : i.label_en).join(', ');
    const ok = confirm(isZh
      ? `以下需消耗 tokens 更新：\n${names}\n\n確認執行？`
      : `These need tokens to update:\n${names}\n\nProceed?`);
    if (ok) {
      // Run first token-based protocol (single-job lock means one at a time)
      for (const item of staleToken) {
        const protocolMap = { sector: 'sector', news: 'news' };
        const name = protocolMap[item.key];
        if (!name) continue;
        try {
          await fetch('/api/run-protocol', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name }),
          });
          UI.showToast(isZh ? `已啟動 ${item.label}` : `Started ${item.label_en}`, 'info', 3000);
          break; // single-job lock — only start one
        } catch (e) { /* ignore */ }
      }
    }
  }
  closePreflight();
  // Let the free cache poll handle refresh
  setTimeout(() => { updateDashboard(); loadPreflightData(); }, 5000);
});

// ── Boot ───────────────────────────────────────────────────────────────────
const _activePage = document.body.dataset.page || 'index';
UI.boot(_activePage, { translate: applyTranslations, reload: updateDashboard });
updateDashboard();
setInterval(updateDashboard, 60000);

// Mount global analyze-queue widget inside Quick Launch engine card
if (window.AnalyzeQueue) window.AnalyzeQueue.renderWidget('#analyze-queue-widget');
