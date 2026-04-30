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
    let upcomingEvents = [];           // from data.json upcoming_events[]
    let earningsCacheMap = {};         // V1.71 — TICKER → {composite_score, verdict, report_path, ...}
    let generatedAt = '';
    let todayIso = '';                 // 瀏覽器當天，每次 load 都重算（不再吃 indexer 的 j.today）
    let indexedAt = '';                // event_index.json 的 today（僅在 stats 顯示，做 staleness 提示）
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
        document.getElementById('cal-llm-review').addEventListener('click', copyLlmReviewBundle);
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') closeDetailPanel();
        });
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
        set('cal-aggregate-title',        t.aggregate       || (isZh ? '依來源彙總' : 'Aggregate by Source'));
        set('cal-aggregate-hint',         t.aggregate_hint  || (isZh ? 'verdict 分布 + 命中率' : 'verdict distribution + hit rate'));

        rebuildFilterBar();

        // Re-render data-driven sections so translated strings apply
        if (allDecisions.length) {
            renderGrid();
            renderAggregate();
        }
    }

    // ── Data load ─────────────────────────────────────────────────────────
    async function loadAndRender() {
        try {
            // Parallel: event_index for past decisions + data.json for upcoming events
            const [evRes, dashRes] = await Promise.all([
                fetch(EVENT_INDEX_URL, { cache: 'no-store' }),
                fetch(DASHBOARD_DATA_URL, { cache: 'no-store' }),
            ]);
            if (!evRes.ok) throw new Error('event_index not found');
            const j = await evRes.json();
            allDecisions = j.decisions || [];
            generatedAt = j.generated_at || '';
            indexedAt = j.today || '';        // indexer 跑的當天（可能比實際今日舊）
            todayIso = browserTodayIso();     // 始終用瀏覽器當天

            if (dashRes.ok) {
                const dash = await dashRes.json();
                upcomingEvents = Array.isArray(dash.upcoming_events) ? dash.upcoming_events : [];
                // V1.71 — earnings-analyst cache index for inline cached-state chips
                earningsCacheMap = {};
                for (const ea of (dash.earnings_analyses || [])) {
                    if (ea && ea.ticker) earningsCacheMap[ea.ticker.toUpperCase()] = ea;
                }
            } else {
                upcomingEvents = [];
                earningsCacheMap = {};
            }

            // 自動跳到今天所在月份（瀏覽器當天，非 indexer 當天）
            const [y, m] = todayIso.split('-').map(Number);
            currentMonth = new Date(y, m - 1, 1);

            document.getElementById('cal-no-data').classList.add('hidden');
            document.getElementById('cal-main').classList.remove('hidden');
            document.getElementById('cal-aggregate').classList.remove('hidden');

            let stats = `${allDecisions.length} decisions · ${upcomingEvents.length} upcoming · today=${todayIso}`;
            if (indexedAt && indexedAt !== todayIso) {
                stats += ` · indexed=${indexedAt}`;
            }
            document.getElementById('cal-stats').textContent = stats;

            renderGrid();
            renderUpcoming();
            renderAggregate();
        } catch (e) {
            console.error('[calendar] load failed', e);
            document.getElementById('cal-no-data').classList.remove('hidden');
            document.getElementById('cal-main').classList.add('hidden');
            document.getElementById('cal-aggregate').classList.add('hidden');
        }
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
    function upcomingEventsByDate() {
        const m = {};
        for (const e of upcomingEvents) {
            if (!e.date) continue;
            if (!eventPasses(e)) continue;
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

            cell.innerHTML = dayNum + renderBadges(decisions) + renderEventChips(events);

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

    // Compact category-grouped chips for upcoming events on a calendar date.
    // Each chip: <icon><count>; binary/high-impact get tinted styles. Up to 4
    // categories shown — overflow shows "+N" tail. Click cell → drawer.
    function renderEventChips(events) {
        if (!events.length) return '';

        const byCat = {};
        for (const e of events) {
            const cat = e.category || 'system';
            (byCat[cat] = byCat[cat] || []).push(e);
        }

        // Order: categories with binary first, then high-impact, then by count
        const ordered = Object.entries(byCat).sort((a, b) => {
            const aBin = a[1].some(e => e.is_binary) ? 1 : 0;
            const bBin = b[1].some(e => e.is_binary) ? 1 : 0;
            if (aBin !== bBin) return bBin - aBin;
            const aHigh = a[1].some(e => e.impact === 'high') ? 1 : 0;
            const bHigh = b[1].some(e => e.impact === 'high') ? 1 : 0;
            if (aHigh !== bHigh) return bHigh - aHigh;
            return b[1].length - a[1].length;
        });

        const VISIBLE = 4;
        let chips = '';
        for (const [cat, arr] of ordered.slice(0, VISIBLE)) {
            const meta = CATEGORY_META[cat] || { icon: '📅' };
            const hasBin = arr.some(e => e.is_binary);
            const hasHigh = arr.some(e => e.impact === 'high');
            const cls = hasBin ? 'cal-cell-event-chip-binary'
                      : hasHigh ? 'cal-cell-event-chip-high'
                      : '';
            const titlesArr = arr.map(e => {
                const t = e.title || '';
                const tk = (e.tickers && e.tickers[0]) ? `[${e.tickers[0]}] ` : '';
                return tk + t;
            });
            const tooltip = titlesArr.join(' · ').replace(/"/g, '&quot;');
            const countTag = arr.length > 1
                ? `<span class="cal-cell-event-count">${arr.length}</span>`
                : '';
            chips += `<span class="cal-cell-event-chip ${cls}" title="${tooltip}">${meta.icon}${countTag}</span>`;
        }

        if (ordered.length > VISIBLE) {
            const extra = ordered.slice(VISIBLE).reduce((sum, [, arr]) => sum + arr.length, 0);
            chips += `<span class="cal-cell-event-more">+${extra}</span>`;
        }

        return `<div class="cal-cell-events">${chips}</div>`;
    }

    function renderBadges(decisions) {
        if (!decisions.length) return '';
        const bySrc = groupBySource(decisions);
        const ordered = Object.entries(bySrc).sort((a, b) => b[1].length - a[1].length);
        let html = '<div class="cal-badge-row">';
        for (const [src, arr] of ordered) {
            const meta = SOURCE_META[src] || { icon: '?' };
            const v = aggregateVerdictColor(arr);
            const vMeta = VERDICT_META[v];
            const count = arr.length > 1 ? `<span class="cal-badge-count">${arr.length}</span>` : '';
            html += `<span class="cal-badge ${vMeta.badgeClass}" title="${src} (${arr.length}) — ${v}">${meta.icon}${count}</span>`;
        }
        html += '</div>';
        return html;
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
        panel.classList.remove('hidden');
        panel.setAttribute('aria-hidden', 'false');
        // Force reflow then trigger expand transition
        requestAnimationFrame(() => panel.classList.add('cal-detail-open'));
        UI.icons();

        // Smoothly bring the panel into view if user clicked a cell scrolled high up
        requestAnimationFrame(() => {
            panel.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
        });
    }

    function closeDetailPanel() {
        const panel = document.getElementById('cal-detail');
        if (!panel) return;
        panel.classList.remove('cal-detail-open');
        panel.setAttribute('aria-hidden', 'true');
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
            ? `<span class="font-mono font-bold text-sm">${ticker}</span>`
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
            ? e.tickers.slice(0, 3).map(t => `<span class="cal-upcoming-ticker-chip">${t}</span>`).join('')
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

    // ── LLM Review button ────────────────────────────────────────────────
    async function copyLlmReviewBundle() {
        try {
            const [pr, ir] = await Promise.all([
                fetch(REVIEW_PROMPT_URL, { cache: 'no-store' }),
                fetch(EVENT_INDEX_URL, { cache: 'no-store' }),
            ]);
            const promptText = await pr.text();
            const idxText = await ir.text();

            const bundle =
                promptText +
                '\n\n---\n\n' +
                '# Event Index Data\n\n' +
                '```json\n' + idxText + '\n```\n';

            await navigator.clipboard.writeText(bundle);
            UI.showToast(
                UI.currentLang === 'zh'
                    ? '已複製 prompt + 最新 event_index 到 clipboard, 貼到新 Claude 對話即可'
                    : 'Copied prompt + latest event_index to clipboard. Paste into a new Claude conversation.',
                'info', 5000);
        } catch (e) {
            console.error('[calendar] copy failed', e);
            UI.showToast('Copy failed: ' + e.message, 'error', 4000);
        }
    }

})();
