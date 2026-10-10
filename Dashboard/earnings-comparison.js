/* Earnings comparison: server-calculated outcomes, read-only presentation. */
(function (root) {
    'use strict';
    const esc = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
    const finite = v => typeof v === 'number' && Number.isFinite(v);
    const STATES = ['exceeded', 'met', 'missed', 'pending', 'unverifiable'];
    const metrics = {revenue:['營收','Revenue'], eps_diluted:['稀釋 EPS','Diluted EPS'], gross_margin:['毛利率','Gross margin'], operating_margin:['營業利益率','Operating margin'], free_cash_flow:['自由現金流','Free cash flow']};
    function period(p, zh) { return p ? `FY${p.fiscal_year} ${p.period === 'FY' ? (zh ? '全年' : 'Full year') : p.period}` : (zh ? '期間未註明' : 'Period unspecified'); }
    function value(actual) {
        if (!actual || !finite(actual.value)) return '—';
        const n = actual.value;
        if (actual.unit === 'ratio') return `${(n * 100).toFixed(1)}%`;
        if (actual.unit === 'percentage_points') return `${n.toFixed(1)} pp`;
        const symbol = actual.currency === 'USD' ? '$' : actual.currency ? actual.currency + ' ' : '';
        const abs = Math.abs(n);
        const scale = actual.unit === 'currency_per_share' ? 1 : abs >= 1e12 ? 1e12 : abs >= 1e9 ? 1e9 : abs >= 1e6 ? 1e6 : abs >= 1e3 ? 1e3 : 1;
        return symbol + (n / scale).toLocaleString('en-US', {minimumFractionDigits:2,maximumFractionDigits:2}) + ({1e12:'T',1e9:'B',1e6:'M',1e3:'K'}[scale] || '');
    }
    function change(row, key, zh) {
        const delta = row[key] || {};
        if (!finite(delta.delta)) return {text: zh ? '無可比資料' : 'Not comparable', cls:'neutral'};
        const n = row.unit === 'ratio' ? delta.delta * 100 : finite(delta.pct) ? delta.pct * 100 : delta.delta;
        const unit = row.unit === 'ratio' ? ' pp' : finite(delta.pct) ? '%' : '';
        const display = unit ? Math.abs(n).toFixed(1) + unit : value({...row.current, value:Math.abs(n)});
        return {text:`${n > 0 ? '+' : n < 0 ? '−' : ''}${display}`, cls:n > 0 ? 'positive' : n < 0 ? 'negative' : 'neutral'};
    }
    function safeLink(url, label) {
        if (typeof url !== 'string' || !/^https?:\/\//i.test(url)) return '';
        try { const u = new URL(url); if (u.username || u.password) return ''; } catch (_) { return ''; }
        return `<a href="${esc(url)}" target="_blank" rel="noopener noreferrer">${esc(label)} ↗</a>`;
    }
    function renderHTML(payload, lang='zh') {
        const zh = lang !== 'en', t = (a,b) => zh ? a : b;
        const c = payload.comparison;
        if (!c) return `<div class="ec-notice" role="status">${t('比較資料尚未載入，請重新整理頁面。','Comparison data is unavailable. Please refresh.')}</div>`;
        const view = payload.view || {}, prev = c.previous_analysis || {}, ctx = c.context || {};
        const name = m => metrics[m]?.[zh ? 0 : 1] || m || t('觀察項目','Observation');
        const statusName = {exceeded:t('超標','Exceeded'),met:t('達標','Met'),missed:t('未達標','Missed'),pending:t('尚未到期','Not due yet'),unverifiable:t('待補證據','Needs evidence')};
        const reason = r => ({
            target_not_reported:t('目標期間尚未公布，繼續追蹤。','The target period has not reported yet.'),
            legacy_no_verifiable_contract:t('上次紀錄未完整保存目標與計算口徑，暫不判定達標。','The previous note did not preserve a complete target and measurement basis.'),
            target_period_unknown:t('上次未註明明確的目標期間。','The target period was not specified.'),
            qualitative_no_numeric_criterion:t('這是定性展望，沒有可核對的數值門檻。','This qualitative outlook has no numeric threshold.'),
            actual_unavailable:t('本次缺少這個指標的實際值。','The actual value for this metric is unavailable.'),
            basis_mismatch:t('實際值與目標的幣別或計算口徑不同。','The actual and target use different currencies or measurement bases.'),
            conflicting_actuals:t('來源數值不一致，需要再核對。','Sources disagree on the actual value.'),
            release_date_unavailable:t('尚未確認對應的財報公布日期。','The matching earnings release date is unconfirmed.'),
            not_recorded_before_release:t('無法確認這筆預期在財報公布前已記錄。','This expectation was not confirmed as recorded before the release.'),
            same_period_same_basis:t('已核對相同期間與計算口徑。','Verified against the same period and measurement basis.'),
        }[r] || t('資料仍待確認，暫不判定達標。','More evidence is required before scoring.'));
        const target = e => {
            if (e.operator === 'range' && finite(e.low) && finite(e.high)) return `${value({...e,value:e.low})} – ${value({...e,value:e.high})}`;
            if (['gte','lte'].includes(e.operator) && finite(e.threshold)) return `${e.operator === 'gte' ? '≥' : '≤'} ${value({...e,value:e.threshold})}`;
            return t('文字展望','Qualitative outlook');
        };
        const origins = {management:t('公司指引','Management'),consensus:t('市場共識','Consensus'),analysis:t('分析預期','Analyst view'),legacy:t('上次紀錄','Previous note')};
        const proof = e => `<details class="ed-detail-collapse ec-proof"><summary>${t('展開原文與依據','Original note & evidence')}</summary><div class="ec-proof-body"><p>${esc(e.source_quote || e.statement || '')}</p><div class="ec-proof-meta">${e.published_at ? `${t('公布','Published')} ${esc(e.published_at)} · ` : ''}${e.recorded_at ? `${t('記錄','Recorded')} ${esc(String(e.recorded_at).slice(0,10))}` : ''}</div>${safeLink(e.source_ref,t('原始來源','Source'))}</div></details>`;
        const heading = (icon, title, hint = '') => `<div class="ed-section-head ec-section-heading"><i data-lucide="${icon}" aria-hidden="true"></i><h3>${title}</h3>${hint ? `<span class="ed-charts-hint">${hint}</span>` : ''}</div>`;
        const audit = c.expectation_audit || [];
        const counts = Object.fromEntries(STATES.map(s => [s,audit.filter(r => r.status === s).length]));
        const scored = counts.exceeded + counts.met + counts.missed;
        const priorRevision = /\/history\/[^/]+\/[^/]+\/([a-f0-9]{64})\.json$/.exec(prev.source_ref || '')?.[1];
        const priorHref = prev.status === 'available' ? `earnings-detail.html?ticker=${encodeURIComponent(payload.ticker)}&period=${encodeURIComponent(prev.period_end)}${priorRevision ? '&revision=' + priorRevision : ''}` : '';
        const toolbar = `
            <div class="ec-toolbar">
                <p>${prev.status === 'available' ? `${t('分析紀錄','Analysis records')} · ${esc(period(prev.fiscal_period,zh))} → ${esc(period(ctx.fiscal_period,zh))}${prev.quarters_apart > 1 ? ` · ${t('相隔','Gap of')} ${prev.quarters_apart} ${t('季','quarters')}` : ''}` : t('首次分析紀錄 · 財務數字仍可跨季比較','First analysis on record · Financial history is still comparable')}</p>
                <label class="ec-period-label" for="ec-period">${t('檢視季度','Viewing period')}
                    <select id="ec-period">${(view.periods || []).map(p => `<option value="${esc(p.period_end)}" ${p.period_end === view.selected_period ? 'selected' : ''}>${esc(period(p.fiscal_period,zh))}${p.period_end === view.latest_period ? t(' · 最新',' · Latest') : ''}</option>`).join('')}</select>
                </label>
            </div>`;
        const dates = `<div class="ec-dates"><span>${t('會計期末','Period ended')} <b>${esc(ctx.fiscal_period_end || '—')}</b></span><span>${t('財報公布','Released')} <b>${esc(ctx.earnings_release_date || t('尚未確認','Unconfirmed'))}</b></span>${priorHref ? `<a class="ed-back-btn" href="${priorHref}"><i data-lucide="arrow-left" aria-hidden="true"></i>${t('查看上次財報','Previous report')}</a>` : ''}</div>`;
        const financialRows = (c.financial_changes || []).map(r => {
            const q=change(r,'qoq',zh), y=change(r,'yoy',zh);
            return `<tr><th scope="row">${esc(name(r.metric))}</th>
                <td class="ec-current">${esc(value(r.current))}</td><td>${esc(value(r.previous_quarter))}</td>
                <td><span class="ec-delta ec-${q.cls}">${esc(q.text)}</span></td>
                <td>${esc(value(r.year_ago))}</td><td><span class="ec-delta ec-${y.cls}">${esc(y.text)}</span></td></tr>`;
        }).join('');
        const unitNote = (c.financial_changes || []).some(r=>r.current && r.unit !== 'ratio' && !r.current.currency)
            ? t('B＝十億，M＝百萬，pp＝百分點。舊資料未標記幣別，金額沿用原始財報單位。','B = billion, M = million, pp = percentage points. Older amounts retain source units without a currency label.')
            : t('B＝十億，M＝百萬；利潤率增減以百分點（pp）呈現。','B = billion, M = million; margin changes use percentage points (pp).');
        const financialTable = `<section class="ed-section ed-charts-section" id="ec-financials">
            ${heading('columns-2',t('本季數字 vs 歷季','Quarter comparison'),t('本季 / 上季 / 去年同期','Current / previous / year ago'))}
            <div class="ed-chart-card ec-surface">${toolbar}${dates}
            <div class="ec-table-scroll" tabindex="0" role="region" aria-label="${t('跨季財務比較','Quarterly financial comparison')}">
                <table><thead><tr>${[t('指標','Metric'),period(ctx.fiscal_period,zh),t('上季','Previous quarter'),t('季增減','QoQ'),t('去年同期','Year ago'),t('年增減','YoY')].map((v,i)=>`<th scope="col"${i===1 ? ' class="ec-current"' : ''}>${esc(v)}</th>`).join('')}</tr></thead><tbody>${financialRows}</tbody></table>
            </div><p class="ec-footnote">${unitNote}<span class="ec-scroll-hint">${t('左右滑動查看完整比較','Scroll horizontally for all periods')}</span></p></div></section>`;
        const excerpt = text => text.length > 130 ? text.slice(0,130) + '…' : text;
        const auditRows = audit.map(row => {
            const e=row.expectation || {}, state=STATES.includes(row.status) ? row.status : 'unverifiable';
            return `<article class="ec-audit-row">
                <div class="ec-audit-top"><span class="ec-tag">${esc(origins[e.origin] || origins.analysis)} · ${esc(period(e.target_period,zh))}</span><span class="ec-badge ec-${state}">${statusName[state]}</span></div>
                <h4>${esc(excerpt(e.statement || name(e.metric)))}</h4>
                <div class="ec-audit-values"><div><span>${t('上次預期','Previous expectation')}</span><strong>${esc(target(e))}</strong></div><span class="ec-arrow" aria-hidden="true">→</span><div><span>${t('本次實際','Reported actual')}</span><strong>${row.actual ? esc(value(row.actual)) : state === 'pending' ? t('等待公布','Awaiting release') : t('尚無可比數值','Not yet comparable')}</strong></div></div>
                <p class="ec-reason">${esc(reason(row.reason))}</p>${proof(e)}
            </article>`;
        }).join('');
        const emptyAudit = `<div class="ec-empty"><span aria-hidden="true">—</span><h4>${prev.status !== 'available' ? t('這是第一筆分析','Tracking starts here') : t('上次未留下可核對的預期','No expectations on record')}</h4><p>${t('本季數字將成為下一次的比較基準。','This quarter establishes the baseline for the next review.')}</p></div>`;
        const badges = STATES.filter(s=>counts[s]).map(s=>`<span class="ec-badge ec-${s}">${statusName[s]} <b>${counts[s]}</b></span>`).join('');
        const flagNames = {cash_conversion_wc_driven:t('營運資金影響現金轉換','Working capital affects cash conversion'),dso_slowdown:t('收款天數拉長','Receivables collection slowing'),gross_margin_compression:t('毛利率下滑','Gross margin compression'),accruals_warning:t('應計品質警訊','Accruals warning'),negative_fcf:t('自由現金流為負','Negative free cash flow'),capex_outpaces_ocf:t('資本支出高於營業現金流','Capex exceeds operating cash flow')};
        const flags = c.quality_flag_changes || {};
        const flagRows = flags.available ? [['new',t('新增','New'),'missed'],['continuing',t('持續','Continuing'),'pending'],['resolved',t('解除','Resolved'),'met'],['definition_changed',t('定義調整','Definition changed'),'unverifiable']].flatMap(([key,label,state])=>(flags[key] || []).map(f=>`<li><span>${esc(flagNames[f] || f.replaceAll('_',' '))}</span><span class="ec-badge ec-${state}">${label}</span></li>`)).join('') : '';
        const watch = (c.next_watchlist || []).map(w=>`<li><span>${esc(name(w.metric))}</span><strong>${esc(value(w.baseline))}</strong></li>`).join('');
        const watchAudit = (c.watch_audit || []).map(r=>`<li><span>${esc(name(r.watch?.metric))}</span><strong>${esc(value(r.watch?.baseline))} → ${esc(value(r.actual))}</strong><span>${esc(({up:t('上升','Up'),down:t('下降','Down'),flat:t('持平','Flat'),unavailable:t('待補資料','Unavailable')})[r.direction] || '')}</span></li>`).join('');
        const nextTargets = (c.next_expectations || []).map(e=>`<article class="ec-next-target"><span class="ec-tag">${esc(origins[e.origin] || origins.analysis)} · ${esc(period(e.target_period,zh))}</span><h4>${esc(excerpt(e.statement || name(e.metric)))}</h4><strong>${esc(target(e))}</strong>${proof(e)}</article>`).join('');
        return `
            ${view.selected_period !== view.latest_period || view.revision ? `<div class="ec-notice">${view.revision ? t('正在查看當時保存的分析紀錄。','Viewing the originally saved analysis.') : t('正在查看歷史季度。','Viewing a historical quarter.')} <a href="earnings-detail.html?ticker=${encodeURIComponent(payload.ticker)}&tab=compare">${t('回到最新一季','Back to latest')} →</a></div>` : ''}
            ${view.narrative_available === false ? `<div class="ec-notice">${t('本季已有財務數字，分析摘要尚未完成。','Financials are available; the analysis narrative is not yet complete.')}</div>` : ''}
            ${view.warnings?.length ? `<div class="ec-notice">${t('部分歷史紀錄無法讀取，目前顯示可核對的資料。','Some historical records could not be loaded. Showing verifiable data.')}</div>` : ''}
            ${financialTable}
            <div class="ec-review-grid">
                <section class="ed-section ed-charts-section" id="ec-audit">
                    ${heading('list-checks',t('上次預期 · 本次驗收','Previous outlook · Results'),audit.length ? `${t('可核對','Verifiable')} ${scored} / ${audit.length}` : '')}
                    <div class="ed-chart-card ec-surface">
                    ${audit.length ? `<div class="ec-audit-summary">${badges}</div>${prev.legacy ? `<p class="ec-audit-note">${t('保留上次原文；未到期與缺證據項目不計入達標評分。','Original notes are preserved. Pending and unverifiable items are not scored.')}</p>` : ''}<div class="ec-audit-list">${auditRows}</div>` : emptyAudit}
                    ${watchAudit ? `<details class="ed-detail-collapse ec-observations"><summary>${t('上次觀察項目的變化','Previous observation changes')}</summary><ul class="ec-watch-list">${watchAudit}</ul></details>` : ''}
                    </div>
                </section>
                <aside class="ec-review-aside">
                    <section class="ed-section ed-charts-section" id="ec-next">${heading('scan-eye',t('下季追蹤','Next quarter'),esc(period(c.next_watchlist?.[0]?.target_period,zh)))}
                        <div class="ed-chart-card ec-surface ec-next-body">
                        ${nextTargets}<div class="ec-watch-head"><span>${t('觀察指標','Watchlist')}</span><span>${t('本季基準','Current baseline')}</span></div>
                        <ul class="ec-watch-list">${watch}</ul><p class="ec-footnote">${t('觀察基準，不是公司承諾，不計入達標率。','Observation baselines, not company commitments or scored predictions.')}</p></div>
                    </section>
                    ${flagRows ? `<section class="ed-section ed-charts-section">${heading('shield-alert',t('財務品質變化','Quality changes'))}<div class="ed-chart-card ec-surface"><ul class="ec-quality-list">${flagRows}</ul>${flags.definition_changed?.length ? `<p class="ec-footnote">${t('定義調整的項目仍待核對，未列為解除。','Changed definitions need review and are not treated as resolved.')}</p>` : ''}</div></section>` : ''}
                </aside>
            </div>`;
    }
    function render(container, payload, lang) {
        if (!container) return;
        // Preserve expanded evidence and history tables when switching language/theme.
        const opened = [...container.querySelectorAll('details')].map(el=>el.open);
        container.innerHTML = renderHTML(payload,lang);
        container.querySelectorAll('details').forEach((el,i)=>{ el.open=!!opened[i]; });
        const select=container.querySelector('#ec-period');
        if (select) select.addEventListener('change',()=>{
            const url=new URL(root.location.href); url.searchParams.set('period',select.value); url.searchParams.delete('revision'); url.searchParams.set('tab','compare');
            root.location.assign(url.href);
        });
    }
    const api={render,renderHTML,value,change};
    root.EarningsComparison=api;
    if (typeof module !== 'undefined') module.exports=api;
})(typeof window !== 'undefined' ? window : globalThis);
