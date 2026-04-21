/**
 * page-sector.js — Sector Intelligence page presenter (ARCH-9)
 * Depends on: utils.js (window.UI, window.logToUI), i18n.js, data-store.js (window.DataStore)
 * Requires Chart.js (loaded via CDN in sector.html)
 */

/* ── Constants ──────────────────────────────────────────────── */
const VC = {
    HOT:   { hex: '#22c55e', bg: 'rgba(34,197,94,0.10)',  border: 'rgba(34,197,94,0.30)'  },
    WARM:  { hex: '#eab308', bg: 'rgba(234,179,8,0.10)',  border: 'rgba(234,179,8,0.30)'  },
    COLD:  { hex: '#ef4444', bg: 'rgba(239,68,68,0.10)',  border: 'rgba(239,68,68,0.30)'  },
    AVOID: { hex: '#71717a', bg: 'rgba(113,113,122,0.08)', border: 'rgba(113,113,122,0.25)' },
};
const SECTOR_ZH = {
    UTILITIES:'公用事業', BASIC_MATERIALS:'基礎材料', INDUSTRIALS:'工業',
    TECHNOLOGY:'科技', FINANCIAL:'金融', ENERGY:'能源',
    HEALTHCARE:'醫療保健', CONSUMER_CYCLICAL:'非必需消費', COMMUNICATION_SERVICES:'通訊服務',
    CONSUMER_DEFENSIVE:'必需消費', REAL_ESTATE:'房地產',
};

// Map sector page names (data.json .sectors[].name) → momentum page row.sector
// (GICS sector names from sp500_sectors.json). Used when clicking a sector
// card to deep-link into the momentum table with the sector filter pre-applied.
const SECTOR_TO_GICS = {
    'Industrials':            'Industrials',
    'Financials':             'Financials',
    'Utilities':              'Utilities',
    'Consumer_Discretionary': 'Consumer Discretionary',
    'Technology':             'Information Technology',
    'Materials':              'Materials',
    'Healthcare':             'Health Care',
    'Real_Estate':            'Real Estate',
    'Communication':          'Communication Services',
    'Communication_Services': 'Communication Services',
    'Consumer_Staples':       'Consumer Staples',
    'Energy':                 'Energy',
};
const FLAG_LABELS = {
    zh: {
        overbought:                  '超買',
        binary_risk_within_48h:      '⚡ 48h 二元風險',
        energy_stock_oil_divergence: '⚠ 油價背離',
        pharma_tariff_risk:          '💊 藥品關稅',
        rate_headwind:               '📈 利率逆風',
        late_cycle:                  '🔄 晚期週期',
        fat_tail_warning:            '🔻 肥尾警告',
        extreme_sentiment:           '🚨 極端情緒',
    },
    en: {
        overbought:                  'Overbought',
        binary_risk_within_48h:      '⚡ 48h Binary Risk',
        energy_stock_oil_divergence: '⚠ Oil Divergence',
        pharma_tariff_risk:          '💊 Pharma Tariff',
        rate_headwind:               '📈 Rate Headwind',
        late_cycle:                  '🔄 Late Cycle',
        fat_tail_warning:            '🔻 Fat Tail Warning',
        extreme_sentiment:           '🚨 Extreme Sentiment',
    },
};
// Resolve a flag key to a human label. Looks in (1) local FLAG_LABELS, (2)
// i18n warnings.flags (CamelCase keys like `Below_200MA`), (3) i18n
// sector_page.risk_flags (lowercase keys like `consensus_warning`). Strips
// trailing `_MM_DD` date suffix from dynamic keys like `binary_earnings_4_28`
// so one translation entry covers all dates.
function flagLabel(key) {
    if (!key) return '';
    const lang = UI.currentLang;
    const local = (FLAG_LABELS[lang] || FLAG_LABELS.en)[key];
    if (local) return local;

    const i18nRoot = window.i18n?.[lang] || {};
    const warnFlags = i18nRoot.warnings?.flags || {};
    const sectorRiskFlags = i18nRoot.sector_page?.risk_flags || {};
    if (warnFlags[key]) return warnFlags[key];
    if (sectorRiskFlags[key]) return sectorRiskFlags[key];

    // Dynamic earnings date pattern: binary_earnings_4_28 → binary_earnings + " 4/28"
    const m = key.match(/^([a-z_]+?)_(\d{1,2})_(\d{1,2})$/);
    if (m && sectorRiskFlags[m[1]]) return `${sectorRiskFlags[m[1]]} ${m[2]}/${m[3]}`;
    if (m && warnFlags[m[1]]) return `${warnFlags[m[1]]} ${m[2]}/${m[3]}`;

    return key.replace(/_/g, ' ');
}

/* ── Main loader ─────────────────────────────────────────────── */
async function loadSectorData() {
    logToUI('Sector: loading data...');
    try {
        const data = await DataStore.get();
        const lang = UI.currentLang;

        document.getElementById('last-update').textContent = `SYNCED: ${data.last_updated}`;

        renderStatusStrip(data);
        renderBinaryAlert(data.binary_risks || []);
        renderHandoff(data.market);
        renderSectorMatrix(data.sectors || [], lang);
        renderThreeSignal(data.breadth, data.ftd, data.market_top);
        renderCatalystFeed(data.market);
        renderDivergence(data.divergence_watch || []);
        renderThemes(data.market?.themes || []);

        lucide.createIcons();
        logToUI('Sector: render complete');
    } catch (e) {
        logToUI('Sector ERROR: ' + e.message);
    }
}

/* ── Status Strip ────────────────────────────────────────────── */
function renderStatusStrip(data) {
    const m   = data.market || {};
    const br  = data.breadth || {};
    const ftd = data.ftd    || {};
    const mt  = data.market_top || {};

    const regimeColor = { BULL:'#22c55e', VOLATILE:'#f97316', BEAR:'#ef4444', SIDEWAYS:'#eab308', RISK_OFF:'#ef4444', RISK_ON:'#22c55e' };
    const zoneColor   = { Strong:'#22c55e', Healthy:'#22c55e', Neutral:'#eab308', Weakening:'#f97316', Critical:'#ef4444' };
    const ftdColor    = ftd.state === 'FTD_CONFIRMED' ? '#22c55e' : ftd.state === 'RALLY_ATTEMPT' ? '#eab308' : '#ef4444';
    const fgColor     = (m.fear_greed||50) < 25 ? '#ef4444' : (m.fear_greed||50) < 45 ? '#f97316' : (m.fear_greed||50) < 55 ? '#eab308' : '#22c55e';

    const tr = t();
    const ftdVal = ftd.state === 'FTD_CONFIRMED'
        ? (tr.ftd_confirmed || '✓ Confirmed')
        : (ftd.state?.replace(/_/g,' ') || '--');
    const pills = [
        { id:'pill-regime',   label: tr.pill_regime   || 'Regime',      value: m.regime||'--',                     color: regimeColor[m.regime] || '#eab308' },
        { id:'pill-breadth',  label: tr.pill_breadth  || 'Breadth',     value: (br.score||m.breadth_score||'--'),  color: zoneColor[br.zone] || '#eab308' },
        { id:'pill-ftd',      label: tr.pill_ftd      || 'FTD State',   value: ftdVal,                             color: ftdColor },
        { id:'pill-exposure', label: tr.pill_exposure || 'Exposure Cap',value: m.exposure_ceiling||'--',           color: '#a78bfa' },
        { id:'pill-fg',       label: tr.pill_fg       || 'Fear & Greed',value: `${m.fear_greed||'--'} ${m.fear_greed_label||''}`, color: fgColor },
        { id:'pill-cycle',    label: tr.pill_cycle    || 'Cycle',       value: m.cycle_phase||'--',                color: '#60a5fa' },
        { id:'pill-vix',      label: tr.pill_vix      || 'VIX',         value: data.market_top?.vix_level != null ? Number(data.market_top.vix_level).toFixed(1) : '--', color: '#a78bfa' },
    ];

    pills.forEach(p => {
        const el = document.getElementById(p.id);
        if (!el) return;
        el.innerHTML = `
            <span class="status-pill-label">${p.label}</span>
            <span class="status-pill-value" style="color:${p.color}">${p.value}</span>
        `;
    });

    // Warning flags — clear first so language switches / reloads don't append duplicates
    const flagRow = document.getElementById('warning-flags-row');
    if (flagRow) {
        flagRow.innerHTML = '';
        (m.warning_flags || []).forEach(f => {
            const label = flagLabel(f);
            flagRow.insertAdjacentHTML('beforeend', `
                <div class="text-[8px] font-black px-2 py-1 rounded border bg-yellow-500/8 text-yellow-500 border-yellow-500/20 tracking-tight">${label}</div>
            `);
        });
    }

    // Scan date
    const sd = document.getElementById('scan-date');
    if (sd) sd.textContent = data.last_updated ? `SCAN: ${data.last_updated.split(' ')[0]}` : '';
}

/* ── Binary Alert (minimalist strip) ─────────────────────────── */
function renderBinaryAlert(risks) {
    const urgent = risks.filter(r => r.within_48h);
    const section = document.getElementById('binary-alert-section');
    if (!urgent.length) { section?.classList.add('hidden'); return; }
    section.classList.remove('hidden');
    const tr = t();
    const dateLabel = (r) => {
        if (r.days_until === 0) return tr.binary_today    || 'TODAY';
        if (r.days_until === 1) return tr.binary_tomorrow || 'TOMORROW';
        return r.date || '';
    };
    const container = document.getElementById('binary-alert-items');
    container.innerHTML = urgent.map(r => `
        <div class="flex items-start gap-3">
            <span class="binary-date-pill shrink-0 mt-0.5">${dateLabel(r)}</span>
            <div class="flex-1 min-w-0">
                <div class="text-[12px] font-semibold leading-snug" style="color:var(--text-main)">${r.event}</div>
                ${r.affected_sectors?.length ? `
                <div class="flex flex-wrap gap-1 mt-1.5">
                    ${r.affected_sectors.map(s => `<span class="binary-sector-chip">${s.replace(/_/g,' ')}</span>`).join('')}
                </div>` : ''}
            </div>
        </div>
    `).join('');
}

/* ── Today's Verdict (hero card) — shared component ──────────── */
// Implementation moved to components.js (Components.renderTodayVerdict).
// Keep the legacy `renderHandoff` alias so existing callers still work.
function renderHandoff(market) { Components.renderTodayVerdict(market); }

/* ── Sector Cards ────────────────────────────────────────────── */
function renderSectorMatrix(sectors, lang) {
    const groups = { HOT: [], WARM: [], COLD: [], AVOID: [] };
    sectors.forEach(s => {
        const v = s.verdict || 'COLD';
        if (groups[v]) groups[v].push(s);
    });

    Object.entries(groups).forEach(([verdict, list]) => {
        const groupEl = document.getElementById(`group-${verdict}`);
        const gridEl  = document.getElementById(`grid-${verdict}`);
        const countEl = document.getElementById(`count-${verdict}`);
        if (!groupEl || !gridEl) return;

        if (!list.length) { groupEl.classList.add('hidden'); return; }
        groupEl.classList.remove('hidden');
        countEl.textContent = `${list.length} ${t().sectors_unit || 'sectors'}`;

        list.sort((a, b) => b.score - a.score);
        gridEl.innerHTML = list.map(s => buildSectorCard(s, lang)).join('');

        // Click a sector card → deep-link into momentum page with sector filter pre-applied
        gridEl.querySelectorAll('[data-sector-jump]').forEach(card => {
            card.addEventListener('click', (ev) => {
                // Don't trigger when the user clicks something interactive inside the card
                if (ev.target.closest('button, a, input, select')) return;
                const gics = card.dataset.sectorJump;
                if (gics) window.location.href = `momentum.html?sector=${encodeURIComponent(gics)}`;
            });
        });
    });
}

function buildSectorCard(s, lang) {
    const v      = s.verdict || 'COLD';
    const vc     = VC[v] || VC.COLD;
    const pct    = Math.min(100, s.score || 0);
    const nameZH = SECTOR_ZH[(s.name||'').toUpperCase().replace(/ /g,'_')] || s.name?.replace(/_/g,' ');
    const nameEN = (s.name||'').replace(/_/g,' ');
    const dispName = lang === 'zh' ? nameZH : nameEN;

    const rotIcon  = s.rotation_signal === 'INFLOW' ? '▲' : s.rotation_signal === 'OUTFLOW' ? '▼' : '–';
    const rotColor = s.rotation_signal === 'INFLOW' ? '#22c55e' : s.rotation_signal === 'OUTFLOW' ? '#ef4444' : '#71717a';

    const flags = (s.risk_flags || []).map(f => {
        const lbl = flagLabel(f);
        return `<span class="flag-pill verdict-${v}">${lbl}</span>`;
    }).join('');

    const reasons = (s.key_reasons || (s.key_reason ? [s.key_reason] : [])).slice(0, 2).map(r =>
        `<div class="flex items-start gap-1.5"><span class="text-zinc-500 mt-0.5 shrink-0">▸</span><span class="text-xs leading-snug" style="color:var(--text-muted)">${r}</span></div>`
    ).join('');

    // Score components mini bars
    const sc = s.score_components || {};
    const cT = t();
    const compBars = Object.entries({
        [cT.comp_bm || 'BM']: sc.breadth_momentum,
        [cT.comp_th || 'TH']: sc.theme_heat,
        [cT.comp_nc || 'NC']: sc.news_catalyst,
        [cT.comp_rs || 'RS']: sc.rotation_signal,
    }).map(([k, v_]) => {
        if (v_ == null) return '';
        const w = Math.round((v_ / 25) * 100);
        return `<div class="flex items-center gap-1.5">
            <span class="text-[9px] text-zinc-500 w-5 shrink-0 font-bold">${k}</span>
            <div class="component-bar flex-1 verdict-${s.verdict}" style="height:4px"><div class="component-bar-fill" style="width:${w}%;height:4px"></div></div>
            <span class="text-[9px] font-mono font-bold w-5 text-right" style="color:var(--vc)">${v_}</span>
        </div>`;
    }).filter(Boolean).join('');

    const tr = t();
    const daNote = s.devils_advocate
        ? `<div class="mt-2 pt-2 border-t border-violet-500/20">
            <div class="text-[9px] font-black text-violet-400 mb-1 uppercase tracking-wider">${tr.da_challenge || 'DA Challenge'}</div>
            <p class="text-[10px] text-violet-300/80 leading-snug">${s.devils_advocate}</p>
           </div>`
        : '';

    const uptrendBar = s.uptrend_ratio != null
        ? `<div class="flex items-center gap-1.5 mt-1">
            <span class="text-[10px] text-zinc-500 font-bold shrink-0">${tr.uptrend_label_card || 'Uptrend'}</span>
            <div class="flex-1 h-2 rounded-full" style="background:${vc.border}"><div class="h-2 rounded-full" style="width:${Math.round(s.uptrend_ratio*100)}%;background:${vc.hex}"></div></div>
            <span class="text-[10px] font-mono font-bold shrink-0" style="color:${vc.hex}">${(s.uptrend_ratio*100).toFixed(0)}%</span>
           </div>`
        : '';

    const gicsSector = SECTOR_TO_GICS[s.name] || '';
    const clickAttrs = gicsSector
        ? `data-sector-jump="${gicsSector}" style="cursor:pointer" title="${t().jump_to_momentum || '查看此產業的動能選股結果'}"`
        : '';
    return `
    <div class="sector-card verdict-${v} flex flex-col gap-2" ${clickAttrs}>
        <!-- Header row -->
        <div class="flex items-start justify-between gap-1">
            <div>
                <div class="text-sm font-black tracking-tight" style="color:${vc.hex}">${s.proxy_etf || nameEN}</div>
                <div class="text-[11px] text-zinc-500 leading-tight mt-0.5">${dispName}</div>
            </div>
            <div class="flex flex-col items-end gap-1 shrink-0">
                <span class="text-[9px] font-black px-2 py-0.5 rounded" style="background:${vc.bg};color:${vc.hex};border:1px solid ${vc.border}">${v}</span>
                <span class="text-[10px] font-black" style="color:${rotColor}">${rotIcon} ${s.rotation_signal || ''}</span>
            </div>
        </div>

        <!-- Score ring + uptrend -->
        <div class="flex items-center gap-3">
            <div class="score-ring verdict-${v}" style="--pct:${pct}">
                <div class="score-ring-inner">${s.score}</div>
            </div>
            <div class="flex-1 min-w-0">
                ${uptrendBar}
                ${s.overbought_risk === 'HIGH' ? `<div class="text-[10px] text-orange-400 font-bold mt-1">${t().overbought_label || '⚠ Overbought'}</div>` : ''}
            </div>
        </div>

        <!-- Score components breakdown -->
        ${compBars ? `<div class="space-y-0.5">${compBars}</div>` : ''}

        <!-- Key reasons -->
        ${reasons ? `<div class="space-y-0.5">${reasons}</div>` : ''}

        <!-- Risk flags -->
        ${flags ? `<div class="flex flex-wrap gap-1">${flags}</div>` : ''}

        <!-- DA note -->
        ${daNote}
    </div>`;
}

/* ── Three-Signal Synthesis ──────────────────────────────────── */
function renderThreeSignal(breadth, ftd, marketTop) {
    const container = document.getElementById('three-signal-content');
    if (!container) return;

    // ── Helper: parse "40-55%" → 47.5 (midpoint) ──
    function parseMidpoint(str) {
        if (!str) return null;
        const nums = String(str).replace(/%/g, '').split('-').map(Number).filter(n => !isNaN(n));
        if (nums.length === 2) return (nums[0] + nums[1]) / 2;
        if (nums.length === 1) return nums[0];
        return null;
    }

    // ── Signal data ──
    const bScore  = breadth?.score ?? null;
    const bZone   = breadth?.zone   || '–';
    const bCeil   = breadth?.exposure_ceiling || '–';
    const bPhase  = breadth?.cycle_phase || '–';

    const ftdState = (ftd?.state || 'NO_SIGNAL').replace(/_/g, ' ');
    const ftdQ     = ftd?.quality_score ?? null;
    const ftdExp   = ftd?.exposure_range || '–';

    const mtScore  = marketTop?.composite_score ?? null;
    const mtZone   = marketTop?.zone || '–';
    const mtBudget = marketTop?.risk_budget || '–';

    // ── Color helpers ──
    function zoneColor(zone) {
        if (!zone) return '#71717a';
        const z = zone.toLowerCase();
        if (z.includes('strong') || z.includes('healthy')) return '#22c55e';
        if (z.includes('weak'))   return '#f59e0b';
        if (z.includes('crit'))   return '#ef4444';
        if (z.includes('normal') || z.includes('early')) return '#22c55e';
        if (z.includes('elevat') || z.includes('high'))  return '#f59e0b';
        if (z.includes('top'))    return '#ef4444';
        return '#71717a';
    }
    function ftdColor(state) {
        if (!state) return '#71717a';
        const s = state.toUpperCase();
        if (s.includes('CONFIRMED')) return '#22c55e';
        if (s.includes('WINDOW'))    return '#3b82f6';
        if (s.includes('RALLY'))     return '#f59e0b';
        if (s.includes('INVALIDAT')) return '#ef4444';
        if (s.includes('CORRECTION'))return '#ef4444';
        return '#71717a';
    }

    // ── Synthesized exposure ceiling ──
    const ceilMids = [bCeil, ftdExp, mtBudget].map(parseMidpoint).filter(v => v !== null);
    const synthMid = ceilMids.length ? Math.min(...ceilMids) : null;
    let synthLabel = synthMid !== null ? `${Math.round(synthMid)}%` : '–';

    // Conflict detection: spread > 30pp
    const maxMid   = ceilMids.length ? Math.max(...ceilMids) : null;
    const hasConflict = ceilMids.length >= 2 && maxMid - synthMid > 30;

    // ── Signal rows ──
    function signalRow(icon, label, mainVal, subVal, color, barPct) {
        const pct = Math.min(100, Math.max(0, barPct ?? 0));
        return `
        <div class="rounded-md p-2.5" style="background:color-mix(in srgb,${color},transparent 92%)">
            <div class="flex items-center justify-between mb-1.5">
                <div class="flex items-center gap-1.5">
                    <i data-lucide="${icon}" class="w-3 h-3" style="color:${color}"></i>
                    <span class="text-[9px] font-black uppercase tracking-widest text-zinc-400">${label}</span>
                </div>
                <span class="text-xs font-black" style="color:${color}">${mainVal}</span>
            </div>
            <div class="h-1 rounded-full bg-zinc-700/40 mb-1.5">
                <div class="h-1 rounded-full transition-all" style="width:${pct}%;background:${color}"></div>
            </div>
            <div class="text-[9px] text-zinc-500 truncate">${subVal}</div>
        </div>`;
    }

    const bColor  = zoneColor(bZone);
    const ftdC    = ftdColor(ftd?.state || '');
    const mtColor = zoneColor(mtZone);

    // ── Synthesized exposure badge ──
    const synthColor = synthMid === null ? '#71717a'
        : synthMid >= 75 ? '#22c55e'
        : synthMid >= 50 ? '#f59e0b'
        : '#ef4444';

    const tr = t();
    const conflictBadge = hasConflict ? `
        <div class="flex items-center gap-1 mt-1">
            <i data-lucide="alert-triangle" class="w-3 h-3 text-yellow-400"></i>
            <span class="text-[9px] text-yellow-400">${tr.signal_conflict || 'Signal conflict — use conservative ceiling'}</span>
        </div>` : '';

    container.innerHTML = `
        ${signalRow('activity',       tr.signal_breadth || 'Breadth',    bScore !== null ? `${bScore}` : '–', `${bZone} · ${bPhase} · ${tr.cap_label || 'Cap'} ${bCeil}`, bColor,  bScore)}
        ${signalRow('trending-up',    tr.signal_ftd     || 'FTD',        ftdState,  `${tr.quality_label || 'Quality'} ${ftdQ ?? '–'} · ${tr.exposure_label || 'Exp'} ${ftdExp}`, ftdC, ftdQ)}
        ${signalRow('shield-alert',   tr.signal_top     || 'Market Top', mtScore !== null ? `${mtScore}` : '–', `${mtZone} · ${tr.budget_label || 'Budget'} ${mtBudget}`, mtColor, 100 - (mtScore ?? 50))}

        <div class="rounded-md p-2.5 mt-1" style="background:color-mix(in srgb,${synthColor},transparent 88%);border:1px solid color-mix(in srgb,${synthColor},transparent 70%)">
            <div class="flex items-center justify-between">
                <span class="text-[9px] font-black uppercase tracking-widest text-zinc-400">${tr.synthesized_ceiling || 'Synthesized Ceiling'}</span>
                <span class="text-sm font-black" style="color:${synthColor}">${synthLabel}</span>
            </div>
            <div class="text-[9px] text-zinc-500 mt-0.5">${tr.synth_subtitle || 'min(Breadth, FTD, Top) — most conservative'}</div>
            ${conflictBadge}
        </div>`;

    UI.icons();
}

/* ── Catalyst Feed ───────────────────────────────────────────── */
function renderCatalystFeed(market) {
    if (!market) return;
    const container = document.getElementById('catalyst-feed');
    const items = [];

    // Trump signals
    (market.trump_signals || []).forEach(ts => {
        const bearish = ts.direction === 'bearish';
        const color   = bearish ? '#ef4444' : '#22c55e';
        const icon    = bearish ? '🔻' : '🔺';
        items.push(`
        <div class="trump-signal-card" style="border-left-color:${color};background:color-mix(in srgb,${color},transparent 94%)">
            <div class="flex items-start gap-2">
                <span>${icon}</span>
                <div class="flex-1 min-w-0">
                    <div class="text-[9px] font-black uppercase tracking-wide mb-0.5" style="color:${color}">${ts.keyword?.replace(/_/g,' ').toUpperCase()}</div>
                    <p class="text-[10px] leading-snug" style="color:var(--text-muted)">${ts.headline}</p>
                    <div class="flex flex-wrap gap-1 mt-1">
                        ${(ts.affected_sectors||[]).map(s => `<span class="text-[8px] px-1 rounded" style="background:${color}18;color:${color}">${s.replace(/_/g,' ')}</span>`).join('')}
                    </div>
                </div>
            </div>
        </div>`);
    });

    // Named targets
    if (market.named_targets?.length) {
        const ntLabel = t().named_targets_today || 'Named Targets Today';
        items.push(`
        <div class="px-3 py-2 rounded-lg border border-red-500/25 bg-red-500/6">
            <div class="text-[8px] font-black text-red-400 uppercase tracking-wider mb-1">${ntLabel}</div>
            <div class="flex flex-wrap gap-1.5">
                ${market.named_targets.map(nt => `<span class="text-[9px] font-bold text-red-300 bg-red-500/12 px-2 py-0.5 rounded border border-red-500/20">${nt}</span>`).join('')}
            </div>
        </div>`);
    }

    // Top catalysts (market-moving events over past ~7 days)
    if (market.top_catalysts?.length) {
        const cLabel = t().top_catalysts_title || '主要催化事件';
        items.push(`<div class="text-[8px] font-black text-zinc-500 uppercase tracking-wider pt-2 border-t border-zinc-200 dark:border-zinc-800">${cLabel}</div>`);
        market.top_catalysts.forEach(cat => {
            const dir = cat.direction;
            const color = dir === 'bullish' ? '#22c55e'
                        : dir === 'bearish' ? '#ef4444'
                        : dir === 'binary'  ? '#f97316'
                        :                     '#a1a1aa';
            const icon = dir === 'bullish' ? '🔺'
                       : dir === 'bearish' ? '🔻'
                       : dir === 'binary'  ? '⚡'
                       :                     '·';
            const impact = cat.impact_score ? ` · impact ${cat.impact_score}/5` : '';
            const sectors = (cat.affected_sectors || []).slice(0, 3)
                .map(s => `<span class="text-[8px] px-1 rounded" style="background:${color}18;color:${color}">${s.replace(/_/g,' ')}</span>`).join('');
            items.push(`
            <div class="trump-signal-card" style="border-left-color:${color};background:color-mix(in srgb,${color},transparent 94%)">
                <div class="flex items-start gap-2">
                    <span>${icon}</span>
                    <div class="flex-1 min-w-0">
                        <p class="text-[10px] leading-snug" style="color:var(--text-muted)">${cat.event}</p>
                        <div class="flex flex-wrap gap-1 mt-1 items-center">
                            ${sectors}
                            <span class="text-[8px] text-zinc-500">${cat.timing || ''}${impact}</span>
                        </div>
                    </div>
                </div>
            </div>`);
        });
    }

    container.innerHTML = items.join('') || `<p class="text-[10px] text-zinc-600">${t().no_catalyst || 'No political signals detected.'}</p>`;
}

/* ── Divergence Watch ────────────────────────────────────────── */
function renderDivergence(divs) {
    const container = document.getElementById('divergence-list');
    const tr = t();
    if (!divs.length) {
        container.innerHTML = `<p class="text-[10px] text-zinc-600">${tr.no_divergence || 'No active divergences.'}</p>`;
        return;
    }
    container.innerHTML = divs.map(d => {
        const isRedFlag = d.signal?.includes('positive_price_negative');
        const color     = isRedFlag ? '#ef4444' : '#eab308';
        const actionIcon = d.action === 'reduce_exposure'
            ? (tr.action_reduce || '↓ Reduce Exposure')
            : (tr.action_monitor || '👁 Monitor');
        return `
        <div class="flex items-start gap-3 p-3 rounded-lg border" style="border-color:${color}30;background:${color}08">
            <div class="w-2 h-2 rounded-full mt-1 shrink-0" style="background:${color}"></div>
            <div class="flex-1 min-w-0">
                <div class="flex items-center gap-2 flex-wrap mb-0.5">
                    <span class="text-[10px] font-black" style="color:${color}">${d.sector}</span>
                    <span class="text-[7px] font-bold px-1.5 py-0.5 rounded border" style="color:${color};border-color:${color}40;background:${color}15">${d.signal?.replace(/_/g,' ').toUpperCase()}</span>
                </div>
                <p class="text-[9px] leading-snug" style="color:var(--text-muted)">${d.description}</p>
                <p class="text-[8px] font-bold mt-1" style="color:${color}">${actionIcon}</p>
            </div>
        </div>`;
    }).join('');
}

/* ── Themes ──────────────────────────────────────────────────── */
function renderThemes(themes) {
    const container = document.getElementById('themes-feed');
    if (!themes.length) { container.innerHTML = `<p class="text-[10px] text-zinc-600">${t().no_themes || 'No active themes.'}</p>`; return; }
    container.innerHTML = themes.map((t, i) => `
        <div class="flex items-start gap-2 p-2.5 rounded-lg bg-violet-500/5 border border-violet-500/15">
            <span class="text-[9px] font-black text-violet-500 shrink-0">${String(i+1).padStart(2,'0')}</span>
            <span class="text-[10px] font-medium leading-snug" style="color:var(--text-muted)">${t.replace(/_/g,' ')}</span>
        </div>`).join('');
}

/* ── Bootstrap ───────────────────────────────────────────────── */
function t() { return (window.i18n?.[UI.currentLang]?.sector_page) || {}; }

function applyTranslations() {
    const tr = t();
    const set = (id, val) => { const el = document.getElementById(id); if (el && val != null) el.textContent = val; };
    // Header: Chinese title + English subtitle (matches decisions.html pattern)
    if (UI.currentLang === 'zh') {
        set('sector-title',    '產業掃描');
        set('sector-subtitle', 'Sector Intelligence');
    } else {
        set('sector-title',    'Sector Intelligence');
        set('sector-subtitle', '產業掃描');
    }
    // Refresh button: short label to match other pages ("更新" / "Refresh")
    set('refresh-sector-label', UI.currentLang === 'zh' ? '更新' : 'Refresh');
    set('binary-alert-title',   tr.binary_alert);
    set('handoff-title',        tr.handoff_title);
    set('tv-takeaways-title',   tr.tv_takeaways_title);
    set('tv-actions-title',     tr.tv_actions_title);
    set('tv-watch-title',       tr.tv_watch_title);
    set('tv-fallback-title',    tr.handoff_title);
    set('three-signal-title',   tr.three_signal_title);
    set('catalyst-title',       tr.catalyst_title);
    set('divergence-title',     tr.divergence_title);
    set('themes-title',         tr.themes_title);
}

/* ── Reverse-call: trigger Claude to run sector scan ─────────── */
let _scanPollTimer = null;

function formatElapsed(sec) {
    const m = Math.floor(sec / 60); const s = sec % 60;
    return `${String(m).padStart(2,'0')}:${String(s).padStart(2,'0')}`;
}

const STATUS_STYLES = {
    running:   { bg: 'rgba(234,179,8,0.12)',  border: 'rgba(234,179,8,0.35)',  text: '#facc15', icon: 'zap' },
    done:      { bg: 'rgba(34,197,94,0.12)',  border: 'rgba(34,197,94,0.35)',  text: '#4ade80', icon: 'check-circle' },
    error:     { bg: 'rgba(239,68,68,0.12)',  border: 'rgba(239,68,68,0.35)',  text: '#f87171', icon: 'x-circle' },
    cancelled: { bg: 'rgba(113,113,122,0.15)',border: 'rgba(113,113,122,0.35)',text: '#a1a1aa', icon: 'minus-circle' },
};

function showScanBanner() {
    const b = document.getElementById('scan-banner');
    if (b) b.classList.remove('hidden');
}
function hideScanBanner() {
    document.getElementById('scan-banner')?.classList.add('hidden');
    document.getElementById('scan-banner-panel')?.classList.add('hidden');
    if (_scanPollTimer) { clearInterval(_scanPollTimer); _scanPollTimer = null; }
}
function setBannerStatus(status) {
    const card = document.getElementById('scan-banner');      // outer glass-card
    const st   = document.getElementById('scan-banner-status'); // status tag inside header row
    const sty  = STATUS_STYLES[status] || STATUS_STYLES.running;
    // Color the card's left border via CSS variable — both the solid 6px band
    // and the inset glow read from --scan-accent. Unified across momentum / sector / news.
    if (card) card.style.setProperty('--scan-accent', sty.text);
    const pulse = document.getElementById('scan-banner-pulse');
    if (pulse) {
        pulse.style.background = sty.text;
        // Stop the pulse in terminal states — steady dot reads as "not working anymore"
        pulse.classList.toggle('animate-pulse', status === 'running');
    }
    if (st) {
        const tr = t();
        const labelMap = {
            running:   tr.scan_running   || 'RUNNING',
            done:      tr.scan_done      || 'DONE',
            error:     tr.scan_error     || 'ERROR',
            cancelled: tr.scan_cancelled || 'CANCELLED',
        };
        st.textContent = labelMap[status] || status.toUpperCase();
        st.style.color      = sty.text;
        st.style.background = sty.bg;
    }
    // Cancel only while running; Dismiss for everything else
    document.getElementById('scan-cancel-btn')?.classList.toggle('hidden', status !== 'running');
    document.getElementById('scan-dismiss-btn')?.classList.toggle('hidden', status === 'running');
}

function renderScanEvents(events) {
    const pre = document.getElementById('scan-events');
    if (!pre) return;
    if (!events || !events.length) {
        pre.textContent = '(waiting for first event...)';
        return;
    }
    const wasBottom = pre.scrollTop + pre.clientHeight >= pre.scrollHeight - 10;
    pre.textContent = events.map(ev => `${ev.icon || '·'} ${ev.text || ''}`).join('\n');
    if (wasBottom) pre.scrollTop = pre.scrollHeight;
    // Banner latest = last event
    const latest = document.getElementById('scan-banner-latest');
    const last = events[events.length - 1];
    if (latest && last) {
        latest.textContent = `${last.icon} ${last.text}`;
        latest.title = last.text;
    }
}

async function pollScanStatus() {
    try {
        const res = await fetch('/api/run-protocol/status');
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const s = await res.json();
        setBannerStatus(s.status);
        document.getElementById('scan-banner-elapsed').textContent = formatElapsed(s.elapsed_sec || 0);
        renderScanEvents(s.events || []);
        if (s.status !== 'running') {
            if (_scanPollTimer) { clearInterval(_scanPollTimer); _scanPollTimer = null; }
            if (s.status === 'error' || s.status === 'cancelled') {
                const err = document.getElementById('scan-error');
                if (err) { err.textContent = s.error || s.status; err.classList.remove('hidden'); }
            }
            if (s.status === 'done') {
                // Wait for bridge.py (kicked off async after scan) then refresh page data
                setTimeout(() => loadSectorData(), 3000);
                // Banner stays up — user dismisses via the ✕ (#scan-dismiss-btn) button.
            }
        }
    } catch (e) {
        logToUI('scan poll error: ' + e.message, 'error');
    }
}

async function triggerSectorScan() {
    const tr = t();
    const confirmMsg = tr.scan_confirm || 'Run full sector scan via Claude? (~3-5 min, consumes tokens)';
    if (!confirm(confirmMsg)) return;
    showScanBanner();
    setBannerStatus('running');
    document.getElementById('scan-banner-elapsed').textContent = '00:00';
    document.getElementById('scan-banner-latest').textContent = '(starting...)';
    renderScanEvents([]);
    document.getElementById('scan-error')?.classList.add('hidden');
    try {
        const res = await fetch('/api/run-protocol', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name: 'sector' }),
        });
        if (!res.ok) {
            const err = await res.json().catch(() => ({ error: res.statusText }));
            throw new Error(err.error || `HTTP ${res.status}`);
        }
        _scanPollTimer = setInterval(pollScanStatus, 2000);
        pollScanStatus();
    } catch (e) {
        const errEl = document.getElementById('scan-error');
        if (errEl) {
            errEl.textContent = `${tr.scan_start_failed || 'failed to start'}: ${e.message}`;
            errEl.classList.remove('hidden');
        }
        setBannerStatus('error');
    }
}

async function cancelSectorScan() {
    try { await fetch('/api/run-protocol/cancel', { method: 'POST' }); }
    catch (e) { logToUI('cancel error: ' + e.message, 'error'); }
}

function toggleScanPanel() {
    const panel = document.getElementById('scan-banner-panel');
    const btn   = document.getElementById('scan-expand-btn');
    if (!panel) return;
    const open = panel.classList.toggle('hidden') === false;
    if (btn) {
        const tr = t();
        btn.textContent = open ? (tr.scan_minimize || '收合') : (tr.scan_expand || '展開');
    }
    if (open) {
        const pre = document.getElementById('scan-events');
        if (pre) pre.scrollTop = pre.scrollHeight;
    }
}

document.getElementById('refresh-sector').addEventListener('click', triggerSectorScan);
document.getElementById('scan-cancel-btn')?.addEventListener('click', cancelSectorScan);
document.getElementById('scan-dismiss-btn')?.addEventListener('click', hideScanBanner);
document.getElementById('scan-expand-btn')?.addEventListener('click', toggleScanPanel);

// Resume banner on page load if a scan is already running
(async () => {
    try {
        const r = await fetch('/api/run-protocol/status');
        const s = await r.json();
        if (s.status === 'running') {
            showScanBanner();
            setBannerStatus('running');
            _scanPollTimer = setInterval(pollScanStatus, 2000);
            pollScanStatus();
        }
    } catch (e) { /* ignore */ }
})();
UI.boot('sector', {
    translate: applyTranslations,
    reload: loadSectorData,
    onThemeChange: () => loadSectorData(),
});
loadSectorData();
