/**
 * page-radar.js — Tactical Opportunity Radar v0.2
 *
 * Renders data.tactical (populated by bridge.py from
 * skills/thematic-screener/data/recommendations/<latest>.json).
 *
 * v0.2 design (per user discussion 2026-04-25):
 *   - Show ALL detected themes (~20) as a grid
 *   - Each theme card: mid_heat + bullish_breadth_pct + avg_conviction
 *   - Click theme card → expand top 5 movers panel below
 *   - Sort by short_term bullish_breadth_pct (default) OR mid heat
 *   - Regime layer: 2 independent badges (RSI + VIX) + factor display
 *   - Strict §11.D display rules preserved on mover cards
 */

const t = () => (window.i18n?.[UI.currentLang]?.radar) || {};
const $ = (id) => document.getElementById(id);

// ── Term tooltip dictionary (zh + en) ─────────────────────────
const RADAR_TERMS = {
    mid_heat: {
        zh: { title: '中期熱度 (MID)', desc: 'theme-detector 算的 1-3 月主題熱度（FINVIZ 產業 momentum + volume + breadth）。', hint: '<strong>0-100</strong>，>60 熱、30-60 溫、<30 冷。反映「有沒有資金在滾這個題材」。' },
        en: { title: 'Mid-term Heat (MID)', desc: 'theme-detector\'s 1-3 month heat from FINVIZ industry momentum/volume/breadth.', hint: '<strong>0-100</strong>. >60 hot, 30-60 warm, <30 cool. "Is money flowing into this theme?"' },
    },
    short_bull: {
        zh: { title: '短期看多率', desc: '主題內 5 個 mover 中，5 日預測為「正報酬」的 % 比例。', hint: '<strong>100%</strong> = 全部 movers 預測上漲；<strong>40%</strong> = 5 個有 2 個漲。已套用 regime factor (大盤調整)。' },
        en: { title: 'Short Bullish Breadth', desc: '% of theme\'s movers with positive 5d prediction.', hint: '<strong>100%</strong> = all movers predict up; <strong>40%</strong> = 2 of 5. Adjusted by regime factor.' },
    },
    avg_conv: {
        zh: { title: '平均信心', desc: '主題內 5 個 mover 的 5 日預測信心平均（0-1）。', hint: '<strong>>0.55</strong> 高信心；<strong>0.40-0.55</strong> 中等；<strong><0.40</strong> 低（模型本身不確定）。' },
        en: { title: 'Avg Conviction', desc: 'Average 5d prediction confidence across the theme\'s movers (0-1).', hint: '<strong>>0.55</strong> high; <strong>0.40-0.55</strong> medium; <strong><0.40</strong> low (model uncertain).' },
    },
    horizon_1d: {
        zh: { title: '1 日 Horizon', desc: '預測未來 1 個交易日的 target 與 range。', hint: '主要受新聞 + overnight gap 驅動。clamp 至 ±5%。' },
        en: { title: '1-day Horizon', desc: 'Prediction for 1 trading day ahead.', hint: 'News + overnight gap dominates. Clamped to ±5%.' },
    },
    horizon_5d: {
        zh: { title: '5 日 Horizon ★', desc: '預測未來 5 個交易日的 target 與 range（**主要 horizon**）。', hint: '動能延續性 + 產業熱度主導。clamp 至 ±15%。Theme card 的 SHORT bull 用此 horizon 計算。' },
        en: { title: '5-day Horizon ★', desc: 'Prediction for 5 trading days ahead (**primary horizon**).', hint: 'Momentum persistence + sector heat dominate. Clamped to ±15%. SHORT bull metric uses this.' },
    },
    horizon_15d: {
        zh: { title: '15 日 Horizon', desc: '預測未來 15 個交易日的 target 與 range。', hint: '主題持續性主導；機構流向參與。clamp 至 ±30%。15d 信心通常較低（cap 0.6）。' },
        en: { title: '15-day Horizon', desc: 'Prediction for 15 trading days ahead.', hint: 'Theme persistence + institutional flow dominate. Clamped to ±30%. Confidence usually capped 0.6.' },
    },
    range: {
        zh: { title: '預測區間', desc: 'target_low 到 target_high — 模型預測的 ±1 個 ATR 區間。', hint: '不是停損點！只是「合理價格範圍」。停損看 trading_meta 裡的 Stop。' },
        en: { title: 'Prediction Range', desc: 'target_low to target_high — model\'s ±1 ATR confidence band.', hint: 'Not a stop! Just "reasonable price range". For stop, see trading_meta.Stop.' },
    },
    confidence: {
        zh: { title: 'Confidence (信心)', desc: '0-1 的綜合信心分數，由 7 個 component 加總而成（點開有 breakdown）。', hint: '<strong>>0.55</strong> 強訊號；<strong><0.40</strong> 模型不確定，預測值僅供參考。' },
        en: { title: 'Confidence', desc: '0-1 composite confidence (sum of 7 components — expand for breakdown).', hint: '<strong>>0.55</strong> strong signal; <strong><0.40</strong> model uncertain, low weight.' },
    },
    driver_news: {
        zh: { title: 'News Driver (新聞)', desc: 'v0.1 用 volume × gap proxy 模擬新聞催化（v0.2 將接 Finnhub /company-news）。', hint: '<strong>>0.5</strong> 強正向催化；<strong><-0.5</strong> 負向。0 = 無明顯新聞訊號。' },
        en: { title: 'News Driver', desc: 'v0.1 proxy from volume × gap (v0.2 will use Finnhub /company-news).', hint: '<strong>>0.5</strong> strong positive catalyst; <strong><-0.5</strong> negative. 0 = no signal.' },
    },
    driver_sector: {
        zh: { title: 'Sector Heat Driver', desc: '從 sector_intel cache 抓出來的當日產業熱度 (0-1 標準化)。', hint: '個股表現會被同產業熱度 boost / drag。<strong>>0.6</strong> 順風；<strong><0.4</strong> 逆風。' },
        en: { title: 'Sector Heat Driver', desc: 'Daily sector heat from sector_intel cache (0-1 normalized).', hint: 'Stock performance gets boost/drag from sector tailwind. >0.6 tailwind; <0.4 headwind.' },
    },
    driver_momentum: {
        zh: { title: 'Momentum Driver (動能)', desc: 'RSI + MA structure (MA20/MA50/MA200) 算出的 -1~+1 動能分數。', hint: 'Stage 2 趨勢 + RSI 70-85 通常 >0.5。RSI > 90 會被 dampen 至 0.3 (反彈衰竭警示)。' },
        en: { title: 'Momentum Driver', desc: 'Momentum score from RSI + MA structure (MA20/50/200), range -1 to +1.', hint: 'Stage 2 + RSI 70-85 usually >0.5. RSI > 90 dampened to 0.3 (exhaustion warning).' },
    },
    driver_atr: {
        zh: { title: 'ATR (波動度)', desc: 'Average True Range 14 日，以當前股價的 % 表示。', hint: '<strong>>5%</strong> 高波動 (Quantum/小型股) → confidence 自動降低；<strong><2%</strong> 低波動 (utility)。' },
        en: { title: 'ATR (Volatility)', desc: '14-day Average True Range as % of current price.', hint: '<strong>>5%</strong> high vol → auto-lowers confidence; <strong><2%</strong> low vol (utilities).' },
    },
    invalidation: {
        zh: { title: '失效條件', desc: '當下列任一情況觸發，這個 trade thesis 應視為失效。', hint: '<strong>建議用 alert</strong> 在 stop 點 / 條件達成時通知；不要被動持有期待反彈。' },
        en: { title: 'Invalidation', desc: 'Conditions that invalidate this trade thesis.', hint: '<strong>Set alerts</strong> at stop / condition trigger; don\'t hold passively hoping.' },
    },
    concentration: {
        zh: { title: '同主題集中警示', desc: '這個 mover 的同主題還有 N 檔被推薦。', hint: '同主題股票相關性高，如果一起加碼 = 隱性放大同類風險。可以選 1 檔或分散到不同主題。' },
        en: { title: 'Concentration Warning', desc: 'Other movers from the same theme also recommended.', hint: 'Same-theme stocks have high correlation. Buying multiple = amplified exposure. Pick 1 or diversify.' },
    },
    trading_stop: {
        zh: { title: '停損 (Stop)', desc: '建議停損價 = 當前價 - 1.5 × ATR。', hint: '<strong>機械式停損</strong>，不要往下移。低信心 trade 可考慮更緊（1 ATR）。' },
        en: { title: 'Stop Loss', desc: 'Suggested stop = current - 1.5 × ATR.', hint: '<strong>Mechanical stop</strong>, do not move down. Low-conviction trades may use tighter (1 ATR).' },
    },
    trading_pos: {
        zh: { title: '建議倉位 %', desc: '依 0.33/ATR% 公式計算（cap 0.5%-5%），假設你接受每筆 0.5% 投組風險。', hint: '高 ATR 股 → 較小倉位；低 ATR 股 → 較大倉位。如果你風險容忍不同，按比例調整。' },
        en: { title: 'Position Size %', desc: '0.33/ATR% formula (cap 0.5-5%), assumes 0.5% portfolio risk per trade.', hint: 'High ATR → smaller position; Low ATR → larger. Scale linearly to your risk tolerance.' },
    },
    trading_tx: {
        zh: { title: '交易成本估算', desc: '單向手續費 + spread 估算 (來回約 0.05% for liquid US 股)。', hint: '5 日預測幅度 < tx cost 的 trade 不值得做。' },
        en: { title: 'Tx Cost Estimate', desc: 'One-way fee + spread (~0.05% round-trip for liquid US stocks).', hint: 'Skip trades where 5d prediction < tx cost.' },
    },
    trading_exit: {
        zh: { title: '出場觸發', desc: '達到下列任一條件就考慮出場。', hint: '5 日 target 達成 = 部分停利；confidence 降至 < 0.4 = 模型對這 trade 已沒主見。' },
        en: { title: 'Exit Trigger', desc: 'Conditions to consider exiting.', hint: '5d target hit = partial profit; confidence < 0.4 = model lost conviction.' },
    },
    fred_regime: {
        zh: { title: 'FRED 經濟體制', desc: 'FRED macro 訊號合成的 regime label。', hint: '<strong>Expansion (擴張)</strong> = 殖利率正常 + 信用利差低；<strong>Caution (警戒)</strong> = 任一風險指標亮起。' },
        en: { title: 'FRED Macro Regime', desc: 'Composite regime label from FRED macro signals.', hint: '<strong>Expansion</strong> = normal yield curve + low credit spread; <strong>Caution</strong> = any risk lit up.' },
    },
    factor: {
        zh: { title: 'Regime Factor (大盤調整係數)', desc: '依 SPY RSI 與 VIX 計算的 dampen/amplify 係數。', hint: '<strong>< 1.0</strong> 大盤過熱/恐慌 → 自動降所有 bullish_breadth；<strong>> 1.0</strong> 反彈機會 → amplify。1.0 = 正常。' },
        en: { title: 'Regime Factor', desc: 'Dampen/amplify factor derived from SPY RSI + VIX.', hint: '<strong><1.0</strong> overbought/panic → reduce all bullish; <strong>>1.0</strong> rebound opportunity. 1.0 = normal.' },
    },
    spy_rsi: {
        zh: { title: 'SPY RSI 14', desc: 'S&P 500 14 日相對強弱指標。', hint: '<strong>>85</strong> 極端超買；<strong>30-70</strong> 正常；<strong><25</strong> 極端超賣（contrarian buy 機會）。' },
        en: { title: 'SPY RSI 14', desc: 'S&P 500 14-day RSI.', hint: '<strong>>85</strong> extreme overbought; <strong>30-70</strong> normal; <strong><25</strong> extreme oversold.' },
    },
    vix: {
        zh: { title: 'VIX (恐慌指數)', desc: 'CBOE 隱含波動率指數。', hint: '<strong><13</strong> 過度自滿；<strong>15-20</strong> 正常；<strong>>25</strong> 緊張；<strong>>40</strong> 投降底。' },
        en: { title: 'VIX (Fear Index)', desc: 'CBOE implied volatility index.', hint: '<strong><13</strong> complacency; <strong>15-20</strong> normal; <strong>>25</strong> tension; <strong>>40</strong> capitulation.' },
    },
    yield_curve: {
        zh: { title: '殖利率曲線 T10Y2Y', desc: '10 年公債殖利率 - 2 年公債殖利率（%）。', hint: '<strong>負值 (倒掛)</strong> = 12-18 個月衰退預警；<strong>>1.0</strong> = 健康陡峭。' },
        en: { title: 'Yield Curve T10Y2Y', desc: '10Y minus 2Y Treasury yield (%).', hint: '<strong>Negative (inverted)</strong> = 12-18m recession warning; <strong>>1.0</strong> = healthy steepness.' },
    },
    credit_spread: {
        zh: { title: '信用利差百分位 (1Y)', desc: '高收益債利差在過去 1 年的百分位。', hint: '<strong>>75</strong> 信用市場緊縮 (risk-off 警示)；<strong><30</strong> 寬鬆。' },
        en: { title: 'Credit Spread Percentile', desc: 'High-yield credit spread vs past year percentile.', hint: '<strong>>75</strong> credit stress (risk-off); <strong><30</strong> easy money.' },
    },
};

function getTermTip(key) {
    const lang = UI.currentLang === 'en' ? 'en' : 'zh';
    return RADAR_TERMS[key]?.[lang] || null;
}

// Tooltip element handler (mirrors momentum's mom-pill-tooltip pattern)
let _radarHideTimer = null;
function showRadarTip(el) {
    const tip = $('radar-term-tooltip');
    if (!tip) return;
    const key = el.dataset.radarTip;
    const entry = getTermTip(key);
    if (!entry) return;
    tip.innerHTML = `
        <div class="rtt-title">${escapeHtml(entry.title)}</div>
        <div class="rtt-desc">${entry.desc}</div>
        <div class="rtt-hint">${entry.hint}</div>
    `;
    tip.style.opacity = '0';
    tip.style.top = '-9999px';
    tip.classList.add('visible');
    requestAnimationFrame(() => {
        const rect = el.getBoundingClientRect();
        const tRect = tip.getBoundingClientRect();
        const gap = 8;
        let top = rect.top - tRect.height - gap;
        if (top < 8) top = rect.bottom + gap;
        let left = rect.left + (rect.width - tRect.width) / 2;
        left = Math.max(8, Math.min(left, window.innerWidth - tRect.width - 8));
        tip.style.top = top + 'px';
        tip.style.left = left + 'px';
        tip.style.opacity = '';
    });
}
function hideRadarTip() {
    const tip = $('radar-term-tooltip');
    if (tip) tip.classList.remove('visible');
}

// ── Map helpers (English data → localized string) ─────────────
function mapVal(mapName, key, fallback) {
    if (!key) return fallback ?? '—';
    const m = (t()[mapName]) || {};
    return m[key] || fallback || key;
}
const tThemeName = (k) => mapVal('theme_names', k, k);
const tLifecycle = (k) => mapVal('lifecycle_map', k, k);
const tHeatLabel = (k) => mapVal('heat_label_map', k, k);
const tConfLabel = (k) => mapVal('conf_map', k, k);
const tFredRegime = (k) => mapVal('fred_regime_map', k, k);
const tMaStatus = (k) => mapVal('ma_status_map', k, k);

let _currentSort = 'short';     // 'short' or 'mid'
let _currentHorizon = '5d';     // '1d' | '5d' | '15d' — which horizon's breadth/conv to display
let _expandedTheme = null;
let _lastData = null;

// ── Render entry ──────────────────────────────────────────────
function render(data) {
    const tac = data?.tactical;
    _lastData = tac;
    if (!tac || tac.status !== 'success' || !tac.themes?.length) {
        $('radar-no-data')?.classList.remove('hidden');
        $('radar-regime-banner')?.classList.add('hidden');
        $('radar-no-data-text').textContent = t().no_data || '尚無 tactical 推薦';
        return;
    }
    $('radar-no-data')?.classList.add('hidden');

    renderHeader(tac);
    renderRegimeBanner(tac);
    renderRegimeBadges(tac);
    renderThemeGrid(tac);
    if (_expandedTheme) renderExpanded(_expandedTheme, tac);

    if (window.lucide?.createIcons) window.lucide.createIcons();
}

// ── Header ────────────────────────────────────────────────────
function renderHeader(tac) {
    $('radar-title').textContent = t().title || '短期雷達';
    $('radar-experimental-text').textContent = t().experimental || 'EXPERIMENTAL';
    if (tac.as_of) {
        const dt = new Date(tac.as_of);
        $('radar-as-of').textContent = `${UI.currentLang === 'zh' ? '更新' : 'as_of'} ${dt.getMonth()+1}/${dt.getDate()} ${String(dt.getHours()).padStart(2,'0')}:${String(dt.getMinutes()).padStart(2,'0')}`;
    }
    if (tac._total_log_days != null) {
        $('radar-log-days').textContent = `${t().log_days || 'Log Days'}: ${tac._total_log_days}`;
    }
    // Sort + Horizon toggle labels
    const sortLbl = $('radar-sort-label');
    if (sortLbl) sortLbl.textContent = (t().sort_label || 'Sort') + ':';
    const horizonLbl = $('radar-horizon-label');
    if (horizonLbl) horizonLbl.textContent = (t().horizon_label || 'Horizon') + ':';
    $('sort-by-short').textContent = t().sort_short || 'Short';
    $('sort-by-mid').textContent = t().sort_mid || 'Mid';
}

// ── Regime banner (existing FRED + market) ────────────────────
function renderRegimeBanner(tac) {
    const banner = $('radar-regime-banner');
    if (!banner) return;
    const r = tac.regime_snapshot || {};
    const factor = (tac.regime_factor && tac.regime_factor.factor) ?? 1.0;

    const pillEl = $('radar-regime-pill');
    const fredLabel = r.fred_regime_label || 'unknown';
    const cls = fredLabel === 'expansion' ? 'risk-on' : fredLabel === 'caution' ? 'caution' : '';
    pillEl.className = `regime-pill ${cls}`;
    pillEl.textContent = tFredRegime(fredLabel);
    // Update label-text label for the regime pill
    const lbl = $('radar-regime-label-text');
    if (lbl) lbl.textContent = t().regime_label || '市場環境';
    // Factor label prefix
    const factorMetricSpan = $('radar-factor')?.parentElement;
    if (factorMetricSpan) {
        const labelNode = factorMetricSpan.childNodes[0];
        if (labelNode && labelNode.nodeType === Node.TEXT_NODE) {
            labelNode.textContent = (t().factor_label || 'Factor') + ' ';
        }
    }

    $('radar-spy').textContent = r.spy_close != null ? `$${r.spy_close.toFixed(2)}` : '—';
    $('radar-rsi').textContent = r.spy_rsi_14 != null ? r.spy_rsi_14.toFixed(1) : '—';
    $('radar-vix').textContent = r.vix != null ? r.vix.toFixed(2) : '—';
    $('radar-yc').textContent = r.yield_curve_t10y2y != null ? r.yield_curve_t10y2y.toFixed(2) : '—';
    $('radar-credit').textContent = r.credit_spread_pctile_1y != null ? r.credit_spread_pctile_1y : '—';

    const factorEl = $('radar-factor');
    factorEl.textContent = factor.toFixed(2) + 'x';
    if (factor < 1.0) factorEl.style.color = '#fbbf24';
    else if (factor > 1.0) factorEl.style.color = '#22c55e';
    else factorEl.style.color = 'var(--text-main)';

    banner.classList.remove('hidden');
}

// ── Regime badges (RSI + VIX independent) ─────────────────────
function renderRegimeBadges(tac) {
    const wrap = $('radar-regime-badges');
    if (!wrap) return;
    wrap.innerHTML = '';
    const badges = tac.regime_badges || {};
    const useEn = (UI.currentLang === 'en');

    ['rsi', 'vix'].forEach(kind => {
        const b = badges[kind];
        if (!b) return;
        let cls = 'caution';
        if (b.level && (b.level.includes('oversold') || b.level.includes('capitulation'))) cls = 'risk-on';
        const msg = useEn ? (b.msg_en || b.msg) : b.msg;
        const alertText = (kind === 'rsi') ? (t().rsi_alert || 'RSI ALERT') : (t().vix_alert || 'VIX ALERT');
        const div = document.createElement('div');
        div.className = `regime-banner`;
        div.style.borderColor = (cls === 'risk-on') ? 'rgba(34,197,94,0.35)' : 'rgba(251,191,36,0.35)';
        div.style.background = (cls === 'risk-on') ? 'rgba(34,197,94,0.08)' : 'rgba(251,191,36,0.08)';
        div.innerHTML = `
            <span class="text-[10px] font-bold uppercase tracking-widest" style="color: ${cls === 'risk-on' ? '#22c55e' : '#fbbf24'}">${escapeHtml(alertText)}</span>
            <span class="text-[12px]">${escapeHtml(msg)}</span>
        `;
        wrap.appendChild(div);
    });
}

// ── Theme grid (all themes) ───────────────────────────────────
function renderThemeGrid(tac) {
    const grid = $('radar-theme-grid');
    if (!grid) return;
    grid.innerHTML = '';

    let themes = [...(tac.themes || [])];
    // Per-theme horizon-specific breadth & conviction (uses _currentHorizon)
    const getH = (theme) => (theme.short_term?.by_horizon || {})[_currentHorizon] || {};

    // Sort
    themes.sort((a, b) => {
        if (_currentSort === 'mid') {
            return (b.mid_heat || 0) - (a.mid_heat || 0);
        }
        return ((getH(b).bullish_breadth_pct ?? -1) - (getH(a).bullish_breadth_pct ?? -1));
    });

    const themesLabel = (UI.currentLang === 'zh') ? '個主題' : 'themes';
    $('radar-theme-count').textContent = `${themes.length} ${themesLabel}  ·  ${_currentHorizon} view`;
    $('radar-themes-section-title').textContent = t().themes_section || 'All Themes';

    themes.forEach(theme => {
        const st = theme.short_term || {};
        const horizonView = getH(theme);
        const bp = horizonView.bullish_breadth_pct;
        const cv = horizonView.avg_conviction;
        const nValid = horizonView.n_valid_predictions ?? 0;
        const nBullish = horizonView.n_bullish ?? 0;
        const nTotal = st.n_total_constituents ?? 0;
        const mid = theme.mid_heat || 0;
        const isExpanded = (_expandedTheme === theme.name);

        const heatTier = mid >= 60 ? 'hot' : mid >= 30 ? 'warm' : 'cool';

        const card = document.createElement('div');
        card.className = `theme-card-radar glass-card p-3 ${isExpanded ? 'expanded' : ''}`;
        card.dataset.themeName = theme.name;
        // Border color shows mid_heat tier: red=hot, light-blue=cool, default=warm
        if (heatTier === 'hot') {
            card.style.borderColor = 'rgba(239, 68, 68, 0.55)';     // warm red
            card.style.boxShadow = '0 0 0 1px rgba(239, 68, 68, 0.10) inset';
        } else if (heatTier === 'cool') {
            card.style.borderColor = 'rgba(96, 165, 250, 0.45)';    // light blue (sky-400)
            card.style.boxShadow = '0 0 0 1px rgba(96, 165, 250, 0.08) inset';
        }
        // 'warm' tier uses default glass-card border
        // Tooltip with full localized info (heat_label + lifecycle + confidence)
        const tipParts = [tThemeName(theme.name)];
        if (theme.heat_label) tipParts.push(tHeatLabel(theme.heat_label));
        if (theme.lifecycle_stage) tipParts.push(tLifecycle(theme.lifecycle_stage));
        if (theme.confidence) tipParts.push(`${t().confidence || 'conf'}: ${tConfLabel(theme.confidence)}`);
        card.title = tipParts.join(' · ');

        const bpStr = bp != null ? `${bp.toFixed(0)}%` : '—';
        const bpColor = bp == null ? 'text-zinc-500' :
                        bp >= 80 ? 'text-emerald-400' :
                        bp >= 50 ? 'text-yellow-400' :
                        bp >= 30 ? 'text-orange-400' :
                        'text-red-400';

        const cvStr = cv != null ? cv.toFixed(2) : '—';
        const displayName = tThemeName(theme.name);

        // Sort indicator: arrow only (no row background highlight per user request)
        const midSortInd = (_currentSort === 'mid') ? '<span class="text-indigo-400 ml-1">↓</span>' : '';
        const shortSortInd = (_currentSort === 'short') ? '<span class="text-indigo-400 ml-1">↓</span>' : '';
        // MID row keeps faint sort highlight (so mid heat is discoverable as sort target);
        // SHORT bull row never highlights — too noisy on the headline metric.
        const midRowCls = (_currentSort === 'mid') ? 'metric-row sorting-by' : 'metric-row';
        const shortRowCls = 'metric-row';

        card.innerHTML = `
            <div class="font-bold text-[12px] leading-tight mb-1 truncate">${escapeHtml(displayName)}</div>

            <div class="flex items-center gap-1 mb-1 ${midRowCls}" data-radar-tip="mid_heat">
                <span class="text-[8px] font-bold uppercase text-zinc-500 w-8">${escapeHtml(t().card_mid || 'MID')}${midSortInd}</span>
                <div class="heat-bar flex-1"><div style="width: ${Math.min(100, mid)}%;"></div></div>
                <span class="text-[10px] font-mono w-7 text-right">${mid.toFixed(0)}</span>
            </div>

            <div class="flex items-center justify-between text-[10px] mt-2 ${shortRowCls}" data-radar-tip="short_bull">
                <span class="text-zinc-500">${escapeHtml(t().card_short_bull || 'SHORT bull')} <span class="text-zinc-600">[${_currentHorizon}]</span>${shortSortInd}</span>
                <span class="${bpColor} font-mono font-bold">${bpStr}${nValid > 0 ? `<span class="text-[9px] text-zinc-600 ml-1">${nBullish}/${nValid}</span>` : ''}</span>
            </div>

            <div class="flex items-center justify-between text-[10px] metric-row" data-radar-tip="avg_conv">
                <span class="text-zinc-500">${escapeHtml(t().card_conv || 'conv')} <span class="text-zinc-600">[${_currentHorizon}]</span></span>
                <span class="font-mono">${cvStr}</span>
            </div>

            <div class="flex items-center justify-between text-[9px] text-zinc-600 mt-0.5">
                <span>${UI.currentLang === 'zh' ? '主題股數' : 'constituents'}: ${nTotal}</span>
            </div>

            <div class="flex items-center justify-end text-[9px] mt-1 pt-1 border-t border-zinc-800/50">
                <span class="text-indigo-400">${escapeHtml(isExpanded ? (t().card_movers_close || '▲ close') : (t().card_movers_open || '▼ movers'))}</span>
            </div>
        `;
        card.addEventListener('click', () => toggleExpand(theme.name));
        grid.appendChild(card);
    });
}

// ── Expand / collapse one theme ───────────────────────────────
function toggleExpand(themeName) {
    if (_expandedTheme === themeName) {
        _expandedTheme = null;
        $('radar-expanded-section').classList.add('hidden');
    } else {
        _expandedTheme = themeName;
        renderExpanded(themeName, _lastData);
        $('radar-expanded-section').classList.remove('hidden');
        // Scroll into view
        $('radar-expanded-section').scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }
    renderThemeGrid(_lastData);
    if (window.lucide?.createIcons) window.lucide.createIcons();
}

function renderExpanded(themeName, tac) {
    const theme = (tac.themes || []).find(th => th.name === themeName);
    if (!theme) return;
    $('radar-expanded-theme-name').textContent = tThemeName(theme.name);
    const suffix = $('radar-expanded-suffix');
    if (suffix) suffix.textContent = t().expanded_top_movers || 'Top Movers';
    // Update close button text
    const closeBtn = $('radar-expanded-close');
    if (closeBtn) {
        const txt = closeBtn.querySelector('span');
        if (txt) txt.textContent = t().close || 'close';
    }
    const wrap = $('radar-expanded-movers');
    const noMovers = UI.currentLang === 'zh' ? '無 movers' : 'No movers found.';
    wrap.innerHTML = (theme.top_movers || []).map(m => renderMoverCard(m)).join('') ||
        `<div class="text-zinc-500 text-sm">${noMovers}</div>`;
    if (window.lucide?.createIcons) window.lucide.createIcons();
}

// ── Per-mover card (strict §11.D) ─────────────────────────────
function renderMoverCard(mover) {
    const ticker = mover.ticker || '?';
    const st = mover.short_term || {};

    if (st.error) {
        return `
            <div class="glass-card p-3 border border-red-500/20" style="background: rgba(239,68,68,0.05)">
                <div class="flex items-center justify-between">
                    <div class="font-bold">${escapeHtml(ticker)}</div>
                    <span class="insufficient-pill" style="background: rgba(239,68,68,0.15); color:#ef4444">${escapeHtml(t().pred_failed || 'Prediction Failed')}</span>
                </div>
                <div class="text-[10px] text-zinc-500 mt-1">${escapeHtml(st.error || '')}</div>
            </div>`;
    }

    const horizons = st.horizons || {};
    const h5 = horizons['5d'] || {};
    const tm = st.trading_meta || {};
    const cf = mover.concentration_flag;
    const current = st.current_price;

    return `
        <div class="glass-card p-3 space-y-3 mover-card-radar">
            <div class="flex items-center justify-between">
                <div>
                    <div class="font-bold text-base">${escapeHtml(ticker)}</div>
                    <div class="text-[10px] text-zinc-500 font-mono">${current != null ? '$' + current.toFixed(2) : '—'}</div>
                </div>
                <div class="flex items-center gap-2">
                    ${st.weights_version ? `<span class="text-[9px] font-mono text-zinc-600">${escapeHtml(st.weights_version)}</span>` : ''}
                    <button class="analyze-ticker-btn" data-ticker="${escapeHtml(ticker)}" title="${escapeHtml(UI.currentLang === 'zh' ? '深度分析（投資協議 V4.8.1，~10-15 分鐘）' : 'Deep analyze (investment_protocol V4.8.1, ~10-15 min)')}">
                        <i data-lucide="search" class="w-3 h-3"></i>
                        <span>${escapeHtml(UI.currentLang === 'zh' ? '分析' : 'Analyze')}</span>
                    </button>
                </div>
            </div>

            <div class="horizon-bar">
                ${renderHorizon('1d', horizons['1d'], false)}
                ${renderHorizon('5d', horizons['5d'], false)}
                ${renderHorizon('15d', horizons['15d'], false)}
            </div>

            ${h5.status === 'ok' ? `
                <div>
                    <div class="text-[9px] font-bold uppercase tracking-widest text-zinc-500 mb-1">${escapeHtml(t().drivers || 'Drivers')}</div>
                    <div class="space-y-1">
                        ${renderDriverRow(t().driver_news || 'News', h5.drivers?.news_score, h5.driver_labels?.news, false, 'driver_news')}
                        ${renderDriverRow(t().driver_sector || 'Sector', h5.drivers?.sector_heat, h5.driver_labels?.sector_status, false, 'driver_sector')}
                        ${renderDriverRow(t().driver_momentum || 'Momentum', h5.drivers?.momentum_score, h5.driver_labels?.momentum, false, 'driver_momentum')}
                        ${renderDriverRow(t().driver_atr || 'ATR', h5.drivers?.atr_pct, '%', true, 'driver_atr')}
                    </div>
                </div>

                <details class="text-[10px]">
                    <summary class="cursor-pointer text-zinc-500 hover:text-zinc-300">
                        ${escapeHtml(t().confidence || 'Confidence')}: <strong>${(h5.confidence ?? 0).toFixed(2)}</strong>
                    </summary>
                    <div class="confidence-breakdown mt-2 pt-2 border-t border-zinc-800">
                        ${renderBreakdown(h5.confidence_breakdown || {})}
                    </div>
                </details>

                ${st.invalidation ? `
                    <div class="invalidation-box" data-radar-tip="invalidation">
                        <div class="text-[9px] font-bold uppercase tracking-wider text-red-400 mb-1">⚠ ${escapeHtml(t().invalidation || 'Invalidation')}</div>
                        ${escapeHtml(UI.currentLang === 'zh' && st.invalidation_zh ? st.invalidation_zh : st.invalidation)}
                    </div>
                ` : ''}

                ${cf ? `
                    <div class="concentration-warning" data-radar-tip="concentration">
                        <div class="text-[9px] font-bold uppercase tracking-wider text-orange-400 mb-1">🟠 ${escapeHtml(t().concentration || 'Concentration')}</div>
                        ${UI.currentLang === 'zh'
                            ? `主題「${escapeHtml(tThemeName(cf.theme))}」共有 ${(cf.co_recommendations || []).length + 1} 檔同主題推薦，注意同類回檔風險`
                            : escapeHtml(cf.warning || '')}
                        ${cf.co_recommendations?.length ? `<div class="mt-1 font-mono text-[10px] text-zinc-400">${UI.currentLang === 'zh' ? '同主題：' : 'co-recs:'} ${cf.co_recommendations.join(', ')}</div>` : ''}
                    </div>
                ` : ''}

                ${tm && !tm.insufficient_data ? (() => {
                    const dir = (h5.target_central_pct ?? 0) > 0 ? 'bull' : (h5.target_central_pct ?? 0) < 0 ? 'bear' : 'flat';
                    const dirColor = dir === 'bull' ? '#22c55e' : dir === 'bear' ? '#ef4444' : '#a1a1aa';
                    const targetVal = h5.target_central ?? 0;
                    const horizonNote = UI.currentLang === 'zh'
                        ? 'Drivers / Target / Stop 基於 5d 計算（primary horizon）'
                        : 'Drivers / Target / Stop based on 5d horizon (primary)';
                    return `
                    <div class="text-[10px] text-zinc-500 pt-2 border-t border-zinc-800">
                        <div class="font-bold uppercase tracking-wider mb-1">💼 ${escapeHtml(t().trading_meta || 'Trading')}</div>
                        <div class="grid grid-cols-2 gap-x-3 gap-y-1 font-mono">
                            <div data-radar-tip="trading_stop">${t().stop_loss || 'Stop'}: <span style="color:#ef4444; font-weight:700">$${(tm.stop_suggestion ?? 0).toFixed(2)}</span></div>
                            <div>${UI.currentLang === 'zh' ? '目標' : 'Target'}: <span style="color:${dirColor}; font-weight:700">$${targetVal.toFixed(2)}</span></div>
                            <div data-radar-tip="trading_pos">${t().pos_size_hint || 'Pos'}: <span class="text-zinc-200">${(tm.position_size_hint_pct ?? 0).toFixed(1)}%</span></div>
                            <div data-radar-tip="trading_tx">${t().tx_cost || 'Tx'}: <span class="text-zinc-200">${(tm.tx_cost_estimate_pct ?? 0).toFixed(2)}%</span></div>
                            <div class="col-span-2" data-radar-tip="trading_exit">${t().exit_trigger || 'Exit'}: <span class="text-zinc-400 truncate">${escapeHtml(((UI.currentLang === 'zh' && tm.exit_trigger_zh) ? tm.exit_trigger_zh : (tm.exit_trigger || '')).slice(0, 80))}…</span></div>
                        </div>
                        <div class="mt-2 pt-1 border-t border-zinc-800/50 text-[9px] text-zinc-600 italic">${escapeHtml(horizonNote)}</div>
                    </div>
                    `;
                })() : ''}
            ` : `
                <div class="text-[11px] text-zinc-500">
                    <span class="insufficient-pill">${escapeHtml(t().insufficient_data || 'Insufficient Data')}</span>
                    ${(h5.missing||[]).length ? `<div class="mt-1 text-[10px]">missing: ${h5.missing.join(', ')}</div>` : ''}
                </div>
            `}
        </div>
    `;
}

function renderHorizon(label, h, isPrimary) {
    if (!h || h.status !== 'ok') {
        return `
            <div class="h-cell">
                <div class="h-label">${label}</div>
                <div class="text-[10px] text-zinc-600">—</div>
            </div>`;
    }
    const conf = h.confidence ?? 0;
    const confCls = conf >= 0.55 ? 'h-conf-high' : conf >= 0.4 ? 'h-conf-med' : 'h-conf-low';
    const pct = h.target_central_pct ?? 0;
    const pctCls = pct > 0 ? 'text-emerald-400' : pct < 0 ? 'text-red-400' : 'text-zinc-400';
    const rangeLabel = (UI.currentLang === 'zh') ? '區間' : 'range';
    const tipKey = label.startsWith('1d') ? 'horizon_1d' :
                   label.startsWith('5d') ? 'horizon_5d' :
                   label.startsWith('15d') ? 'horizon_15d' : 'horizon_5d';
    return `
        <div class="h-cell ${isPrimary ? 'primary' : ''}" data-radar-tip="${tipKey}">
            <div class="h-label">${label}</div>
            <div class="h-mid ${pctCls}">${pct >= 0 ? '+' : ''}${pct.toFixed(2)}%</div>
            <div class="h-range" data-radar-tip="range">${rangeLabel} $${(h.target_low ?? 0).toFixed(2)} – $${(h.target_high ?? 0).toFixed(2)}</div>
            <span class="h-conf ${confCls}" data-radar-tip="confidence">${conf.toFixed(2)}</span>
        </div>
    `;
}

function renderDriverRow(label, value, hint, isPct, tipKey) {
    if (value == null) return '';
    const v = isPct ? `${value.toFixed(2)}%` : (typeof value === 'number' ? value.toFixed(2) : value);
    const tipAttr = tipKey ? `data-radar-tip="${tipKey}"` : '';
    return `
        <div class="driver-row" ${tipAttr}>
            <span class="d-label">${escapeHtml(label)}</span>
            <span class="d-value">${v}${hint ? `<span class="text-zinc-600 font-normal ml-1">(${escapeHtml(hint)})</span>` : ''}</span>
        </div>
    `;
}

function renderBreakdown(b) {
    const order = ['base', 'news_freshness', 'sector_heat_persistence', 'atr_penalty', 'horizon_penalty', 'data_completeness_bonus', 'model_clamped_penalty'];
    return order.map(k => {
        if (b[k] == null) return '';
        const v = b[k];
        const cls = v > 0.001 ? 'pos' : v < -0.001 ? 'neg' : 'zero';
        const sign = v > 0 ? '+' : '';
        return `
            <div class="cb-label">${k.replace(/_/g, ' ')}</div>
            <div class="cb-value ${cls}">${sign}${v.toFixed(3)}</div>
        `;
    }).join('');
}

function escapeHtml(s) {
    if (s == null) return '';
    return String(s).replace(/[&<>"']/g, m => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[m]));
}

// ── Trigger investment_protocol analysis on a ticker ──────────
async function analyzeTicker(ticker) {
    const isZh = UI.currentLang === 'zh';
    const risk = (UI && UI.riskTolerance) || 'MEDIUM';
    const msg = isZh
        ? `加入個股分析佇列：${ticker}（risk=${risk}）？\nV4.8.1 每檔約 10-15 分鐘，~$4 tokens。重複請求會被忽略。`
        : `Enqueue invest analysis for ${ticker} (risk=${risk})?\nV4.8.1 ~10-15 min, ~$4 tokens. Duplicates ignored.`;
    if (!confirm(msg)) return;
    if (window.AnalyzeQueue) {
        await window.AnalyzeQueue.enqueue(ticker);
    } else {
        try {
            const res = await fetch('/api/run-protocol', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ name: 'invest', ticker: ticker.toUpperCase(), risk_tolerance: risk }),
            });
            if (!res.ok) throw new Error((await res.json().catch(() => ({}))).error || `HTTP ${res.status}`);
            UI.showToast?.(`Queued: ${ticker}`, 'success');
        } catch (e) {
            UI.showToast?.(e.message, 'error') || alert(e.message);
        }
    }
}

// ── Sort toggle ───────────────────────────────────────────────
function setSortMode(mode) {
    _currentSort = mode;
    [$('sort-by-short'), $('sort-by-mid')].forEach(b => b?.classList.remove('active'));
    $(`sort-by-${mode}`).classList.add('active');
    if (_lastData) renderThemeGrid(_lastData);
}

function setHorizon(h) {
    _currentHorizon = h;
    [$('horizon-1d'), $('horizon-5d'), $('horizon-15d')].forEach(b => b?.classList.remove('active'));
    $(`horizon-${h}`)?.classList.add('active');
    if (_lastData) renderThemeGrid(_lastData);
}

// ── Page-level translate (called by UI.boot on lang change) ────
function translate() {
    if (window.DataStore) DataStore.get().then(render).catch(()=>{});
}

function reload() {
    if (window.DataStore) DataStore.refresh?.();
}

// ── Boot ──────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
    UI.boot('radar', { translate, reload });

    $('sort-by-short').addEventListener('click', () => setSortMode('short'));
    $('sort-by-mid').addEventListener('click', () => setSortMode('mid'));
    $('horizon-1d').addEventListener('click',  () => setHorizon('1d'));
    $('horizon-5d').addEventListener('click',  () => setHorizon('5d'));
    $('horizon-15d').addEventListener('click', () => setHorizon('15d'));

    // Tooltip hover handler
    document.addEventListener('mouseover', e => {
        const el = e.target.closest('[data-radar-tip]');
        if (!el) return;
        if (_radarHideTimer) { clearTimeout(_radarHideTimer); _radarHideTimer = null; }
        showRadarTip(el);
    });
    document.addEventListener('mouseout', e => {
        const el = e.target.closest('[data-radar-tip]');
        if (!el) return;
        _radarHideTimer = setTimeout(hideRadarTip, 80);
    });

    // Analyze button click delegation (mover cards rendered dynamically)
    document.addEventListener('click', e => {
        const btn = e.target.closest('.analyze-ticker-btn');
        if (!btn) return;
        e.stopPropagation();
        const ticker = btn.dataset.ticker;
        if (ticker) analyzeTicker(ticker);
    });
    $('radar-expanded-close').addEventListener('click', () => {
        _expandedTheme = null;
        $('radar-expanded-section').classList.add('hidden');
        if (_lastData) renderThemeGrid(_lastData);
    });

    if (window.DataStore) {
        DataStore.subscribe(render);
        DataStore.get().catch(err => console.error('Radar data load failed:', err));
    } else {
        fetch('data.json?t=' + Date.now())
            .then(r => r.json())
            .then(render)
            .catch(err => console.error('Radar data load failed:', err));
    }
});
