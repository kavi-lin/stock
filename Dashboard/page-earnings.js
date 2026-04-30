/**
 * page-earnings.js — Earnings Analyst Dashboard (V1.71.1)
 *
 * Reads `data.earnings_analyses[]` from data.json (bridge.py extract_earnings_analyses)
 * and presents an editorial × financial-terminal style UI:
 *   - hero stat strip (count-up animated)
 *   - command bar trigger (>, JetBrains Mono)
 *   - segmented + chip filter bar (verdict / flags)
 *   - asymmetric cards with verdict stripe + 8Q margin sparkline + component bars
 *   - report modal via UI.viewReport (reuses utils.js:322-344 + marked.js)
 *
 * Triggers analysis via POST /api/protocol-queue (name=earnings).
 */
(function () {
    'use strict';

    // ── State ────────────────────────────────────────────────────────────
    let allAnalyses = [];
    let lastUpdatedAt = null;

    const VERDICTS = ['STRONG', 'SOLID', 'MIXED', 'WEAK', 'DETERIORATING'];

    const filterState = {
        sort:         localStorage.getItem('ea_sort')         || 'score-desc',
        verdicts:     new Set(JSON.parse(localStorage.getItem('ea_verdicts') || JSON.stringify(VERDICTS))),
        flags:        localStorage.getItem('ea_flags')        || 'any', // 'any' | 'clean' | 'has'
    };

    const RECENT_KEY = 'ea_recent_tickers';
    const RECENT_MAX = 5;

    // ── Bootstrap ────────────────────────────────────────────────────────
    document.addEventListener('DOMContentLoaded', async () => {
        UI.logToUI?.('Initializing System...');
        UI.boot('earnings', { translate: applyTranslations, reload: loadAndRender });

        renderHeroStrip([], { initial: true });   // skeleton
        renderFilterBar();
        wireCommandBar();
        wireFilterBar();
        wireEmptyStateSamples();
        wireReportModal();

        await loadAndRender();

        if (window.DataStore) {
            window.DataStore.subscribe((data) => {
                allAnalyses = Array.isArray(data?.earnings_analyses) ? data.earnings_analyses : [];
                lastUpdatedAt = data?.last_updated;
                renderAll();
            });
        }
    });

    async function loadAndRender() {
        try {
            const data = window.DataStore
                ? await window.DataStore.get()
                : await fetch('data.json', { cache: 'no-store' }).then(r => r.json());
            allAnalyses = Array.isArray(data?.earnings_analyses) ? data.earnings_analyses : [];
            lastUpdatedAt = data?.last_updated;
        } catch (e) {
            console.error('[earnings] load failed:', e);
            allAnalyses = [];
        }
        renderAll();
    }

    function renderAll() {
        renderHeroStrip(allAnalyses);
        renderRecentChips();
        renderGrid();
        if (window.UI?.applySyncLight && lastUpdatedAt) {
            UI.applySyncLight(document.getElementById('last-update'), lastUpdatedAt);
        }
    }

    // ── i18n ─────────────────────────────────────────────────────────────
    function applyTranslations() {
        const lang = UI.currentLang;
        const isZh = lang === 'zh';
        document.getElementById('ea-title').textContent = isZh ? '財報分析' : 'Earnings Analyst';
        document.getElementById('ea-run-label').textContent = isZh ? '執行' : 'Run';
        document.getElementById('ea-sort-label').textContent = isZh ? '排序' : 'Sort';
        document.getElementById('ea-verdict-label').textContent = isZh ? '評級' : 'Verdict';
        document.getElementById('ea-flags-label').textContent = isZh ? '品質' : 'Flags';
        document.getElementById('ea-empty-title').textContent = isZh ? '尚未有任何財報分析' : 'No earnings analyses yet';
        document.getElementById('ea-empty-hint').textContent = isZh
            ? '輸入 ticker 開始第一份分析,或從以下熱門個股 quick-start。'
            : 'Type a ticker above, or quick-start from one of these.';
        document.getElementById('ea-recent-label').textContent = isZh ? '最近:' : 'Recent:';
        document.getElementById('ea-filter-reset').textContent = isZh ? '重置' : 'Reset';

        // Sort buttons
        document.querySelectorAll('#ea-sort-segmented .ea-segmented-btn').forEach(btn => {
            const sort = btn.dataset.sort;
            const labels = isZh
                ? { 'score-desc':'分數↓','score-asc':'分數↑','date-desc':'最新','ticker-asc':'A→Z' }
                : { 'score-desc':'Score ↓','score-asc':'Score ↑','date-desc':'Recent','ticker-asc':'A→Z' };
            btn.textContent = labels[sort] || sort;
        });

        renderHeroStrip(allAnalyses);  // re-render labels
        renderFilterBar();              // re-render chip labels
        renderGrid();
    }

    // ── Hero stat strip ──────────────────────────────────────────────────
    function renderHeroStrip(rows, opts = {}) {
        const isZh = UI.currentLang === 'zh';
        const total = rows.length;
        const avg = total ? Math.round(rows.reduce((s, r) => s + (r.composite_score || 0), 0) / total) : 0;
        const strong = rows.filter(r => r.verdict === 'STRONG').length;
        const weak = rows.filter(r => r.verdict === 'WEAK' || r.verdict === 'DETERIORATING').length;

        const tiles = [
            { label: isZh ? '已分析' : 'Analyses',     value: total,  accent: 'zinc'    },
            { label: isZh ? '平均分數' : 'Avg score',  value: avg,    suffix: '/100', accent: 'zinc' },
            { label: isZh ? 'STRONG'   : 'STRONG',      value: strong, accent: 'emerald' },
            { label: isZh ? '警示中'   : 'Risk Watch', value: weak,   accent: 'rose'    },
        ];

        const wrap = document.getElementById('ea-hero-strip');
        wrap.innerHTML = tiles.map((t, i) => `
            <div class="ea-stat-tile" style="animation: ea-card-reveal 0.45s cubic-bezier(0.22,1,0.36,1) ${i*0.08}s both">
                <div class="ea-stat-tile-accent ea-stat-accent-${t.accent}"></div>
                <div class="ea-stat-tile-label">${t.label}</div>
                <div class="ea-stat-tile-value">
                    <span class="ea-anim-num" data-target="${t.value}">${opts.initial ? 0 : t.value}</span>${t.suffix ? `<span class="ea-stat-tile-suffix">${t.suffix}</span>` : ''}
                </div>
            </div>
        `).join('');

        // Count-up animation
        if (!opts.initial) {
            wrap.querySelectorAll('.ea-anim-num').forEach(el => {
                animateCount(el, parseInt(el.dataset.target, 10), 480);
            });
        }
    }

    function animateCount(el, target, duration) {
        if (!isFinite(target)) { el.textContent = target; return; }
        const start = 0;
        const t0 = performance.now();
        function step(now) {
            const t = Math.min(1, (now - t0) / duration);
            const ease = 1 - Math.pow(1 - t, 3);
            const v = Math.round(start + (target - start) * ease);
            el.textContent = String(v);
            if (t < 1) requestAnimationFrame(step);
        }
        requestAnimationFrame(step);
    }

    // ── Filter bar ───────────────────────────────────────────────────────
    function renderFilterBar() {
        const isZh = UI.currentLang === 'zh';

        // Verdict chips
        const vWrap = document.getElementById('ea-verdict-chips');
        vWrap.innerHTML = VERDICTS.map(v => {
            const active = filterState.verdicts.has(v) ? 'active' : '';
            const klass = `ea-chip-${v.toLowerCase()}`;
            return `<button class="ea-chip ${klass} ${active}" data-verdict="${v}" type="button"><span>${v}</span></button>`;
        }).join('');

        // Flags chips (mutually exclusive: any / clean / has)
        const fWrap = document.getElementById('ea-flags-chips');
        const flagsOpts = [
            { key: 'clean', label: isZh ? '✅ 乾淨' : '✅ Clean',    klass: 'ea-chip-flag-clean' },
            { key: 'has',   label: isZh ? '⚠️ 有警示' : '⚠️ Has Flags', klass: 'ea-chip-flag-has'   },
        ];
        fWrap.innerHTML = flagsOpts.map(o => {
            const active = filterState.flags === o.key ? 'active' : '';
            return `<button class="ea-chip ${o.klass} ${active}" data-flag="${o.key}" type="button"><span>${o.label}</span></button>`;
        }).join('');

        // Sort segmented
        document.querySelectorAll('#ea-sort-segmented .ea-segmented-btn').forEach(btn => {
            btn.classList.toggle('active', btn.dataset.sort === filterState.sort);
        });
    }

    function wireFilterBar() {
        // Sort
        document.getElementById('ea-sort-segmented').addEventListener('click', (e) => {
            const btn = e.target.closest('.ea-segmented-btn');
            if (!btn) return;
            filterState.sort = btn.dataset.sort;
            localStorage.setItem('ea_sort', filterState.sort);
            renderFilterBar();
            renderGrid();
        });

        // Verdict toggles
        document.getElementById('ea-verdict-chips').addEventListener('click', (e) => {
            const btn = e.target.closest('.ea-chip[data-verdict]');
            if (!btn) return;
            const v = btn.dataset.verdict;
            if (filterState.verdicts.has(v)) filterState.verdicts.delete(v);
            else filterState.verdicts.add(v);
            localStorage.setItem('ea_verdicts', JSON.stringify([...filterState.verdicts]));
            renderFilterBar();
            renderGrid();
        });

        // Flags toggle (mutually exclusive — click again to clear)
        document.getElementById('ea-flags-chips').addEventListener('click', (e) => {
            const btn = e.target.closest('.ea-chip[data-flag]');
            if (!btn) return;
            const k = btn.dataset.flag;
            filterState.flags = (filterState.flags === k) ? 'any' : k;
            localStorage.setItem('ea_flags', filterState.flags);
            renderFilterBar();
            renderGrid();
        });

        // Reset
        document.getElementById('ea-filter-reset').addEventListener('click', () => {
            filterState.sort = 'score-desc';
            filterState.verdicts = new Set(VERDICTS);
            filterState.flags = 'any';
            localStorage.removeItem('ea_sort');
            localStorage.removeItem('ea_verdicts');
            localStorage.removeItem('ea_flags');
            renderFilterBar();
            renderGrid();
        });
    }

    // ── Command bar ──────────────────────────────────────────────────────
    function wireCommandBar() {
        const input = document.getElementById('ea-ticker-input');
        const btn = document.getElementById('ea-run-btn');
        const placeholders = ['NVDA', 'AAPL', 'MSFT', 'AVGO', 'META'];
        let phIdx = Math.floor(Math.random() * placeholders.length);
        input.placeholder = placeholders[phIdx];
        setInterval(() => {
            if (document.activeElement === input) return;
            phIdx = (phIdx + 1) % placeholders.length;
            input.placeholder = placeholders[phIdx];
        }, 3500);

        const trigger = () => {
            const t = (input.value || '').trim().toUpperCase();
            if (!t) {
                UI.showToast(UI.currentLang === 'zh' ? '請先輸入 ticker' : 'Enter a ticker first', 'warn');
                return;
            }
            input.value = '';
            runEarnings(t);
        };

        btn.addEventListener('click', trigger);
        input.addEventListener('keydown', (e) => {
            if (e.key === 'Enter') { e.preventDefault(); trigger(); }
        });
    }

    function getRecentTickers() {
        try { return JSON.parse(localStorage.getItem(RECENT_KEY) || '[]'); }
        catch { return []; }
    }
    function pushRecentTicker(ticker) {
        const list = getRecentTickers().filter(t => t !== ticker);
        list.unshift(ticker);
        if (list.length > RECENT_MAX) list.length = RECENT_MAX;
        localStorage.setItem(RECENT_KEY, JSON.stringify(list));
        renderRecentChips();
    }
    function renderRecentChips() {
        const wrap = document.getElementById('ea-recent-chips');
        const list = getRecentTickers().slice(0, 3);
        if (!list.length) {
            wrap.innerHTML = `<span class="text-zinc-600">—</span>`;
            return;
        }
        wrap.innerHTML = list.map(t =>
            `<button class="ea-recent-chip" data-ticker="${t}" type="button">${t}</button>`
        ).join('');
        wrap.querySelectorAll('.ea-recent-chip').forEach(c => {
            c.addEventListener('click', () => runEarnings(c.dataset.ticker));
        });
    }

    function wireEmptyStateSamples() {
        document.getElementById('ea-empty-samples').addEventListener('click', (e) => {
            const btn = e.target.closest('.ea-empty-chip');
            if (btn) runEarnings(btn.dataset.ticker);
        });
    }

    async function runEarnings(ticker) {
        ticker = (ticker || '').toUpperCase();
        if (!ticker) return;
        const lang = UI.currentLang;
        try {
            const r = await fetch('/api/protocol-queue', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ name: 'earnings', ticker })
            });
            const body = await r.json();
            if (r.status === 202 && body.queued) {
                pushRecentTicker(ticker);
                const pos = body.position || '?';
                UI.showToast(lang === 'zh' ? `已排入財報分析:${ticker}(第 ${pos} 位)` : `Queued earnings: ${ticker} (#${pos})`, 'info');
            } else if (r.status === 409 && body.reason === 'duplicate_active') {
                UI.showToast(lang === 'zh' ? `${ticker} 財報分析已在執行中` : `${ticker} earnings already running`, 'warn');
            } else if (r.status === 409 && body.reason === 'duplicate_pending') {
                UI.showToast(lang === 'zh' ? `${ticker} 財報已在佇列` : `${ticker} earnings already queued`, 'warn');
            } else {
                UI.showToast(lang === 'zh' ? `加入失敗:${body.error || r.status}` : `Failed: ${body.error || r.status}`, 'error');
            }
        } catch (e) {
            UI.showToast(lang === 'zh' ? `網路錯誤:${e.message}` : `Network error: ${e.message}`, 'error');
        }
    }

    // ── Report modal wiring ──────────────────────────────────────────────
    function wireReportModal() {
        const modal = document.getElementById('report-modal');
        if (!modal) return;
        document.getElementById('close-modal')?.addEventListener('click', () => modal.classList.add('hidden'));
        modal.addEventListener('click', (e) => {
            if (e.target === modal) modal.classList.add('hidden');
        });
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && !modal.classList.contains('hidden')) modal.classList.add('hidden');
        });
    }

    // ── Filtering & Sorting ──────────────────────────────────────────────
    function getFilteredSorted() {
        let rows = allAnalyses.slice();

        // Verdict
        rows = rows.filter(r => filterState.verdicts.has(r.verdict));

        // Flags
        if (filterState.flags === 'clean') {
            rows = rows.filter(r => !(r.quality_flags || []).length);
        } else if (filterState.flags === 'has') {
            rows = rows.filter(r => (r.quality_flags || []).length > 0);
        }

        // Sort
        switch (filterState.sort) {
            case 'score-desc': rows.sort((a, b) => (b.composite_score ?? -1) - (a.composite_score ?? -1)); break;
            case 'score-asc':  rows.sort((a, b) => (a.composite_score ?? 999) - (b.composite_score ?? 999)); break;
            case 'date-desc':  rows.sort((a, b) => (b.as_of_date || '').localeCompare(a.as_of_date || '')); break;
            case 'ticker-asc': rows.sort((a, b) => (a.ticker || '').localeCompare(b.ticker || '')); break;
        }
        return rows;
    }

    // ── Grid rendering ───────────────────────────────────────────────────
    function renderGrid() {
        const rows = getFilteredSorted();
        const grid = document.getElementById('ea-grid');
        const empty = document.getElementById('ea-empty');

        document.getElementById('ea-match-now').textContent = rows.length;
        document.getElementById('ea-match-total').textContent = allAnalyses.length;

        if (!allAnalyses.length) {
            grid.innerHTML = '';
            empty.classList.remove('hidden');
            UI.icons?.();
            return;
        }
        empty.classList.add('hidden');

        if (!rows.length) {
            grid.innerHTML = `<div class="col-span-full text-center text-sm text-zinc-500 py-12">${UI.currentLang==='zh'?'此篩選條件下沒有符合的分析。':'No analyses match the current filters.'}</div>`;
            return;
        }

        grid.innerHTML = rows.map((r, i) => renderCard(r, i)).join('');
        UI.icons?.();
    }

    function renderCard(r, idx) {
        const lang = UI.currentLang;
        const isZh = lang === 'zh';
        const verdict = r.verdict || 'n/a';
        const vKey = verdict.toLowerCase();
        const sc = r.score_components || {};
        const company = (r.company_name || '').replace(/"/g, '&quot;');

        // Sparkline (8Q gross margin)
        const sparkline = renderSparklineSVG(r);
        // Component bars
        const comps = renderComponentBars(sc);
        // Quality flag chips
        const flagsRow = renderFlagsRow(r.quality_flags, isZh);
        // Freshness
        const fresh = renderFreshness(r.cache_age_days, isZh);
        // Buttons
        const reportBtn = r.report_path
            ? `<button class="ea-act-btn ea-act-btn-primary" data-action="view" data-path="${r.report_path}">📄 ${isZh?'看報告':'Report'}</button>`
            : '';
        const rerunBtn = `<button class="ea-act-btn" data-action="rerun" data-ticker="${r.ticker}">🔄 ${isZh?'重跑':'Re-run'}</button>`;

        // Meta pills
        const metaPills = [];
        if (r.sector)            metaPills.push(`<span class="ea-pill">${r.sector}</span>`);
        if (r.industry && r.industry !== r.sector) metaPills.push(`<span class="ea-pill">${r.industry}</span>`);
        if (r.last_earnings_date) metaPills.push(`<span class="ea-pill ea-pill-date" title="${isZh?'最新財報':'Last earnings'}">📅 ${r.last_earnings_date}</span>`);

        return `<div class="ea-card" style="animation-delay:${idx * 60}ms" data-ticker="${r.ticker}">
            <div class="ea-card-stripe ea-card-stripe-${vKey}"></div>

            <div class="ea-score-col">
                <div>
                    <div class="ea-score-num ea-score-num-${vKey}">
                        <span class="ea-anim-num" data-target="${r.composite_score ?? 0}">0</span>
                    </div>
                    <div class="ea-score-suffix">/ 100</div>
                </div>
                <div class="ea-verdict-pill ea-verdict-pill-${vKey}">${verdict}</div>
            </div>

            <div class="ea-data-col">
                <div class="ea-ticker-row">
                    <span class="ea-ticker">${r.ticker}</span>
                    <span class="ea-company" title="${company}">${company}</span>
                </div>
                <div class="ea-meta-pills">${metaPills.join('')}</div>
                ${flagsRow}
                ${sparkline}
                <div class="ea-components">${comps}</div>
                <div class="ea-action-row">
                    <span class="ea-freshness ${fresh.cls}" title="${fresh.tooltip}">
                        <span class="ea-freshness-dot" style="background:currentColor"></span>
                        ${fresh.label}
                    </span>
                    ${reportBtn}
                    ${rerunBtn}
                </div>
            </div>
        </div>`;
    }

    function renderSparklineSVG(r) {
        const margins = (r.score_components && (r.derived?.margins_8q || r.margins_8q)) || [];
        // Note: bridge.py's slim summary doesn't include 'derived'. We need to fetch
        // it separately from cache for richer card. Since current data.json from
        // extract_earnings_analyses only has thin summary, we render a placeholder
        // OR fetch /api/earnings-cache/<ticker> on demand. For initial paint we'll
        // skip if no margins; future enhancement: prefetch full bundle.

        // Try to get margins from any nested location:
        const m = (r.derived && r.derived.margins_8q) || r.margins_8q;
        if (!Array.isArray(m) || m.length < 2) {
            return ''; // no sparkline if data not present (bridge index doesn't include 8Q yet)
        }

        const isZh = UI.currentLang === 'zh';
        // Take gross margins (oldest first for left-to-right time)
        const series = m.slice().reverse().map(q => q.gross).filter(v => typeof v === 'number');
        if (series.length < 2) return '';

        const w = 100, h = 28;
        const min = Math.min(...series);
        const max = Math.max(...series);
        const range = max - min || 1;
        const points = series.map((v, i) => {
            const x = (i / (series.length - 1)) * w;
            const y = h - ((v - min) / range) * (h - 4) - 2;
            return `${x.toFixed(1)},${y.toFixed(1)}`;
        });

        const fillPoints = `0,${h} ${points.join(' ')} ${w},${h}`;
        const trend = series[series.length - 1] - series[0];
        const stroke = trend > 0 ? '#22c55e' : trend < 0 ? '#ef4444' : '#a1a1aa';
        const deltaClass = trend > 0 ? 'delta-up' : trend < 0 ? 'delta-down' : 'delta-flat';
        const deltaStr = (trend >= 0 ? '+' : '') + (trend * 100).toFixed(1) + ' pts';

        return `<div>
            <svg class="ea-sparkline" viewBox="0 0 ${w} ${h}" preserveAspectRatio="none">
                <polygon class="ea-sparkline-fill" points="${fillPoints}" fill="${stroke}"/>
                <polyline points="${points.join(' ')}" stroke="${stroke}"/>
            </svg>
            <div class="ea-sparkline-label">
                <span>${isZh ? '毛利率 8Q' : '8Q Gross Margin'}</span>
                <span class="${deltaClass}">${deltaStr}</span>
            </div>
        </div>`;
    }

    function renderComponentBars(sc) {
        const items = [
            { key: 'quality',   label: 'QUALITY',  val: sc.quality   ?? 0, max: 30, fill: 'q' },
            { key: 'growth',    label: 'GROWTH',   val: sc.growth    ?? 0, max: 30, fill: 'g' },
            { key: 'valuation', label: 'VALUE',    val: sc.valuation ?? 0, max: 25, fill: 'v' },
            { key: 'analyst',   label: 'ANALYST',  val: sc.analyst   ?? 0, max: 15, fill: 'a' },
        ];
        return items.map(it => {
            const pct = Math.max(0, Math.min(100, (it.val / it.max) * 100));
            return `<div class="ea-comp">
                <div class="ea-comp-row">
                    <span class="ea-comp-name">${it.label}</span>
                    <span class="ea-comp-val">${it.val}<span class="max">/${it.max}</span></span>
                </div>
                <div class="ea-comp-bar">
                    <div class="ea-comp-fill ea-comp-fill-${it.fill}" style="width:${pct.toFixed(1)}%"></div>
                </div>
            </div>`;
        }).join('');
    }

    function renderFlagsRow(flags, isZh) {
        if (!flags || !flags.length) {
            return `<div class="ea-meta-pills"><span class="ea-pill ea-pill-clean">${isZh?'✅ 品質乾淨':'✅ Clean'}</span></div>`;
        }
        const labels = {
            accruals_warning:         isZh ? '🟡 應計品質' : '🟡 Accruals',
            capex_outpaces_ocf:       isZh ? '🔴 CapEx 燒錢' : '🔴 CapEx>OCF',
            gross_margin_compression: isZh ? '🟠 毛利壓縮' : '🟠 GM compress',
            dso_slowdown:             isZh ? '🟠 收款放緩' : '🟠 DSO slow',
            negative_fcf:             isZh ? '🔴 FCF 為負' : '🔴 -FCF',
            debt_buildup:             isZh ? '🟠 債務累積' : '🟠 Debt up',
        };
        const html = flags.map(f =>
            `<span class="ea-pill ea-pill-flag">${labels[f] || f}</span>`
        ).join('');
        return `<div class="ea-meta-pills">${html}</div>`;
    }

    function renderFreshness(ageDays, isZh) {
        if (typeof ageDays !== 'number') {
            return { cls: 'ea-freshness-fresh', label: '—', tooltip: '' };
        }
        const ageLabel = ageDays < 1
            ? (isZh ? '今天' : 'today')
            : (isZh ? `${ageDays.toFixed(0)} 天前` : `${ageDays.toFixed(0)}d ago`);
        let cls;
        if (ageDays <= 14)      cls = 'ea-freshness-fresh';
        else if (ageDays <= 45) cls = 'ea-freshness-aging';
        else                    cls = 'ea-freshness-stale';
        return { cls, label: ageLabel, tooltip: isZh ? '財報快取新鮮度' : 'Cache freshness' };
    }

    // ── Action delegation (view report / re-run) ─────────────────────────
    document.addEventListener('click', (e) => {
        const btn = e.target.closest('.ea-act-btn');
        if (!btn) return;
        const action = btn.dataset.action;
        if (action === 'view') {
            const path = btn.dataset.path;
            if (path && window.UI?.viewReport) {
                window.UI.viewReport(path);
            }
        } else if (action === 'rerun') {
            runEarnings(btn.dataset.ticker);
        }
    });

    // ── Animate score numbers when grid renders ──────────────────────────
    // Use IntersectionObserver to count up score nums as they reveal
    const scoreObserver = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (!entry.isIntersecting) return;
            const el = entry.target;
            if (el.dataset.animated) return;
            el.dataset.animated = '1';
            animateCount(el, parseInt(el.dataset.target, 10), 520);
            scoreObserver.unobserve(el);
        });
    }, { threshold: 0.4 });

    // Re-attach observer after grid renders
    const gridObserver = new MutationObserver(() => {
        document.querySelectorAll('.ea-card .ea-anim-num[data-target]').forEach(el => {
            if (!el.dataset.animated) scoreObserver.observe(el);
        });
    });
    document.addEventListener('DOMContentLoaded', () => {
        const grid = document.getElementById('ea-grid');
        if (grid) gridObserver.observe(grid, { childList: true, subtree: false });
    });

})();
