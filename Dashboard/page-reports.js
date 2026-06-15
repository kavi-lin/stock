/**
 * page-reports.js — Reports Center (V3.26.0)
 *
 * Read-only viewer over reports/*.md. Fetches the classified list from
 * /api/reports, fetches raw markdown from /api/reports/view/<filename>,
 * renders via marked.js with IC-memo-specific post-processing (verdict
 * badge, decision_lock chip, degraded banner, TOC).
 *
 * Does NOT touch decisions / skills / protocols — pure browser.
 */

const t = () => (window.i18n?.[UI.currentLang]?.reports) || {};
const tCommon = () => window.i18n?.[UI.currentLang] || {};

const TYPE_ORDER = [
    'ic_memo', 'deep_dive', 'earnings', 'pre_earnings', 'sector', 'theme',
    'news_digest', 'news_flash', 'weekly_short', 'weekly',
    'premarket', 'shadow', 'postmortem', 'llm_review', 'ledger',   // V4.6 產出閉環
    'sentiment', 'valuation', 'other',
];

const state = {
    reports: [],
    counts: {},
    filter: 'all',
    query: '',
    selected: null,
};

function typeLabel(typeKey) {
    const isZh = UI.currentLang === 'zh';
    const item = state.reports.find(r => r.type === typeKey);
    if (item) return isZh ? item.label_zh : item.label_en;
    return typeKey;
}

async function fetchList() {
    const list = document.getElementById('reports-items');
    try {
        const r = await fetch('/api/reports', { cache: 'no-store' });
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        const data = await r.json();
        state.reports = data.reports || [];
        state.counts = data.counts || {};
        const meta = document.getElementById('reports-meta');
        if (meta) {
            const isZh = UI.currentLang === 'zh';
            meta.textContent = isZh
                ? `${data.total} 份報告`
                : `${data.total} reports`;
        }
        renderTabs();
        renderList();
        applyHashSelection();
    } catch (e) {
        if (UI.isFetchCancellation(e)) return;
        list.innerHTML = `<li class="text-xs text-red-500 p-4 text-center">載入失敗：${UI.escapeHTML(e.message)}</li>`;
    }
}

function renderTabs() {
    const tabs = document.getElementById('reports-tabs');
    if (!tabs) return;
    const isZh = UI.currentLang === 'zh';
    const total = state.reports.length;

    const presentTypes = TYPE_ORDER.filter(k => state.counts[k]);
    const allBtn = `<button class="report-type-tab${state.filter === 'all' ? ' active' : ''}" data-filter="all">
        ${isZh ? '全部' : 'All'}<span class="count">${total}</span></button>`;
    const typeBtns = presentTypes.map(k => `
        <button class="report-type-tab${state.filter === k ? ' active' : ''}" data-filter="${k}">
            ${typeLabel(k)}<span class="count">${state.counts[k]}</span>
        </button>`).join('');

    tabs.innerHTML = allBtn + typeBtns;
    tabs.querySelectorAll('button[data-filter]').forEach(btn => {
        btn.addEventListener('click', () => {
            state.filter = btn.dataset.filter;
            renderTabs();
            renderList();
        });
    });
}

function renderList() {
    const list = document.getElementById('reports-items');
    if (!list) return;
    const q = state.query.trim().toLowerCase();
    const rows = state.reports.filter(r => {
        if (state.filter !== 'all' && r.type !== state.filter) return false;
        if (!q) return true;
        return r.filename.toLowerCase().includes(q)
            || (r.ticker && r.ticker.toLowerCase().includes(q))
            || (r.label_en && r.label_en.toLowerCase().includes(q))
            || (r.label_zh && r.label_zh.includes(q));
    });

    if (!rows.length) {
        const isZh = UI.currentLang === 'zh';
        list.innerHTML = `<li class="text-xs text-zinc-500 p-4 text-center">${isZh ? '無符合條件的報告' : 'No matching reports'}</li>`;
        return;
    }

    const isZh = UI.currentLang === 'zh';
    list.innerHTML = rows.map(r => {
        const label = isZh ? r.label_zh : r.label_en;
        const cls = state.selected === r.filename ? ' active' : '';
        return `
            <li class="report-list-item${cls}" data-filename="${UI.escapeHTML(r.filename)}">
                <div class="rli-top">
                    <span class="rli-type rli-type-${r.type}">${UI.escapeHTML(label)}</span>
                    ${r.ticker ? `<span class="rli-ticker">${UI.escapeHTML(r.ticker)}</span>` : ''}
                    <span class="rli-date">${r.date || '—'}</span>
                </div>
                <div class="rli-filename">${UI.escapeHTML(r.filename)}</div>
                ${r.summary ? `<div class="rli-summary">${UI.escapeHTML(r.summary)}</div>` : ''}
            </li>`;
    }).join('');

    list.querySelectorAll('.report-list-item').forEach(li => {
        li.addEventListener('click', () => loadReport(li.dataset.filename));
    });
}

// ── Parse the YAML-ish leading metadata block from IC memos ─────────────
// Lines look like:  - **Date**: 2026-05-27
function parseHeaderMeta(md) {
    const meta = {};
    const lines = md.split('\n');
    for (let i = 0; i < Math.min(lines.length, 25); i++) {
        const m = lines[i].match(/^-\s*\*\*([^:]+?)\*\*:\s*(.+?)\s*$/);
        if (m) {
            const k = m[1].trim().toLowerCase().replace(/\s+/g, '_').replace(/[\/]/g, '_');
            meta[k] = m[2].trim();
        }
    }
    return meta;
}

function verdictKey(finalAction) {
    if (!finalAction) return 'no-action';
    const fa = finalAction.replace(/\*/g, '').trim().toUpperCase();
    if (['BUY', 'EXECUTE', 'STAGED', 'STAGED_ENTRY'].includes(fa)) return 'buy';
    if (['SELL', 'CANCEL'].includes(fa))                              return 'sell';
    if (['HOLD', 'ARCHIVE', 'STAGED_EXIT', 'PREVIEW'].includes(fa))   return 'hold';
    return 'no-action';
}

function renderSummaryCard(filename, meta, isIcMemo) {
    const card = document.getElementById('reports-summary-card');
    if (!isIcMemo || !meta.final_action) {
        card.classList.add('hidden');
        card.innerHTML = '';
        return;
    }
    const isZh = UI.currentLang === 'zh';
    const vKey = verdictKey(meta.final_action);
    const vLabel = meta.final_action.replace(/\*/g, '').trim();

    const rows = [
        { lab: isZh ? '日期' : 'Date',          val: meta.date },
        { lab: isZh ? '分析價' : 'Analysis Price', val: meta.analysis_price },
        { lab: isZh ? '即時價' : 'Live Spot',   val: meta.live_spot },
        { lab: isZh ? '市值' : 'Market Cap',     val: meta.market_cap },
        { lab: isZh ? '產業' : 'Sector',         val: meta.sector_industry },
    ].filter(r => r.val);

    card.classList.remove('hidden');
    card.innerHTML = `
        <div class="flex items-start gap-4 flex-wrap">
            <span class="report-verdict-badge ${vKey}">${UI.escapeHTML(vLabel)}</span>
            <div class="flex-1 grid gap-2" style="grid-template-columns: repeat(auto-fit, minmax(140px, 1fr))">
                ${rows.map(r => `
                    <div>
                        <div class="text-[10px] uppercase tracking-wider text-zinc-500 font-bold">${UI.escapeHTML(r.lab)}</div>
                        <div class="text-xs font-mono">${UI.escapeHTML(r.val)}</div>
                    </div>
                `).join('')}
            </div>
            <span class="report-decision-lock" title="${isZh ? '§11 委員會結論欄位由 11 欄位 SHA256 hash 鎖保護 — 任何竄改會讓 validate_ic_memo.py rc=1' : '§11 verdict fields protected by 11-field SHA256 decision_lock; tampering trips validate_ic_memo.py rc=1'}">
                🔒 decision_lock
            </span>
        </div>`;
}

function detectDegraded(md) {
    const m = md.match(/degraded_sections:\s*\[([^\]]*)\]/);
    if (!m || !m[1].trim()) return null;
    return m[1].split(',').map(s => s.trim()).filter(Boolean);
}

function renderDegradedBanner(items) {
    const el = document.getElementById('reports-degraded-banner');
    if (!items || !items.length) {
        el.classList.add('hidden');
        el.innerHTML = '';
        return;
    }
    const isZh = UI.currentLang === 'zh';
    el.classList.remove('hidden');
    el.innerHTML = `
        <div class="report-degraded-banner">
            <i data-lucide="alert-triangle" class="w-4 h-4"></i>
            <div>
                <div class="font-bold text-xs">${isZh ? 'Degraded sections' : 'Degraded sections'}</div>
                <div class="text-[11px] opacity-80">${items.map(s => UI.escapeHTML(s)).join(' · ')}</div>
            </div>
        </div>`;
    UI.icons();
}

function slugify(text) {
    return String(text || '').trim().toLowerCase()
        .replace(/[\s\.·]+/g, '-')
        .replace(/[^\w\-一-鿿§]/g, '')
        .replace(/\-+/g, '-').replace(/^-|-$/g, '') || ('h-' + Math.random().toString(36).slice(2, 8));
}

function renderTOC(bodyEl) {
    const toc = document.getElementById('reports-toc');
    if (!toc) return;
    const isZh = UI.currentLang === 'zh';
    const heads = bodyEl.querySelectorAll('h2, h3');
    if (!heads.length) {
        toc.innerHTML = '';
        return;
    }
    const seen = new Set();
    const links = [];
    heads.forEach(h => {
        let id = h.id || slugify(h.textContent);
        let base = id, n = 2;
        while (seen.has(id)) { id = `${base}-${n++}`; }
        seen.add(id);
        h.id = id;
        const indent = h.tagName === 'H3' ? 'pl-3' : '';
        links.push(`<a href="#${id}" class="block ${indent} text-zinc-500 hover:text-emerald-500 truncate" title="${UI.escapeHTML(h.textContent)}">${UI.escapeHTML(h.textContent)}</a>`);
    });
    toc.innerHTML = `
        <div class="text-[10px] uppercase tracking-widest font-bold text-zinc-500 mb-2">${isZh ? '目錄' : 'Contents'}</div>
        <div class="space-y-1">${links.join('')}</div>`;
}

async function loadReport(filename) {
    if (!filename) return;
    state.selected = filename;

    // Highlight active row immediately
    document.querySelectorAll('.report-list-item').forEach(li => {
        li.classList.toggle('active', li.dataset.filename === filename);
    });

    const empty = document.getElementById('reports-empty');
    const wrap = document.getElementById('reports-viewer-wrap');
    const body = document.getElementById('reports-body');
    empty.classList.add('hidden');
    wrap.classList.remove('hidden');
    body.innerHTML = '<div class="text-zinc-500 text-sm">載入中…</div>';

    try {
        const r = await fetch('/api/reports/view/' + encodeURIComponent(filename), { cache: 'no-store' });
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        const md = await r.text();

        const isIcMemo = /_ic_memo\.md$/.test(filename);
        const meta = parseHeaderMeta(md);
        renderSummaryCard(filename, meta, isIcMemo);
        renderDegradedBanner(detectDegraded(md));

        const html = marked.parse(md, { gfm: true, breaks: false });
        body.innerHTML = html;

        // Strip any script/iframe tags as belt-and-suspenders. Our own files
        // don't contain them, but keep the renderer hardened anyway.
        body.querySelectorAll('script, iframe').forEach(el => el.remove());

        // Style markdown tables with .glass-table for consistency
        body.querySelectorAll('table').forEach(tbl => tbl.classList.add('glass-table'));

        renderTOC(body);

        // Sync URL hash so refresh / share keeps the same report open
        const newHash = '#report=' + encodeURIComponent(filename);
        if (location.hash !== newHash) {
            history.replaceState(null, '', newHash);
        }

        UI.icons();
    } catch (e) {
        if (UI.isFetchCancellation(e)) return;
        body.innerHTML = `<div class="text-red-500 text-sm">載入失敗：${UI.escapeHTML(e.message)}</div>`;
    }
}

function applyHashSelection() {
    const m = location.hash.match(/#report=([^&]+)/);
    if (!m) return;
    const fn = decodeURIComponent(m[1]);
    if (state.reports.some(r => r.filename === fn)) {
        loadReport(fn);
    }
}

function translate() {
    const isZh = UI.currentLang === 'zh';
    const title = document.getElementById('reports-title');
    const sub = document.getElementById('reports-subtitle');
    const search = document.getElementById('reports-search');
    const refresh = document.getElementById('reports-refresh-label');
    const emptyMsg = document.getElementById('reports-empty-msg');
    if (title) title.textContent = isZh ? '投資報告中心' : 'Reports Center';
    if (sub) sub.textContent = isZh ? 'Reports Center' : 'INVESTMENT REPORTS';
    if (search) search.placeholder = isZh ? '搜尋 ticker / 檔名…' : 'Search ticker / filename…';
    if (refresh) refresh.textContent = isZh ? '重新掃描' : 'Rescan';
    if (emptyMsg) emptyMsg.textContent = isZh ? '從左側選一份報告開啟' : 'Pick a report from the left to open';
    // Re-render dependent UI
    renderTabs();
    renderList();
}

document.addEventListener('DOMContentLoaded', () => {
    UI.boot('reports', { translate, reload: fetchList });

    document.getElementById('reports-search')?.addEventListener('input', e => {
        state.query = e.target.value || '';
        renderList();
    });
    document.getElementById('reports-refresh')?.addEventListener('click', fetchList);

    window.addEventListener('hashchange', applyHashSelection);

    fetchList();
});
