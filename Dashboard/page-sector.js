/**
 * page-sector.js — Sector Intelligence page presenter (ARCH-9)
 * Depends on: utils.js (window.UI, window.logToUI), i18n.js, data-store.js (window.DataStore)
 * Requires Chart.js (loaded via CDN in sector.html)
 */

/* ── Pill hover tooltip ─────────────────────────────────────── */
const PILL_TIPS = {
    regime: {
        zh: { title: '市場機制', desc: '描述大盤資金流向的整體狀態，由廣度、FTD、情緒三訊號綜合判定。影響個股分析的建議曝險上限。', scale: '🟢 RISK_ON / BULL：資金進場，適合持股\n🟡 SIDEWAYS / VOLATILE：震盪觀望\n🔴 RISK_OFF / BEAR：資金撤退，降低倉位' },
        en: { title: 'Market Regime', desc: 'Overall direction of institutional money flow, derived from breadth, FTD, and sentiment signals. Sets the exposure ceiling for individual trades.', scale: '🟢 RISK_ON / BULL: money flowing in, hold positions\n🟡 SIDEWAYS / VOLATILE: wait & watch\n🔴 RISK_OFF / BEAR: money leaving, reduce exposure' },
    },
    breadth: {
        zh: { title: '市場廣度分數', desc: '衡量市場中有多少股票真正在上漲趨勢。避免「大盤漲但多數個股跌」的陷阱，分數 0–100。', scale: '🟢 60–100  Healthy / Strong：多數股票參與\n🟡 40–60   Neutral：觀望，選股需謹慎\n🔴  0–40   Weakening / Critical：只有少數股票在漲，市場很窄' },
        en: { title: 'Market Breadth Score', desc: 'Percentage of stocks in an uptrend. Guards against "index up but most stocks down" traps. Scale 0–100.', scale: '🟢 60–100  Healthy / Strong: broad participation\n🟡 40–60   Neutral: selective, proceed with caution\n🔴  0–40   Weakening / Critical: only a handful leading, narrow rally' },
    },
    ftd: {
        zh: { title: 'FTD 跟進日狀態', desc: 'Follow-Through Day（跟進日），William O\'Neil 確認大盤反彈的信號。反彈第 4 天以上出現大成交量收漲，代表機構資金進場確認。', scale: '🟢 FTD_CONFIRMED：反彈已確認，可增加曝險\n🟡 RALLY_ATTEMPT：反彈觀察中，還沒確認\n🔴 NO_SIGNAL / DISTRIBUTION：無反彈信號或派發中，偏弱' },
        en: { title: 'Follow-Through Day', desc: 'O\'Neil signal confirming a market rally. A big-volume up day on day 4+ of a rally attempt signals institutional buying.', scale: '🟢 FTD_CONFIRMED: rally confirmed, increase exposure\n🟡 RALLY_ATTEMPT: watching, not yet confirmed\n🔴 NO_SIGNAL / DISTRIBUTION: no signal or distribution phase' },
    },
    exposure: {
        zh: { title: '建議曝險上限', desc: '由廣度、FTD、市場頂部三訊號合成的最保守倉位上限。超過這個比例持股，整體組合風險偏高。', scale: '🟢 75–100%：市場強健，可高持股\n🟡 50–74%：謹慎，精選個股\n🔴 <50%：防守模式，降低整體倉位' },
        en: { title: 'Synthesized Exposure Ceiling', desc: 'Most conservative position limit derived from breadth, FTD, and market-top signals. Holding above this level raises portfolio risk.', scale: '🟢 75–100%: strong market, high allocation OK\n🟡 50–74%: cautious, be selective\n🔴 <50%: defensive, reduce overall exposure' },
    },
    fg: {
        zh: { title: '貪婪恐懼指數', desc: 'CNN Fear & Greed Index，0–100 測量市場整體情緒。極度恐懼時往往是買點，極度貪婪時市場容易反轉。', scale: '🟢 45–74  Greed / Neutral：正常市場情緒\n🟡 75–89  Extreme Greed：警戒，估值偏貴\n🔴  0–24  Extreme Fear：恐慌（逆向可能是機會）\n⚠️  >90  Euphoria：高度警戒反轉風險' },
        en: { title: 'Fear & Greed Index', desc: 'CNN 0–100 gauge of overall market sentiment. Extreme fear can signal buying opportunities; extreme greed often precedes corrections.', scale: '🟢 45–74  Greed / Neutral: healthy sentiment\n🟡 75–89  Extreme Greed: caution, valuations stretched\n🔴  0–24  Extreme Fear: panic (contrarian opportunity)\n⚠️  >90  Euphoria: high reversal risk' },
    },
    cycle: {
        zh: { title: '市場週期位置', desc: '大盤所處的多頭週期階段，影響產業輪動方向。不同階段適合的產業類型不同。', scale: '🟢 Early：週期初期，科技/成長股最強\n🟡 Mid：均衡輪動，工業/金融輪強\n🔴 Late：週期末，防禦性/能源輪強，成長股逐漸退場' },
        en: { title: 'Market Cycle Phase', desc: 'Stage of the current bull cycle, driving sector rotation direction.', scale: '🟢 Early: growth & tech outperform\n🟡 Mid: balanced rotation, industrials/financials strengthen\n🔴 Late: defensives & energy lead, growth fades' },
    },
    vix: {
        zh: { title: 'VIX 波動率指數', desc: 'CBOE 恐慌指數，衡量市場對未來 30 天波動的預期。VIX 越高代表市場越不安，個股波動也會放大。', scale: '🟢 <15  低波動：市場平靜，持股舒適\n🟡 15–24 正常：一般市況\n🔴 25–30 警戒：波動升溫，謹慎加倉\n🆘 >30  恐慌：高波動，停損紀律非常重要' },
        en: { title: 'VIX Volatility Index', desc: 'CBOE fear gauge measuring expected 30-day market volatility. Higher VIX means bigger swings and wider stop-losses needed.', scale: '🟢 <15  Low: calm market, comfortable holding\n🟡 15–24 Normal: typical conditions\n🔴 25–30 Elevated: increasing risk, be careful adding\n🆘 >30  Fear: high volatility, strict stops essential' },
    },
};

(function initPillTooltip() {
    const tip = document.getElementById('pill-tooltip');
    if (!tip) return;
    let _hideTimer = null;

    function showTip(el) {
        const key = el.dataset.tipKey;
        const lang = document.documentElement.lang === 'en' ? 'en' : 'zh';
        const data = PILL_TIPS[key]?.[lang];
        if (!data) return;

        // Build content
        const valueEl = el.querySelector('.status-pill-value');
        const valueColor = valueEl?.style.color || 'var(--text-main)';
        const currentVal = valueEl?.textContent || '';
        tip.innerHTML = `
            <div class="tip-title">${data.title} <span style="color:${valueColor};font-size:11px;font-weight:700">${currentVal}</span></div>
            <div class="tip-desc">${data.desc}</div>
            <div class="tip-scale">${data.scale.replace(/\n/g, '<br>')}</div>
        `;

        // Position: invisible first to measure height
        tip.style.opacity = '0';
        tip.style.top = '-9999px';
        tip.classList.add('tip-visible');

        requestAnimationFrame(() => {
            const rect  = el.getBoundingClientRect();
            const tRect = tip.getBoundingClientRect();
            const gap   = 8;
            let top  = rect.top - tRect.height - gap;
            if (top < 8) top = rect.bottom + gap;     // flip below if near top
            let left = rect.left + (rect.width - tRect.width) / 2;
            left = Math.max(8, Math.min(left, window.innerWidth - tRect.width - 8));
            tip.style.top  = top  + 'px';
            tip.style.left = left + 'px';
            tip.style.opacity = '';  // CSS transition takes over
        });
    }

    function hideTip() {
        tip.classList.remove('tip-visible');
    }

    document.addEventListener('mouseover', e => {
        const pill = e.target.closest('[data-tip-key]');
        if (!pill) return;
        if (_hideTimer) { clearTimeout(_hideTimer); _hideTimer = null; }
        showTip(pill);
    });
    document.addEventListener('mouseout', e => {
        const pill = e.target.closest('[data-tip-key]');
        if (!pill) return;
        _hideTimer = setTimeout(hideTip, 80);
    });
})();

/* ── Constants ──────────────────────────────────────────────── */
const VC = {
    HOT:   { hex: '#22c55e', bg: 'rgba(34,197,94,0.10)',  border: 'rgba(34,197,94,0.30)'  },
    WARM:  { hex: '#eab308', bg: 'rgba(234,179,8,0.10)',  border: 'rgba(234,179,8,0.30)'  },
    COLD:  { hex: '#ef4444', bg: 'rgba(239,68,68,0.10)',  border: 'rgba(239,68,68,0.30)'  },
    AVOID: { hex: '#71717a', bg: 'rgba(113,113,122,0.08)', border: 'rgba(113,113,122,0.25)' },
};
const SECTOR_ZH = {
    UTILITIES:'公用事業', BASIC_MATERIALS:'基礎材料', INDUSTRIALS:'工業',
    TECHNOLOGY:'科技', FINANCIAL:'金融', ENERGY:'能源',
    HEALTHCARE:'醫療保健', CONSUMER_CYCLICAL:'非必需消費', COMMUNICATION_SERVICES:'通訊服務',
    CONSUMER_DEFENSIVE:'必需消費', REAL_ESTATE:'房地產',
};

// Map sector page names (data.json .sectors[].name) → momentum page row.sector
// (GICS sector names from sp500_sectors.json). Used when clicking a sector
// card to deep-link into the momentum table with the sector filter pre-applied.
const SECTOR_TO_GICS = {
    'Industrials':            'Industrials',
    'Financials':             'Financials',
    'Utilities':              'Utilities',
    'Consumer_Discretionary': 'Consumer Discretionary',
    'Technology':             'Information Technology',
    'Materials':              'Materials',
    'Healthcare':             'Health Care',
    'Real_Estate':            'Real Estate',
    'Communication':          'Communication Services',
    'Communication_Services': 'Communication Services',
    'Consumer_Staples':       'Consumer Staples',
    'Energy':                 'Energy',
};
const FLAG_LABELS = {
    zh: {
        overbought:                  '超買',
        binary_risk_within_48h:      '⚡ 48h 二元風險',
        energy_stock_oil_divergence: '⚠ 油價背離',
        pharma_tariff_risk:          '💊 藥品關稅',
        rate_headwind:               '📈 利率逆風',
        late_cycle:                  '🔄 晚期週期',
        fat_tail_warning:            '🔻 肥尾警告',
        extreme_sentiment:           '🚨 極端情緒',
    },
    en: {
        overbought:                  'Overbought',
        binary_risk_within_48h:      '⚡ 48h Binary Risk',
        energy_stock_oil_divergence: '⚠ Oil Divergence',
        pharma_tariff_risk:          '💊 Pharma Tariff',
        rate_headwind:               '📈 Rate Headwind',
        late_cycle:                  '🔄 Late Cycle',
        fat_tail_warning:            '🔻 Fat Tail Warning',
        extreme_sentiment:           '🚨 Extreme Sentiment',
    },
};
// Resolve a flag key to a human label. Looks in (1) local FLAG_LABELS, (2)
// i18n warnings.flags (CamelCase keys like `Below_200MA`), (3) i18n
// sector_page.risk_flags (lowercase keys like `consensus_warning`). Strips
// trailing `_MM_DD` date suffix from dynamic keys like `binary_earnings_4_28`
// so one translation entry covers all dates.
function flagLabel(key) {
    if (!key) return '';
    const lang = UI.currentLang;
    const local = (FLAG_LABELS[lang] || FLAG_LABELS.en)[key];
    if (local) return local;

    const i18nRoot = window.i18n?.[lang] || {};
    const warnFlags = i18nRoot.warnings?.flags || {};
    const sectorRiskFlags = i18nRoot.sector_page?.risk_flags || {};
    if (warnFlags[key]) return warnFlags[key];
    if (sectorRiskFlags[key]) return sectorRiskFlags[key];

    // Dynamic earnings date pattern: binary_earnings_4_28 → binary_earnings + " 4/28"
    const m = key.match(/^([a-z_]+?)_(\d{1,2})_(\d{1,2})$/);
    if (m && sectorRiskFlags[m[1]]) return `${sectorRiskFlags[m[1]]} ${m[2]}/${m[3]}`;
    if (m && warnFlags[m[1]]) return `${warnFlags[m[1]]} ${m[2]}/${m[3]}`;

    return key.replace(/_/g, ' ');
}

/* ── Main loader ─────────────────────────────────────────────── */
async function loadSectorData() {
    logToUI('Sector: loading data...');
    try {
        const data = await DataStore.get();
        const lang = UI.currentLang;

        UI.applySyncLight(document.getElementById('last-update'), data.last_updated, null, [
            { label: '產業掃描', ts: data?.market?.generated_at,                          ttl: 720, hint: '執行「產業掃描」' },
            { label: '廣度分析', ts: data?.breadth?.generated_at || data?.breadth?.data_date, ttl: 180, hint: 'daily_update.sh Step 1' },
            { label: 'FTD 偵測', ts: data?.ftd?.generated_at,                             ttl: 180, hint: 'daily_update.sh Step 2' },
            { label: '市場頂部', ts: data?.market_top?.generated_at,                      ttl: 180, hint: 'daily_update.sh Step 3' },
        ]);

        renderStatusStrip(data);
        renderBinaryAlert(data.binary_risks || []);
        // V2.20.0 — populate theme override map for renderThemes ⚡ icon
        window.UI = window.UI || {};
        window.UI._themeOverrides = data.theme_overrides || [];

        renderHandoff(data.market);
        renderSectorMatrix(data.sectors || [], lang);
        renderThreeSignal(data.breadth, data.ftd, data.market_top);
        renderCatalystFeed(data.market);
        renderDivergence(data.divergence_watch || []);
        renderThemes(data.market?.themes || []);

        lucide.createIcons();
        logToUI('Sector: render complete');
    } catch (e) {
        logToUI('Sector ERROR: ' + e.message);
    }
}


/* ── V1.73.4 — Status strip + binary alert + 8 gauge helpers + REDUNDANT_FLAGS_DASH render moved to script.js (dashboard) ── */
function renderStatusStrip(data) { /* no-op: lives on dashboard */ }
function renderBinaryAlert(risks) { /* no-op: lives on dashboard */ }

/* ── Today's Verdict (hero card) — shared component ──────────── */
// Implementation moved to components.js (Components.renderTodayVerdict).
// Keep the legacy `renderHandoff` alias so existing callers still work.
function renderHandoff(market) { Components.renderTodayVerdict(market); }

/* ── Sector Cards ────────────────────────────────────────────── */
function renderSectorMatrix(sectors, lang) {
    const groups = { HOT: [], WARM: [], COLD: [], AVOID: [] };
    sectors.forEach(s => {
        const v = s.verdict || 'COLD';
        if (groups[v]) groups[v].push(s);
    });

    Object.entries(groups).forEach(([verdict, list]) => {
        const groupEl = document.getElementById(`group-${verdict}`);
        const gridEl  = document.getElementById(`grid-${verdict}`);
        const countEl = document.getElementById(`count-${verdict}`);
        if (!groupEl || !gridEl) return;

        if (!list.length) { groupEl.classList.add('hidden'); return; }
        groupEl.classList.remove('hidden');
        countEl.textContent = `${list.length} ${t().sectors_unit || 'sectors'}`;

        list.sort((a, b) => b.score - a.score);
        gridEl.innerHTML = list.map(s => buildSectorCard(s, lang)).join('');

        // Click a sector card → deep-link into momentum page with sector filter pre-applied
        gridEl.querySelectorAll('[data-sector-jump]').forEach(card => {
            card.addEventListener('click', (ev) => {
                // Don't trigger when the user clicks something interactive inside the card
                if (ev.target.closest('button, a, input, select')) return;
                const gics = card.dataset.sectorJump;
                if (gics) window.location.href = `momentum.html?sector=${encodeURIComponent(gics)}`;
            });
        });
    });
}

function buildSectorCard(s, lang) {
    const v      = s.verdict || 'COLD';
    const vc     = VC[v] || VC.COLD;
    const pct    = Math.min(100, s.score || 0);
    const nameZH = SECTOR_ZH[(s.name||'').toUpperCase().replace(/ /g,'_')] || s.name?.replace(/_/g,' ');
    const nameEN = (s.name||'').replace(/_/g,' ');
    const dispName = lang === 'zh' ? nameZH : nameEN;

    const rotIcon  = s.rotation_signal === 'INFLOW' ? '▲' : s.rotation_signal === 'OUTFLOW' ? '▼' : '–';
    const rotColor = s.rotation_signal === 'INFLOW' ? '#22c55e' : s.rotation_signal === 'OUTFLOW' ? '#ef4444' : '#71717a';

    const flags = (s.risk_flags || []).map(f => {
        const lbl = flagLabel(f);
        return `<span class="flag-pill verdict-${v}">${lbl}</span>`;
    }).join('');

    const reasons = (s.key_reasons || (s.key_reason ? [s.key_reason] : [])).slice(0, 2).map(r =>
        `<div class="flex items-start gap-1.5"><span class="text-zinc-500 mt-0.5 shrink-0">▸</span><span class="text-xs leading-snug" style="color:var(--text-muted)">${r}</span></div>`
    ).join('');

    // Score components mini bars
    const sc = s.score_components || {};
    const cT = t();
    const compBars = Object.entries({
        [cT.comp_bm || 'BM']: sc.breadth_momentum,
        [cT.comp_th || 'TH']: sc.theme_heat,
        [cT.comp_nc || 'NC']: sc.news_catalyst,
        [cT.comp_rs || 'RS']: sc.rotation_signal,
    }).map(([k, v_]) => {
        if (v_ == null) return '';
        const w = Math.round((v_ / 25) * 100);
        return `<div class="flex items-center gap-1.5">
            <span class="text-[9px] text-zinc-500 w-5 shrink-0 font-bold">${k}</span>
            <div class="component-bar flex-1 verdict-${s.verdict}" style="height:4px"><div class="component-bar-fill" style="width:${w}%;height:4px"></div></div>
            <span class="text-[9px] font-mono font-bold w-5 text-right" style="color:var(--vc)">${v_}</span>
        </div>`;
    }).filter(Boolean).join('');

    const tr = t();
    const daNote = s.devils_advocate
        ? `<div class="mt-2 pt-2 border-t border-violet-500/20">
            <div class="text-[9px] font-black text-violet-400 mb-1 uppercase tracking-wider">${tr.da_challenge || 'DA Challenge'}</div>
            <p class="text-[10px] text-violet-300/80 leading-snug">${s.devils_advocate}</p>
           </div>`
        : '';

    const uptrendBar = s.uptrend_ratio != null
        ? `<div class="flex items-center gap-1.5 mt-1">
            <span class="text-[10px] text-zinc-500 font-bold shrink-0">${tr.uptrend_label_card || 'Uptrend'}</span>
            <div class="flex-1 h-2 rounded-full" style="background:${vc.border}"><div class="h-2 rounded-full" style="width:${Math.round(s.uptrend_ratio*100)}%;background:${vc.hex}"></div></div>
            <span class="text-[10px] font-mono font-bold shrink-0" style="color:${vc.hex}">${(s.uptrend_ratio*100).toFixed(0)}%</span>
           </div>`
        : '';

    const gicsSector = SECTOR_TO_GICS[s.name] || '';
    const clickAttrs = gicsSector
        ? `data-sector-jump="${gicsSector}" style="cursor:pointer" title="${t().jump_to_momentum || '查看此產業的動能選股結果'}"`
        : '';

    // V2.17.1 — Top-5 competitive landscape (collapsible). Data sourced from
    // bridge.py extract_sector_competitors() via SECTOR_TOP_5 + 24h profile cache.
    // V2.17.2 — rich tooltip (signal-tip style) on row hover via data-comp-tip.
    // Hidden when sector has no competitors (graceful skip).
    const competitors = Array.isArray(s.competitors) ? s.competitors : [];
    const compRows = competitors.map(c => {
        const mc = c.market_cap;
        const mcStr = mc == null ? '—'
                    : mc >= 1e12 ? `$${(mc/1e12).toFixed(2)}T`
                    : mc >= 1e9  ? `$${(mc/1e9).toFixed(0)}B`
                    : `$${(mc/1e6).toFixed(0)}M`;
        const company = (c.company || '—').replace(/"/g, '&quot;');
        // Pack metadata into data-* attrs for the rich tooltip handler below.
        const tipData = JSON.stringify({
            ticker:    c.ticker,
            company:   c.company || null,
            industry:  c.industry || null,
            ceo:       c.ceo || null,
            price:     c.price != null ? c.price : null,
            market_cap: mc != null ? mc : null,
            sector:    s.name,
            verdict:   s.verdict,
        }).replace(/"/g, '&quot;');
        const jumpTo = gicsSector
            ? `momentum.html?sector=${encodeURIComponent(gicsSector)}&ticker=${encodeURIComponent(c.ticker)}`
            : `momentum.html?ticker=${encodeURIComponent(c.ticker)}`;
        return `<tr class="sec-comp-row" data-comp-tip="${tipData}">
            <td class="sec-comp-ticker"><a href="${jumpTo}" onclick="event.stopPropagation()">${c.ticker}</a></td>
            <td class="sec-comp-company">${company}</td>
            <td class="sec-comp-mc">${mcStr}</td>
        </tr>`;
    }).join('');
    const competitorsBlock = compRows
        ? `<details class="sec-comp" onclick="event.stopPropagation()">
              <summary class="sec-comp-summary">📊 ${lang==='zh'?'Top 5 競品':'Top 5'}</summary>
              <table class="sec-comp-table"><tbody>${compRows}</tbody></table>
           </details>`
        : '';
    return `
    <div class="sector-card verdict-${v} flex flex-col gap-2" ${clickAttrs}>
        <!-- Header row -->
        <div class="flex items-start justify-between gap-1">
            <div>
                <div class="text-sm font-black tracking-tight" style="color:${vc.hex}">${s.proxy_etf || nameEN}</div>
                <div class="text-[11px] text-zinc-500 leading-tight mt-0.5">${dispName}</div>
            </div>
            <div class="flex flex-col items-end gap-1 shrink-0">
                <span class="text-[9px] font-black px-2 py-0.5 rounded" style="background:${vc.bg};color:${vc.hex};border:1px solid ${vc.border}">${v}</span>
                <span class="text-[10px] font-black" style="color:${rotColor}">${rotIcon} ${s.rotation_signal || ''}</span>
            </div>
        </div>

        <!-- Score ring + uptrend -->
        <div class="flex items-center gap-3">
            <div class="score-ring verdict-${v}" style="--pct:${pct}">
                <div class="score-ring-inner">${s.score}</div>
            </div>
            <div class="flex-1 min-w-0">
                ${uptrendBar}
                ${s.overbought_risk === 'HIGH' ? `<div class="text-[10px] text-orange-400 font-bold mt-1">${t().overbought_label || '⚠ Overbought'}</div>` : ''}
            </div>
        </div>

        <!-- Score components breakdown -->
        ${compBars ? `<div class="space-y-0.5">${compBars}</div>` : ''}

        <!-- Key reasons -->
        ${reasons ? `<div class="space-y-0.5">${reasons}</div>` : ''}

        <!-- Risk flags -->
        ${flags ? `<div class="flex flex-wrap gap-1">${flags}</div>` : ''}

        <!-- DA note -->
        ${daNote}

        <!-- V2.17.1 — Top 5 競品 collapsible -->
        ${competitorsBlock}
    </div>`;
}

/* ── Three-Signal Synthesis ──────────────────────────────────── */
function renderThreeSignal(breadth, ftd, marketTop) {
    const container = document.getElementById('three-signal-content');
    if (!container) return;

    // ── Helper: parse "40-55%" → 47.5 (midpoint) ──
    function parseMidpoint(str) {
        if (!str) return null;
        const nums = String(str).replace(/%/g, '').split('-').map(Number).filter(n => !isNaN(n));
        if (nums.length === 2) return (nums[0] + nums[1]) / 2;
        if (nums.length === 1) return nums[0];
        return null;
    }

    // ── Signal data ──
    const bScore  = breadth?.score ?? null;
    const bZone   = breadth?.zone   || '–';
    const bCeil   = breadth?.exposure_ceiling || '–';
    const bPhase  = breadth?.cycle_phase || '–';

    const ftdState = (ftd?.state || 'NO_SIGNAL').replace(/_/g, ' ');
    const ftdQ     = ftd?.quality_score ?? null;
    const ftdExp   = ftd?.exposure_range || '–';

    const mtScore  = marketTop?.composite_score ?? null;
    const mtZone   = marketTop?.zone || '–';
    const mtBudget = marketTop?.risk_budget || '–';

    // ── Color helpers ──
    function zoneColor(zone) {
        if (!zone) return '#71717a';
        const z = zone.toLowerCase();
        if (z.includes('strong') || z.includes('healthy')) return '#22c55e';
        if (z.includes('weak'))   return '#f59e0b';
        if (z.includes('crit'))   return '#ef4444';
        if (z.includes('normal') || z.includes('early')) return '#22c55e';
        if (z.includes('elevat') || z.includes('high'))  return '#f59e0b';
        if (z.includes('top'))    return '#ef4444';
        return '#71717a';
    }
    function ftdColor(state) {
        if (!state) return '#71717a';
        const s = state.toUpperCase();
        if (s.includes('CONFIRMED')) return '#22c55e';
        if (s.includes('WINDOW'))    return '#3b82f6';
        if (s.includes('RALLY'))     return '#f59e0b';
        if (s.includes('INVALIDAT')) return '#ef4444';
        if (s.includes('CORRECTION'))return '#ef4444';
        return '#71717a';
    }

    // ── Synthesized exposure ceiling ──
    const ceilMids = [bCeil, ftdExp, mtBudget].map(parseMidpoint).filter(v => v !== null);
    const synthMid = ceilMids.length ? Math.min(...ceilMids) : null;
    let synthLabel = synthMid !== null ? `${Math.round(synthMid)}%` : '–';

    // Conflict detection: spread > 30pp
    const maxMid   = ceilMids.length ? Math.max(...ceilMids) : null;
    const hasConflict = ceilMids.length >= 2 && maxMid - synthMid > 30;

    // ── Signal rows ──
    function signalRow(icon, label, mainVal, subVal, color, barPct) {
        const pct = Math.min(100, Math.max(0, barPct ?? 0));
        return `
        <div class="rounded-md p-2.5" style="background:color-mix(in srgb,${color},transparent 92%)">
            <div class="flex items-center justify-between mb-1.5">
                <div class="flex items-center gap-1.5">
                    <i data-lucide="${icon}" class="w-3 h-3" style="color:${color}"></i>
                    <span class="text-[9px] font-black uppercase tracking-widest text-zinc-400">${label}</span>
                </div>
                <span class="text-xs font-black" style="color:${color}">${mainVal}</span>
            </div>
            <div class="h-1 rounded-full bg-zinc-700/40 mb-1.5">
                <div class="h-1 rounded-full transition-all" style="width:${pct}%;background:${color}"></div>
            </div>
            <div class="text-[9px] text-zinc-500 truncate">${subVal}</div>
        </div>`;
    }

    const bColor  = zoneColor(bZone);
    const ftdC    = ftdColor(ftd?.state || '');
    const mtColor = zoneColor(mtZone);

    // ── Synthesized exposure badge ──
    const synthColor = synthMid === null ? '#71717a'
        : synthMid >= 75 ? '#22c55e'
        : synthMid >= 50 ? '#f59e0b'
        : '#ef4444';

    const tr = t();
    const conflictBadge = hasConflict ? `
        <div class="flex items-center gap-1 mt-1">
            <i data-lucide="alert-triangle" class="w-3 h-3 text-yellow-400"></i>
            <span class="text-[9px] text-yellow-400">${tr.signal_conflict || 'Signal conflict — use conservative ceiling'}</span>
        </div>` : '';

    container.innerHTML = `
        ${signalRow('activity',       tr.signal_breadth || 'Breadth',    bScore !== null ? `${bScore}` : '–', `${bZone} · ${bPhase} · ${tr.cap_label || 'Cap'} ${bCeil}`, bColor,  bScore)}
        ${signalRow('trending-up',    tr.signal_ftd     || 'FTD',        ftdState,  `${tr.quality_label || 'Quality'} ${ftdQ ?? '–'} · ${tr.exposure_label || 'Exp'} ${ftdExp}`, ftdC, ftdQ)}
        ${signalRow('shield-alert',   tr.signal_top     || 'Market Top', mtScore !== null ? `${mtScore}` : '–', `${mtZone} · ${tr.budget_label || 'Budget'} ${mtBudget}`, mtColor, 100 - (mtScore ?? 50))}

        <div class="rounded-md p-2.5 mt-1" style="background:color-mix(in srgb,${synthColor},transparent 88%);border:1px solid color-mix(in srgb,${synthColor},transparent 70%)">
            <div class="flex items-center justify-between">
                <span class="text-[9px] font-black uppercase tracking-widest text-zinc-400">${tr.synthesized_ceiling || 'Synthesized Ceiling'}</span>
                <span class="text-sm font-black" style="color:${synthColor}">${synthLabel}</span>
            </div>
            <div class="text-[9px] text-zinc-500 mt-0.5">${tr.synth_subtitle || 'min(Breadth, FTD, Top) — most conservative'}</div>
            ${conflictBadge}
        </div>`;

    UI.icons();
}

/* ── Catalyst Feed ───────────────────────────────────────────── */
function renderCatalystFeed(market) {
    if (!market) return;
    const container = document.getElementById('catalyst-feed');
    const items = [];

    // Trump signals
    (market.trump_signals || []).forEach(ts => {
        const bearish = ts.direction === 'bearish';
        const color   = bearish ? '#ef4444' : '#22c55e';
        const icon    = bearish ? '🔻' : '🔺';
        items.push(`
        <div class="trump-signal-card" style="border-left-color:${color};background:color-mix(in srgb,${color},transparent 94%)">
            <div class="flex items-start gap-2">
                <span>${icon}</span>
                <div class="flex-1 min-w-0">
                    <div class="text-[9px] font-black uppercase tracking-wide mb-0.5" style="color:${color}">${ts.keyword?.replace(/_/g,' ').toUpperCase()}</div>
                    <p class="text-[10px] leading-snug" style="color:var(--text-muted)">${ts.headline}</p>
                    <div class="flex flex-wrap gap-1 mt-1">
                        ${(ts.affected_sectors||[]).map(s => `<span class="text-[8px] px-1 rounded" style="background:${color}18;color:${color}">${s.replace(/_/g,' ')}</span>`).join('')}
                    </div>
                </div>
            </div>
        </div>`);
    });

    // Named targets
    if (market.named_targets?.length) {
        const ntLabel = t().named_targets_today || 'Named Targets Today';
        items.push(`
        <div class="px-3 py-2 rounded-lg border border-red-500/25 bg-red-500/6">
            <div class="text-[8px] font-black text-red-400 uppercase tracking-wider mb-1">${ntLabel}</div>
            <div class="flex flex-wrap gap-1.5">
                ${market.named_targets.map(nt => `<span class="text-[9px] font-bold text-red-300 bg-red-500/12 px-2 py-0.5 rounded border border-red-500/20">${nt}</span>`).join('')}
            </div>
        </div>`);
    }

    // Top catalysts (market-moving events over past ~7 days)
    if (market.top_catalysts?.length) {
        const cLabel = t().top_catalysts_title || '主要催化事件';
        items.push(`<div class="text-[8px] font-black text-zinc-500 uppercase tracking-wider pt-2 border-t border-zinc-200 dark:border-zinc-800">${cLabel}</div>`);
        market.top_catalysts.forEach(cat => {
            const dir = cat.direction;
            const color = dir === 'bullish' ? '#22c55e'
                        : dir === 'bearish' ? '#ef4444'
                        : dir === 'binary'  ? '#f97316'
                        :                     '#a1a1aa';
            const icon = dir === 'bullish' ? '🔺'
                       : dir === 'bearish' ? '🔻'
                       : dir === 'binary'  ? '⚡'
                       :                     '·';
            const impact = cat.impact_score ? ` · impact ${cat.impact_score}/5` : '';
            const sectors = (cat.affected_sectors || []).slice(0, 3)
                .map(s => `<span class="text-[8px] px-1 rounded" style="background:${color}18;color:${color}">${s.replace(/_/g,' ')}</span>`).join('');
            items.push(`
            <div class="trump-signal-card" style="border-left-color:${color};background:color-mix(in srgb,${color},transparent 94%)">
                <div class="flex items-start gap-2">
                    <span>${icon}</span>
                    <div class="flex-1 min-w-0">
                        <p class="text-[10px] leading-snug" style="color:var(--text-muted)">${cat.event}</p>
                        <div class="flex flex-wrap gap-1 mt-1 items-center">
                            ${sectors}
                            <span class="text-[8px] text-zinc-500">${cat.timing || ''}${impact}</span>
                        </div>
                    </div>
                </div>
            </div>`);
        });
    }

    container.innerHTML = items.join('') || `<p class="text-[10px] text-zinc-600">${t().no_catalyst || 'No political signals detected.'}</p>`;
}

/* ── Divergence Watch ────────────────────────────────────────── */
function renderDivergence(divs) {
    const container = document.getElementById('divergence-list');
    const tr = t();
    if (!divs.length) {
        container.innerHTML = `<p class="text-[10px] text-zinc-600">${tr.no_divergence || 'No active divergences.'}</p>`;
        return;
    }
    container.innerHTML = divs.map(d => {
        const isRedFlag = d.signal?.includes('positive_price_negative');
        const color     = isRedFlag ? '#ef4444' : '#eab308';
        const actionIcon = d.action === 'reduce_exposure'
            ? (tr.action_reduce || '↓ Reduce Exposure')
            : (tr.action_monitor || '👁 Monitor');
        return `
        <div class="flex items-start gap-3 p-3 rounded-lg border" style="border-color:${color}30;background:${color}08">
            <div class="w-2 h-2 rounded-full mt-1 shrink-0" style="background:${color}"></div>
            <div class="flex-1 min-w-0">
                <div class="flex items-center gap-2 flex-wrap mb-0.5">
                    <span class="text-[10px] font-black" style="color:${color}">${d.sector}</span>
                    <span class="text-[7px] font-bold px-1.5 py-0.5 rounded border" style="color:${color};border-color:${color}40;background:${color}15">${d.signal?.replace(/_/g,' ').toUpperCase()}</span>
                </div>
                <p class="text-[9px] leading-snug" style="color:var(--text-muted)">${d.description}</p>
                <p class="text-[8px] font-bold mt-1" style="color:${color}">${actionIcon}</p>
            </div>
        </div>`;
    }).join('');
}

/* ── Themes ──────────────────────────────────────────────────── */
function renderThemes(themes) {
    const container = document.getElementById('themes-feed');
    if (!themes.length) { container.innerHTML = `<p class="text-[10px] text-zinc-600">${t().no_themes || 'No active themes.'}</p>`; return; }

    // V2.20.0 — overlay paradigm-shift theme overrides from theme-detector cache.
    // Renders ⚡ icon + tooltip with hits (e.g. MU:CONFIRMED, NVDA:CANDIDATE).
    const overrides = (window.UI?._themeOverrides) || [];
    const overrideMap = new Map();
    overrides.forEach(o => {
        const norm = (o.name || '').toLowerCase().replace(/[\s_&]+/g, '');
        if (norm) overrideMap.set(norm, o);
    });
    const _matchOverride = (themeName) => {
        const norm = (themeName || '').toLowerCase().replace(/[\s_&]+/g, '');
        // Try exact match first; fall back to substring (sector themes use varied naming)
        if (overrideMap.has(norm)) return overrideMap.get(norm);
        for (const [key, val] of overrideMap.entries()) {
            if (norm.includes(key) || key.includes(norm)) return val;
        }
        return null;
    };

    container.innerHTML = themes.map((th, i) => {
        const themeStr = (typeof th === 'string') ? th : (th.name || String(th));
        const ovr = _matchOverride(themeStr);
        const boltHtml = ovr
            ? ` <span style="color:#f59e0b;font-weight:700" title="V2.18 結構性轉變 — bonus +${ovr.bonus} (${(ovr.hits||[]).join(', ')})">⚡</span>`
            : '';
        return `
        <div class="flex items-start gap-2 p-2.5 rounded-lg bg-violet-500/5 border border-violet-500/15">
            <span class="text-[9px] font-black text-violet-500 shrink-0">${String(i+1).padStart(2,'0')}</span>
            <span class="text-[10px] font-medium leading-snug" style="color:var(--text-muted)">${themeStr.replace(/_/g,' ')}${boltHtml}</span>
        </div>`;
    }).join('');
}

/* ── Bootstrap ───────────────────────────────────────────────── */
function t() { return (window.i18n?.[UI.currentLang]?.sector_page) || {}; }

function applyTranslations() {
    const tr = t();
    const set = (id, val) => { const el = document.getElementById(id); if (el && val != null) el.textContent = val; };
    // Header: Chinese title + English subtitle (matches decisions.html pattern)
    if (UI.currentLang === 'zh') {
        set('sector-title',    '產業掃描');
        set('sector-subtitle', 'Sector Intelligence');
    } else {
        set('sector-title',    'Sector Intelligence');
        set('sector-subtitle', '產業掃描');
    }
    // Refresh button: short label to match other pages ("更新" / "Refresh")
    set('refresh-sector-label', UI.currentLang === 'zh' ? '更新' : 'Refresh');
    set('binary-alert-title',   tr.binary_alert);
    set('handoff-title',        tr.handoff_title);
    set('tv-takeaways-title',   tr.tv_takeaways_title);
    set('tv-actions-title',     tr.tv_actions_title);
    set('tv-watch-title',       tr.tv_watch_title);
    set('tv-fallback-title',    tr.handoff_title);
    set('catalyst-title',       tr.catalyst_title);
    set('divergence-title',     tr.divergence_title);
    set('themes-title',         tr.themes_title);
    set('heatmap-title',        tr.heatmap_title);
}

/* ── Reverse-call: trigger Claude to run sector scan ─────────── */
let _scanPollTimer = null;

function formatElapsed(sec) {
    const m = Math.floor(sec / 60); const s = sec % 60;
    return `${String(m).padStart(2,'0')}:${String(s).padStart(2,'0')}`;
}

const STATUS_STYLES = {
    running:   { bg: 'rgba(234,179,8,0.12)',  border: 'rgba(234,179,8,0.35)',  text: '#facc15', icon: 'zap' },
    done:      { bg: 'rgba(34,197,94,0.12)',  border: 'rgba(34,197,94,0.35)',  text: '#4ade80', icon: 'check-circle' },
    error:     { bg: 'rgba(239,68,68,0.12)',  border: 'rgba(239,68,68,0.35)',  text: '#f87171', icon: 'x-circle' },
    cancelled: { bg: 'rgba(113,113,122,0.15)',border: 'rgba(113,113,122,0.35)',text: '#a1a1aa', icon: 'minus-circle' },
};

function showScanBanner() {
    const b = document.getElementById('scan-banner');
    if (b) b.classList.remove('hidden');
}
function hideScanBanner() {
    document.getElementById('scan-banner')?.classList.add('hidden');
    document.getElementById('scan-banner-panel')?.classList.add('hidden');
    if (_scanPollTimer) { clearInterval(_scanPollTimer); _scanPollTimer = null; }
}
function setBannerStatus(status) {
    const card = document.getElementById('scan-banner');      // outer glass-card
    const st   = document.getElementById('scan-banner-status'); // status tag inside header row
    const titleEl = document.getElementById('scan-banner-title');
    const sty  = STATUS_STYLES[status] || STATUS_STYLES.running;
    
    if (card) card.style.setProperty('--scan-accent', sty.text);
    const pulse = document.getElementById('scan-banner-pulse');
    if (pulse) {
        pulse.style.background = sty.text;
        pulse.classList.toggle('animate-pulse', status === 'running');
    }

    const tr = t();
    if (titleEl) {
        const titleMap = {
            running:   tr.scan_banner_title_running || (UI.currentLang === 'zh' ? '產業掃描執行中…' : 'Sector Intel Running…'),
            done:      tr.scan_banner_title_done    || (UI.currentLang === 'zh' ? '產業掃描已完成' : 'Sector Intel Complete'),
            error:     tr.scan_banner_title_err     || (UI.currentLang === 'zh' ? '掃描發生錯誤' : 'Scan Failed'),
            cancelled: tr.scan_banner_title_err     || (UI.currentLang === 'zh' ? '掃描已取消' : 'Scan Cancelled'),
        };
        titleEl.textContent = titleMap[status] || titleMap.running;
    }

    if (st) {
        const labelMap = {
            running:   tr.scan_running   || 'RUNNING',
            done:      tr.scan_done      || 'DONE',
            error:     tr.scan_error     || 'ERROR',
            cancelled: tr.scan_cancelled || 'CANCELLED',
        };
        st.textContent = labelMap[status] || status.toUpperCase();
        st.style.color      = sty.text;
        st.style.background = sty.bg;
    }

    // Hide latest log preview on terminal states to reduce clutter
    const latest = document.getElementById('scan-banner-latest');
    if (latest) {
        const isTerminal = (status === 'done' || status === 'error' || status === 'cancelled');
        latest.closest('.min-w-0.relative')?.classList.toggle('hidden', isTerminal);
    }

    // Cancel only while running; Dismiss for everything else
    document.getElementById('scan-cancel-btn')?.classList.toggle('hidden', status !== 'running');
    document.getElementById('scan-dismiss-btn')?.classList.toggle('hidden', status === 'running');
}

function renderScanEvents(events) {
    const pre = document.getElementById('scan-events');
    if (!pre) return;
    if (!events || !events.length) {
        pre.textContent = '(waiting for first event...)';
        return;
    }
    const wasBottom = pre.scrollTop + pre.clientHeight >= pre.scrollHeight - 10;
    pre.textContent = events.map(ev => `${ev.icon || '·'} ${ev.text || ''}`).join('\n');
    if (wasBottom) pre.scrollTop = pre.scrollHeight;
    // Banner latest = last event
    const latest = document.getElementById('scan-banner-latest');
    const last = events[events.length - 1];
    if (latest && last) {
        latest.textContent = `${last.icon} ${last.text}`;
        latest.title = last.text;
    }
}

async function pollScanStatus() {
    try {
        const res = await fetch('/api/run-protocol/status');
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const s = await res.json();
        setBannerStatus(s.status);
        document.getElementById('scan-banner-elapsed').textContent = formatElapsed(s.elapsed_sec || 0);
        renderScanEvents(s.events || []);
        if (s.status !== 'running') {
            if (_scanPollTimer) { clearInterval(_scanPollTimer); _scanPollTimer = null; }
            if (s.status === 'error' || s.status === 'cancelled') {
                const err = document.getElementById('scan-error');
                if (err) { err.textContent = s.error || s.status; err.classList.remove('hidden'); }
            }
            if (s.status === 'done') {
                // Wait for bridge.py (kicked off async after scan) then refresh page data
                setTimeout(() => loadSectorData(), 3000);
                // Banner stays up — user dismisses via the ✕ (#scan-dismiss-btn) button.
            }
        }
    } catch (e) {
        logToUI('scan poll error: ' + e.message, 'error');
    }
}

/* Auto-run breadth/FTD/market_top if any are stale before sector scan.
   Returns when preflight is done (or on timeout/error — scan proceeds anyway). */
async function _runPreflightIfStale() {
    const latest = document.getElementById('scan-banner-latest');
    try {
        const checkRes = await fetch('/api/preflight');
        if (!checkRes.ok) return;
        const { items } = await checkRes.json();
        const stale = (items || []).filter(i => (i.status === 'STALE' || i.status === 'MISSING') && i.free);
        if (stale.length === 0) return;

        const labels = stale.map(i => i.label || i.key).join(', ');
        if (latest) latest.textContent = `⏳ 更新基礎數據 (${labels})…`;

        const runRes = await fetch('/api/preflight/run-free', { method: 'POST' });
        if (!runRes.ok) return; // proceed even if kick-off fails

        await new Promise(resolve => {
            const timer = setInterval(async () => {
                try {
                    const s = await fetch('/api/preflight/status').then(r => r.json());
                    if (s.status !== 'running') { clearInterval(timer); resolve(); }
                } catch { clearInterval(timer); resolve(); }
            }, 2000);
            setTimeout(() => { clearInterval(timer); resolve(); }, 3 * 60 * 1000); // 3 min hard cap
        });

        if (latest) latest.textContent = '✅ 基礎數據已更新，啟動產業掃描中…';
    } catch {
        // preflight failure is non-fatal — let scan proceed
    }
}

async function triggerSectorScan() {
    const tr = t();
    const prefix = await UI.dailyUpdatePrefix();
    const confirmMsg = prefix + (tr.scan_confirm || 'Run full sector scan via Claude? (~3-5 min, consumes tokens)');
    if (!confirm(confirmMsg)) return;
    showScanBanner();
    setBannerStatus('running');
    document.getElementById('scan-banner-elapsed').textContent = '00:00';
    document.getElementById('scan-banner-latest').textContent = '(starting...)';
    renderScanEvents([]);
    document.getElementById('scan-error')?.classList.add('hidden');
    try {
        await _runPreflightIfStale();
        const res = await fetch('/api/run-protocol', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name: 'sector' }),
        });
        if (!res.ok) {
            const err = await res.json().catch(() => ({ error: res.statusText }));
            throw new Error(err.error || `HTTP ${res.status}`);
        }
        _scanPollTimer = setInterval(pollScanStatus, 2000);
        pollScanStatus();
    } catch (e) {
        const errEl = document.getElementById('scan-error');
        if (errEl) {
            errEl.textContent = `${tr.scan_start_failed || 'failed to start'}: ${e.message}`;
            errEl.classList.remove('hidden');
        }
        setBannerStatus('error');
    }
}

async function cancelSectorScan() {
    try { await fetch('/api/run-protocol/cancel', { method: 'POST' }); }
    catch (e) { logToUI('cancel error: ' + e.message, 'error'); }
}

function toggleScanPanel() {
    const panel = document.getElementById('scan-banner-panel');
    const btn   = document.getElementById('scan-expand-btn');
    if (!panel) return;
    const open = panel.classList.toggle('hidden') === false;
    if (btn) {
        const tr = t();
        btn.textContent = open ? (tr.scan_minimize || '收合') : (tr.scan_expand || '展開');
    }
    if (open) {
        const pre = document.getElementById('scan-events');
        if (pre) pre.scrollTop = pre.scrollHeight;
    }
}

document.getElementById('refresh-sector').addEventListener('click', triggerSectorScan);
document.getElementById('scan-cancel-btn')?.addEventListener('click', cancelSectorScan);
document.getElementById('scan-dismiss-btn')?.addEventListener('click', hideScanBanner);
document.getElementById('scan-expand-btn')?.addEventListener('click', toggleScanPanel);

// Resume banner on page load for in-flight *or* recently-finished scans.
// Without this, navigating away mid-scan and back made the progress card vanish;
// worse, a just-finished result disappeared before the user could read it.
// Rule: always show the banner for running; show done/error if ended in the last 5 min.
(async () => {
    try {
        const r = await fetch('/api/run-protocol/status');
        const s = await r.json();
        if (s.name && s.name !== 'sector') return;  // banner belongs to another protocol
        const RESUME_TERMINAL_WINDOW_MS = 5 * 60 * 1000;
        const endedRecently = s.ended_at
            && (Date.now() - new Date(s.ended_at).getTime()) < RESUME_TERMINAL_WINDOW_MS;
        if (s.status === 'running') {
            showScanBanner();
            setBannerStatus('running');
            _scanPollTimer = setInterval(pollScanStatus, 2000);
            pollScanStatus();
        } else if ((s.status === 'done' || s.status === 'error') && endedRecently) {
            showScanBanner();
            setBannerStatus(s.status);
            document.getElementById('scan-banner-elapsed').textContent =
                formatElapsed(s.elapsed_sec || 0);
            renderScanEvents(s.events || []);
            if (s.status === 'error') {
                const err = document.getElementById('scan-error');
                if (err) { err.textContent = s.error || 'error'; err.classList.remove('hidden'); }
            }
        }
    } catch (e) { /* ignore */ }
})();
UI.boot('sector', {
    translate: applyTranslations,
    reload: loadSectorData,
    onThemeChange: () => { loadSectorData(); recolorHeatmap(); },
});
loadSectorData();

/* ════════════════════════════════════════════════════════════════════
 * S&P 500 + NDX 100 LIVE HEATMAP
 * - Polls /api/heatmap/data every 3 min (visibility-aware)
 * - Treemap: Sector → Industry → Ticker, sized by market cap
 * - Hover: instant tooltip (cached fields); 3s debounce → fetch news
 * ════════════════════════════════════════════════════════════════════ */

const HEATMAP_POLL_MS    = 180000;   // 3 min
const HEATMAP_TOOLTIP_DELAY_MS = 3000;  // user-confirmed: only fetch news after 3s sustained hover

let _heatmapData      = null;
let _heatmapBuiltKey  = null;        // cache key for layout (changes when universe rebuilt)
let _heatmapTimer     = null;
let _tooltipDebounce  = null;
let _newsAbort        = null;
let _heatmapHoverEl   = null;        // currently hovered ticker (for tooltip news fill)

function _heatmapColorFor(changePct) {
    if (changePct === null || changePct === undefined || isNaN(changePct)) return '#d4d4d8';
    // 7-stop divergent scale: 螢光紅 → 紅 → 紅淺灰 → 淺灰 → 綠淺灰 → 綠 → 螢光綠
    // Center is light gray (zinc-300), small moves stay near gray, large moves saturate.
    const clamped = Math.max(-3, Math.min(3, changePct));
    const t = Math.abs(clamped) / 3;        // 0 → light gray, 1 → vivid color
    const center = [212, 212, 216];         // zinc-300 淺灰
    let mid, peak;
    if (clamped >= 0) {
        mid  = [134, 239, 172];             // green-300 綠淺灰 (mid stop)
        peak = [16, 185, 129];              // emerald-500 螢光綠
    } else {
        mid  = [252, 165, 165];             // red-300 紅淺灰 (mid stop)
        peak = [239, 68, 68];               // red-500 螢光紅
    }
    // Two-segment piecewise: center → mid (0..0.5) → peak (0.5..1)
    let r, g, b;
    if (t < 0.5) {
        const lt = t / 0.5;
        r = center[0] + (mid[0] - center[0]) * lt;
        g = center[1] + (mid[1] - center[1]) * lt;
        b = center[2] + (mid[2] - center[2]) * lt;
    } else {
        const lt = (t - 0.5) / 0.5;
        r = mid[0] + (peak[0] - mid[0]) * lt;
        g = mid[1] + (peak[1] - mid[1]) * lt;
        b = mid[2] + (peak[2] - mid[2]) * lt;
    }
    return `rgb(${Math.round(r)},${Math.round(g)},${Math.round(b)})`;
}

function _heatmapTextColor(changePct) {
    if (changePct === null || isNaN(changePct)) return '#52525b';   // zinc-600 dark on light gray
    // Light gray and pale-tint backgrounds need dark text; only saturated extremes get white
    return Math.abs(changePct) >= 1.8 ? '#ffffff' : '#18181b';
}

function _truncateForWidth(text, availPx, charPx) {
    if (!text) return '';
    const maxChars = Math.floor(availPx / charPx);
    if (maxChars < 2) return '';
    if (text.length <= maxChars) return text;
    return text.slice(0, Math.max(1, maxChars - 1)) + '…';
}

function _formatMarketCap(mcap) {
    if (!mcap) return '--';
    if (mcap >= 1e12) return (mcap / 1e12).toFixed(2) + 'T';
    if (mcap >= 1e9)  return (mcap / 1e9).toFixed(1)  + 'B';
    if (mcap >= 1e6)  return (mcap / 1e6).toFixed(0)  + 'M';
    return mcap.toFixed(0);
}

function _formatVolume(v) {
    if (!v) return '--';
    if (v >= 1e9) return (v / 1e9).toFixed(2) + 'B';
    if (v >= 1e6) return (v / 1e6).toFixed(2) + 'M';
    if (v >= 1e3) return (v / 1e3).toFixed(1) + 'K';
    return String(v);
}

async function loadHeatmap() {
    try {
        const r = await fetch('/api/heatmap/data');
        if (!r.ok) throw new Error('HTTP ' + r.status);
        const data = await r.json();
        _heatmapData = data;

        // Update status row
        const tr = t();
        const statusEl = document.getElementById('heatmap-market-status');
        const updateEl = document.getElementById('heatmap-last-update');
        if (statusEl) {
            statusEl.textContent = data.market_open
                ? (tr.heatmap_market_open || 'MARKET OPEN')
                : (tr.heatmap_market_closed || 'MARKET CLOSED');
            statusEl.style.color = data.market_open ? '#22c55e' : '#71717a';
        }
        if (updateEl && data.last_update) {
            const dt = new Date(data.last_update);
            updateEl.textContent = dt.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
        }

        // Decide if we need full layout rebuild
        const needRebuild = (data.universe_built_at !== _heatmapBuiltKey)
                            || !document.querySelector('#heatmap-container svg');
        renderHeatmap(data, needRebuild);
        if (needRebuild) _heatmapBuiltKey = data.universe_built_at;
    } catch (e) {
        if (window.logToUI) logToUI('Heatmap load error: ' + e.message, 'error');
    }
}

function renderHeatmap(data, fullRebuild) {
    const container = document.getElementById('heatmap-container');
    if (!container || !window.d3) return;
    const tickers = (data.tickers || []).filter(t => t && t.market_cap > 0);
    if (!tickers.length) return;

    // Hide loading placeholder once we have data
    const loading = document.getElementById('heatmap-loading');
    if (loading) loading.style.display = 'none';

    if (!fullRebuild) {
        // Color-only update path (~10ms): rect fill + cell-ticker fill + cell-pct text & fill
        const byTicker = new Map(tickers.map(t => [t.ticker, t]));
        d3.select(container).selectAll('g.cell').each(function(d) {
            const next = byTicker.get(d.data.ticker);
            if (!next) return;
            d.data.price       = next.price;
            d.data.change_pct  = next.change_pct;
            d.data.day_low     = next.day_low;
            d.data.day_high    = next.day_high;
            d.data.volume      = next.volume;
            d.data.prev_close  = next.prev_close;
            d.data.pe          = next.pe;
            d.data.forward_pe  = next.forward_pe;
            d.data.ev_ebitda   = next.ev_ebitda;
            const fill = _heatmapTextColor(next.change_pct);
            d3.select(this).select('rect').attr('fill', _heatmapColorFor(next.change_pct));
            d3.select(this).select('.cell-ticker').attr('fill', fill);
            d3.select(this).select('.cell-pct')
                .text(next.change_pct == null ? '--' : (next.change_pct >= 0 ? '+' : '') + next.change_pct.toFixed(2) + '%')
                .attr('fill', fill);
        });
        return;
    }

    // FULL REBUILD ─────────────────────────────────────────────────
    container.innerHTML = '';
    const width  = container.clientWidth;
    const height = container.clientHeight;
    if (width <= 0 || height <= 0) return;

    // Build hierarchy: root → sector → industry → ticker
    const bySector = d3.group(tickers, d => d.sector || 'Other', d => d.industry || 'Other');
    const root = {
        name: 'root',
        children: Array.from(bySector, ([sector, industries]) => ({
            name: sector,
            children: Array.from(industries, ([industry, items]) => ({
                name: industry,
                children: items.map(item => ({ ...item, name: item.ticker }))
            }))
        }))
    };

    const hierarchy = d3.hierarchy(root)
        .sum(d => d.market_cap || 0)
        .sort((a, b) => (b.value || 0) - (a.value || 0));

    d3.treemap()
        .size([width, height])
        .paddingTop(d => d.depth === 1 ? 18 : (d.depth === 2 ? 12 : 0))
        .paddingInner(d => d.depth === 1 ? 2 : 1)
        .paddingOuter(2)
        .round(true)(hierarchy);

    const svg = d3.select(container)
        .append('svg')
        .attr('width', width)
        .attr('height', height)
        .style('display', 'block')
        .style('font-family', 'Inter, sans-serif');

    // Sector labels (depth 1) — truncate to fit width, hide if too small
    svg.selectAll('text.sector-label')
        .data(hierarchy.descendants().filter(d => d.depth === 1 && (d.x1 - d.x0) >= 50))
        .enter()
        .append('text')
        .attr('class', 'sector-label')
        .attr('x', d => d.x0 + 4)
        .attr('y', d => d.y0 + 13)
        .attr('font-size', 11)
        .attr('font-weight', 800)
        .attr('fill', '#fafafa')
        .text(d => {
            const sectorPct = _sectorAvgChange(d);
            const pctStr = sectorPct == null ? '' : '  ' + (sectorPct >= 0 ? '+' : '') + sectorPct.toFixed(2) + '%';
            const full = d.data.name + pctStr;
            return _truncateForWidth(full, (d.x1 - d.x0) - 8, 6.5);
        });

    // Industry labels (depth 2) — truncate to fit, only if min space
    svg.selectAll('text.industry-label')
        .data(hierarchy.descendants().filter(d => d.depth === 2 && (d.x1 - d.x0) >= 40 && (d.y1 - d.y0) >= 24))
        .enter()
        .append('text')
        .attr('class', 'industry-label')
        .attr('x', d => d.x0 + 3)
        .attr('y', d => d.y0 + 10)
        .attr('font-size', 9)
        .attr('font-weight', 600)
        .attr('fill', '#a1a1aa')
        .text(d => _truncateForWidth(d.data.name, (d.x1 - d.x0) - 6, 5.2));

    // Ticker cells (depth 3)
    const cells = svg.selectAll('g.cell')
        .data(hierarchy.descendants().filter(d => d.depth === 3))
        .enter()
        .append('g')
        .attr('class', 'cell')
        .attr('transform', d => `translate(${d.x0},${d.y0})`)
        .style('cursor', 'pointer');

    cells.append('rect')
        .attr('width',  d => Math.max(0, d.x1 - d.x0))
        .attr('height', d => Math.max(0, d.y1 - d.y0))
        .attr('fill', d => _heatmapColorFor(d.data.change_pct))
        .attr('stroke', 'rgba(0,0,0,0.4)')
        .attr('stroke-width', 0.5);

    // Ticker + % rendering: pick orientation per cell shape
    //   wide enough → horizontal (ticker on top, % below if room)
    //   narrow but tall → vertical 90° rotation
    //   too small either way → no label
    cells.each(function(d) {
        const w = d.x1 - d.x0, h = d.y1 - d.y0;
        const ticker = d.data.ticker || '';
        const pct = d.data.change_pct;
        const pctStr = pct == null ? '--' : (pct >= 0 ? '+' : '') + pct.toFixed(2) + '%';
        const fill = _heatmapTextColor(pct);
        const g = d3.select(this);

        // Estimate font scale by box area
        const baseSize = Math.min(13, Math.max(8, Math.sqrt(w * h) / 5.5));
        const charPx = baseSize * 0.62;
        const tickerWHor = ticker.length * charPx;
        const tickerWVer = ticker.length * charPx;  // when rotated, length runs along height

        const fitsHor = w >= tickerWHor + 4 && h >= baseSize + 4;
        const fitsVer = !fitsHor && h >= tickerWVer + 4 && w >= baseSize + 4;

        if (fitsHor) {
            // Horizontal: centered ticker, optional % below
            const showPct = h >= baseSize * 2 + 6 && w >= (pctStr.length * baseSize * 0.55) + 4;
            const dy = showPct ? -2 : (baseSize / 3);
            g.append('text')
                .attr('x', w / 2)
                .attr('y', h / 2 + dy)
                .attr('class', 'cell-ticker')
                .attr('text-anchor', 'middle')
                .attr('font-size', baseSize)
                .attr('font-weight', 800)
                .attr('fill', fill)
                .text(ticker);
            if (showPct) {
                g.append('text')
                    .attr('class', 'cell-pct')
                    .attr('x', w / 2)
                    .attr('y', h / 2 + baseSize)
                    .attr('text-anchor', 'middle')
                    .attr('font-size', baseSize * 0.78)
                    .attr('font-weight', 600)
                    .attr('fill', fill)
                    .text(pctStr);
            }
        } else if (fitsVer) {
            // Vertical: rotate text 90° around cell center
            const fs = Math.min(baseSize, w - 2);
            g.append('text')
                .attr('class', 'cell-ticker')
                .attr('text-anchor', 'middle')
                .attr('font-size', fs)
                .attr('font-weight', 800)
                .attr('fill', fill)
                .attr('transform', `translate(${w / 2}, ${h / 2}) rotate(90)`)
                .text(ticker);
        }
        // else: cell too small, leave as colored block only
    });

    // Hover handlers
    cells.on('mouseenter', function(event, d) { onHeatmapEnter(event, d.data); })
         .on('mousemove',  function(event)    { positionTooltip(event); })
         .on('mouseleave', function()         { onHeatmapLeave(); });
}

function _sectorAvgChange(sectorNode) {
    const leaves = sectorNode.leaves().filter(l => l.data.change_pct != null);
    if (!leaves.length) return null;
    const totalCap = leaves.reduce((s, l) => s + (l.data.market_cap || 0), 0);
    if (totalCap <= 0) return null;
    const weighted = leaves.reduce((s, l) => s + (l.data.change_pct || 0) * (l.data.market_cap || 0), 0);
    return weighted / totalCap;
}

function recolorHeatmap() {
    if (!_heatmapData) return;
    renderHeatmap(_heatmapData, false);
}

/* ── Tooltip ────────────────────────────────────────────────── */
function onHeatmapEnter(event, ticker) {
    _heatmapHoverEl = ticker.ticker;
    showHeatmapTooltip(ticker, event);

    // 3s debounce: fetch news only if user keeps hovering
    clearTimeout(_tooltipDebounce);
    _tooltipDebounce = setTimeout(() => {
        if (_heatmapHoverEl !== ticker.ticker) return;  // moved away
        if (_newsAbort) _newsAbort.abort();
        _newsAbort = new AbortController();
        fetch(`/api/heatmap/news/${ticker.ticker}`, { signal: _newsAbort.signal })
            .then(r => r.json())
            .then(payload => {
                if (_heatmapHoverEl !== ticker.ticker) return;  // moved away mid-fetch
                appendNewsToTooltip(payload.items || []);
            })
            .catch(() => {});  // ignore aborts
    }, HEATMAP_TOOLTIP_DELAY_MS);
}

function onHeatmapLeave() {
    _heatmapHoverEl = null;
    clearTimeout(_tooltipDebounce);
    if (_newsAbort) { _newsAbort.abort(); _newsAbort = null; }
    hideHeatmapTooltip();
}

function showHeatmapTooltip(ticker, event) {
    const tip = document.getElementById('heatmap-tooltip');
    if (!tip) return;
    const tr = t();
    const pct = ticker.change_pct;
    const pctColor = pct == null ? '#a1a1aa' : (pct >= 0 ? '#22c55e' : '#ef4444');
    const pctStr   = pct == null ? '--' : (pct >= 0 ? '+' : '') + pct.toFixed(2) + '%';
    const priceStr = ticker.price == null ? '--' : '$' + ticker.price.toFixed(2);
    const rangeStr = (ticker.day_low != null && ticker.day_high != null)
        ? `$${ticker.day_low.toFixed(2)} – $${ticker.day_high.toFixed(2)}` : '--';
    // V2.13.10/12 — valuation triplet: PE TTM + Forward PE + EV/EBITDA
    function _peColor(v) {
        if (v == null) return '#a1a1aa';
        if (v < 0)        return '#f87171';
        if (v < 15)       return '#4ade80';
        if (v > 30)       return '#fbbf24';
        return 'var(--text-main)';
    }
    function _evColor(v) {
        if (v == null) return '#a1a1aa';
        if (v < 0)        return '#f87171';
        if (v < 10)       return '#4ade80';
        if (v > 20)       return '#fbbf24';
        return 'var(--text-main)';
    }
    const pe       = ticker.pe;
    const fwdPe    = ticker.forward_pe;
    const evEbitda = ticker.ev_ebitda;
    const peStr    = pe       != null ? pe.toFixed(1)       : '--';
    const fwdPeStr = fwdPe    != null ? fwdPe.toFixed(1)    : '--';
    const evStr    = evEbitda != null ? evEbitda.toFixed(1) : '--';

    tip.innerHTML = `
        <div class="text-[10px] text-zinc-500 mb-1">${escapeHtml(ticker.sector)} · ${escapeHtml(ticker.industry)}</div>
        <div class="flex items-baseline gap-2 mb-2">
            <span class="text-base font-black" style="color: var(--text-main)">${escapeHtml(ticker.ticker)}</span>
            <span class="text-[10px] text-zinc-400 truncate">${escapeHtml(ticker.name || '')}</span>
        </div>
        <div class="space-y-1 text-[11px]">
            <div class="flex justify-between"><span class="text-zinc-500">${tr.heatmap_price || 'Price'}</span><span class="font-mono font-bold" style="color: var(--text-main)">${priceStr}</span></div>
            <div class="flex justify-between"><span class="text-zinc-500">${tr.heatmap_change || 'Change'}</span><span class="font-mono font-bold" style="color: ${pctColor}">${pctStr}</span></div>
            <div class="flex justify-between" title="TTM 含一次性項目可能扭曲；負值常為一次性虧損"><span class="text-zinc-500">P/E TTM</span><span class="font-mono font-bold" style="color: ${_peColor(pe)}">${peStr}</span></div>
            <div class="flex justify-between" title="Forward P/E (next FY consensus EPS) — 排除一次性 hit"><span class="text-zinc-500">Fwd P/E</span><span class="font-mono font-bold" style="color: ${_peColor(fwdPe)}">${fwdPeStr}</span></div>
            <div class="flex justify-between" title="EV/EBITDA TTM — 跨資本結構可比，&lt;10 便宜、&gt;20 高估"><span class="text-zinc-500">EV/EBITDA</span><span class="font-mono font-bold" style="color: ${_evColor(evEbitda)}">${evStr}</span></div>
            <div class="flex justify-between"><span class="text-zinc-500">${tr.heatmap_marketcap || 'Market Cap'}</span><span class="font-mono">${_formatMarketCap(ticker.market_cap)}</span></div>
            <div class="flex justify-between"><span class="text-zinc-500">${tr.heatmap_dayrange || 'Day Range'}</span><span class="font-mono">${rangeStr}</span></div>
            <div class="flex justify-between"><span class="text-zinc-500">${tr.heatmap_volume || 'Volume'}</span><span class="font-mono">${_formatVolume(ticker.volume)}</span></div>
        </div>
        <div id="heatmap-news-slot" class="mt-2 pt-2 border-t border-zinc-700/40 text-[10px] text-zinc-500 italic">
            ${escapeHtml(tr.heatmap_news_hint || '停留 3 秒讀新聞…')}
        </div>
    `;
    tip.classList.remove('hidden');
    tip.style.opacity = '1';
    positionTooltip(event);
}

function appendNewsToTooltip(items) {
    const slot = document.getElementById('heatmap-news-slot');
    if (!slot) return;
    const tr = t();
    if (!items.length) {
        slot.innerHTML = `<span class="italic text-zinc-500">${escapeHtml(tr.heatmap_no_news || '無近期新聞')}</span>`;
        return;
    }
    slot.classList.remove('italic');
    slot.innerHTML = items.map(n => {
        const url = n.url ? `href="${escapeAttr(n.url)}" target="_blank" rel="noopener"` : '';
        const title = n.title || '(無標題)';
        return `<div class="mb-1 leading-snug"><a ${url} class="hover:underline" style="color: var(--text-main); pointer-events: auto">${escapeHtml(title.slice(0, 110))}</a><span class="ml-1 text-[9px] text-zinc-500">${escapeHtml(n.source || '')}</span></div>`;
    }).join('');
    // Re-enable pointer events on links (tooltip itself is pointer-events: none)
    slot.style.pointerEvents = 'auto';
}

function positionTooltip(event) {
    const tip = document.getElementById('heatmap-tooltip');
    if (!tip || tip.classList.contains('hidden')) return;
    const rect = tip.getBoundingClientRect();
    const margin = 12;
    let x = event.clientX + 14;
    let y = event.clientY + 14;
    if (x + rect.width  > window.innerWidth  - margin) x = event.clientX - rect.width  - 14;
    if (y + rect.height > window.innerHeight - margin) y = event.clientY - rect.height - 14;
    tip.style.left = Math.max(margin, x) + 'px';
    tip.style.top  = Math.max(margin, y) + 'px';
}

function hideHeatmapTooltip() {
    const tip = document.getElementById('heatmap-tooltip');
    if (tip) tip.classList.add('hidden');
}

function escapeHtml(s) {
    return String(s == null ? '' : s).replace(/[&<>"']/g, c => ({ '&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;' }[c]));
}
function escapeAttr(s) { return escapeHtml(s); }

/* ── Polling (visibility-aware) ─────────────────────────────── */
function startHeatmapPolling() {
    if (_heatmapTimer) clearInterval(_heatmapTimer);
    _heatmapTimer = setInterval(() => {
        if (document.visibilityState === 'visible') loadHeatmap();
    }, HEATMAP_POLL_MS);
}

document.addEventListener('visibilitychange', () => {
    if (document.visibilityState === 'visible') loadHeatmap();
});

window.addEventListener('resize', () => {
    // Re-render on resize since treemap uses container width
    if (_heatmapData) renderHeatmap(_heatmapData, true);
});

// Bootstrap: kick off after page settles
setTimeout(() => { loadHeatmap(); startHeatmapPolling(); }, 800);


/* ── V2.17.2 — Top-5 競品 row rich tooltip (signal-tip style) ────────────
 * Reuses #signal-tip-tooltip element + its .stt-* CSS so visual matches
 * the existing 7 status pill tooltips. Distinct trigger attribute
 * (`data-comp-tip`) so it doesn't conflict with the SIGNAL_TIPS engine.
 */
(function initCompetitorTooltip() {
    function init() {
        const tip = document.getElementById('signal-tip-tooltip');
        if (!tip) return;
        let _hideTimer = null;

        function _fmtMC(mc) {
            if (mc == null) return '—';
            if (mc >= 1e12) return `$${(mc/1e12).toFixed(2)}T`;
            if (mc >= 1e9)  return `$${(mc/1e9).toFixed(1)}B`;
            if (mc >= 1e6)  return `$${(mc/1e6).toFixed(0)}M`;
            return `$${mc.toFixed(0)}`;
        }

        function _renderContent(data, lang) {
            const isZh = lang === 'zh';
            const title = `${data.ticker}${data.company ? ' · ' + data.company : ''}`;
            const subTitle = data.industry || '—';
            const rows = [];
            if (data.sector) {
                rows.push({
                    k: isZh ? '所屬產業' : 'Sector',
                    v: `${data.sector} · ${data.verdict || ''}`,
                });
            }
            if (data.market_cap != null) {
                rows.push({ k: isZh ? '市值'    : 'Market cap', v: _fmtMC(data.market_cap) });
            }
            if (data.price != null) {
                rows.push({ k: isZh ? '股價'    : 'Price',      v: `$${data.price.toFixed(2)}` });
            }
            if (data.ceo) {
                rows.push({ k: 'CEO', v: data.ceo });
            }
            const stages = rows.map(r => `
                <div class="stt-stage-row">
                    <span class="stt-stage-tag">${r.k}</span>
                    <span class="stt-stage-action" style="grid-column:2 / -1;font-style:normal;color:var(--text-main)">${r.v}</span>
                </div>`).join('');
            const hint = isZh
                ? `點擊 ticker → 跳 momentum 頁套用該 sector 過濾`
                : `Click ticker → momentum page with sector filter`;
            return `
                <div class="stt-title">${title}</div>
                <div class="stt-desc">${subTitle}</div>
                <div class="stt-stages">${stages}</div>
                <div class="stt-hint">${hint}</div>`;
        }

        function showCompTip(el) {
            let data;
            try {
                data = JSON.parse(el.dataset.compTip || '{}');
            } catch { return; }
            const lang = (window.UI && window.UI.currentLang) || 'zh';
            tip.innerHTML = _renderContent(data, lang);
            tip.style.opacity = '0';
            tip.style.top = '-9999px';
            tip.classList.add('visible');
            requestAnimationFrame(() => {
                const rect  = el.getBoundingClientRect();
                const tRect = tip.getBoundingClientRect();
                const gap   = 8;
                // Prefer right of the row, then above, then below
                let left = rect.right + gap;
                let top  = rect.top - 4;
                if (left + tRect.width > window.innerWidth - 8) {
                    // Fallback: above the row centered
                    left = rect.left + (rect.width - tRect.width) / 2;
                    top  = rect.top - tRect.height - gap;
                    if (top < 8) top = rect.bottom + gap;
                }
                left = Math.max(8, Math.min(left, window.innerWidth - tRect.width - 8));
                tip.style.top = top + 'px';
                tip.style.left = left + 'px';
                tip.style.opacity = '';
            });
        }

        function hideCompTip() { tip.classList.remove('visible'); }

        document.addEventListener('mouseover', e => {
            const el = e.target.closest('[data-comp-tip]');
            if (!el) return;
            if (_hideTimer) { clearTimeout(_hideTimer); _hideTimer = null; }
            showCompTip(el);
        });
        document.addEventListener('mouseout', e => {
            const el = e.target.closest('[data-comp-tip]');
            if (!el) return;
            _hideTimer = setTimeout(hideCompTip, 80);
        });
    }
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
