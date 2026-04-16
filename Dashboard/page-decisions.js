/**
 * page-decisions.js — Decisions center (Watch Radar + History + Positions unified)
 * Depends on: utils.js (window.UI), i18n.js, data-store.js (window.DataStore)
 */

// ── Page translations ──────────────────────────────────────────
function applyTranslations() {
    if (!window.i18n) return;
    const t  = window.i18n[UI.currentLang];
    const wl = t.watchlist || {};
    const pos = t.positions || {};
    if (!wl.title) return;

    document.getElementById('page-title').textContent    = wl.title;
    document.getElementById('page-subtitle').textContent = wl.subtitle;
    document.getElementById('refresh-label').textContent = UI.currentLang === 'zh' ? '更新' : 'Refresh';
    document.getElementById('lbl-active').textContent    = wl.active_label;
    document.getElementById('lbl-waiting').textContent   = wl.waiting_label;
    document.getElementById('lbl-conf').textContent      = wl.avg_conf;
    document.getElementById('lbl-rr').textContent        = wl.avg_rr;
    document.getElementById('ftab-all').textContent        = wl.filter_all;
    document.getElementById('ftab-execute').textContent    = wl.filter_active;
    document.getElementById('ftab-waiting').textContent    = wl.filter_waiting;
    document.getElementById('ftab-historical').textContent = wl.filter_historical || (UI.currentLang === 'zh' ? '歷史' : 'Historical');
    document.getElementById('ftab-positions').textContent  = wl.filter_positions  || (UI.currentLang === 'zh' ? '持倉' : 'Positions');

    // Positions form
    const byId = (id, val) => { const el = document.getElementById(id); if (el && val) el.textContent = val; };
    byId('add-position-label', pos.add_btn?.replace(/^\+\s*/, '') || 'Add Position');
    byId('position-modal-title', pos.modal_title);
    byId('pf-ticker-lbl',  pos.ticker);
    byId('pf-date-lbl',    pos.entry_date);
    byId('pf-price-lbl',   pos.entry_price);
    byId('pf-shares-lbl',  pos.shares);
    byId('pf-track-lbl',   pos.track);
    byId('pf-notes-lbl',   pos.notes);
    const cancelBtn = document.getElementById('pf-cancel');
    const submitBtn = document.getElementById('pf-submit');
    if (cancelBtn && pos.cancel) cancelBtn.textContent = pos.cancel;
    if (submitBtn && pos.submit) submitBtn.textContent = pos.submit;

    // Translate <option> labels (track select) via data-i18n-key
    document.querySelectorAll('#position-form option[data-i18n-key]').forEach(opt => {
        const k = opt.dataset.i18nKey;
        if (pos[k]) opt.textContent = pos[k];
    });

    // Translate placeholders
    const setPh = (sel, val) => { const el = document.querySelector(sel); if (el && val) el.placeholder = val; };
    setPh('#position-form input[name="ticker"]',      pos.ticker_placeholder);
    setPh('#position-form input[name="entry_price"]', pos.price_placeholder);
    setPh('#position-form input[name="shares"]',      pos.shares_placeholder);
    setPh('#position-form textarea[name="notes"]',    pos.notes_placeholder);

    // Close-position modal
    byId('exit-modal-title', pos.close_modal_title);
    byId('cf-date-lbl',   pos.exit_date);
    byId('cf-price-lbl',  pos.exit_price);
    byId('cf-shares-lbl', pos.closed_shares);
    byId('cf-hint',       pos.close_partial_hint);
    const cfCancel = document.getElementById('cf-cancel');
    if (cfCancel && pos.cancel) cfCancel.textContent = pos.cancel;
    const cfSubmit = document.getElementById('cf-submit');
    if (cfSubmit && pos.confirm_btn) cfSubmit.textContent = pos.confirm_btn;
}

// ── Position modal control ─────────────────────────────────────
function openPositionModal(prefillTicker) {
    const modal = document.getElementById('position-modal');
    const form  = document.getElementById('position-form');
    form.reset();
    form.entry_date.value = new Date().toISOString().slice(0, 10);
    if (prefillTicker) form.ticker.value = prefillTicker;
    document.getElementById('position-form-error').classList.add('hidden');
    applyTranslations();   // ensure labels reflect current language on every open
    modal.classList.remove('hidden');
    form.ticker.focus();
}
function closePositionModal() {
    document.getElementById('position-modal').classList.add('hidden');
}

async function submitPositionForm(e) {
    e.preventDefault();
    const form = e.target;
    const errEl = document.getElementById('position-form-error');
    errEl.classList.add('hidden');
    const body = {
        ticker:      form.ticker.value.toUpperCase().trim(),
        entry_date:  form.entry_date.value,
        entry_price: parseFloat(form.entry_price.value),
        shares:      parseFloat(form.shares.value),
        track:       form.track.value,
        notes:       form.notes.value,
    };
    try {
        const res = await fetch('/api/positions', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body),
        });
        if (!res.ok) {
            const err = await res.json().catch(() => ({ error: res.statusText }));
            throw new Error(err.error || `HTTP ${res.status}`);
        }
        logToUI(`Position saved: ${body.ticker} ${body.shares}@$${body.entry_price}`);
        closePositionModal();
        // Reload after bridge.py completes (it runs async on server)
        setTimeout(() => loadWatchlist(), 1500);
    } catch (err) {
        errEl.textContent = err.message;
        errEl.classList.remove('hidden');
    }
}

async function deletePosition(posId) {
    if (!confirm(`Delete position ${posId}?`)) return;
    try {
        const res = await fetch(`/api/positions/${posId}`, { method: 'DELETE' });
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        logToUI(`Position deleted: ${posId}`);
        setTimeout(() => loadWatchlist(), 1500);
    } catch (err) {
        alert(`Delete failed: ${err.message}`);
    }
}
window.deletePosition = deletePosition;
window.openPositionModal = openPositionModal;

// ── Close (exit) position flow ─────────────────────────────────
let _closingLot = null;

function openClosePositionModal(posId) {
    const lot = (window._positionsFlat || []).find(l => l.id === posId);
    if (!lot) { alert('Position not found'); return; }
    _closingLot = lot;
    const modal = document.getElementById('exit-modal');
    const form  = document.getElementById('close-form');
    form.reset();
    form.exit_date.value = new Date().toISOString().slice(0, 10);
    form.exit_price.value = lot.current_price || lot.entry_price;
    form.closed_shares.value = lot.shares;
    const _pos = window.i18n?.[UI.currentLang]?.positions || {};
    const _sh = _pos.shares_lbl || 'sh';
    document.getElementById('close-summary').textContent =
        `${lot.ticker} • ${lot.shares} ${_sh} @ $${lot.entry_price} (${lot.entry_date})`;
    document.getElementById('close-form-error').classList.add('hidden');
    applyTranslations();
    updateClosePreview();
    modal.classList.remove('hidden');
    form.exit_price.focus();
    form.exit_price.select();
}
function closeExitModal() {
    document.getElementById('exit-modal').classList.add('hidden');
    _closingLot = null;
}
function updateClosePreview() {
    if (!_closingLot) return;
    const form = document.getElementById('close-form');
    const ep = parseFloat(form.exit_price.value);
    const sh = parseFloat(form.closed_shares.value);
    const preview = document.getElementById('close-form-preview');
    if (!isFinite(ep) || !isFinite(sh) || sh <= 0) {
        preview.classList.add('hidden'); return;
    }
    const pl = (ep - _closingLot.entry_price) * sh;
    const pct = (ep / _closingLot.entry_price - 1) * 100;
    const isPartial = sh < _closingLot.shares - 1e-6;
    const color = pl >= 0 ? '#22c55e' : '#ef4444';
    const _pos = window.i18n?.[UI.currentLang]?.positions || {};
    const tag = isPartial ? (_pos.partial_exit || 'PARTIAL EXIT') : (_pos.full_close || 'FULL CLOSE');
    const rpLabel = _pos.realized_pl || 'Realized P/L';
    const shLbl = _pos.shares_lbl || 'sh';
    preview.innerHTML = `
        <div>${tag} → ${sh} ${shLbl} @ $${ep.toFixed(2)}</div>
        <div style="color:${color}">${rpLabel}: ${pl >= 0 ? '+' : ''}$${pl.toFixed(2)} (${pct >= 0 ? '+' : ''}${pct.toFixed(2)}%)</div>`;
    preview.classList.remove('hidden');
}

async function submitCloseForm(e) {
    e.preventDefault();
    if (!_closingLot) return;
    const form = e.target;
    const errEl = document.getElementById('close-form-error');
    errEl.classList.add('hidden');
    const closedSh = parseFloat(form.closed_shares.value);
    if (closedSh <= 0 || closedSh > _closingLot.shares + 1e-6) {
        errEl.textContent = `shares must be > 0 and ≤ ${_closingLot.shares}`;
        errEl.classList.remove('hidden');
        return;
    }
    const body = {
        exit_date:     form.exit_date.value,
        exit_price:    parseFloat(form.exit_price.value),
        closed_shares: closedSh,
    };
    try {
        const res = await fetch(`/api/positions/${_closingLot.id}`, {
            method: 'PATCH',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body),
        });
        if (!res.ok) {
            const err = await res.json().catch(() => ({ error: res.statusText }));
            throw new Error(err.error || `HTTP ${res.status}`);
        }
        logToUI(`Position closed: ${_closingLot.ticker} ${closedSh}@$${body.exit_price}`);
        closeExitModal();
        setTimeout(() => loadWatchlist(), 1500);
    } catch (err) {
        errEl.textContent = err.message;
        errEl.classList.remove('hidden');
    }
}
window.openClosePositionModal = openClosePositionModal;

// ── Report Modal ───────────────────────────────────────────────
async function viewReport(path) {
    if (!path || path === 'null') { alert('Report pending...'); return; }
    const modal   = document.getElementById('report-modal');
    const content = document.getElementById('report-content');
    modal.classList.remove('hidden');
    content.innerHTML = '<div class="flex items-center justify-center h-full p-20 animate-pulse text-zinc-500">Loading...</div>';
    try {
        const full = '../' + path + '?t=' + Date.now();
        if (path.endsWith('.html')) {
            content.innerHTML = `<iframe src="${full}" class="w-full h-full border-0 bg-white rounded-lg"></iframe>`;
        } else {
            const md = await (await fetch(full)).text();
            const isDark = document.documentElement.classList.contains('dark');
            const proseTheme = isDark
              ? 'prose-invert text-zinc-300 prose-headings:text-zinc-100 prose-strong:text-zinc-100 prose-code:text-emerald-400 prose-a:text-emerald-400'
              : 'text-zinc-800 prose-headings:text-zinc-900 prose-strong:text-zinc-900 prose-code:text-emerald-700 prose-a:text-emerald-700 prose-li:text-zinc-700 prose-p:text-zinc-700';
            content.innerHTML = `<div class="p-8 prose prose-zinc max-w-none ${proseTheme}">${marked.parse(md)}</div>`;
        }
    } catch (e) {
        content.innerHTML = `<div class="p-10 text-center text-red-500">Failed: ${e.message}</div>`;
    }
}
document.getElementById('close-modal').addEventListener('click', () =>
    document.getElementById('report-modal').classList.add('hidden'));
document.addEventListener('keydown', e => { if (e.key === 'Escape') document.getElementById('report-modal').classList.add('hidden'); });

// ── Filter State ───────────────────────────────────────────────
// Support ?view=active|waiting|historical|positions deep-link from index.html
const _viewParam = new URLSearchParams(window.location.search).get('view');
const _viewMap = { active: 'execute', execute: 'execute', waiting: 'waiting',
                   historical: 'historical', positions: 'positions', all: 'all' };
let activeFilter = _viewMap[_viewParam] || 'all';
document.getElementById('filter-tabs').addEventListener('click', e => {
    const btn = e.target.closest('[data-filter]');
    if (!btn) return;
    activeFilter = btn.dataset.filter;
    document.querySelectorAll('.filter-tab').forEach(b => {
        const on = b.dataset.filter === activeFilter;
        b.className = `filter-tab px-4 py-1.5 rounded-lg text-xs font-bold border transition-all ${
            on ? 'bg-emerald-500 text-black border-emerald-500'
               : 'border-zinc-200 dark:border-zinc-800 text-zinc-500 hover:border-zinc-400'}`;
    });
    renderCards(activeFilter);
});
// init tab styles (respect deep-link activeFilter)
document.querySelectorAll('.filter-tab').forEach(b => {
    const on = b.dataset.filter === activeFilter;
    b.className = `filter-tab px-4 py-1.5 rounded-lg text-xs font-bold border transition-all ${
        on ? 'bg-emerald-500 text-black border-emerald-500'
           : 'border-zinc-200 dark:border-zinc-800 text-zinc-500 hover:border-zinc-400'}`;
});

// ── Render ─────────────────────────────────────────────────────
const DECISION_COLOR = {
    EXECUTE: 'var(--status-bullish)', BUY: 'var(--status-bullish)',
    STAGED: 'var(--status-binary)', STAGED_ENTRY: 'var(--status-binary)',
    STAGED_EXIT: 'var(--status-binary)',
    CANCEL:  'var(--status-bearish)', SELL: 'var(--status-bearish)',
    HOLD: 'var(--text-muted)', ARCHIVE: 'var(--text-muted)',
};

function isActiveDecision(d) {
    return d === 'EXECUTE' || d === 'BUY' || d === 'STAGED' || d === 'STAGED_ENTRY';
}

function riskTag(risk) {
    const clean = risk.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
    return `<span class="text-[9px] font-bold px-2 py-0.5 rounded bg-red-500/10 text-red-400 border border-red-500/20 whitespace-nowrap">${clean}</span>`;
}

function conditionRow(label, text, color = 'var(--status-bullish)') {
    // Stacked layout: label on its own line (supports long keys like BREAKOUT_UP/CATALYST_MISS)
    return `
    <div class="mb-1.5 last:mb-0">
        <div class="text-[9px] font-black uppercase tracking-widest leading-tight" style="color:${color}">${label}</div>
        <div class="text-[10px] leading-relaxed mt-0.5" style="color:var(--text-main)">${text}</div>
    </div>`;
}

function buildCard(item) {
    const isExecute = isActiveDecision(item.decision);
    const isStaged = item.decision === 'STAGED' || item.decision === 'STAGED_ENTRY' || item.final_decision === 'STAGED_ENTRY';
    const statusColor = DECISION_COLOR[item.decision] || 'var(--text-muted)';
    const t  = window.i18n?.[UI.currentLang] || {};
    const wl = t.watchlist || {};
    const status  = t.status?.[item.decision] || item.decision;
    const horizon = item.time_horizon ? (t.horizon?.[item.time_horizon] || item.time_horizon) : null;

    // Live position overlay
    const pos = t.positions || {};
    let livePosHtml = '';
    if (item.live_position) {
        const lp = item.live_position;
        const plColor = (lp.unrealized_pct ?? 0) >= 0 ? 'var(--status-bullish)' : 'var(--status-bearish)';
        const plSign = (lp.unrealized_pct ?? 0) >= 0 ? '+' : '';
        livePosHtml = `
        <div class="mt-3 rounded-lg p-3" style="background:color-mix(in srgb,${plColor},transparent 92%);border:1px solid color-mix(in srgb,${plColor},transparent 75%)">
            <div class="flex items-center justify-between gap-3">
                <div class="flex items-center gap-2">
                    <i data-lucide="wallet" class="w-3.5 h-3.5" style="color:${plColor}"></i>
                    <span class="text-[9px] font-black uppercase tracking-widest" style="color:${plColor}">${pos.live_pos || 'HELD'}</span>
                    <span class="text-[11px] font-mono font-bold" style="color:var(--text-card-title)">${lp.total_shares} ${pos.shares_lbl || 'sh'}</span>
                    <span class="text-[10px] font-mono text-zinc-500">@ $${lp.avg_cost}</span>
                    ${lp.lots > 1 ? `<span class="text-[8px] text-zinc-600">(${lp.lots} ${pos.lots || 'lots'})</span>` : ''}
                </div>
                ${lp.unrealized_pct != null ? `<div class="text-right">
                    <div class="text-[8px] font-bold text-zinc-500 uppercase">${pos.upl || 'U/L'}</div>
                    <div class="text-sm font-mono font-black" style="color:${plColor}">${plSign}${lp.unrealized_pct}%</div>
                </div>` : ''}
            </div>
            ${item.position_lots?.length ? `
            <div class="mt-2 pt-2 border-t border-zinc-200 dark:border-zinc-800/50 flex flex-wrap gap-1">
                ${item.position_lots.map(lot => `
                    <div class="text-[8px] font-mono px-1.5 py-0.5 rounded bg-zinc-100 dark:bg-zinc-900/50 border border-zinc-200 dark:border-zinc-800 flex items-center gap-1">
                        <span>${lot.entry_date}</span>
                        <span class="text-zinc-500">${lot.shares}@$${lot.entry_price}</span>
                        <button onclick="event.stopPropagation(); deletePosition('${lot.id}')" class="text-zinc-500 hover:text-red-400 ml-0.5" title="${pos.delete || 'Delete'}">×</button>
                    </div>`).join('')}
            </div>` : ''}
        </div>`;
    }

    // V4.6 badges: consensus bonus, macro alignment, binary class
    const badgesHtml = [
        item.consensus_bonus ? `<span class="text-[8px] px-1.5 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 font-bold">×1.15 CONSENSUS</span>` : '',
        item.macro_alignment === 'CONTRARIAN' ? `<span class="text-[8px] px-1.5 py-0.5 rounded bg-violet-500/10 text-violet-400 border border-violet-500/20 font-bold">CONTRARIAN</span>` : '',
        item.binary_class === 'positive' ? `<span class="text-[8px] px-1.5 py-0.5 rounded bg-blue-500/10 text-blue-400 border border-blue-500/20 font-bold">POS BINARY</span>` : '',
        item.binary_class === 'negative' ? `<span class="text-[8px] px-1.5 py-0.5 rounded bg-red-500/10 text-red-400 border border-red-500/20 font-bold">NEG BINARY</span>` : '',
    ].filter(Boolean).join(' ');

    // Entry targets block — V4.6 supports dual-track
    const tgt = item.targets || {};
    let targetHtml = '';
    if (tgt.tp || tgt.sl) {
        targetHtml = `
        <div class="flex gap-4 pt-3 border-t border-zinc-200 dark:border-zinc-900/50">
            ${tgt.tp ? `<div><p class="text-[8px] text-zinc-600 font-bold uppercase">TP</p><p class="text-xs font-mono font-bold" style="color:var(--status-bullish)">$${tgt.tp}</p></div>` : ''}
            ${tgt.sl ? `<div class="border-l border-zinc-200 dark:border-zinc-900/50 pl-4"><p class="text-[8px] text-zinc-600 font-bold uppercase">SL</p><p class="text-xs font-mono font-bold" style="color:var(--status-bearish)">$${tgt.sl}</p></div>` : ''}
            ${!tgt.entry_aggressive && tgt.entry ? `<div class="border-l border-zinc-200 dark:border-zinc-900/50 pl-4"><p class="text-[8px] text-zinc-600 font-bold uppercase">Entry</p><p class="text-xs font-mono font-bold" style="color:var(--status-binary)">${tgt.entry}</p></div>` : ''}
        </div>`;
    } else if (tgt.watch || tgt.entry) {
        const val = tgt.watch || tgt.entry;
        const lbl = tgt.watch ? 'Watch' : 'Entry';
        targetHtml = `
        <div class="pt-3 border-t border-zinc-200 dark:border-zinc-900/50">
            <p class="text-[8px] text-zinc-600 font-bold uppercase">${lbl}</p>
            <p class="text-xs font-mono font-bold" style="color:var(--status-binary)">${val}</p>
        </div>`;
    }

    // V4.6 dual-track entry block
    let dualTrackHtml = '';
    if (tgt.entry_aggressive || tgt.entry_conservative) {
        const split = item.staged_split || {};
        const aggPct = split.aggressive_pct != null ? ` (${Math.round(split.aggressive_pct * 100)}%)` : '';
        const consPct = split.conservative_pct != null ? ` (${Math.round(split.conservative_pct * 100)}%)` : '';
        dualTrackHtml = `
        <div class="mt-4 pt-4 border-t border-zinc-200 dark:border-zinc-900/50 space-y-2">
            <p class="text-[9px] font-black uppercase tracking-widest flex items-center gap-1" style="color:var(--status-binary)">
                <i data-lucide="git-fork" class="w-3 h-3"></i> ${wl.dual_track || 'Dual-Track Entry'}
            </p>
            ${tgt.entry_aggressive ? `
            <div class="flex gap-2 items-start">
                <span class="text-[9px] font-black uppercase tracking-widest mt-0.5 shrink-0 w-20" style="color:var(--status-bullish)">AGG${aggPct}</span>
                <span class="text-[10px] font-mono leading-relaxed" style="color:var(--text-main)">$${tgt.entry_aggressive}</span>
            </div>` : ''}
            ${tgt.entry_conservative ? `
            <div class="flex gap-2 items-start">
                <span class="text-[9px] font-black uppercase tracking-widest mt-0.5 shrink-0 w-20" style="color:var(--status-binary)">CONS${consPct}</span>
                <span class="text-[10px] font-mono leading-relaxed" style="color:var(--text-main)">$${tgt.entry_conservative}</span>
            </div>` : ''}
        </div>`;
    }

    // Watch conditions block — different semantics per decision state:
    //   HOLD / CANCEL → re-evaluation triggers (watchlist state change)
    //   BUY / STAGED  → entry triggers (price to enter)
    let condHtml = '';
    if (item.watch_conditions) {
        const entries = Object.entries(item.watch_conditions);
        const isReEval = (item.decision === 'HOLD' || item.decision === 'CANCEL')
                         && item.final_decision !== 'STAGED_ENTRY';
        const header = isReEval
            ? (wl.reeval_triggers || (UI.currentLang === 'zh' ? '觀察觸發條件' : 'Watch Triggers'))
            : (wl.entry_triggers || (UI.currentLang === 'zh' ? '進場觸發條件' : 'Entry Triggers'));
        const icon = isReEval ? 'eye' : 'crosshair';
        condHtml = `
        <div class="mt-4 pt-4 border-t border-zinc-200 dark:border-zinc-900/50">
            <p class="text-[9px] font-black text-yellow-500 uppercase tracking-widest flex items-center gap-1 mb-2">
                <i data-lucide="${icon}" class="w-3 h-3"></i> ${header}
            </p>
            ${entries.map(([k, v]) => conditionRow(k.toUpperCase().replace(/_/g, ' '), v, 'var(--status-binary)')).join('')}
        </div>`;
    }

    // Key risks
    let risksHtml = '';
    if (item.key_risks && item.key_risks.length) {
        risksHtml = `
        <div class="mt-4 pt-4 border-t border-zinc-200 dark:border-zinc-900/50">
            <p class="text-[9px] font-black text-red-500 uppercase tracking-widest mb-2 flex items-center gap-1">
                <i data-lucide="shield-alert" class="w-3 h-3"></i> ${wl.key_risks || 'Key Risks'}
            </p>
            <div class="flex flex-wrap gap-1.5">${item.key_risks.map(riskTag).join('')}</div>
        </div>`;
    }

    // Meta row (R/R, confidence, horizon)
    const metaItems = [
        item.rr_ratio    ? `<div><span class="text-[8px] text-zinc-600 font-bold uppercase block">${wl.rr_label || 'R/R'}</span><span class="text-sm font-mono font-bold" style="color:var(--text-card-title)">${item.rr_ratio}x</span></div>` : '',
        item.avg_confidence ? `<div><span class="text-[8px] text-zinc-600 font-bold uppercase block">${wl.conf_label || 'Conf'}</span><span class="text-sm font-mono font-bold" style="color:var(--text-card-title)">${Math.round(item.avg_confidence * 100)}%</span></div>` : '',
        horizon ? `<div><span class="text-[8px] text-zinc-600 font-bold uppercase block">${wl.horizon_label || 'Horizon'}</span><span class="text-sm font-bold" style="color:var(--text-card-title)">${horizon}</span></div>` : '',
        item.position_pct != null && item.position_pct > 0 ? `<div><span class="text-[8px] text-zinc-600 font-bold uppercase block">${wl.size_label || 'Size'}</span><span class="text-sm font-mono font-bold" style="color:var(--text-card-title)">${Math.round(item.position_pct * 100)}%</span></div>` : '',
    ].filter(Boolean).join('');

    const statusGlow = isExecute ? 'glow-green' : '';

    return `
    <div class="glass-card p-6 flex flex-col gap-0 ${statusGlow} hover:border-zinc-500/50 transition-all">
        <!-- Header -->
        <div class="flex justify-between items-start mb-4">
            <div>
                <h4 class="text-3xl font-black tracking-tighter" style="color:var(--text-card-title)">${item.ticker}</h4>
                <p class="text-[10px] text-zinc-500 font-mono">${item.time}</p>
            </div>
            <div class="flex flex-col items-end gap-2">
                <span class="px-2 py-1 rounded text-[10px] font-black border"
                    style="background:color-mix(in srgb,${statusColor},transparent 90%);border-color:color-mix(in srgb,${statusColor},transparent 75%);color:${statusColor}">
                    ${status}
                </span>
                ${item.da_filed ? `<span class="text-[8px] px-1.5 py-0.5 rounded bg-violet-500/10 text-violet-400 border border-violet-500/20 font-bold">${wl.da_filed || 'DA Filed'}</span>` : ''}
            </div>
        </div>

        ${badgesHtml ? `<div class="flex flex-wrap gap-1.5 mb-3">${badgesHtml}</div>` : ''}

        <!-- Score + Meta -->
        <div class="flex items-end justify-between mb-2">
            <div>
                <p class="text-[9px] text-zinc-500 font-bold uppercase tracking-widest mb-1">${wl.model_score || 'Model Score'}</p>
                <p class="text-4xl font-bold tracking-tighter" style="color:var(--text-card-title)">${item.score}</p>
            </div>
            <div class="flex gap-4">${metaItems}</div>
        </div>

        ${targetHtml}
        ${dualTrackHtml}
        ${livePosHtml}
        ${condHtml}
        ${risksHtml}

        <!-- Footer -->
        <div class="mt-4 pt-3 border-t border-zinc-200 dark:border-zinc-900/50 flex justify-end gap-2">
            <button onclick="copyFlashPrompt('${item.ticker}')"
                class="flex items-center gap-1.5 text-[10px] font-bold px-3 py-1.5 rounded-lg border border-zinc-200 dark:border-zinc-800 hover:bg-blue-500 hover:text-black hover:border-blue-500 transition-all" title="Run news FLASH for ${item.ticker}">
                <i data-lucide="newspaper" class="w-3 h-3"></i> ${wl.flash_btn || 'FLASH'}
            </button>
            <button onclick="openPositionModal('${item.ticker}')"
                class="flex items-center gap-1.5 text-[10px] font-bold px-3 py-1.5 rounded-lg border border-zinc-200 dark:border-zinc-800 hover:bg-emerald-500 hover:text-black hover:border-emerald-500 transition-all">
                <i data-lucide="plus" class="w-3 h-3"></i> ${(t.positions?.add_btn || '+ Add').replace(/^\+\s*/, '')}
            </button>
            <button onclick="viewReport('${item.report_url}')"
                class="flex items-center gap-2 text-[10px] font-bold px-3 py-1.5 rounded-lg border border-zinc-200 dark:border-zinc-800 hover:bg-emerald-500 hover:text-black hover:border-emerald-500 transition-all">
                <i data-lucide="file-text" class="w-3 h-3"></i> ${wl.view_report || 'View Report'}
            </button>
        </div>
    </div>`;
}

async function goFlash(ticker) {
    const isZh = UI.currentLang === 'zh';
    const confirmMsg = isZh
        ? `透過 Claude 執行「新聞分析 FLASH ${ticker}」？（約 2-3 分鐘，消耗 tokens）`
        : `Run "FLASH ${ticker}" via Claude? (~2-3 min, consumes tokens)`;
    if (!confirm(confirmMsg)) return;
    try {
        const res = await fetch('/api/run-protocol', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name: 'flash', ticker: ticker.toUpperCase() }),
        });
        if (!res.ok) {
            const err = await res.json().catch(() => ({ error: res.statusText }));
            throw new Error(err.error || `HTTP ${res.status}`);
        }
        window.location.href = `news.html?running=flash&ticker=${encodeURIComponent(ticker)}`;
    } catch (e) {
        UI.showToast(e.message, 'error', 5000);
    }
}
window.copyFlashPrompt = goFlash;

function renderCards(filter) {
    const grid     = document.getElementById('watchlist-grid');
    const posCont  = document.getElementById('positions-table-container');
    const all      = window._allAnalysis || [];
    const watched  = window._watchlistData || [];
    const positions = window._positionsFlat || [];

    // Positions tab → flat table, hide the grid
    if (filter === 'positions') {
        grid.classList.add('hidden');
        posCont.classList.remove('hidden');
        renderPositionsTable(positions);
        return;
    }
    grid.classList.remove('hidden');
    posCont.classList.add('hidden');

    let source, filtered;
    if (filter === 'historical') {
        source = all;                                      // include CANCEL/ARCHIVE
        filtered = source;
    } else if (filter === 'execute') {
        source = watched;
        filtered = source.filter(i => i.decision === 'EXECUTE' || i.decision === 'BUY');
    } else if (filter === 'waiting') {
        source = watched;
        filtered = source.filter(i =>
            i.decision === 'STAGED' || i.decision === 'STAGED_ENTRY'
            || i.final_decision === 'STAGED_ENTRY'
            || i.watch_conditions
            || (i.targets?.watch && !isActiveDecision(i.decision))
        );
    } else {  // all
        source = watched;
        filtered = source;
    }

    if (!filtered.length) {
        const noItems = (window.i18n?.[UI.currentLang]?.watchlist?.no_items) || 'No items match this filter.';
        grid.innerHTML = `<div class="col-span-full py-20 text-center text-zinc-600">${noItems}</div>`;
        return;
    }
    grid.innerHTML = filtered.map(buildCard).join('');
    lucide.createIcons();
}

// ── Positions Table (flat, cross-ticker) ──────────────────────
let _showClosed = false;
function renderPositionsTable(lots) {
    const cont = document.getElementById('positions-table-container');
    const t    = window.i18n?.[UI.currentLang] || {};
    const pos  = t.positions || {};
    if (!lots.length) {
        cont.innerHTML = `<div class="glass-card p-20 text-center text-zinc-600">${pos.no_positions || 'No positions recorded yet. Click "Add Position" to start tracking.'}</div>`;
        return;
    }

    // Sort by ticker, then entry_date desc; filter closed unless toggled on
    const visible = lots.filter(l => _showClosed || l.status !== 'closed');
    const sorted = [...visible].sort((a, b) => {
        if (a.ticker !== b.ticker) return a.ticker.localeCompare(b.ticker);
        return b.entry_date.localeCompare(a.entry_date);
    });

    // Open/active aggregation
    const open = lots.filter(l => l.status !== 'closed');
    const totalCost = open.reduce((s, l) => s + (l.cost_basis || 0), 0);
    const totalUPL  = open.reduce((s, l) => s + (l.unrealized_pl || 0), 0);
    const totalPct  = totalCost ? (totalUPL / totalCost) * 100 : 0;
    const totalColor = totalUPL >= 0 ? 'var(--status-bullish)' : 'var(--status-bearish)';

    // Realized aggregation across all (closed + trimmed lots)
    const totalRealized = lots.reduce((s, l) => s + (l.realized_pl || 0), 0);
    const realizedColor = totalRealized >= 0 ? 'var(--status-bullish)' : 'var(--status-bearish)';
    const closedCount = lots.filter(l => l.status === 'closed').length;

    const statusLabel = (s) => {
        const k = `status_${s || 'open'}`;
        return pos[k] || s || 'open';
    };
    const statusColor = (s) => s === 'closed' ? 'var(--text-muted)'
                             : s === 'trimmed' ? 'var(--status-binary)'
                             : 'var(--status-bullish)';
    const trackLabel = (tr) => pos[`track_${tr}`] || tr || 'manual';

    const rows = sorted.map(l => {
        const isClosed = l.status === 'closed';
        const plColor = (l.unrealized_pct ?? 0) >= 0 ? 'var(--status-bullish)' : 'var(--status-bearish)';
        const plSign  = (l.unrealized_pct ?? 0) >= 0 ? '+' : '';
        const rpColor = (l.realized_pl ?? 0) >= 0 ? 'var(--status-bullish)' : 'var(--status-bearish)';
        const rpSign  = (l.realized_pl ?? 0) >= 0 ? '+' : '';
        const trackColor = l.track === 'aggressive' ? 'var(--status-bullish)'
                         : l.track === 'conservative' ? 'var(--status-binary)'
                         : 'var(--text-muted)';
        const stColor = statusColor(l.status);
        return `
        <tr class="border-t border-zinc-200 dark:border-zinc-800/50 hover:bg-zinc-50 dark:hover:bg-zinc-900/30 transition-all ${isClosed ? 'opacity-60' : ''}">
            <td class="px-3 py-3 font-mono font-bold text-sm" style="color:var(--text-card-title)">${l.ticker}</td>
            <td class="px-3 py-3 font-mono text-[11px] text-zinc-500">${l.entry_date}</td>
            <td class="px-3 py-3 font-mono text-xs text-right">${l.shares}</td>
            <td class="px-3 py-3 font-mono text-xs text-right">$${l.entry_price}</td>
            <td class="px-3 py-3 font-mono text-xs text-right text-zinc-500">$${l.cost_basis?.toLocaleString() || '–'}</td>
            <td class="px-3 py-3 font-mono text-xs text-right" style="color:var(--text-card-title)">${!isClosed && l.current_price ? '$'+l.current_price : '–'}</td>
            <td class="px-3 py-3 font-mono text-xs text-right font-bold" style="color:${plColor}">
                ${!isClosed && l.unrealized_pct != null ? `${plSign}${l.unrealized_pct}%` : '–'}
            </td>
            <td class="px-3 py-3 font-mono text-xs text-right font-bold" style="color:${plColor}">
                ${!isClosed && l.unrealized_pl != null ? `${plSign}$${Math.abs(l.unrealized_pl).toLocaleString()}` : '–'}
            </td>
            <td class="px-3 py-3 font-mono text-xs text-right font-bold" style="color:${rpColor}">
                ${l.realized_pl != null ? `${rpSign}$${Math.abs(l.realized_pl).toLocaleString()}` : '–'}
            </td>
            <td class="px-3 py-3">
                <span class="text-[8px] font-black uppercase tracking-widest px-1.5 py-0.5 rounded border"
                      style="color:${stColor};border-color:color-mix(in srgb,${stColor},transparent 65%);background:color-mix(in srgb,${stColor},transparent 88%)">
                    ${statusLabel(l.status)}
                </span>
            </td>
            <td class="px-3 py-3">
                <span class="text-[8px] font-black uppercase tracking-widest px-1.5 py-0.5 rounded border"
                      style="color:${trackColor};border-color:color-mix(in srgb,${trackColor},transparent 65%);background:color-mix(in srgb,${trackColor},transparent 88%)">
                    ${trackLabel(l.track)}
                </span>
            </td>
            <td class="px-3 py-3 text-[10px] text-zinc-500 italic max-w-[200px] truncate" title="${l.notes || ''}">${l.notes || ''}</td>
            <td class="px-3 py-3 text-right whitespace-nowrap">
                ${!isClosed ? `<button onclick="openClosePositionModal('${l.id}')" class="text-amber-500 hover:text-amber-400 text-[10px] font-black uppercase tracking-widest px-2 py-1 rounded border border-amber-500/30 hover:border-amber-500 transition-all mr-1" title="${pos.close_btn || 'Close'}">
                    ${pos.close_btn || 'CLOSE'}
                </button>` : ''}
                <button onclick="deletePosition('${l.id}')" class="text-zinc-500 hover:text-red-400 text-xs font-bold transition-all" title="${pos.delete || 'Delete'}">
                    <i data-lucide="trash-2" class="w-3.5 h-3.5"></i>
                </button>
            </td>
        </tr>`;
    }).join('');

    cont.innerHTML = `
    <div class="glass-card overflow-hidden">
        <div class="flex items-center justify-between px-5 py-4 border-b border-zinc-200 dark:border-zinc-800/50">
            <div class="flex items-center gap-2">
                <i data-lucide="wallet" class="w-4 h-4 text-emerald-500"></i>
                <h3 class="text-sm font-bold" style="color:var(--text-card-title)">${pos.portfolio_title || (UI.currentLang === 'zh' ? '投資組合' : 'Portfolio')}</h3>
                <span class="text-[10px] text-zinc-500">${lots.length} ${pos.lots || 'lots'}</span>
            </div>
            <div class="flex items-center gap-6">
                <div>
                    <div class="text-[9px] text-zinc-500 font-bold uppercase tracking-widest">${pos.total_cost || 'Total Cost'}</div>
                    <div class="text-sm font-mono font-bold" style="color:var(--text-card-title)">$${totalCost.toLocaleString()}</div>
                </div>
                <div>
                    <div class="text-[9px] text-zinc-500 font-bold uppercase tracking-widest">${pos.total_upl || 'Unrealized P/L'}</div>
                    <div class="text-sm font-mono font-black" style="color:${totalColor}">
                        ${totalUPL >= 0 ? '+' : ''}$${Math.abs(Math.round(totalUPL)).toLocaleString()}
                        <span class="text-[10px] ml-1">(${totalUPL >= 0 ? '+' : ''}${totalPct.toFixed(2)}%)</span>
                    </div>
                </div>
                <div>
                    <div class="text-[9px] text-zinc-500 font-bold uppercase tracking-widest">${pos.total_realized || 'Realized P/L'}</div>
                    <div class="text-sm font-mono font-black" style="color:${realizedColor}">
                        ${totalRealized >= 0 ? '+' : ''}$${Math.abs(Math.round(totalRealized)).toLocaleString()}
                    </div>
                </div>
                ${closedCount > 0 ? `
                <label class="flex items-center gap-2 text-[10px] text-zinc-500 font-bold uppercase tracking-widest cursor-pointer">
                    <input type="checkbox" id="show-closed-toggle" ${_showClosed ? 'checked' : ''} class="accent-emerald-500">
                    ${pos.show_closed || 'Show Closed'} (${closedCount})
                </label>` : ''}
            </div>
        </div>
        <div class="overflow-x-auto">
            <table class="w-full text-xs">
                <thead>
                    <tr class="text-[9px] font-black uppercase tracking-widest text-zinc-500 bg-zinc-50 dark:bg-zinc-900/30">
                        <th class="px-3 py-2 text-left">${pos.ticker || 'Ticker'}</th>
                        <th class="px-3 py-2 text-left">${pos.entry_date || 'Date'}</th>
                        <th class="px-3 py-2 text-right">${pos.shares || 'Shares'}</th>
                        <th class="px-3 py-2 text-right">${pos.entry_price || 'Entry'}</th>
                        <th class="px-3 py-2 text-right">${pos.cost_col || 'Cost'}</th>
                        <th class="px-3 py-2 text-right">${pos.current || 'Current'}</th>
                        <th class="px-3 py-2 text-right">${pos.pct_col || '%'}</th>
                        <th class="px-3 py-2 text-right">${pos.upl || 'U/L'}</th>
                        <th class="px-3 py-2 text-right">${pos.realized_pl || 'Realized'}</th>
                        <th class="px-3 py-2 text-left">${pos.status_col || 'Status'}</th>
                        <th class="px-3 py-2 text-left">${pos.track || 'Track'}</th>
                        <th class="px-3 py-2 text-left">${pos.notes || 'Notes'}</th>
                        <th class="px-3 py-2 text-right"></th>
                    </tr>
                </thead>
                <tbody>${rows}</tbody>
            </table>
        </div>
    </div>`;
    lucide.createIcons();
    const tgl = document.getElementById('show-closed-toggle');
    if (tgl) tgl.addEventListener('change', e => {
        _showClosed = e.target.checked;
        renderPositionsTable(window._positionsFlat || []);
    });
}

// ── Load ───────────────────────────────────────────────────────
async function loadWatchlist() {
    logToUI('Loading decisions data...');
    try {
        const data = await DataStore.get(true);   // force fresh read after mutations
        document.getElementById('last-update').textContent = `SYNC: ${data.last_updated}`;

        const allAnalysis = data.recent_analysis || [];
        const watchItems  = allAnalysis.filter(a => a.on_watchlist);
        const positions   = data.positions || [];

        window._allAnalysis   = allAnalysis;
        window._watchlistData = watchItems;
        window._positionsFlat = positions;

        // Summary counts (based on watchlist subset)
        const execCount = watchItems.filter(a => a.decision === 'EXECUTE' || a.decision === 'BUY').length;
        const waitCount = watchItems.filter(a =>
            a.decision === 'STAGED' || a.decision === 'STAGED_ENTRY'
            || a.final_decision === 'STAGED_ENTRY'
            || a.watch_conditions
            || (a.targets?.watch && !isActiveDecision(a.decision))
        ).length;
        document.getElementById('count-execute').textContent = execCount;
        document.getElementById('count-waiting').textContent = waitCount;

        const validConf = watchItems.filter(a => a.avg_confidence != null);
        document.getElementById('avg-conf').textContent = validConf.length
            ? Math.round(validConf.reduce((s, a) => s + a.avg_confidence, 0) / validConf.length * 100) + '%'
            : '–';

        const validRR = watchItems.filter(a => a.rr_ratio != null);
        document.getElementById('avg-rr').textContent = validRR.length
            ? (validRR.reduce((s, a) => s + a.rr_ratio, 0) / validRR.length).toFixed(2) + 'x'
            : '–';

        renderCards(activeFilter);
        logToUI(`Decisions loaded: ${allAnalysis.length} analyses, ${watchItems.length} watched, ${positions.length} position lots`);
    } catch (e) {
        logToUI(e.message, 'error');
        document.getElementById('watchlist-grid').innerHTML =
            `<div class="col-span-full glass-card p-10 text-center text-red-500">${e.message}</div>`;
    }
}

document.getElementById('refresh-btn').addEventListener('click', loadWatchlist);
UI.boot('decisions', { translate: applyTranslations, reload: loadWatchlist });
loadWatchlist();

// ── Position modal wiring ──────────────────────────────────────
document.getElementById('add-position-btn').addEventListener('click', () => openPositionModal());
document.getElementById('close-position-modal').addEventListener('click', closePositionModal);
document.getElementById('pf-cancel').addEventListener('click', closePositionModal);
document.getElementById('position-form').addEventListener('submit', submitPositionForm);

// Close-position modal wiring
document.getElementById('close-exit-modal').addEventListener('click', closeExitModal);
document.getElementById('cf-cancel').addEventListener('click', closeExitModal);
document.getElementById('close-form').addEventListener('submit', submitCloseForm);
document.getElementById('close-form').addEventListener('input', updateClosePreview);

document.addEventListener('keydown', e => {
    if (e.key === 'Escape') { closePositionModal(); closeExitModal(); }
});

// ── Refresh countdown ring ─────────────────────────────────────
const REFRESH_RING_CIRC = 100.53;   // 2π × r (r=16)

async function updateRefreshStatus() {
    try {
        const res = await fetch('/api/refresh_status');
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const s = await res.json();

        const now       = Date.now();
        const nextMs    = s.next_scheduled ? new Date(s.next_scheduled).getTime() : 0;
        const intervalS = s.refresh_interval_sec || 300;
        const intervalMs = intervalS * 1000;
        const remainMs  = Math.max(0, nextMs - now);
        // progress: 1.0 = just refreshed (full ring), 0.0 = about to refresh (empty ring)
        const progress  = nextMs ? Math.min(1, remainMs / intervalMs) : 0;

        const ring        = document.getElementById('refresh-ring');
        const countdown   = document.getElementById('refresh-countdown');
        const container   = document.getElementById('refresh-status');
        if (!ring || !countdown || !container) return;

        // Ring fill amount
        ring.style.strokeDashoffset = (REFRESH_RING_CIRC * (1 - progress)).toFixed(2);

        // Countdown label (mm:ss or ss)
        const m   = Math.floor(remainMs / 60000);
        const sec = Math.floor((remainMs % 60000) / 1000);
        countdown.textContent = m > 0 ? `${m}:${String(sec).padStart(2,'0')}` : `${sec}s`;

        // Ring color by state
        let color;
        if (s.in_progress)      color = '#a78bfa';  // purple — running
        else if (s.last_error)  color = '#ef4444';  // red — last run failed
        else if (s.last_ok)     color = '#22c55e';  // green — healthy
        else                    color = '#71717a';  // grey — no data yet
        ring.setAttribute('stroke', color);

        // Tooltip
        const lines = [];
        if (s.last_ok)        lines.push(`✓ Last OK: ${s.last_ok}`);
        if (s.last_error)     lines.push(`✗ Last error: ${s.last_error.slice(0, 180)}`);
        if (s.last_reason)    lines.push(`Reason: ${s.last_reason}`);
        if (s.next_scheduled) lines.push(`Next: ${s.next_scheduled}`);
        lines.push(`Interval: ${intervalS}s`);
        if (s.in_progress)    lines.push(`(Running…)`);
        container.title = lines.join('\n');
    } catch (e) {
        const container = document.getElementById('refresh-status');
        if (container) container.title = `refresh_status fetch error: ${e.message}`;
    }
}

updateRefreshStatus();
setInterval(updateRefreshStatus, 1000);
