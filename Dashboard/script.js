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
  // Layer 3 teaser titles
  const setText = (id, val) => { const el = document.getElementById(id); if (el && val) el.textContent = val; };
  setText('teaser-hot-title',      o.teaser_hot);
  setText('teaser-news-title',     o.teaser_news);
  setText('teaser-momentum-title', o.teaser_momentum);
  // Layer 1 today_verdict 3-col titles (shared strings from sector_page namespace)
  const sp = t.sector_page || {};
  setText('tv-takeaways-title', sp.tv_takeaways_title);
  setText('tv-actions-title',   sp.tv_actions_title);
  setText('tv-watch-title',     sp.tv_watch_title);
  setText('tv-fallback-title',  sp.handoff_title);
}

// ── i18n helper ───────────────────────────────────────────────────────────
function sig() { return window.i18n?.[UI.currentLang]?.signals || {}; }
function ov()  { return window.i18n?.[UI.currentLang]?.overview || {}; }
function tvT() { return window.i18n?.[UI.currentLang]?.sector_page || {}; }

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

// Today's Verdict hero is a shared component — see components.js Components.renderTodayVerdict

// ── 3-signal mini gauge (bottom of hero) ──────────────────────────────────
function renderThreeSignalMini(data) {
  const el = document.getElementById('three-signal-mini');
  if (!el) return;
  const br  = data.breadth    || {};
  const ftd = data.ftd        || {};
  const mt  = data.market_top || {};
  const mkt = data.market     || {};

  const pm = s => { if (!s) return null; const n = String(s).replace(/%/g,'').split('-').map(Number).filter(x => !isNaN(x)); return n.length === 2 ? (n[0]+n[1])/2 : n.length === 1 ? n[0] : null; };
  const mids = [br.exposure_ceiling, ftd.exposure_range, mt.risk_budget].map(pm).filter(v => v !== null);
  const synth = mids.length ? Math.min(...mids) : null;
  const synthLabel = synth !== null ? `${Math.round(synth)}%` : '—';
  const synthColor = synth === null ? '#71717a' : synth >= 75 ? '#22c55e' : synth >= 50 ? '#f59e0b' : '#ef4444';

  const zoneCol = (z) => {
    if (!z) return '#71717a'; const zl = z.toLowerCase();
    if (zl.includes('strong') || zl.includes('healthy') || zl.includes('normal') || zl.includes('early')) return '#22c55e';
    if (zl.includes('weak')   || zl.includes('elevat')  || zl.includes('high'))    return '#f59e0b';
    if (zl.includes('crit')   || zl.includes('top'))    return '#ef4444';
    return '#71717a';
  };
  const ftdCol = (st) => { const s = String(st||'').toUpperCase();
    if (s.includes('CONFIRMED')) return '#22c55e';
    if (s.includes('WINDOW'))    return '#3b82f6';
    if (s.includes('RALLY'))     return '#f59e0b';
    if (s.includes('INVALID') || s.includes('CORRECTION')) return '#ef4444';
    return '#71717a'; };

  const tr = tvT();
  el.innerHTML = `
    <div class="grid grid-cols-1 md:grid-cols-4 gap-3 items-center">
      <div class="flex flex-col gap-0.5 px-1 -mx-1" data-signal-tip="breadth"
           data-br-score="${br.score ?? ''}" data-br-zone="${br.zone || ''}"
           data-br-ceiling="${br.exposure_ceiling || ''}">
        <span class="text-[9px] font-black uppercase tracking-widest text-zinc-500">${tr.signal_breadth || 'Breadth'}</span>
        <div class="flex items-baseline gap-2">
          <span class="text-xl font-black" style="color:${zoneCol(br.zone)}">${br.score ?? '—'}</span>
          <span class="text-[10px] text-zinc-500 truncate">${br.zone || ''}</span>
        </div>
      </div>
      <div class="flex flex-col gap-0.5 px-1 -mx-1" data-signal-tip="ftd"
           data-ftd-state="${ftd.state || ''}" data-ftd-date="${ftd.ftd_date || ''}"
           data-ftd-day="${ftd.days_since_ftd ?? ''}" data-ftd-status="${(ftd.ftd_status_text || '').replace(/"/g,'&quot;')}">
        <span class="text-[9px] font-black uppercase tracking-widest text-zinc-500">${tr.signal_ftd || 'FTD'}</span>
        <div class="flex items-baseline gap-2">
          <span class="text-xl font-black" style="color:${ftdCol(ftd.state)}">${ftd.quality_score ?? '—'}</span>
          <span class="text-[10px] text-zinc-500 truncate">${(ftd.state||'').replace(/_/g,' ')}</span>
        </div>
        ${ftd.ftd_date ? `<span class="text-[9px] text-zinc-500 font-mono mt-0.5">${ftd.ftd_date} · day ${ftd.days_since_ftd ?? '—'}</span>` : ''}
      </div>
      <div class="flex flex-col gap-0.5 px-1 -mx-1" data-signal-tip="market_top"
           data-mt-score="${mt.composite_score ?? ''}" data-mt-zone="${mt.zone || ''}"
           data-mt-budget="${mt.risk_budget || ''}">
        <span class="text-[9px] font-black uppercase tracking-widest text-zinc-500">${tr.signal_top || 'Market Top'}</span>
        <div class="flex items-baseline gap-2">
          <span class="text-xl font-black" style="color:${zoneCol(mt.zone)}">${mt.composite_score ?? '—'}</span>
          <span class="text-[10px] text-zinc-500 truncate">${(mt.zone||'').replace(/\(.*\)/,'').trim()}</span>
        </div>
      </div>
      <div class="flex flex-col gap-0.5 items-end md:border-l md:border-zinc-800 md:pl-3 px-1 -mx-1" data-signal-tip="synth"
           data-synth-mid="${synth ?? ''}" data-synth-label="${synthLabel}"
           data-br-ceiling="${br.exposure_ceiling || ''}" data-ftd-range="${ftd.exposure_range || ''}"
           data-mt-budget="${mt.risk_budget || ''}">
        <span class="text-[9px] font-black uppercase tracking-widest text-zinc-500">${tr.synthesized_ceiling || 'Synthesized Ceiling'}</span>
        <span class="text-xl font-black" style="color:${synthColor}">${synthLabel}</span>
      </div>
    </div>`;
}

// ── Layer 2a: Binary Risk 48h banner ──────────────────────────────────────
// Translate sector keys (Energy, Consumer_Discretionary, …) into zh/en.
const SECTOR_I18N = {
  zh: {
    Energy:'能源', Industrials:'工業', Financials:'金融', Utilities:'公用事業',
    Technology:'科技', Materials:'基礎材料', Healthcare:'醫療保健',
    Real_Estate:'房地產', Communication:'通訊服務', Communication_Services:'通訊服務',
    Consumer_Staples:'必需消費', Consumer_Discretionary:'非必需消費', Consumer_Cyclical:'非必需消費',
    Tanker_Shipping:'油輪運輸', Airlines:'航空', Chemicals:'化工', Transports:'運輸',
  },
  en: {
    Energy:'Energy', Industrials:'Industrials', Financials:'Financials', Utilities:'Utilities',
    Technology:'Technology', Materials:'Materials', Healthcare:'Healthcare',
    Real_Estate:'Real Estate', Communication:'Communication', Communication_Services:'Communication',
    Consumer_Staples:'Cons. Staples', Consumer_Discretionary:'Cons. Discr.', Consumer_Cyclical:'Cons. Discr.',
    Tanker_Shipping:'Tankers', Airlines:'Airlines', Chemicals:'Chemicals', Transports:'Transports',
  },
};
function sectorLabelIndex(key) {
  const table = SECTOR_I18N[UI.currentLang] || SECTOR_I18N.en;
  return table[key] || String(key).replace(/_/g, ' ');
}

function renderBinaryAlertIndex(risks) {
  const urgent = (risks || []).filter(r => r.within_48h);
  const section = document.getElementById('binary-alert-section');
  if (!section) return;
  if (!urgent.length) { section.classList.add('hidden'); return; }
  section.classList.remove('hidden');

  const isZh = UI.currentLang === 'zh';
  const sp = window.i18n?.[UI.currentLang]?.sector_page || {};
  // Apply translated header strings
  const titleEl = section.querySelector('[style*="color:#ef4444"]');
  if (titleEl) titleEl.textContent = sp.binary_alert || '⚡ Binary Risk Within 48h';
  const deratedEl = document.getElementById('binary-alert-derated');
  if (deratedEl) {
    deratedEl.textContent = isZh ? '自動降權 ×0.70' : 'auto-derated ×0.70';
    deratedEl.setAttribute('data-tip-key', 'binary_derated_tip');
    deratedEl.removeAttribute('title');
  }

  const dateLabel = (r) => r.days_until === 0 ? (sp.binary_today    || (isZh ? '今日' : 'TODAY'))
                         : r.days_until === 1 ? (sp.binary_tomorrow || (isZh ? '明日' : 'TOMORROW'))
                         : (r.date || '');
  const container = document.getElementById('binary-alert-items');
  container.innerHTML = urgent.map(r => {
    const isTomorrow = r.days_until === 1;
    const lbl = dateLabel(r);

    return `
      <div class="binary-row">
        <!-- Date Box: Fixed Width -->
        <div class="binary-date-box">
          <span class="binary-date-pill ${isTomorrow ? 'tomorrow' : ''}">${lbl}</span>
        </div>

        <!-- Content: Headline + Sectors -->
        <div class="binary-content">
          <div class="binary-headline">${r.event}</div>
          ${r.affected_sectors?.length ? `
            <div class="binary-sector-group">
              ${r.affected_sectors.map(s => `<span class="binary-sector-chip">${sectorLabelIndex(s)}</span>`).join('')}
            </div>` : ''}
        </div>
      </div>`;
  }).join('');
  }


// ── Layer 2b: Warning Flags strip ─────────────────────────────────────────
function renderWarningFlagsIndex(market) {
  const row = document.getElementById('warning-flags-row');
  if (!row) return;
  row.innerHTML = '';
  const flags = market?.warning_flags || [];
  if (!flags.length) return;
  const tw = window.i18n?.[UI.currentLang]?.warnings?.flags || {};
  flags.forEach(f => {
    const label = tw[f] || f.replace(/_/g, ' ');
    const isCrit = /Death_Cross|Extreme_Fear|Critical|Bearish/i.test(f);
    const cls = isCrit ? 'bg-red-500/10 text-red-400 border-red-500/25'
                       : 'bg-yellow-500/8 text-yellow-500 border-yellow-500/20';
    row.insertAdjacentHTML('beforeend',
      `<span class="text-[10px] font-bold px-2 py-1 rounded border ${cls}">⚠ ${label}</span>`);
  });
}

// ── Layer 3a: HOT Sectors Teaser (top 3) ──────────────────────────────────
const SECTOR_TO_GICS_IDX = {
  'Industrials':'Industrials', 'Financials':'Financials', 'Utilities':'Utilities',
  'Consumer_Discretionary':'Consumer Discretionary', 'Technology':'Information Technology',
  'Materials':'Materials', 'Healthcare':'Health Care', 'Real_Estate':'Real Estate',
  'Communication':'Communication Services', 'Communication_Services':'Communication Services',
  'Consumer_Staples':'Consumer Staples', 'Energy':'Energy',
};

function renderHotSectorsTeaser(sectors, momentum) {
  const el = document.getElementById('hot-sectors-teaser');
  if (!el) return;
  const top = (sectors || []).slice().sort((a,b) => (b.score||0) - (a.score||0)).slice(0, 3);
  if (!top.length) { el.innerHTML = `<p class="text-[10px] text-zinc-600 italic">—</p>`; return; }

  const VC_COL = { HOT:'#22c55e', WARM:'#eab308', COLD:'#ef4444', AVOID:'#71717a' };
  const allMoms = (momentum || {}).rows || [];

  el.innerHTML = top.map(s => {
    const col = VC_COL[s.verdict] || '#71717a';
    const gics = SECTOR_TO_GICS_IDX[s.name] || '';
    const href = gics ? `momentum.html?sector=${encodeURIComponent(gics)}` : 'sector.html';

    // Find top 3 stocks in this sector (sorted by score desc)
    const sectorStocks = allMoms
      .filter(r => r.sector === gics)
      .slice(0, 3);

    return `<div class="teaser-card no-underline mb-3 block" style="border-left: 3px solid ${col}">
      <!-- Header: Sector Name + Score -->
      <a href="${href}" class="flex items-center justify-between no-underline group">
        <div class="flex flex-col">
          <div class="flex items-center gap-2">
            <span class="text-base font-black tracking-tight" style="color:var(--text-card-title)">${s.proxy_etf || s.name}</span>
            <span class="text-[9px] font-black px-1.5 py-0.5 rounded mt-[-5px]" style="background:${col}1A;color:${col}">${s.verdict}</span>
          </div>
          <span class="text-[10px] text-zinc-500">${sectorLabelIndex(s.name || '')}</span>
        </div>
        <div class="flex flex-col items-end">
          <span class="text-[14px] font-black font-mono" style="color:${col}">${s.score ?? '—'}</span>
          <span class="text-[9px] text-zinc-500 group-hover:text-emerald-500 transition-all">→</span>
        </div>
      </a>

      <!-- Lead Tickers: Horiz pills -->
      <div class="flex flex-wrap gap-2 mt-2 pt-2 border-t border-zinc-200/10 dark:border-zinc-800/40">
        ${sectorStocks.length ? sectorStocks.map(r => {
          const sCol = (r.score||0) >= 70 ? '#3b82f6' : (r.score||0) >= 50 ? '#22c55e' : '#eab308';
          return `<a href="momentum.html?search=${r.ticker}" class="sector-ticker-pill no-underline">
            <div class="score-dot" style="background:${sCol}"></div>
            <span>${r.ticker}</span>
            <span class="text-[8px] opacity-60">${r.score?.toFixed(0)}</span>
          </a>`;
        }).join('') : `<span class="text-[9px] text-zinc-600 italic">No tickers scanned</span>`}
      </div>
    </div>`;
  }).join('');
}

// ── Layer 3b: Latest News Verdicts Teaser ─────────────────────────────────
function renderNewsVerdictsTeaser(news) {
  const el = document.getElementById('news-verdicts-teaser');
  if (!el) return;
  const pool = (news || []).filter(n =>
    (n.depth === 'deep' || n.depth == null) &&
    (n.review_status === 'reviewed' || !n.review_status) &&
    n.impact
  );
  // Sort by date desc, then by impact score absolute value
  pool.sort((a, b) => {
    const da = a.date || '0000-00-00';
    const db = b.date || '0000-00-00';
    if (db !== da) return db.localeCompare(da);
    return Math.abs(b.score || 0) - Math.abs(a.score || 0);
  });
  const top = pool.slice(0, 3);
  if (!top.length) { el.innerHTML = `<p class="text-[10px] text-zinc-600 italic">—</p>`; return; }

  const ICOL = { bullish:'#22c55e', bearish:'#ef4444', binary:'#f97316', neutral:'#a1a1aa' };
  const isZh = UI.currentLang === 'zh';
  const impactLbl = { bullish: isZh?'利多':'BULLISH', bearish: isZh?'利空':'BEARISH', binary: isZh?'變數':'BINARY', neutral: isZh?'中性':'NEUTRAL' };

  el.innerHTML = top.map(n => {
    const key = String(n.impact || 'neutral').toLowerCase();
    const col = ICOL[key] || '#a1a1aa';
    const scoreTxt = n.score != null ? `${n.score >= 0 ? '+' : ''}${Number(n.score).toFixed(1)}` : '';
    const label = impactLbl[key] || key.toUpperCase();
    
    // Summary logic: take bull_case or bear_case based on impact
    const reason = key === 'bearish' ? (n.bear_case || n.arbiter_reasoning) : (n.bull_case || n.arbiter_reasoning);
    const sectors = (n.sectors || []).slice(0, 2).map(s => sectorLabelIndex(s));

    return `<a href="news.html" class="news-teaser-card no-underline mb-3 block" style="border-left: 3px solid ${col}">
      <!-- Header: Verdict + Score -->
      <div class="flex items-center justify-between">
        <span class="impact-badge" style="background:${col}1A;color:${col}">${label}</span>
        <span class="text-[12px] font-black font-mono" style="color:${col}">${scoreTxt}</span>
      </div>

      <!-- Title: Headline -->
      <h4 class="text-[11px] font-bold leading-tight" style="color:var(--text-card-title)">${n.headline_zh || n.headline}</h4>

      <!-- Content: Core Reason (truncated) -->
      ${reason ? `<p class="text-[10px] text-zinc-500 line-clamp-2 leading-relaxed mt-1 italic">${reason}</p>` : ''}

      <!-- Footer: Sectors -->
      <div class="flex flex-wrap gap-1.5 mt-1 pt-2 border-t border-zinc-200/10 dark:border-zinc-800/40">
        ${sectors.map(s => `<span class="news-sector-pill">${s}</span>`).join('')}
      </div>
      </a>`;

  }).join('');
}

// ── Layer 3c: Momentum Top 3 + M3 Focus Ticker ────────────────────────────
function renderMomentumTeaser(momentum, crossSet) {
  const el = document.getElementById('momentum-teaser');
  if (!el) return;
  const rows = ((momentum || {}).rows || []).slice(0, 3);
  if (!rows.length) { el.innerHTML = `<p class="text-[10px] text-zinc-600 italic">—</p>`; return; }

  const isZh = UI.currentLang === 'zh';
  const sigMap = window.i18n?.[UI.currentLang]?.momentum?.signals_map || {};
  const warnMap = window.i18n?.[UI.currentLang]?.momentum?.warnings_map || {};

  el.innerHTML = rows.map((r, i) => {
    const rankNum = i + 1;
    const score = Number(r.score) || 0;
    const star = crossSet && crossSet.has(r.ticker) ? `<span class="cross-signal-star ml-1" title="雙軍同向">⭐</span>` : '';
    
    // Battery logic
    const fullCells = Math.floor(score / 10);
    const tierColor = fullCells >= 7 ? '#3b82f6' : fullCells >= 5 ? '#22c55e' : fullCells >= 3 ? '#eab308' : '#ef4444';
    let cellsHTML = '';
    for (let c=0; c<10; c++) cellsHTML += `<div class="cell" style="background:${c < fullCells ? tierColor : 'rgba(161,161,170,0.15)'}"></div>`;

    // Pros & Cons (Take first 2 of each)
    const pros = (r.signals || []).slice(0, 2).map(s => sigMap[s] || s.replace(/_/g, ' '));
    const cons = (r.warnings || []).slice(0, 2).map(w => warnMap[w] || w.replace(/_/g, ' '));

    return `<a href="momentum.html" class="teaser-card rank-card-${rankNum} no-underline mb-3 block">
      <!-- Header: Rank + Ticker + Score -->
      <div class="flex items-center justify-between">
        <div class="flex items-center gap-2">
          <span class="rank-badge rank-${rankNum}">${rankNum}</span>
          <span class="text-base font-black tracking-tight" style="color:var(--text-card-title)">${r.ticker}</span>
          ${star}
          <span class="text-[10px] text-zinc-500 font-mono ml-1">$${r.price ? r.price.toFixed(2) : '—'}</span>
        </div>
        <div class="flex flex-col items-end">
          <div class="score-battery mb-1">${cellsHTML}</div>
          <span class="score-num" style="color:${tierColor}">${score.toFixed(1)}</span>
        </div>
      </div>

      <!-- Content: Pros & Cons -->
      <div class="flex flex-col gap-1.5 mt-1">
        ${pros.length ? `<div class="flex flex-wrap gap-1.5">
          ${pros.map(p => `<span class="pc-pill pc-pro"><i data-lucide="check-circle-2" class="w-2.5 h-2.5"></i> ${p}</span>`).join('')}
        </div>` : ''}
        ${cons.length ? `<div class="flex flex-wrap gap-1.5">
          ${cons.map(c => `<span class="pc-pill pc-con"><i data-lucide="alert-triangle" class="w-2.5 h-2.5"></i> ${c}</span>`).join('')}
        </div>` : ''}
      </div>

      <!-- Footer: Sector & RSI -->
      <div class="flex items-center justify-between mt-1 pt-2 border-t border-zinc-200/20 dark:border-zinc-800/50">
        <span class="news-sector-pill">${r.sector || 'Unknown'}</span>
        <span class="text-[9px] font-mono ${r.rsi_14 > 70 ? 'text-red-400' : r.rsi_14 < 30 ? 'text-blue-400' : 'text-zinc-500'}">RSI ${r.rsi_14?.toFixed(1) || '—'}</span>
      </div>
    </a>`;
  }).join('');
  
  // Re-run icon hydration for the new cards
  if (window.lucide) { lucide.createIcons(); }
}

// ── M3: Today's Focus Ticker (cross-module intersection) ──────────────────
// Find a ticker that: (1) sits in a sector_actions.overweight sector
// AND (2) is in momentum top N AND (3) has a BULLISH/STRONGLY_BULLISH label
function renderFocusTicker(data) {
  const el = document.getElementById('focus-ticker-card');
  if (!el) { return; }
  const tv = data.market?.today_verdict;
  const moms = (data.momentum_screen?.rows) || [];
  if (!tv || !moms.length) { el.classList.add('hidden'); return; }

  const overweightSectors = new Set(
    (tv.sector_actions || [])
      .filter(a => a.action === 'overweight')
      .map(a => SECTOR_TO_GICS_IDX[a.sector] || '')
      .filter(Boolean)
  );
  if (!overweightSectors.size) { el.classList.add('hidden'); return; }

  const candidates = moms
    .filter(r => overweightSectors.has(r.sector))
    .filter(r => r.label === 'STRONGLY_BULLISH' || r.label === 'BULLISH')
    .slice(0, 20);
  if (!candidates.length) { el.classList.add('hidden'); return; }

  const pick = candidates.reduce((best, r) => (r.score || 0) > (best.score || 0) ? r : best, candidates[0]);

  const isZh = UI.currentLang === 'zh';
  const sectorName = pick.sector || '';
  el.classList.remove('hidden');
  el.innerHTML = `
    <div class="focus-ticker-card">
      <div class="flex items-center gap-2 mb-1">
        <span class="text-[9px] font-black uppercase tracking-widest" style="color:#a78bfa">✨ ${isZh ? '今日焦點' : 'TODAY FOCUS'}</span>
        <span class="text-[9px] text-zinc-500">${isZh ? '三軍同向（AI verdict + 產業 + 動能）' : 'Tri-signal alignment'}</span>
      </div>
      <div class="flex items-baseline gap-3 flex-wrap">
        <span class="text-lg font-black tracking-tight" style="color:var(--text-card-title)">${pick.ticker}</span>
        <span class="text-[10px] text-zinc-500 font-mono">$${pick.price ? pick.price.toFixed(2) : '—'}</span>
        <span class="text-[10px] font-mono" style="color:#a78bfa">score ${pick.score ?? '—'}</span>
        <button onclick="window.AnalyzeQueue && window.AnalyzeQueue.enqueue('${pick.ticker}')"
                class="ml-auto text-[9px] font-black px-2 py-1 rounded" style="background:#a78bfa;color:#fff">
          ${isZh ? '加入佇列' : 'ENQUEUE'}
        </button>
      </div>
      <div class="text-[10px] text-zinc-500 mt-1 leading-snug">${sectorName} · ${isZh ? '來自 AI overweight 產業的動能領先股' : 'Momentum leader in an AI-overweight sector'}</div>
    </div>`;
}

// ── M3: Cross-signal intersection set (momentum top 30 ∩ recent BUY/EXECUTE)
function computeCrossSignalSet(data) {
  const recentBuys = new Set(
    (data.recent_analysis || [])
      .filter(a => a.decision === 'BUY' || a.decision === 'EXECUTE')
      .map(a => a.ticker)
  );
  const momTop30 = new Set(
    ((data.momentum_screen || {}).rows || []).slice(0, 30).map(r => r.ticker)
  );
  return new Set([...recentBuys].filter(t => momTop30.has(t)));
}

// ── Dashboard Update ───────────────────────────────────────────────────────
async function updateDashboard() {
  UI.logToUI('Refreshing system synchronization...');
  UI.updateMarketStatus();
  let data = null;

  try {
    data = await DataStore.get(true);

    // Layer 1: Today's AI Verdict hero + 3-signal mini gauge
    Components.renderTodayVerdict(data.market);
    renderThreeSignalMini(data);

    // Layer 2: Binary risk + warning flags
    renderBinaryAlertIndex(data.binary_risks);
    renderWarningFlagsIndex(data.market);

    // Layer 3: Deep-dive teasers + M3 focus ticker
    const crossSet = computeCrossSignalSet(data);
    renderHotSectorsTeaser(data.sectors, data.momentum_screen);
    renderNewsVerdictsTeaser(data.news);
    renderMomentumTeaser(data.momentum_screen, crossSet);
    renderFocusTicker(data);

    // Layer 4: Recent Analysis (compact list) — M3 ⭐ badge attached via crossSet
    const condensedGrid = document.getElementById('audit-grid-condensed');
    const fullGrid      = document.getElementById('audit-grid-full');
    const decorate = (card, ticker) => {
      if (!crossSet.has(ticker)) return card;
      const title = card.querySelector('.font-black') || card.querySelector('span');
      if (title && !title.querySelector('.cross-signal-star')) {
        title.insertAdjacentHTML('afterend',
          ` <span class="cross-signal-star" title="雙軍同向（動能榜 Top 30 + BUY/EXECUTE）">⭐</span>`);
      }
      return card;
    };
    if (condensedGrid) {
      condensedGrid.innerHTML = '';
      data.recent_analysis?.slice(0, 3).forEach(item =>
        condensedGrid.appendChild(decorate(Components.renderAuditCard(item, true), item.ticker)));
    }
    if (fullGrid) {
      fullGrid.innerHTML = '';
      data.recent_analysis?.forEach(item =>
        fullGrid.appendChild(decorate(Components.renderAuditCard(item, false), item.ticker)));
    }

  } catch (error) {
    UI.logToUI(error.message, 'error');
    console.error('Dashboard update failed:', error);
  } finally {
    UI.icons();
    const syncEl = document.getElementById('last-update');
    if (syncEl) UI.applySyncLight(syncEl, data?.last_updated, null, [
      { label: '廣度分析', ts: data?.breadth?.generated_at || data?.breadth?.data_date, ttl: 180, hint: 'daily_update.sh Step 1' },
      { label: 'FTD 偵測', ts: data?.ftd?.generated_at,        ttl: 180, hint: 'daily_update.sh Step 2' },
      { label: '市場頂部', ts: data?.market_top?.generated_at, ttl: 180, hint: 'daily_update.sh Step 3' },
      { label: '產業掃描', ts: data?.market?.generated_at,     ttl: 720, hint: '執行「產業掃描」' },
    ]);
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
        // Banner stays up — user dismisses via the ✕ (#launch-status-dismiss) button.
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
document.getElementById('launch-status-dismiss')?.addEventListener('click', () => {
  document.getElementById('launch-status')?.classList.add('hidden');
});

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
        // Live progress indicator during run
        if (s.status === 'running') {
          body.innerHTML =
            `<div class="text-center py-8 text-blue-400 text-sm">
               ${isZh ? '正在更新免費 cache...' : 'Updating free caches...'}
               <div class="text-[11px] text-zinc-500 mt-2 font-mono">
                 ${s.items_done || 0} / ${s.items_total || 0}
               </div>
             </div>`;
          return;
        }
        clearInterval(pollId);
        updateDashboard();
        loadPreflightData();
        // After checklist re-renders, PREPEND an error panel if any script failed.
        // This stays visible until user closes the modal (no auto-dismiss).
        setTimeout(() => {
          const errs = Array.isArray(s.errors) ? s.errors : [];
          if (!errs.length) {
            UI.showToast(isZh ? '✅ 免費項目更新完成' : '✅ Free caches updated', 'success', 4000);
            return;
          }
          const items = errs.map(e => {
            if (typeof e === 'string') {
              return `<div class="text-red-400 text-xs font-mono">${UI.escapeHTML(e)}</div>`;
            }
            const header = `❌ ${e.key || '?'} (rc=${e.rc != null ? e.rc : 'n/a'})`;
            const std = e.stderr_tail || e.error || '';
            const out = e.stdout_tail || '';
            return `
              <div class="bg-red-500/10 border border-red-500/30 rounded-lg p-3">
                <div class="text-red-400 font-bold text-xs mb-1">${UI.escapeHTML(header)}</div>
                ${std ? `<pre class="text-red-300 whitespace-pre-wrap text-[10px] font-mono leading-snug">${UI.escapeHTML(std)}</pre>` : ''}
                ${out ? `<details class="mt-1"><summary class="text-[10px] text-zinc-400 cursor-pointer">stdout tail</summary><pre class="text-zinc-500 whitespace-pre-wrap text-[10px] font-mono mt-1">${UI.escapeHTML(out)}</pre></details>` : ''}
              </div>`;
          }).join('');
          const banner = `
            <div class="mb-3 space-y-2">
              <div class="text-xs font-bold text-red-400">
                ${isZh ? `⚠ ${errs.length} 個項目更新失敗（手動關閉時消失，不會自動隱藏）` : `⚠ ${errs.length} preflight item(s) failed (sticky until you close)`}
              </div>
              ${items}
            </div>`;
          const bd = document.getElementById('preflight-body');
          if (bd) bd.insertAdjacentHTML('afterbegin', banner);
          UI.showToast(isZh ? `⚠ ${errs.length} 個項目更新失敗，詳情見 Modal` : `⚠ ${errs.length} failed — see modal`, 'error', 8000);
        }, 200);
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

// ── Shared Tooltip Engine (Ported from page-sector.js) ─────────────────────
(function initGlobalTooltips() {
  const tip = document.getElementById('pill-tooltip');
  if (!tip) return;
  let _hideTimer = null;

  function showTip(target) {
    const key = target.getAttribute('data-tip-key');
    const isZh = UI.currentLang === 'zh';
    const dict = isZh ? (window.i18n?.zh || {}) : (window.i18n?.en || {});
    
    // Search for content: top-level key OR sector_page logic
    const body = dict[key] || dict.sector_page?.risk_flags?.[key] || key;
    const title = isZh ? '解釋說明' : 'EXPLANATION';

    tip.innerHTML = `<h4 class="text-[10px] font-black uppercase tracking-widest mb-1" style="color:#ef4444">${title}</h4><p class="text-[11px] leading-relaxed text-zinc-300">${body}</p>`;
    tip.classList.add('tip-visible');

    const rect = target.getBoundingClientRect();
    let left = rect.left + rect.width / 2 - 140;
    if (left < 10) left = 10;
    if (left + 280 > window.innerWidth - 10) left = window.innerWidth - 290;
    
    // Default position: above
    let top = rect.top - tip.offsetHeight - 12;
    if (top < 10) {
      // Fallback: below
      top = rect.bottom + 12;
    }

    tip.style.top = top + 'px';
    tip.style.left = left + 'px';
    tip.style.opacity = '1';
    tip.style.transform = 'translateY(0)';
  }

  function hideTip() {
    tip.classList.remove('tip-visible');
    tip.style.opacity = '0';
    tip.style.transform = 'translateY(10px)';
  }

  document.addEventListener('mouseover', e => {
    const el = e.target.closest('[data-tip-key]');
    if (!el) return;
    if (_hideTimer) { clearTimeout(_hideTimer); _hideTimer = null; }
    showTip(el);
  });
  document.addEventListener('mouseout', e => {
    const el = e.target.closest('[data-tip-key]');
    if (!el) return;
    _hideTimer = setTimeout(hideTip, 80);
  });
})();

// ── Signal pill tooltip (FTD / etc.) — richer than pill-tooltip, mirrors radar UX ─
(function initSignalTipTooltip() {
  const tip = document.getElementById('signal-tip-tooltip');
  if (!tip) return;
  let _hideTimer = null;

  const SIGNAL_TIPS = {
    ftd: {
      zh: {
        title: 'FTD · 市場底部確認訊號',
        desc:  '市場大跌觸底後開始反彈，從反彈第 1 天開始計算 rally day。若第 4-7 天主要指數出現「漲幅 ≥ +1% + 成交量比前日放大」→ 那天就標為 FTD，代表機構資金在這天介入抄底。從 FTD 起算，越早進場勝率越高（領導股剛起飛）；越晚進場屬於「補漲」性質，風險升高。',
        stages: [
          { key: 'prime',      range: [1,5],   range_label: 'day 1-5',   tag: '黃金期', action: '可以買', detail: '領導股剛起飛，新趨勢確立，標準倉位最高勝率' },
          { key: 'standard',   range: [6,12],  range_label: 'day 6-12',  tag: '主升期', action: '仍可參與', detail: '主升段未終結，標準倉位 + 標準停損，選擇 RS 強的個股' },
          { key: 'late_cycle', range: [13,20], range_label: 'day 13-20', tag: '補漲期', action: '晚但仍有機會', detail: '行情進入後段，補漲股風險上升 — 倉位降 25%、停損收緊 1pp' },
          { key: 'exhausted',  range: [21,99], range_label: 'day 21+',   tag: '過熱期', action: '等下一輪', detail: '多數領導股已 stage 2 末期，倉位降 50% 或拒單，等下一波 FTD' },
        ],
        no_active: '尚未出現有效 FTD（rally 仍在 attempt 階段、或前次 FTD 已失效）',
        hint: 'Reset 條件：跌破 swing low / 累積 6+ distribution days / 出現新一輪修正',
      },
      en: {
        title: 'FTD · Market Bottom Signal',
        desc:  'After a sell-off bottoms and a rally begins, count from rally day 1. If the index closes ≥+1% on heavier volume on rally days 4-7 → that day is marked as the FTD, signaling institutions are stepping in to buy. From that date, earlier entries have higher win rates (leadership stocks break out first); later entries become "chase trades" with elevated risk.',
        stages: [
          { key: 'prime',      range: [1,5],   range_label: 'day 1-5',   tag: 'Prime',     action: 'Buy zone',         detail: 'Leadership stocks just breaking out — full size, highest win rate' },
          { key: 'standard',   range: [6,12],  range_label: 'day 6-12',  tag: 'Standard',  action: 'Still tradeable',  detail: 'Uptrend intact — standard size + stop, focus on high-RS names' },
          { key: 'late_cycle', range: [13,20], range_label: 'day 13-20', tag: 'Late',      action: 'Chase, cut size',  detail: 'Late phase, chase trades — size −25%, stop tighter by 1pp' },
          { key: 'exhausted',  range: [21,99], range_label: 'day 21+',   tag: 'Exhausted', action: 'Wait for next',    detail: 'Most leaders late stage 2 — size −50% or reject, wait for next FTD' },
        ],
        no_active: 'No active FTD (rally still in attempt phase, or previous FTD invalidated)',
        hint: 'Reset triggers: close below swing low / 6+ distribution days / new correction begins',
      },
    },
    breadth: {
      zh: {
        title: '市場廣度 · 多少股票還在強勢區',
        desc:  '計算成分股「在 200 日均線之上的比例 + 8 日均線變化 + 突破/破底家數比 + 漲跌家數差」等多個指標，合成 0-100 分。分數高 = 大盤健康（不是只有少數權值股撐盤）；分數低 = 多數個股已轉弱、行情危險。建議倉位由分數決定。',
        stages: [
          { key: 'br_strong',    range: [75,100], range_label: 'score 75+',    tag: '健康強勢', action: '全力進攻', detail: '多數成分股健康突破，可以高倉位、新進不限制' },
          { key: 'br_healthy',   range: [60,74],  range_label: 'score 60-75',  tag: '主升中段', action: '標準參與', detail: '行情仍在主升段，標準倉位 + 一般停損即可' },
          { key: 'br_neutral',   range: [40,59],  range_label: 'score 40-60',  tag: '訊號混合', action: '選股、降倉', detail: '多空交雜，僅選 RS 強標的 + 倉位降 25%' },
          { key: 'br_weakening', range: [25,39],  range_label: 'score 25-40',  tag: '走弱中',   action: '防禦為主',  detail: '個股普遍轉弱，避免新進、現有倉位收緊停損' },
          { key: 'br_critical',  range: [0,24],   range_label: 'score < 25',   tag: '行情危險', action: '退守 cash', detail: '多數股票破位，cash 為王、保留資金等下次 FTD' },
        ],
        no_active: '廣度資料缺失或來源失敗',
        hint: '資料源：TraderMonty CSV (每日盤後更新，盤前看到的可能是 D-1 收盤值)',
      },
      en: {
        title: 'Market Breadth · How many stocks are still strong',
        desc:  'Composite of "% stocks above 200-day MA + 8-day MA delta + new highs vs lows + advance/decline gap" → 0-100 score. High = market is healthy (not just a few mega-caps holding it up); low = most stocks already weakening, dangerous.',
        stages: [
          { key: 'br_strong',    range: [75,100], range_label: 'score 75+',    tag: 'Strong',     action: 'Full attack',  detail: 'Most stocks healthy & breaking out — full size, no entry restrictions' },
          { key: 'br_healthy',   range: [60,74],  range_label: 'score 60-75',  tag: 'Healthy',    action: 'Standard',     detail: 'Uptrend intact — standard size + stop' },
          { key: 'br_neutral',   range: [40,59],  range_label: 'score 40-60',  tag: 'Neutral',    action: 'Selective',    detail: 'Mixed signals — high-RS only + size −25%' },
          { key: 'br_weakening', range: [25,39],  range_label: 'score 25-40',  tag: 'Weakening',  action: 'Defensive',    detail: 'Stocks broadly weakening — no new entries + tighten stops' },
          { key: 'br_critical',  range: [0,24],   range_label: 'score < 25',   tag: 'Critical',   action: 'Cash priority',detail: 'Most stocks breaking down — cash priority, wait for next FTD' },
        ],
        no_active: 'Breadth data unavailable / source failed',
        hint: 'Source: TraderMonty CSV (updated post-close — pre-market values may be D-1)',
      },
    },
    synth: {
      zh: {
        title: '綜合曝險 · 三訊號合成的倉位上限',
        desc:  '把廣度建議倉位、FTD 倉位、頂部風控三個來源的中位數取「最保守者（最小值）」 → 得出可承受倉位上限。意義：當三訊號彼此衝突時（例如 breadth 還健康但頂部風險爆表），系統會自動偏向最保守那一個，避免單一訊號誤判。實際個股建倉以這個上限為基準再乘 sector / FTD timeline / tail risk 等其他乘數。',
        stages: [
          { key: 'sy_aggressive', range: [75,100], range_label: '75-100%', tag: '進攻',     action: '滿倉操作',     detail: '三訊號全綠，可開高倉位、新進不限、停損標準' },
          { key: 'sy_standard',   range: [50,74],  range_label: '50-75%',  tag: '標準',     action: '正常配置',     detail: '主升段或訊號小幅雜訊，一般倉位 + 一般停損' },
          { key: 'sy_defensive',  range: [25,49],  range_label: '25-50%',  tag: '防守',     action: '降倉、選股',   detail: '至少一個訊號明顯轉弱，倉位降至 50% 以下、僅留高 conviction' },
          { key: 'sy_crisis',     range: [0,24],   range_label: '0-25%',   tag: '危機模式', action: 'Cash 主導',    detail: '三訊號之一已 critical，幾乎不開新倉、保留資金等下次 FTD' },
        ],
        no_active: '至少一個訊號缺失，無法合成曝險上限',
        hint: '計算：min( breadth_ceiling中位數, ftd_range中位數, market_top_budget中位數 )',
      },
      en: {
        title: 'Synthesized Ceiling · Position cap from 3 signals',
        desc:  'Takes the midpoint of breadth ceiling, FTD range, and market top budget — uses the most conservative (lowest) one as your position cap. Why: when signals disagree (e.g. breadth healthy but topping signals are loud), the system auto-defers to the most cautious. Per-trade size = this cap × sector / FTD-timeline / tail-risk multipliers downstream.',
        stages: [
          { key: 'sy_aggressive', range: [75,100], range_label: '75-100%', tag: 'Aggressive', action: 'Full size',    detail: 'All 3 signals green — full size, no entry restrictions, normal stops' },
          { key: 'sy_standard',   range: [50,74],  range_label: '50-75%',  tag: 'Standard',   action: 'Normal',       detail: 'Uptrend or minor signal noise — normal size + stop' },
          { key: 'sy_defensive',  range: [25,49],  range_label: '25-50%',  tag: 'Defensive',  action: 'Cut & select',  detail: 'At least one signal weakening — cut size <50%, high-conviction only' },
          { key: 'sy_crisis',     range: [0,24],   range_label: '0-25%',   tag: 'Crisis',     action: 'Cash priority', detail: 'One signal is critical — barely any new entries, hold cash for next FTD' },
        ],
        no_active: 'At least one signal missing — cap cannot be synthesized',
        hint: 'Formula: min( breadth_ceiling_mid, ftd_range_mid, market_top_budget_mid )',
      },
    },
    market_top: {
      zh: {
        title: '頂部風險 · 大盤是否已過熱',
        desc:  '綜合 distribution day（高量殺低天數）、領導股是否轉弱、防禦類股是否輪動進場、新高家數萎縮、Russell 2000 落後 SPY 程度等多類指標 → 合成 0-100 分。分數越高代表頂部訊號越多，需要降倉防範。與 breadth 互補：breadth 看「現在健康嗎」，這個看「快崩了嗎」。',
        stages: [
          { key: 'mt_normal',     range: [0,29],   range_label: 'score 0-30',   tag: '正常',     action: '可進攻',      detail: '暫無頂部訊號，廣度與領導同步，倉位上限可拉滿' },
          { key: 'mt_warning',    range: [30,49],  range_label: 'score 30-50',  tag: '早期警告', action: '留意',        detail: '個別訊號出現（如 distribution day 累積），上限不變但需密切觀察' },
          { key: 'mt_elevated',   range: [50,64],  range_label: 'score 50-65',  tag: '風險升高', action: '降倉、收緊',  detail: '訊號累積中，倉位上限調降至 60-80%、停損收緊' },
          { key: 'mt_high',       range: [65,79],  range_label: 'score 65-80',  tag: '高機率頂部', action: '撤退中',     detail: '明確頂部訊號，倉位上限 40-60%、僅留高 conviction 標的' },
          { key: 'mt_top',        range: [80,100], range_label: 'score 80+',    tag: '頂部成形', action: 'Cash 優先',  detail: '訊號全到位，倉位上限 ≤ 30%、現金為主等修正' },
        ],
        no_active: '頂部資料缺失或來源失敗',
        hint: '組合內部：distribution day / leadership / defensive rotation / 新高萎縮 等子分數',
      },
      en: {
        title: 'Market Top Risk · Is the market overheated',
        desc:  'Composite of distribution days, leadership deterioration, defensive sector rotation, new-high contraction, Russell 2000 lagging SPY, etc. → 0-100 risk score. Higher = more topping signals stacked, time to de-risk. Complementary to breadth: breadth = "is it healthy now", market top = "is it about to crack".',
        stages: [
          { key: 'mt_normal',     range: [0,29],   range_label: 'score 0-30',   tag: 'Normal',         action: 'Attack',       detail: 'No topping signals, breadth + leadership aligned, full size OK' },
          { key: 'mt_warning',    range: [30,49],  range_label: 'score 30-50',  tag: 'Early warning',  action: 'Watch',        detail: 'Isolated signals (e.g. distribution days) — size unchanged but monitor' },
          { key: 'mt_elevated',   range: [50,64],  range_label: 'score 50-65',  tag: 'Elevated',       action: 'Cut & tighten',detail: 'Signals stacking — cap at 60-80%, tighten stops' },
          { key: 'mt_high',       range: [65,79],  range_label: 'score 65-80',  tag: 'High risk',      action: 'Retreat',      detail: 'Clear top signals — cap at 40-60%, keep only high-conviction names' },
          { key: 'mt_top',        range: [80,100], range_label: 'score 80+',    tag: 'Top formed',     action: 'Cash priority',detail: 'All signals tripped — cap ≤30%, cash priority, wait for correction' },
        ],
        no_active: 'Market top data unavailable / source failed',
        hint: 'Sub-scores include: distribution days / leadership / defensive rotation / new-high contraction',
      },
    },
  };

  function classifyStage(stages, daysSince) {
    if (daysSince == null || daysSince === '' || isNaN(daysSince)) return null;
    const n = Number(daysSince);
    return stages.find(s => n >= s.range[0] && n <= s.range[1]) || null;
  }

  const STAGE_DOTS = {
    // FTD
    prime: '🟢', standard: '🟡', late_cycle: '🟠', exhausted: '🔴',
    // Breadth
    br_strong: '🟢', br_healthy: '🟢', br_neutral: '🟡', br_weakening: '🟠', br_critical: '🔴',
    // Market top
    mt_normal: '🟢', mt_warning: '🟡', mt_elevated: '🟠', mt_high: '🟠', mt_top: '🔴',
    // Synth ceiling
    sy_aggressive: '🟢', sy_standard: '🟡', sy_defensive: '🟠', sy_crisis: '🔴',
  };

  function renderStageRows(stages, activeStage) {
    return stages.map(s => {
      const active = activeStage && s.key === activeStage.key;
      return `<div class="stt-stage-row${active ? ' stt-stage-active' : ''}">
        <span class="stt-stage-dot">${STAGE_DOTS[s.key] || '⚪'}</span>
        <span class="stt-stage-range">${s.range_label}</span>
        <span class="stt-stage-tag">${s.tag}</span>
        <span class="stt-stage-action">${s.action}</span>
        <div class="stt-stage-detail">${s.detail}</div>
      </div>`;
    }).join('');
  }

  // Per-signal live banner builders. Return { liveHTML, stage } for the active state.
  function ftdLive(el, t, lang) {
    const state = el.dataset.ftdState || '';
    const date  = el.dataset.ftdDate || '';
    const day   = el.dataset.ftdDay;
    if (state !== 'FTD_CONFIRMED' || !date) return { liveHTML: `<div class="stt-live"><span>${t.no_active}</span></div>`, stage: null };
    const stage = classifyStage(t.stages, day);
    if (!stage) return { liveHTML: `<div class="stt-live"><span>${t.no_active}</span></div>`, stage: null };
    const dayLabel = lang === 'en' ? `day ${day}` : `已過 ${day} 天`;
    const liveHTML = `<div class="stt-live">
      <span class="stt-live-dot">${STAGE_DOTS[stage.key] || '⚪'}</span>
      <span>📅 ${date}</span>
      <span class="stt-live-day">· ${dayLabel}</span>
      <span class="stt-live-stage">${stage.tag} — ${stage.action}</span>
    </div>`;
    return { liveHTML, stage };
  }

  function breadthLive(el, t, lang) {
    const score = el.dataset.brScore;
    const zone  = el.dataset.brZone || '';
    const ceil  = el.dataset.brCeiling || '';
    if (score === '' || score == null) return { liveHTML: `<div class="stt-live"><span>${t.no_active}</span></div>`, stage: null };
    const stage = classifyStage(t.stages, score);
    const ceilLabel = lang === 'en' ? `ceiling ${ceil}` : `建議倉位 ${ceil}`;
    const liveHTML = `<div class="stt-live">
      <span class="stt-live-dot">${STAGE_DOTS[stage?.key] || '⚪'}</span>
      <span>📊 ${Number(score).toFixed(1)}</span>
      <span class="stt-live-day">· ${zone}</span>
      <span class="stt-live-stage">${ceilLabel}</span>
    </div>`;
    return { liveHTML, stage };
  }

  function marketTopLive(el, t, lang) {
    const score  = el.dataset.mtScore;
    const zone   = (el.dataset.mtZone || '').replace(/\(.*\)/, '').trim();
    const budget = el.dataset.mtBudget || '';
    if (score === '' || score == null) return { liveHTML: `<div class="stt-live"><span>${t.no_active}</span></div>`, stage: null };
    const stage = classifyStage(t.stages, score);
    const budgetLabel = lang === 'en' ? `budget ${budget}` : `風控 ${budget}`;
    const liveHTML = `<div class="stt-live">
      <span class="stt-live-dot">${STAGE_DOTS[stage?.key] || '⚪'}</span>
      <span>⚠️ ${Number(score).toFixed(1)}</span>
      <span class="stt-live-day">· ${zone}</span>
      <span class="stt-live-stage">${budgetLabel}</span>
    </div>`;
    return { liveHTML, stage };
  }

  function synthLive(el, t, lang) {
    const mid    = el.dataset.synthMid;
    const label  = el.dataset.synthLabel || '';
    const brC    = el.dataset.brCeiling || '—';
    const ftdR   = el.dataset.ftdRange || '—';
    const mtB    = el.dataset.mtBudget || '—';
    if (mid === '' || mid == null) return { liveHTML: `<div class="stt-live"><span>${t.no_active}</span></div>`, stage: null };
    const stage = classifyStage(t.stages, mid);
    const sourceLabel = lang === 'en'
      ? `breadth ${brC} · FTD ${ftdR} · top ${mtB}`
      : `廣度 ${brC} · FTD ${ftdR} · 頂部 ${mtB}`;
    const liveHTML = `<div class="stt-live">
      <span class="stt-live-dot">${STAGE_DOTS[stage?.key] || '⚪'}</span>
      <span>🎯 ${label}</span>
      <span class="stt-live-stage">${stage?.tag || ''} — ${stage?.action || ''}</span>
    </div>
    <div class="stt-live-sources">${sourceLabel}</div>`;
    return { liveHTML, stage };
  }

  const LIVE_BUILDERS = { ftd: ftdLive, breadth: breadthLive, market_top: marketTopLive, synth: synthLive };

  function buildSignalTipHTML(el, lang) {
    const key = el.dataset.signalTip;
    const tBundle = SIGNAL_TIPS[key];
    if (!tBundle) return '';
    const t = tBundle[lang === 'en' ? 'en' : 'zh'];
    const builder = LIVE_BUILDERS[key];
    const { liveHTML, stage } = builder ? builder(el, t, lang) : { liveHTML: '', stage: null };
    return `
      <div class="stt-title">${t.title}</div>
      <div class="stt-desc">${t.desc}</div>
      ${liveHTML}
      <div class="stt-stages">${renderStageRows(t.stages, stage)}</div>
      <div class="stt-hint">${t.hint}</div>
    `;
  }

  function showSignalTip(el) {
    const key = el.dataset.signalTip;
    if (!SIGNAL_TIPS[key]) return;
    const lang = UI.currentLang || 'zh';
    tip.innerHTML = buildSignalTipHTML(el, lang);

    tip.style.opacity = '0';
    tip.style.top = '-9999px';
    tip.classList.add('visible');
    requestAnimationFrame(() => {
      const rect = el.getBoundingClientRect();
      const tRect = tip.getBoundingClientRect();
      const gap = 8;
      let top = rect.bottom + gap;
      if (top + tRect.height > window.innerHeight - 8) top = rect.top - tRect.height - gap;
      let left = rect.left + (rect.width - tRect.width) / 2;
      left = Math.max(8, Math.min(left, window.innerWidth - tRect.width - 8));
      tip.style.top = top + 'px';
      tip.style.left = left + 'px';
      tip.style.opacity = '';
    });
  }

  function hideSignalTip() {
    tip.classList.remove('visible');
  }

  document.addEventListener('mouseover', e => {
    const el = e.target.closest('[data-signal-tip]');
    if (!el) return;
    if (_hideTimer) { clearTimeout(_hideTimer); _hideTimer = null; }
    showSignalTip(el);
  });
  document.addEventListener('mouseout', e => {
    const el = e.target.closest('[data-signal-tip]');
    if (!el) return;
    _hideTimer = setTimeout(hideSignalTip, 80);
  });
})();
