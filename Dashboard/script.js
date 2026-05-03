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

  // Build a 10-cell .score-battery for any 0-100 score with a colour tint
  // (reused style from Momentum teaser at line ~520 — identical visual language).
  const battery = (val, color) => {
    const v = Math.max(0, Math.min(100, Number(val) || 0));
    const filled = Math.round(v / 10);
    let cells = '';
    for (let c = 0; c < 10; c++) {
      const bg = c < filled ? color : 'rgba(161,161,170,0.18)';
      cells += `<div class="cell" style="background:${bg}"></div>`;
    }
    return `<div class="score-battery mt-1">${cells}</div>`;
  };

  const tr = tvT();
  const brColor    = zoneCol(br.zone);
  const ftdColor   = ftdCol(ftd.state);
  const mtColor    = zoneCol(mt.zone);

  el.innerHTML = `
    <div class="grid grid-cols-1 md:grid-cols-4 gap-3 items-start">
      <div class="flex flex-col gap-0.5 px-1 -mx-1" data-signal-tip="breadth"
           data-br-score="${UI.escapeHTML(br.score ?? '')}" data-br-zone="${UI.escapeHTML(br.zone || '')}"
           data-br-ceiling="${UI.escapeHTML(br.exposure_ceiling || '')}">
        <span class="text-[9px] font-black uppercase tracking-widest text-zinc-500">${UI.escapeHTML(tr.signal_breadth || 'Breadth')}</span>
        <div class="flex items-baseline gap-2">
          <span class="text-xl font-black" style="color:${brColor}">${UI.escapeHTML(br.score ?? '—')}</span>
          <span class="text-[10px] text-zinc-500 truncate">${UI.escapeHTML(br.zone || '')}</span>
        </div>
        ${br.score != null ? battery(br.score, brColor) : ''}
      </div>
      <div class="flex flex-col gap-0.5 px-1 -mx-1" data-signal-tip="ftd"
           data-ftd-state="${UI.escapeHTML(ftd.state || '')}" data-ftd-date="${UI.escapeHTML(ftd.ftd_date || '')}"
           data-ftd-day="${UI.escapeHTML(ftd.days_since_ftd ?? '')}" data-ftd-status="${UI.escapeHTML(ftd.ftd_status_text || '')}">
        <span class="text-[9px] font-black uppercase tracking-widest text-zinc-500">${UI.escapeHTML(tr.signal_ftd || 'FTD')}</span>
        <div class="flex items-baseline gap-2">
          <span class="text-xl font-black" style="color:${ftdColor}">${UI.escapeHTML(ftd.quality_score ?? '—')}</span>
          <span class="text-[10px] text-zinc-500 truncate">${UI.escapeHTML((ftd.state||'').replace(/_/g,' '))}</span>
        </div>
        ${ftd.quality_score != null ? battery(ftd.quality_score, ftdColor) : ''}
        ${ftd.ftd_date ? `<span class="text-[9px] text-zinc-500 font-mono mt-0.5">${UI.escapeHTML(ftd.ftd_date)} · day ${UI.escapeHTML(ftd.days_since_ftd ?? '—')}</span>` : ''}
      </div>
      <div class="flex flex-col gap-0.5 px-1 -mx-1" data-signal-tip="market_top"
           data-mt-score="${UI.escapeHTML(mt.composite_score ?? '')}" data-mt-zone="${UI.escapeHTML(mt.zone || '')}"
           data-mt-budget="${UI.escapeHTML(mt.risk_budget || '')}">
        <span class="text-[9px] font-black uppercase tracking-widest text-zinc-500">${UI.escapeHTML(tr.signal_top || 'Market Top')}</span>
        <div class="flex items-baseline gap-2">
          <span class="text-xl font-black" style="color:${mtColor}">${UI.escapeHTML(mt.composite_score ?? '—')}</span>
          <span class="text-[10px] text-zinc-500 truncate">${UI.escapeHTML((mt.zone||'').replace(/\(.*\)/,'').trim())}</span>
        </div>
        ${mt.composite_score != null ? battery(mt.composite_score, mtColor) : ''}
      </div>
      <div class="flex flex-col gap-0.5 items-end md:border-l md:border-zinc-800 md:pl-3 px-1 -mx-1" data-signal-tip="synth"
           data-synth-mid="${UI.escapeHTML(synth ?? '')}" data-synth-label="${UI.escapeHTML(synthLabel)}"
           data-br-ceiling="${UI.escapeHTML(br.exposure_ceiling || '')}" data-ftd-range="${UI.escapeHTML(ftd.exposure_range || '')}"
           data-mt-budget="${UI.escapeHTML(mt.risk_budget || '')}">
        <span class="text-[9px] font-black uppercase tracking-widest text-zinc-500">${UI.escapeHTML(tr.synthesized_ceiling || 'Synthesized Ceiling')}</span>
        <span class="text-xl font-black" style="color:${synthColor}">${UI.escapeHTML(synthLabel)}</span>
        ${synth != null ? battery(synth, synthColor) : ''}
      </div>
    </div>`;
}

// ── V1.73.4 — Sector status row (8 circular gauges) — promoted from page-sector.js ──
function _gaugeColor(score, polarity) {
    const s = Number(score) || 0;
    if (polarity === 'amber') {
        if (s >= 70) return '#d97706';
        if (s >= 40) return '#f59e0b';
        return '#fbbf24';
    }
    if (polarity === 'amber-bell') {
        if (s < 15 || s > 85) return '#d97706';
        if (s < 30 || s > 75) return '#f59e0b';
        return '#fbbf24';
    }
    if (polarity === 'negative') {
        if (s >= 70) return '#ef4444';
        if (s >= 40) return '#f59e0b';
        return '#22c55e';
    }
    if (polarity === 'bell') {
        if (s < 15 || s > 85) return '#ef4444';
        if (s < 30 || s > 75) return '#f59e0b';
        return '#22c55e';
    }
    if (s >= 70) return '#22c55e';
    if (s >= 40) return '#f59e0b';
    return '#ef4444';
}

function _gaugeHTML({ value, label, suffix, color, valueDisplay, max = 100, displaySize = 'lg' }) {
    const v = Number.isFinite(value) ? value : null;
    const pct = v == null ? 0 : Math.max(0, Math.min(100, (v / max) * 100));
    const C = 264;
    const dash = (pct / 100) * C;
    const display = valueDisplay != null ? valueDisplay : (v == null ? '--' : Math.round(v));
    const sizeClass = displaySize === 'sm' ? 'sector-gauge-value-sm'
                    : displaySize === 'md' ? 'sector-gauge-value-md' : '';
    return `
        <div class="sector-gauge" style="--gauge-color:${color}">
            <svg class="sector-gauge-svg" viewBox="0 0 100 100">
                <circle class="sector-gauge-track" cx="50" cy="50" r="42"></circle>
                <circle class="sector-gauge-fill"  cx="50" cy="50" r="42"
                        stroke-dasharray="${dash.toFixed(1)} ${C}"></circle>
            </svg>
            <div class="sector-gauge-center">
                <div class="sector-gauge-value ${sizeClass}">${display}</div>
                ${suffix ? `<div class="sector-gauge-suffix">${suffix}</div>` : ''}
            </div>
            <div class="sector-gauge-label">${label}</div>
        </div>`;
}

function _gaugeSegmentedHTML({ segments, activeIndex, label, valueDisplay, color, displaySize = 'sm' }) {
    const N = segments.length;
    const C = 264;
    const gapPx = 5;
    const segLen = (C - N * gapPx) / N;
    const segsHTML = segments.map((seg, i) => {
        const offset = -(i * (segLen + gapPx));
        const isActive = i === activeIndex;
        const stroke = isActive ? (color || '#22c55e') : 'rgba(161,161,170,0.18)';
        return `<circle class="sector-gauge-seg ${isActive ? 'active' : ''}"
                cx="50" cy="50" r="42"
                stroke="${stroke}"
                stroke-dasharray="${segLen.toFixed(1)} ${(C - segLen).toFixed(1)}"
                stroke-dashoffset="${offset.toFixed(1)}"></circle>`;
    }).join('');
    const sizeClass = displaySize === 'sm' ? 'sector-gauge-value-sm' : 'sector-gauge-value-md';
    const display = valueDisplay
        || (activeIndex >= 0 && segments[activeIndex] ? (segments[activeIndex].label || segments[activeIndex]) : '--');
    return `
        <div class="sector-gauge" style="--gauge-color:${color || '#22c55e'}">
            <svg class="sector-gauge-svg" viewBox="0 0 100 100">
                ${segsHTML}
            </svg>
            <div class="sector-gauge-center">
                <div class="sector-gauge-value ${sizeClass}">${display}</div>
            </div>
            <div class="sector-gauge-label">${label}</div>
        </div>`;
}

function renderSectorStatusStrip(data) {
    const m   = data.market || {};
    const br  = data.breadth || {};
    const ftd = data.ftd     || {};
    const mt  = data.market_top || {};
    const isZh = UI.currentLang === 'zh';
    const tr = (window.i18n?.[UI.currentLang]?.sector_page) || {};

    // ── 4 numeric gauges ─────────────────────────────────────────
    const breadthScore = br.score ?? m.breadth_score;
    const breadthEl = document.getElementById('pill-breadth');
    if (breadthEl) {
        breadthEl.innerHTML = _gaugeHTML({
            value: breadthScore,
            label: tr.pill_breadth || (isZh ? '廣度分數' : 'Breadth'),
            color: _gaugeColor(breadthScore, 'positive'),
        });
    }

    const ftdScore = ftd.quality_score;
    const ftdEl = document.getElementById('pill-ftd');
    if (ftdEl) {
        ftdEl.innerHTML = _gaugeHTML({
            value: ftdScore,
            label: tr.pill_ftd || (isZh ? 'FTD 狀態' : 'FTD'),
            color: ftd.state === 'FTD_CONFIRMED' ? '#22c55e'
                 : _gaugeColor(ftdScore, 'positive'),
        });
    }

    const mtScore = mt.composite_score ?? mt.score ?? m.market_top_score;
    const mtopEl = document.getElementById('pill-marketop');
    if (mtopEl) {
        mtopEl.innerHTML = _gaugeHTML({
            value: mtScore,
            label: tr.pill_marketop || (isZh ? '頂部風險' : 'Market Top'),
            color: _gaugeColor(mtScore, 'amber'),
        });
    }

    const fgScore = m.fear_greed ?? m.fear_greed_index;
    const fgEl = document.getElementById('pill-fg');
    if (fgEl) {
        fgEl.innerHTML = _gaugeHTML({
            value: fgScore,
            label: tr.pill_fg || (isZh ? '恐懼貪婪' : 'Fear & Greed'),
            color: _gaugeColor(fgScore, 'amber-bell'),
        });
    }

    // ── 4 categorical / scaled gauges ────────────────────────────
    const regimeEl = document.getElementById('pill-regime');
    if (regimeEl) {
        const REGIME_SEG = [
            { key: 'BULL',     label: 'BULL',     color: '#22c55e', map: ['BULL', 'RISK_ON'] },
            { key: 'SIDEWAYS', label: 'SIDE',     color: '#eab308', map: ['SIDEWAYS'] },
            { key: 'VOLATILE', label: 'VOL',      color: '#f97316', map: ['VOLATILE'] },
            { key: 'BEAR',     label: 'BEAR',     color: '#ef4444', map: ['BEAR', 'RISK_OFF'] },
        ];
        const cur = (m.regime || '').toUpperCase();
        const activeIdx = REGIME_SEG.findIndex(s => s.map.includes(cur));
        const activeColor = activeIdx >= 0 ? REGIME_SEG[activeIdx].color : '#71717a';
        regimeEl.innerHTML = _gaugeSegmentedHTML({
            segments: REGIME_SEG,
            activeIndex: activeIdx,
            label: tr.pill_regime || (isZh ? '市場體制' : 'Regime'),
            valueDisplay: cur || '--',
            color: activeColor,
            displaySize: 'sm',
        });
    }

    const cycleEl = document.getElementById('pill-cycle');
    if (cycleEl) {
        const CYCLE_SEG = [
            { key: 'Early',     label: 'EARLY', color: '#22c55e' },
            { key: 'Mid',       label: 'MID',   color: '#84cc16' },
            { key: 'Late',      label: 'LATE',  color: '#f59e0b' },
            { key: 'Recession', label: 'REC',   color: '#ef4444' },
        ];
        const cur = m.cycle_phase || '';
        const activeIdx = CYCLE_SEG.findIndex(s => s.key.toLowerCase() === cur.toLowerCase());
        const activeColor = activeIdx >= 0 ? CYCLE_SEG[activeIdx].color : '#71717a';
        cycleEl.innerHTML = _gaugeSegmentedHTML({
            segments: CYCLE_SEG,
            activeIndex: activeIdx,
            label: tr.pill_cycle || (isZh ? '週期位置' : 'Cycle'),
            valueDisplay: (cur || '--').toUpperCase(),
            color: activeColor,
            displaySize: 'sm',
        });
    }

    const exposureEl = document.getElementById('pill-exposure');
    if (exposureEl) {
        const raw = m.exposure_ceiling || '';
        const m1 = raw.match(/(\d+)\s*-\s*(\d+)/);
        const single = raw.match(/(\d+)/);
        let midPct = null, displayStr = '--';
        if (m1) {
            midPct = (Number(m1[1]) + Number(m1[2])) / 2;
            displayStr = `${m1[1]}-${m1[2]}<span class="sector-gauge-unit">%</span>`;
        } else if (single) {
            midPct = Number(single[1]);
            displayStr = `${single[1]}<span class="sector-gauge-unit">%</span>`;
        }
        exposureEl.innerHTML = _gaugeHTML({
            value: midPct,
            label: tr.pill_exposure || (isZh ? '曝險上限' : 'Exposure'),
            valueDisplay: displayStr,
            color: '#a78bfa',
            displaySize: 'md',
        });
    }

    const vixEl = document.getElementById('pill-vix');
    if (vixEl) {
        const vix = mt.vix_level;
        const vixColor = vix == null ? '#71717a'
                       : vix >= 25 ? '#ef4444'
                       : vix >= 18 ? '#f59e0b'
                       : '#22c55e';
        const display = vix != null ? Number(vix).toFixed(1) : '--';
        vixEl.innerHTML = _gaugeHTML({
            value: vix,
            max: 40,
            label: tr.pill_vix || (isZh ? '波動指數' : 'VIX'),
            valueDisplay: display,
            color: vixColor,
            displaySize: 'md',
        });
    }

    // Data attrs for shared signal-tip engine (utils.js)
    const setAttrs = (id, attrs) => {
        const el = document.getElementById(id);
        if (!el) return;
        Object.entries(attrs).forEach(([k, v]) => el.setAttribute(k, v == null ? '' : String(v)));
    };
    setAttrs('pill-regime',   { 'data-regime': m.regime || '' });
    setAttrs('pill-breadth',  { 'data-br-score':   br.score ?? m.breadth_score ?? '',
                                'data-br-zone':    br.zone || '',
                                'data-br-ceiling': br.exposure_ceiling || m.exposure_ceiling || '' });
    setAttrs('pill-ftd',      { 'data-ftd-state': ftd.state || '',
                                'data-ftd-date':  ftd.ftd_date || '',
                                'data-ftd-day':   ftd.days_since_ftd ?? '' });
    setAttrs('pill-marketop', { 'data-mt-score': mt.composite_score ?? '',
                                'data-mt-zone':  mt.zone || '' });
    setAttrs('pill-exposure', { 'data-exposure': m.exposure_ceiling || '' });
    setAttrs('pill-fg',       { 'data-fg-score': m.fear_greed ?? '',
                                'data-fg-label': m.fear_greed_label || '' });
    setAttrs('pill-cycle',    { 'data-cycle': m.cycle_phase || '' });
    setAttrs('pill-vix',      { 'data-vix': mt.vix_level ?? '' });
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

// V1.73.4 — #risk-overview now contains the 8-gauge status row (always populated when data
// loaded), so unconditionally unhide it. binary-alert-section is sibling and manages its own.
function updateRiskOverviewVisibility() {
  const wrap = document.getElementById('risk-overview');
  if (!wrap) return;
  // Status row pills are always rendered after data loads → keep visible
  wrap.classList.remove('hidden');

  // Apply translated title each time (covers both initial render and language toggle)
  const titleEl = document.getElementById('risk-overview-title-text');
  const w = window.i18n?.[UI.currentLang]?.warnings || {};
  if (titleEl && w.risk_overview_title) titleEl.textContent = w.risk_overview_title;

  // Count badge — total active flags (state-driven only; binary_alert is event-driven)
  const countEl = document.getElementById('risk-overview-count');
  if (countEl) {
    const n = flags ? flags.children.length : 0;
    if (n > 0) {
      const isZh = UI.currentLang === 'zh';
      countEl.textContent = isZh ? `${n} 項` : `${n} active`;
      countEl.classList.remove('hidden');
    } else {
      countEl.classList.add('hidden');
    }
  }
}

// V1.73.4 — Adaptive binary alert (≤2 inline / 3-5 grid / ≥6 collapsible) — ported from sector page
function renderBinaryAlertIndex(risks) {
  const urgent = (risks || []).filter(r => r.within_48h);
  const section = document.getElementById('binary-alert-section');
  if (!section) { return; }
  if (!urgent.length) { section.classList.add('hidden'); updateRiskOverviewVisibility(); return; }
  section.classList.remove('hidden');

  const isZh = UI.currentLang === 'zh';
  const sp = window.i18n?.[UI.currentLang]?.sector_page || {};
  // Translated header strings
  const titleEl = document.getElementById('binary-alert-title');
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
  const renderRow = (r) => {
    const lbl = dateLabel(r);
    const cls = r.days_until === 0 ? '' : r.days_until === 1 ? 'tomorrow' : 'future';
    const sectorTxt = (r.affected_sectors && r.affected_sectors.length)
      ? r.affected_sectors.slice(0, 3).map(s => sectorLabelIndex(s)).join(' · ')
      : '';
    return `
      <div class="binary-adaptive-row">
        <span class="binary-day-pill ${cls}">${UI.escapeHTML(lbl)}</span>
        <span class="binary-event-text" title="${UI.escapeHTML(r.event || '')}">${UI.escapeHTML(r.event || '')}</span>
        ${sectorTxt ? `<span class="binary-sectors-inline">${UI.escapeHTML(sectorTxt)}</span>` : ''}
      </div>`;
  };

  const N = urgent.length;
  const list = document.getElementById('binary-alert-items');
  const countEl = document.getElementById('binary-alert-count');
  if (countEl) countEl.textContent = N === 1 ? '1 event' : `${N} events`;

  if (N <= 2) {
    list.dataset.density = 'compact';
    list.innerHTML = urgent.map(renderRow).join('');
  } else if (N <= 5) {
    list.dataset.density = 'grid';
    list.innerHTML = urgent.map(renderRow).join('');
  } else {
    list.dataset.density = 'compact';
    const first = urgent.slice(0, 2);
    const rest  = urgent.slice(2);
    const moreLabel = isZh ? `展開更多 ${rest.length}` : `Show ${rest.length} more`;
    const lessLabel = isZh ? '收合' : 'Collapse';
    list.innerHTML = `
      ${first.map(renderRow).join('')}
      <details class="binary-collapsible">
        <summary class="binary-collapsible-summary">
          <span class="caret">▸</span>
          <span class="open-label">${UI.escapeHTML(moreLabel)}</span>
          <span class="close-label" style="display:none">${UI.escapeHTML(lessLabel)}</span>
        </summary>
        ${rest.map(renderRow).join('')}
      </details>
    `;
    const det = list.querySelector('.binary-collapsible');
    det?.addEventListener('toggle', () => {
      const ol = det.querySelector('.open-label');
      const cl = det.querySelector('.close-label');
      if (ol) ol.style.display = det.open ? 'none' : '';
      if (cl) cl.style.display = det.open ? '' : 'none';
    });
  }

  updateRiskOverviewVisibility();
  }


// ── Layer 2b: Severity-tiered Warning Flags strip ─────────────────────────
// Schema: prefer `market.warning_flags_v2` (object[] from bridge.py with key/severity/metric_value).
// Fall back to legacy `market.warning_flags` (string[]) so old data.json still renders.
const WARN_SEVERITY_DEFAULT = {
  Bearish_Signal_Active:     'critical',
  Critical_Zone:             'critical',
  Death_Cross_SP500:         'critical',
  Extreme_Fear_Sentiment:    'critical',
  Below_200MA:               'warning',
  Low_Historical_Percentile: 'warning',
  Early_Warning_Divergence:  'warning',
  Narrowing_Breadth:         'warning',
  Mean_Reversion_Risk:       'warning',
  Late_Cycle:                'caution',
  High_Selectivity:          'caution',
  Overbought:                'caution',
  Oversold:                  'caution',
  Weakening_Zone:            'caution',
};
const WARN_SEVERITY_RANK = { critical: 0, warning: 1, caution: 2 };

function _formatFlagMetric(key, mv) {
  if (!mv || typeof mv !== 'object') return '';
  if (key === 'Below_200MA' && mv.gap_pct != null) {
    const g = Number(mv.gap_pct);
    return `gap ${g >= 0 ? '+' : ''}${g.toFixed(2)}%`;
  }
  if (key === 'Low_Historical_Percentile' && mv.percentile != null) {
    return `pct ${Number(mv.percentile).toFixed(0)}%`;
  }
  if ((key === 'Weakening_Zone' || key === 'Critical_Zone') && mv.breadth_score != null) {
    return `score ${Number(mv.breadth_score).toFixed(1)}`;
  }
  if (key === 'Bearish_Signal_Active' && mv.bearish_score != null) {
    return `risk ${Number(mv.bearish_score).toFixed(0)}`;
  }
  if (key === 'Early_Warning_Divergence' && mv.signal) {
    return String(mv.signal).toLowerCase();
  }
  return '';
}

// V1.73.4 — Flags already encoded in Breadth gauge (now on dashboard) — filter to avoid dup
const REDUNDANT_FLAGS_DASH = new Set(['Below_200MA', 'Critical_Zone', 'Weakening_Zone']);

// V1.73.4 — Map flag key → SIGNAL_TIPS key so shared #signal-tip-tooltip engine renders
const FLAG_TIP_KEY_DASH = {
  Bearish_Signal_Active:     'bearish_signal',
  Low_Historical_Percentile: 'low_historical_percentile',
  Early_Warning_Divergence:  'divergence',
};

function renderWarningFlagsIndex(market) {
  const row = document.getElementById('warning-flags-row');
  if (!row) return;
  row.innerHTML = '';

  // Normalize to object[] regardless of schema
  let flags = [];
  if (Array.isArray(market?.warning_flags_v2) && market.warning_flags_v2.length) {
    flags = market.warning_flags_v2;
  } else if (Array.isArray(market?.warning_flags) && market.warning_flags.length) {
    flags = market.warning_flags.map(k => ({ key: k, severity: WARN_SEVERITY_DEFAULT[k] || 'caution', metric_value: null }));
  }
  // V1.73.4 — Filter flags already encoded in Breadth circular gauge (avoid duplicate signal)
  flags = flags.filter(f => f.key && !REDUNDANT_FLAGS_DASH.has(f.key));

  if (!flags.length) { updateRiskOverviewVisibility(); return; }

  // Sort: critical → warning → caution; preserve original order within tier
  flags = flags.map((f, i) => ({ ...f, _ix: i }))
               .sort((a, b) => (WARN_SEVERITY_RANK[a.severity] ?? 9) - (WARN_SEVERITY_RANK[b.severity] ?? 9) || a._ix - b._ix);

  const tw = window.i18n?.[UI.currentLang]?.warnings || {};
  const flagNames = tw.flags || {};

  // V1.73.4 — route to #signal-tip-tooltip engine (rich style, matches gauges)
  const html = flags.map(f => {
    const key      = f.key || '';
    const severity = f.severity || WARN_SEVERITY_DEFAULT[key] || 'caution';
    const name     = flagNames[key] || key.replace(/_/g, ' ');
    const metric   = _formatFlagMetric(key, f.metric_value);
    const tipKey   = FLAG_TIP_KEY_DASH[key] || '';
    const tipAttr  = tipKey ? `data-signal-tip="${tipKey}"` : '';
    return `<div class="risk-flag-card risk-flag-sector sev-${UI.escapeHTML(severity)}"
                 ${tipAttr}
                 data-flag-key="${UI.escapeHTML(key)}"
                 data-flag-severity="${UI.escapeHTML(severity)}"
                 data-flag-name="${UI.escapeHTML(name)}"
                 data-flag-metric="${UI.escapeHTML(metric)}">
              <span class="rfc-dot"></span>
              <div class="rfc-text">
                <span class="rfc-name">${UI.escapeHTML(name)}</span>
                ${metric ? `<span class="rfc-metric">${UI.escapeHTML(metric)}</span>` : ''}
              </div>
            </div>`;
  }).join('');

  row.innerHTML = html;
  updateRiskOverviewVisibility();
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
      <a href="${UI.escapeHTML(href)}" class="flex items-center justify-between no-underline group">
        <div class="flex flex-col">
          <div class="flex items-center gap-2">
            <span class="text-base font-black tracking-tight" style="color:var(--text-card-title)">${UI.escapeHTML(s.proxy_etf || s.name)}</span>
            <span class="text-[9px] font-black px-1.5 py-0.5 rounded mt-[-5px]" style="background:${col}1A;color:${col}">${UI.escapeHTML(s.verdict)}</span>
          </div>
          <span class="text-[10px] text-zinc-500">${UI.escapeHTML(sectorLabelIndex(s.name || ''))}</span>
        </div>
        <div class="flex flex-col items-end">
          <span class="text-[14px] font-black font-mono" style="color:${col}">${UI.escapeHTML(s.score ?? '—')}</span>
          <span class="text-[9px] text-zinc-500 group-hover:text-emerald-500 transition-all">→</span>
        </div>
      </a>

      <!-- Lead Tickers: Horiz pills -->
      <div class="flex flex-wrap gap-2 mt-2 pt-2 border-t border-zinc-200/10 dark:border-zinc-800/40">
        ${sectorStocks.length ? sectorStocks.map(r => {
          const sCol = (r.score||0) >= 70 ? '#3b82f6' : (r.score||0) >= 50 ? '#22c55e' : '#eab308';
          return `<a href="momentum.html?search=${encodeURIComponent(r.ticker || '')}" class="sector-ticker-pill no-underline">
            <div class="score-dot" style="background:${sCol}"></div>
            <span>${UI.escapeHTML(r.ticker)}</span>
            <span class="text-[8px] opacity-60">${UI.escapeHTML(r.score?.toFixed(0) ?? '')}</span>
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
        <span class="impact-badge" style="background:${col}1A;color:${col}">${UI.escapeHTML(label)}</span>
        <span class="text-[12px] font-black font-mono" style="color:${col}">${UI.escapeHTML(scoreTxt)}</span>
      </div>

      <!-- Title: Headline -->
      <h4 class="text-[11px] font-bold leading-tight" style="color:var(--text-card-title)">${UI.escapeHTML(n.headline_zh || n.headline || '')}</h4>

      <!-- Content: Core Reason (truncated) -->
      ${reason ? `<p class="text-[10px] text-zinc-500 line-clamp-2 leading-relaxed mt-1 italic">${UI.escapeHTML(reason)}</p>` : ''}

      <!-- Footer: Sectors -->
      <div class="flex flex-wrap gap-1.5 mt-1 pt-2 border-t border-zinc-200/10 dark:border-zinc-800/40">
        ${sectors.map(s => `<span class="news-sector-pill">${UI.escapeHTML(s)}</span>`).join('')}
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
          <span class="text-base font-black tracking-tight" style="color:var(--text-card-title)">${UI.escapeHTML(r.ticker)}</span>
          ${star}
          <span class="text-[10px] text-zinc-500 font-mono ml-1">$${r.price ? Number(r.price).toFixed(2) : '—'}</span>
        </div>
        <div class="flex flex-col items-end">
          <div class="score-battery mb-1">${cellsHTML}</div>
          <span class="score-num" style="color:${tierColor}">${score.toFixed(1)}</span>
        </div>
      </div>

      <!-- Content: Pros & Cons -->
      <div class="flex flex-col gap-1.5 mt-1">
        ${pros.length ? `<div class="flex flex-wrap gap-1.5">
          ${pros.map(p => `<span class="pc-pill pc-pro"><i data-lucide="check-circle-2" class="w-2.5 h-2.5"></i> ${UI.escapeHTML(p)}</span>`).join('')}
        </div>` : ''}
        ${cons.length ? `<div class="flex flex-wrap gap-1.5">
          ${cons.map(c => `<span class="pc-pill pc-con"><i data-lucide="alert-triangle" class="w-2.5 h-2.5"></i> ${UI.escapeHTML(c)}</span>`).join('')}
        </div>` : ''}
      </div>

      <!-- Footer: Sector & RSI -->
      <div class="flex items-center justify-between mt-1 pt-2 border-t border-zinc-200/20 dark:border-zinc-800/50">
        <span class="news-sector-pill">${UI.escapeHTML(r.sector || 'Unknown')}</span>
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
  // Defence-in-depth: tickers are A-Z0-9.- in our universe; strip anything else
  // before splicing into the inline onclick string. The data fields are still
  // escaped via UI.escapeHTML for HTML attribute / text contexts.
  const safeTicker = String(pick.ticker || '').replace(/[^A-Za-z0-9.\-]/g, '');
  el.classList.remove('hidden');
  el.innerHTML = `
    <div class="focus-ticker-card">
      <div class="flex items-center gap-2 mb-1">
        <span class="text-[9px] font-black uppercase tracking-widest" style="color:#a78bfa">✨ ${isZh ? '今日焦點' : 'TODAY FOCUS'}</span>
        <span class="text-[9px] text-zinc-500">${isZh ? '三軍同向（AI verdict + 產業 + 動能）' : 'Tri-signal alignment'}</span>
      </div>
      <div class="flex items-baseline gap-3 flex-wrap">
        <span class="text-lg font-black tracking-tight" style="color:var(--text-card-title)">${UI.escapeHTML(safeTicker)}</span>
        <span class="text-[10px] text-zinc-500 font-mono">$${pick.price ? Number(pick.price).toFixed(2) : '—'}</span>
        <span class="text-[10px] font-mono" style="color:#a78bfa">score ${UI.escapeHTML(pick.score ?? '—')}</span>
        <button onclick="window.AnalyzeQueue && window.AnalyzeQueue.enqueue('${safeTicker}')"
                class="ml-auto text-[9px] font-black px-2 py-1 rounded" style="background:#a78bfa;color:#fff">
          ${isZh ? '加入佇列' : 'ENQUEUE'}
        </button>
      </div>
      <div class="text-[10px] text-zinc-500 mt-1 leading-snug">${UI.escapeHTML(sectorName)} · ${isZh ? '來自 AI overweight 產業的動能領先股' : 'Momentum leader in an AI-overweight sector'}</div>
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

    // Layer 1: Today's AI Verdict hero (4-bar mini gauge replaced by sector-status-row below)
    Components.renderTodayVerdict(data.market);

    // V1.73.4: 8-gauge status row + binary alert (adaptive) + warning flags
    renderSectorStatusStrip(data);
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

// Resolves when /api/run-protocol/status reports a non-running state.
// Used by the preflight queue runner to chain protocols sequentially —
// the backend single-job lock means we must wait between POSTs.
function waitForProtocolDone() {
  return new Promise((resolve) => {
    const id = setInterval(async () => {
      try {
        const r = await fetch('/api/run-protocol/status');
        const s = await r.json();
        if (s.status !== 'running') { clearInterval(id); resolve(s); }
      } catch (e) { /* keep polling */ }
    }, 3000);
  });
}

async function launchAnalysis() {
  const input = document.getElementById('ticker-input');
  if (!input) return;
  const ticker = input.value.trim().toUpperCase();
  if (!ticker) return;

  // 檢查是否已在佇列或正在進行中
  if (window.AnalyzeQueue) {
    const state = window.AnalyzeQueue.state || {};
    const isActive = state.active && state.active.ticker === ticker;
    const isQueued = (state.queue || []).some(q => q.ticker === ticker);

    if (isActive || isQueued) {
      const tr = window.i18n?.[UI.currentLang]?.analyze_queue || {};
      const msg = isActive
        ? (tr.toast_dup_active || `${ticker} 正在分析中`)
        : (tr.toast_dup_pending || `${ticker} 已在佇列中`);
      UI.showToast(msg.replace('{tk}', ticker), 'warning');
      input.value = '';
      return;
    }
  }

  const isZh = UI.currentLang === 'zh';
  const prefix = await UI.dailyUpdatePrefix();
  const confirmMsg = prefix + (isZh
    ? `加入個股分析佇列：${ticker}（risk=${UI.riskTolerance}）？\nV4.8 每檔約 10-15 分鐘，~$4 tokens。`
    : `Enqueue invest analysis for ${ticker} (risk=${UI.riskTolerance})?\nV4.8 ~10-15 min per ticker, ~$4 tokens.`);
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
  // V2.7.17 — render checklist into #preflight-checklist (not #preflight-body)
  // so the new chain UI in #preflight-chain coexists in the same modal.
  const body = document.getElementById('preflight-checklist') || document.getElementById('preflight-body');
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

// Run all stale (free first, then token-based sequentially)
// Order is FIXED (news → sector): sector protocol Phase 3 consumes news_protocol_v2
// output (top_catalysts[]). Running sector first would reference stale news cache.
const PREFLIGHT_PROTOCOL_MAP = { sector: 'sector', news: 'news' };
const PREFLIGHT_ORDER = ['news', 'sector'];

document.getElementById('preflight-run-all')?.addEventListener('click', async () => {
  const isZh = UI.currentLang === 'zh';
  // Step 1: run free caches
  try {
    await fetch('/api/preflight/run-free', { method: 'POST' });
  } catch (e) { /* ignore, may already be fresh */ }

  // Step 2: build queue of stale token-based items in dependency order
  const r = await fetch('/api/preflight');
  const d = await r.json();
  const queue = (d.items || [])
    .filter(i => i.status !== 'FRESH' && !i.free && PREFLIGHT_PROTOCOL_MAP[i.key])
    .sort((a, b) => PREFLIGHT_ORDER.indexOf(a.key) - PREFLIGHT_ORDER.indexOf(b.key));

  if (queue.length > 0) {
    const names = queue.map(i => isZh ? i.label : i.label_en).join(' → ');
    const ok = confirm(isZh
      ? `以下需消耗 tokens 更新（將依序執行）：\n${names}\n\n確認執行？`
      : `These need tokens to update (will run sequentially):\n${names}\n\nProceed?`);
    if (ok) {
      closePreflight();
      runPreflightQueue(queue, isZh);
      return;
    }
  }
  closePreflight();
  setTimeout(() => { updateDashboard(); loadPreflightData(); }, 5000);
});

async function runPreflightQueue(items, isZh) {
  // Enqueue all protocols at once via /api/protocol-queue (server-side FIFO).
  // Earlier impl used /api/run-protocol + frontend wait loop, which silently
  // aborted if user switched tab or reloaded — leaving sector never dispatched
  // even though news ran. Server queue keeps running regardless of UI state.
  const enqueued = [];
  for (const item of items) {
    const name = PREFLIGHT_PROTOCOL_MAP[item.key];
    const label = isZh ? item.label : item.label_en;
    try {
      const res = await fetch('/api/protocol-queue', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name }),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        UI.showToast(`${label}: ${err.error || res.statusText}`, 'error', 5000);
        continue;
      }
      const data = await res.json().catch(() => ({}));
      enqueued.push({ label, position: data.position, total_ahead: data.total_ahead });
    } catch (e) {
      UI.showToast(`${label}: ${e.message}`, 'error', 5000);
    }
  }

  if (enqueued.length === 0) {
    UI.showToast(isZh ? '沒有 protocol 被排入佇列' : 'No protocols queued', 'warn', 5000);
    return;
  }

  // Trigger existing launch-status banner so user gets live progress on index.
  if (_launchPollTimer) clearInterval(_launchPollTimer);
  _launchPollTimer = setInterval(pollLaunchStatus, 2000);
  pollLaunchStatus();

  const labels = enqueued.map(e => e.label).join(' → ');
  UI.showToast(
    isZh
      ? `已排入 ${enqueued.length} 個 protocol：${labels}（server 序列執行，切頁/關 tab 都會繼續）`
      : `${enqueued.length} protocols queued: ${labels} (runs server-side, safe to switch pages)`,
    'success', 7000
  );
  setTimeout(() => { updateDashboard(); loadPreflightData(); }, 2000);
}

// ── V2.7.17 — Pre-market check chain orchestrator ──────────────────────────
// Phase 1 (parallel): bash daily_update.sh + news Claude protocol
// Phase 2 (after both Phase 1 done): sector Claude protocol
// Phase 3 (auto): bridge.py refresh → AI verdict pills auto-update
let _chainPollTimers = { daily: null, proto: null };
let _chainState = { phase: 0, dailyDone: false, newsDone: false, sectorDone: false };
const ZH = () => UI.currentLang === 'zh';

function _setRow(rowKey, icon, meta, barPct) {
  const ic = document.getElementById(`preflight-icon-${rowKey}`);
  const mt = document.getElementById(`preflight-meta-${rowKey}`);
  const bar = document.getElementById(`preflight-bar-${rowKey}`);
  if (ic) ic.textContent = icon;
  if (mt) mt.textContent = meta;
  if (bar) bar.style.width = `${Math.max(0, Math.min(100, barPct || 0))}%`;
}
function _fmtSec(s) {
  if (s == null) return '—';
  const m = Math.floor(s / 60), x = s % 60;
  return m ? `${m}m ${String(x).padStart(2,'0')}s` : `${x}s`;
}

async function runPremarketChain() {
  const isZh = ZH();
  // Show chain UI, hide checklist
  document.getElementById('preflight-chain')?.classList.remove('hidden');
  document.getElementById('preflight-checklist')?.classList.add('hidden');
  document.getElementById('preflight-run-chain').setAttribute('disabled', 'true');

  _chainState = { phase: 1, dailyDone: false, newsDone: false, sectorDone: false };
  _setRow('daily', '🔄', isZh ? '啟動中…' : 'starting…', 0);
  _setRow('news',  '🔄', isZh ? '啟動中…' : 'starting…', 0);
  _setRow('sector','⏳', isZh ? '等 Phase 1' : 'waiting Phase 1', 0);
  _setRow('verdict','⏳', isZh ? '等 Phase 2' : 'waiting Phase 2', 0);

  // Phase 1 — fire both in parallel
  const [dailyRes, newsRes] = await Promise.allSettled([
    fetch('/api/run-daily-update', { method: 'POST' }).then(r => r.json()),
    fetch('/api/protocol-queue', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name: 'news' }),
    }).then(r => r.json()),
  ]);
  if (dailyRes.status === 'rejected' || (dailyRes.value && dailyRes.value.error && !dailyRes.value.job_id)) {
    _setRow('daily', '❌', `${isZh?'啟動失敗':'failed'}: ${dailyRes.value?.error || dailyRes.reason}`, 0);
  }
  if (newsRes.status === 'rejected' || (newsRes.value && newsRes.value.error)) {
    _setRow('news', '❌', `${isZh?'啟動失敗':'failed'}: ${newsRes.value?.error || newsRes.reason}`, 0);
  }

  // Start poll loops (independent timers)
  if (_chainPollTimers.daily) clearInterval(_chainPollTimers.daily);
  if (_chainPollTimers.proto) clearInterval(_chainPollTimers.proto);
  _chainPollTimers.daily = setInterval(_pollDailyUpdate, 2500);
  _chainPollTimers.proto = setInterval(_pollProtoForChain, 2500);
  _pollDailyUpdate();
  _pollProtoForChain();
}

async function _pollDailyUpdate() {
  const isZh = ZH();
  try {
    const r = await fetch('/api/run-daily-update/status', { cache: 'no-store' });
    if (!r.ok) return;
    const s = await r.json();
    if (s.status === 'running') {
      const step = s.current_step || 0;
      const tot  = s.total_steps  || 6;
      const pct  = (step / tot) * 100;
      _setRow('daily', '🔄', `step ${step}/${tot} · ${_fmtSec(s.elapsed_sec)}`, pct);
    } else if (s.status === 'done') {
      _setRow('daily', '✅', `${isZh?'完成':'done'} · ${_fmtSec(s.elapsed_sec)}`, 100);
      if (!_chainState.dailyDone) { _chainState.dailyDone = true; _maybeStartPhase2(); }
      clearInterval(_chainPollTimers.daily);
    } else if (s.status === 'error') {
      _setRow('daily', '❌', `${isZh?'錯誤':'error'}: ${(s.error || s.log_tail || '').slice(0, 80)}`, 100);
      clearInterval(_chainPollTimers.daily);
    }
  } catch {}
}

async function _pollProtoForChain() {
  const isZh = ZH();
  try {
    const r = await fetch('/api/run-protocol/status', { cache: 'no-store' });
    if (!r.ok) return;
    const s = await r.json();
    // Map active job by name
    const target = (_chainState.phase === 1 && !_chainState.newsDone) ? 'news'
                 : (_chainState.phase === 2 && !_chainState.sectorDone) ? 'sector'
                 : null;
    if (!target) return;
    if (s.name !== target) return;
    if (s.status === 'running') {
      _setRow(target, '🔄', `running · ${_fmtSec(s.elapsed_sec)}`, Math.min(95, (s.elapsed_sec || 0) / 9));
    } else if (s.status === 'done') {
      _setRow(target, '✅', `${isZh?'完成':'done'} · ${_fmtSec(s.elapsed_sec)}`, 100);
      if (target === 'news') {
        _chainState.newsDone = true;
        _maybeStartPhase2();
      } else if (target === 'sector') {
        _chainState.sectorDone = true;
        _finalizeChain();
      }
    } else if (s.status === 'error') {
      _setRow(target, '❌', `${isZh?'錯誤':'error'}: ${(s.error || '').slice(0, 80)}`, 100);
      // halt chain
      clearInterval(_chainPollTimers.proto);
      document.getElementById('preflight-run-chain')?.removeAttribute('disabled');
    }
  } catch {}
}

async function _maybeStartPhase2() {
  if (!_chainState.dailyDone || !_chainState.newsDone) return;
  const isZh = ZH();
  _chainState.phase = 2;
  _setRow('sector', '🔄', isZh ? '啟動中…' : 'starting…', 0);
  try {
    await fetch('/api/protocol-queue', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name: 'sector' }),
    });
  } catch (e) {
    _setRow('sector', '❌', `${isZh?'啟動失敗':'failed to start'}: ${e.message}`, 0);
  }
}

function _finalizeChain() {
  const isZh = ZH();
  clearInterval(_chainPollTimers.proto);
  _chainState.phase = 3;
  _setRow('verdict', '🔄', isZh ? '刷新中…' : 'refreshing…', 50);
  // bridge.py auto-runs in protocol worker after sector done; wait ~5s then refresh dashboard
  setTimeout(() => {
    _setRow('verdict', '✅', isZh ? 'Dashboard 更新完成' : 'dashboard updated', 100);
    updateDashboard();
    document.getElementById('preflight-run-chain')?.removeAttribute('disabled');
    UI.showToast(isZh ? '盤前檢查完成' : 'Pre-market check complete', 'success', 5000);
  }, 5000);
}

document.getElementById('preflight-run-chain')?.addEventListener('click', runPremarketChain);

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

    // Special-case: severity-tiered warning flag (Layer 2b on index.html).
    // Build a rich body from i18n.warnings.tooltips.<flag_key> + the flag's
    // own data-* attributes (name, severity, formatted metric).
    if (key === 'warning_flag') {
      const flagKey  = target.getAttribute('data-flag-key') || '';
      const severity = target.getAttribute('data-flag-severity') || 'caution';
      const name     = target.getAttribute('data-flag-name') || flagKey;
      const metric   = target.getAttribute('data-flag-metric') || '';
      const w        = (dict.warnings || {});
      const sevLabel = (w.severity && w.severity[severity]) || severity.toUpperCase();
      const tooltip  = (w.tooltips && w.tooltips[flagKey]) || {};
      const def      = tooltip.definition || '';
      const hint     = tooltip.hint || '';

      tip.innerHTML = `
        <h4 class="text-[10px] font-black uppercase tracking-widest mb-1 rft-title-${UI.escapeHTML(severity)}">
          ${UI.escapeHTML(sevLabel)} · ${UI.escapeHTML(name)}
        </h4>
        ${def ? `<p class="text-[11px] leading-relaxed text-zinc-300">${UI.escapeHTML(def)}</p>` : ''}
        ${metric ? `<div class="rft-metric-row"><span>${UI.escapeHTML(metric)}</span></div>` : ''}
        ${hint ? `<div class="rft-hint">${UI.escapeHTML(hint)}</div>` : ''}
      `;
      tip.classList.add('tip-visible');

      const rect2 = target.getBoundingClientRect();
      let left2 = rect2.left + rect2.width / 2 - 140;
      if (left2 < 10) left2 = 10;
      if (left2 + 280 > window.innerWidth - 10) left2 = window.innerWidth - 290;
      let top2 = rect2.top - tip.offsetHeight - 12;
      if (top2 < 10) top2 = rect2.bottom + 12;
      tip.style.top = top2 + 'px';
      tip.style.left = left2 + 'px';
      tip.style.opacity = '1';
      tip.style.transform = 'translateY(0)';
      return;
    }

    // Search for content: top-level key OR sector_page logic
    const body = dict[key] || dict.sector_page?.risk_flags?.[key] || key;
    const title = isZh ? '解釋說明' : 'EXPLANATION';

    tip.innerHTML = `<h4 class="text-[10px] font-black uppercase tracking-widest mb-1" style="color:#ef4444">${UI.escapeHTML(title)}</h4><p class="text-[11px] leading-relaxed text-zinc-300">${UI.escapeHTML(body)}</p>`;
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
