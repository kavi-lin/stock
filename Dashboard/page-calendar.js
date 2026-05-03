/**
 * page-calendar.js — Decision Review Calendar Hub
 *
 * Reads `reports/decision_review/event_index_latest.json`, renders a month grid
 * with badges per source, drawer with per-decision retrospective cards, right
 * rail of upcoming events (within event_index), and bottom aggregate stats.
 *
 * "🤖 Ask LLM Review" button copies REVIEW_PROMPT.md + latest event_index JSON
 * to clipboard so user can paste into a fresh Claude conversation.
 */
(function () {
    'use strict';

    // ── Constants ─────────────────────────────────────────────────────────
    const EVENT_INDEX_URL = '/decision_review/event_index_latest.json';
    const REVIEW_PROMPT_URL = '/decision_review/REVIEW_PROMPT.md';
    const DASHBOARD_DATA_URL = '/data.json';

    // Category → display icon (Coming Up rail)
    const CATEGORY_META = {
        'earnings':     { icon: '💼' },
        'macro':        { icon: '🏛️' },
        'econ':         { icon: '📊' },
        'binary':       { icon: '⚠️' },
        'geopolitical': { icon: '⚠️' },
        'system':       { icon: '📅' },
        'watchlist':    { icon: '🎯' },
    };

    const SOURCE_META = {
        'deep-dive':         { icon: '📈', label: 'deep-dive' },
        'sector-scan':       { icon: '📊', label: 'sector' },
        'news-digest':       { icon: '📰', label: 'news' },
        'theme-detector':    { icon: '🎨', label: 'theme' },
        'momentum-screen':   { icon: '💪', label: 'momentum' },
        'thematic-screener': { icon: '🎯', label: 'radar' },
        'earnings-analyzer': { icon: '💼', label: 'earnings' },
        'short-term-weekly': { icon: '📓', label: 'weekly' },
        'postmortem':        { icon: '📓', label: 'postmortem' },
    };

    const VERDICT_META = {
        'hit':     { emoji: '✅', badgeClass: 'cal-badge-hit',     stripeClass: 'cal-card-stripe-hit',     barClass: 'cal-stat-bar-seg-hit',     textClass: 'text-green-500',  key: 'hit'     },
        'miss':    { emoji: '❌', badgeClass: 'cal-badge-miss',    stripeClass: 'cal-card-stripe-miss',    barClass: 'cal-stat-bar-seg-miss',    textClass: 'text-red-500',    key: 'miss'    },
        'neutral': { emoji: '⚪', badgeClass: 'cal-badge-neutral', stripeClass: 'cal-card-stripe-neutral', barClass: 'cal-stat-bar-seg-neutral', textClass: 'text-yellow-500', key: 'neutral' },
        'pending': { emoji: '⏳', badgeClass: 'cal-badge-pending', stripeClass: 'cal-card-stripe-pending', barClass: 'cal-stat-bar-seg-pending', textClass: 'text-zinc-400',   key: 'pending' },
        'n/a':     { emoji: '—',  badgeClass: 'cal-badge-na',      stripeClass: 'cal-card-stripe-na',      barClass: 'cal-stat-bar-seg-na',      textClass: 'text-zinc-500',   key: 'n/a'     },
    };

    // ── State ─────────────────────────────────────────────────────────────
    let allDecisions = [];
    let recentAnalysis = [];           // raw from data.json:recent_analysis[] (primary source)
    let watchlistTickers = new Set();  // tickers with on_watchlist=true (drives event filter)
    let logoMap = {};                  // ticker → image URL (from recent_analysis + upcoming earnings)
    let upcomingEvents = [];           // from data.json upcoming_events[]
    let earningsCacheMap = {};         // V1.71 — TICKER → {composite_score, verdict, report_path, ...}
    let generatedAt = '';
    let todayIso = '';                 // 瀏覽器當天，每次 load 都重算（不再吃 indexer 的 j.today）
    let indexedAt = '';                // event_index.json 的 today（僅在 stats 顯示，做 staleness 提示）
    let earningsDensity = 'high';      // 'high' = high impact + watchlist intersect; 'all' = every earnings
    let llmReviewPollTimer = null;     // setInterval handle for status polling while llm_review job is running
    function browserTodayIso() {
        const d = new Date();
        return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
    }
    let currentMonth = (() => {
        const d = new Date();
        return new Date(d.getFullYear(), d.getMonth(), 1);
    })();
    let selectedDate = null;           // ISO date currently shown in inline detail panel

    // ── Filter state (toggle on/off; default = All mode) ──────────────────
    const ALL_SOURCES = [
        'deep-dive', 'sector-scan', 'news-digest', 'theme-detector',
        'momentum-screen', 'thematic-screener', 'earnings-analyzer',
        'short-term-weekly', 'postmortem',
    ];
    const ALL_VERDICTS = ['hit', 'miss', 'neutral', 'pending', 'n/a'];
    const ALL_EVENT_CATS = ['earnings', 'macro', 'econ', 'binary', 'geopolitical', 'watchlist', 'system'];

    const filterState = {
        sources:    new Set(ALL_SOURCES),
        verdicts:   new Set(ALL_VERDICTS),
        eventCats:  new Set(ALL_EVENT_CATS),
    };

    const PRESETS = {
        'all':      { sources: ALL_SOURCES, verdicts: ALL_VERDICTS, eventCats: ALL_EVENT_CATS },
        'analysis': { sources: ALL_SOURCES, verdicts: ALL_VERDICTS, eventCats: [] },
        'up-event': { sources: [],          verdicts: [],           eventCats: ALL_EVENT_CATS },
    };

    function applyPreset(name) {
        const p = PRESETS[name];
        if (!p) return;
        filterState.sources   = new Set(p.sources);
        filterState.verdicts  = new Set(p.verdicts);
        filterState.eventCats = new Set(p.eventCats);
        rebuildFilterBar();
        rerenderAll();
    }

    function activePresetName() {
        const setEq = (a, b) => a.size === b.length && b.every(x => a.has(x));
        for (const name of Object.keys(PRESETS)) {
            const p = PRESETS[name];
            if (setEq(filterState.sources, p.sources) &&
                setEq(filterState.verdicts, p.verdicts) &&
                setEq(filterState.eventCats, p.eventCats)) return name;
        }
        return null;
    }

    function toggleFilter(type, key) {
        const set = type === 'sources' ? filterState.sources
                  : type === 'verdicts' ? filterState.verdicts
                  : type === 'events' ? filterState.eventCats
                  : null;
        if (!set) return;
        if (set.has(key)) set.delete(key); else set.add(key);
        rebuildFilterBar();
        rerenderAll();
    }

    function rerenderAll() {
        renderGrid();
        renderMonthlySummary();
        renderUpcomingStrip();
        renderAggregate();
    }

    // Filter predicates — sources/verdicts intersect (AND), within each: OR
    function decisionPasses(d) {
        if (!filterState.sources.size || !filterState.verdicts.size) return false;
        const v = (d.verdict && d.verdict.label) || 'n/a';
        return filterState.sources.has(d.source) && filterState.verdicts.has(v);
    }
    function eventPasses(e) {
        if (!filterState.eventCats.size) return false;
        return filterState.eventCats.has(e.category || 'system');
    }

    // ── Bootstrap ─────────────────────────────────────────────────────────
    document.addEventListener('DOMContentLoaded', async () => {
        UI.boot('calendar', { translate: applyTranslations, reload: loadAndRender });
        UI.icons();
        wireControls();
        wireFilterBar();
        await loadAndRender();
    });

    function wireControls() {
        document.getElementById('cal-prev').addEventListener('click', () => {
            currentMonth = new Date(currentMonth.getFullYear(), currentMonth.getMonth() - 1, 1);
            closeDetailPanel();
            renderGrid();
        });
        document.getElementById('cal-next').addEventListener('click', () => {
            currentMonth = new Date(currentMonth.getFullYear(), currentMonth.getMonth() + 1, 1);
            closeDetailPanel();
            renderGrid();
        });
        document.getElementById('cal-detail-close').addEventListener('click', closeDetailPanel);
        const backdrop = document.getElementById('cal-detail-backdrop');
        if (backdrop) backdrop.addEventListener('click', closeDetailPanel);
        document.getElementById('cal-llm-review').addEventListener('click', requestLlmReview);
        const reviewRefresh = document.getElementById('cal-llm-review-refresh');
        if (reviewRefresh) reviewRefresh.addEventListener('click', requestLlmReview);
        const densityBtn = document.getElementById('cal-density-toggle');
        if (densityBtn) {
            densityBtn.addEventListener('click', () => {
                earningsDensity = earningsDensity === 'high' ? 'all' : 'high';
                try { localStorage.setItem('cal_earnings_density', earningsDensity); } catch {}
                updateDensityToggleLabel();
                renderGrid();
                renderUpcomingStrip();
            });
        }
        try {
            const saved = localStorage.getItem('cal_earnings_density');
            if (saved === 'all' || saved === 'high') earningsDensity = saved;
        } catch {}
        updateDensityToggleLabel();
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') closeDetailPanel();
        });
    }

    function updateDensityToggleLabel() {
        const lbl = document.getElementById('cal-density-toggle-label');
        const btn = document.getElementById('cal-density-toggle');
        if (!lbl || !btn) return;
        const isZh = UI.currentLang === 'zh';
        if (earningsDensity === 'high') {
            lbl.textContent = isZh ? 'High + 觀察清單' : 'High + Watchlist';
            btn.classList.add('is-on');
        } else {
            lbl.textContent = isZh ? '所有 earnings' : 'All earnings';
            btn.classList.remove('is-on');
        }
    }

    // ── i18n ──────────────────────────────────────────────────────────────
    function applyTranslations() {
        const t = (window.i18n?.[UI.currentLang]?.calendar) || {};
        const isZh = UI.currentLang === 'zh';
        document.title = isZh ? 'AI 投資委員會 | 決策日曆' : 'AI Investment Committee | Decision Calendar';
        const set = (id, val) => { const el = document.getElementById(id); if (el && val != null) el.textContent = val; };

        set('cal-title',                  t.title           || (isZh ? '決策日曆' : 'Decision Calendar'));
        set('cal-subtitle',               t.subtitle        || 'Decision Review Hub');
        set('cal-llm-btn-text',           t.llm_review      || (isZh ? '請 LLM 檢討' : 'Ask LLM Review'));
        set('cal-upcoming-title',         t.upcoming        || (isZh ? '即將發生' : 'Coming Up'));
        set('cal-upcoming-subtitle',      t.upcoming_sub    || (isZh ? '未來 7 天' : 'Next 7 days'));
        set('cal-upcoming-empty-title',   isZh ? '未來 7 天無事件' : 'No upcoming events');
        set('cal-upcoming-empty-text',    isZh
            ? '尚未接入 earnings-calendar / FOMC 事件源。當前僅顯示 event_index 內的未來日期決策。'
            : 'earnings-calendar / FOMC event sources not yet wired in. Currently only showing future-dated decisions inside event_index.');
        set('cal-no-data-text',           t.no_data         || (isZh ? '尚無決策資料。請先跑 indexer：' : 'No decision data yet. Run the indexer first:'));
        set('cal-filter-mode-label',      isZh ? '模式' : 'Mode');
        set('cal-filter-sources-label',   t.legend_sources  || (isZh ? '來源' : 'Sources'));
        set('cal-filter-verdicts-label',  t.legend_verdicts || (isZh ? '判讀' : 'Verdicts'));
        set('cal-filter-events-label',    isZh ? '事件' : 'Events');
        set('cal-aggregate-title',        t.verdict_review_title || (isZh ? '命中率回顧（依來源）' : 'Verdict Review by Source'));
        set('cal-aggregate-hint',         t.verdict_review_hint  || (isZh ? '點開展開詳細命中率' : 'click to expand hit rate'));
        set('cal-monthly-summary-title',  isZh ? '近 30 天分析' : 'Past 30 Days');
        set('cal-monthly-summary-hint',   isZh ? '分析過的公司' : 'companies analyzed');
        set('cal-upcoming-strip-title',   isZh ? '未來 7 天事件' : 'Coming Up Next 7 Days');
        set('cal-upcoming-strip-hint',    isZh ? 'earnings + 經濟事件' : 'earnings + macro events');

        rebuildFilterBar();
        updateDensityToggleLabel();

        // Re-render data-driven sections so translated strings apply
        if (allDecisions.length || recentAnalysis.length) {
            renderGrid();
            renderMonthlySummary();
            renderUpcomingStrip();
            renderAggregate();
        }
    }

    // ── Data load ─────────────────────────────────────────────────────────
    async function loadAndRender() {
        try {
            // Parallel: event_index for past decisions verdicts + data.json for live decisions + upcoming events
            const [evRes, dashRes] = await Promise.all([
                fetch(EVENT_INDEX_URL, { cache: 'no-store' }).catch(() => null),
                fetch(DASHBOARD_DATA_URL, { cache: 'no-store' }),
            ]);

            let indexDecisions = [];
            if (evRes && evRes.ok) {
                const j = await evRes.json();
                indexDecisions = j.decisions || [];
                generatedAt = j.generated_at || '';
                indexedAt = j.today || '';
            }
            todayIso = browserTodayIso();

            if (!dashRes.ok) throw new Error('data.json not found');
            const dash = await dashRes.json();
            recentAnalysis = Array.isArray(dash.recent_analysis) ? dash.recent_analysis : [];
            upcomingEvents = Array.isArray(dash.upcoming_events) ? dash.upcoming_events : [];

            // V1.71 — earnings-analyst cache index for inline cached-state chips
            earningsCacheMap = {};
            for (const ea of (dash.earnings_analyses || [])) {
                if (ea && ea.ticker) earningsCacheMap[ea.ticker.toUpperCase()] = ea;
            }

            // Build watchlist + logo map from recent_analysis (primary) and upcoming earnings (secondary)
            watchlistTickers = new Set();
            logoMap = {};
            for (const a of recentAnalysis) {
                if (!a.ticker) continue;
                const tk = a.ticker.toUpperCase();
                if (a.on_watchlist) watchlistTickers.add(tk);
                if (a.profile_image && !logoMap[tk]) logoMap[tk] = a.profile_image;
            }
            for (const e of upcomingEvents) {
                if (e.profile_image && Array.isArray(e.tickers) && e.tickers.length) {
                    const tk = e.tickers[0].toUpperCase();
                    if (!logoMap[tk]) logoMap[tk] = e.profile_image;
                }
            }

            // Merge: recent_analysis[] -> unified decision shape, then layer event_index verdicts
            const indexByKey = {};
            for (const d of indexDecisions) {
                if (!d.decision_date) continue;
                const tk = (d.tickers && d.tickers[0]) ? d.tickers[0].toUpperCase() : null;
                indexByKey[`${d.decision_date}|${tk || d.source}`] = d;
            }

            const mergedFromRecent = recentAnalysis
                .filter(a => a.ticker && a.time)
                .map(a => {
                    const tk = a.ticker.toUpperCase();
                    const dateIso = (a.time || '').slice(0, 10);
                    const key = `${dateIso}|${tk}`;
                    const indexed = indexByKey[key];
                    // verdict comes from event_index when available; otherwise unknown→pending/n/a
                    const verdict = indexed && indexed.verdict
                        ? indexed.verdict
                        : { label: 'pending', rationale: '' };
                    return {
                        source: 'deep-dive',
                        decision_date: dateIso,
                        tickers: [tk],
                        verdict,
                        // primary fields preserved for detail panel
                        decision_content: indexed?.decision_content || {
                            final_action: a.decision,
                            final_score: a.score,
                            final_decision: a.final_decision,
                            macro_regime: null,
                            trader_proposal: a.targets || {},
                        },
                        agent_breakdown: indexed?.agent_breakdown || [],
                        reality_at_eval: indexed?.reality_at_eval || {},
                        tuning_hooks: indexed?.tuning_hooks || {},
                        raw_path: a.report_url ? '/' + a.report_url : (indexed?.raw_path || null),
                        summary: a.decision || '',
                        // calendar render hints (not in event_index schema)
                        _logo: a.profile_image || logoMap[tk] || null,
                        _live_decision: a.decision,
                        _on_watchlist: !!a.on_watchlist,
                        _from_recent: true,
                    };
                });

            // Build allDecisions = merged recent_analysis ∪ index decisions that aren't already covered
            const seenKeys = new Set(mergedFromRecent.map(d => `${d.decision_date}|${d.tickers[0]}`));
            const indexExtras = indexDecisions.filter(d => {
                if (!d.decision_date) return false;
                const tk = (d.tickers && d.tickers[0]) ? d.tickers[0].toUpperCase() : null;
                return !tk || !seenKeys.has(`${d.decision_date}|${tk}`);
            }).map(d => {
                const tk = (d.tickers && d.tickers[0]) ? d.tickers[0].toUpperCase() : null;
                return Object.assign({}, d, {
                    _logo: tk ? (logoMap[tk] || null) : null,
                });
            });
            allDecisions = mergedFromRecent.concat(indexExtras);

            // Auto-jump to current month
            const [y, m] = todayIso.split('-').map(Number);
            currentMonth = new Date(y, m - 1, 1);

            document.getElementById('cal-no-data').classList.add('hidden');
            document.getElementById('cal-main').classList.remove('hidden');
            const aggEl = document.getElementById('cal-aggregate');
            if (aggEl) aggEl.classList.remove('hidden');

            let stats = `${allDecisions.length} decisions · ${upcomingEvents.length} upcoming · today=${todayIso}`;
            if (indexedAt && indexedAt !== todayIso) {
                stats += ` · indexed=${indexedAt}`;
            }
            document.getElementById('cal-stats').textContent = stats;

            renderGrid();
            renderMonthlySummary();
            renderUpcomingStrip();
            renderAggregate();
            // Show last LLM Review (if any) on page load + resume poll if a job is running
            loadLatestReview();
            checkLlmReviewRunning();
        } catch (e) {
            console.error('[calendar] load failed', e);
            document.getElementById('cal-no-data').classList.remove('hidden');
            document.getElementById('cal-main').classList.add('hidden');
            const aggEl = document.getElementById('cal-aggregate');
            if (aggEl) aggEl.classList.add('hidden');
        }
    }

    // ── Logo helpers ──────────────────────────────────────────────────────
    function monogramColorFromTicker(t) {
        // Stable hash → HSL hue. Same ticker always gets same color.
        let h = 0;
        for (let i = 0; i < t.length; i++) h = (h * 31 + t.charCodeAt(i)) >>> 0;
        const hue = h % 360;
        return `hsl(${hue}, 55%, 35%)`;
    }
    function renderTickerLogo(ticker, opts = {}) {
        const size = opts.size || 18;
        const ringColor = opts.ringColor || 'transparent';
        const ringWidth = opts.ringWidth || 0;
        const tk = (ticker || '').toUpperCase();
        const url = logoMap[tk];
        const mono = (tk.slice(0, 2) || '?').toUpperCase();
        const bg = monogramColorFromTicker(tk || '?');
        const ringStyle = ringWidth ? `box-shadow: 0 0 0 ${ringWidth}px ${ringColor};` : '';
        // <img> with onerror → swap to monogram span sibling shown via display swap
        const id = `logo-${tk}-${Math.random().toString(36).slice(2, 8)}`;
        if (url) {
            return `<span class="cal-ticker-logo" style="width:${size}px;height:${size}px;${ringStyle}">
                <img src="${url}" alt="${tk}" loading="lazy"
                     onerror="this.style.display='none';this.nextElementSibling.style.display='flex';"/>
                <span class="cal-monogram-fallback" style="background:${bg};display:none">${mono}</span>
            </span>`;
        }
        return `<span class="cal-ticker-logo" style="width:${size}px;height:${size}px;${ringStyle}">
            <span class="cal-monogram-fallback" style="background:${bg}">${mono}</span>
        </span>`;
    }
    function ringColorForDecision(dec, verdictLabel) {
        // verdict overrides decision tint (event_index post-eval)
        if (verdictLabel === 'hit') return 'rgba(34, 197, 94, 0.85)';
        if (verdictLabel === 'miss') return 'rgba(239, 68, 68, 0.85)';
        if (verdictLabel === 'neutral') return 'rgba(234, 179, 8, 0.85)';
        // live decision tint
        if (dec === 'EXECUTE') return 'rgba(34, 197, 94, 0.7)';
        if (dec === 'STAGED') return 'rgba(245, 158, 11, 0.7)';
        if (dec === 'CANCEL') return 'rgba(239, 68, 68, 0.7)';
        return 'rgba(113, 113, 122, 0.55)';
    }
    function renderLogoStack(items, opts = {}) {
        // items: [{ticker, ringColor}]; cell size + overlap configurable
        const size = opts.size || 18;
        const overlap = opts.overlap != null ? opts.overlap : 6;
        const max = opts.max || 3;
        const visible = items.slice(0, max);
        const extra = items.length - visible.length;
        const html = visible.map((it, i) => `<span class="cal-logo-stack-slot" style="margin-left:${i === 0 ? 0 : -overlap}px;z-index:${visible.length - i}">${renderTickerLogo(it.ticker, { size, ringColor: it.ringColor || 'transparent', ringWidth: it.ringColor ? 2 : 0 })}</span>`).join('');
        const more = extra > 0
            ? `<span class="cal-logo-stack-more" style="margin-left:${-overlap}px;width:${size}px;height:${size}px;line-height:${size}px">+${extra}</span>`
            : '';
        return `<span class="cal-logo-stack">${html}${more}</span>`;
    }

    // ── Helpers ───────────────────────────────────────────────────────────
    // ── Filter-bar UI ─────────────────────────────────────────────────────
    function rebuildFilterBar() {
        const t = (window.i18n?.[UI.currentLang]?.calendar) || {};
        const isZh = UI.currentLang === 'zh';
        const srcLabels = t.sources || {};
        const vLabels = t.verdicts || {};
        const eventLabels = isZh
            ? { earnings: '財報', macro: '聯準會', econ: '經濟', binary: '二元', geopolitical: '地緣', watchlist: '觀察', system: '系統' }
            : { earnings: 'Earnings', macro: 'Fed/Macro', econ: 'Econ', binary: 'Binary', geopolitical: 'Geo', watchlist: 'Watchlist', system: 'System' };

        // Preset row
        const presetMeta = [
            { key: 'all',      labelZh: '全部',     labelEn: 'All'      },
            { key: 'analysis', labelZh: '分析',     labelEn: 'Analysis' },
            { key: 'up-event', labelZh: '事件',     labelEn: 'Up-Event' },
        ];
        const activePreset = activePresetName();
        const presetsEl = document.getElementById('cal-filter-presets');
        if (presetsEl) {
            presetsEl.innerHTML = presetMeta.map(p => {
                const active = p.key === activePreset;
                return `<button type="button" class="cal-filter-preset${active ? ' is-active' : ''}" data-preset="${p.key}">${isZh ? p.labelZh : p.labelEn}</button>`;
            }).join('');
        }

        // Sources row
        const srcMeta = ALL_SOURCES.map(k => ({ key: k, icon: (SOURCE_META[k] || {}).icon || '?' }));
        const srcEl = document.getElementById('cal-filter-sources');
        if (srcEl) {
            srcEl.innerHTML = srcMeta.map(s => {
                const on = filterState.sources.has(s.key);
                return `<button type="button" class="cal-filter-pill${on ? ' is-on' : ''}" data-filter="sources" data-key="${s.key}" title="${s.key}">${s.icon} <span class="cal-filter-pill-label">${srcLabels[s.key] || s.key}</span></button>`;
            }).join('');
        }

        // Verdicts row
        const verdictMeta = [
            { key: 'hit',     emoji: '✅' },
            { key: 'miss',    emoji: '❌' },
            { key: 'neutral', emoji: '⚪' },
            { key: 'pending', emoji: '⏳' },
            { key: 'n/a',     emoji: '—'  },
        ];
        const vEl = document.getElementById('cal-filter-verdicts');
        if (vEl) {
            vEl.innerHTML = verdictMeta.map(v => {
                const on = filterState.verdicts.has(v.key);
                return `<button type="button" class="cal-filter-pill${on ? ' is-on' : ''}" data-filter="verdicts" data-key="${v.key}">${v.emoji} <span class="cal-filter-pill-label">${vLabels[v.key] || v.key}</span></button>`;
            }).join('');
        }

        // Events row
        const eventMeta = ALL_EVENT_CATS.map(k => ({ key: k, icon: (CATEGORY_META[k] || {}).icon || '📅' }));
        const evEl = document.getElementById('cal-filter-events');
        if (evEl) {
            evEl.innerHTML = eventMeta.map(e => {
                const on = filterState.eventCats.has(e.key);
                return `<button type="button" class="cal-filter-pill${on ? ' is-on' : ''}" data-filter="events" data-key="${e.key}">${e.icon} <span class="cal-filter-pill-label">${eventLabels[e.key] || e.key}</span></button>`;
            }).join('');
        }
    }

    function wireFilterBar() {
        const bar = document.getElementById('cal-filterbar');
        if (!bar) return;
        bar.addEventListener('click', (ev) => {
            const presetBtn = ev.target.closest('[data-preset]');
            if (presetBtn) { applyPreset(presetBtn.dataset.preset); return; }
            const pillBtn = ev.target.closest('[data-filter][data-key]');
            if (pillBtn) toggleFilter(pillBtn.dataset.filter, pillBtn.dataset.key);
        });
    }

    function decisionsByDate() {
        const m = {};
        for (const d of allDecisions) {
            if (!decisionPasses(d)) continue;
            const dt = d.decision_date;
            if (!dt) continue;
            (m[dt] = m[dt] || []).push(d);
        }
        return m;
    }

    function dateToIso(year, month, day) {
        return `${year}-${String(month + 1).padStart(2, '0')}-${String(day).padStart(2, '0')}`;
    }

    function aggregateVerdictColor(decisions) {
        // priority: miss > hit > neutral > pending > n/a
        if (decisions.some(d => d.verdict?.label === 'miss')) return 'miss';
        if (decisions.some(d => d.verdict?.label === 'hit')) return 'hit';
        if (decisions.some(d => d.verdict?.label === 'neutral')) return 'neutral';
        if (decisions.some(d => d.verdict?.label === 'pending')) return 'pending';
        return 'n/a';
    }

    function groupBySource(arr) {
        const m = {};
        for (const d of arr) (m[d.source] = m[d.source] || []).push(d);
        return m;
    }

    // ── Upcoming events ↔ date map (for in-cell rendering) ────────────────
    function eventPassesDensity(e) {
        // Earnings density filter: 'high' = high-impact OR ticker in watchlist; 'all' = any
        if (e.category !== 'earnings') return true;
        if (earningsDensity === 'all') return true;
        if (e.impact === 'high') return true;
        const tks = (e.tickers || []).map(t => t.toUpperCase());
        return tks.some(t => watchlistTickers.has(t));
    }
    function upcomingEventsByDate() {
        const m = {};
        for (const e of upcomingEvents) {
            if (!e.date) continue;
            if (!eventPasses(e)) continue;
            if (!eventPassesDensity(e)) continue;
            (m[e.date] = m[e.date] || []).push(e);
        }
        return m;
    }

    // ── Calendar Grid ─────────────────────────────────────────────────────
    function renderGrid() {
        const byDate = decisionsByDate();
        const eventsByDate = upcomingEventsByDate();
        const year = currentMonth.getFullYear();
        const month = currentMonth.getMonth();

        document.getElementById('cal-month-label').textContent =
            currentMonth.toLocaleDateString(UI.currentLang === 'zh' ? 'zh-TW' : 'en-US',
                { year: 'numeric', month: 'long' });

        const first = new Date(year, month, 1);
        const startDay = first.getDay(); // 0 = Sun
        const daysInMonth = new Date(year, month + 1, 0).getDate();

        const grid = document.getElementById('cal-grid');
        grid.innerHTML = '';

        const dayHeaders = UI.currentLang === 'zh'
            ? ['日', '一', '二', '三', '四', '五', '六']
            : ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
        for (const h of dayHeaders) {
            grid.insertAdjacentHTML('beforeend', `<div class="cal-dayhead">${h}</div>`);
        }

        for (let i = 0; i < startDay; i++) {
            grid.insertAdjacentHTML('beforeend', '<div class="cal-cell-empty"></div>');
        }

        const todayDate = todayIso ? new Date(todayIso) : null;

        for (let day = 1; day <= daysInMonth; day++) {
            const dateStr = dateToIso(year, month, day);
            const decisions = byDate[dateStr] || [];
            const events = eventsByDate[dateStr] || [];
            const isToday = dateStr === todayIso;
            const cellDate = new Date(dateStr);
            const isPast = todayDate && cellDate < todayDate && !isToday;

            const cell = document.createElement('div');
            cell.className = 'cal-cell';
            if (isToday) cell.classList.add('cal-cell-today');
            else if (isPast) cell.classList.add('cal-cell-past');
            if (decisions.length === 0 && events.length === 0) cell.classList.add('cal-cell-no-events');
            if (dateStr === selectedDate) cell.classList.add('cal-cell-selected');
            cell.dataset.date = dateStr;

            const dayNum = `<div class="cal-cell-day">
                <span class="cal-cell-num">${day}</span>
                ${isToday ? `<span class="cal-cell-today-tag">${(window.i18n?.[UI.currentLang]?.calendar?.today_tag) || 'today'}</span>` : ''}
            </div>`;

            cell.innerHTML = dayNum + renderDecisionLogoGroup(decisions) + renderEventLogoGroup(events);

            if (decisions.length > 0 || events.length > 0) {
                cell.addEventListener('click', () => {
                    if (selectedDate === dateStr) closeDetailPanel();
                    else openDetailPanel(dateStr, decisions, events);
                });
            }
            grid.appendChild(cell);
        }

        UI.icons();
    }

    // ── In-cell event row: category-grouped logo stack + ticker text ───────
    // Pattern per row: [category icon] [logo stack OR text]. Same icon never
    // repeats within a cell. Single line per category; max 2 categories shown.
    function renderEventLogoGroup(events) {
        // Always render slot (empty case) so dashed-line baseline stays aligned across all cells
        if (!events.length) return '<div class="cal-cell-event-rows is-empty"></div>';
        const byCat = {};
        for (const e of events) {
            const cat = e.category || 'system';
            (byCat[cat] = byCat[cat] || []).push(e);
        }
        const order = ['earnings', 'macro', 'binary', 'econ', 'geopolitical', 'watchlist', 'system'];
        const sorted = order.filter(c => byCat[c]).map(c => [c, byCat[c]]);
        const VISIBLE = 2;
        let html = '<div class="cal-cell-event-rows">';
        for (const [cat, arr] of sorted.slice(0, VISIBLE)) {
            const meta = CATEGORY_META[cat] || { icon: '📅' };
            const hasBin = arr.some(e => e.is_binary);
            const hasHigh = arr.some(e => e.impact === 'high');
            const rowCls = hasBin ? 'cal-cell-event-row-binary'
                         : hasHigh ? 'cal-cell-event-row-high' : '';
            // Tickered events → logo stack; non-ticker → first title text
            const tickered = arr.filter(e => Array.isArray(e.tickers) && e.tickers.length);
            const non = arr.filter(e => !(Array.isArray(e.tickers) && e.tickers.length));
            let body;
            if (tickered.length) {
                const stackItems = tickered.map(e => ({
                    ticker: e.tickers[0].toUpperCase(),
                    ringColor: e.is_binary ? 'rgba(239, 68, 68, 0.85)' : (e.impact === 'high' ? 'rgba(245, 158, 11, 0.7)' : 'transparent'),
                }));
                const tickers = tickered.slice(0, 3).map(e => e.tickers[0].toUpperCase()).join('·');
                const more = tickered.length > 3 ? ` +${tickered.length - 3}` : '';
                body = `${renderLogoStack(stackItems, { size: 16, max: 3 })}<span class="cal-cell-event-tickers">${tickers}${more}</span>`;
            } else {
                const first = (non[0] && non[0].title) ? non[0].title : '';
                const short = first.length > 22 ? first.slice(0, 21) + '…' : first;
                const cnt = non.length > 1 ? ` (${non.length})` : '';
                body = `<span class="cal-cell-event-text">${short}${cnt}</span>`;
            }
            html += `<div class="cal-cell-event-row ${rowCls}">
                <span class="cal-cell-event-cat-icon">${meta.icon}</span>
                ${body}
            </div>`;
        }
        if (sorted.length > VISIBLE) {
            const extraCats = sorted.slice(VISIBLE);
            const extra = extraCats.reduce((s, [, a]) => s + a.length, 0);
            html += `<div class="cal-cell-event-row-more">+${extra} more</div>`;
        }
        html += '</div>';
        return html;
    }

    // ── In-cell decision row: logo stack + ticker text ─────────────────────
    function renderDecisionLogoGroup(decisions) {
        // Always render slot so events row stays anchored at bottom (consistent cell layout)
        if (!decisions.length) return '<div class="cal-cell-decision-row is-empty"></div>';
        // Sort: live deep-dive (from recent_analysis) first, then by source priority
        const sorted = [...decisions].sort((a, b) => {
            if (!!b._from_recent !== !!a._from_recent) return (b._from_recent ? 1 : 0) - (a._from_recent ? 1 : 0);
            return 0;
        });
        const stackItems = sorted.map(d => {
            const tk = (d.tickers && d.tickers[0]) ? d.tickers[0].toUpperCase() : '';
            return {
                ticker: tk,
                ringColor: ringColorForDecision(d._live_decision || (d.decision_content || {}).final_action, d.verdict?.label),
            };
        }).filter(it => it.ticker);
        if (!stackItems.length) {
            // Fallback for source-only decisions (no ticker) — keep old badge style
            const bySrc = groupBySource(decisions);
            let h = '<div class="cal-badge-row">';
            for (const [src, arr] of Object.entries(bySrc)) {
                const meta = SOURCE_META[src] || { icon: '?' };
                const v = aggregateVerdictColor(arr);
                const vMeta = VERDICT_META[v];
                const count = arr.length > 1 ? `<span class="cal-badge-count">${arr.length}</span>` : '';
                h += `<span class="cal-badge ${vMeta.badgeClass}" title="${src} (${arr.length}) — ${v}">${meta.icon}${count}</span>`;
            }
            h += '</div>';
            return h;
        }
        const tickers = stackItems.slice(0, 3).map(it => it.ticker).join('·');
        const extra = stackItems.length - 3;
        const more = extra > 0 ? ` +${extra}` : '';
        return `<div class="cal-cell-decision-row">
            ${renderLogoStack(stackItems, { size: 18, max: 3 })}
            <span class="cal-cell-decision-tickers">${tickers}${more}</span>
        </div>`;
    }

    // ── Inline Detail Panel (replaces drawer) ─────────────────────────────
    function openDetailPanel(dateStr, decisions, events = []) {
        const isZh = UI.currentLang === 'zh';
        const prevSelected = selectedDate;
        selectedDate = dateStr;

        // Update cell ring: clear previous, mark current
        if (prevSelected) {
            const prevCell = document.querySelector(`.cal-cell[data-date="${prevSelected}"]`);
            if (prevCell) prevCell.classList.remove('cal-cell-selected');
        }
        const curCell = document.querySelector(`.cal-cell[data-date="${dateStr}"]`);
        if (curCell) curCell.classList.add('cal-cell-selected');

        document.getElementById('cal-detail-date').textContent = dateStr;
        const decLabel = isZh ? ' 筆 decisions' : ' decisions';
        const evLabel  = isZh ? ' 件 events'    : ' events';
        const parts = [];
        if (decisions.length) parts.push(decisions.length + decLabel);
        if (events.length)    parts.push(events.length + evLabel);
        document.getElementById('cal-detail-count').textContent =
            parts.length ? (isZh ? '共 ' : 'Total ') + parts.join(' · ') : '—';

        const content = document.getElementById('cal-detail-content');
        let html = '';

        // Upcoming events section (rendered first — what to watch for the day)
        if (events.length) {
            html += renderEventsDetailSection(events, isZh);
        }

        // Past decisions, grouped by source
        const bySrc = groupBySource(decisions);
        for (const [src, arr] of Object.entries(bySrc)) {
            const meta = SOURCE_META[src] || {};
            html += `<section class="cal-drawer-section">
                <div class="cal-drawer-section-head">
                    <span class="cal-drawer-section-icon">${meta.icon}</span>
                    <span>${meta.label}</span>
                    <span class="cal-drawer-section-count">${arr.length}</span>
                </div>
                <div class="space-y-2">`;
            for (const d of arr) html += renderDecisionCard(d);
            html += '</div></section>';
        }
        content.innerHTML = html;

        const panel = document.getElementById('cal-detail');
        const backdrop = document.getElementById('cal-detail-backdrop');
        panel.classList.remove('hidden');
        panel.setAttribute('aria-hidden', 'false');
        if (backdrop) {
            backdrop.classList.remove('hidden');
            requestAnimationFrame(() => backdrop.classList.add('cal-detail-backdrop-open'));
        }
        // Lock body scroll while modal open
        document.body.classList.add('cal-detail-locked');
        // Force reflow then trigger scale-in transition
        requestAnimationFrame(() => panel.classList.add('cal-detail-open'));
        UI.icons();
    }

    function closeDetailPanel() {
        const panel = document.getElementById('cal-detail');
        const backdrop = document.getElementById('cal-detail-backdrop');
        if (!panel) return;
        panel.classList.remove('cal-detail-open');
        panel.setAttribute('aria-hidden', 'true');
        if (backdrop) {
            backdrop.classList.remove('cal-detail-backdrop-open');
            backdrop.setAttribute('aria-hidden', 'true');
            setTimeout(() => backdrop.classList.add('hidden'), 240);
        }
        document.body.classList.remove('cal-detail-locked');
        setTimeout(() => panel.classList.add('hidden'), 240);

        if (selectedDate) {
            const prevCell = document.querySelector(`.cal-cell[data-date="${selectedDate}"]`);
            if (prevCell) prevCell.classList.remove('cal-cell-selected');
        }
        selectedDate = null;
    }

    function renderEventsDetailSection(events, isZh) {
        const impactOrder = { high: 0, med: 1, low: 2 };
        const sorted = [...events].sort((a, b) => {
            const ab = (b.is_binary ? 1 : 0) - (a.is_binary ? 1 : 0);
            if (ab !== 0) return ab;
            return (impactOrder[a.impact] ?? 3) - (impactOrder[b.impact] ?? 3);
        });
        const headLabel = isZh ? '當日事件' : 'Events';
        let html = `<section class="cal-drawer-section">
            <div class="cal-drawer-section-head">
                <span class="cal-drawer-section-icon">📌</span>
                <span>${headLabel}</span>
                <span class="cal-drawer-section-count">${events.length}</span>
            </div>
            <div class="space-y-2">`;
        for (const e of sorted) html += renderUpcomingCard(e);
        html += '</div></section>';
        return html;
    }

    function renderDecisionCard(d) {
        const v = d.verdict || {};
        const vMeta = VERDICT_META[v.label] || VERDICT_META['n/a'];
        const re = d.reality_at_eval || {};

        // source-specific render
        let body = '';
        switch (d.source) {
            case 'deep-dive':         body = renderDeepDiveBody(d, re); break;
            case 'sector-scan':       body = renderSectorScanBody(d, re); break;
            case 'news-digest':       body = renderNewsBody(d, re); break;
            case 'theme-detector':    body = renderThemeBody(d, re); break;
            case 'momentum-screen':   body = renderMomentumBody(d, re); break;
            case 'thematic-screener': body = renderRadarBody(d, re); break;
            case 'earnings-analyzer': body = renderEarningsBody(d, re); break;
            case 'short-term-weekly': body = renderWeeklyBody(d, re); break;
            case 'postmortem':        body = renderPostmortemBody(d, re); break;
            default:                  body = `<div class="text-zinc-500">${d.summary || ''}</div>`;
        }

        const ticker = (d.tickers || [])[0] || '';
        const headerLeft = ticker
            ? `<span class="cal-card-header-logo">${renderTickerLogo(ticker, { size: 22 })}</span><span class="font-mono font-bold text-sm">${ticker}</span>`
            : `<span class="text-xs text-zinc-400 truncate" style="max-width:280px">${d.summary || ''}</span>`;

        return `<div class="cal-card pl-4">
            <div class="cal-card-verdict-stripe ${vMeta.stripeClass}"></div>
            <div class="flex items-center justify-between mb-1.5">
                <div class="flex items-center gap-2">
                    <span class="text-base">${vMeta.emoji}</span>
                    ${headerLeft}
                    <span class="text-[10px] uppercase font-bold tracking-widest ${vMeta.textClass}">${v.label || 'n/a'}</span>
                </div>
                ${d.raw_path ? `<button class="text-[10px] text-zinc-500 hover:text-emerald-400 flex items-center gap-1"
                        onclick="window.open('${d.raw_path}','_blank')">
                    <i data-lucide="external-link" class="w-3 h-3"></i>
                    raw
                </button>` : ''}
            </div>
            <div class="text-[11px] text-zinc-400 mb-2 italic">${v.rationale || ''}</div>
            ${body}
        </div>`;
    }

    // ── Per-source body renderers ────────────────────────────────────────
    function pctStr(v) { return (v == null) ? '—' : (v >= 0 ? '+' : '') + v.toFixed(2) + '%'; }

    function renderDeepDiveBody(d, re) {
        const dc = d.decision_content || {};
        const r = re.ticker_reality;
        const tp = dc.trader_proposal || {};
        const isZh = UI.currentLang === 'zh';
        const dt = (window.i18n?.[UI.currentLang]?.calendar?.drawer) || {};
        const ag = (d.agent_breakdown || []).map(a =>
            `<span class="text-[10px] mr-2"><span class="text-zinc-500">${a.agent}</span> ${a.signal} ${a.score >= 0 ? '+' : ''}${a.score}</span>`).join('');
        return `
            <div class="text-[11px] text-zinc-400">
                <div>${dt.at_decision || 'At decision'}：<span class="font-mono">${dc.final_action || '?'}</span> · score ${dc.final_score} · regime ${dc.macro_regime || '—'}</div>
                ${tp.entry || tp.tp || tp.sl ? `<div>Trader: entry=${tp.entry || '—'} TP=${tp.tp || '—'} SL=${tp.sl || '—'}</div>` : ''}
                ${ag ? `<div class="mt-1">${ag}</div>` : ''}
            </div>
            ${r ? `<div class="text-[11px] mt-1 font-mono"><span class="text-zinc-500">${dt.reality || 'Reality'}:</span> ${r.price_at_decision} → ${r.price_at_eval} <span class="font-bold ${r.return_pct >= 0 ? 'text-green-400' : 'text-red-400'}">${pctStr(r.return_pct)}</span> · max ${r.max_runup_since} / min ${r.max_drawdown_since}</div>` : ''}
            <div class="text-[10px] text-zinc-600 mt-1">window ${re.window_complete_pct}% (${re.days_elapsed}/${re.window_days}d) · decisive=${(d.tuning_hooks || {}).decisive_agent || '—'}</div>
        `;
    }

    function renderSectorScanBody(d, re) {
        const dc = d.decision_content || {};
        const etfs = re.etf_returns || {};
        const spy = etfs.SPY ?? 0;
        const ratings = (dc.sector_ratings || []).slice(0, 6);
        const dt = (window.i18n?.[UI.currentLang]?.calendar?.drawer) || {};
        const rows = ratings.map(r => {
            const ret = etfs[r.etf];
            const rel = (ret != null && spy != null) ? ret - spy : null;
            return `<tr><td class="pr-2">${r.sector}</td><td class="pr-2 text-zinc-500">${r.rating}</td><td class="pr-2 font-mono">${r.etf || '—'}</td><td class="pr-2 font-mono">${pctStr(ret)}</td><td class="font-mono ${rel != null && rel > 0 ? 'text-green-400' : (rel != null && rel < 0 ? 'text-red-400' : 'text-zinc-500')}">${pctStr(rel)}</td></tr>`;
        }).join('');
        return `<div class="text-[10px] text-zinc-500 mb-1">regime=${dc.market_regime} · breadth=${dc.breadth_score} · SPY ${pctStr(spy)}</div>
            <table class="text-[11px]"><thead><tr class="text-zinc-600"><th class="pr-2 text-left">${dt.tbl_sector||'Sector'}</th><th class="pr-2">${dt.tbl_rating||'Rating'}</th><th class="pr-2">${dt.tbl_etf||'ETF'}</th><th class="pr-2">${dt.tbl_return||'Return'}</th><th class="pr-2">${dt.tbl_vs_spy||'vs SPY'}</th></tr></thead><tbody>${rows}</tbody></table>`;
    }

    function renderNewsBody(d, re) {
        const dc = d.decision_content || {};
        return `<div class="text-[11px] text-zinc-400">
            macro_delta=<span class="font-mono">${dc.macro_delta ?? '—'}</span> · cards=${(dc.impact_cards || []).length}
        </div>
        <div class="text-[11px] mt-1 font-mono"><span class="text-zinc-500">SPY ${re.window_days}d:</span> <span class="${re.spy_return_pct >= 0 ? 'text-green-400' : 'text-red-400'}">${pctStr(re.spy_return_pct)}</span></div>`;
    }

    function renderThemeBody(d, re) {
        const dc = d.decision_content || {};
        const etfs = re.etf_returns || {};
        const spy = etfs.SPY ?? 0;
        const lead = (dc.themes || []).filter(t => t.direction === 'LEAD').slice(0, 5);
        const rows = lead.map(t => {
            const etf = (t.proxy_etfs || [])[0];
            const ret = etfs[etf];
            const rel = (ret != null && spy != null) ? ret - spy : null;
            return `<div class="flex justify-between text-[11px]"><span>${t.name?.slice(0, 22) || '—'} <span class="text-zinc-600">(${t.stage}, ${t.confidence})</span></span><span class="font-mono">${etf || '—'} ${pctStr(rel)}</span></div>`;
        }).join('');
        return `<div class="text-[10px] text-zinc-500 mb-1">SPY ${pctStr(spy)}</div>${rows}`;
    }

    function renderMomentumBody(d, re) {
        const dc = d.decision_content || {};
        const pt = (re.per_ticker || []).slice(0, 6);
        const rows = pt.map(t => {
            const vMeta = VERDICT_META[t.verdict] || VERDICT_META['n/a'];
            const warns = (t.warnings || []).join(',') || '—';
            return `<tr>
                <td class="pr-2 font-mono font-bold">${t.ticker}</td>
                <td class="pr-2">${t.score}</td>
                <td class="pr-2 text-[10px] text-zinc-500">${warns}</td>
                <td class="pr-2 font-mono ${t.return_pct >= 0 ? 'text-green-400' : 'text-red-400'}">${pctStr(t.return_pct)}</td>
                <td>${vMeta.emoji}</td>
            </tr>`;
        }).join('');
        const dt = (window.i18n?.[UI.currentLang]?.calendar?.drawer) || {};
        const more = (re.per_ticker || []).length > 6
            ? `<div class="text-[10px] text-zinc-600 mt-1">${typeof dt.rest_omitted === 'function' ? dt.rest_omitted((re.per_ticker||[]).length - 6) : `+${(re.per_ticker||[]).length - 6}`}</div>`
            : '';
        const screenedLabel = typeof dt.screened === 'function' ? dt.screened(dc.n_total_screened, dc.n_evaluated) : `${dc.n_total_screened} → top ${dc.n_evaluated}`;
        return `<div class="text-[10px] text-zinc-500 mb-1">${screenedLabel}</div>
            <table class="text-[11px]"><thead><tr class="text-zinc-600"><th class="pr-2 text-left">ticker</th><th class="pr-2">score</th><th class="pr-2 text-left">warnings</th><th class="pr-2">ret</th><th>v</th></tr></thead><tbody>${rows}</tbody></table>${more}`;
    }

    function renderRadarBody(d, re) {
        const dc = d.decision_content || {};
        const themes = (dc.themes || []).slice(0, 3);
        const lines = themes.map(t => `<div class="text-[11px] truncate"><span class="font-bold">${t.name}</span> <span class="text-zinc-500">(${t.direction}, ${t.lifecycle_stage}, conf=${t.confidence})</span></div>`).join('');
        return `<div class="text-[11px] text-zinc-500 mb-1">${(re.pending ? '⏳ ' : '')}window ${re.window_complete_pct}% · ${(dc.themes || []).length} themes</div>${lines}`;
    }

    function renderEarningsBody(d, re) {
        const dc = d.decision_content || {};
        const summary = dc.summary || {};
        const ab = (dc.results || []).filter(r => ['A', 'B'].includes(r.grade)).slice(0, 5);
        const rows = ab.map(r => `<div class="text-[11px]"><span class="font-mono font-bold">${r.symbol}</span> <span class="text-zinc-500">${r.grade} score=${r.composite_score} gap=${r.gap_pct}%</span></div>`).join('');
        return `<div class="text-[10px] text-zinc-500 mb-1">A:${summary.grade_a} B:${summary.grade_b} C:${summary.grade_c} D:${summary.grade_d}</div>${rows}`;
    }

    function renderWeeklyBody(d, re) {
        const dc = d.decision_content || {};
        return `<div class="text-[11px] text-zinc-400">
            pending=${dc.pending} · hit_rate=${dc.hit_rate ?? '—'} · alpha=${dc.avg_alpha_pct ?? '—'}%
        </div>`;
    }

    function renderPostmortemBody(d, re) {
        const dc = d.decision_content || {};
        const buckets = (dc.decision_buckets || []).slice(0, 5).map(b =>
            `<span class="text-[11px] mr-2"><span class="text-zinc-500">${b.bucket}</span>: n=${b.n} (${b.ret_so_far})</span>`).join('');
        return `<div class="text-[11px] text-zinc-400 mb-1">parsed ${dc.reports_parsed} reports · ${dc.with_outcome} with outcome</div>${buckets}`;
    }

    // ── Right Rail: Coming Up — sourced from data.json.upcoming_events[] ──
    // Schema: reports/decision_review/UPCOMING_EVENTS_SCHEMA.md

    function renderUpcoming() {
        const today = new Date(todayIso || browserTodayIso());
        const seven = new Date(today);
        seven.setDate(today.getDate() + 7);

        const events = upcomingEvents.filter(e => {
            if (!e.date) return false;
            const dt = new Date(e.date);
            return dt >= today && dt <= seven;
        });

        const list = document.getElementById('cal-upcoming-list');
        const emptyEl = document.getElementById('cal-upcoming-empty');

        if (events.length === 0) {
            list.innerHTML = '';
            emptyEl.classList.remove('hidden');
            UI.icons();
            return;
        }
        emptyEl.classList.add('hidden');

        // Group by offset_days
        const byOffset = {};
        for (const e of events) {
            const dt = new Date(e.date);
            const offset = Math.round((dt - today) / 86400000);
            (byOffset[offset] = byOffset[offset] || []).push(e);
        }

        const isZh = UI.currentLang === 'zh';
        const dows = isZh ? ['日', '一', '二', '三', '四', '五', '六']
                          : ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];

        let html = '';
        for (const offset of Object.keys(byOffset).sort((a, b) => Number(a) - Number(b))) {
            const items = byOffset[offset];
            const dt = new Date(today);
            dt.setDate(today.getDate() + Number(offset));

            let relLabel;
            if (Number(offset) === 0) relLabel = isZh ? '今天' : 'Today';
            else if (Number(offset) === 1) relLabel = isZh ? '明天' : 'Tomorrow';
            else relLabel = (isZh ? '週' : '') + dows[dt.getDay()];

            const dateBadge = `${(dt.getMonth() + 1).toString().padStart(2, '0')}/${dt.getDate().toString().padStart(2, '0')}`;

            html += `<div class="cal-upcoming-group">
                <div class="cal-upcoming-day-label">
                    <span class="cal-upcoming-day-relative${Number(offset) <= 1 ? ' is-tomorrow' : ''}">${relLabel}</span>
                    <span class="cal-upcoming-day-date">${dateBadge}</span>
                    <span class="cal-upcoming-day-countdown">+${offset}d</span>
                </div>`;

            // Sort: binary first, then by impact (high→low)
            const impactOrder = { high: 0, med: 1, low: 2 };
            items.sort((a, b) => {
                const ab = (b.is_binary ? 1 : 0) - (a.is_binary ? 1 : 0);
                if (ab !== 0) return ab;
                return (impactOrder[a.impact] ?? 3) - (impactOrder[b.impact] ?? 3);
            });

            for (const e of items) html += renderUpcomingCard(e);
            html += '</div>';
        }
        list.innerHTML = html;
        UI.icons();
    }

    function renderUpcomingCard(e) {
        const impactClass = `cal-upcoming-impact-${e.impact || 'low'}`;
        const cat = e.category || 'system';
        const meta = CATEGORY_META[cat] || { icon: '📅' };
        const typeLabels = {
            earnings:     { zh: '財報',     en: 'Earnings' },
            macro:        { zh: '聯準會',   en: 'Fed/Macro' },
            econ:         { zh: '經濟數據', en: 'Econ Data' },
            binary:       { zh: '二元事件', en: 'Binary' },
            geopolitical: { zh: '地緣政治', en: 'Geopolitical' },
            watchlist:    { zh: '觀察清單', en: 'Watchlist' },
            system:       { zh: '系統',     en: 'System' },
        };
        const lang = UI.currentLang;
        const typeLabel = (typeLabels[cat] || { zh: cat, en: cat })[lang === 'zh' ? 'zh' : 'en'];

        const tickerChips = (e.tickers && e.tickers.length)
            ? e.tickers.slice(0, 3).map(t => `<span class="cal-upcoming-ticker-chip">${renderTickerLogo(t, { size: 14 })}<span>${t}</span></span>`).join('')
            : '';

        // Sector chips (smaller, different tone). 顯示前 3 個避免擠爆。
        const sectorChips = (e.sectors && e.sectors.length && (!e.tickers || e.tickers.length === 0))
            ? e.sectors.slice(0, 3).map(s =>
                `<span class="cal-upcoming-sector-chip" title="${s}">${s.replace(/_/g, ' ').slice(0, 10)}</span>`
              ).join('') + (e.sectors.length > 3 ? `<span class="cal-upcoming-sector-chip-more">+${e.sectors.length - 3}</span>` : '')
            : '';

        const timeChip = e.time
            ? `<span class="cal-upcoming-time-chip" title="${e.time}">${e.time === 'ALL' ? '🌐' : e.time}</span>`
            : '';

        const binaryFlag = e.is_binary
            ? `<span class="cal-upcoming-binary-flag" title="${lang === 'zh' ? '二元事件' : 'Binary risk'}">⚠</span>`
            : '';

        // description 顯示為第二行小字 (如果有)
        const descEsc = (e.description || '').replace(/"/g, '&quot;');
        const descRow = e.description
            ? `<div class="cal-upcoming-card-desc" title="${descEsc}">${e.description}</div>`
            : '';

        // tooltip 用 raw_title (原始長文) 讓 hover 還能看到完整脈絡
        const tooltipText = ((e.source_payload && e.source_payload.raw_title) || e.title || '').replace(/"/g, '&quot;');
        const cls = e.is_binary ? 'cal-upcoming-card cal-upcoming-card-binary' : 'cal-upcoming-card';

        // V1.71 — earnings event: append "📊 跑財報" / "📄 看報告" action button
        const primaryTicker = (cat === 'earnings' && e.tickers && e.tickers.length) ? e.tickers[0].toUpperCase() : null;
        let earningsActionRow = '';
        if (primaryTicker) {
            const cached = earningsCacheMap[primaryTicker];
            if (cached && cached.composite_score != null) {
                const verdict = cached.verdict || 'n/a';
                const score = cached.composite_score;
                const verdictClass = ({
                    STRONG: 'text-emerald-400', SOLID: 'text-emerald-500',
                    MIXED: 'text-amber-400', WEAK: 'text-orange-500',
                    DETERIORATING: 'text-red-500',
                }[verdict]) || 'text-zinc-400';
                const reportLink = cached.report_path
                    ? `<button class="cal-earnings-btn" onclick="event.stopPropagation();window.open('/${cached.report_path}','_blank')" title="${lang==='zh'?'開啟報告':'Open report'}">📄 ${lang==='zh'?'看報告':'Report'}</button>`
                    : '';
                const refreshBtn = `<button class="cal-earnings-btn cal-earnings-btn-refresh" onclick="event.stopPropagation();window.runEarningsAnalysis('${primaryTicker}')" title="${lang==='zh'?'重新分析(會排隊)':'Re-run (queues)'}">🔄</button>`;
                earningsActionRow = `<div class="cal-earnings-action-row">
                    <span class="cal-earnings-cached-badge ${verdictClass}" title="${lang==='zh'?'已有財報分析':'Cached analysis'}">${verdict} ${score}/100</span>
                    ${reportLink}
                    ${refreshBtn}
                </div>`;
            } else {
                earningsActionRow = `<div class="cal-earnings-action-row">
                    <button class="cal-earnings-btn cal-earnings-btn-run" onclick="event.stopPropagation();window.runEarningsAnalysis('${primaryTicker}')" title="${lang==='zh'?'排隊跑深度財報分析(5-10 分鐘)':'Queue earnings analysis (5-10 min)'}">📊 ${lang==='zh'?'跑財報分析':'Run earnings'}</button>
                </div>`;
            }
        }

        return `<div class="${cls}" title="${tooltipText}">
            <span class="cal-upcoming-impact-dot ${impactClass}" title="${e.impact || 'low'} impact"></span>
            <span class="cal-upcoming-card-icon">${meta.icon}</span>
            <div class="cal-upcoming-card-body">
                <div class="cal-upcoming-card-title-row">
                    <span class="cal-upcoming-card-title">${binaryFlag}${e.title}</span>
                    ${timeChip}
                </div>
                ${descRow}
                <div class="cal-upcoming-card-meta-row">
                    <span class="cal-upcoming-card-type">${typeLabel}</span>
                    ${tickerChips}${sectorChips}
                </div>
                ${earningsActionRow}
            </div>
        </div>`;
    }

    // V1.71 — global handler for inline earnings buttons
    window.runEarningsAnalysis = async function(ticker) {
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
    };

    // ── Bottom: Aggregate stat tiles (respects active filters) ───────────
    function renderAggregate() {
        const bySrc = {};
        for (const d of allDecisions) {
            if (!decisionPasses(d)) continue;
            const s = d.source;
            const v = d.verdict?.label || 'n/a';
            (bySrc[s] = bySrc[s] || { hit: 0, miss: 0, neutral: 0, pending: 0, 'n/a': 0 })[v]++;
        }

        const order = ['deep-dive', 'sector-scan', 'news-digest', 'theme-detector',
            'momentum-screen', 'thematic-screener', 'earnings-analyzer',
            'short-term-weekly', 'postmortem'];

        const ct = (window.i18n?.[UI.currentLang]?.calendar) || {};
        const srcLabels = ct.sources || {};
        const decisionsLbl = ct.agg_decisions || 'decisions';
        const hitRateLbl   = ct.agg_hit_rate  || 'hit rate';

        let html = '';
        for (const s of order) {
            const c = bySrc[s];
            if (!c) continue;
            const n = c.hit + c.miss + c.neutral + c.pending + c['n/a'];
            const evaluable = c.hit + c.miss + c.neutral;
            const hitRate = evaluable > 0 ? (c.hit / evaluable * 100) : null;
            const hitRateStr = hitRate != null ? hitRate.toFixed(0) + '%' : '—';
            const hitRateColor = hitRate == null ? 'text-zinc-500'
                : hitRate >= 60 ? 'text-green-400'
                    : hitRate >= 40 ? 'text-yellow-400' : 'text-red-400';
            const meta = SOURCE_META[s] || { icon: '?', label: s };
            const srcLabel = srcLabels[s] || meta.label;

            // build segmented bar
            const segs = ['hit', 'miss', 'neutral', 'pending', 'n/a'].map(k => {
                if (c[k] === 0) return '';
                const pct = (c[k] / n * 100);
                const cls = VERDICT_META[k].barClass;
                return `<div class="${cls}" style="width:${pct}%" title="${k}: ${c[k]}"></div>`;
            }).join('');

            // mini tags for non-zero counts
            const tags = ['hit', 'miss', 'neutral', 'pending'].filter(k => c[k] > 0).map(k => {
                const vm = VERDICT_META[k];
                return `<span class="cal-stat-mini-tag ${vm.badgeClass}">${vm.emoji} ${c[k]}</span>`;
            }).join('');

            html += `<div class="cal-stat-tile">
                <div class="cal-stat-source">
                    <span class="cal-stat-source-icon">${meta.icon}</span>
                    <span>${srcLabel}</span>
                </div>
                <div class="cal-stat-numbers">
                    <span class="cal-stat-n">${n}</span>
                    <span class="cal-stat-n-label">${decisionsLbl}</span>
                </div>
                <div class="cal-stat-hitrate ${hitRateColor}">${hitRateLbl} ${hitRateStr}</div>
                <div class="cal-stat-bar">${segs}</div>
                <div class="cal-stat-tags">${tags}</div>
            </div>`;
        }
        document.getElementById('cal-aggregate-table').innerHTML =
            `<div class="cal-aggregate-grid">${html}</div>`;
    }

    // ── Monthly Summary (Past 30d analyses pill cloud) ────────────────────
    function renderMonthlySummary() {
        const host = document.getElementById('cal-monthly-summary-body');
        if (!host) return;
        const isZh = UI.currentLang === 'zh';
        const todayD = new Date(todayIso);
        const cutoff = new Date(todayD); cutoff.setDate(todayD.getDate() - 30);

        const recent = recentAnalysis.filter(a => {
            if (!a.time) return false;
            const d = new Date(a.time.slice(0, 10));
            return d >= cutoff && d <= todayD;
        });

        if (!recent.length) {
            host.innerHTML = `<div class="text-xs text-zinc-500 italic">${isZh ? '近 30 天無分析記錄' : 'No analyses in last 30 days'}</div>`;
            return;
        }

        const buckets = { EXECUTE: 0, STAGED: 0, CANCEL: 0, OTHER: 0 };
        for (const a of recent) {
            const k = (a.decision || '').toUpperCase();
            if (k in buckets) buckets[k]++; else buckets.OTHER++;
        }

        const summaryLine = isZh
            ? `<span class="cal-monthly-stat-num">${recent.length}</span> 筆 · <span class="text-emerald-400">${buckets.EXECUTE} EXECUTE</span> / <span class="text-amber-400">${buckets.STAGED} STAGED</span> / <span class="text-red-400">${buckets.CANCEL} CANCEL</span>`
            : `<span class="cal-monthly-stat-num">${recent.length}</span> decisions · <span class="text-emerald-400">${buckets.EXECUTE} EXECUTE</span> / <span class="text-amber-400">${buckets.STAGED} STAGED</span> / <span class="text-red-400">${buckets.CANCEL} CANCEL</span>`;

        // Dedupe by ticker; latest decision wins. Sort by time desc.
        const byTicker = {};
        for (const a of recent) {
            const tk = (a.ticker || '').toUpperCase();
            if (!tk) continue;
            const prev = byTicker[tk];
            if (!prev || new Date(a.time) > new Date(prev.time)) byTicker[tk] = a;
        }
        const tickers = Object.values(byTicker).sort((a, b) => new Date(b.time) - new Date(a.time));

        const pills = tickers.map(a => {
            const tk = a.ticker.toUpperCase();
            const dec = (a.decision || '').toUpperCase();
            const tone = dec === 'EXECUTE' ? 'is-execute'
                       : dec === 'STAGED' ? 'is-staged'
                       : dec === 'CANCEL' ? 'is-cancel' : 'is-other';
            const url = a.report_url ? '/' + a.report_url : '';
            const open = url ? `onclick="window.open('${url}','_blank')"` : '';
            const date = (a.time || '').slice(5, 10);
            return `<span class="cal-monthly-pill ${tone}" title="${tk} ${dec} · ${a.time}" ${open}>
                ${renderTickerLogo(tk, { size: 16 })}
                <span class="cal-monthly-pill-ticker">${tk}</span>
                <span class="cal-monthly-pill-date">${date}</span>
            </span>`;
        }).join('');

        host.innerHTML = `<div class="cal-monthly-summary-line">${summaryLine}</div>
            <div class="cal-monthly-pill-cloud">${pills}</div>`;
    }

    // ── Coming Up Strip (Next 7 days) — replaces hidden right-rail ────────
    function renderUpcomingStrip() {
        const host = document.getElementById('cal-upcoming-strip-body');
        if (!host) return;
        const isZh = UI.currentLang === 'zh';
        const today = new Date(todayIso);
        const seven = new Date(today); seven.setDate(today.getDate() + 7);

        const events = upcomingEvents.filter(e => {
            if (!e.date) return false;
            if (!eventPassesDensity(e)) return false;
            const dt = new Date(e.date);
            return dt >= today && dt <= seven;
        });

        if (!events.length) {
            host.innerHTML = `<div class="text-xs text-zinc-500 italic">${isZh ? '未來 7 天無重要事件（已套用 high-impact + 觀察清單篩選）' : 'No high-impact events in next 7 days'}</div>`;
            return;
        }

        // Group by date
        const byDate = {};
        for (const e of events) (byDate[e.date] = byDate[e.date] || []).push(e);
        const dates = Object.keys(byDate).sort();

        const dows = isZh ? ['日', '一', '二', '三', '四', '五', '六']
                          : ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];

        const rows = dates.map(dateStr => {
            const items = byDate[dateStr];
            const dt = new Date(dateStr);
            const offset = Math.round((dt - today) / 86400000);
            const rel = offset === 0 ? (isZh ? '今天' : 'Today')
                      : offset === 1 ? (isZh ? '明天' : 'Tomorrow')
                      : (isZh ? '週' : '') + dows[dt.getDay()];
            const dateBadge = `${(dt.getMonth() + 1).toString().padStart(2, '0')}/${dt.getDate().toString().padStart(2, '0')}`;

            // Group by category for compact display
            const byCat = {};
            for (const e of items) (byCat[e.category || 'system'] = byCat[e.category || 'system'] || []).push(e);
            const catOrder = ['earnings', 'macro', 'binary', 'econ', 'geopolitical', 'system'];
            const catCells = catOrder.filter(c => byCat[c]).map(c => {
                const arr = byCat[c];
                const meta = CATEGORY_META[c] || { icon: '📅' };
                const tickered = arr.filter(e => Array.isArray(e.tickers) && e.tickers.length);
                const non = arr.filter(e => !(Array.isArray(e.tickers) && e.tickers.length));
                let body;
                if (tickered.length) {
                    const stackItems = tickered.map(e => ({
                        ticker: e.tickers[0].toUpperCase(),
                        ringColor: e.is_binary ? 'rgba(239, 68, 68, 0.85)' : (e.impact === 'high' ? 'rgba(245, 158, 11, 0.7)' : 'transparent'),
                    }));
                    const labels = tickered.slice(0, 4).map(e => e.tickers[0].toUpperCase()).join(' ');
                    const more = tickered.length > 4 ? ` +${tickered.length - 4}` : '';
                    body = `${renderLogoStack(stackItems, { size: 18, max: 4 })}<span class="cal-up-strip-tickers">${labels}${more}</span>`;
                } else {
                    const titles = non.slice(0, 2).map(e => e.title || '').join(' · ');
                    const more = non.length > 2 ? ` +${non.length - 2}` : '';
                    body = `<span class="cal-up-strip-text">${titles}${more}</span>`;
                }
                return `<span class="cal-up-strip-cat" title="${c}">
                    <span class="cal-up-strip-cat-icon">${meta.icon}</span>${body}
                </span>`;
            }).join('');

            return `<div class="cal-up-strip-row">
                <div class="cal-up-strip-date">
                    <span class="cal-up-strip-rel">${rel}</span>
                    <span class="cal-up-strip-mmdd">${dateBadge}</span>
                </div>
                <div class="cal-up-strip-cells">${catCells}</div>
            </div>`;
        }).join('');

        host.innerHTML = rows;
    }

    // ── LLM Review (backend queue + status poll + result render) ──────────
    async function requestLlmReview() {
        const isZh = UI.currentLang === 'zh';
        const confirmMsg = isZh
            ? 'LLM 檢討會跑 ~10–15 分鐘並消耗 Claude API tokens（event_index 約 300KB + 三步驟推論）。確定要排入佇列？'
            : 'LLM Review takes ~10–15 min and consumes Claude API tokens (event_index ≈ 300KB + 3-step reasoning). Queue it?';
        if (!window.confirm(confirmMsg)) return;
        try {
            const r = await fetch('/api/protocol-queue', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ name: 'llm_review' })
            });
            const body = await r.json();
            if (r.status === 202 && body.queued) {
                const pos = body.position || '?';
                UI.showToast(isZh ? `已排入 LLM 檢討（第 ${pos} 位，~10-15 min）` : `Queued LLM Review (#${pos}, ~10-15 min)`, 'info', 4000);
                startLlmReviewPoll();
            } else if (r.status === 409 && body.reason === 'duplicate_active') {
                UI.showToast(isZh ? 'LLM 檢討執行中' : 'LLM Review already running', 'warn', 3000);
                startLlmReviewPoll();
            } else if (r.status === 409 && body.reason === 'duplicate_pending') {
                UI.showToast(isZh ? 'LLM 檢討已在佇列' : 'LLM Review already queued', 'warn', 3000);
                startLlmReviewPoll();
            } else {
                UI.showToast(isZh ? `加入失敗：${body.error || r.status}` : `Failed: ${body.error || r.status}`, 'error', 4000);
            }
        } catch (e) {
            UI.showToast(isZh ? `網路錯誤：${e.message}` : `Network error: ${e.message}`, 'error', 4000);
        }
    }

    function startLlmReviewPoll() {
        if (llmReviewPollTimer) return;
        setLlmReviewBtnRunning(0);
        llmReviewPollTimer = setInterval(pollLlmReviewStatus, 3000);
        pollLlmReviewStatus();
    }
    function stopLlmReviewPoll() {
        if (llmReviewPollTimer) clearInterval(llmReviewPollTimer);
        llmReviewPollTimer = null;
        setLlmReviewBtnIdle();
    }

    async function pollLlmReviewStatus() {
        const isZh = UI.currentLang === 'zh';
        try {
            const r = await fetch('/api/run-protocol/status', { cache: 'no-store' });
            if (!r.ok) return;
            const s = await r.json();
            // Only react when the *currently active* protocol is llm_review
            if (s.name !== 'llm_review') return;
            if (s.status === 'running') {
                setLlmReviewBtnRunning(s.elapsed_sec || 0);
            } else if (s.status === 'done') {
                stopLlmReviewPoll();
                UI.showToast(isZh ? 'LLM 檢討完成，正在載入結果…' : 'LLM Review done, loading…', 'info', 3000);
                await loadLatestReview();
            } else if (s.status === 'error') {
                stopLlmReviewPoll();
                const tail = (s.log_tail || '').slice(-300);
                UI.showToast(isZh ? `LLM 檢討失敗：${tail}` : `LLM Review failed: ${tail}`, 'error', 8000);
            }
        } catch (e) {
            // Network blip; let interval retry
        }
    }

    async function checkLlmReviewRunning() {
        try {
            const r = await fetch('/api/run-protocol/status', { cache: 'no-store' });
            if (!r.ok) return;
            const s = await r.json();
            if (s.name === 'llm_review' && s.status === 'running') startLlmReviewPoll();
        } catch {}
    }

    function setLlmReviewBtnRunning(elapsed) {
        const btn = document.getElementById('cal-llm-review');
        const lbl = document.getElementById('cal-llm-btn-text');
        const refreshBtn = document.getElementById('cal-llm-review-refresh');
        if (!btn || !lbl) return;
        btn.disabled = true;
        btn.classList.add('cal-llm-review-running');
        const isZh = UI.currentLang === 'zh';
        lbl.textContent = isZh ? `檢討中… ${elapsed}s` : `Reviewing… ${elapsed}s`;
        if (refreshBtn) {
            refreshBtn.disabled = true;
            refreshBtn.classList.add('cal-llm-review-running');
        }
    }
    function setLlmReviewBtnIdle() {
        const btn = document.getElementById('cal-llm-review');
        const lbl = document.getElementById('cal-llm-btn-text');
        const refreshBtn = document.getElementById('cal-llm-review-refresh');
        if (!btn || !lbl) return;
        btn.disabled = false;
        btn.classList.remove('cal-llm-review-running');
        const isZh = UI.currentLang === 'zh';
        lbl.textContent = isZh ? '請 LLM 檢討' : 'Ask LLM Review';
        if (refreshBtn) {
            refreshBtn.disabled = false;
            refreshBtn.classList.remove('cal-llm-review-running');
        }
    }

    async function loadLatestReview() {
        const host = document.getElementById('cal-llm-review-body');
        const meta = document.getElementById('cal-llm-review-meta');
        if (!host) return;
        const isZh = UI.currentLang === 'zh';
        // Try today first, walk back up to 14 days for fallback
        const today = new Date(todayIso || browserTodayIso());
        for (let offset = 0; offset < 14; offset++) {
            const d = new Date(today); d.setDate(today.getDate() - offset);
            const iso = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
            const url = `/decision_review/REVIEW_${iso}.md`;
            try {
                const r = await fetch(url, { cache: 'no-store' });
                if (!r.ok) continue;
                const md = await r.text();
                host.innerHTML = renderReviewMarkdown(md);
                // Extract summary metadata: decisions_analyzed + pattern count + recommendation count
                const decsMatch = md.match(/_decisions_analyzed:\s*(\d+)/);
                const idxAtMatch = md.match(/_event_index_at:\s*([\dT:\.\-]+)/);
                const patternCount = (md.match(/^### .+?\(n=\d+/gm) || []).length;
                const recCount = ((md.split(/^## +Adjustment Recommendations\b/m)[1] || '').match(/^### /gm) || []).length;
                if (meta) {
                    const parts = [isZh ? `${iso} 產出` : `${iso}`];
                    if (decsMatch) parts.push(isZh ? `${decsMatch[1]} 筆決策` : `${decsMatch[1]} decisions`);
                    if (patternCount) parts.push(isZh ? `${patternCount} patterns` : `${patternCount} patterns`);
                    if (recCount) parts.push(isZh ? `${recCount} 建議` : `${recCount} recs`);
                    meta.textContent = parts.join(' · ');
                }
                document.getElementById('cal-llm-review-section')?.classList.add('cal-llm-review-has-result');
                return;
            } catch {}
        }
        host.innerHTML = `<div class="cal-llm-review-empty">${isZh ? '尚未跑過 LLM 檢討。點右上角「請 LLM 檢討」觸發。' : 'No LLM Review yet. Click "Ask LLM Review" at top-right.'}</div>`;
        if (meta) meta.textContent = isZh ? '尚未產出' : 'no review yet';
    }

    // Hand-rolled markdown → safe HTML.
    // Supports: # / ## / ### headers, - / * bullets, **bold**, `inline code`, paragraphs, hr (---).
    // Intentionally minimal — review output uses these patterns and nothing more.
    function renderReviewMarkdown(md) {
        const escapeHtml = (s) => s.replace(/[&<>"']/g, c => ({
            '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;',
        }[c]));
        const inlines = (s) => escapeHtml(s)
            .replace(/`([^`]+)`/g, '<code>$1</code>')
            .replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
            .replace(/_([^_]+)_/g, '<em>$1</em>');
        const lines = md.split(/\r?\n/);
        const out = [];
        let inList = false;
        const closeList = () => { if (inList) { out.push('</ul>'); inList = false; } };
        for (const raw of lines) {
            const line = raw.trimEnd();
            if (!line.trim()) { closeList(); out.push(''); continue; }
            if (/^---+\s*$/.test(line)) { closeList(); out.push('<hr>'); continue; }
            const h = line.match(/^(#{1,6})\s+(.+)$/);
            if (h) { closeList(); const lvl = h[1].length; out.push(`<h${lvl}>${inlines(h[2])}</h${lvl}>`); continue; }
            const li = line.match(/^[\-\*]\s+(.+)$/);
            if (li) {
                if (!inList) { out.push('<ul>'); inList = true; }
                out.push(`<li>${inlines(li[1])}</li>`);
                continue;
            }
            closeList();
            out.push(`<p>${inlines(line)}</p>`);
        }
        closeList();
        return out.join('\n');
    }

})();
