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

// ── Launch Engine ──────────────────────────────────────────────────────────
function launchAnalysis() {
  const input = document.getElementById('ticker-input');
  const hint  = document.getElementById('launch-hint');
  const cmdEl = document.getElementById('launch-cmd');
  if (!input) return;
  const ticker = input.value.trim().toUpperCase();
  if (!ticker) return;
  const cmd = `分析 ${ticker}`;
  cmdEl.textContent = cmd;
  hint.classList.remove('hidden');
  UI.logToUI(`Launch command generated: "${cmd}"`, 'info');
}

document.getElementById('launch-btn')?.addEventListener('click', launchAnalysis);
document.getElementById('ticker-input')?.addEventListener('keydown', e => { if (e.key === 'Enter') launchAnalysis(); });
document.getElementById('copy-cmd')?.addEventListener('click', () => {
  const cmd = document.getElementById('launch-cmd')?.textContent;
  if (!cmd) return;
  navigator.clipboard.writeText(cmd).then(() => {
    const btn = document.getElementById('copy-cmd');
    btn.innerHTML = '<i data-lucide="check" class="w-3 h-3"></i> COPIED';
    btn.classList.add('text-green-400', 'border-green-500');
    UI.icons();
    setTimeout(() => {
      btn.innerHTML = '<i data-lucide="copy" class="w-3 h-3"></i> COPY';
      btn.classList.remove('text-green-400', 'border-green-500');
      UI.icons();
    }, 2000);
  });
});

// ── Boot ───────────────────────────────────────────────────────────────────
const _activePage = document.body.dataset.page || 'index';
UI.boot(_activePage, { translate: applyTranslations, reload: updateDashboard });
updateDashboard();
setInterval(updateDashboard, 60000);
