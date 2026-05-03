/**
 * page-earnings-detail.js — Earnings Detail Infographic page (V1.73)
 * Reads /api/earnings-infographic/<TICKER>, renders 7 sections with .ed-* classes.
 * Depends on: utils.js (window.UI), i18n.js, data-store.js (sidebar event bus only)
 */

(function () {
    'use strict';

    let _payload = null;     // last fetched {ticker, infographic, cache}
    let _markdownLoaded = false;

    // ── i18n helper ──────────────────────────────────────────────────────
    function ed() { return (window.i18n?.[UI.currentLang]?.earnings_detail) || {}; }

    function tStr(key, fallback) {
        const tr = ed();
        return tr[key] || fallback || key;
    }

    function applyTranslations() {
        document.querySelectorAll('[data-i18n-key]').forEach(el => {
            const key = el.getAttribute('data-i18n-key');
            const parts = key.split('.');
            let cur = window.i18n?.[UI.currentLang];
            for (const p of parts) cur = cur?.[p];
            if (cur) el.textContent = cur;
        });
        // Language-dependent dynamic strings re-render
        if (_payload) renderAll(_payload);
    }

    // ── Number formatters ────────────────────────────────────────────────
    function fmtUSD(n) {
        if (n == null || isNaN(n)) return '—';
        const abs = Math.abs(n);
        if (abs >= 1e12) return `$${(n / 1e12).toFixed(2)}T`;
        if (abs >= 1e9)  return `$${(n / 1e9).toFixed(1)}B`;
        if (abs >= 1e6)  return `$${(n / 1e6).toFixed(1)}M`;
        if (abs >= 1e3)  return `$${(n / 1e3).toFixed(1)}K`;
        return `$${n.toFixed(2)}`;
    }
    function fmtPct(n, decimals = 1) {
        if (n == null || isNaN(n)) return '—';
        const sign = n >= 0 ? '+' : '';
        return `${sign}${(n * 100).toFixed(decimals)}%`;
    }
    function fmtEPS(n) {
        if (n == null || isNaN(n)) return '—';
        return `$${Number(n).toFixed(2)}`;
    }

    // ── Get ticker from URL ──────────────────────────────────────────────
    function getTicker() {
        const params = new URLSearchParams(location.search);
        const t = (params.get('ticker') || '').toUpperCase();
        // Sanitize: only A-Z0-9.-
        return t.replace(/[^A-Z0-9.\-]/g, '');
    }

    // ── Hero render ──────────────────────────────────────────────────────
    function renderHero(payload) {
        const inf = payload.infographic || {};
        const cache = payload.cache || {};
        const snap = cache.snapshot || {};

        document.getElementById('ed-title-ticker').textContent = payload.ticker;
        const fiscalEl = document.getElementById('ed-fiscal-pill');
        if (inf.fiscal_label) {
            fiscalEl.textContent = inf.fiscal_label;
            fiscalEl.hidden = false;
        }
        const asOf = inf.as_of_date || cache.as_of_date || '';
        document.getElementById('ed-asof-pill').textContent = asOf ? `AS OF ${asOf}` : '';

        // Logo via FMP CDN (no API key required)
        const logo = document.getElementById('ed-hero-logo');
        logo.src = `https://financialmodelingprep.com/image-stock/${encodeURIComponent(payload.ticker)}.png`;
        logo.alt = payload.ticker;
        logo.onerror = () => { logo.style.display = 'none'; };

        document.getElementById('ed-hero-company').textContent = snap.companyName || payload.ticker;
        document.getElementById('ed-hero-oneliner').textContent = inf.headline_oneliner || '';

        // Verdict pill row (reuses logic from earnings page — small inline pill)
        const verdictRow = document.getElementById('ed-hero-verdict-row');
        verdictRow.innerHTML = '';
        if (cache.verdict) {
            const v = String(cache.verdict).toUpperCase();
            const color = v === 'STRONG' ? '#22c55e'
                        : v === 'SOLID'  ? '#16a34a'
                        : v === 'MIXED'  ? '#eab308'
                        : v === 'WEAK'   ? '#f97316'
                        : '#ef4444';
            const pill = document.createElement('span');
            pill.style.cssText = `font-size:10px;font-weight:900;padding:3px 9px;border-radius:999px;background:${color}1A;color:${color};letter-spacing:0.10em`;
            pill.textContent = `${v} · ${cache.composite_score ?? '—'}`;
            verdictRow.appendChild(pill);
        }
        if (snap.sector) {
            const s = document.createElement('span');
            s.style.cssText = 'font-size:10px;color:var(--text-muted);letter-spacing:0.06em';
            s.textContent = snap.sector;
            verdictRow.appendChild(s);
        }
    }

    // ── 4 metric cards ───────────────────────────────────────────────────
    function metricCard(label, valueStr, vsEstStr, beat) {
        const tr = ed();
        const cls = beat === true ? 'beat' : beat === false ? 'miss' : '';
        const flagText = beat === true ? (tr.beat || 'BEAT')
                       : beat === false ? (tr.miss || 'MISS') : '';
        const flagIcon = beat === true ? '✓' : beat === false ? '✗' : '·';
        return `
            <div class="ed-metric-card ${cls}">
                <div class="ed-metric-label">${UI.escapeHTML(label)}</div>
                <div class="ed-metric-value">${UI.escapeHTML(valueStr)}</div>
                <div class="ed-metric-vs">${UI.escapeHTML(vsEstStr)}</div>
                ${beat !== null ? `<div class="ed-metric-flag ${cls}">${flagIcon} ${UI.escapeHTML(flagText)}</div>` : ''}
            </div>`;
    }

    function renderMetricCards(surprise) {
        const grid = document.getElementById('ed-metric-cards');
        if (!surprise) { grid.innerHTML = ''; return; }
        const tr = ed();
        const vsTpl = tr.vs_estimate || 'Est. {value}';
        const cards = [];
        // Revenue
        if (surprise.revenue_actual != null) {
            const vs = vsTpl.replace('{value}', fmtUSD(surprise.revenue_estimated));
            cards.push(metricCard(tr.metric_revenue || 'Revenue',
                fmtUSD(surprise.revenue_actual), vs, surprise.revenue_beat));
        }
        // EPS
        if (surprise.eps_actual != null) {
            const vs = vsTpl.replace('{value}', fmtEPS(surprise.eps_estimated));
            cards.push(metricCard(tr.metric_eps || 'EPS',
                fmtEPS(surprise.eps_actual), vs, surprise.eps_beat));
        }
        // YoY revenue
        if (surprise.yoy_revenue_growth != null) {
            cards.push(metricCard(tr.metric_yoy_revenue || 'YoY Revenue',
                fmtPct(surprise.yoy_revenue_growth),
                surprise.revenue_surprise_pct != null
                    ? `Surprise ${fmtPct(surprise.revenue_surprise_pct, 2)}` : '',
                null));
        }
        // YoY EPS
        if (surprise.yoy_eps_growth != null) {
            cards.push(metricCard(tr.metric_yoy_eps || 'YoY EPS',
                fmtPct(surprise.yoy_eps_growth),
                surprise.eps_surprise_pct != null
                    ? `Surprise ${fmtPct(surprise.eps_surprise_pct, 2)}` : '',
                null));
        }
        grid.innerHTML = cards.join('');
    }

    // ── Segment cell helper ──────────────────────────────────────────────
    function segmentCell(name, amountUSD, yoyPct, iconName, highlight) {
        const yoyClass = yoyPct == null ? 'flat'
                       : yoyPct > 0.005  ? 'up'
                       : yoyPct < -0.005 ? 'down' : 'flat';
        const yoyTxt = yoyPct == null ? '—' : fmtPct(yoyPct);
        const iconHTML = iconName
            ? `<i data-lucide="${UI.escapeHTML(iconName)}" class="ed-segment-icon"></i>` : '';
        return `
            <div class="ed-segment-cell ${highlight ? 'highlight' : ''}">
                ${iconHTML}
                <div class="ed-segment-name">${UI.escapeHTML(name)}</div>
                <div class="ed-segment-amt">${UI.escapeHTML(fmtUSD(amountUSD))}</div>
                <div class="ed-segment-yoy ${yoyClass}">${UI.escapeHTML(yoyTxt)}</div>
            </div>`;
    }

    function renderSegments(segments_q) {
        const grid = document.getElementById('ed-segment-grid');
        const tag  = document.getElementById('ed-segments-fallback');
        const items = (segments_q || {}).items || [];
        if (!items.length) {
            grid.innerHTML = `<p class="text-[12px] text-zinc-600 italic">—</p>`;
            return;
        }
        tag.hidden = !segments_q.is_fy_fallback;
        grid.innerHTML = items.map(it => segmentCell(
            it.name || '?', it.amount_usd, it.yoy_pct, it.icon, !!it.highlight
        )).join('');
    }

    function renderGeographic(geographic_q) {
        const section = document.getElementById('ed-geo-section');
        const grid    = document.getElementById('ed-geo-grid');
        const tag     = document.getElementById('ed-geo-fallback');
        const items = (geographic_q || {}).items || [];
        if (items.length < 3) {
            section.hidden = true;     // skip when too coarse (e.g. MSFT US/Non-US only)
            return;
        }
        section.hidden = false;
        tag.hidden = !geographic_q.is_fy_fallback;
        grid.innerHTML = items.map(it => segmentCell(
            it.region || it.name || '?', it.amount_usd, it.yoy_pct, 'globe', false
        )).join('');
    }

    // ── Capital return ───────────────────────────────────────────────────
    function capretBlock(label, valueStr, subStr) {
        return `
            <div class="ed-capret-block">
                <div class="ed-capret-block-label">${UI.escapeHTML(label)}</div>
                <div class="ed-capret-block-value">${UI.escapeHTML(valueStr)}</div>
                ${subStr ? `<div class="ed-capret-block-sub">${UI.escapeHTML(subStr)}</div>` : ''}
            </div>`;
    }

    function renderCapitalReturn(cap, dividends) {
        const card = document.getElementById('ed-capret-card');
        const tr = ed();
        if (!cap) { card.innerHTML = ''; return; }

        const blocks = [];
        // Buyback
        if (cap.buyback_authorization_usd) {
            const sub = cap.buyback_qtr_executed_usd
                ? `${tr.capital_buyback_qtr || 'Executed Q'}: ${fmtUSD(cap.buyback_qtr_executed_usd)}`
                : '';
            blocks.push(capretBlock(tr.capital_buyback || 'Buyback Authorized',
                fmtUSD(cap.buyback_authorization_usd), sub));
        }
        // Dividend
        if (cap.dividend_per_share_new || (dividends && dividends.is_paying)) {
            const dps = cap.dividend_per_share_new ?? (dividends && dividends.latest_dps);
            const hike = cap.dividend_hike_pct;
            const sub = hike
                ? `${tr.capital_dividend_per || 'per share/Q'} · ${fmtPct(hike)} hike`
                : (tr.capital_dividend_per || 'per share/Q');
            blocks.push(capretBlock(tr.capital_dividend || 'Dividend',
                dps != null ? `$${Number(dps).toFixed(2)}` : (tr.no_dividend || 'Not paying'),
                sub));
        } else if (dividends && dividends.is_paying === false) {
            blocks.push(capretBlock(tr.capital_dividend || 'Dividend',
                tr.no_dividend || 'Not paying', ''));
        }
        // Total returned
        if (cap.total_returned_qtr_usd) {
            blocks.push(capretBlock(tr.capital_total || 'Returned this Q',
                fmtUSD(cap.total_returned_qtr_usd),
                cap.dividend_qtr_paid_usd
                    ? `Div ${fmtUSD(cap.dividend_qtr_paid_usd)} + Buyback ${fmtUSD(cap.buyback_qtr_executed_usd)}`
                    : ''));
        }
        // Cash position
        if (cap.cash_and_marketable_usd) {
            blocks.push(capretBlock(tr.capital_cash || 'Cash Position',
                fmtUSD(cap.cash_and_marketable_usd), ''));
        }

        // Announcements list
        const announcements = (cap.announcements || []).slice(0, 6);
        const annHTML = announcements.length
            ? `<ul class="ed-capret-announcements">
                  ${announcements.map(a => `<li>${UI.escapeHTML(a)}</li>`).join('')}
               </ul>`
            : '';

        card.innerHTML = blocks.join('') + annHTML;
    }

    // ── CEO quote ────────────────────────────────────────────────────────
    function renderQuote(quote) {
        const section = document.getElementById('ed-quote-section');
        const card    = document.getElementById('ed-quote-card');
        if (!quote || !quote.quote) { section.hidden = true; return; }
        section.hidden = false;
        const speaker = quote.speaker || '';
        const title   = quote.title || '';
        const context = quote.context || '';
        card.innerHTML = `
            <p class="ed-quote-text">${UI.escapeHTML(quote.quote)}</p>
            <span class="ed-quote-attrib">
                — ${UI.escapeHTML(speaker)}${title ? ', ' + UI.escapeHTML(title) : ''}
                ${context ? `<span class="ed-quote-context">${UI.escapeHTML(context)}</span>` : ''}
            </span>`;
    }

    // ── Highlights / Summary ─────────────────────────────────────────────
    function renderHighlights(items) {
        const ul = document.getElementById('ed-highlight-list');
        if (!items || !items.length) { ul.innerHTML = ''; return; }
        ul.innerHTML = items.map(h => {
            const icon = h.icon || 'sparkles';
            return `
                <li class="ed-highlight-item">
                    <i data-lucide="${UI.escapeHTML(icon)}" class="ed-highlight-icon"></i>
                    <div class="ed-highlight-body-wrap">
                        <div class="ed-highlight-title">${UI.escapeHTML(h.title || '')}</div>
                        <div class="ed-highlight-body">${UI.escapeHTML(h.body || '')}</div>
                    </div>
                </li>`;
        }).join('');
    }

    function renderSummary(items) {
        const ul = document.getElementById('ed-summary-list');
        if (!items || !items.length) { ul.innerHTML = ''; return; }
        ul.innerHTML = items.map(s =>
            `<li class="ed-summary-item">${UI.escapeHTML(String(s))}</li>`
        ).join('');
    }

    // ── Detail markdown collapse (lazy load) ─────────────────────────────
    function wireDetailCollapse(reportPath) {
        const det = document.getElementById('ed-detail-collapse');
        const body = document.getElementById('ed-detail-md-body');
        if (!reportPath) { det.hidden = true; return; }

        det.addEventListener('toggle', async () => {
            if (!det.open || _markdownLoaded) return;
            body.innerHTML = `<p class="text-zinc-500 text-sm">Loading…</p>`;
            try {
                const r = await fetch('/' + reportPath);
                if (!r.ok) throw new Error(`HTTP ${r.status}`);
                const md = await r.text();
                body.innerHTML = window.marked
                    ? window.marked.parse(md, { breaks: true })
                    : `<pre>${UI.escapeHTML(md)}</pre>`;
                _markdownLoaded = true;
            } catch (e) {
                body.innerHTML = `<p class="text-red-500 text-sm">Failed: ${UI.escapeHTML(e.message)}</p>`;
            }
        });
    }

    // ── Empty state ──────────────────────────────────────────────────────
    function renderEmptyState(ticker) {
        document.getElementById('ed-loading').hidden = true;
        document.getElementById('ed-content').hidden = true;
        document.getElementById('ed-empty-state').hidden = false;
        const tr = ed();
        const tpl = tr.empty_state_btn || 'Re-run 財報 {ticker}';
        document.getElementById('ed-empty-rerun-label').textContent =
            tpl.replace('{ticker}', ticker);

        document.getElementById('ed-empty-rerun-btn').onclick = async () => {
            try {
                const r = await fetch('/api/protocol-queue', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    // Flat shape: server treats all top-level keys (except `name`) as params
                    body: JSON.stringify({ name: 'earnings', ticker })
                });
                if (r.ok) {
                    document.getElementById('ed-empty-msg').textContent =
                        `已加入佇列,5-10 分鐘後重新整理本頁。`;
                } else {
                    const j = await r.json().catch(() => ({}));
                    document.getElementById('ed-empty-msg').textContent =
                        `Failed: ${j.error || r.status}`;
                }
            } catch (e) {
                document.getElementById('ed-empty-msg').textContent = `Failed: ${e.message}`;
            }
        };
    }

    // ── Render all sections ──────────────────────────────────────────────
    function renderAll(payload) {
        renderHero(payload);
        const inf = payload.infographic || {};
        renderMetricCards(inf.surprise);
        renderTrendCharts(payload);
        renderSegments(inf.segments_q);
        renderGeographic(inf.geographic_q);
        renderCapitalReturn(inf.capital_returns, inf.dividends);
        renderQuote(inf.ceo_quote);
        renderHighlights(inf.key_highlights);
        renderSummary(inf.summary);
        wireDetailCollapse((payload.cache || {}).report_path);

        if (window.lucide) lucide.createIcons();
    }

    // ── V2.7.15 — Trend infographic charts (Chart.js) ────────────────────
    const _charts = {}; // id → Chart instance, destroyed on re-render

    function chartTheme() {
        const isDark = document.documentElement.getAttribute('data-theme') !== 'light';
        return {
            text:  isDark ? 'rgba(228,228,231,0.85)' : 'rgba(39,39,42,0.85)',
            grid:  isDark ? 'rgba(82,82,91,0.25)'   : 'rgba(228,228,231,0.6)',
            axis:  isDark ? 'rgba(161,161,170,0.7)' : 'rgba(82,82,91,0.7)',
        };
    }
    function makeChart(id, cfg) {
        if (!window.Chart) return;
        if (_charts[id]) { _charts[id].destroy(); delete _charts[id]; }
        const el = document.getElementById(id);
        if (!el) return;
        try { _charts[id] = new Chart(el, cfg); } catch (e) {
            console.error('[chart]', id, e);
        }
    }
    function fmtBn(v) { return v == null ? '' : (v / 1e9).toFixed(1) + 'B'; }
    function quartersToLabels(arr) {
        // arr is most-recent-first; chart wants oldest-first → reverse, slice(-5)
        // Use calendar month-year (e.g. "Mar '26") instead of fiscal Q (which
        // confuses users when ticker FY ≠ calendar year — TEAM/AAPL fiscal
        // labels would imply future periods that haven't actually occurred yet).
        const MONTHS = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
        const ordered = [...arr].reverse().slice(-5);
        return ordered.map(q => {
            const date = q.date || '';
            if (date.length >= 7) {
                const yr = date.slice(2, 4);
                const mo = parseInt(date.slice(5, 7), 10);
                if (!isNaN(mo) && mo >= 1 && mo <= 12) return `${MONTHS[mo - 1]} '${yr}`;
            }
            const fy = q.fiscalYear ? String(q.fiscalYear).slice(-2) : '';
            const p  = q.period || '';
            return p && fy ? `${p}${fy}` : date.slice(0, 7);
        });
    }
    function quartersValues(arr, getter) {
        const ordered = [...arr].reverse().slice(-5);
        return ordered.map(q => {
            try { const v = getter(q); return (v == null || isNaN(v)) ? null : v; }
            catch { return null; }
        });
    }

    // V2.8.0 — set inline summary text below each chart canvas (always visible
    // replacement for disabled Chart.js native tooltip). Color-codes positive
    // values green / negative red for at-a-glance scan.
    function _setChartSummary(id, html) {
        const el = document.getElementById('ed-chart-summary-' + id);
        if (el) el.innerHTML = html;
    }
    function _summaryItem(label, value, color) {
        const safeLabel = String(label).replace(/[<>"&]/g, c => ({'<':'&lt;','>':'&gt;','"':'&quot;','&':'&amp;'}[c]));
        const safeValue = String(value).replace(/[<>"&]/g, c => ({'<':'&lt;','>':'&gt;','"':'&quot;','&':'&amp;'}[c]));
        const styled = color
            ? `<span style="color:${color};font-weight:700">${safeValue}</span>`
            : `<strong>${safeValue}</strong>`;
        return `<span class="ed-chart-summary-item"><span class="ed-chart-summary-label">${safeLabel}</span> ${styled}</span>`;
    }

    function renderTrendCharts(payload) {
        const c = payload.cache || {};
        const inf = payload.infographic || {};
        const t = chartTheme();
        const tr = ed();
        const L = {
            revenue:    tr.legend_revenue    || 'Revenue',
            net_income: tr.legend_net_income || 'Net Income',
            eps:        tr.legend_eps        || 'EPS',
            ocf:        tr.legend_ocf        || 'OCF',
            fcf:        tr.legend_fcf        || 'FCF',
            gm:         tr.legend_gm         || 'GM',
            om:         tr.legend_om         || 'OM',
            yoy:        tr.legend_yoy        || 'YoY %',
        };
        const baseOpts = (extra = {}) => ({
            responsive: true,
            maintainAspectRatio: false,
            interaction: { mode: 'index', intersect: false },
            plugins: {
                legend: {
                    position: 'top', align: 'end',
                    labels: { color: t.text, boxWidth: 10, padding: 8, font: { size: 11 } },
                },
                // V2.8.0 — Chart.js native tooltip disabled (was overlapping
                // sector-style signal-tip on card hover). Per-bar values are
                // surfaced via always-visible .ed-chart-summary inline below.
                tooltip: { enabled: false },
            },
            scales: {
                x: {
                    ticks: { color: t.axis, font: { size: 10 } },
                    grid:  { color: t.grid, drawBorder: false },
                },
                y: {
                    ticks: { color: t.axis, font: { size: 10 } },
                    grid:  { color: t.grid, drawBorder: false },
                },
            },
            ...extra,
        });

        // 1) Revenue + Net Income bars
        const qpnl = c.quarterly_pnl || [];
        if (qpnl.length) {
            const lbls = quartersToLabels(qpnl);
            makeChart('ed-chart-revni', {
                type: 'bar',
                data: {
                    labels: lbls,
                    datasets: [
                        { label: L.revenue, data: quartersValues(qpnl, q => q.revenue),
                          backgroundColor: 'rgba(59,130,246,0.7)', borderColor: 'rgba(59,130,246,1)', borderWidth: 1 },
                        { label: L.net_income, data: quartersValues(qpnl, q => q.netIncome),
                          backgroundColor: 'rgba(251,191,36,0.75)', borderColor: 'rgba(251,191,36,1)', borderWidth: 1 },
                    ],
                },
                options: baseOpts({
                    scales: {
                        x: { ticks: { color: t.axis, font: { size: 10 } }, grid: { color: t.grid } },
                        y: {
                            ticks: { color: t.axis, font: { size: 10 },
                                     callback: v => fmtBn(v) },
                            grid: { color: t.grid },
                        },
                    },
                }),
            });
            // Summary: latest Q + YoY revenue
            const latest = qpnl[0] || {};
            const yoyQ = qpnl[4] || {};
            const yoyRev = (latest.revenue && yoyQ.revenue)
                ? ((latest.revenue / yoyQ.revenue - 1) * 100).toFixed(1) : null;
            const yoyColor = yoyRev != null
                ? (parseFloat(yoyRev) >= 0 ? 'rgb(34,197,94)' : 'rgb(239,68,68)') : null;
            _setChartSummary('revni', [
                _summaryItem(L.revenue, fmtBn(latest.revenue)),
                _summaryItem(L.net_income, fmtBn(latest.netIncome)),
                yoyRev != null ? _summaryItem(L.yoy + ' Rev', (parseFloat(yoyRev) >= 0 ? '+' : '') + yoyRev + '%', yoyColor) : '',
            ].filter(Boolean).join(' · '));
        }

        // 2) EPS line
        if (qpnl.length) {
            makeChart('ed-chart-eps', {
                type: 'line',
                data: {
                    labels: quartersToLabels(qpnl),
                    datasets: [{
                        label: L.eps,
                        data: quartersValues(qpnl, q => q.eps),
                        borderColor: 'rgba(125,211,252,1)',
                        backgroundColor: 'rgba(125,211,252,0.18)',
                        pointBackgroundColor: 'rgba(125,211,252,1)',
                        tension: 0.25, fill: true,
                    }],
                },
                options: baseOpts({
                    scales: {
                        x: { ticks: { color: t.axis, font: { size: 10 } }, grid: { color: t.grid } },
                        y: {
                            ticks: { color: t.axis, font: { size: 10 },
                                     callback: v => '$' + Number(v).toFixed(2) },
                            grid: { color: t.grid },
                        },
                    },
                }),
            });
            // Summary: latest EPS + 5Q range + YoY
            const eps5 = quartersValues(qpnl, q => q.eps).filter(v => v != null);
            const latest = qpnl[0] || {};
            const yoyQ = qpnl[4] || {};
            const yoyEps = (latest.eps && yoyQ.eps)
                ? ((latest.eps / yoyQ.eps - 1) * 100).toFixed(1) : null;
            const yoyColor = yoyEps != null
                ? (parseFloat(yoyEps) >= 0 ? 'rgb(34,197,94)' : 'rgb(239,68,68)') : null;
            const range = eps5.length ? `$${Math.min(...eps5).toFixed(2)}–$${Math.max(...eps5).toFixed(2)}` : '—';
            _setChartSummary('eps', [
                _summaryItem('Latest', latest.eps != null ? `$${Number(latest.eps).toFixed(2)}` : '—'),
                _summaryItem('5Q', range),
                yoyEps != null ? _summaryItem(L.yoy, (parseFloat(yoyEps) >= 0 ? '+' : '') + yoyEps + '%', yoyColor) : '',
            ].filter(Boolean).join(' · '));
        }

        // 3) OCF + FCF bars
        const cf = c.cash_flow || [];
        if (cf.length) {
            makeChart('ed-chart-cashflow', {
                type: 'bar',
                data: {
                    labels: quartersToLabels(cf),
                    datasets: [
                        { label: L.ocf, data: quartersValues(cf, q => q.operatingCashFlow),
                          backgroundColor: 'rgba(251,191,36,0.75)', borderColor: 'rgba(251,191,36,1)', borderWidth: 1 },
                        { label: L.fcf, data: quartersValues(cf, q => q.freeCashFlow),
                          backgroundColor: 'rgba(56,189,248,0.75)', borderColor: 'rgba(56,189,248,1)', borderWidth: 1 },
                    ],
                },
                options: baseOpts({
                    scales: {
                        x: { ticks: { color: t.axis, font: { size: 10 } }, grid: { color: t.grid } },
                        y: {
                            ticks: { color: t.axis, font: { size: 10 },
                                     callback: v => fmtBn(v) },
                            grid: { color: t.grid },
                        },
                    },
                }),
            });
            // Summary: latest OCF + FCF + FCF margin
            const latest = cf[0] || {};
            const latestRev = (qpnl[0] || {}).revenue;
            const fcfMargin = (latest.freeCashFlow && latestRev)
                ? ((latest.freeCashFlow / latestRev) * 100).toFixed(1) : null;
            _setChartSummary('cashflow', [
                _summaryItem(L.ocf, fmtBn(latest.operatingCashFlow)),
                _summaryItem(L.fcf, fmtBn(latest.freeCashFlow)),
                fcfMargin != null ? _summaryItem('FCF margin', fcfMargin + '%') : '',
            ].filter(Boolean).join(' · '));
        }

        // 4) Gross + Operating Margin lines
        const margins = c.margins_8q || [];
        if (margins.length) {
            const ordered = [...margins].reverse().slice(-5);
            const MONTHS = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
            const mlabels = ordered.map(m => {
                const d = m.date || '';
                if (d.length >= 7) {
                    const yr = d.slice(2, 4);
                    const mo = parseInt(d.slice(5, 7), 10);
                    if (!isNaN(mo) && mo >= 1 && mo <= 12) return `${MONTHS[mo - 1]} '${yr}`;
                }
                return d.slice(0, 7);
            });
            makeChart('ed-chart-margins', {
                type: 'line',
                data: {
                    labels: mlabels,
                    datasets: [
                        { label: L.gm, data: ordered.map(m => m.gross != null ? +(m.gross * 100).toFixed(2) : null),
                          borderColor: 'rgba(251,191,36,1)', backgroundColor: 'rgba(251,191,36,0.15)',
                          pointBackgroundColor: 'rgba(251,191,36,1)', tension: 0.25 },
                        { label: L.om, data: ordered.map(m => m.operating != null ? +(m.operating * 100).toFixed(2) : null),
                          borderColor: 'rgba(56,189,248,1)', backgroundColor: 'rgba(56,189,248,0.15)',
                          pointBackgroundColor: 'rgba(56,189,248,1)', tension: 0.25 },
                    ],
                },
                options: baseOpts({
                    scales: {
                        x: { ticks: { color: t.axis, font: { size: 10 } }, grid: { color: t.grid } },
                        y: {
                            ticks: { color: t.axis, font: { size: 10 },
                                     callback: v => v + '%' },
                            grid: { color: t.grid },
                        },
                    },
                }),
            });
            // Summary: latest GM + OM + delta from prior Q
            const latest = margins[0] || {};
            const prior  = margins[1] || {};
            const gmDelta = (latest.gross != null && prior.gross != null)
                ? (((latest.gross - prior.gross) * 100).toFixed(1)) : null;
            const omDelta = (latest.operating != null && prior.operating != null)
                ? (((latest.operating - prior.operating) * 100).toFixed(1)) : null;
            _setChartSummary('margins', [
                _summaryItem(L.gm, latest.gross != null ? (latest.gross * 100).toFixed(1) + '%' : '—'),
                _summaryItem(L.om, latest.operating != null ? (latest.operating * 100).toFixed(1) + '%' : '—'),
                gmDelta != null ? _summaryItem('GM Δ', (parseFloat(gmDelta) >= 0 ? '+' : '') + gmDelta + 'pp',
                    parseFloat(gmDelta) >= 0 ? 'rgb(34,197,94)' : 'rgb(239,68,68)') : '',
            ].filter(Boolean).join(' · '));
        }

        // 5) Segment YoY Growth horizontal bars
        const segItems = ((inf.segments_q || {}).items || [])
            .filter(it => it.yoy_pct != null)
            .slice(0, 8);
        if (segItems.length) {
            makeChart('ed-chart-seggrowth', {
                type: 'bar',
                data: {
                    labels: segItems.map(it => it.name || '?'),
                    datasets: [{
                        label: L.yoy,
                        data: segItems.map(it => +(it.yoy_pct * 100).toFixed(1)),
                        backgroundColor: segItems.map(it => it.yoy_pct >= 0
                            ? 'rgba(34,197,94,0.7)' : 'rgba(239,68,68,0.7)'),
                    }],
                },
                options: baseOpts({
                    indexAxis: 'y',
                    plugins: {
                        legend: { display: false },
                        tooltip: { enabled: false },
                    },
                    scales: {
                        x: {
                            ticks: { color: t.axis, font: { size: 10 }, callback: v => v + '%' },
                            grid: { color: t.grid },
                        },
                        y: { ticks: { color: t.text, font: { size: 11 } }, grid: { display: false } },
                    },
                }),
            });
            // Summary: list each segment with YoY%
            _setChartSummary('seggrowth', segItems.slice(0, 6).map(it => {
                const v = (it.yoy_pct * 100).toFixed(1);
                const sign = parseFloat(v) >= 0 ? '+' : '';
                const color = parseFloat(v) >= 0 ? 'rgb(34,197,94)' : 'rgb(239,68,68)';
                return _summaryItem(it.name || '?', sign + v + '%', color);
            }).join(' · '));
        } else {
            const card = document.querySelector('#ed-chart-seggrowth')?.closest('.ed-chart-card');
            if (card) card.style.display = 'none';
        }

        // 6) Geography YoY Growth horizontal bars (FY fallback when yoy_pct null)
        const geoItems = ((inf.geographic_q || {}).items || [])
            .filter(it => it.yoy_pct != null)
            .slice(0, 8);
        const geoCard = document.getElementById('ed-chart-card-geogrowth');
        if (geoItems.length) {
            if (geoCard) geoCard.style.display = '';
            makeChart('ed-chart-geogrowth', {
                type: 'bar',
                data: {
                    labels: geoItems.map(it => it.region || '?'),
                    datasets: [{
                        label: L.yoy,
                        data: geoItems.map(it => +(it.yoy_pct * 100).toFixed(1)),
                        backgroundColor: geoItems.map(it => it.yoy_pct >= 0
                            ? 'rgba(34,197,94,0.7)' : 'rgba(239,68,68,0.7)'),
                    }],
                },
                options: baseOpts({
                    indexAxis: 'y',
                    plugins: {
                        legend: { display: false },
                        tooltip: { enabled: false },
                    },
                    scales: {
                        x: {
                            ticks: { color: t.axis, font: { size: 10 }, callback: v => v + '%' },
                            grid: { color: t.grid },
                        },
                        y: { ticks: { color: t.text, font: { size: 11 } }, grid: { display: false } },
                    },
                }),
            });
            // Summary: list each region with YoY%
            _setChartSummary('geogrowth', geoItems.slice(0, 6).map(it => {
                const v = (it.yoy_pct * 100).toFixed(1);
                const sign = parseFloat(v) >= 0 ? '+' : '';
                const color = parseFloat(v) >= 0 ? 'rgb(34,197,94)' : 'rgb(239,68,68)';
                return _summaryItem(it.region || '?', sign + v + '%', color);
            }).join(' · '));
        } else if (geoCard) {
            geoCard.style.display = 'none';
        }
    }

    // ── Boot ─────────────────────────────────────────────────────────────
    UI.boot('earnings', { translate: applyTranslations });

    const ticker = getTicker();
    if (!ticker) {
        document.getElementById('ed-loading').hidden = true;
        document.getElementById('ed-empty-state').hidden = false;
        document.getElementById('ed-empty-msg').textContent =
            'URL missing ?ticker=X parameter';
        return;
    }

    document.getElementById('ed-title-ticker').textContent = ticker;

    fetch(`/api/earnings-infographic/${encodeURIComponent(ticker)}`)
        .then(async r => {
            if (r.status === 404) { renderEmptyState(ticker); return null; }
            if (!r.ok) throw new Error(`HTTP ${r.status}`);
            return r.json();
        })
        .then(payload => {
            if (!payload) return;
            _payload = payload;
            document.getElementById('ed-loading').hidden = true;
            document.getElementById('ed-content').hidden = false;
            renderAll(payload);
            applyTranslations();   // ensure static labels reflect current lang
        })
        .catch(err => {
            document.getElementById('ed-loading').hidden = true;
            document.getElementById('ed-empty-state').hidden = false;
            const tr = ed();
            document.getElementById('ed-empty-msg').textContent =
                `${tr.load_error || 'Load failed'}: ${err.message}`;
        });
})();
