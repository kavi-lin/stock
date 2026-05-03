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

    // V1.74 cmdbar i18n
    const dc = t.decisions || {};
    const setText = (id, val) => { const el = document.getElementById(id); if (el && val) el.textContent = val; };
    document.querySelectorAll('[data-i18n="decisions.cmdbar_run"]').forEach(el => {
        if (dc.cmdbar_run) el.textContent = dc.cmdbar_run;
    });
    document.querySelectorAll('[data-i18n="decisions.cmdbar_recent_label"]').forEach(el => {
        if (dc.cmdbar_recent_label) el.textContent = dc.cmdbar_recent_label;
    });
    document.querySelectorAll('[data-i18n="decisions.cmdbar_risk_hint"]').forEach(el => {
        if (dc.cmdbar_risk_hint) el.textContent = dc.cmdbar_risk_hint;
    });
    const dcInput = document.getElementById('dc-ticker-input');
    if (dcInput && dc.cmdbar_placeholder) dcInput.placeholder = dc.cmdbar_placeholder;
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
        awaitBridgeAndReload();
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
        awaitBridgeAndReload();
    } catch (err) {
        alert(`Delete failed: ${err.message}`);
    }
}

// Wait until dashboard_server's bridge.py run finishes (it's spawned async on every
// positions.json mutation), THEN reload the component. Replaces the old fixed-1500ms
// setTimeout race that silently failed when bridge.py took longer than 1.5s.
async function awaitBridgeAndReload() {
    const startTs  = Date.now();
    const deadline = startTs + 15000;  // 15s cap — bridge can take 3-8s
    // First wait briefly for bridge thread to start (it's launched async server-side)
    await new Promise(res => setTimeout(res, 400));
    while (Date.now() < deadline) {
        try {
            const r = await fetch('/api/refresh_status');
            if (r.ok) {
                const s = await r.json();
                // Wait until bridge is no longer running AND last_ok is after our mutation
                if (!s.in_progress && s.last_ok) {
                    const lastOkTs = new Date(s.last_ok).getTime();
                    if (lastOkTs >= startTs) break;
                }
            }
        } catch {}
        await new Promise(res => setTimeout(res, 300));
    }
    await loadWatchlist();
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
        awaitBridgeAndReload();
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
let searchQuery = '';
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
document.getElementById('ticker-search').addEventListener('input', e => {
    searchQuery = e.target.value.trim().toUpperCase();
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
    // Title-case latin words but leave CJK / punctuation intact.
    // `\b\w` matches word boundaries which include CJK transitions, so we limit
    // to ASCII via [a-zA-Z] to avoid accidentally lowercasing the rest of a long
    // mixed-language risk (e.g. "FRED Overheating + sector_rotation_avoid …").
    const clean = risk.replace(/_/g, ' ').replace(/\b[a-zA-Z]/g, c => c.toUpperCase());
    // Long risks (e.g. multi-clause sector rotation reasons) must wrap inside
    // the pill — `whitespace-nowrap` previously caused overflow past the card.
    return `<span class="text-[9px] font-bold px-2 py-0.5 rounded bg-red-500/10 text-red-400 border border-red-500/20 leading-relaxed max-w-full break-words">${clean}</span>`;
}

function conditionRow(label, text, color = 'var(--status-bullish)') {
    // Stacked layout: label on its own line (supports long keys like BREAKOUT_UP/CATALYST_MISS)
    return `
    <div class="mb-1.5 last:mb-0">
        <div class="text-[9px] font-black uppercase tracking-widest leading-tight" style="color:${color}">${label}</div>
        <div class="text-[10px] leading-relaxed mt-0.5" style="color:var(--text-main)">${text}</div>
    </div>`;
}

// Build ticker→GICS-sector map from momentum_screen data (S&P 500 only).
// Populated by loadWatchlist(); used to show sector subscript on each card.
let _tickerSectorMap = {};
function sectorBadgeLabel(gics) {
    if (!gics) return '';
    const m = window.i18n?.[UI.currentLang]?.momentum?.sectors_map || {};
    return m[gics] || gics;
}

/* ── Rich pill tooltips (matches sector page #pill-tooltip pattern) ─── */
const DECISION_TIPS = {
    tp_sl: {
        zh: {
            title: '止盈 / 止損 · 出場目標',
            desc: 'TP 觸及代表 thesis 兌現、部分或全部出場；SL 觸及代表 thesis 失敗、無條件出場。R/R = (TP − 進場) ÷ (進場 − SL)，越大代表潛在報酬相對於風險越值得。',
            scale: '🟢 TP (Take Profit / 止盈) — 目標價，觸及後出場\n🔴 SL (Stop Loss / 止損) — 停損價，跌破無條件出場',
        },
        en: {
            title: 'Take Profit / Stop Loss · Exit Targets',
            desc: 'TP confirms thesis works → exit (full or partial). SL means thesis broke → unconditional exit. R/R = (TP − entry) ÷ (entry − SL), the higher the better.',
            scale: '🟢 TP (Take Profit) — target hit → exit\n🔴 SL (Stop Loss) — price breached → cut',
        },
    },
    dual_track: {
        zh: {
            title: '雙軌進場 (Dual-Track Entry)',
            desc: '把建倉拆兩段下，避免 timing 全押單一價位。同時保有趨勢敞口與回測機會。',
            scale: '🟢 AGG (積極) — 上半段先進，搶趨勢\n🟡 CONS (保守) — 下半段等回測或更好價位',
        },
        en: {
            title: 'Dual-Track Entry',
            desc: 'Split the position in two so timing is not bet on one price. Captures trend exposure plus retest opportunity.',
            scale: '🟢 AGG (Aggressive) — upper half, chases trend\n🟡 CONS (Conservative) — lower half, waits for retest',
        },
    },
    da_filed: {
        zh: {
            title: '反向論點已提交 (DA Filed)',
            desc: '投資長啟動 Devils Advocate 流程，書面記錄反對 thesis 的論述。代表決策經過刻意挑戰，是 quality flag。',
            scale: '⚖ 觸發條件：final_score 靠近邊界 OR 共識過於一致時強制提交',
        },
        en: {
            title: 'Devils Advocate Filed',
            desc: "PM officially logged a written counter-thesis. Quality flag — decision survived deliberate challenge.",
            scale: '⚖ Triggered when final_score near boundary OR consensus too uniform',
        },
    },
    contrarian: {
        zh: {
            title: '逆勢訊號 (Contrarian)',
            desc: '此分析違反當下 macro regime（如 RISK_OFF 仍 BUY、或多頭轉折時 SELL）。需特別小心 thesis 假設與 macro 條件的相容性。',
            scale: '🎯 CONTRARIAN：方向 ≠ macro_alignment\n✅ ALIGNED：方向跟大環境一致（不顯示 badge）',
        },
        en: {
            title: 'Contrarian Signal',
            desc: 'Analysis runs against current macro regime (e.g. BUY in RISK_OFF). Watch thesis assumptions vs macro context carefully.',
            scale: '🎯 CONTRARIAN: direction ≠ macro_alignment\n✅ ALIGNED: matches macro (no badge shown)',
        },
    },
    pos_binary: {
        zh: {
            title: '正向二元事件 (Positive Binary)',
            desc: '48 小時內有確定的正向 catalyst（財報、法規裁決、併購投票等）。預期結果落地會大幅推升價格，倉位可較積極，但需準備錯邊的對沖。',
        },
        en: {
            title: 'Positive Binary Catalyst',
            desc: 'Confirmed positive catalyst within 48h (earnings / ruling / M&A vote). Outcome likely drives price up — sizing can be more aggressive, but hedge for wrong-side risk.',
        },
    },
    neg_binary: {
        zh: {
            title: '負向二元事件 (Negative Binary)',
            desc: '48 小時內有確定下行 catalyst。建議嚴控倉位、考慮避開直到事件落地、或用 protective put 對沖。',
        },
        en: {
            title: 'Negative Binary Catalyst',
            desc: 'Confirmed downside catalyst within 48h. Tighten size, consider waiting it out, or use protective puts.',
        },
    },
    consensus: {
        zh: {
            title: '共識加權 ×1.15',
            desc: '四個分析師（Bull / Bear / Sector / Macro）方向一致 → 模型分數 ×1.15 加權，提高決策信心。',
            scale: 'V4.7+：需通過 Red Team 審核才會啟用',
        },
        en: {
            title: 'Consensus Bonus ×1.15',
            desc: 'All 4 analysts (Bull/Bear/Sector/Macro) align → score multiplied by 1.15 for higher confidence.',
            scale: 'V4.7+: gated by Red Team review',
        },
    },
    fragility_robust: {
        zh: {
            title: '論點穩健度：穩健',
            desc: 'Tail-risk 三維評估：論點建立在多支柱（基本面 + 技術 + 估值）之上，容忍負面驚奇能力高。可採標準倉位上限。',
            scale: '🟢 ROBUST  穩健 — 多支柱 thesis\n🟡 MODERATE 中等脆弱 — 對特定變數敏感\n🔴 FRAGILE  脆弱 — 高度依賴單一 narrative',
        },
        en: {
            title: 'Thesis Fragility: Robust',
            desc: 'Tail-risk 3-dim assessment: thesis stands on multiple pillars (fundamentals + technical + valuation), high tolerance to negative surprises. Standard sizing cap OK.',
            scale: '🟢 ROBUST    multi-pillar\n🟡 MODERATE  sensitive to certain vars\n🔴 FRAGILE   single-narrative dependence',
        },
    },
    fragility_moderate: {
        zh: {
            title: '論點穩健度：中等脆弱',
            desc: 'Tail-risk 三維評估：論點對部分變數敏感，少數負面 catalyst 即可動搖。建議倉位降一檔。',
            scale: '🟢 ROBUST  穩健 — 多支柱 thesis\n🟡 MODERATE 中等脆弱 — 對特定變數敏感\n🔴 FRAGILE  脆弱 — 高度依賴單一 narrative',
        },
        en: {
            title: 'Thesis Fragility: Moderate',
            desc: 'Tail-risk 3-dim assessment: thesis sensitive to certain variables; minor negative catalyst can shake R/R. Reduce sizing one notch.',
            scale: '🟢 ROBUST    multi-pillar\n🟡 MODERATE  sensitive to certain vars\n🔴 FRAGILE   single-narrative dependence',
        },
    },
    fragility_fragile: {
        zh: {
            title: '論點穩健度：脆弱',
            desc: 'Tail-risk 三維評估：論點高度依賴單一驅動或 narrative，一個負面驚奇就會大幅減損 R/R。倉位需大砍，或考慮先觀望。',
            scale: '🟢 ROBUST  穩健 — 多支柱 thesis\n🟡 MODERATE 中等脆弱 — 對特定變數敏感\n🔴 FRAGILE  脆弱 — 高度依賴單一 narrative',
        },
        en: {
            title: 'Thesis Fragility: Fragile',
            desc: 'Tail-risk 3-dim: thesis hinges on single driver / narrative — one negative surprise materially impairs R/R. Cut sizing significantly, or consider waiting.',
            scale: '🟢 ROBUST    multi-pillar\n🟡 MODERATE  sensitive to certain vars\n🔴 FRAGILE   single-narrative dependence',
        },
    },
    phase2_fanout: {
        zh: {
            title: 'Phase 2 fanout 降級',
            desc: 'Parallel subagent 多 lane 平行分析有部分沒跑完（PARTIAL_FALLBACK 或 FULL_FALLBACK）。最終分數的多視角驗證減弱，宜降低信心。',
        },
        en: {
            title: 'Phase 2 Fanout Degraded',
            desc: "Parallel subagent fanout did not fully complete (PARTIAL/FULL_FALLBACK). Final score lacks full multi-viewpoint validation — discount confidence.",
        },
    },
    degraded_lanes: {
        zh: {
            title: 'Lane 降級警告',
            desc: '部分分析師 lane 沒跑成（fallback 或 timeout），最終分數可能少了 1-2 視角的權重。',
        },
        en: {
            title: 'Degraded Analyst Lanes',
            desc: 'One or more analyst lanes failed or fell back. Final score may lack 1-2 viewpoints\' weight.',
        },
    },
    burry_override: {
        zh: {
            title: 'Burry 覆寫啟動',
            desc: 'Burry 模型（深度價值）推翻共識 BUY → 自動把倉位砍半，並在指定交易日後重新檢視。代表基本面有重大警訊，不該滿倉進。',
        },
        en: {
            title: 'Burry Override Active',
            desc: 'Burry deep-value model overrode consensus BUY — position halved with mandatory recheck date. Indicates major fundamental flag.',
        },
    },
};

(function initDecisionTip() {
    const tip = document.getElementById('decision-tip');
    if (!tip) return;
    if (tip._init) return;
    tip._init = true;
    let _hideTimer = null;

    function showTip(el) {
        const key = el.dataset.tipKey;
        const lang = (typeof UI !== 'undefined' && UI.currentLang === 'en') ? 'en' : 'zh';
        const data = DECISION_TIPS[key]?.[lang];
        if (!data) return;
        let html = `<div class="tip-title">${data.title}</div>`;
        html += `<div class="tip-desc">${data.desc}</div>`;
        if (data.scale) html += `<div class="tip-scale">${data.scale}</div>`;
        tip.innerHTML = html;
        tip.style.opacity = '0';
        tip.style.top = '-9999px';
        tip.classList.add('tip-visible');
        requestAnimationFrame(() => {
            const rect  = el.getBoundingClientRect();
            const tRect = tip.getBoundingClientRect();
            const gap   = 8;
            let top  = rect.top - tRect.height - gap;
            if (top < 8) top = rect.bottom + gap;
            let left = rect.left + (rect.width - tRect.width) / 2;
            left = Math.max(8, Math.min(left, window.innerWidth - tRect.width - 8));
            tip.style.top  = top + 'px';
            tip.style.left = left + 'px';
            tip.style.opacity = '';
        });
    }
    function hideTip() { tip.classList.remove('tip-visible'); }

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

/* ── Version detection + UI helpers ─────────────────────────── */
function detectProtocolVersion(item) {
    // Trust bridge.py if it set protocol_version (from session_export_version)
    if (item.protocol_version && item.protocol_version !== 'legacy') {
        // Normalize: "V5.0" / "V4.8" / "V4.7" / "V4.6" / "V4.5" → keep as-is
        return String(item.protocol_version).toUpperCase();
    }
    // Fallback heuristic for older entries with no version stamp
    if (item.valuation_lane || item.fair_value_summary) return 'V5.0';
    if (item.degraded_analysts != null && item.phase2_fanout_mode) return 'V4.8';
    if (item.red_team_verdict) return 'V4.7';
    return 'LEGACY';
}

const VERSION_COLOR = {
    'V5.0':   { bg: 'rgba(16,185,129,0.18)',  border: 'rgba(16,185,129,0.55)',  fg: '#34d399', label: 'V5.0'   },
    'V4.8':   { bg: 'rgba(59,130,246,0.18)',  border: 'rgba(59,130,246,0.55)',  fg: '#60a5fa', label: 'V4.8'   },
    'V4.7':   { bg: 'rgba(245,158,11,0.18)',  border: 'rgba(245,158,11,0.55)',  fg: '#fbbf24', label: 'V4.7'   },
    'V4.6':   { bg: 'rgba(161,161,170,0.16)', border: 'rgba(161,161,170,0.45)', fg: '#a1a1aa', label: 'V4.6'   },
    'V4.5':   { bg: 'rgba(161,161,170,0.16)', border: 'rgba(161,161,170,0.45)', fg: '#a1a1aa', label: 'V4.5'   },
    'LEGACY': { bg: 'rgba(82,82,91,0.18)',    border: 'rgba(82,82,91,0.45)',    fg: '#71717a', label: 'ARCHIVE'},
};

function buildVersionBookmark(version) {
    const c = VERSION_COLOR[version] || VERSION_COLOR['LEGACY'];
    return `
    <div class="version-bookmark" title="Protocol ${c.label}"
         style="position:absolute; top:0; right:8px; z-index:2;
                padding:2px 7px 3px; font-size:8px; font-weight:800; letter-spacing:0.06em;
                border:1px solid ${c.border}; border-top:0;
                border-bottom-left-radius:5px; border-bottom-right-radius:5px;
                background:${c.bg}; color:${c.fg};
                box-shadow: 0 1px 3px rgba(0,0,0,0.2); opacity: 0.85;">
        ${c.label}
    </div>`;
}

/* ── V5.0 — Valuation Lane + Fair Value Summary ──────────────── */
const ANCHOR_INFO = {
    dcf_unlevered: {
        label: 'DCF-U',
        tip_zh: '無槓桿 DCF — Unlevered Free Cash Flow 折現後減淨債務',
        tip_en: 'Unlevered DCF — UFCF discounted, then minus net debt',
    },
    dcf_levered: {
        label: 'DCF-L',
        tip_zh: '有槓桿 DCF — 直接折現 Levered FCF',
        tip_en: 'Levered DCF — direct LFCF discount',
    },
    analyst_pt_consensus: {
        label: 'Analyst PT',
        tip_zh: '賣方分析師 12 個月目標價共識（FMP）',
        tip_en: '12-month sell-side analyst price target consensus (FMP)',
    },
    peer_pe_implied: {
        label: 'Peer P/E',
        tip_zh: '同業中位數 P/E × ticker EPS',
        tip_en: 'Peer-group median P/E × ticker EPS',
    },
    owner_earnings_mult: {
        label: 'Owner E.',
        tip_zh: '巴菲特 Owner Earnings — (淨利 + 折舊 - 維持性 capex) × 倍數',
        tip_en: 'Buffett Owner Earnings — (NI + D&A − maintenance capex) × multiple',
    },
    forecaster_blend: {
        label: 'Forecaster',
        tip_zh: 'earnings-valuation-forecaster skill 的 12 個月 blended fair value',
        tip_en: '12-month blended fair value from earnings-valuation-forecaster skill',
    },
};

function buildV5ValuationBlock(item, wl) {
    const fvs = item.fair_value_summary;
    const lane = item.valuation_lane;
    if (!fvs && !lane) return '';
    const bandLabels = {
        extreme_undervalued: { fg: '#10b981', text: wl.fv_extreme_under   || '極度低估' },
        undervalued:         { fg: '#22c55e', text: wl.fv_undervalued     || '低估' },
        fairly_valued:       { fg: '#a1a1aa', text: wl.fv_fair            || '合理' },
        overvalued:          { fg: '#f97316', text: wl.fv_overvalued      || '高估' },
        extreme_overvalued:  { fg: '#ef4444', text: wl.fv_extreme_over    || '極度高估' },
    };
    const band = (fvs && fvs.verdict_band) ? (bandLabels[fvs.verdict_band] || { fg:'#a1a1aa', text: fvs.verdict_band }) : null;
    const fv   = fvs?.weighted_fair_value ?? lane?.weighted_fair_value;
    const pct  = fvs?.vs_current_pct ?? lane?.vs_current_pct;
    const conf = fvs?.confidence ?? lane?.confidence;
    const anchorCount = fvs?.anchors_available;
    const tipKey = (typeof UI !== 'undefined' && UI.currentLang === 'zh') ? 'tip_zh' : 'tip_en';
    const anchorChips = fvs?.anchors
        ? Object.entries(fvs.anchors).filter(([_, v]) => v != null)
              .map(([k, _]) => {
                  const info = ANCHOR_INFO[k] || { label: k, tip_zh: k, tip_en: k };
                  return `<span class="text-[10px] px-2.5 py-1 rounded-md bg-zinc-700/40 text-zinc-100 border border-zinc-500/40 font-mono" title="${escapeHtmlDc(info[tipKey])}">${info.label}</span>`;
              }).join(' ')
        : '';
    const pctStr = pct != null ? `${pct >= 0 ? '+' : ''}${Number(pct).toFixed(1)}%` : '--';
    const pctColor = pct == null ? '#a1a1aa' : (pct >= 0 ? '#22c55e' : '#ef4444');

    return `
    <div class="mt-4 pt-4 border-t border-zinc-200 dark:border-zinc-900/50">
        <p class="text-[10px] font-black uppercase tracking-widest mb-2 flex items-center gap-1" style="color:#34d399">
            <i data-lucide="scale" class="w-3 h-3"></i>
            ${wl.fv_block_title || 'Valuation · Fair Value'}
            ${band ? `<span class="ml-auto text-[9px] font-black px-1.5 py-0.5 rounded" style="background:color-mix(in srgb,${band.fg},transparent 85%);color:${band.fg};border:1px solid color-mix(in srgb,${band.fg},transparent 65%)">${band.text}</span>` : ''}
        </p>
        <div class="grid grid-cols-3 gap-2 mb-2">
            <div>
                <div class="text-[10px] text-zinc-300 font-bold uppercase tracking-wide">${wl.fv_fair_value || 'Fair Value'}</div>
                <div class="text-sm font-mono font-bold" style="color:var(--text-card-title)">${fv != null ? '$' + Number(fv).toFixed(2) : '--'}</div>
            </div>
            <div>
                <div class="text-[10px] text-zinc-300 font-bold uppercase tracking-wide">${wl.fv_vs_current || 'vs Current'}</div>
                <div class="text-sm font-mono font-bold" style="color:${pctColor}">${pctStr}</div>
            </div>
            <div>
                <div class="text-[10px] text-zinc-300 font-bold uppercase tracking-wide">${wl.fv_confidence || 'Confidence'}</div>
                <div class="text-sm font-bold capitalize" style="color:var(--text-card-title)">${conf || '--'}</div>
            </div>
        </div>
        ${anchorChips ? `<div class="flex flex-wrap gap-1.5 items-center">${anchorChips}${anchorCount != null ? `<span class="text-[10px] text-zinc-300 ml-1 font-mono">${anchorCount}/6</span>` : ''}</div>` : ''}
        ${fvs?.methodology_note ? `<div class="text-[10px] text-zinc-400 italic mt-2 leading-relaxed">${escapeHtmlDc(fvs.methodology_note)}</div>` : ''}
    </div>`;
}

/* ── V4.7+ — Red Team challenge block ───────────────────────── */
function buildRedTeamBlock(item, wl) {
    if (!item.red_team_verdict) return '';
    const verdictColor = {
        'NO_VIABLE_COUNTER': '#22c55e',
        'MODERATE_COUNTER':  '#eab308',
        'STRONG_COUNTER':    '#ef4444',
    };
    const fg = verdictColor[item.red_team_verdict] || '#a1a1aa';
    const verdictText = (wl[`rt_${item.red_team_verdict.toLowerCase()}`]) || item.red_team_verdict.replace(/_/g, ' ');
    const kill = item.red_team_kill || [];
    const thesis = item.red_team_thesis;
    const failed = item.red_team_failed;
    return `
    <div class="mt-4 pt-4 border-t border-zinc-200 dark:border-zinc-900/50">
        <p class="text-[9px] font-black uppercase tracking-widest mb-2 flex items-center gap-1" style="color:${fg}">
            <i data-lucide="swords" class="w-3 h-3"></i>
            ${wl.rt_block_title || 'Red Team Challenge'}
            <span class="ml-auto text-[8px] px-1.5 py-0.5 rounded" style="background:color-mix(in srgb,${fg},transparent 85%);color:${fg};border:1px solid color-mix(in srgb,${fg},transparent 65%)">${verdictText}</span>
        </p>
        ${failed ? `<div class="text-[9px] text-amber-600 dark:text-amber-400 mb-1.5">⚠ ${wl.rt_failed || 'Red Team execution degraded'}</div>` : ''}
        ${thesis ? `<details class="mb-1.5"><summary class="text-[11px] font-bold text-zinc-700 dark:text-zinc-300 cursor-pointer hover:text-zinc-900 dark:hover:text-zinc-100">${wl.rt_thesis || 'Counter thesis'}</summary><p class="text-[11px] mt-1 leading-relaxed" style="color:var(--text-main)">${escapeHtmlDc(thesis)}</p></details>` : ''}
        ${kill.length ? `<div><div class="text-[9px] font-black uppercase mb-1 text-zinc-700 dark:text-zinc-400">${wl.rt_kill || 'Kill conditions'}</div><ol class="text-[11px] list-decimal list-inside space-y-0.5 leading-relaxed" style="color:var(--text-main)">${kill.slice(0,3).map(k => `<li>${escapeHtmlDc(k)}</li>`).join('')}</ol></div>` : ''}
    </div>`;
}

/* ── V4.8 status pills (degraded analysts, fanout, burry override) ─── */
function buildV48StatusPills(item, wl) {
    const pills = [];
    const isZh = (typeof UI !== 'undefined' && UI.currentLang === 'zh');
    if (item.phase2_fanout_mode && item.phase2_fanout_mode !== 'PARALLEL_SUBAGENT') {
        pills.push(`<span class="text-[8px] px-1.5 py-0.5 rounded bg-amber-500/10 text-amber-600 dark:text-amber-400 border border-amber-500/30 font-bold" data-tip-key="phase2_fanout">⚠ ${item.phase2_fanout_mode.replace(/_/g,' ')}</span>`);
    }
    if (item.degraded_analysts && item.degraded_analysts.length) {
        pills.push(`<span class="text-[8px] px-1.5 py-0.5 rounded bg-amber-500/10 text-amber-600 dark:text-amber-400 border border-amber-500/30 font-bold" data-tip-key="degraded_lanes">⚠ ${wl.degraded_lanes || 'Degraded'}: ${item.degraded_analysts.length}</span>`);
    }
    if (item.burry_override) {
        const recheck = item.burry_recheck ? ` (recheck ${item.burry_recheck})` : '';
        pills.push(`<span class="text-[8px] px-1.5 py-0.5 rounded bg-purple-500/10 text-purple-600 dark:text-purple-400 border border-purple-500/30 font-bold" data-tip-key="burry_override">${wl.burry_override || 'BURRY OVERRIDE'}${recheck}</span>`);
    }
    if (item.fragility_label) {
        const fragColor = { ROBUST: '#22c55e', MODERATE: '#eab308', FRAGILE: '#ef4444', RESILIENT: '#22c55e' }[item.fragility_label] || '#a1a1aa';
        const fragLabelMap = isZh
            ? { ROBUST: '穩健', MODERATE: '中等脆弱', FRAGILE: '脆弱', RESILIENT: '穩健' }
            : { ROBUST: 'ROBUST', MODERATE: 'MODERATE', FRAGILE: 'FRAGILE', RESILIENT: 'RESILIENT' };
        const tipKey = (item.fragility_label === 'FRAGILE') ? 'fragility_fragile'
                      : (item.fragility_label === 'MODERATE') ? 'fragility_moderate'
                      : 'fragility_robust';
        const label = fragLabelMap[item.fragility_label] || item.fragility_label;
        pills.push(`<span class="text-[8px] px-1.5 py-0.5 rounded font-bold" data-tip-key="${tipKey}" style="background:color-mix(in srgb,${fragColor},transparent 88%);color:${fragColor};border:1px solid color-mix(in srgb,${fragColor},transparent 70%)">${label}</span>`);
    }
    // V2.10.0 — det_shadow polarization + agreement
    const ds = item.det_shadow || {};
    if (ds.signal_polarization === 'BIPOLAR') {
        const tip = isZh ? 'Lane 訊號兩極（強空＋強多並存）→ verdict 重跑會晃；不該重押任一邊'
                         : 'Lanes are extremely polarized (strong long + strong short coexist) → verdict will swing on rerun; avoid heavy sizing';
        pills.push(`<span class="text-[8px] px-1.5 py-0.5 rounded font-bold" title="${tip}" style="background:color-mix(in srgb,#a855f7,transparent 88%);color:#a855f7;border:1px solid color-mix(in srgb,#a855f7,transparent 70%)">${isZh ? '訊號兩極' : 'BIPOLAR'}</span>`);
    } else if (ds.signal_polarization === 'MIXED') {
        const tip = isZh ? 'Lane 訊號分歧（一正一負，未到極端）'
                         : 'Lanes mixed (some positive, some negative, less extreme)';
        pills.push(`<span class="text-[8px] px-1.5 py-0.5 rounded font-bold" title="${tip}" style="background:color-mix(in srgb,#0ea5e9,transparent 88%);color:#0ea5e9;border:1px solid color-mix(in srgb,#0ea5e9,transparent 70%)">${isZh ? '訊號分歧' : 'MIXED'}</span>`);
    }
    if (ds.red_team_agreement === 'DISAGREE') {
        const det = ds.red_team_verdict_det || '';
        const tip = isZh
            ? `LLM Red Team = ${item.red_team_verdict || 'N/A'}，但量化規則 = ${det}（${ds.red_team_detail?.kill_count ?? '?'} 條 kill trigger 觸發）→ LLM 比量化寬鬆，警覺`
            : `LLM=${item.red_team_verdict || 'N/A'} vs deterministic=${det} (${ds.red_team_detail?.kill_count ?? '?'} kill triggers) → LLM softer than rules`;
        pills.push(`<span class="text-[8px] px-1.5 py-0.5 rounded font-bold" title="${tip}" style="background:color-mix(in srgb,#f97316,transparent 88%);color:#f97316;border:1px solid color-mix(in srgb,#f97316,transparent 70%)">${isZh ? 'Red Team 不一致' : 'RT DISAGREE'}</span>`);
    }
    if (ds.val_agreement === 'DISAGREE') {
        const llm = item.valuation_lane?.score;
        const det = ds.valuation_score_det;
        const tip = isZh
            ? `LLM Val score = ${llm}，但純 FV/price 算的 det = ${det} → LLM 在 valuation 上比純算數 ${(llm < det) ? '更悲觀' : '更樂觀'}`
            : `LLM Val=${llm} vs deterministic FV-vs-price=${det} → LLM is ${(llm < det) ? 'more bearish' : 'more bullish'}`;
        pills.push(`<span class="text-[8px] px-1.5 py-0.5 rounded font-bold" title="${tip}" style="background:color-mix(in srgb,#f59e0b,transparent 88%);color:#f59e0b;border:1px solid color-mix(in srgb,#f59e0b,transparent 70%)">${isZh ? 'Val 不一致' : 'VAL DISAGREE'}</span>`);
    }
    // V2.13.0 — action_label (ATTACK / WAIT / DEFENSIVE)
    if (item.action_label) {
        const actionMap = {
            ATTACK:    { color: '#f97316', label_zh: '🔥 進攻',     label_en: '🔥 ATTACK',    tip_zh: '立即進場：訊號明確且確信度高',                  tip_en: 'Immediate entry: clear signals with high confidence' },
            WAIT:      { color: '#eab308', label_zh: '⏳ 等待',     label_en: '⏳ WAIT',      tip_zh: '等 pullback / 條件觸發再進場',                tip_en: 'Wait for pullback / condition trigger' },
            DEFENSIVE: { color: '#64748b', label_zh: '🛡 防守',     label_en: '🛡 DEFENSIVE', tip_zh: '訊號矛盾或下行偏多，主動避開或縮倉',         tip_en: 'Conflicting/bearish signals; avoid or downsize' },
        };
        const a = actionMap[item.action_label];
        if (a) {
            pills.push(`<span class="text-[8px] px-1.5 py-0.5 rounded font-bold" title="${isZh ? a.tip_zh : a.tip_en}" style="background:color-mix(in srgb,${a.color},transparent 86%);color:${a.color};border:1px solid color-mix(in srgb,${a.color},transparent 65%)">${isZh ? a.label_zh : a.label_en}</span>`);
        }
    }
    // V2.13.0 — moat_assessment (Fundamentals lane)
    const moat = item.fundamentals_lane?.moat_assessment;
    if (moat && moat.level && moat.level !== 'INSUFFICIENT_DATA') {
        const moatMap = {
            WIDE:    { color: '#eab308', label_zh: '寬護城河', label_en: 'WIDE MOAT' },
            NARROW:  { color: '#a1a1aa', label_zh: '窄護城河', label_en: 'NARROW MOAT' },
            ERODING: { color: '#ef4444', label_zh: '護城河侵蝕', label_en: 'ERODING MOAT' },
            NONE:    { color: '#71717a', label_zh: '無護城河', label_en: 'NO MOAT' },
        };
        const m = moatMap[moat.level];
        if (m) {
            const tip = `${moat.type || ''} — ${moat.evidence_one_line || ''}`.replace(/^—\s*/, '').replace(/\s*—\s*$/, '');
            pills.push(`<span class="text-[8px] px-1.5 py-0.5 rounded font-bold" title="${escapeHtmlDc(tip || moat.level)}" style="background:color-mix(in srgb,${m.color},transparent 86%);color:${m.color};border:1px solid color-mix(in srgb,${m.color},transparent 65%)">${isZh ? m.label_zh : m.label_en}</span>`);
        }
    }
    // V2.13.0 — Technical pattern_taxonomy
    const pat = item.technical_lane?.pattern_taxonomy;
    if (pat && pat.pattern && pat.pattern !== 'INSUFFICIENT_DATA') {
        const patternZh = {
            uptrend_breakout:        '突破',
            uptrend_continuation:    '續漲',
            consolidation:           '整理',
            pullback_in_uptrend:     '回踩',
            false_breakout:          '假突破',
            topping_pattern:         '頂部',
            downtrend:               '下降',
            oversold_bounce_attempt: '超賣反彈',
        };
        const isUp = pat.pattern.startsWith('uptrend') || pat.pattern === 'pullback_in_uptrend' || pat.pattern === 'oversold_bounce_attempt';
        const isDown = pat.pattern === 'topping_pattern' || pat.pattern === 'downtrend' || pat.pattern === 'false_breakout';
        const color = isUp ? '#22c55e' : (isDown ? '#ef4444' : '#a1a1aa');
        const label = isZh ? (patternZh[pat.pattern] || pat.pattern) : pat.pattern.replace(/_/g, ' ');
        pills.push(`<span class="text-[8px] px-1.5 py-0.5 rounded font-bold" title="${escapeHtmlDc(pat.confirmation_criteria || '')}" style="background:color-mix(in srgb,${color},transparent 86%);color:${color};border:1px solid color-mix(in srgb,${color},transparent 65%)">${escapeHtmlDc(label)}</span>`);
    }
    // V2.13.0 — Technical market_strength
    const strength = item.technical_lane?.market_strength;
    if (strength && strength !== 'INSUFFICIENT_DATA') {
        const strengthMap = {
            STRONG:  { color: '#22c55e', label_zh: '盤面強', label_en: 'STRONG' },
            NEUTRAL: { color: '#a1a1aa', label_zh: '盤面中性', label_en: 'NEUTRAL' },
            WEAK:    { color: '#ef4444', label_zh: '盤面弱', label_en: 'WEAK' },
        };
        const s = strengthMap[strength];
        if (s) {
            pills.push(`<span class="text-[8px] px-1.5 py-0.5 rounded font-bold" style="background:color-mix(in srgb,${s.color},transparent 86%);color:${s.color};border:1px solid color-mix(in srgb,${s.color},transparent 65%)">${isZh ? s.label_zh : s.label_en}</span>`);
        }
    }
    // V2.13.0 — decision_confidence_pct
    if (typeof item.decision_confidence_pct === 'number') {
        const c = item.decision_confidence_pct;
        const color = c >= 70 ? '#22c55e' : (c >= 50 ? '#eab308' : '#71717a');
        const tip = isZh ? '決策信心度（V2.13.0 PM 整合層輸出）' : 'Decision confidence (V2.13.0 PM synthesis)';
        pills.push(`<span class="text-[8px] px-1.5 py-0.5 rounded font-mono font-bold" title="${tip}" style="color:${color};border:1px solid color-mix(in srgb,${color},transparent 70%)">${c}%</span>`);
    }
    return pills.join(' ');
}

function escapeHtmlDc(s) {
    return String(s == null ? '' : s).replace(/[&<>"']/g, c => ({ '&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;' }[c]));
}

function buildCard(item) {
    const isExecute = isActiveDecision(item.decision);
    const isStaged = item.decision === 'STAGED' || item.decision === 'STAGED_ENTRY' || item.final_decision === 'STAGED_ENTRY';
    const statusColor = DECISION_COLOR[item.decision] || 'var(--text-muted)';
    const t  = window.i18n?.[UI.currentLang] || {};
    const wl = t.watchlist || {};
    const status  = t.status?.[item.decision] || item.decision;
    const horizon = item.time_horizon ? (t.horizon?.[item.time_horizon] || item.time_horizon) : null;
    const version = detectProtocolVersion(item);
    const sectorBadge = _tickerSectorMap[item.ticker]
        ? `<span class="inline-flex items-center text-[9px] font-bold px-2 py-0.5 rounded" style="background:#e0e7ff;border:1px solid #93c5fd;color:#1e3a8a">${sectorBadgeLabel(_tickerSectorMap[item.ticker])}</span>`
        : '';

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
    const isZhDc = (typeof UI !== 'undefined' && UI.currentLang === 'zh');
    const badgesHtml = [
        item.consensus_bonus ? `<span class="text-[8px] px-1.5 py-0.5 rounded bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border border-emerald-500/20 font-bold" data-tip-key="consensus">${wl.badge_consensus || '×1.15 CONSENSUS'}</span>` : '',
        item.macro_alignment === 'CONTRARIAN' ? `<span class="text-[8px] px-1.5 py-0.5 rounded bg-violet-500/10 text-violet-600 dark:text-violet-400 border border-violet-500/20 font-bold" data-tip-key="contrarian">${wl.badge_contrarian || 'CONTRARIAN'}</span>` : '',
        item.binary_class === 'positive' ? `<span class="text-[8px] px-1.5 py-0.5 rounded bg-blue-500/10 text-blue-600 dark:text-blue-400 border border-blue-500/20 font-bold" data-tip-key="pos_binary">${wl.badge_pos_binary || 'POS BINARY'}</span>` : '',
        item.binary_class === 'negative' ? `<span class="text-[8px] px-1.5 py-0.5 rounded bg-red-500/10 text-red-600 dark:text-red-400 border border-red-500/20 font-bold" data-tip-key="neg_binary">${wl.badge_neg_binary || 'NEG BINARY'}</span>` : '',
        // V4.8+ status pills (fragility / degraded / burry override / fanout)
        buildV48StatusPills(item, wl),
    ].filter(Boolean).join(' ');

    // Version-specific extras
    const v5BlockHtml      = (version === 'V5.0') ? buildV5ValuationBlock(item, wl) : '';
    const redTeamBlockHtml = (version === 'V5.0' || version === 'V4.8' || version === 'V4.7') ? buildRedTeamBlock(item, wl) : '';
    const bookmarkHtml     = buildVersionBookmark(version);

    // Entry targets block — V4.6 supports dual-track
    const tgt = item.targets || {};
    let targetHtml = '';
    if (tgt.tp || tgt.sl) {
        targetHtml = `
        <div class="flex gap-4 pt-3 border-t border-zinc-200 dark:border-zinc-900/50" data-tip-key="tp_sl">
            ${tgt.tp ? `<div><p class="text-[9px] text-zinc-700 dark:text-zinc-400 font-bold uppercase">TP</p><p class="text-xs font-mono font-bold" style="color:var(--status-bullish)">$${tgt.tp}</p></div>` : ''}
            ${tgt.sl ? `<div class="border-l border-zinc-200 dark:border-zinc-900/50 pl-4"><p class="text-[9px] text-zinc-700 dark:text-zinc-400 font-bold uppercase">SL</p><p class="text-xs font-mono font-bold" style="color:var(--status-bearish)">$${tgt.sl}</p></div>` : ''}
            ${!tgt.entry_aggressive && tgt.entry ? `<div class="border-l border-zinc-200 dark:border-zinc-900/50 pl-4"><p class="text-[9px] text-zinc-700 dark:text-zinc-400 font-bold uppercase">Entry</p><p class="text-xs font-mono font-bold" style="color:var(--status-binary)">${tgt.entry}</p></div>` : ''}
        </div>`;
    } else if (tgt.watch || tgt.entry) {
        const val = tgt.watch || tgt.entry;
        const lbl = tgt.watch ? 'Watch' : 'Entry';
        targetHtml = `
        <div class="pt-3 border-t border-zinc-200 dark:border-zinc-900/50">
            <p class="text-[9px] text-zinc-700 dark:text-zinc-400 font-bold uppercase">${lbl}</p>
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
            <p class="text-[10px] font-black uppercase tracking-widest flex items-center gap-1" data-tip-key="dual_track" style="color:var(--status-binary)">
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
    const refreshLbl = wl.refresh_btn || (UI.currentLang === 'zh' ? '重新分析' : 'Re-analyze');

    return `
    <div class="glass-card dc-card-hover p-6 flex flex-col gap-0 ${statusGlow} cursor-pointer" data-history-ticker="${item.ticker}" data-protocol-version="${version}" style="position:relative;">
        ${bookmarkHtml}
        <!-- Header -->
        <div class="flex justify-between items-start mb-4">
            <div class="min-w-0 flex-1">
                <div class="flex items-baseline gap-3 flex-wrap">
                    <h4 class="text-3xl font-black tracking-tighter" style="color:var(--text-card-title)">${item.ticker}</h4>
                    ${item.current_price != null ? (() => {
                        const cp = item.current_price;
                        const ap = item.analysis_price;
                        let drift = '';
                        if (ap != null && ap > 0) {
                            const pct = ((cp / ap - 1) * 100);
                            if (Math.abs(pct) >= 0.5) {
                                const sign = pct >= 0 ? '+' : '';
                                const color = pct >= 0 ? 'var(--status-bullish)' : 'var(--status-bearish)';
                                drift = `<span class="text-[10px] font-mono font-bold ml-1" style="color:${color}">${sign}${pct.toFixed(1)}%</span>`;
                            }
                        }
                        return `<span class="text-base font-mono font-bold" style="color:var(--text-main)">$${cp}</span>${drift}`;
                    })() : ''}
                </div>
                <div class="text-[10px] text-zinc-500 font-mono flex items-center gap-2 mt-1.5 flex-wrap">
                    ${sectorBadge}
                    <span>${item.time}</span>
                    ${item.analysis_price != null ? `<span class="text-zinc-600" title="${wl.analysis_price_hint || 'Price at analysis time'}">@ $${item.analysis_price}</span>` : ''}
                    ${item._history_count > 1 ? `<span class="inline-flex items-center gap-0.5 px-1.5 py-0.5 rounded bg-blue-500/10 text-blue-400 border border-blue-500/20 text-[8px] font-bold" title="${wl.history_hint || 'Click card to see previous analyses'}"><i data-lucide="history" class="w-2.5 h-2.5"></i>+${item._history_count - 1}</span>` : ''}
                </div>
            </div>
            <div class="flex items-start gap-2">
                <button type="button" data-refresh-ticker="${item.ticker}"
                    class="refresh-card-btn flex items-center gap-1 text-[10px] font-bold px-2 py-1 rounded-md border border-zinc-200 dark:border-zinc-800 hover:bg-blue-500/10 hover:border-blue-500/50 hover:text-blue-400 transition-all"
                    title="${refreshLbl}">
                    <i data-lucide="refresh-cw" class="w-3 h-3 refresh-icon"></i>
                    <span class="timer-span hidden font-mono text-[10px]">00:00</span>
                </button>
                <div class="flex flex-col items-end gap-2">
                    <span class="px-2 py-1 rounded text-[10px] font-black border"
                        style="background:color-mix(in srgb,${statusColor},transparent 90%);border-color:color-mix(in srgb,${statusColor},transparent 75%);color:${statusColor}">
                        ${status}
                    </span>
                    ${item.da_filed ? `<span class="text-[8px] px-1.5 py-0.5 rounded bg-violet-500/10 text-violet-600 dark:text-violet-400 border border-violet-500/20 font-bold" data-tip-key="da_filed">${wl.da_filed || 'DA Filed'}</span>` : ''}
                </div>
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
        ${v5BlockHtml}
        ${redTeamBlockHtml}
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
    const prefix = await UI.dailyUpdatePrefix();
    const confirmMsg = prefix + (isZh
        ? `透過 Claude 執行「新聞分析 FLASH ${ticker}」？（約 2-3 分鐘，消耗 tokens）`
        : `Run "FLASH ${ticker}" via Claude? (~2-3 min, consumes tokens)`);
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
        UI.showToast(e.message, 'error');
    }
}
window.copyFlashPrompt = goFlash;

// Dedupe items by ticker, keeping the latest-time entry per ticker.
// Also stashes `_history_count` on each returned item so buildCard can
// surface a "+N earlier" hint.  `all` is the full unfiltered history used
// to compute history depth (items list may be a watchlist subset).
function dedupeByTicker(items, all) {
    if (!Array.isArray(items) || items.length === 0) return items;
    const latest = new Map();
    const keyTime = (i) => i?.time || '';
    for (const item of items) {
        const t = item?.ticker;
        if (!t) continue;
        const prev = latest.get(t);
        if (!prev || keyTime(item).localeCompare(keyTime(prev)) > 0) {
            latest.set(t, item);
        }
    }
    // Count how many total history entries exist per ticker (from full `all`),
    // not just within the filtered subset — so the +N hint is honest.
    const historyCount = new Map();
    for (const item of (all || items)) {
        if (!item?.ticker) continue;
        historyCount.set(item.ticker, (historyCount.get(item.ticker) || 0) + 1);
    }
    // Attach count to each returned item (non-destructive copy)
    return [...latest.values()].map(item => ({
        ...item,
        _history_count: historyCount.get(item.ticker) || 1,
    }));
}

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

    // Dedupe: one card per ticker (latest entry wins). Earlier analyses of the
    // same ticker stay accessible via the drill-down overlay — data.json still
    // has every row, but the grid shows only the most recent snapshot.
    filtered = dedupeByTicker(filtered, all);

    if (searchQuery) {
        filtered = filtered.filter(i => (i.ticker || '').toUpperCase().includes(searchQuery));
    }

    if (!filtered.length) {
        const noItems = (window.i18n?.[UI.currentLang]?.watchlist?.no_items) || 'No items match this filter.';
        grid.innerHTML = `<div class="col-span-full py-20 text-center text-zinc-600">${noItems}</div>`;
        return;
    }
    grid.innerHTML = filtered.map(buildCard).join('');
    lucide.createIcons();
    syncLockUI();   // apply current protocol-lock state to freshly rendered cards
}

// ── Card click delegation: drill-down or refresh ─────────────────
// Attached once on the grid container; survives re-renders.
(function attachCardDelegation() {
    const grid = document.getElementById('watchlist-grid');
    if (!grid || grid._delegationAttached) return;
    grid._delegationAttached = true;
    grid.addEventListener('click', (e) => {
        // Refresh button wins
        const refreshBtn = e.target.closest('[data-refresh-ticker]');
        if (refreshBtn) {
            e.stopPropagation();
            refreshTicker(refreshBtn.dataset.refreshTicker);
            return;
        }
        // Ignore clicks on interactive footer buttons (FLASH / Add / View Report / delete-lot)
        // and disclosure widgets (<details>/<summary>) so they toggle without opening drill.
        if (e.target.closest('button, a, input, select, textarea, summary, details')) return;
        // Card body → drill
        const card = e.target.closest('[data-history-ticker]');
        if (card) openHistoryDrill(card.dataset.historyTicker);
    });
})();

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
        UI.applySyncLight(document.getElementById('last-update'), data.last_updated,
            '同步內容：個股分析結果（history.json → data.json）\n每次執行「分析 TICKER」後需重跑 bridge.py 才會更新');

        const allAnalysis = data.recent_analysis || [];
        const watchItems  = allAnalysis.filter(a => a.on_watchlist);
        const positions   = data.positions || [];

        // Build ticker→GICS sector lookup from momentum_screen (S&P 500 universe)
        _tickerSectorMap = {};
        ((data.momentum_screen || {}).rows || []).forEach(r => {
            if (r.ticker && r.sector && r.sector !== 'Unknown') _tickerSectorMap[r.ticker] = r.sector;
        });

        window._allAnalysis   = allAnalysis;
        window._watchlistData = watchItems;
        window._positionsFlat = positions;

        // Summary counts/averages are computed on the deduped watchlist so that
        // a ticker analysed three times this week only contributes once.
        const watchLatest = dedupeByTicker(watchItems, allAnalysis);
        const execCount = watchLatest.filter(a => a.decision === 'EXECUTE' || a.decision === 'BUY').length;
        const waitCount = watchLatest.filter(a =>
            a.decision === 'STAGED' || a.decision === 'STAGED_ENTRY'
            || a.final_decision === 'STAGED_ENTRY'
            || a.watch_conditions
            || (a.targets?.watch && !isActiveDecision(a.decision))
        ).length;
        document.getElementById('count-execute').textContent = execCount;
        document.getElementById('count-waiting').textContent = waitCount;

        const validConf = watchLatest.filter(a => a.avg_confidence != null);
        document.getElementById('avg-conf').textContent = validConf.length
            ? Math.round(validConf.reduce((s, a) => s + a.avg_confidence, 0) / validConf.length * 100) + '%'
            : '–';

        const validRR = watchLatest.filter(a => a.rr_ratio != null);
        document.getElementById('avg-rr').textContent = validRR.length
            ? (validRR.reduce((s, a) => s + a.rr_ratio, 0) / validRR.length).toFixed(2) + 'x'
            : '–';

        renderCards(activeFilter);
        logToUI(`Decisions loaded: ${allAnalysis.length} analyses, ${watchItems.length} watched, ${positions.length} position lots`);

        // Deep-link: ?ticker=XXX from index.html → auto-open history drill
        const qpTicker = new URLSearchParams(window.location.search).get('ticker');
        if (qpTicker && !window._tickerDeepLinkHandled) {
            window._tickerDeepLinkHandled = true;
            const upper = qpTicker.toUpperCase();
            if (allAnalysis.some(a => a.ticker === upper)) {
                setTimeout(() => openHistoryDrill(upper), 100);
            }
        }
    } catch (e) {
        logToUI(e.message, 'error');
        document.getElementById('watchlist-grid').innerHTML =
            `<div class="col-span-full glass-card p-10 text-center text-red-500">${e.message}</div>`;
    }
}

document.getElementById('refresh-btn').addEventListener('click', loadWatchlist);
UI.boot('decisions', { translate: applyTranslations, reload: loadWatchlist });
loadWatchlist();

// ─── V1.74 Invest cmdbar (terminal-style quick-launch) ─────────────────
const DC_RECENT_LS = 'dc_recent_invest_tickers';
const DC_RECENT_MAX = 5;

function dcGetRecent() {
    try {
        const raw = localStorage.getItem(DC_RECENT_LS) || '[]';
        const arr = JSON.parse(raw);
        return Array.isArray(arr) ? arr.filter(s => typeof s === 'string') : [];
    } catch { return []; }
}
function dcSetRecent(list) {
    localStorage.setItem(DC_RECENT_LS, JSON.stringify(list.slice(0, DC_RECENT_MAX)));
}
function dcPushRecent(ticker) {
    const t = String(ticker || '').toUpperCase();
    if (!t) return;
    const cur = dcGetRecent().filter(x => x !== t);
    cur.unshift(t);
    dcSetRecent(cur);
    dcRenderRecent();
}
function dcRenderRecent() {
    const wrap = document.getElementById('dc-recent-chips-wrap');
    const host = document.getElementById('dc-recent-chips');
    if (!wrap || !host) return;
    const list = dcGetRecent();
    if (!list.length) { wrap.hidden = true; return; }
    wrap.hidden = false;
    host.innerHTML = list.map(t =>
        `<span class="ea-recent-chip" data-dc-recent-ticker="${UI.escapeHTML(t)}">${UI.escapeHTML(t)}</span>`
    ).join('');
}
function dcRefreshRiskHint() {
    const valEl = document.getElementById('dc-risk-value');
    if (valEl) valEl.textContent = (window.UI && window.UI.riskTolerance) || 'MEDIUM';
}

async function dcRunInvest(rawTicker) {
    const ticker = String(rawTicker || '').trim().toUpperCase().replace(/[^A-Z0-9.\-]/g, '');
    const tr = window.i18n?.[UI.currentLang]?.decisions || {};
    if (!ticker) {
        UI.showToast?.(tr.cmdbar_empty || (UI.currentLang === 'zh' ? '請輸入 ticker' : 'Please enter a ticker'), 'error');
        return;
    }
    const risk = (window.UI && window.UI.riskTolerance) || 'MEDIUM';
    try {
        const r = await fetch('/api/protocol-queue', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name: 'invest', ticker, risk_tolerance: risk })
        });
        const j = await r.json().catch(() => ({}));
        if (r.status === 202) {
            dcPushRecent(ticker);
            const tpl = tr.cmdbar_queued || (UI.currentLang === 'zh'
                ? '已加入 invest 佇列：{ticker}（risk={risk}）'
                : 'Queued invest analysis: {ticker} (risk={risk})');
            UI.showToast?.(tpl.replace('{ticker}', ticker).replace('{risk}', risk), 'success');
            // Clear input after successful enqueue
            const input = document.getElementById('dc-ticker-input');
            if (input) input.value = '';
        } else if (r.status === 409) {
            const tpl = tr.cmdbar_duplicate || (UI.currentLang === 'zh'
                ? '{ticker} 已在佇列或執行中'
                : '{ticker} already queued or running');
            UI.showToast?.(tpl.replace('{ticker}', ticker), 'warn');
        } else {
            UI.showToast?.(`Failed: ${j.error || r.status}`, 'error');
        }
    } catch (e) {
        UI.showToast?.(`Failed: ${e.message}`, 'error');
    }
}

(function wireCmdbar() {
    const input = document.getElementById('dc-ticker-input');
    const btn   = document.getElementById('dc-run-btn');
    if (!input || !btn) return;
    btn.addEventListener('click', () => dcRunInvest(input.value));
    input.addEventListener('keydown', e => {
        if (e.key === 'Enter') { e.preventDefault(); dcRunInvest(input.value); }
    });
    input.addEventListener('focus', dcRefreshRiskHint);
    window.addEventListener('focus', dcRefreshRiskHint);
    // Recent chip click → re-run
    const chips = document.getElementById('dc-recent-chips');
    if (chips) {
        chips.addEventListener('click', e => {
            const c = e.target.closest('[data-dc-recent-ticker]');
            if (c) dcRunInvest(c.dataset.dcRecentTicker);
        });
    }
    dcRefreshRiskHint();
    dcRenderRecent();
})();

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

// ═══════════════════════════════════════════════════════════════
// Per-card refresh + global protocol lock + history drill overlay
// ═══════════════════════════════════════════════════════════════

const _protoLock = {
    running:       false,
    name:          null,   // 'invest' | 'flash' | 'digest' | 'review' | 'sector'
    ticker:        null,
    started_at:    null,
    elapsed_sec:   0,
    last_done_job: null,   // job_id of last completed run — used to trigger data refresh exactly once
};

function fmtElapsed(sec) {
    sec = Math.max(0, Math.floor(sec || 0));
    const m = Math.floor(sec / 60);
    const s = sec % 60;
    return `${String(m).padStart(2,'0')}:${String(s).padStart(2,'0')}`;
}

// Pull protocol status; update lock state; sync UI.
async function pollProtocolStatus() {
    try {
        const res = await fetch('/api/run-protocol/status');
        if (!res.ok) return;
        const s = await res.json();

        const wasRunning = _protoLock.running;
        _protoLock.running     = (s.status === 'running');
        _protoLock.name        = s.name;
        _protoLock.elapsed_sec = s.elapsed_sec || 0;
        _protoLock.started_at  = s.started_at;
        // Extract ticker from job_id (e.g. "invest_20260418_120342") — fallback: parse log_path
        _protoLock.ticker = _extractTicker(s);

        // Transition: running → done/error/cancelled → refresh data.json + re-render
        if (wasRunning && !_protoLock.running && s.job_id && s.job_id !== _protoLock.last_done_job) {
            _protoLock.last_done_job = s.job_id;
            if (s.status === 'done') {
                UI.showToast(
                    UI.currentLang === 'zh' ? `分析完成：${_protoLock.ticker || ''}` : `Analysis complete: ${_protoLock.ticker || ''}`,
                    'success'
                );
                loadWatchlist();   // refresh data.json + re-render cards
            } else if (s.status === 'error') {
                UI.showToast(
                    UI.currentLang === 'zh' ? `分析失敗：${s.error || 'unknown'}` : `Analysis failed: ${s.error || 'unknown'}`,
                    'error'
                );
            }
        }
        syncLockUI();
    } catch (e) {
        // silent — the refresh-status ring already surfaces server issues
    }
}

// Try to pull a ticker name out of the protocol state (job_id or log path).
// invest/flash/review all run with {ticker} substitution so the prompt contains it,
// but job_id only has timestamp — fall back to log_path parsing if needed.
function _extractTicker(state) {
    if (!state || !state.log_path) return null;
    // Prior call to refreshTicker stashed it in _protoLock.ticker already when we
    // kicked off the run; server-side state doesn't carry it. Best-effort only.
    return _protoLock.ticker;
}

function syncLockUI() {
    const running = _protoLock.running;
    const runningTicker = _protoLock.ticker;
    const elapsedStr = fmtElapsed(_protoLock.elapsed_sec);
    
    // Also get currently queued tickers from AnalyzeQueue
    const queueState = (window.AnalyzeQueue && window.AnalyzeQueue.getQueueState) 
        ? window.AnalyzeQueue.getQueueState() : { queue: [] };
    const queuedTickers = new Set(queueState.queue.map(q => q.ticker));

    document.querySelectorAll('[data-refresh-ticker]').forEach(btn => {
        const btnTicker = btn.dataset.refreshTicker;
        const icon  = btn.querySelector('.refresh-icon');
        const timer = btn.querySelector('.timer-span');
        
        const isCurrentlyRunning = running && btnTicker === runningTicker;
        const isQueued = queuedTickers.has(btnTicker);

        if (isCurrentlyRunning) {
            btn.disabled = true;
            btn.classList.add('border-blue-500/50', 'text-blue-400');
            btn.classList.remove('opacity-40', 'pointer-events-none');
            icon?.classList.add('animate-spin');
            if (timer) {
                timer.textContent = elapsedStr;
                timer.classList.remove('hidden');
            }
            btn.title = (UI.currentLang === 'zh' ? `分析中：${btnTicker}` : `Analyzing: ${btnTicker}`) + ` (${elapsedStr})`;
        } else if (isQueued) {
            btn.disabled = true;
            btn.classList.add('opacity-60', 'border-amber-500/50', 'text-amber-400');
            btn.classList.remove('pointer-events-none');
            icon?.classList.remove('animate-spin');
            timer?.classList.add('hidden');
            btn.title = (UI.currentLang === 'zh' ? '已在佇列中排隊' : 'In Queue...');
        } else {
            // System idle or other ticker running — allow enqueuing!
            btn.disabled = false;
            btn.classList.remove('pointer-events-none', 'border-blue-500/50', 'text-blue-400', 'border-amber-500/50', 'text-amber-400');
            if (running) btn.classList.add('opacity-40');
            else         btn.classList.remove('opacity-40');
            
            icon?.classList.remove('animate-spin');
            timer?.classList.add('hidden');
            const lbl = (window.i18n?.[UI.currentLang]?.watchlist?.refresh_btn) ||
                        (UI.currentLang === 'zh' ? '重新分析' : 'Re-analyze');
            btn.title = lbl;
        }
    });
}

async function refreshTicker(ticker) {
    const isZh = UI.currentLang === 'zh';
    const prefix = await UI.dailyUpdatePrefix();
    const confirmMsg = prefix + (isZh
        ? `加入個股分析佇列：${ticker}（risk=${UI.riskTolerance}）？\nV4.8 每檔約 10-15 分鐘，~$4 tokens。已在佇列/分析中的重複請求會被忽略。`
        : `Enqueue invest analysis for ${ticker} (risk=${UI.riskTolerance})?\nV4.8 ~10-15 min per ticker, ~$4 tokens. Duplicates (queued or active) are abandoned.`);
    if (!confirm(confirmMsg)) return;

    if (window.AnalyzeQueue) {
        await window.AnalyzeQueue.enqueue(ticker);
    } else {
        // Fallback to direct run if the queue module didn't load for any reason
        try {
            const res = await fetch('/api/run-protocol', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ name: 'invest', ticker: ticker.toUpperCase(), risk_tolerance: UI.riskTolerance }),
            });
            if (!res.ok) throw new Error((await res.json().catch(() => ({}))).error || `HTTP ${res.status}`);
        } catch (e) {
            UI.showToast(e.message, 'error');
        }
    }
}

// ── History drill overlay ──────────────────────────────────────
function openHistoryDrill(ticker) {
    const all = window._allAnalysis || [];
    // Filter by ticker, sort by date descending (newest first)
    const items = all.filter(a => a.ticker === ticker)
                     .sort((a, b) => (b.time || '').localeCompare(a.time || ''));

    const overlay = document.getElementById('history-drill-overlay');
    const titleEl = document.getElementById('history-drill-title');
    const rail    = document.getElementById('history-drill-rail');
    const emptyEl = document.getElementById('history-drill-empty');
    if (!overlay || !rail) return;

    const t  = window.i18n?.[UI.currentLang] || {};
    const wl = t.watchlist || {};
    titleEl.textContent = `${ticker} — ${wl.history_title || (UI.currentLang === 'zh' ? '歷次分析' : 'Analysis History')} (${items.length})`;

    if (!items.length) {
        rail.innerHTML = '';
        emptyEl.textContent = wl.history_empty || (UI.currentLang === 'zh' ? '沒有歷史分析記錄' : 'No prior analyses.');
        emptyEl.classList.remove('hidden');
    } else {
        emptyEl.classList.add('hidden');
        // Reuse buildCard for identical visual parity; wrap each with a fixed-width shell so they lay out horizontally
        rail.innerHTML = items.map(i => `<div class="shrink-0 w-[420px]">${buildCard(i)}</div>`).join('');
    }

    overlay.classList.remove('hidden');
    lucide.createIcons();
    syncLockUI();   // make sure refresh buttons inside the rail also reflect lock state
}

function closeHistoryDrill() {
    const overlay = document.getElementById('history-drill-overlay');
    if (overlay) overlay.classList.add('hidden');
}

// Overlay dismiss: click backdrop or ESC
(function wireDrillDismissal() {
    const overlay = document.getElementById('history-drill-overlay');
    if (!overlay) return;
    overlay.addEventListener('click', (e) => {
        if (e.target === overlay) closeHistoryDrill();
    });
    const closeBtn = document.getElementById('history-drill-close');
    if (closeBtn) closeBtn.addEventListener('click', closeHistoryDrill);
})();

// Extend existing ESC handler (already closes modals) to also close drill overlay.
document.addEventListener('keydown', e => {
    if (e.key === 'Escape') closeHistoryDrill();
});

// Start protocol-status poller (2s cadence). Kicks off with an immediate poll
// so first page load picks up an in-flight job.
pollProtocolStatus();
setInterval(pollProtocolStatus, 2000);
setInterval(updateRefreshStatus, 1000);
