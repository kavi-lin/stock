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

/* ── Status Strip ────────────────────────────────────────────── */
function renderStatusStrip(data) {
    const m   = data.market || {};
    const br  = data.breadth || {};
    const ftd = data.ftd    || {};
    const mt  = data.market_top || {};

    const regimeColor = { BULL:'#22c55e', VOLATILE:'#f97316', BEAR:'#ef4444', SIDEWAYS:'#eab308', RISK_OFF:'#ef4444', RISK_ON:'#22c55e' };
    const zoneColor   = { Strong:'#22c55e', Healthy:'#22c55e', Neutral:'#eab308', Weakening:'#f97316', Critical:'#ef4444' };
    const ftdColor    = ftd.state === 'FTD_CONFIRMED' ? '#22c55e' : ftd.state === 'RALLY_ATTEMPT' ? '#eab308' : '#ef4444';
    const fgColor     = (m.fear_greed||50) < 25 ? '#ef4444' : (m.fear_greed||50) < 45 ? '#f97316' : (m.fear_greed||50) < 55 ? '#eab308' : '#22c55e';

    const tr = t();
    const ftdVal = ftd.state === 'FTD_CONFIRMED'
        ? (tr.ftd_confirmed || '✓ Confirmed')
        : (ftd.state?.replace(/_/g,' ') || '--');
    const pills = [
        { id:'pill-regime',   label: tr.pill_regime   || 'Regime',      value: m.regime||'--',                     color: regimeColor[m.regime] || '#eab308' },
        { id:'pill-breadth',  label: tr.pill_breadth  || 'Breadth',     value: (br.score||m.breadth_score||'--'),  color: zoneColor[br.zone] || '#eab308' },
        { id:'pill-ftd',      label: tr.pill_ftd      || 'FTD State',   value: ftdVal,                             color: ftdColor },
        { id:'pill-exposure', label: tr.pill_exposure || 'Exposure Cap',value: m.exposure_ceiling||'--',           color: '#a78bfa' },
        { id:'pill-fg',       label: tr.pill_fg       || 'Fear & Greed',value: `${m.fear_greed||'--'} ${m.fear_greed_label||''}`, color: fgColor },
        { id:'pill-cycle',    label: tr.pill_cycle    || 'Cycle',       value: m.cycle_phase||'--',                color: '#60a5fa' },
        { id:'pill-vix',      label: tr.pill_vix      || 'VIX',         value: data.market_top?.vix_level != null ? Number(data.market_top.vix_level).toFixed(1) : '--', color: '#a78bfa' },
    ];

    pills.forEach(p => {
        const el = document.getElementById(p.id);
        if (!el) return;
        el.innerHTML = `
            <span class="status-pill-label">${p.label}</span>
            <span class="status-pill-value" style="color:${p.color}">${p.value}</span>
        `;
    });

    // Populate live data attributes for shared signal-tip engine (utils.js).
    // Each pill exposes the metric so the rich tooltip can render the live banner
    // and highlight the active stage row.
    const setAttrs = (id, attrs) => {
        const el = document.getElementById(id);
        if (!el) return;
        Object.entries(attrs).forEach(([k, v]) => el.setAttribute(k, v == null ? '' : String(v)));
    };
    setAttrs('pill-regime',   { 'data-regime': m.regime || '' });
    setAttrs('pill-breadth',  { 'data-br-score':   br.score ?? m.breadth_score ?? '',
                                'data-br-zone':    br.zone || '',
                                'data-br-ceiling': br.exposure_ceiling || m.exposure_ceiling || '' });
    setAttrs('pill-ftd',      { 'data-ftd-state': ftd.state || '',
                                'data-ftd-date':  ftd.ftd_date || '',
                                'data-ftd-day':   ftd.days_since_ftd ?? '' });
    setAttrs('pill-exposure', { 'data-exposure': m.exposure_ceiling || '' });
    setAttrs('pill-fg',       { 'data-fg-score': m.fear_greed ?? '',
                                'data-fg-label': m.fear_greed_label || '' });
    setAttrs('pill-cycle',    { 'data-cycle': m.cycle_phase || '' });
    setAttrs('pill-vix',      { 'data-vix': mt.vix_level ?? '' });

    // Warning flags — clear first so language switches / reloads don't append duplicates
    const flagRow = document.getElementById('warning-flags-row');
    if (flagRow) {
        flagRow.innerHTML = '';
        (m.warning_flags || []).forEach(f => {
            const label = flagLabel(f);
            flagRow.insertAdjacentHTML('beforeend', `
                <div class="text-[8px] font-black px-2 py-1 rounded border bg-yellow-500/8 text-yellow-500 border-yellow-500/20 tracking-tight">${label}</div>
            `);
        });
    }

    // Scan date
    const sd = document.getElementById('scan-date');
    if (sd) sd.textContent = data.last_updated ? `SCAN: ${data.last_updated.split(' ')[0]}` : '';
}

/* ── Binary Alert (minimalist strip) ─────────────────────────── */
function renderBinaryAlert(risks) {
    const urgent = risks.filter(r => r.within_48h);
    const section = document.getElementById('binary-alert-section');
    if (!urgent.length) { section?.classList.add('hidden'); return; }
    section.classList.remove('hidden');
    const tr = t();
    const dateLabel = (r) => {
        if (r.days_until === 0) return tr.binary_today    || 'TODAY';
        if (r.days_until === 1) return tr.binary_tomorrow || 'TOMORROW';
        return r.date || '';
    };
    const container = document.getElementById('binary-alert-items');
    container.innerHTML = urgent.map(r => {
        const isTomorrow = r.days_until === 1;
        const lbl = dateLabel(r);
        return `
        <div class="binary-row">
            <div class="binary-date-box">
                <span class="binary-date-pill ${isTomorrow ? 'tomorrow' : ''}">${lbl}</span>
            </div>
            <div class="binary-content">
                <div class="binary-headline">${r.event}</div>
                ${r.affected_sectors?.length ? `
                <div class="binary-sector-group">
                    ${r.affected_sectors.map(s => `<span class="binary-sector-chip">${s.replace(/_/g,' ')}</span>`).join('')}
                </div>` : ''}
            </div>
        </div>`;
    }).join('');
    }


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
    container.innerHTML = themes.map((t, i) => `
        <div class="flex items-start gap-2 p-2.5 rounded-lg bg-violet-500/5 border border-violet-500/15">
            <span class="text-[9px] font-black text-violet-500 shrink-0">${String(i+1).padStart(2,'0')}</span>
            <span class="text-[10px] font-medium leading-snug" style="color:var(--text-muted)">${t.replace(/_/g,' ')}</span>
        </div>`).join('');
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
    set('three-signal-title',   tr.three_signal_title);
    set('catalyst-title',       tr.catalyst_title);
    set('divergence-title',     tr.divergence_title);
    set('themes-title',         tr.themes_title);
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
    onThemeChange: () => loadSectorData(),
});
loadSectorData();
