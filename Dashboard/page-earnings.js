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
    // V2.15.1 — ticker → {date, days_until} for upcoming earnings (fmp_confirmed).
    // Built from data.json upcoming_events on each load. Used by the command-bar
    // input listener to morph button + show hint as user types.
    let upcomingEarningsMap = {};

    const VERDICTS = ['STRONG', 'SOLID', 'MIXED', 'WEAK', 'DETERIORATING'];

    const filterState = {
        sort:         localStorage.getItem('ea_sort')         || 'score-desc',
        verdicts:     new Set(JSON.parse(localStorage.getItem('ea_verdicts') || JSON.stringify(VERDICTS))),
        flags:        localStorage.getItem('ea_flags')        || 'any', // 'any' | 'clean' | 'has'
        search:       '',  // V2.8.2 — ticker substring filter
    };

    const RECENT_KEY = 'ea_recent_tickers';
    const RECENT_MAX = 5;

    // V2.13.7 — earnings-scoped run banner state
    let _eaPollTimer    = null;
    let _eaActiveJobId  = null;
    let _eaActiveTicker = null;
    // V2.15.3 — track which mode is active so done banner can show the right
    // post-success affordance (重新整理 for earnings vs 看前瞻報告 for preview).
    let _eaActiveMode   = null;  // 'earnings' | 'earnings_preview' | null

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
        wirePreviewModal();
        wireEarningsRunBanner();
        resumeEarningsRunBanner();

        await loadAndRender();

        if (window.DataStore) {
            window.DataStore.subscribe((data) => {
                allAnalyses = Array.isArray(data?.earnings_analyses) ? data.earnings_analyses : [];
                lastUpdatedAt = data?.last_updated;
                rebuildUpcomingEarningsMap(data?.upcoming_events);
                renderAll();
            });
        }
    });

    // V2.15.1 — build ticker → nearest-future-earnings-date map from data.json
    // upcoming_events. Source events come from FMP earnings calendar (all
    // fmp_confirmed by definition). Multiple future events → keep nearest.
    function rebuildUpcomingEarningsMap(upcomingEvents) {
        upcomingEarningsMap = {};
        if (!Array.isArray(upcomingEvents)) return;
        const today = new Date();
        today.setHours(0, 0, 0, 0);
        for (const e of upcomingEvents) {
            if (e.category !== 'earnings' || !e.date) continue;
            const evd = new Date(e.date);
            if (isNaN(evd.getTime())) continue;
            const days = Math.round((evd - today) / 86400000);
            if (days < 0) continue;  // past — skip
            for (const t of (Array.isArray(e.tickers) ? e.tickers : [])) {
                const key = String(t).toUpperCase();
                const prev = upcomingEarningsMap[key];
                if (!prev || days < prev.days_until) {
                    upcomingEarningsMap[key] = { date: e.date, days_until: days };
                }
            }
        }
    }

    async function loadAndRender() {
        try {
            const data = window.DataStore
                ? await window.DataStore.get()
                : await fetch('data.json', { cache: 'no-store' }).then(r => r.json());
            allAnalyses = Array.isArray(data?.earnings_analyses) ? data.earnings_analyses : [];
            lastUpdatedAt = data?.last_updated;
            rebuildUpcomingEarningsMap(data?.upcoming_events);
            // V2.19.2 — populate watchlist set for ⚡ badge in card render
            window.UI = window.UI || {};
            window.UI.watchlistSet = new Set(((data?.structural_watchlist || {}).candidates || []).map(c => c.ticker));
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

        // Verdict chips (V2.20.0 — i18n + signal-tip on chips)
        const VERDICT_CHIP_ZH = { STRONG: '強勁', SOLID: '穩健', MIXED: '混合', WEAK: '疲軟', DETERIORATING: '惡化' };
        const vWrap = document.getElementById('ea-verdict-chips');
        vWrap.innerHTML = VERDICTS.map(v => {
            const active = filterState.verdicts.has(v) ? 'active' : '';
            const klass = `ea-chip-${v.toLowerCase()}`;
            const lbl = isZh ? (VERDICT_CHIP_ZH[v] || v) : v;
            return `<button class="ea-chip ${klass} ${active}" data-verdict="${v}" data-signal-tip="verdict_${v.toLowerCase()}" type="button"><span>${lbl}</span></button>`;
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
            filterState.search = '';
            localStorage.removeItem('ea_sort');
            localStorage.removeItem('ea_verdicts');
            localStorage.removeItem('ea_flags');
            const si = document.getElementById('ea-search-input');
            if (si) si.value = '';
            renderFilterBar();
            renderGrid();
        });

        // V2.8.2 — ticker search input
        const searchInput = document.getElementById('ea-search-input');
        if (searchInput) {
            searchInput.addEventListener('input', (e) => {
                filterState.search = (e.target.value || '').trim();
                renderGrid();
            });
        }
    }

    // ── Command bar ──────────────────────────────────────────────────────
    function wireCommandBar() {
        const input = document.getElementById('ea-ticker-input');
        const btn = document.getElementById('ea-run-btn');
        const label = document.getElementById('ea-run-label');
        const hint = document.getElementById('ea-cmd-hint');
        const placeholders = ['NVDA', 'AAPL', 'MSFT', 'AVGO', 'META'];
        let phIdx = Math.floor(Math.random() * placeholders.length);
        input.placeholder = placeholders[phIdx];
        setInterval(() => {
            if (document.activeElement === input) return;
            phIdx = (phIdx + 1) % placeholders.length;
            input.placeholder = placeholders[phIdx];
        }, 3500);

        // V2.15.1 — morph button + show hint based on upcomingEarningsMap match
        // Mode buckets:
        //   "preview" — fmp_confirmed earnings within 0-7 days → button=📋 amber + hint
        //   "soon"    — fmp_confirmed earnings within 8-30 days → button=🔄 default + info hint
        //   "post"    — no upcoming match → button=🔄 default + analyze-last-quarter hint
        //   "empty"   — input empty → reset
        function syncMode() {
            const t = (input.value || '').trim().toUpperCase();
            if (!t) {
                label.textContent = UI.currentLang === 'zh' ? '執行' : 'Run';
                btn.classList.remove('ea-cmdbar-btn-preview');
                btn.dataset.mode = 'post';
                if (hint) { hint.textContent = ''; hint.dataset.mode = 'empty'; }
                return;
            }
            const isZh = UI.currentLang === 'zh';
            const match = upcomingEarningsMap[t];
            if (match && match.days_until >= 0 && match.days_until <= 7) {
                label.textContent = isZh ? '📋 財報前瞻' : '📋 Preview';
                btn.classList.add('ea-cmdbar-btn-preview');
                btn.dataset.mode = 'preview';
                if (hint) {
                    hint.textContent = isZh
                        ? `⚡ ${t} 下次財報 ${match.date}（${match.days_until}d）→ 跑前瞻 cheat sheet`
                        : `⚡ Next ${t} earnings ${match.date} (${match.days_until}d) → run preview cheat sheet`;
                    hint.dataset.mode = 'preview';
                }
            } else if (match && match.days_until <= 30) {
                label.textContent = isZh ? '執行' : 'Run';
                btn.classList.remove('ea-cmdbar-btn-preview');
                btn.dataset.mode = 'post';
                if (hint) {
                    hint.textContent = isZh
                        ? `📅 ${t} 下次財報 ${match.date}（${match.days_until}d）→ 跑分析上季（前瞻在 7d 內才開放）`
                        : `📅 Next ${t} earnings ${match.date} (${match.days_until}d) → run last-quarter analysis (preview opens at ≤7d)`;
                    hint.dataset.mode = 'soon';
                }
            } else {
                label.textContent = isZh ? '執行' : 'Run';
                btn.classList.remove('ea-cmdbar-btn-preview');
                btn.dataset.mode = 'post';
                if (hint) {
                    hint.textContent = isZh
                        ? `📊 ${t} 無近期 FMP 確認財報日 → 跑分析上季`
                        : `📊 No FMP-confirmed upcoming earnings for ${t} → run last-quarter analysis`;
                    hint.dataset.mode = 'post';
                }
            }
        }

        const trigger = () => {
            const t = (input.value || '').trim().toUpperCase();
            if (!t) {
                UI.showToast(UI.currentLang === 'zh' ? '請先輸入 ticker' : 'Enter a ticker first', 'warn');
                return;
            }
            const mode = btn.dataset.mode;
            input.value = '';
            syncMode();
            if (mode === 'preview') runEarningsPreview(t);
            else                    runEarnings(t);
        };

        btn.addEventListener('click', trigger);
        input.addEventListener('input', syncMode);
        input.addEventListener('keydown', (e) => {
            if (e.key === 'Enter') { e.preventDefault(); trigger(); }
        });
        // Initial state
        syncMode();
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

    // V2.15.0 — fork of runEarnings for pre-earnings preview mode (forecaster --pre-earnings).
    // Routes through SCRIPT_PROTOCOLS path on server (no Claude turn).
    async function runEarningsPreview(ticker) {
        ticker = (ticker || '').toUpperCase();
        if (!ticker) return;
        const lang = UI.currentLang;
        try {
            const r = await fetch('/api/protocol-queue', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ name: 'earnings_preview', ticker })
            });
            const body = await r.json();
            if (r.status === 202 && body.queued) {
                pushRecentTicker(ticker);
                const pos = body.position || '?';
                UI.showToast(lang === 'zh' ? `已排入財報前瞻:${ticker}(第 ${pos} 位)` : `Queued preview: ${ticker} (#${pos})`, 'info');
                _eaActiveJobId  = body.id;
                _eaActiveTicker = ticker;
                _eaActiveMode   = 'earnings_preview';
                if (pos === 1 && (body.total_ahead || 0) === 0) {
                    eaShowRunBanner(ticker, lang === 'zh' ? '財報前瞻啟動中…' : 'Preview starting…');
                }
                if (_eaPollTimer) clearInterval(_eaPollTimer);
                _eaPollTimer = setInterval(pollEarningsRunStatus, 2000);
            } else if (r.status === 409 && body.reason === 'duplicate_active') {
                UI.showToast(lang === 'zh' ? `${ticker} 前瞻已在執行中` : `${ticker} preview already running`, 'warn');
            } else if (r.status === 409 && body.reason === 'duplicate_pending') {
                UI.showToast(lang === 'zh' ? `${ticker} 前瞻已在佇列` : `${ticker} preview already queued`, 'warn');
            } else {
                UI.showToast(lang === 'zh' ? `加入失敗:${body.error || r.status}` : `Failed: ${body.error || r.status}`, 'error');
            }
        } catch (e) {
            UI.showToast(lang === 'zh' ? `網路錯誤:${e.message}` : `Network error: ${e.message}`, 'error');
        }
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
                _eaActiveJobId  = body.id;
                _eaActiveTicker = ticker;
                _eaActiveMode   = 'earnings';
                if (pos === 1 && (body.total_ahead || 0) === 0) {
                    eaShowRunBanner(ticker, lang === 'zh' ? '啟動中…' : 'Starting…');
                }
                if (_eaPollTimer) clearInterval(_eaPollTimer);
                _eaPollTimer = setInterval(pollEarningsRunStatus, 2000);
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

    // ── Run banner (V2.13.7) ─────────────────────────────────────────────
    function eaFormatElapsed(sec) {
        const m = String(Math.floor((sec || 0) / 60)).padStart(2, '0');
        const s = String((sec || 0) % 60).padStart(2, '0');
        return `${m}:${s}`;
    }

    function eaShowRunBanner(ticker, detail) {
        const banner = document.getElementById('ea-run-banner');
        if (!banner) return;
        const isZh = UI.currentLang === 'zh';
        const isPreview = _eaActiveMode === 'earnings_preview';
        banner.classList.remove('hidden', 'border-l-emerald-500', 'border-l-red-500');
        document.getElementById('ea-run-icon').innerHTML =
            '<span class="inline-block w-2 h-2 rounded-full bg-purple-500 animate-pulse"></span>';
        document.getElementById('ea-run-title').textContent =
            (isPreview ? (isZh ? '財報前瞻中 · ' : 'Preview · ')
                       : (isZh ? '財報分析中 · ' : 'Earnings · ')) + (ticker || '');
        document.getElementById('ea-run-detail').textContent = detail || '';
        document.getElementById('ea-run-elapsed').textContent = '00:00';
        document.getElementById('ea-run-cancel').classList.remove('hidden');
        document.getElementById('ea-run-reload')?.classList.add('hidden');
        document.getElementById('ea-run-view-report')?.classList.add('hidden');
    }

    // V2.15.3 — done banner branches by mode:
    //   earnings_preview → show 📄 看前瞻報告 link (opens reports/<DATE>_<T>_pre_earnings.md)
    //   earnings         → show 重新整理 button (existing behaviour, picks up new card)
    function eaSetRunBannerDone(ticker) {
        const banner = document.getElementById('ea-run-banner');
        if (!banner) return;
        const isZh = UI.currentLang === 'zh';
        const isPreview = _eaActiveMode === 'earnings_preview';
        banner.classList.remove('border-l-blue-500', 'border-l-red-500');
        banner.classList.add('border-l-emerald-500');
        document.getElementById('ea-run-icon').innerHTML =
            '<span class="text-emerald-400 font-bold">✓</span>';
        document.getElementById('ea-run-title').textContent =
            (isPreview ? (isZh ? '財報前瞻完成 · ' : 'Preview done · ')
                       : (isZh ? '財報分析完成 · ' : 'Earnings done · ')) + (ticker || '');
        document.getElementById('ea-run-detail').textContent = '';
        document.getElementById('ea-run-cancel').classList.add('hidden');

        const reloadBtn = document.getElementById('ea-run-reload');
        const viewBtn   = document.getElementById('ea-run-view-report');
        if (isPreview && ticker && viewBtn) {
            // V2.16.0 — clicks open card-view modal (not raw MD). Convert <a> to button-style behavior.
            viewBtn.removeAttribute('href');
            viewBtn.removeAttribute('target');
            viewBtn.style.cursor = 'pointer';
            viewBtn.onclick = (e) => { e.preventDefault(); openPreviewModal(ticker.toUpperCase()); };
            const lbl = document.getElementById('ea-run-view-report-label');
            if (lbl) lbl.textContent = isZh ? '看前瞻報告' : 'View report';
            viewBtn.classList.remove('hidden');
            reloadBtn?.classList.add('hidden');
        } else {
            viewBtn?.classList.add('hidden');
            reloadBtn?.classList.remove('hidden');
        }
    }

    function eaSetRunBannerError(msg) {
        const banner = document.getElementById('ea-run-banner');
        if (!banner) return;
        banner.classList.remove('border-l-blue-500', 'border-l-emerald-500');
        banner.classList.add('border-l-red-500');
        document.getElementById('ea-run-icon').innerHTML =
            '<span class="text-red-400 font-bold">✗</span>';
        document.getElementById('ea-run-title').textContent = msg || 'Error';
        document.getElementById('ea-run-detail').textContent = '';
        document.getElementById('ea-run-cancel').classList.add('hidden');
        document.getElementById('ea-run-reload')?.classList.remove('hidden');
    }

    async function pollEarningsRunStatus() {
        try {
            const r = await fetch('/api/run-protocol/status');
            if (!r.ok) return;
            const s = await r.json();
            // Gate: only react when the running protocol is earnings AND it's
            // either our queued job (matching id) or — at minimum — earnings.
            // queue_id may not be exposed; fall back to name + ticker match.
            const isEarnings = s.name === 'earnings' || s.name === 'earnings_preview';
            const matchesId  = _eaActiveJobId && s.queue_id === _eaActiveJobId;
            const matchesTicker = _eaActiveTicker && (s.analyze_ticker === _eaActiveTicker || s.ticker === _eaActiveTicker);
            if (!isEarnings || (!matchesId && !matchesTicker)) {
                // Not my job yet — keep polling silently while queued.
                return;
            }
            // It's my earnings run. Show banner if not yet visible.
            const banner = document.getElementById('ea-run-banner');
            if (banner && banner.classList.contains('hidden') && s.status === 'running') {
                eaShowRunBanner(_eaActiveTicker || s.analyze_ticker || s.ticker, UI.currentLang === 'zh' ? 'Claude 處理中…' : 'Claude is processing…');
            }
            document.getElementById('ea-run-elapsed').textContent = eaFormatElapsed(s.elapsed_sec || 0);
            const logEl = document.getElementById('ea-run-log');
            if (logEl && typeof s.log_tail === 'string' && s.log_tail !== logEl.textContent) {
                const pinned = Math.abs(logEl.scrollHeight - logEl.clientHeight - logEl.scrollTop) < 40;
                logEl.textContent = s.log_tail;
                if (pinned) logEl.scrollTop = logEl.scrollHeight;
            }
            if (s.status !== 'running') {
                if (_eaPollTimer) { clearInterval(_eaPollTimer); _eaPollTimer = null; }
                if (s.status === 'done') {
                    // Backfill mode from server name if banner was resumed without it
                    if (!_eaActiveMode && s.name) _eaActiveMode = s.name;
                    eaSetRunBannerDone(_eaActiveTicker || s.analyze_ticker || s.ticker);
                    // Skip data.json reload for preview — it doesn't update earnings_analyses
                    if (_eaActiveMode !== 'earnings_preview') {
                        setTimeout(() => loadAndRender(), 2500);
                    }
                } else {
                    eaSetRunBannerError(s.error || s.status);
                }
                _eaActiveJobId  = null;
                _eaActiveTicker = null;
                // Don't clear _eaActiveMode here — done banner stays visible until
                // user dismisses; clearing would break re-render of the right button.
            }
        } catch (e) { /* ignore */ }
    }

    function wireEarningsRunBanner() {
        document.getElementById('ea-run-expand')?.addEventListener('click', () => {
            const panel = document.getElementById('ea-run-panel');
            const btn   = document.getElementById('ea-run-expand');
            if (!panel) return;
            const open = panel.classList.toggle('hidden') === false;
            if (btn) btn.textContent = open ? '收起' : '展開';
            if (open) {
                const log = document.getElementById('ea-run-log');
                if (log) log.scrollTop = log.scrollHeight;
            }
        });
        document.getElementById('ea-run-cancel')?.addEventListener('click', async () => {
            try { await fetch('/api/run-protocol/cancel', { method: 'POST' }); } catch (e) { /* ignore */ }
        });
        document.getElementById('ea-run-dismiss')?.addEventListener('click', () => {
            document.getElementById('ea-run-banner')?.classList.add('hidden');
            _eaActiveMode = null;
            try { sessionStorage.setItem('ea_banner_dismissed', String(Date.now())); } catch (e) { /* ignore */ }
        });
        document.getElementById('ea-run-reload')?.addEventListener('click', () => {
            try { sessionStorage.setItem('ea_banner_dismissed', String(Date.now())); } catch (e) { /* ignore */ }
            location.reload();
        });
    }

    // Resume banner on page load when an earnings run is currently in flight
    // (e.g. user reloaded the tab during a long analysis).
    async function resumeEarningsRunBanner() {
        try {
            const dismissedAt = parseInt(sessionStorage.getItem('ea_banner_dismissed') || '0', 10);
            if (dismissedAt && (Date.now() - dismissedAt) < 30000) {
                sessionStorage.removeItem('ea_banner_dismissed');
                return;
            }
            const r = await fetch('/api/run-protocol/status');
            if (!r.ok) return;
            const s = await r.json();
            if (s.status === 'running' && s.name === 'earnings') {
                _eaActiveTicker = s.analyze_ticker || s.ticker || null;
                eaShowRunBanner(_eaActiveTicker, UI.currentLang === 'zh' ? 'Claude 處理中…' : 'Claude is processing…');
                if (_eaPollTimer) clearInterval(_eaPollTimer);
                _eaPollTimer = setInterval(pollEarningsRunStatus, 2000);
            }
        } catch (e) { /* ignore */ }
    }

    // ── V2.16.0 Pre-earnings Preview Modal ───────────────────────────────
    function wirePreviewModal() {
        const modal = document.getElementById('ea-preview-modal');
        if (!modal) return;
        document.getElementById('ea-preview-close')?.addEventListener('click', closePreviewModal);
        modal.addEventListener('click', (e) => {
            if (e.target === modal) closePreviewModal();
        });
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && modal.style.display !== 'none') closePreviewModal();
        });
    }

    function closePreviewModal() {
        const modal = document.getElementById('ea-preview-modal');
        if (modal) {
            modal.style.display = 'none';
            modal.classList.add('hidden');
        }
    }

    function openPreviewModal(ticker) {
        ticker = (ticker || '').toUpperCase();
        if (!ticker) return;
        const modal = document.getElementById('ea-preview-modal');
        const body  = document.getElementById('ea-preview-body');
        const titleEl = document.getElementById('ea-preview-modal-title');
        const mdLink  = document.getElementById('ea-preview-md-link');
        if (!modal || !body) return;
        modal.style.display = 'flex';
        modal.classList.remove('hidden');
        const isZh = UI.currentLang === 'zh';
        titleEl.textContent = `${ticker} · ${isZh ? '財報前瞻' : 'Pre-Earnings Preview'}`;
        body.innerHTML = `<div class="ea-pv-error">${isZh ? '載入中…' : 'Loading…'}</div>`;
        if (mdLink) {
            const now = new Date();
            const stamp = now.getFullYear() + String(now.getMonth()+1).padStart(2,'0') + String(now.getDate()).padStart(2,'0');
            mdLink.href = `/reports/${stamp}_${ticker}_pre_earnings.md`;
            mdLink.classList.remove('hidden');
        }
        fetch(`/api/preview-cache/${encodeURIComponent(ticker)}`)
            .then(r => {
                if (r.status === 404) throw new Error('no-cache');
                if (!r.ok) throw new Error(`http ${r.status}`);
                return r.json();
            })
            .then(data => renderPreviewModal(body, data, isZh))
            .catch(err => {
                const msg = err.message === 'no-cache'
                    ? (isZh ? '前瞻 cache 不存在 — 先點「📋 財報前瞻」跑一次再回來' : 'No preview cache — run preview first then reopen')
                    : (isZh ? `載入失敗:${err.message}` : `Load failed: ${err.message}`);
                body.innerHTML = `<div class="ea-pv-error">${msg}</div>`;
            });
    }

    function renderPreviewModal(body, data, isZh) {
        const ticker = data.ticker;
        const pe   = data.pre_earnings || {};
        const nxt  = pe.next_earnings || {};
        const seas = pe.seasonality_4q || [];
        const watch = pe.watch_metrics || [];
        const scenarios = data.scenarios;  // null when negative_eps
        const isNeg = !!data.negative_eps;

        // Header card
        const days = nxt.days_until;
        const cdClass = (days === 0) ? 'ea-pv-cd-today' : '';
        const cdLabel = (days == null) ? (isZh ? '無確認日期' : 'Date unknown')
                       : (days === 0)  ? (isZh ? '今天' : 'Today')
                       : (days === 1)  ? (isZh ? '明天' : 'Tomorrow')
                       :                 (isZh ? `${days} 天後` : `In ${days}d`);
        const dateStr = nxt.date || '—';
        const headerCard = `
            <div class="ea-pv-section">
                <div class="ea-pv-header-card">
                    <div class="ea-pv-header-logo">${ticker.slice(0,4)}</div>
                    <div class="ea-pv-header-meta">
                        <div class="ea-pv-header-ticker">${ticker}</div>
                        <div class="ea-pv-header-name">${isZh?'下次財報':'Next earnings'}: ${dateStr}</div>
                        <div class="ea-pv-countdown ${cdClass}">📅 ${cdLabel}</div>
                    </div>
                    <div class="ea-pv-price">
                        $${data.current_price ?? '—'}
                        <div class="ea-pv-price-sub">${isZh?'TTM EPS':'TTM EPS'}: $${data.ttm_eps ?? '—'}${isNeg ? ' ⚠' : ''}</div>
                    </div>
                </div>
            </div>`;

        // Consensus card
        const epsE = nxt.eps_estimated;
        const revE = nxt.rev_estimated;
        const epsCls = (epsE != null && epsE < 0) ? 'ea-pv-neg' : '';
        const consensusCard = `
            <div class="ea-pv-section">
                <div class="ea-pv-section-label">${isZh?'Street 共識（本季）':'Street Consensus (this Q)'}</div>
                <div class="ea-pv-stats">
                    <div class="ea-pv-stat">
                        <div class="ea-pv-stat-label">EPS estimate</div>
                        <div class="ea-pv-stat-value ${epsCls}">${epsE != null ? '$'+epsE : '—'}</div>
                    </div>
                    <div class="ea-pv-stat">
                        <div class="ea-pv-stat-label">Revenue estimate</div>
                        <div class="ea-pv-stat-value">${revE != null ? '$'+(revE/1e9).toFixed(2)+'B' : '—'}</div>
                    </div>
                </div>
            </div>`;

        // Seasonality SVG (revenue bars + GM% line)
        const seasonalityCard = renderSeasonalitySection(seas, isZh);

        // Watch list chips
        const chipIcons = ['📊','🎯','💼','🔮','🧩','📈'];
        const watchChips = watch.length === 0
            ? `<div class="ea-pv-chip-hint">${isZh?'無 watch list':'No watch metrics'}</div>`
            : watch.map((w, i) => {
                const [zh, en, hint] = Array.isArray(w) ? w : [w, w, ''];
                const title = isZh ? zh : en;
                return `<div class="ea-pv-chip" title="${(hint||'').replace(/"/g,'&quot;')}">
                    <div class="ea-pv-chip-title">${chipIcons[i % chipIcons.length]} ${title}</div>
                    <div class="ea-pv-chip-hint">${hint || ''}</div>
                </div>`;
            }).join('');
        const watchCard = `
            <div class="ea-pv-section">
                <div class="ea-pv-section-label">${isZh?'本季 Watch List':'This Quarter Watch List'}</div>
                <div class="ea-pv-watch-chips">${watchChips}</div>
            </div>`;

        // 12M Scenarios (PE-based by default; P/S-based when negative-EPS path supplies method='ps')
        let scenariosCard;
        if (scenarios) {
            const fmtUp = (p) => (p > 0 ? '+' : '') + p.toFixed(1) + '%';
            const isPS = scenarios.method === 'ps';
            const sectionLabel = isPS
                ? (isZh ? '12M Target Price · P/S 法（負 EPS）' : '12M Target Price · P/S method (negative EPS)')
                : '12M Target Price';
            const psMeta = isPS
                ? `<div class="ea-pv-chip-hint" style="margin-bottom:8px">${isZh
                    ? `TTM 營收 $${scenarios.ttm_revenue_b}B · 當前 P/S ${scenarios.current_ps}x · 近期 YoY ${scenarios.recent_yoy_pct}%`
                    : `TTM rev $${scenarios.ttm_revenue_b}B · current P/S ${scenarios.current_ps}x · recent YoY ${scenarios.recent_yoy_pct}%`}</div>`
                : '';
            scenariosCard = `
                <div class="ea-pv-section">
                    <div class="ea-pv-section-label">${sectionLabel}</div>
                    ${psMeta}
                    <div class="ea-pv-scenarios">
                        <div class="ea-pv-scen ea-pv-scen-bull">
                            <div class="ea-pv-scen-icon">🐂</div>
                            <div class="ea-pv-scen-name">Bull</div>
                            <div class="ea-pv-scen-target">$${scenarios.bull.target}</div>
                            <div class="ea-pv-scen-upside">${fmtUp(scenarios.bull.upside_pct)}</div>
                            <div class="ea-pv-scen-trigger">${scenarios.bull.achieves_if || '—'}</div>
                        </div>
                        <div class="ea-pv-scen ea-pv-scen-base">
                            <div class="ea-pv-scen-icon">📊</div>
                            <div class="ea-pv-scen-name">Base</div>
                            <div class="ea-pv-scen-target">$${scenarios.base.target}</div>
                            <div class="ea-pv-scen-upside">${fmtUp(scenarios.base.upside_pct)}</div>
                            <div class="ea-pv-scen-trigger">${scenarios.base.achieves_if || '—'}</div>
                        </div>
                        <div class="ea-pv-scen ea-pv-scen-bear">
                            <div class="ea-pv-scen-icon">🐻</div>
                            <div class="ea-pv-scen-name">Bear</div>
                            <div class="ea-pv-scen-target">$${scenarios.bear.target}</div>
                            <div class="ea-pv-scen-upside">${fmtUp(scenarios.bear.upside_pct)}</div>
                            <div class="ea-pv-scen-trigger">${scenarios.bear.achieves_if || '—'}</div>
                        </div>
                    </div>
                </div>`;
        } else {
            scenariosCard = `
                <div class="ea-pv-section">
                    <div class="ea-pv-section-label">12M Target Price</div>
                    <div class="ea-pv-scen-na">⚠ ${isZh?'TTM EPS ≤ 0 且 P/S 推算數據不足 — 跳過':'TTM EPS ≤ 0 and P/S inputs unavailable — skipped'}</div>
                </div>`;
        }

        // Caveats
        const caveatsCard = `
            <details class="ea-pv-caveats">
                <summary>${isZh?'⚠ Caveats':'⚠ Caveats'}</summary>
                <div style="margin-top:8px">
                  • ${isZh?'Consensus EPS / Rev 來源 FMP `/earnings`，不含 whisper number':'Consensus EPS / Rev sourced from FMP /earnings — whisper numbers not available on free tier'}<br>
                  • ${isZh?'Watch list 來源：earnings-analyst cache（若有）+ generic fallback':'Watch list source: earnings-analyst cache (if present) + generic fallback'}<br>
                  • ${isZh?'12M target 為長期估值參考，不直接預測本季 beat/miss':'12M target is long-term valuation reference, not a beat/miss predictor'}<br>
                  • ${isZh?'Generated':'Generated'} ${data.generated_at || '—'} · cache age ${Math.round((data.cache_age_sec || 0)/60)}m
                </div>
            </details>`;

        body.innerHTML = headerCard + consensusCard + seasonalityCard + watchCard + scenariosCard + caveatsCard;
    }

    function renderSeasonalitySection(seas, isZh) {
        if (!seas.length) {
            return `<div class="ea-pv-section">
                <div class="ea-pv-section-label">${isZh?'過去 4Q Seasonality':'Past 4Q Seasonality'}</div>
                <div class="ea-pv-chip-hint">${isZh?'無季度數據':'No quarterly data'}</div>
            </div>`;
        }
        // Compute SVG dimensions
        const W = 760, H = 130, padL = 36, padR = 36, padT = 18, padB = 30;
        const innerW = W - padL - padR;
        const innerH = H - padT - padB;
        const n = seas.length;
        const barGap = innerW / n;
        const barW = barGap * 0.55;
        const revs = seas.map(q => q.revenue || 0);
        const gms  = seas.map(q => q.gross_margin_pct);
        const maxRev = Math.max(...revs, 1);
        const minGm = Math.min(...gms.filter(v => v != null), 100);
        const maxGm = Math.max(...gms.filter(v => v != null), 0);
        const gmSpan = Math.max(maxGm - minGm, 1);

        // Bar rectangles + labels
        const bars = seas.map((q, i) => {
            const x = padL + i * barGap + (barGap - barW) / 2;
            const h = (q.revenue || 0) / maxRev * innerH;
            const y = padT + innerH - h;
            const revB = (q.revenue / 1e9).toFixed(2);
            return `<rect x="${x}" y="${y}" width="${barW}" height="${h}" rx="3" fill="rgba(251,191,36,0.55)" />
                    <text x="${x + barW/2}" y="${y - 4}" text-anchor="middle" font-size="10" fill="#fbbf24" font-family="JetBrains Mono">$${revB}B</text>
                    <text x="${x + barW/2}" y="${H - padB + 14}" text-anchor="middle" font-size="9" fill="#a1a1aa" font-family="JetBrains Mono">${q.period || ''}</text>`;
        }).join('');

        // GM% polyline (mapped to inner area, separate Y-scale)
        const points = seas.map((q, i) => {
            if (q.gross_margin_pct == null) return null;
            const x = padL + i * barGap + barGap / 2;
            const yPct = (q.gross_margin_pct - minGm) / gmSpan;
            const y = padT + innerH - yPct * innerH * 0.7 - innerH * 0.15; // GM% sits in top 70% region
            return `${x},${y}`;
        }).filter(Boolean).join(' ');
        const gmCircles = seas.map((q, i) => {
            if (q.gross_margin_pct == null) return '';
            const x = padL + i * barGap + barGap / 2;
            const yPct = (q.gross_margin_pct - minGm) / gmSpan;
            const y = padT + innerH - yPct * innerH * 0.7 - innerH * 0.15;
            // Bar revenue label sits at (barTop - 4). Place GM% label below circle when
            // it would otherwise crowd the bar-top label (within ~14px). Otherwise above.
            const barH = (q.revenue || 0) / maxRev * innerH;
            const barTopY = padT + innerH - barH;
            const above = (y > barTopY + 14);  // safe to put label above circle
            const labelY = above ? (y - 6) : (y + 12);
            return `<circle cx="${x}" cy="${y}" r="3" fill="#10b981" />
                    <text x="${x + 8}" y="${labelY}" font-size="9" fill="#10b981" font-family="JetBrains Mono">${q.gross_margin_pct.toFixed(0)}%</text>`;
        }).join('');

        const svg = `<svg class="ea-pv-chart" viewBox="0 0 ${W} ${H}" preserveAspectRatio="xMidYMid meet">
            ${bars}
            <polyline points="${points}" fill="none" stroke="#10b981" stroke-width="1.5" stroke-dasharray="3 2" />
            ${gmCircles}
        </svg>
        <div class="ea-pv-chart-legend">
            <span><span class="ea-pv-chart-legend-dot" style="background:rgba(251,191,36,0.55)"></span>${isZh?'營收 (USD)':'Revenue (USD)'}</span>
            <span><span class="ea-pv-chart-legend-dot" style="background:#10b981;border-radius:50%"></span>${isZh?'毛利率 %':'Gross Margin %'}</span>
        </div>`;

        return `<div class="ea-pv-section">
            <div class="ea-pv-section-label">${isZh?'過去 4Q Seasonality':'Past 4Q Seasonality'}</div>
            ${svg}
        </div>`;
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

        // V2.8.2 — ticker substring search
        if (filterState.search) {
            const q = filterState.search.toUpperCase();
            rows = rows.filter(r => (r.ticker || '').toUpperCase().includes(q));
        }

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
        // V2.20.0 — verdict i18n (zh / en) — display only; filter chips uses raw key
        const VERDICT_LABEL_ZH = { STRONG: '強勁', SOLID: '穩健', MIXED: '混合', WEAK: '疲軟', DETERIORATING: '惡化' };
        const verdictLabel = isZh ? (VERDICT_LABEL_ZH[verdict] || verdict) : verdict;
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
        // Buttons (V1.73 — primary now opens infographic page; markdown moved to inline collapse)
        const reportBtn = `<button class="ea-act-btn ea-act-btn-primary" data-action="infographic" data-ticker="${r.ticker}">📊 ${isZh?'Infographic':'Infographic'}${r.has_infographic === false ? ' *' : ''}</button>`;
        // V2.15.0 — morph 重跑 → 📋 財報前瞻 when next earnings is fmp_confirmed AND ≤ 7 days
        let actionBtn;
        if (r.next_earnings_source === 'fmp_confirmed' && r.next_earnings_est) {
            const today = new Date();
            today.setHours(0, 0, 0, 0);
            const ne = new Date(r.next_earnings_est);
            const daysUntil = Math.round((ne - today) / 86400000);
            if (daysUntil >= 0 && daysUntil <= 7) {
                const tipZh = `下次財報 ${r.next_earnings_est}（${daysUntil}d）— 跑前瞻 cheat sheet（forecaster --pre-earnings）`;
                const tipEn = `Next earnings ${r.next_earnings_est} (${daysUntil}d) — run pre-earnings cheat sheet`;
                actionBtn = `<button class="ea-act-btn ea-act-btn-preview" data-action="preview" data-ticker="${r.ticker}" title="${isZh?tipZh:tipEn}">📋 ${isZh?'財報前瞻':'Preview'}</button>`;
            }
        }
        const rerunBtn = actionBtn || `<button class="ea-act-btn" data-action="rerun" data-ticker="${r.ticker}">🔄 ${isZh?'重跑':'Re-run'}</button>`;

        // Meta pills
        const metaPills = [];
        if (r.sector)            metaPills.push(`<span class="ea-pill">${r.sector}</span>`);
        if (r.industry && r.industry !== r.sector) metaPills.push(`<span class="ea-pill">${r.industry}</span>`);
        // V2.13.10/12 — valuation pills (PE TTM + Forward PE + EV/EBITDA)
        const _peStyle = (v) => {
            if (v == null) return '';
            if (v < 0)        return 'background:rgba(239,68,68,0.10);color:#f87171;border-color:rgba(239,68,68,0.30)';
            if (v < 15)       return 'background:rgba(34,197,94,0.10);color:#4ade80;border-color:rgba(34,197,94,0.30)';
            if (v > 30)       return 'background:rgba(234,179,8,0.10);color:#fbbf24;border-color:rgba(234,179,8,0.30)';
            return '';
        };
        const _evStyle = (v) => {
            if (v == null) return '';
            if (v < 0)        return 'background:rgba(239,68,68,0.10);color:#f87171;border-color:rgba(239,68,68,0.30)';
            if (v < 10)       return 'background:rgba(34,197,94,0.10);color:#4ade80;border-color:rgba(34,197,94,0.30)';
            if (v > 20)       return 'background:rgba(234,179,8,0.10);color:#fbbf24;border-color:rgba(234,179,8,0.30)';
            return '';
        };
        if (r.pe_ttm != null) {
            const tip = isZh ? '本益比 (TTM)' : 'P/E ratio (TTM)';
            metaPills.push(`<span class="ea-pill" style="${_peStyle(r.pe_ttm)}" title="${tip}">P/E ${r.pe_ttm.toFixed(1)}</span>`);
        }
        if (r.forward_pe != null) {
            const tip = isZh ? '預估本益比（次年共識 EPS）' : 'Forward P/E (next-FY consensus EPS)';
            metaPills.push(`<span class="ea-pill" style="${_peStyle(r.forward_pe)}" title="${tip}">Fwd ${r.forward_pe.toFixed(1)}</span>`);
        }
        if (r.ev_ebitda != null) {
            const tip = isZh ? 'EV/EBITDA TTM — 跨資本結構估值' : 'EV/EBITDA TTM — capital-structure neutral';
            metaPills.push(`<span class="ea-pill" style="${_evStyle(r.ev_ebitda)}" title="${tip}">EV/EBITDA ${r.ev_ebitda.toFixed(1)}</span>`);
        }
        // V2.8.4 — last earnings pill with fiscal label fallback
        if (r.last_earnings_date) {
            const fiscalPart = r.fiscal_label ? `${r.fiscal_label} · ` : '';
            const lastLabel = isZh ? '最新財報' : 'Last earnings';
            metaPills.push(
                `<span class="ea-pill ea-pill-date" title="${lastLabel}">📅 ${fiscalPart}${r.last_earnings_date}</span>`
            );
        }
        // Next earnings — FMP confirmed (📅) or +91d heuristic fallback (🔮)
        if (r.next_earnings_est) {
            // Bump fiscal quarter by 1 if we know last quarter (e.g. Q4 FY26 → Q1 FY27)
            let nextFiscal = '';
            if (r.fiscal_label) {
                const m = String(r.fiscal_label).match(/Q(\d)\s*FY\s*(\d+)/i);
                if (m) {
                    const q = parseInt(m[1], 10);
                    const fy = parseInt(m[2], 10);
                    const nq = q === 4 ? 1 : q + 1;
                    const nfy = q === 4 ? fy + 1 : fy;
                    nextFiscal = `Q${nq} FY${nfy} · `;
                }
            }
            const isConfirmed = r.next_earnings_source === 'fmp_confirmed';
            const icon  = isConfirmed ? '📅' : '🔮';
            const label = isConfirmed
                ? (isZh ? '下次財報' : 'Next earnings')
                : (isZh ? '下次預估' : 'Next earnings (est.)');
            let tip = label;
            if (isConfirmed && r.next_earnings_eps_estimate != null) {
                tip += ` · EPS est ${r.next_earnings_eps_estimate}`;
                if (r.next_earnings_revenue_estimate != null) {
                    tip += ` · Rev est $${(r.next_earnings_revenue_estimate / 1e9).toFixed(2)}B`;
                }
            }
            metaPills.push(
                `<span class="ea-pill ea-pill-date-next" title="${tip}">${icon} ${nextFiscal}${r.next_earnings_est}</span>`
            );
        }

        return `<div class="ea-card" style="animation-delay:${idx * 60}ms" data-ticker="${r.ticker}">
            <div class="ea-card-stripe ea-card-stripe-${vKey}"></div>

            <div class="ea-score-col">
                <div>
                    <div class="ea-score-num ea-score-num-${vKey}">
                        <span class="ea-anim-num" data-target="${r.composite_score ?? 0}">0</span>
                    </div>
                    <div class="ea-score-suffix">/ 100</div>
                </div>
                <div class="ea-verdict-pill ea-verdict-pill-${vKey}" data-signal-tip="verdict_${vKey}">${verdictLabel}</div>
            </div>

            <div class="ea-data-col">
                <div class="ea-ticker-row">
                    <span class="ea-ticker">${r.ticker}${(window.UI?.watchlistSet?.has?.(r.ticker)) ? ` <span class="watchlist-bolt" data-signal-tip="watchlist_bolt" style="color:#f59e0b;font-size:0.55em;vertical-align:0.4em">⚡</span>` : ''}</span>
                    <span class="ea-company" title="${company}">${company}</span>
                    ${(() => {
                        const tier = (r.structural_shift || {}).tier;
                        if (tier === 'CONFIRMED') return `<span data-signal-tip="structural_shift_confirmed" style="font-size:9px;font-weight:800;padding:2px 6px;border-radius:4px;background:#dc2626;color:white;letter-spacing:0.5px">SHIFT⚡⚡</span>`;
                        if (tier === 'CANDIDATE') return `<span data-signal-tip="structural_shift_candidate" style="font-size:9px;font-weight:800;padding:2px 6px;border-radius:4px;background:#f59e0b;color:white;letter-spacing:0.5px">SHIFT⚡</span>`;
                        return '';
                    })()}
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
        // V2.8.4 — each row gets data-signal-tip pointing to ed_score_<key> in
        // utils.js SIGNAL_TIPS, so hover triggers sector-style explanation card.
        const items = [
            { key: 'quality',   tip: 'ed_score_quality', label: 'QUALITY',  val: sc.quality   ?? 0, max: 30, fill: 'q' },
            { key: 'growth',    tip: 'ed_score_growth',  label: 'GROWTH',   val: sc.growth    ?? 0, max: 30, fill: 'g' },
            { key: 'valuation', tip: 'ed_score_value',   label: 'VALUE',    val: sc.valuation ?? 0, max: 25, fill: 'v' },
            { key: 'analyst',   tip: 'ed_score_analyst', label: 'ANALYST',  val: sc.analyst   ?? 0, max: 15, fill: 'a' },
        ];
        return items.map(it => {
            const pct = Math.max(0, Math.min(100, (it.val / it.max) * 100));
            const pctStr = pct.toFixed(0);
            return `<div class="ea-comp" data-signal-tip="${it.tip}">
                <div class="ea-comp-row">
                    <span class="ea-comp-name">${it.label}</span>
                    <span class="ea-comp-val">${it.val}<span class="max">/${it.max} · ${pctStr}%</span></span>
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

    // ── Action delegation (infographic detail page / re-run / preview) ───
    document.addEventListener('click', (e) => {
        const btn = e.target.closest('.ea-act-btn');
        if (!btn) return;
        const action = btn.dataset.action;
        if (action === 'infographic') {
            const t = btn.dataset.ticker;
            if (t) window.location.href = `earnings-detail.html?ticker=${encodeURIComponent(t)}`;
        } else if (action === 'rerun') {
            runEarnings(btn.dataset.ticker);
        } else if (action === 'preview') {
            runEarningsPreview(btn.dataset.ticker);
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
