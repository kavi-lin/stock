/**
 * page-momentum.js — Momentum Screener page presenter
 * Depends on: utils.js (window.UI), i18n.js, data-store.js, Chart.js
 */

const t = () => (window.i18n?.[UI.currentLang]?.momentum) || {};

// Translation helpers — fall back to human-readable English if key is missing
// from the map so new signals don't render as blank.
function sigLabel(key) {
    return t().signals_map?.[key] || key.replace(/_/g, ' ');
}
function warnLabel(key) {
    return t().warnings_map?.[key] || key.replace(/_/g, ' ');
}
function stageLabel(key) {
    return t().stages_map?.[key] || key || '—';
}
function labelText(key) {
    return t().labels_map?.[key] || key || '—';
}

// Signal / warning chip lists — shown in the filter panel. Order matters (most useful first).
const FILTER_SIGNALS = [
    'stage2_uptrend_intact',
    'volume_expansion',
    'fresh_golden_cross_20_50',
    'fresh_golden_cross_50_200',
    'heavy_volume_spike_today',
    'squeeze_candidate',
    'oversold_rsi',
    'low_short_interest',
    'high_short_interest',
];
const FILTER_WARNINGS = [
    'overbought_rsi',
    'parabolic_blowoff_risk',
    'stage4_downtrend',
    'volume_dry_up',
    'fresh_death_cross_20_50',
    'fresh_death_cross_50_200',
];

function defaultFilter() {
    return {
        minScore: 50,
        maxScore: null,
        minRsi:   null,
        maxRsi:   null,
        stage:    'any',
        sector:   'any',
        requiredSignals:   new Set(),
        excludedWarnings:  new Set(),
        search:   '',
    };
}

// GICS sector list matching sp500_sectors.json values — used for dropdown translation
const SECTOR_KEYS = [
    'Information Technology', 'Financials', 'Health Care',
    'Consumer Discretionary', 'Communication Services', 'Industrials',
    'Consumer Staples', 'Energy', 'Utilities', 'Real Estate', 'Materials',
];

function sectorLabel(key) {
    return t().sectors_map?.[key] || key;
}

// Preset strategies — classic filter combos with a known rationale. Order matters
// (rendered left-to-right). Each applies atomically (overwrites current filter).
const PRESETS = {
    breakout: {   // 🔥 fresh 20/50 golden cross + volume confirmation on Stage 2 name
        filter: {
            minScore: 0, maxScore: null, minRsi: null, maxRsi: null,
            stage: 'Stage 2 uptrend', sector: 'any',
            requiredSignals:  ['fresh_golden_cross_20_50', 'volume_expansion'],
            excludedWarnings: ['overbought_rsi'],
            search: '',
        },
    },
    uptrend: {    // 💪 established trend, score ≥65, not overextended
        filter: {
            minScore: 65, maxScore: null, minRsi: null, maxRsi: null,
            stage: 'Stage 2 uptrend', sector: 'any',
            requiredSignals:  [],
            excludedWarnings: ['overbought_rsi', 'parabolic_blowoff_risk'],
            search: '',
        },
    },
    pullback: {   // 📉 oversold RSI in a still-uptrending stock
        filter: {
            minScore: 45, maxScore: null, minRsi: null, maxRsi: null,
            stage: 'Stage 2 uptrend', sector: 'any',
            requiredSignals:  ['oversold_rsi'],
            excludedWarnings: [],
            search: '',
        },
    },
    squeeze: {    // ⚡ short-squeeze candidates (high short + positive momentum)
        filter: {
            minScore: 0, maxScore: null, minRsi: null, maxRsi: null,
            stage: 'any', sector: 'any',
            requiredSignals:  ['squeeze_candidate'],
            excludedWarnings: [],
            search: '',
        },
    },
    safe: {       // 🎯 score ≥60, no overbought / parabolic — conservative quality
        filter: {
            minScore: 60, maxScore: null, minRsi: null, maxRsi: null,
            stage: 'any', sector: 'any',
            requiredSignals:  [],
            excludedWarnings: ['overbought_rsi', 'parabolic_blowoff_risk'],
            search: '',
        },
    },
    all: {        // 📊 reset — see everything
        filter: null,  // resolved to defaultFilter() on apply
    },
};

function applyPreset(key) {
    const p = PRESETS[key];
    if (!p) return;
    if (p.filter === null) {
        _state.filter = defaultFilter();
    } else {
        _state.filter = {
            ...p.filter,
            requiredSignals:  new Set(p.filter.requiredSignals),
            excludedWarnings: new Set(p.filter.excludedWarnings),
        };
    }
    renderFilterPanel();
    renderTable();
}

let _state = {
    rows: [],
    filter: defaultFilter(),
    sort: { field: 'score', dir: 'desc' },  // default: highest score first
    history: {},
    journalStats: null,
    historyChart: null,
};

// Stage ordering for sort: most bullish → most bearish.
// Used when sorting by "stage" column.
const STAGE_ORDER = {
    'Stage 2 uptrend':   4,
    'Stage 1 basing':    3,
    'Stage 3 top':       2,
    'Stage 4 downtrend': 1,
    'unknown':           0,
};

function _sortKey(r, field) {
    if (field === 'stage') return STAGE_ORDER[r.stage] ?? -1;
    const v = r[field];
    // Nulls sort last regardless of direction
    if (v == null) return null;
    return v;
}

function _compareRows(a, b, field, dir) {
    const va = _sortKey(a, field);
    const vb = _sortKey(b, field);
    if (va == null && vb == null) return 0;
    if (va == null) return 1;   // nulls always last
    if (vb == null) return -1;
    const c = va < vb ? -1 : va > vb ? 1 : 0;
    return dir === 'desc' ? -c : c;
}

/* ── Init ─────────────────────────────────────────────────────── */
async function loadMomentumData() {
    UI.logToUI('Momentum: loading data...');
    try {
        const data = await DataStore.get();
        document.getElementById('last-update').textContent = `SYNCED: ${data.last_updated}`;

        const ms = data.momentum_screen || { status: 'no_data' };
        if (ms.status !== 'success' || !ms.rows || ms.rows.length === 0) {
            showEmptyState();
            return;
        }

        _state.rows = ms.rows;
        _state.history = ms.history_by_ticker || {};
        _state.journalStats = ms.journal?.stats || null;

        document.getElementById('no-data-banner').classList.add('hidden');
        document.getElementById('meta-strip').classList.remove('hidden');
        document.getElementById('filter-bar').classList.remove('hidden');
        document.getElementById('table-wrap').classList.remove('hidden');
        document.getElementById('journal-section').classList.remove('hidden');

        renderMeta(ms);
        renderFilterPanel();
        renderTable();
        renderJournalStats(ms.journal);

        UI.icons();
    } catch (e) {
        UI.logToUI('Momentum load error: ' + e.message, 'error');
        console.error('[momentum] load error:', e);
    }
}

function showEmptyState() {
    document.getElementById('no-data-banner').classList.remove('hidden');
    document.getElementById('meta-strip').classList.add('hidden');
    document.getElementById('filter-bar').classList.add('hidden');
    document.getElementById('table-wrap').classList.add('hidden');
    document.getElementById('journal-section').classList.add('hidden');
    document.getElementById('no-data-text').textContent = t().no_data || '尚未有掃描結果';
    document.getElementById('snap-id').textContent = '';
    UI.icons();
}

/* ── Meta strip ────────────────────────────────────────────────── */
function renderMeta(ms) {
    const tr = t();
    document.getElementById('snap-id').textContent = ms.snap_id || '';

    document.getElementById('meta-time-label').textContent   = tr.snapshot_time || 'Scanned';
    document.getElementById('meta-time').textContent         = ms.generated_at || '—';
    document.getElementById('meta-time-sub').textContent     = ms.freshness
        ? `${ms.freshness}  ·  ${ms.age_label}` : '';

    document.getElementById('meta-matched-label').textContent = tr.total_matched || 'Matched';
    document.getElementById('meta-matched').textContent       = ms.total_rows ?? '—';
    document.getElementById('meta-matched-sub').textContent   = ms.snap_date || '';

    document.getElementById('meta-journal-label').textContent = tr.journal_total || 'Journal entries';
    document.getElementById('meta-journal').textContent       = ms.journal?.total_entries ?? 0;
    const stats = ms.journal?.stats;
    document.getElementById('meta-journal-sub').textContent   = stats
        ? `5d:${stats.fill_counts?.['5d'] || 0} · 20d:${stats.fill_counts?.['20d'] || 0} · 60d:${stats.fill_counts?.['60d'] || 0}`
        : '';

    document.getElementById('meta-snaps-label').textContent = tr.snapshot_count || 'Snapshots';
    document.getElementById('meta-snaps').textContent       = ms.snapshot_count ?? '—';
    document.getElementById('meta-snaps-sub').textContent   = stats
        ? `${stats.date_range?.earliest || ''} → ${stats.date_range?.latest || ''}` : '';
}

/* ── Filter panel ─────────────────────────────────────────────── */
function renderSignalChips() {
    const wrap = document.getElementById('f-signal-chips');
    wrap.innerHTML = FILTER_SIGNALS.map(sig => {
        const active = _state.filter.requiredSignals.has(sig);
        return `<span class="filter-chip${active ? ' active' : ''}" data-sig="${sig}" title="${sig}">${sigLabel(sig)}</span>`;
    }).join('');
    wrap.querySelectorAll('[data-sig]').forEach(el => {
        el.onclick = () => {
            const k = el.dataset.sig;
            const s = _state.filter.requiredSignals;
            if (s.has(k)) s.delete(k); else s.add(k);
            renderSignalChips();
            renderTable();
        };
    });
}

function renderWarningChips() {
    const wrap = document.getElementById('f-warning-chips');
    wrap.innerHTML = FILTER_WARNINGS.map(w => {
        const active = _state.filter.excludedWarnings.has(w);
        return `<span class="filter-chip warn${active ? ' active' : ''}" data-warn="${w}" title="${w}">${warnLabel(w)}</span>`;
    }).join('');
    wrap.querySelectorAll('[data-warn]').forEach(el => {
        el.onclick = () => {
            const k = el.dataset.warn;
            const s = _state.filter.excludedWarnings;
            if (s.has(k)) s.delete(k); else s.add(k);
            renderWarningChips();
            renderTable();
        };
    });
}

function renderPresetRow() {
    const wrap = document.getElementById('f-presets');
    if (!wrap) return;
    const tr = t();
    wrap.innerHTML = Object.keys(PRESETS).map(key => {
        const entry = tr['preset_' + key] || {};
        const label = entry.label || key;
        const tip   = entry.tip   || '';
        return `<button class="preset-btn" data-preset="${key}" title="${tip}">${label}</button>`;
    }).join('');
    wrap.querySelectorAll('[data-preset]').forEach(el => {
        el.addEventListener('click', () => applyPreset(el.dataset.preset));
    });
}

function renderFilterPanel() {
    // Populate controls from state (called once after load + after preset apply + after reset)
    document.getElementById('f-min-score').value = _state.filter.minScore;
    document.getElementById('filter-score-val').textContent = `≥ ${_state.filter.minScore}`;
    document.getElementById('f-min-rsi').value = _state.filter.minRsi ?? '';
    document.getElementById('f-max-rsi').value = _state.filter.maxRsi ?? '';
    document.getElementById('f-stage').value = _state.filter.stage;
    document.getElementById('f-sector').value = _state.filter.sector;
    document.getElementById('search-ticker').value = _state.filter.search;
    renderPresetRow();
    renderSignalChips();
    renderWarningChips();
    UI.icons();
}

/* ── Matcher + table render ───────────────────────────────────── */
function matchesFilter(r) {
    const f = _state.filter;
    if (r.score == null || r.score < f.minScore) return false;
    if (f.maxScore != null && r.score > f.maxScore) return false;
    if (f.minRsi != null && (r.rsi_14 == null || r.rsi_14 < f.minRsi)) return false;
    if (f.maxRsi != null && (r.rsi_14 == null || r.rsi_14 > f.maxRsi)) return false;
    if (f.stage !== 'any' && r.stage !== f.stage) return false;
    if (f.sector !== 'any' && r.sector !== f.sector) return false;
    const sigs = new Set(r.signals || []);
    for (const s of f.requiredSignals) if (!sigs.has(s)) return false;
    const warns = new Set(r.warnings || []);
    for (const w of f.excludedWarnings) if (warns.has(w)) return false;
    if (f.search && !(r.ticker || '').toUpperCase().includes(f.search.toUpperCase())) return false;
    return true;
}

function renderTable() {
    const tbody = document.getElementById('mom-tbody');
    const visible = _state.rows.filter(matchesFilter);

    // Sort according to current _state.sort
    const { field, dir } = _state.sort;
    visible.sort((a, b) => _compareRows(a, b, field, dir));

    // Re-rank within the visible set so # reflects the current filter view
    const ranked = visible.map((r, i) => ({ ...r, rank: i + 1 }));
    tbody.innerHTML = ranked.map(rowHTML).join('') || emptyRow();

    // Paint sort indicators on headers
    _updateSortHeaders();

    const countTxt = `${visible.length} / ${_state.rows.length}`;
    document.getElementById('table-count').textContent = countTxt;
    const matchEl = document.getElementById('filter-match-count');
    if (matchEl) matchEl.textContent = countTxt;

    tbody.querySelectorAll('.mom-row').forEach(tr => {
        tr.addEventListener('click', () => openHistory(tr.dataset.ticker));
    });
    // Volume cell click → intercept before row handler fires
    tbody.querySelectorAll('.vol-cell').forEach(td => {
        td.addEventListener('click', e => {
            e.stopPropagation();
            const r = _state.rows.find(x => x.ticker === td.dataset.tickerVol);
            if (r) openVolumePopup(r);
        });
    });
    // Stage cell click
    tbody.querySelectorAll('.stage-cell').forEach(td => {
        td.addEventListener('click', e => {
            e.stopPropagation();
            const r = _state.rows.find(x => x.ticker === td.dataset.tickerStage);
            if (r) openStagePopup(r);
        });
    });
    // RSI cell click
    tbody.querySelectorAll('.rsi-cell').forEach(td => {
        td.addEventListener('click', e => {
            e.stopPropagation();
            const r = _state.rows.find(x => x.ticker === td.dataset.tickerRsi);
            if (r) openRsiPopup(r);
        });
    });
}

/* Score battery: 10 cells, tier colors, partial cell via gradient.
   Cells 1-3 red (0-30), 4-5 yellow (30-50), 6-7 green (50-70), 8-10 blue (70-100). */
const BATTERY_COLORS = [
    '#ef4444', '#ef4444', '#ef4444',                          // 1-3 red
    '#eab308', '#eab308',                                      // 4-5 yellow
    '#22c55e', '#22c55e',                                      // 6-7 green
    '#3b82f6', '#3b82f6', '#3b82f6',                          // 8-10 blue
];
const BATTERY_UNFILLED = 'rgba(161,161,170,0.15)';

function scoreBatteryHTML(score) {
    if (score == null) return '<span class="text-zinc-600">—</span>';
    const clamped = Math.max(0, Math.min(100, score));
    const filled = clamped / 10;              // e.g. 6.25
    const fullCells = Math.floor(filled);     // 6
    const partial = filled - fullCells;       // 0.25

    const cells = Array.from({ length: 10 }, (_, i) => {
        const color = BATTERY_COLORS[i];
        let bg;
        if (i < fullCells) {
            bg = color;
        } else if (i === fullCells && partial > 0) {
            const pct = Math.round(partial * 100);
            bg = `linear-gradient(to right, ${color} ${pct}%, ${BATTERY_UNFILLED} ${pct}%)`;
        } else {
            bg = BATTERY_UNFILLED;
        }
        return `<span class="cell" style="background:${bg}"></span>`;
    }).join('');

    // Numeric label colored by highest-filled tier
    const tierColor = fullCells >= 7 ? '#3b82f6'
                    : fullCells >= 5 ? '#22c55e'
                    : fullCells >= 3 ? '#eab308'
                    : '#ef4444';
    const n = score.toFixed(1);

    return `<div class="flex items-center gap-2 justify-end">
        <div class="score-battery">${cells}</div>
        <span class="score-num" style="color:${tierColor}">${n}</span>
    </div>`;
}

// RSI cell: number with tier-based color.
// >70 red (overbought), 50-70 green (bullish), 30-50 yellow (neutral), <30 blue (oversold)
function rsiCell(v) {
    if (v == null) return '<span class="text-zinc-600 text-xs">—</span>';
    const color = v >= 70 ? '#ef4444'
                : v >= 50 ? '#22c55e'
                : v >= 30 ? '#eab308'
                : '#3b82f6';
    return `<span class="font-mono text-xs font-bold" style="color:${color};text-decoration:underline dotted rgba(161,161,170,0.4)">${v.toFixed(0)}</span>`;
}

// Volume ratio color tier — mirrors popup logic
//   ≥3.0 red (HEAVY_SPIKE) · ≥2.0 yellow (MILD_SPIKE) · ≥1.3 green (expansion)
//   ≥0.7 neutral · <0.7 orange (drying up)
function _ratioColor(r) {
    if (r == null) return '#71717a';
    if (r >= 3.0) return '#ef4444';
    if (r >= 2.0) return '#eab308';
    if (r >= 1.3) return '#22c55e';
    if (r <  0.7) return '#fbbf24';
    return '#a1a1aa';
}

function rowHTML(r) {
    const above200 = r.above_ma200_pct;
    const above200Txt = above200 == null ? '—'
                       : `${above200 >= 0 ? '+' : ''}${above200.toFixed(1)}%`;
    const above200Color = above200 == null ? 'color:#71717a'
                         : above200 >= 0 ? 'color:#86efac' : 'color:#fca5a5';

    const sigHTML = (r.signals || []).slice(0, 4)
        .map(s => `<span class="signal-pill" title="${s}">${sigLabel(s)}</span>`).join('')
      + (r.warnings || []).slice(0, 2)
        .map(w => `<span class="warning-pill" title="${w}">${warnLabel(w)}</span>`).join('');

    const shortTxt = r.short_pct_float == null ? '—'
                    : `${r.short_pct_float.toFixed(1)}%`;
    const shortColor = r.short_interpretation === 'very_high'     ? '#ef4444'
                     : r.short_interpretation === 'high'          ? '#fbbf24'
                     : r.short_interpretation === 'low'           ? '#71717a'
                     : '#a1a1aa';

    const sectorTxt = r.sector && r.sector !== 'Unknown'
        ? `<div class="text-[9px] text-zinc-500 font-normal leading-none mt-0.5">${sectorLabel(r.sector)}</div>`
        : '';
    return `<tr class="mom-row" data-ticker="${r.ticker}">
        <td class="text-zinc-500 font-mono text-xs">${r.rank ?? '—'}</td>
        <td><div class="font-bold">${r.ticker}</div>${sectorTxt}</td>
        <td class="text-right font-mono">$${r.price != null ? r.price.toFixed(2) : '—'}</td>
        <td class="text-right score-cell">${scoreBatteryHTML(r.score)}</td>
        <td><span class="mlabel label-${r.label || 'NEUTRAL'}" title="${r.label || ''}">${labelText(r.label)}</span></td>
        <td class="text-xs text-zinc-400 stage-cell" data-ticker-stage="${r.ticker}" style="cursor:pointer;text-decoration:underline dotted rgba(161,161,170,0.4)" title="${r.stage || ''}">${stageLabel(r.stage)}</td>
        <td class="text-right font-mono text-xs vol-cell" data-ticker-vol="${r.ticker}" style="cursor:pointer;text-decoration:underline dotted rgba(161,161,170,0.4);color:${_ratioColor(r.ratio_20d)};font-weight:700">${r.ratio_20d != null ? r.ratio_20d.toFixed(2) + '×' : '—'}</td>
        <td class="text-right font-mono text-xs" style="${above200Color}">${above200Txt}</td>
        <td class="text-right rsi-cell" data-ticker-rsi="${r.ticker}" style="cursor:pointer">${rsiCell(r.rsi_14)}</td>
        <td>${sigHTML || '<span class="text-zinc-600 text-xs">—</span>'}</td>
        <td class="text-xs" style="color:${shortColor}">${shortTxt}</td>
    </tr>`;
}

function emptyRow() {
    return `<tr><td colspan="11" class="text-center text-zinc-500 py-8 text-xs">
        ${t().no_data || 'No matches'}</td></tr>`;
}

function _updateSortHeaders() {
    document.querySelectorAll('.mom-th.sortable').forEach(th => {
        const field = th.dataset.sort;
        const arrow = th.querySelector('.sort-arrow');
        if (!arrow) return;
        if (_state.sort.field === field) {
            th.classList.add('active-sort');
            arrow.textContent = _state.sort.dir === 'desc' ? '▼' : '▲';
        } else {
            th.classList.remove('active-sort');
            arrow.textContent = '▼';  // inactive indicator (dimmed)
        }
    });
}

function _bindSortHeaders() {
    document.querySelectorAll('.mom-th.sortable').forEach(th => {
        th.addEventListener('click', () => {
            const field = th.dataset.sort;
            if (_state.sort.field === field) {
                // Same column → toggle direction
                _state.sort.dir = _state.sort.dir === 'desc' ? 'asc' : 'desc';
            } else {
                // New column → default desc (highest first is usually what you want)
                _state.sort.field = field;
                _state.sort.dir = 'desc';
            }
            renderTable();
        });
    });
}

/* ── RSI-14 popup (macaron blood bar) ────────────────────────── */
// Pastel palette for the four zones (Tailwind 300-400 shades feel macaron).
const RSI_PALETTE = {
    oversold:   '#93c5fd',   // soft sky blue
    neutral:    '#fcd34d',   // butter yellow
    bullish:    '#86efac',   // mint green
    overbought: '#fca5a5',   // pink coral
};

function _rsiZoneKey(v) {
    if (v == null) return null;
    if (v < 30) return 'oversold';
    if (v < 50) return 'neutral';
    if (v < 70) return 'bullish';
    return 'overbought';
}

function openRsiPopup(r) {
    const tr = t();
    const v = r.rsi_14;
    document.getElementById('rsi-modal-title').textContent =
        `${r.ticker} — ${tr.rsi_modal_title || 'RSI-14 分析'}`;

    if (v == null) {
        document.getElementById('rsi-modal-body').innerHTML =
            `<div class="text-zinc-500">${tr.rsi_msg_unknown || 'RSI 無法判定（資料不足）。'}</div>`;
        document.getElementById('rsi-modal').classList.remove('hidden');
        UI.icons();
        return;
    }

    const zoneKey = _rsiZoneKey(v);
    const zoneLabel = {
        oversold:   tr.rsi_bar_oversold   || '超賣',
        neutral:    tr.rsi_bar_neutral    || '偏弱',
        bullish:    tr.rsi_bar_bullish    || '健康',
        overbought: tr.rsi_bar_overbought || '超買',
    }[zoneKey];
    const zoneTag = {
        oversold:   'OVERSOLD',
        neutral:    'NEUTRAL',
        bullish:    'BULLISH',
        overbought: 'OVERBOUGHT',
    }[zoneKey];

    // Personalised message, with {rsi} substitution
    const msgKey = `rsi_msg_${zoneKey}`;
    const msgTpl = tr[msgKey] || '';
    const personalMsg = msgTpl.replace(/\{rsi\}/g, v.toFixed(1));

    // Pointer label — number sits above a triangle and a vertical line
    // dropping through the bar at the exact RSI%.
    const pct = Math.max(0, Math.min(100, v));

    document.getElementById('rsi-modal-body').innerHTML = `
      <!-- Header: current value + zone tag -->
      <div class="flex items-baseline gap-3">
        <span class="text-[10px] font-black uppercase tracking-widest text-zinc-500">${tr.rsi_zone_title || '目前 RSI-14'}</span>
        <span class="font-mono font-black" style="font-size:22px;color:${RSI_PALETTE[zoneKey]}">${v.toFixed(1)}</span>
        <span class="text-[10px] font-black uppercase tracking-widest" style="color:${RSI_PALETTE[zoneKey]}">${zoneTag} · ${zoneLabel}</span>
      </div>

      <!-- Blood bar with pointer -->
      <div class="rsi-bar-wrap">
        <div class="rsi-pointer" style="left:${pct}%">
          <div class="rsi-pointer-num">${v.toFixed(1)}</div>
          <div class="rsi-pointer-tri">▼</div>
        </div>
        <div class="rsi-bar">
          <div class="rsi-zone" style="width:30%;background:${RSI_PALETTE.oversold}">${tr.rsi_bar_oversold || '超賣'}</div>
          <div class="rsi-zone" style="width:20%;background:${RSI_PALETTE.neutral}">${tr.rsi_bar_neutral || '偏弱'}</div>
          <div class="rsi-zone" style="width:20%;background:${RSI_PALETTE.bullish}">${tr.rsi_bar_bullish || '健康'}</div>
          <div class="rsi-zone" style="width:30%;background:${RSI_PALETTE.overbought}">${tr.rsi_bar_overbought || '超買'}</div>
        </div>
        <div class="rsi-pointer-line" style="left:${pct}%"></div>
        <div class="rsi-ticks">
          <span class="rsi-tick" style="left:0%">0</span>
          <span class="rsi-tick" style="left:30%">30</span>
          <span class="rsi-tick" style="left:50%">50</span>
          <span class="rsi-tick" style="left:70%">70</span>
          <span class="rsi-tick" style="left:100%">100</span>
        </div>
      </div>

      <!-- Zone legend -->
      <div>
        <div class="text-[10px] font-black uppercase tracking-widest text-zinc-500 mb-2">
          ${tr.rsi_zones_title || '分區意義'}
        </div>
        <div class="space-y-1.5 text-[11px] leading-snug">
          <div><span class="inline-block w-3 h-3 rounded-sm align-middle mr-2" style="background:${RSI_PALETTE.oversold}"></span>${tr.rsi_zone_0_30   || '0-30 超賣'}</div>
          <div><span class="inline-block w-3 h-3 rounded-sm align-middle mr-2" style="background:${RSI_PALETTE.neutral}"></span>${tr.rsi_zone_30_50  || '30-50 偏弱'}</div>
          <div><span class="inline-block w-3 h-3 rounded-sm align-middle mr-2" style="background:${RSI_PALETTE.bullish}"></span>${tr.rsi_zone_50_70  || '50-70 健康'}</div>
          <div><span class="inline-block w-3 h-3 rounded-sm align-middle mr-2" style="background:${RSI_PALETTE.overbought}"></span>${tr.rsi_zone_70_100 || '70-100 超買'}</div>
        </div>
      </div>

      <!-- Personalised advice -->
      <div class="pt-3 border-t border-zinc-200 dark:border-zinc-800">
        <div class="text-[10px] font-black uppercase tracking-widest text-zinc-500 mb-1.5">
          ${tr.rsi_your_situation || '你目前的狀況'}
        </div>
        <div class="text-zinc-300 leading-snug text-[11px]" style="color:var(--text-main)">${personalMsg}</div>
      </div>
    `;

    document.getElementById('rsi-modal').classList.remove('hidden');
    UI.icons();
}

function closeRsiPopup() {
    document.getElementById('rsi-modal').classList.add('hidden');
}

/* ── Stage classification popup ──────────────────────────────── */
// Mirrors momentum.py _classify_stage logic so users see WHY a ticker is in a given stage.
// Rules (from the Python side):
//   Stage 2 uptrend:   ma20 > ma50 > ma200  AND price > ma20
//   Stage 4 downtrend: ma20 < ma50 < ma200  AND price < ma20
//   Stage 3 top:       ma50 > ma200  AND price < ma20  AND ma20 < ma50
//   Stage 1 basing:    otherwise
function _stageRules(r) {
    const p = r.price, m20 = r.ma_20, m50 = r.ma_50, m200 = r.ma_200;
    const tr = t();
    const yes = (ok, txt) => ({ok, txt});
    const rules = {
        'Stage 2 uptrend': [
            yes(m20 != null && m50 != null && m200 != null && m20 > m50 && m50 > m200,
                `MA 20 > MA 50 > MA 200 (${tr.stage_cond_trend || '趨勢排列正確'})`),
            yes(p != null && m20 != null && p > m20,
                `${tr.stage_cond_price_above_20 || '價格 > MA 20（短期動能向上）'}`),
        ],
        'Stage 4 downtrend': [
            yes(m20 != null && m50 != null && m200 != null && m20 < m50 && m50 < m200,
                `MA 20 < MA 50 < MA 200 (${tr.stage_cond_bear || '空頭排列'})`),
            yes(p != null && m20 != null && p < m20,
                tr.stage_cond_price_below_20 || '價格 < MA 20（短期跌勢中）'),
        ],
        'Stage 3 top': [
            yes(m50 != null && m200 != null && m50 > m200,
                `MA 50 > MA 200 (${tr.stage_cond_lt_still_up || '長期趨勢仍向上'})`),
            yes(p != null && m20 != null && p < m20,
                tr.stage_cond_price_below_20 || '價格 < MA 20（短期失守）'),
            yes(m20 != null && m50 != null && m20 < m50,
                `MA 20 < MA 50 (${tr.stage_cond_short_below_mid || '短期均線走弱'})`),
        ],
        'Stage 1 basing': [
            {ok: true, txt: tr.stage_1_note || '不符合 Stage 2/3/4，屬整理或基底期（無明確方向）'},
        ],
        'unknown': [
            {ok: false, txt: tr.stage_unknown_note || '歷史不足（< 200 天），無法分類'},
        ],
    };
    const next = {
        'Stage 2 uptrend':   tr.stage_transition_2_to_3 || '價格跌破 MA 20 → 轉向 Stage 3（需觀察 MA 50 是否續 > 200）',
        'Stage 3 top':       tr.stage_transition_3_to_4 || 'MA 50 跌破 MA 200 → 轉向 Stage 4 空頭排列',
        'Stage 4 downtrend': tr.stage_transition_4_to_1 || '價格 > MA 20 + MA 20 反轉向上 → 可能進入 Stage 1 築底',
        'Stage 1 basing':    tr.stage_transition_1_to_2 || 'MA 20 > MA 50 > MA 200 + 價格 > MA 20 → 進入 Stage 2 上升',
        'unknown':           '',
    };
    return {rules: rules[r.stage] || rules.unknown, nextCond: next[r.stage] || ''};
}

function _maStackHTML(r) {
    // Sort the 4 price-points by value descending, render each as a bar
    // with width relative to the max. Color-coded for quick visual parse.
    const items = [
        {label: 'Price',   value: r.price,  color: '#22c55e', key: 'price'},
        {label: 'MA 20',   value: r.ma_20,  color: '#3b82f6', key: 'ma20'},
        {label: 'MA 50',   value: r.ma_50,  color: '#eab308', key: 'ma50'},
        {label: 'MA 200',  value: r.ma_200, color: '#fb923c', key: 'ma200'},
    ].filter(x => x.value != null);
    if (!items.length) return '<div class="text-zinc-500">—</div>';

    items.sort((a, b) => b.value - a.value);
    const maxV = items[0].value;
    const minV = items[items.length - 1].value;
    const span = Math.max(maxV - minV, maxV * 0.01); // avoid zero-span flat bars

    return items.map(it => {
        const pct = ((it.value - minV) / span) * 80 + 20;  // 20-100% width
        const deltaPct = r.price != null && it.key !== 'price'
            ? ` <span class="text-[10px] text-zinc-500">(${((r.price / it.value - 1) * 100).toFixed(1)}%)</span>`
            : '';
        return `<div class="flex items-center gap-2">
            <span class="w-14 text-[10px] font-bold" style="color:${it.color}">${it.label}</span>
            <div class="flex-1 h-4 rounded" style="background:rgba(161,161,170,0.08)">
                <div class="h-full rounded" style="width:${pct}%; background:${it.color}; opacity:0.85"></div>
            </div>
            <span class="w-24 text-right font-mono font-bold">$${it.value.toFixed(2)}${deltaPct}</span>
        </div>`;
    }).join('');
}

function openStagePopup(r) {
    const tr = t();
    document.getElementById('stage-modal-title').textContent =
        `${r.ticker} — ${tr.stage_modal_title || '階段分類解釋'}`;

    const {rules, nextCond} = _stageRules(r);
    const stageColor = r.stage === 'Stage 2 uptrend'   ? '#22c55e'
                     : r.stage === 'Stage 3 top'       ? '#fbbf24'
                     : r.stage === 'Stage 4 downtrend' ? '#ef4444'
                     : r.stage === 'Stage 1 basing'    ? '#a1a1aa'
                     : '#71717a';

    const checklist = rules.map(x => {
        const icon = x.ok ? '☑' : '☐';
        const color = x.ok ? '#22c55e' : '#71717a';
        const dim = x.ok ? '' : 'opacity:0.6;';
        return `<div style="${dim}"><span style="color:${color};font-weight:bold;margin-right:6px">${icon}</span>${x.txt}</div>`;
    }).join('');

    document.getElementById('stage-modal-body').innerHTML = `
      <div class="flex items-center gap-2">
        <span class="text-[10px] font-black uppercase tracking-widest text-zinc-500">${tr.stage_modal_current || '目前階段'}</span>
        <span class="mlabel" style="color:${stageColor};background:${stageColor}1a;padding:2px 10px;border-radius:4px;font-size:11px">
          ${stageLabel(r.stage)}
        </span>
      </div>

      <div>
        <div class="text-[10px] font-black uppercase tracking-widest text-zinc-500 mb-2">
          ${tr.stage_modal_stack || 'MA 結構（由高至低排序）'}
        </div>
        <div class="space-y-1.5">${_maStackHTML(r)}</div>
      </div>

      <div>
        <div class="text-[10px] font-black uppercase tracking-widest text-zinc-500 mb-2">
          ${tr.stage_modal_conditions || '此階段成立的條件'}
        </div>
        <div class="space-y-1">${checklist}</div>
      </div>

      ${nextCond ? `<div class="pt-3 border-t border-zinc-200 dark:border-zinc-800">
        <div class="text-[10px] font-black uppercase tracking-widest text-zinc-500 mb-1.5">
          ${tr.stage_modal_transition || '何時會轉換到下一階段'}
        </div>
        <div class="text-zinc-400 leading-snug">${nextCond}</div>
      </div>` : ''}
    `;
    document.getElementById('stage-modal').classList.remove('hidden');
    UI.icons();
}

function closeStagePopup() {
    document.getElementById('stage-modal').classList.add('hidden');
}

/* ── Volume detail popup ─────────────────────────────────────── */
// Compute NY Eastern Time breakdown: current date/time, whether market is open,
// and the fraction of the regular session (9:30–16:00 ET) elapsed.
function _etNowInfo() {
    const nyStr = new Date().toLocaleString('en-US', {
        timeZone: 'America/New_York', hour12: false,
        year: 'numeric', month: '2-digit', day: '2-digit',
        hour: '2-digit', minute: '2-digit', weekday: 'short',
    });
    // "Mon, 04/19/2026, 11:45"
    const m = nyStr.match(/(\w{3}),\s*(\d{2})\/(\d{2})\/(\d{4}),\s*(\d{2}):(\d{2})/);
    if (!m) return { openNow: false, hhmm: nyStr, elapsed: 0, total: 390 };
    const [, wday, , , , hh, mm] = m;
    const mins = parseInt(hh, 10) * 60 + parseInt(mm, 10);
    const isWeekday = ['Mon','Tue','Wed','Thu','Fri'].includes(wday);
    const open = isWeekday && mins >= 570 && mins < 960;  // 9:30 - 16:00
    const elapsed = Math.max(0, mins - 570);
    return {
        openNow: open,
        hhmm:    `${hh}:${mm}`,
        weekday: wday,
        elapsed: Math.min(elapsed, 390),
        total:   390,
        fraction: Math.min(1, Math.max(0, elapsed / 390)),
    };
}

function _fmtShares(n) {
    if (n == null) return '—';
    if (n >= 1e9) return (n / 1e9).toFixed(2) + 'B';
    if (n >= 1e6) return (n / 1e6).toFixed(2) + 'M';
    if (n >= 1e3) return (n / 1e3).toFixed(1) + 'K';
    return String(Math.round(n));
}

function openVolumePopup(r) {
    const tr = t();
    const body = document.getElementById('volume-modal-body');
    document.getElementById('volume-modal-title').textContent =
        `${r.ticker} — ${tr.vol_modal_title || '量比細項'}`;

    const today = r.volume_today;
    const avg20 = r.avg_20d;
    const ratio = r.ratio_20d;
    const spike = r.spike_label;

    const et = _etNowInfo();
    const isIntraday = et.openNow && et.fraction > 0.02 && et.fraction < 0.98;

    // Projection (only meaningful intraday):
    //   projected_today = today / fraction
    //   projected_ratio = projected_today / avg20
    let projBlock = '';
    if (isIntraday && today && avg20) {
        const projectedToday = today / et.fraction;
        const projectedRatio = projectedToday / avg20;
        const projSpike = projectedRatio >= 3.0 ? 'HEAVY_SPIKE'
                        : projectedRatio >= 2.0 ? 'MILD_SPIKE'
                        : 'NORMAL';
        const spikeColor = projSpike === 'HEAVY_SPIKE' ? '#ef4444'
                         : projSpike === 'MILD_SPIKE'  ? '#eab308'
                         : '#71717a';
        projBlock = `
          <div class="pt-3 border-t border-zinc-200 dark:border-zinc-800">
            <div class="text-[10px] font-black uppercase tracking-widest text-zinc-500 mb-2">
              ${tr.vol_modal_projected || '全日推估（盤中）'}
            </div>
            <div class="grid grid-cols-2 gap-y-1.5">
              <span class="text-zinc-500">${tr.vol_modal_et_now || '目前 ET 時間'}</span>
              <span class="font-mono text-right">${et.hhmm} ET (${et.weekday})</span>
              <span class="text-zinc-500">${tr.vol_modal_elapsed || '盤中經過比例'}</span>
              <span class="font-mono text-right">${(et.fraction * 100).toFixed(0)}% (${(et.elapsed/60).toFixed(2)}h / 6.5h)</span>
              <span class="text-zinc-500">${tr.vol_modal_projected_vol || '依速度推估全日量'}</span>
              <span class="font-mono text-right">${_fmtShares(projectedToday)} ${tr.vol_modal_shares || '股'}</span>
              <span class="text-zinc-500 font-bold">${tr.vol_modal_projected_ratio || '推估全日量比'}</span>
              <span class="font-mono text-right font-bold" style="color:${spikeColor}">${projectedRatio.toFixed(2)}× (${projSpike})</span>
            </div>
            <div class="mt-2 text-[10px] text-zinc-500 leading-snug">
              ⚠ ${tr.vol_modal_warning || '推估假設成交量線性分布；實際多為開盤與收盤集中，早盤估值常偏高。'}
            </div>
          </div>`;
    } else if (et.openNow) {
        projBlock = `<div class="pt-3 border-t border-zinc-200 dark:border-zinc-800 text-[10px] text-zinc-500">
            ${tr.vol_modal_too_early || '盤中經過比例過低或過高，推估不穩定，略過。'}
          </div>`;
    } else {
        projBlock = `<div class="pt-3 border-t border-zinc-200 dark:border-zinc-800 text-[10px] text-zinc-500">
            ${tr.vol_modal_closed || '當前非 ET 盤中（9:30–16:00），僅顯示收盤比率。'} ${et.hhmm} ET (${et.weekday})
          </div>`;
    }

    const ratioColor = _ratioColor(ratio);

    body.innerHTML = `
      <div class="grid grid-cols-2 gap-y-1.5">
        <span class="text-zinc-500">${tr.vol_modal_today || '今日成交量'}</span>
        <span class="font-mono text-right">${_fmtShares(today)} ${tr.vol_modal_shares || '股'}</span>
        <span class="text-zinc-500">${tr.vol_modal_avg20 || '20 日均量（不含今日）'}</span>
        <span class="font-mono text-right">${_fmtShares(avg20)} ${tr.vol_modal_shares || '股'}</span>
      </div>
      <div class="flex items-baseline justify-between pt-2 border-t border-zinc-200 dark:border-zinc-800">
        <span class="text-zinc-500 font-bold">${tr.vol_modal_ratio || '量比'}</span>
        <span class="font-mono text-lg font-black" style="color:${ratioColor}">
          ${ratio != null ? ratio.toFixed(2) + '×' : '—'}
          <span class="text-[10px] font-normal ml-2 text-zinc-500">${spike || ''}</span>
        </span>
      </div>
      ${projBlock}
    `;

    document.getElementById('volume-modal').classList.remove('hidden');
    UI.icons();
}

function closeVolumePopup() {
    document.getElementById('volume-modal').classList.add('hidden');
}

/* ── History modal ────────────────────────────────────────────── */
function openHistory(ticker) {
    const hist = _state.history[ticker] || [];
    document.getElementById('history-ticker-title').textContent = ticker;
    document.getElementById('history-subtitle').textContent =
        `${hist.length} ${t().history_title ? '' : ''} data points`;

    const modal = document.getElementById('history-modal');
    modal.classList.remove('hidden');

    const emptyEl = document.getElementById('history-empty');
    const canvas = document.getElementById('history-chart');
    if (hist.length < 2) {
        canvas.style.display = 'none';
        emptyEl.classList.remove('hidden');
        emptyEl.textContent = t().history_empty || 'No history';
        return;
    }
    canvas.style.display = 'block';
    emptyEl.classList.add('hidden');

    // Parse snap_id → date (YYYYMMDD_HHMM)
    const labels = hist.map(h => {
        const m = h.snap_id.match(/_(\d{4})(\d{2})(\d{2})_(\d{2})(\d{2})$/);
        return m ? `${m[2]}/${m[3]} ${m[4]}:${m[5]}` : h.snap_id;
    });
    const scores = hist.map(h => h.score);

    if (_state.historyChart) { _state.historyChart.destroy(); }
    _state.historyChart = new Chart(canvas.getContext('2d'), {
        type: 'line',
        data: {
            labels,
            datasets: [{
                label: 'Score',
                data: scores,
                borderColor: '#22c55e',
                backgroundColor: 'rgba(34,197,94,0.08)',
                fill: true,
                tension: 0.3,
                pointRadius: 3,
                pointBackgroundColor: '#22c55e',
            }],
        },
        options: {
            responsive: true, maintainAspectRatio: false,
            plugins: { legend: { display: false } },
            scales: {
                y: { min: 0, max: 100, ticks: { color: '#71717a', font: { size: 10 } },
                     grid:  { color: 'rgba(161,161,170,0.12)' } },
                x: { ticks: { color: '#71717a', font: { size: 9 }, maxRotation: 0 },
                     grid:  { display: false } },
            },
        },
    });
    UI.icons();
}

function closeHistory() {
    document.getElementById('history-modal').classList.add('hidden');
    if (_state.historyChart) { _state.historyChart.destroy(); _state.historyChart = null; }
}

/* ── Journal stats ────────────────────────────────────────────── */
function renderJournalStats(journal) {
    const tr = t();
    document.getElementById('journal-title').textContent = tr.journal_title || 'Journal stats';
    document.getElementById('journal-note').textContent  = tr.journal_note || '';
    document.getElementById('stats-signal-title').textContent = tr.stats_signal || 'By signal (20d win rate)';
    document.getElementById('stats-bin-title').textContent    = tr.stats_bin || 'By score bin';
    document.getElementById('stats-col-signal').textContent   = 'Signal';
    document.getElementById('stats-col-n').textContent        = tr.stats_n || 'n';
    document.getElementById('stats-col-winrate').textContent  = tr.stats_winrate || 'Win%';
    document.getElementById('stats-col-mean').textContent     = tr.stats_mean || 'Mean';
    document.getElementById('stats-col-median').textContent   = tr.stats_median || 'Median';

    const stats = journal?.stats;
    const hasData = stats && stats.by_signal
                  && Object.values(stats.by_signal).some(s => s['20d']?.n > 0);

    if (!hasData) {
        document.getElementById('journal-empty').classList.remove('hidden');
        document.getElementById('journal-content').classList.add('hidden');
        document.getElementById('journal-empty-text').textContent = tr.journal_empty || 'No data yet';
        return;
    }
    document.getElementById('journal-empty').classList.add('hidden');
    document.getElementById('journal-content').classList.remove('hidden');

    document.getElementById('journal-fills-label').textContent =
        `${tr.fills_label || 'Filled'}: 20d=${stats.fill_counts?.['20d'] || 0}`;

    // By signal
    const sigRows = [];
    Object.entries(stats.by_signal || {}).forEach(([sig, byH]) => {
        const d20 = byH['20d'];
        if (d20 && d20.n >= 3) sigRows.push([sig, d20]);
    });
    sigRows.sort((a, b) => b[1].win_rate - a[1].win_rate);
    document.getElementById('stats-signal-tbody').innerHTML = sigRows.slice(0, 12).map(([sig, d]) => {
        const wrPct = (d.win_rate * 100).toFixed(0);
        const wrColor = d.win_rate >= 0.6 ? '#22c55e'
                      : d.win_rate >= 0.5 ? '#86efac'
                      : d.win_rate >= 0.4 ? '#fbbf24' : '#ef4444';
        return `<tr class="stats-row">
            <td class="text-xs" title="${sig}">${sigLabel(sig)}</td>
            <td class="text-right text-xs text-zinc-400">${d.n}</td>
            <td>
                <div class="flex items-center gap-2">
                    <div class="winrate-bar flex-1" style="min-width:60px">
                        <div class="winrate-fill" style="width:${wrPct}%; background:${wrColor}"></div>
                    </div>
                    <span class="text-[10px] font-mono" style="color:${wrColor}">${wrPct}%</span>
                </div>
            </td>
            <td class="text-right font-mono text-xs" style="color:${d.mean >= 0 ? '#86efac' : '#fca5a5'}">${d.mean >= 0 ? '+' : ''}${d.mean}</td>
            <td class="text-right font-mono text-xs" style="color:${d.median >= 0 ? '#86efac' : '#fca5a5'}">${d.median >= 0 ? '+' : ''}${d.median}</td>
        </tr>`;
    }).join('');

    // By score bin
    const binOrder = ['90-100', '80-90', '70-80', '60-70', '50-60', '<50'];
    const binRows = binOrder
        .filter(b => stats.by_score_bin?.[b])
        .map(b => [b, stats.by_score_bin[b]]);
    document.getElementById('stats-bin-tbody').innerHTML = binRows.map(([bin, byH]) => {
        const d5 = byH['5d'] || {};
        const d20 = byH['20d'] || {};
        const d60 = byH['60d'] || {};
        const n = d20.n || d5.n || d60.n || 0;
        const wr = d20.win_rate != null ? `${(d20.win_rate*100).toFixed(0)}%` : '—';
        const fmt = v => v == null ? '—' : (v >= 0 ? '+' : '') + v.toFixed(1);
        return `<tr class="stats-row">
            <td class="text-xs font-mono font-bold">${bin}</td>
            <td class="text-right text-xs text-zinc-400">${n}</td>
            <td class="text-xs">${wr}</td>
            <td class="text-right font-mono text-xs">${fmt(d5.mean)}</td>
            <td class="text-right font-mono text-xs">${fmt(d20.mean)}</td>
            <td class="text-right font-mono text-xs">${fmt(d60.mean)}</td>
        </tr>`;
    }).join('');
}

/* ── Refresh action (async + polling) ────────────────────────── */
let _scanPollTimer = null;

function _fmtElapsed(sec) {
    const mm = String(Math.floor(sec / 60)).padStart(2, '0');
    const ss = String(sec % 60).padStart(2, '0');
    return `${mm}:${ss}`;
}

let _indicatorHideTimer = null;

function showScanIndicator(status, phase, elapsedSec, progress) {
    const el = document.getElementById('scan-indicator');
    if (!el) return;
    el.classList.remove('hidden');
    el.classList.add('flex');

    const tr = t();
    const statusLabels = {
        running:  tr.banner_scanning || 'SCANNING',
        bridging: tr.banner_bridging || 'REFRESHING',
        done:     tr.banner_done     || 'DONE',
        error:    tr.banner_error    || 'ERROR',
    };
    const statusColors = {
        running:  { fg: '#22c55e', bg: 'rgba(34,197,94,0.10)', border: 'rgba(34,197,94,0.35)' },
        bridging: { fg: '#eab308', bg: 'rgba(234,179,8,0.10)', border: 'rgba(234,179,8,0.35)' },
        done:     { fg: '#22c55e', bg: 'rgba(34,197,94,0.10)', border: 'rgba(34,197,94,0.35)' },
        error:    { fg: '#ef4444', bg: 'rgba(239,68,68,0.10)', border: 'rgba(239,68,68,0.35)' },
    };
    const c = statusColors[status] || statusColors.running;
    el.style.background  = c.bg;
    el.style.borderColor = c.border;

    const statusEl = document.getElementById('scan-indicator-status');
    let statusTxt = statusLabels[status] || status.toUpperCase();
    // Append progress for running state: "SCANNING 150/503"
    if (status === 'running' && progress && progress.total > 0) {
        statusTxt += `  ${progress.done || 0}/${progress.total}`;
    }
    statusEl.textContent = statusTxt;
    statusEl.style.color = c.fg;

    const iconEl = document.getElementById('scan-indicator-icon');
    iconEl.style.color = c.fg;
    if (status === 'running' || status === 'bridging') {
        iconEl.setAttribute('data-lucide', 'loader-2');
        iconEl.classList.add('animate-spin');
    } else if (status === 'done') {
        iconEl.setAttribute('data-lucide', 'check-circle-2');
        iconEl.classList.remove('animate-spin');
    } else {
        iconEl.setAttribute('data-lucide', 'alert-circle');
        iconEl.classList.remove('animate-spin');
    }

    const elapsedEl = document.getElementById('scan-indicator-elapsed');
    elapsedEl.textContent = _fmtElapsed(elapsedSec || 0);
    // Hover tooltip: phase + cache hit / error count when available
    const tips = [];
    if (phase) tips.push(phase);
    if (progress && progress.total > 0) {
        tips.push(`cache hits ${progress.cache_hits_count || 0}`);
        if (progress.errors_count) tips.push(`fetch errors ${progress.errors_count}`);
    }
    el.title = tips.join(' · ');

    // Auto-hide terminal states after a short display window
    if (_indicatorHideTimer) { clearTimeout(_indicatorHideTimer); _indicatorHideTimer = null; }
    if (status === 'done' || status === 'error') {
        _indicatorHideTimer = setTimeout(hideScanIndicator, 5000);
    }
    UI.icons();
}

function hideScanIndicator() {
    const el = document.getElementById('scan-indicator');
    if (!el) return;
    el.classList.add('hidden');
    el.classList.remove('flex');
    if (_indicatorHideTimer) { clearTimeout(_indicatorHideTimer); _indicatorHideTimer = null; }
}

// Legacy aliases so existing callers keep working without churn
const showScanBanner = showScanIndicator;
const hideScanBanner = hideScanIndicator;

async function triggerRescan() {
    const btn = document.getElementById('refresh-momentum');
    if (btn.dataset.busy === '1') return;
    btn.dataset.busy = '1';
    btn.disabled = true;
    const label = document.getElementById('refresh-btn-label');
    const origLabel = label.textContent;
    label.textContent = (t().banner_scanning || '掃描中…');

    // Server scans the full universe — no min_score filter so the client-side
    // panel has the full distribution to slice through.
    const params = {
        universe: 'sp500',
        journal: true,
    };

    try {
        const res = await fetch('/api/run-momentum-screen', {
            method:  'POST',
            headers: { 'Content-Type': 'application/json' },
            body:    JSON.stringify(params),
        });
        const j = await res.json();
        if (res.status === 409) {
            // Already running — just start polling
            UI.logToUI('Rescan: another scan already running, polling status…', 'warn');
        } else if (!res.ok) {
            throw new Error(j.error || `HTTP ${res.status}`);
        }
        startScanPolling(btn, label, origLabel);
    } catch (e) {
        UI.logToUI('Rescan failed: ' + e.message, 'error');
        showScanBanner('error', e.message, 0);
        btn.dataset.busy = '0';
        btn.disabled = false;
        label.textContent = origLabel;
    }
}

function startScanPolling(btn, label, origLabel) {
    if (_scanPollTimer) clearInterval(_scanPollTimer);

    const poll = async () => {
        try {
            const res = await fetch('/api/run-momentum-screen/status');
            if (!res.ok) throw new Error(`HTTP ${res.status}`);
            const s = await res.json();
            showScanBanner(s.status, s.phase || '', s.elapsed_sec || 0, {
                done: s.done, total: s.total,
                cache_hits_count: s.cache_hits_count,
                errors_count: s.errors_count,
            });

            if (s.status === 'done') {
                clearInterval(_scanPollTimer); _scanPollTimer = null;
                UI.logToUI(`Momentum: scan done → ${s.csv_path || 'no CSV'}`);
                try {
                    await DataStore.refresh();
                    await loadMomentumData();
                } catch (e) {
                    UI.logToUI('Reload after scan failed: ' + e.message, 'error');
                }
                btn.dataset.busy = '0';
                btn.disabled = false;
                label.textContent = origLabel;
            } else if (s.status === 'error') {
                clearInterval(_scanPollTimer); _scanPollTimer = null;
                UI.logToUI('Scan errored: ' + s.error, 'error');
                btn.dataset.busy = '0';
                btn.disabled = false;
                label.textContent = origLabel;
            }
        } catch (e) {
            UI.logToUI('Status poll failed: ' + e.message, 'error');
        }
    };

    poll();                                   // immediate first tick
    _scanPollTimer = setInterval(poll, 1500); // 1.5s cadence
}

async function checkExistingScan() {
    // On page load, if a scan is already in progress (from another tab or page),
    // show the banner so user sees it.
    try {
        const res = await fetch('/api/run-momentum-screen/status');
        if (!res.ok) return;
        const s = await res.json();
        if (s.status === 'running' || s.status === 'bridging') {
            const btn = document.getElementById('refresh-momentum');
            const label = document.getElementById('refresh-btn-label');
            const origLabel = label.textContent;
            btn.dataset.busy = '1';
            btn.disabled = true;
            showScanBanner(s.status, s.phase || '', s.elapsed_sec || 0, {
                done: s.done, total: s.total,
                cache_hits_count: s.cache_hits_count,
                errors_count: s.errors_count,
            });
            startScanPolling(btn, label, origLabel);
        }
    } catch (e) { /* server may not have endpoint yet — ignore */ }
}

/* ── Translations ─────────────────────────────────────────────── */
function translate() {
    const tr = t();
    const set = (id, val) => { const el = document.getElementById(id); if (el && val) el.textContent = val; };
    set('momentum-title',     tr.title);
    set('momentum-subtitle',  tr.subtitle);
    set('refresh-btn-label',  tr.refresh_btn);
    set('th-rank',      tr.col_rank);
    set('th-ticker',    tr.col_ticker);
    set('th-price',     tr.col_price);
    set('th-score',     tr.col_score);
    set('th-label',     tr.col_label);
    set('th-stage',     tr.col_stage);
    set('th-volume',    tr.col_volume);
    set('th-above-200', tr.col_above_200);
    set('th-rsi',       tr.col_rsi);
    set('th-signals',   tr.col_signals);
    set('th-short',     tr.col_short);
    set('no-data-text', tr.no_data);
    set('filter-title',          tr.filter_title);
    set('filter-reset-label',    tr.filter_reset);
    set('filter-score-label',    tr.filter_score);
    set('filter-rsi-label',      tr.filter_rsi);
    set('filter-stage-label',    tr.filter_stage);
    set('filter-sector-label',   tr.filter_sector);
    set('filter-search-label',   tr.filter_search);
    set('filter-preset-label',   tr.filter_preset_title);
    set('filter-req-sig-label',  tr.filter_req_sig);
    set('filter-excl-warn-label',tr.filter_excl_warn);
    // Re-render preset row so tooltips translate on language toggle
    if (_state.rows.length) renderPresetRow();
    const search = document.getElementById('search-ticker');
    if (search && tr.search_placeholder) search.placeholder = tr.search_placeholder;
    const stageSel = document.getElementById('f-stage');
    if (stageSel && tr.stage_any) {
        const anyOpt = stageSel.querySelector('option[value="any"]');
        if (anyOpt) anyOpt.textContent = tr.stage_any;
        stageSel.querySelectorAll('option[value^="Stage"]').forEach(opt => {
            opt.textContent = stageLabel(opt.value);
        });
    }
    const sectorSel = document.getElementById('f-sector');
    if (sectorSel) {
        const anyOpt = sectorSel.querySelector('option[value="any"]');
        if (anyOpt) anyOpt.textContent = tr.stage_any || 'Any';
        SECTOR_KEYS.forEach(key => {
            const opt = sectorSel.querySelector(`option[value="${key}"]`);
            if (opt) opt.textContent = sectorLabel(key);
        });
    }
    const btn = document.getElementById('refresh-momentum');
    if (btn && tr.refresh_hint) btn.title = tr.refresh_hint;
}

/* ── Boot ─────────────────────────────────────────────────────── */
document.addEventListener('DOMContentLoaded', () => {
    UI.boot('momentum', { translate, reload: loadMomentumData });

    document.getElementById('refresh-momentum').addEventListener('click', triggerRescan);
    document.getElementById('history-close').addEventListener('click', closeHistory);
    document.getElementById('history-modal-bg').addEventListener('click', closeHistory);
    document.getElementById('volume-modal-close')?.addEventListener('click', closeVolumePopup);
    document.getElementById('volume-modal-bg')?.addEventListener('click', closeVolumePopup);
    document.getElementById('stage-modal-close')?.addEventListener('click', closeStagePopup);
    document.getElementById('stage-modal-bg')?.addEventListener('click', closeStagePopup);
    document.getElementById('rsi-modal-close')?.addEventListener('click', closeRsiPopup);
    document.getElementById('rsi-modal-bg')?.addEventListener('click', closeRsiPopup);
    // Click the indicator itself to dismiss (works when in terminal state)
    document.getElementById('scan-indicator')?.addEventListener('click', hideScanIndicator);
    document.addEventListener('keydown', e => {
        if (e.key === 'Escape') { closeHistory(); closeVolumePopup(); closeStagePopup(); closeRsiPopup(); }
    });

    // ── Filter panel bindings ───────────────────────────────────
    document.getElementById('f-min-score').addEventListener('input', e => {
        _state.filter.minScore = Number(e.target.value);
        document.getElementById('filter-score-val').textContent = `≥ ${_state.filter.minScore}`;
        renderTable();
    });
    const rsiBind = (id, key) => {
        document.getElementById(id).addEventListener('input', e => {
            const v = e.target.value.trim();
            _state.filter[key] = v === '' ? null : Number(v);
            renderTable();
        });
    };
    rsiBind('f-min-rsi', 'minRsi');
    rsiBind('f-max-rsi', 'maxRsi');
    document.getElementById('f-stage').addEventListener('change', e => {
        _state.filter.stage = e.target.value;
        renderTable();
    });
    document.getElementById('f-sector').addEventListener('change', e => {
        _state.filter.sector = e.target.value;
        renderTable();
    });
    document.getElementById('search-ticker').addEventListener('input', e => {
        _state.filter.search = e.target.value;
        renderTable();
    });
    document.getElementById('filter-reset').addEventListener('click', () => {
        _state.filter = defaultFilter();
        renderFilterPanel();
        renderTable();
    });

    _bindSortHeaders();
    loadMomentumData();
    checkExistingScan();
});
