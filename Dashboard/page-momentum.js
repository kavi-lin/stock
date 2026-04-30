/**
 * page-momentum.js — Momentum Screener page presenter
 * Depends on: utils.js (window.UI), i18n.js, data-store.js, Chart.js
 */

const t = () => (window.i18n?.[UI.currentLang]?.momentum) || {};

// Translation helpers — fall back to human-readable English if key is missing
// from the map so new signals don't render as blank.
function sigLabel(key) {
    return t().signals_map?.[key] || key.replace(/_/g, ' ');
}
function warnLabel(key) {
    return t().warnings_map?.[key] || key.replace(/_/g, ' ');
}
function stageLabel(key) {
    return t().stages_map?.[key] || key || '—';
}
function labelText(key) {
    return t().labels_map?.[key] || key || '—';
}

// ── Signal / warning descriptions for pill hover tooltip ─────────────────
// Each entry: {desc, hint} — desc = what the signal *means*, hint = actionable
// context ("what to do with it"). Designed to replace the browser-native
// title= tooltip which just showed the raw key name.
const SIG_DESC_ZH = {
    stage2_uptrend_intact:       { desc: '完整上升結構成立：MA20 > MA50 > MA200 且價格站上 MA20。技術面最健康的狀態。', hint: '趨勢跟隨派首選；回檔至 MA20 / MA50 可加碼。' },
    fresh_golden_cross_20_50:    { desc: '過去 10 個交易日內 MA20 向上穿越 MA50。短期動能轉強訊號。', hint: '搭配量增 + Stage 2 最有效；單獨出現訊號強度有限。' },
    fresh_golden_cross_50_200:   { desc: '過去 10 個交易日內 MA50 向上穿越 MA200。多頭市場大黃金交叉，結構級轉多訊號。', hint: '歷史上往往是長多起點；適合中長線布局。' },
    volume_expansion:            { desc: '成交量比前 20 日均量放大 ≥ 30% 且 5 日均量 > 10 日均量。資金流入加速。', hint: '搭配價格突破或黃金交叉，可信度最高。' },
    heavy_volume_spike_today:    { desc: '今日量比 ≥ 3 倍前 20 日均量。重大資金事件（新聞 / 業績 / 機構動作）。', hint: '先看方向：上漲 = 可能續強；下跌 = 警戒出貨。' },
    low_short_interest:          { desc: '空單佔流通股比例 < 3%。市場對這檔沒有明顯看空共識。', hint: '偏中性訊息；搭配其他多頭訊號才有意義。' },
    high_short_interest:         {
        desc: '空單佔流通股比例 > 10%。市場對這檔有顯著做空壓力。**雙刃劍**：可能是軋空燃料、也可能反映真的有結構性問題。',
        tiers: [
            { dot: '🟢', label: '軋空候選', text: '基本面轉佳 / 有正面 catalyst → 空單回補引爆，短期爆發力高（搭配 squeeze_candidate 訊號最強）' },
            { dot: '🟡', label: '中性',     text: '無明確催化，純粹高空單，要看其他訊號決定方向' },
            { dot: '🟠', label: '結構性問題', text: '基本面持續惡化、營收下滑 → 空方可能是對的，硬抄底是接刀子' },
        ],
        hint: '判斷關鍵：「為什麼這麼多人放空？」如果你能找出市場錯誤的點 = 機會；找不到 = 跟著對手盤站',
    },
    squeeze_candidate:           {
        desc: '高空單（> 20%）+ 價格站上 MA20 > 5%。軋空燃料已堆疊，等 catalyst 點火。',
        tiers: [
            { dot: '🟢', label: '強訊號', text: '搭配近期正面 catalyst (財報 beat / 產業利多) → 短期爆發力高，可重押短線' },
            { dot: '🟡', label: '標準',   text: '單獨出現無 catalyst → 空單壓力存在但需等火種，可小倉位埋伏' },
            { dot: '🟠', label: '弱',     text: '價格已大漲 + 距 MA50 過遠 → 軋空可能已經發生過，後續吸引力有限' },
        ],
        hint: '此類交易**停損要緊** (1 ATR 內)，因為若 catalyst 沒出現，價格會 drift 回去；屬高 R/R 短線',
    },
    oversold_rsi:                {
        desc: 'RSI < 30 且處於 Stage 2 上升結構。強勢股的短期回檔買點。',
        tiers: [
            { dot: '🟢', label: 'Stage 2 + 量縮', text: '上升趨勢中的健康回檔（量縮回測 MA50）→ 經典 buy-the-dip，勝率高' },
            { dot: '🟡', label: 'Stage 2 + 量增', text: '回檔伴隨量增 = 可能有結構性問題，等 RSI 回 40 + 量恢復' },
            { dot: '🟠', label: 'Stage 3-4',     text: '下跌趨勢中的 oversold = 弱勢延續訊號，**不是機會**，反彈即賣' },
        ],
        hint: '**只在上升股有效**。「RSI < 30 = 買點」是新手陷阱 — 趨勢方向才是主軸',
    },
    macd_bullish_cross:          {
        desc: 'MACD 線今日向上穿越 Signal 線。動能由空轉多的確認訊號。',
        tiers: [
            { dot: '🟢', label: '零線上方', text: 'MACD > 0 處出現黃金交叉 → 強勢延續訊號，可信度最高，標準倉位' },
            { dot: '🟡', label: '零線附近', text: 'MACD ≈ 0 → 中性轉多，可分批進場、設緊停損' },
            { dot: '🟠', label: '零線下方', text: 'MACD < 0 處的反彈訊號 → 多為下跌中反彈，**不應視為趨勢轉多**，等再次穿越零軸' },
        ],
        hint: '配合 MA structure (Stage 2 必要) + 量增可信度更高；單獨 MACD 訊號雜訊很多',
    },
    macd_histogram_rising:       { desc: 'MACD 柱狀圖連續 3 日擴大。多頭動能持續加速。', hint: '最好的 follow-through 訊號；趨勢延續機率高。' },
};
const WARN_DESC_ZH = {
    overbought_rsi:              {
        desc: 'RSI > 70。短期獲利了結壓力上升，**但不一定要賣**。',
        tiers: [
            { dot: '🟢', label: '強勢股延續', text: '主升段強勢股可在 70+ 停留 2-4 週（NVDA/META 等），不要單憑 RSI 出場' },
            { dot: '🟡', label: '一般持倉',   text: '可考慮鎖部分利潤、收緊停損；回檔至 65-70 是加碼點' },
            { dot: '🟠', label: '已過熱',     text: 'RSI > 80 + 距 MA50 > 30% → 拋物線末段，**不要追高**，已持有可分批出' },
        ],
        hint: '「RSI > 70 賣出」是另一個新手陷阱。配合 trend (MA200 角度) + 量能判斷才有意義',
    },
    parabolic_blowoff_risk:      {
        desc: '價格距 MA200 > 50%。拋物線式噴出，均值回歸壓力極大。',
        tiers: [
            { dot: '🟢', label: '無短側機會', text: '純粹「不追」訊號 — 但若你**已持有**，這是重要的部分停利訊號' },
            { dot: '🟡', label: '考慮鎖利',   text: '若已持有 > 30% 獲利，建議出 1/3-1/2，剩餘 trailing stop' },
            { dot: '🔴', label: '高風險',     text: '距 MA200 > 80% 或拋物線斜率陡峭 → 隨時可能崩跌 50%+，不應該再加碼' },
        ],
        hint: '歷史 case: TSLA 2021 $1200、NVDA 2023 $500 → 都在這訊號出現後 30-50% 修正',
    },
    stage4_downtrend:            {
        desc: '空頭排列：MA20 < MA50 < MA200 且價格跌破 MA20。技術面最弱狀態。',
        tiers: [
            { dot: '🟠', label: '初期',     text: '剛進入 Stage 4，可能有反彈但下檔未止 — 可短做反彈但不長持' },
            { dot: '🔴', label: '深度下跌', text: 'MA200 持續下傾 > 1 月 → 持續走弱機率高，不應該有新進部位' },
            { dot: '🟡', label: '築底跡象', text: '價格不再破前低 + 量縮 + RSI 走高 → 觀察 Stage 1 完成再考慮，**不要搶左側**' },
        ],
        hint: '「逆勢抄底」是大部分散戶虧最多的單型；等 Stage 1 base 完成 + FTD 才是入場時機',
    },
    volume_dry_up:               { desc: '量比 < 0.7（較前 20 日均量縮減 30% 以上）。資金離場或觀望。', hint: '上升趨勢中的量縮是警訊；下跌中的量縮可能是洗盤。' },
    fresh_death_cross_20_50:     { desc: '過去 10 個交易日內 MA20 向下跌破 MA50。短期動能轉弱。', hint: '通常是 Stage 2 → 3 轉換的早期訊號，應減倉觀望。' },
    fresh_death_cross_50_200:    { desc: '過去 10 個交易日內 MA50 向下跌破 MA200。結構級轉空。', hint: '歷史上通常伴隨長空；技術派視為大型轉折點，不應硬撐。' },
    macd_bearish_cross:          { desc: 'MACD 線今日向下跌破 Signal 線。動能由多轉空的確認訊號。', hint: '零軸下方的死叉殺傷力更強；若再伴隨跌破 MA200 要格外警戒。' },
};
const SIG_DESC_EN = {
    stage2_uptrend_intact:       { desc: 'Full bullish MA stack: MA20 > MA50 > MA200 with price above MA20. The healthiest technical state.', hint: 'Prime trend-follower setup; pullbacks to MA20/MA50 are add-on points.' },
    fresh_golden_cross_20_50:    { desc: 'MA20 crossed above MA50 in the last 10 sessions. Short-term momentum strengthening.', hint: 'Most reliable when paired with volume expansion + Stage 2.' },
    fresh_golden_cross_50_200:   { desc: 'MA50 crossed above MA200 in the last 10 sessions. Structural bull-market cross.', hint: 'Historically marks long-cycle bottoms; suited for mid-to-long term.' },
    volume_expansion:            { desc: 'Volume ≥ 1.3× 20-day avg AND 5-day avg > 10-day avg. Money flow accelerating.', hint: 'Pair with breakout or golden cross for highest conviction.' },
    heavy_volume_spike_today:    { desc: 'Today volume ≥ 3× 20-day avg. Major capital event (news/earnings/institutional).', hint: 'Check direction first: up = continuation likely; down = distribution warning.' },
    low_short_interest:          { desc: 'Short interest < 3% of float. No significant bearish consensus.', hint: 'Mildly supportive; meaningful only when combined with other bull signals.' },
    high_short_interest:         {
        desc: 'Short interest > 10% of float. Notable bearish pressure. **Double-edged**: can be squeeze fuel, or reflect real structural problems.',
        tiers: [
            { dot: '🟢', label: 'Squeeze candidate', text: 'Improving fundamentals / positive catalyst → short cover ignites, high short-term explosiveness (best paired with squeeze_candidate signal)' },
            { dot: '🟡', label: 'Neutral',           text: 'No clear catalyst, just high short — direction depends on other signals' },
            { dot: '🟠', label: 'Structural problem', text: 'Fundamentals deteriorating, revenue declining → shorts likely correct, knife-catch will hurt' },
        ],
        hint: 'Key question: "Why are so many shorting?" If you can pinpoint the market\'s mistake = opportunity; if not = trading against the right side',
    },
    squeeze_candidate:           {
        desc: 'High short (>20%) + price >5% above MA20. Squeeze fuel stacked, awaiting catalyst.',
        tiers: [
            { dot: '🟢', label: 'Strong', text: 'Recent positive catalyst (earnings beat / sector tailwind) → high short-term explosiveness, can size up' },
            { dot: '🟡', label: 'Standard', text: 'No catalyst yet → short pressure exists but needs a spark, small starter position' },
            { dot: '🟠', label: 'Weak',     text: 'Already extended, far from MA50 → squeeze may have already occurred, limited upside' },
        ],
        hint: 'These trades **need tight stops** (~1 ATR) — without catalyst, price drifts back. High R/R short-term setup',
    },
    oversold_rsi:                {
        desc: 'RSI < 30 while in Stage 2 uptrend. Short-term pullback in a strong stock.',
        tiers: [
            { dot: '🟢', label: 'Stage 2 + low vol', text: 'Healthy pullback in uptrend (low-vol retest of MA50) → classic buy-the-dip, high win rate' },
            { dot: '🟡', label: 'Stage 2 + heavy vol', text: 'Pullback with rising volume = possible structural issue, wait for RSI > 40 + volume normalize' },
            { dot: '🟠', label: 'Stage 3-4',          text: 'Oversold in downtrend = weakness continuation, **not opportunity** — sell into bounces' },
        ],
        hint: '**Only valid in uptrends**. "RSI < 30 = buy" is a beginner trap — trend direction is the master variable',
    },
    macd_bullish_cross:          {
        desc: 'MACD line crossed above Signal line today. Momentum shift from bear to bull confirmed.',
        tiers: [
            { dot: '🟢', label: 'Above zero', text: 'MACD > 0 cross → strong continuation signal, highest reliability, standard size' },
            { dot: '🟡', label: 'Near zero',  text: 'MACD ≈ 0 → neutral-to-bull, scale in, tight stops' },
            { dot: '🟠', label: 'Below zero', text: 'Cross below zero = bounce within downtrend, **not a trend reversal** — wait for re-cross above zero' },
        ],
        hint: 'Pair with MA structure (Stage 2 required) + volume expansion for highest reliability; standalone MACD is noisy',
    },
    macd_histogram_rising:       { desc: 'MACD histogram rising for 3 consecutive days. Bull momentum accelerating.', hint: 'Best follow-through signal; trend-continuation probability is high.' },
};
const WARN_DESC_EN = {
    overbought_rsi:              {
        desc: 'RSI > 70. Short-term profit-taking pressure rising, **but not a sell signal alone**.',
        tiers: [
            { dot: '🟢', label: 'Strong stock continuation', text: 'Leading uptrends can hold 70+ for 2-4 weeks (NVDA, META) — don\'t exit on RSI alone' },
            { dot: '🟡', label: 'Normal hold',               text: 'Lock partial profits, tighten stops; add on pullback to 65-70' },
            { dot: '🟠', label: 'Overheated',                text: 'RSI > 80 + 30%+ above MA50 → late-stage parabolic, **don\'t chase**, scale out if held' },
        ],
        hint: '"RSI > 70 = sell" is another beginner trap. Trend angle (MA200) + volume context matters more',
    },
    parabolic_blowoff_risk:      {
        desc: 'Price > 50% above MA200. Parabolic blow-off, mean-reversion risk extreme.',
        tiers: [
            { dot: '🟢', label: 'No new long',  text: 'Pure "do not chase" signal — but if **already holding**, this is a critical partial-profit trigger' },
            { dot: '🟡', label: 'Lock profits', text: 'If holding > 30% gains, scale out 1/3-1/2, trail stop on the rest' },
            { dot: '🔴', label: 'High risk',    text: '> 80% above MA200 or steep parabolic angle → 50%+ crash possible any time, do not add' },
        ],
        hint: 'Historical cases: TSLA 2021 $1200, NVDA 2023 $500 → 30-50% drawdowns shortly after this signal fired',
    },
    stage4_downtrend:            {
        desc: 'Bearish stack: MA20 < MA50 < MA200 with price below MA20. Technically weakest state.',
        tiers: [
            { dot: '🟠', label: 'Early stage', text: 'Just entered Stage 4, bounces possible but downside not done — short bounces, don\'t hold long' },
            { dot: '🔴', label: 'Deep down',   text: 'MA200 trending down >1 month → continuation likely, no new long positions' },
            { dot: '🟡', label: 'Basing',      text: 'Higher lows + low volume + rising RSI → watch for Stage 1 completion, **don\'t buy left side**' },
        ],
        hint: '"Catching the falling knife" is the costliest retail trade. Wait for Stage 1 base + FTD before entering',
    },
    volume_dry_up:               { desc: 'Volume < 0.7× 20-day avg (≥30% drop). Money leaving or waiting.', hint: 'Dry-up in uptrend = warning; in downtrend = possibly shakeout.' },
    fresh_death_cross_20_50:     { desc: 'MA20 crossed below MA50 in last 10 sessions. Short-term momentum weakening.', hint: 'Usually the early signal of Stage 2→3 transition; reduce exposure.' },
    fresh_death_cross_50_200:    { desc: 'MA50 crossed below MA200 in last 10 sessions. Structural bearish cross.', hint: 'Historically precedes long bear phases; don\'t fight it.' },
    macd_bearish_cross:          { desc: 'MACD line crossed below Signal line today. Momentum shift from bull to bear confirmed.', hint: 'Crosses below zero line are more severe; extra caution if MA200 also breaks.' },
};

function _pillTip(key, isWarning) {
    const zh = isWarning ? WARN_DESC_ZH : SIG_DESC_ZH;
    const en = isWarning ? WARN_DESC_EN : SIG_DESC_EN;
    const dict = (UI.currentLang === 'en' ? en : zh);
    return dict[key];
}

// ── Preset strategy tooltip content ──────────────────────────────────────
// Each entry has: criteria (bullet list of filter rules), strategy (market
// scenario the strategy captures), action (what to do with the results).
// Rendered on hover over preset buttons.
const PRESET_DETAIL_ZH = {
    leaders: {
        criteria: [
            'Score ≥ 75',
            'Stage 2 上升趨勢',
            '量比 ≥ 1.2×（今日成交量 / 20 日均量）',
            '僅熱門產業（HOT — 由每日產業掃描 protocol 動態標記，跟進階篩選的「產業」dropdown 不同）',
            '綜合標籤 = 強多（composite score ≥ 80；動能、均線、空方、趨勢四維度加權）',
        ],
        strategy: '四重共振：基本面 + 技術面 + 資金面 + 產業面全部對齊。抓出當下市場最強的 5-15 檔領頭羊。',
        action: '動能派核心持股候選；回檔至 MA20 / MA50 是加碼點。倉位可重、但要設停損（MA50 跌破 = 清倉訊號）。',
    },
    breakout: {
        criteria: ['Stage 2', '10 日內 MA20/50 黃金交叉', '量能擴張訊號', '排除 RSI 超買'],
        strategy: 'O\'Neil / Minervini 派經典突破進場點。黃金交叉是結構轉強、加上量能確認就是真突破。',
        action: '當日或下一根 K 線市價 / 限價進。停損放前低或 MA20 下方 3-5%，R/R 至少 2:1。',
    },
    uptrend: {
        criteria: ['Score ≥ 65', 'Stage 2', '排除 RSI 超買', '排除拋物線風險'],
        strategy: '趨勢成熟的追蹤標的 — 已在上升段但還沒過熱。比突破晚進場但勝率穩。',
        action: '適合偏保守資金；等 RSI 回落到 50-65 區間再進最佳。倉位可中等、別追當下最熱的。',
    },
    pullback: {
        criteria: ['Stage 2', 'RSI 超賣回檔（< 30 但 Stage 2）'],
        strategy: '強勢股短線回檔買點。**只適用於 Stage 2**；下跌股 RSI < 30 是弱勢延續，不是機會。',
        action: '分批買進（3-5 天內 2-3 批），別 all-in 抄底。停損放回檔前低，確認反彈再加碼。',
    },
    squeeze: {
        criteria: ['squeeze_candidate 訊號（空單 > 20% + 站上 MA20 > 5%）'],
        strategy: '高空單 + 價格已反彈。若有 catalyst（財報 / 政策 / 併購）可能引爆軋空連鎖。',
        action: '短線交易思維，停損緊（-5% 以內），目標 10-20% 快速獲利了結。別長抱、軋空結束很快。',
    },
    safe: {
        criteria: ['Score ≥ 60', '排除超買', '排除拋物線'],
        strategy: '新手友善、保守動能。不追強但避開過熱，適合建倉、長期追蹤。',
        action: '小倉位分散持有；重視整體 portfolio 表現而非單檔爆發力。適合月級時間框架。',
    },
    all: {
        criteria: ['無任何過濾'],
        strategy: '重設所有 filter，看全 503 檔分布。用來了解市場整體狀況或自己手動挑。',
        action: '搭配表頭排序（分數 / RSI / 量比）切換不同維度觀察。',
    },
    macd_breakout: {
        criteria: ['Stage 2', 'MACD 剛黃金交叉', '量能擴張'],
        strategy: '三訊號同時出現：結構 + 動能 + 資金。技術面最完整的進場點，勝率比單一訊號高。',
        action: '黃金交叉當週內進場最佳，錯過 5 天以上訊號就衰退。停損 MA50 下方，目標前高。',
    },
    macd_accelerating: {
        criteria: ['Score ≥ 60', 'MACD histogram 連續擴大'],
        strategy: '趨勢中段動能加速階段 — 不是初升段也不是頂部。用 MACD 柱狀圖確認「動能持續累積」。',
        action: '適合在已有持倉時加碼；新進場也可以但 R/R 比 breakout 略差。',
    },
    macd_reversal: {
        criteria: ['RSI ≤ 40（超賣 / 偏弱）', 'MACD histogram 轉升'],
        strategy: '超賣區底部搭配動能翻轉確認。避免接飛刀 — 光超賣不進，動能跡象出現才動。',
        action: '只在 Stage 2 或 Stage 1 後期使用；Stage 3/4 的 MACD 反轉常是反彈不是反轉。分批進。',
    },
};
const PRESET_DETAIL_EN = {
    leaders: {
        criteria: [
            'Score ≥ 75',
            'Stage 2 uptrend',
            'Volume ratio ≥ 1.2× (today / 20-day avg)',
            'Hot-sector tickers only (HOT = dynamic list from daily sector-scan protocol — NOT the manual "Sector" dropdown in advanced filters)',
            'Composite label = Strongly Bullish (score ≥ 80; weighted volume + MA stage + squeeze + trend acceleration)',
        ],
        strategy: 'Four-way confluence: fundamentals + technicals + flow + sector aligned. Filters to the 5-15 strongest leaders in the market right now.',
        action: 'Core momentum holdings. Add on pullbacks to MA20/MA50. Full-size allowed but set stop at MA50 break.',
    },
    breakout: {
        criteria: ['Stage 2', 'MA20/50 golden cross within 10 days', 'Volume expansion signal', 'Exclude RSI overbought'],
        strategy: 'Classic O\'Neil / Minervini breakout entry. Golden cross = structural strength; volume = confirmation of a real breakout.',
        action: 'Enter same day or next bar (market or limit). Stop below prior pivot or 3-5% below MA20. R/R ≥ 2:1.',
    },
    uptrend: {
        criteria: ['Score ≥ 65', 'Stage 2', 'Exclude RSI overbought', 'Exclude parabolic risk'],
        strategy: 'Mature trend followers — already uptrending but not overheated. Later entry than breakout but more consistent win rate.',
        action: 'Good for conservative capital. Best entry: wait for RSI to retrace to 50-65. Medium position size; avoid the hottest names.',
    },
    pullback: {
        criteria: ['Stage 2', 'RSI oversold pullback (<30 while Stage 2)'],
        strategy: 'Short-term dip in a strong uptrend. ONLY applies to Stage 2; RSI <30 in a downtrend is weakness continuation, not opportunity.',
        action: 'Scale in (2-3 tranches over 3-5 days); don\'t all-in. Stop at prior pullback low. Add after bounce confirms.',
    },
    squeeze: {
        criteria: ['squeeze_candidate signal (short >20% + above MA20 by >5%)'],
        strategy: 'High short interest + price recovery. With a catalyst (earnings/policy/M&A) this can trigger a short squeeze.',
        action: 'Short-term trade mindset. Tight stops (<-5%). Target 10-20% quick profit — squeezes end fast, don\'t hold long.',
    },
    safe: {
        criteria: ['Score ≥ 60', 'Exclude overbought', 'Exclude parabolic'],
        strategy: 'Beginner-friendly conservative momentum. Doesn\'t chase the strongest but avoids overheated — good for building positions.',
        action: 'Small diversified positions. Focus on portfolio-level performance, not single-name explosiveness. Month-scale horizon.',
    },
    all: {
        criteria: ['No filters'],
        strategy: 'Reset all filters — see the full 503-stock distribution. For overall market assessment or manual discovery.',
        action: 'Combine with column sorting (score / RSI / volume) to view from different angles.',
    },
    macd_breakout: {
        criteria: ['Stage 2', 'Fresh MACD bullish cross', 'Volume expansion'],
        strategy: 'Triple confirmation: structure + momentum + flow. Strongest technical entry — win rate exceeds any single signal.',
        action: 'Enter within the week of the cross — signal decays after 5 days. Stop below MA50, target prior highs.',
    },
    macd_accelerating: {
        criteria: ['Score ≥ 60', 'MACD histogram rising consecutively'],
        strategy: 'Mid-trend momentum acceleration — not the initial rally, not the top. Histogram expansion confirms momentum is building.',
        action: 'Good for adding to existing positions. New entries OK but slightly worse R/R than breakout.',
    },
    macd_reversal: {
        criteria: ['RSI ≤ 40 (oversold / weak)', 'MACD histogram turning up'],
        strategy: 'Oversold zone with momentum-flip confirmation. Avoids catching falling knives — don\'t buy on oversold alone, wait for momentum sign.',
        action: 'Use only in Stage 2 or late Stage 1. In Stage 3/4 a MACD reversal is usually a bounce, not a true reversal. Scale in.',
    },
};

function _presetTip(key) {
    const dict = (UI.currentLang === 'en' ? PRESET_DETAIL_EN : PRESET_DETAIL_ZH);
    return dict[key];
}

// Global hover tooltip for signal/warning pills — lifecycle:
// mouseover pill → show tooltip positioned above (flips below near top edge)
// mouseout       → hide after 80ms delay (so moving cursor into tooltip
//                  wouldn't be needed anyway since pointer-events:none)
(function initMomentumPillTooltip() {
    let _hideTimer = null;
    function _renderTierRows(tiers) {
        if (!Array.isArray(tiers) || !tiers.length) return '';
        const rows = tiers.map(tier => `
            <div class="mpt-tier-row">
              <span class="mpt-tier-dot">${tier.dot || '⚪'}</span>
              <span class="mpt-tier-text"><strong>${tier.label}</strong> — ${tier.text}</span>
            </div>
        `).join('');
        return `<div class="mpt-tiers">${rows}</div>`;
    }
    function _renderSignalTip(el, isWarning) {
        const key = el.dataset.sigTip || el.dataset.warnTip;
        const entry = _pillTip(key, isWarning);
        if (!entry) return null;
        const titleLabel = isWarning ? warnLabel(key) : sigLabel(key);
        return {
            cls: isWarning ? 'mpt-warning' : 'mpt-signal',
            html: `
              <div class="mpt-title">${titleLabel}</div>
              <div class="mpt-desc">${entry.desc}</div>
              ${_renderTierRows(entry.tiers)}
              ${entry.hint ? `<div class="mpt-hint">${entry.hint}</div>` : ''}
            `,
        };
    }
    function _renderPresetTip(el) {
        const key = el.dataset.presetTip;
        const entry = _presetTip(key);
        if (!entry) return null;
        const tr = t();
        const i18nEntry = tr['preset_' + key] || {};
        const title = i18nEntry.label || key;
        const isEn = UI.currentLang === 'en';
        const criteriaLbl = isEn ? 'Criteria' : '判斷標準';
        const strategyLbl = isEn ? 'Strategy' : '策略意義';
        const actionLbl   = isEn ? 'How to use' : '使用建議';
        const criteriaList = entry.criteria.map(c => `<li>${c}</li>`).join('');
        return {
            cls: 'mpt-preset',
            html: `
              <div class="mpt-title">${title}</div>
              <div class="mpt-section-label">${criteriaLbl}</div>
              <ul class="mpt-criteria">${criteriaList}</ul>
              <div class="mpt-section-label">${strategyLbl}</div>
              <div class="mpt-desc">${entry.strategy}</div>
              <div class="mpt-hint"><strong>${actionLbl}:</strong> ${entry.action}</div>
            `,
        };
    }
    function showTip(el) {
        const tip = document.getElementById('mom-pill-tooltip');
        if (!tip) return;
        let content;
        if (el.dataset.presetTip)      content = _renderPresetTip(el);
        else if (el.dataset.warnTip)   content = _renderSignalTip(el, true);
        else if (el.dataset.sigTip)    content = _renderSignalTip(el, false);
        if (!content) return;
        tip.className = content.cls;
        tip.innerHTML = content.html;
        // Position invisible first to measure height
        tip.style.opacity = '0';
        tip.style.top = '-9999px';
        tip.classList.add('visible');
        requestAnimationFrame(() => {
            const rect = el.getBoundingClientRect();
            const tRect = tip.getBoundingClientRect();
            const gap = 8;
            let top = rect.top - tRect.height - gap;
            if (top < 8) top = rect.bottom + gap;  // flip below if near top edge
            let left = rect.left + (rect.width - tRect.width) / 2;
            left = Math.max(8, Math.min(left, window.innerWidth - tRect.width - 8));
            tip.style.top = top + 'px';
            tip.style.left = left + 'px';
            tip.style.opacity = '';
        });
    }
    function hideTip() {
        const tip = document.getElementById('mom-pill-tooltip');
        if (tip) tip.classList.remove('visible');
    }
    const SELECTOR = '[data-sig-tip], [data-warn-tip], [data-preset-tip]';
    document.addEventListener('mouseover', e => {
        const el = e.target.closest(SELECTOR);
        if (!el) return;
        if (_hideTimer) { clearTimeout(_hideTimer); _hideTimer = null; }
        showTip(el);
    });
    document.addEventListener('mouseout', e => {
        const el = e.target.closest(SELECTOR);
        if (!el) return;
        _hideTimer = setTimeout(hideTip, 80);
    });
})();

// Signal / warning chip lists — shown in the filter panel. Order matters (most useful first).
const FILTER_SIGNALS = [
    'stage2_uptrend_intact',
    'volume_expansion',
    'fresh_golden_cross_20_50',
    'fresh_golden_cross_50_200',
    'macd_bullish_cross',
    'macd_histogram_rising',
    'heavy_volume_spike_today',
    'squeeze_candidate',
    'oversold_rsi',
    'low_short_interest',
    'high_short_interest',
];
const FILTER_WARNINGS = [
    'overbought_rsi',
    'parabolic_blowoff_risk',
    'stage4_downtrend',
    'volume_dry_up',
    'fresh_death_cross_20_50',
    'fresh_death_cross_50_200',
    'macd_bearish_cross',
];

function defaultFilter() {
    return {
        minScore: 50,
        maxScore: null,
        minRsi:   null,
        maxRsi:   null,
        minVolumeRatio: null,
        onlyHotSectors: false,
        stage:    'any',
        sector:   'any',
        label:    'any',
        universe: 'any',
        requiredSignals:   new Set(),
        requiredWarnings:  new Set(),
        excludedWarnings:  new Set(),
        watchlistMode: 'all',   // 'all' | 'only' | 'exclude'
        search:   '',
    };
}

// GICS sector list matching sp500_sectors.json values — used for dropdown translation
const SECTOR_KEYS = [
    'Information Technology', 'Financials', 'Health Care',
    'Consumer Discretionary', 'Communication Services', 'Industrials',
    'Consumer Staples', 'Energy', 'Utilities', 'Real Estate', 'Materials',
];

function sectorLabel(key) {
    return t().sectors_map?.[key] || key;
}

// Preset strategies — classic filter combos with a known rationale. Order matters
// (rendered left-to-right). Each applies atomically (overwrites current filter).
const PRESETS = {
    leaders: {   // 🚀 "Momentum Leaders" - high score + stage 2 + volume + hot sector
        filter: {
            minScore: 75, maxScore: null, minRsi: null, maxRsi: null,
            minVolumeRatio: 1.2, onlyHotSectors: true,
            stage: 'Stage 2 uptrend', sector: 'any',
            label: 'STRONGLY_BULLISH',
            requiredSignals:  [],
            requiredWarnings: [],
            excludedWarnings: [],
            search: '',
        },
        label_zh: '🚀 真動能領航者',
        label_en: 'Momentum Leaders',
        hint_zh: '高分(75+) + Stage 2 上升趨勢 + 強力買盤(1.2x+) + 處於熱門產業',
        hint_en: 'Score 75+ / Stage 2 / Volume 1.2x+ / Hot Sector only'
    },
    breakout: {   // 🔥 fresh 20/50 golden cross + volume confirmation on Stage 2 name
        filter: {
            minScore: 0, maxScore: null, minRsi: null, maxRsi: null,
            stage: 'Stage 2 uptrend', sector: 'any',
            label: 'any',
            requiredSignals:  ['fresh_golden_cross_20_50', 'volume_expansion'],
            requiredWarnings: [],
            excludedWarnings: ['overbought_rsi'],
            search: '',
        },
    },
    uptrend: {    // 💪 established trend, score ≥65, not overextended
        filter: {
            minScore: 65, maxScore: null, minRsi: null, maxRsi: null,
            stage: 'Stage 2 uptrend', sector: 'any',
            label: 'any',
            requiredSignals:  [],
            requiredWarnings: [],
            excludedWarnings: ['overbought_rsi', 'parabolic_blowoff_risk'],
            search: '',
        },
    },
    pullback: {   // 📉 oversold RSI in a still-uptrending stock
        filter: {
            minScore: 45, maxScore: null, minRsi: null, maxRsi: null,
            stage: 'Stage 2 uptrend', sector: 'any',
            label: 'any',
            requiredSignals:  ['oversold_rsi'],
            requiredWarnings: [],
            excludedWarnings: [],
            search: '',
        },
    },
    squeeze: {    // ⚡ short-squeeze candidates (high short + positive momentum)
        filter: {
            minScore: 0, maxScore: null, minRsi: null, maxRsi: null,
            stage: 'any', sector: 'any',
            label: 'any',
            requiredSignals:  ['squeeze_candidate'],
            requiredWarnings: [],
            excludedWarnings: [],
            search: '',
        },
    },
    safe: {       // 🎯 score ≥60, no overbought / parabolic — conservative quality
        filter: {
            minScore: 60, maxScore: null, minRsi: null, maxRsi: null,
            stage: 'any', sector: 'any',
            label: 'any',
            requiredSignals:  [],
            requiredWarnings: [],
            excludedWarnings: ['overbought_rsi', 'parabolic_blowoff_risk'],
            search: '',
        },
    },
    all: {        // 📊 reset — see everything
        filter: null,  // resolved to defaultFilter() on apply
    },
    macd_breakout: {   // 📈 MACD bullish cross + Stage 2 + volume expansion
        filter: {
            minScore: 0, maxScore: null, minRsi: null, maxRsi: null,
            minVolumeRatio: null, onlyHotSectors: false,
            stage: 'Stage 2 uptrend', sector: 'any',
            label: 'any',
            requiredSignals:  ['macd_bullish_cross', 'volume_expansion'],
            requiredWarnings: [],
            excludedWarnings: [],
            search: '',
        },
    },
    macd_accelerating: {   // ⚡ MACD histogram rising + score ≥ 60 (momentum building)
        filter: {
            minScore: 60, maxScore: null, minRsi: null, maxRsi: null,
            minVolumeRatio: null, onlyHotSectors: false,
            stage: 'any', sector: 'any',
            label: 'any',
            requiredSignals:  ['macd_histogram_rising'],
            requiredWarnings: [],
            excludedWarnings: [],
            search: '',
        },
    },
    macd_reversal: {   // 🔄 RSI oversold + MACD histogram rising (bottom reversal confirm)
        filter: {
            minScore: 0, maxScore: null, minRsi: null, maxRsi: 40,
            minVolumeRatio: null, onlyHotSectors: false,
            stage: 'any', sector: 'any',
            label: 'any',
            requiredSignals:  ['macd_histogram_rising'],
            requiredWarnings: [],
            excludedWarnings: [],
            search: '',
        },
    },
};

function applyPreset(key) {
    const p = PRESETS[key];
    if (!p) return;
    if (p.filter === null) {
        _state.filter = defaultFilter();
    } else {
        _state.filter = {
            ...p.filter,
            requiredSignals:  new Set(p.filter.requiredSignals  || []),
            requiredWarnings: new Set(p.filter.requiredWarnings || []),
            excludedWarnings: new Set(p.filter.excludedWarnings || []),
        };
    }
    renderFilterPanel();
    renderTable();
}

let _state = {
    rows: [],
    filter: defaultFilter(),
    sort: { field: 'score', dir: 'desc' },  // default: highest score first
    history: {},
    journalStats: null,
    historyChart: null,
};

// Stage ordering for sort: most bullish → most bearish.
// Used when sorting by "stage" column.
const STAGE_ORDER = {
    'Stage 2 uptrend':   4,
    'Stage 1 basing':    3,
    'Stage 3 top':       2,
    'Stage 4 downtrend': 1,
    'unknown':           0,
};

function _sortKey(r, field) {
    if (field === 'stage') return STAGE_ORDER[r.stage] ?? -1;
    const v = r[field];
    // Nulls sort last regardless of direction
    if (v == null) return null;
    return v;
}

function _compareRows(a, b, field, dir) {
    const va = _sortKey(a, field);
    const vb = _sortKey(b, field);
    if (va == null && vb == null) return 0;
    if (va == null) return 1;   // nulls always last
    if (vb == null) return -1;
    const c = va < vb ? -1 : va > vb ? 1 : 0;
    return dir === 'desc' ? -c : c;
}

/* ── Init ─────────────────────────────────────────────────────── */
async function loadMomentumData() {
    UI.logToUI('Momentum: loading data...');
    try {
        const data = await DataStore.get();
        UI.applySyncLight(document.getElementById('last-update'), data.last_updated, null, [
            { label: '動能選股', ts: data?.momentum_screen?.generated_at, ttl: 1200, hint: '執行「動能選股」(screen.py)' },
        ]);

        const ms = data.momentum_screen || { status: 'no_data' };
        if (ms.status !== 'success' || !ms.rows || ms.rows.length === 0) {
            showEmptyState();
            return;
        }

        _state.rows = ms.rows;
        _state.market = data.market || null;
        _state.history = ms.history_by_ticker || {};
        _state.journalStats = ms.journal?.stats || null;

        // Deep-link: ?sector=<GICS> from sector page → pre-apply sector filter
        const qp = new URLSearchParams(window.location.search);
        const deepSector = qp.get('sector');
        if (deepSector) {
            const known = new Set(ms.rows.map(r => r.sector).filter(Boolean));
            if (known.has(deepSector)) _state.filter.sector = deepSector;
        }

        document.getElementById('no-data-banner').classList.add('hidden');
        document.getElementById('meta-strip').classList.remove('hidden');
        document.getElementById('filter-bar').classList.remove('hidden');
        document.getElementById('table-wrap').classList.remove('hidden');
        document.getElementById('journal-section').classList.remove('hidden');

        renderMeta(ms);
        renderFilterPanel();
        renderTable();
        renderJournalStats(ms.journal);

        UI.icons();
    } catch (e) {
        UI.logToUI('Momentum load error: ' + e.message, 'error');
        console.error('[momentum] load error:', e);
    }
}

function showEmptyState() {
    document.getElementById('no-data-banner').classList.remove('hidden');
    document.getElementById('meta-strip').classList.add('hidden');
    document.getElementById('filter-bar').classList.add('hidden');
    document.getElementById('table-wrap').classList.add('hidden');
    document.getElementById('journal-section').classList.add('hidden');
    document.getElementById('no-data-text').textContent = t().no_data || '尚未有掃描結果';
    document.getElementById('snap-id').textContent = '';
    UI.icons();
}

/* ── Meta strip ────────────────────────────────────────────────── */
function renderMeta(ms) {
    const tr = t();
    document.getElementById('snap-id').textContent = ms.snap_id || '';

    document.getElementById('meta-time-label').textContent   = tr.snapshot_time || 'Scanned';
    document.getElementById('meta-time').textContent         = ms.generated_at || '—';
    document.getElementById('meta-time-sub').textContent     = ms.freshness
        ? `${ms.freshness}  ·  ${ms.age_label}` : '';

    document.getElementById('meta-matched-label').textContent = tr.total_matched || 'Matched';
    document.getElementById('meta-matched').textContent       = ms.total_rows ?? '—';
    document.getElementById('meta-matched-sub').textContent   = ms.snap_date || '';

    document.getElementById('meta-journal-label').textContent = tr.journal_total || 'Journal entries';
    document.getElementById('meta-journal').textContent       = ms.journal?.total_entries ?? 0;
    const stats = ms.journal?.stats;
    document.getElementById('meta-journal-sub').textContent   = stats
        ? `5d:${stats.fill_counts?.['5d'] || 0} · 20d:${stats.fill_counts?.['20d'] || 0} · 60d:${stats.fill_counts?.['60d'] || 0}`
        : '';

    document.getElementById('meta-snaps-label').textContent = tr.snapshot_count || 'Snapshots';
    document.getElementById('meta-snaps').textContent       = ms.snapshot_count ?? '—';
    document.getElementById('meta-snaps-sub').textContent   = stats
        ? `${stats.date_range?.earliest || ''} → ${stats.date_range?.latest || ''}` : '';
}

/* ── Filter panel ─────────────────────────────────────────────── */
function renderSignalChips() {
    const wrap = document.getElementById('f-signal-chips');
    wrap.innerHTML = FILTER_SIGNALS.map(sig => {
        const active = _state.filter.requiredSignals.has(sig);
        return `<span class="filter-chip${active ? ' active' : ''}" data-sig="${sig}" title="${sig}">${sigLabel(sig)}</span>`;
    }).join('');
    wrap.querySelectorAll('[data-sig]').forEach(el => {
        el.onclick = () => {
            const k = el.dataset.sig;
            const s = _state.filter.requiredSignals;
            if (s.has(k)) s.delete(k); else s.add(k);
            renderSignalChips();
            renderTable();
        };
    });
}

function renderWarningChips() {
    const wrap = document.getElementById('f-warning-chips');
    wrap.innerHTML = FILTER_WARNINGS.map(w => {
        const active = _state.filter.excludedWarnings.has(w);
        return `<span class="filter-chip warn${active ? ' active' : ''}" data-warn="${w}" title="${w}">${warnLabel(w)}</span>`;
    }).join('');
    wrap.querySelectorAll('[data-warn]').forEach(el => {
        el.onclick = () => {
            const k = el.dataset.warn;
            const s = _state.filter.excludedWarnings;
            if (s.has(k)) s.delete(k); else s.add(k);
            renderWarningChips();
            renderTable();
        };
    });
}

function renderRequiredWarningChips() {
    const wrap = document.getElementById('f-required-warning-chips');
    if (!wrap) return;
    wrap.innerHTML = FILTER_WARNINGS.map(w => {
        const active = _state.filter.requiredWarnings.has(w);
        return `<span class="filter-chip${active ? ' active' : ''}" data-reqwarn="${w}" title="${w}">${warnLabel(w)}</span>`;
    }).join('');
    wrap.querySelectorAll('[data-reqwarn]').forEach(el => {
        el.onclick = () => {
            const k = el.dataset.reqwarn;
            const s = _state.filter.requiredWarnings;
            if (s.has(k)) s.delete(k); else s.add(k);
            renderRequiredWarningChips();
            renderTable();
        };
    });
}

function renderWatchlistScope() {
    const wrap = document.getElementById('f-watchlist-toggle');
    if (!wrap) return;
    const current = _state.filter.watchlistMode || 'all';
    wrap.querySelectorAll('.segmented-btn').forEach(btn => {
        const val = btn.dataset.value;
        btn.classList.toggle('active', val === current);
        btn.onclick = () => {
            _state.filter.watchlistMode = val;
            renderWatchlistScope();
            renderTable();
        };
    });
}

function renderUniverseToggle() {
    const wrap = document.getElementById('f-universe-toggle');
    if (!wrap) return;
    const current = _state.filter.universe || 'any';
    wrap.querySelectorAll('.segmented-btn').forEach(btn => {
        const val = btn.dataset.value;
        btn.classList.toggle('active', val === current);
        btn.onclick = () => {
            _state.filter.universe = val;
            renderUniverseToggle();
            renderTable();
        };
    });
}

function renderPresetRow() {
    const wrap = document.getElementById('f-presets');
    if (!wrap) return;
    const tr = t();
    wrap.innerHTML = Object.keys(PRESETS).map(key => {
        const entry = tr['preset_' + key] || {};
        const label = entry.label || key;
        // Use custom hover tooltip (data-preset-tip) instead of browser-native title=.
        // Tooltip content comes from PRESET_DETAIL_ZH/EN — shows criteria + strategy + action.
        return `<button class="preset-btn" data-preset="${key}" data-preset-tip="${key}">${label}</button>`;
    }).join('');
    wrap.querySelectorAll('[data-preset]').forEach(el => {
        el.addEventListener('click', () => applyPreset(el.dataset.preset));
    });
}

function renderFilterPanel() {
    // Populate controls from state (called once after load + after preset apply + after reset)
    document.getElementById('f-min-score').value = _state.filter.minScore;
    document.getElementById('filter-score-val').textContent = `≥ ${_state.filter.minScore}`;
    document.getElementById('f-min-rsi').value = _state.filter.minRsi ?? '';
    document.getElementById('f-max-rsi').value = _state.filter.maxRsi ?? '';
    document.getElementById('f-min-vol').value = _state.filter.minVolumeRatio ?? '';
    document.getElementById('f-only-hot').value = _state.filter.onlyHotSectors ? 'true' : 'false';
    document.getElementById('f-stage').value = _state.filter.stage;
    document.getElementById('f-sector').value = _state.filter.sector;
    const labelSel = document.getElementById('f-label');
    if (labelSel) labelSel.value = _state.filter.label;
    document.getElementById('search-ticker').value = _state.filter.search;
    renderPresetRow();
    renderSignalChips();
    renderRequiredWarningChips();
    renderWarningChips();
    renderUniverseToggle();
    renderWatchlistScope();
    UI.icons();
}

/* ── Matcher + table render ───────────────────────────────────── */
function matchesFilter(r) {
    const f = _state.filter;
    if (r.score == null || r.score < f.minScore) return false;
    if (f.maxScore != null && r.score > f.maxScore) return false;
    if (f.minRsi != null && (r.rsi_14 == null || r.rsi_14 < f.minRsi)) return false;
    if (f.maxRsi != null && (r.rsi_14 == null || r.rsi_14 > f.maxRsi)) return false;
    
    // Min Volume Ratio check
    if (f.minVolumeRatio != null && (r.ratio_20d == null || r.ratio_20d < f.minVolumeRatio)) return false;

    if (f.stage  !== 'any' && r.stage  !== f.stage)  return false;
    if (f.sector !== 'any' && r.sector !== f.sector) return false;

    // Only Hot Sectors check
    if (f.onlyHotSectors) {
        const market = _state.market;
        const hot = market?.hot_sectors || [];
        if (!hot.includes(r.sector)) return false;
    }

    if (f.label  !== 'any' && r.label  !== f.label)  return false;

    // Watchlist scope toggle — filters on origin regardless of other criteria
    const isWatchlistOnly = r.in_sp500 === false && r.in_nasdaq100 === false && r.in_sox === false;
    if (f.watchlistMode === 'only'    && !isWatchlistOnly) return false;
    if (f.watchlistMode === 'exclude' &&  isWatchlistOnly) return false;

    // Universe filter: SP500 / Nasdaq100 / SOX.
    // Watchlist tickers always show regardless of universe filter (preserved behavior).
    if (!isWatchlistOnly) {
        if (f.universe === 'sp500' && !r.in_sp500) return false;
        if (f.universe === 'nasdaq100' && !r.in_nasdaq100) return false;
        if (f.universe === 'sox' && !r.in_sox) return false;
    }

    const sigs = new Set(r.signals || []);
    for (const s of f.requiredSignals) if (!sigs.has(s)) return false;
    const warns = new Set(r.warnings || []);
    for (const w of f.requiredWarnings) if (!warns.has(w)) return false;
    for (const w of f.excludedWarnings) if (warns.has(w))  return false;

    if (f.search && !(r.ticker || '').toUpperCase().includes(f.search.toUpperCase())) return false;
    return true;
}

function renderTable() {
    const tbody = document.getElementById('mom-tbody');
    const visible = _state.rows.filter(matchesFilter);

    // Sort according to current _state.sort
    const { field, dir } = _state.sort;
    visible.sort((a, b) => _compareRows(a, b, field, dir));

    // Re-rank within the visible set so # reflects the current filter view
    const ranked = visible.map((r, i) => ({ ...r, rank: i + 1 }));
    tbody.innerHTML = ranked.map(rowHTML).join('') || emptyRow();

    // Paint sort indicators on headers
    _updateSortHeaders();

    const countTxt = `${visible.length} / ${_state.rows.length}`;
    document.getElementById('table-count').textContent = countTxt;
    // Hero count: big number on its own, total as subtle side label
    const matchEl  = document.getElementById('filter-match-count');
    const totalEl  = document.getElementById('filter-match-total');
    if (matchEl)  matchEl.textContent  = visible.length;
    if (totalEl)  totalEl.textContent  = `/ ${_state.rows.length}`;

    tbody.querySelectorAll('.mom-row').forEach(tr => {
        tr.addEventListener('click', () => openHistory(tr.dataset.ticker));
    });
    // Volume cell click → intercept before row handler fires
    tbody.querySelectorAll('.vol-cell').forEach(td => {
        td.addEventListener('click', e => {
            e.stopPropagation();
            const r = _state.rows.find(x => x.ticker === td.dataset.tickerVol);
            if (r) openVolumePopup(r);
        });
    });
    // Stage cell click
    tbody.querySelectorAll('.stage-cell').forEach(td => {
        td.addEventListener('click', e => {
            e.stopPropagation();
            const r = _state.rows.find(x => x.ticker === td.dataset.tickerStage);
            if (r) openStagePopup(r);
        });
    });
    // RSI cell click
    tbody.querySelectorAll('.rsi-cell').forEach(td => {
        td.addEventListener('click', e => {
            e.stopPropagation();
            const r = _state.rows.find(x => x.ticker === td.dataset.tickerRsi);
            if (r) openRsiPopup(r);
        });
    });
    // MACD cell click
    tbody.querySelectorAll('.macd-cell').forEach(td => {
        td.addEventListener('click', e => {
            e.stopPropagation();
            const r = _state.rows.find(x => x.ticker === td.dataset.tickerMacd);
            if (r) openMacdPopup(r);
        });
    });
    // Analyze button click → enqueue invest protocol
    tbody.querySelectorAll('.analyze-btn').forEach(btn => {
        btn.addEventListener('click', e => {
            e.stopPropagation();
            const tk = btn.dataset.analyzeTicker;
            if (tk && window.AnalyzeQueue) window.AnalyzeQueue.enqueue(tk);
        });
    });
    // Pill click → toggle inclusive filter by label / sector / signal / warning
    tbody.querySelectorAll('.pill-clickable').forEach(el => {
        el.addEventListener('click', e => {
            e.stopPropagation();
            const type  = el.dataset.pillType;
            const value = el.dataset.pillValue;
            if (!type || !value) return;
            _togglePillFilter(type, value);
        });
    });
}

// Toggle inclusive filter based on pill type + value.
// Clicking the same pill that's already active un-sets it.
function _togglePillFilter(type, value) {
    const f = _state.filter;
    if (type === 'label') {
        f.label = (f.label === value) ? 'any' : value;
    } else if (type === 'sector') {
        f.sector = (f.sector === value) ? 'any' : value;
    } else if (type === 'signal') {
        if (f.requiredSignals.has(value)) f.requiredSignals.delete(value);
        else f.requiredSignals.add(value);
    } else if (type === 'warning') {
        // Clicking a row warning pill = "show more like this" = add to REQUIRED warnings
        // (excluded warnings are only set via the filter panel's warning chips)
        if (f.requiredWarnings.has(value)) f.requiredWarnings.delete(value);
        else f.requiredWarnings.add(value);
    }
    renderFilterPanel();
    renderTable();
}

/* Score battery: 10 cells, tier colors, partial cell via gradient.
   Cells 1-3 red (0-30), 4-5 yellow (30-50), 6-7 green (50-70), 8-10 blue (70-100). */
const BATTERY_COLORS = [
    '#ef4444', '#ef4444', '#ef4444',                          // 1-3 red
    '#eab308', '#eab308',                                      // 4-5 yellow
    '#22c55e', '#22c55e',                                      // 6-7 green
    '#3b82f6', '#3b82f6', '#3b82f6',                          // 8-10 blue
];
const BATTERY_UNFILLED = 'rgba(161,161,170,0.15)';

function scoreBatteryHTML(score) {
    if (score == null) return '<span class="text-zinc-600">—</span>';
    const clamped = Math.max(0, Math.min(100, score));
    const filled = clamped / 10;              // e.g. 6.25
    const fullCells = Math.floor(filled);     // 6
    const partial = filled - fullCells;       // 0.25

    const cells = Array.from({ length: 10 }, (_, i) => {
        const color = BATTERY_COLORS[i];
        let bg;
        if (i < fullCells) {
            bg = color;
        } else if (i === fullCells && partial > 0) {
            const pct = Math.round(partial * 100);
            bg = `linear-gradient(to right, ${color} ${pct}%, ${BATTERY_UNFILLED} ${pct}%)`;
        } else {
            bg = BATTERY_UNFILLED;
        }
        return `<span class="cell" style="background:${bg}"></span>`;
    }).join('');

    // Numeric label colored by highest-filled tier
    const tierColor = fullCells >= 7 ? '#3b82f6'
                    : fullCells >= 5 ? '#22c55e'
                    : fullCells >= 3 ? '#eab308'
                    : '#ef4444';
    const n = score.toFixed(1);

    return `<div class="flex items-center gap-2 justify-end">
        <div class="score-battery">${cells}</div>
        <span class="score-num" style="color:${tierColor}">${n}</span>
    </div>`;
}

// RSI cell: number with tier-based color.
// >70 red (overbought), 50-70 green (bullish), 30-50 yellow (neutral), <30 blue (oversold)
function rsiCell(v) {
    if (v == null) return '<span class="text-zinc-600 text-xs">—</span>';
    const color = v >= 70 ? '#ef4444'
                : v >= 50 ? '#22c55e'
                : v >= 30 ? '#eab308'
                : '#3b82f6';
    return `<span class="font-mono text-xs font-bold" style="color:${color};text-decoration:underline dotted rgba(161,161,170,0.4)">${v.toFixed(0)}</span>`;
}

// MACD cell: compact histogram-direction badge with cross marker.
// Shows ⚡▲/⚡▼ on the day of a crossover, ▲/▼ otherwise. Click opens the
// full MACD popup (like RSI) via the macd-cell handler in renderTable.
function macdCell(r) {
    const hist = r.macd_hist;
    if (hist == null) return '<span class="text-zinc-600 text-xs">—</span>';
    const isBull  = hist >= 0;
    const color   = isBull ? '#22c55e' : '#ef4444';
    const arrow   = isBull ? '▲' : '▼';
    const cross   = r.macd_bullish_cross ? '⚡↑' : r.macd_bearish_cross ? '⚡↓' : '';
    return `<span class="font-mono text-xs font-bold" style="color:${color};text-decoration:underline dotted rgba(161,161,170,0.4)">${cross || arrow}</span>`;
}

// Volume ratio color tier — mirrors popup logic
//   ≥3.0 red (HEAVY_SPIKE) · ≥2.0 yellow (MILD_SPIKE) · ≥1.3 green (expansion)
//   ≥0.7 neutral · <0.7 orange (drying up)
function _ratioColor(r) {
    if (r == null) return '#71717a';
    if (r >= 3.0) return '#ef4444';
    if (r >= 2.0) return '#eab308';
    if (r >= 1.3) return '#22c55e';
    if (r <  0.7) return '#fbbf24';
    return '#a1a1aa';
}

// Intraday-aware volume cell rendering. State comes from bridge via CSV:
//   too_early → market open < 30 min, ratio unreliable → dim dash
//   partial   → ratio is scaled projection → show ratio + '*' marker
//   complete  → ratio as-is (weekend / pre-market / post-close)
function _volCellText(r) {
    if (r.intraday_state === 'too_early') return '—';
    if (r.ratio_20d == null) return '—';
    const mark = r.intraday_state === 'partial' ? '*' : '';
    return `${r.ratio_20d.toFixed(2)}×${mark}`;
}
function _volCellColor(r) {
    if (r.intraday_state === 'too_early') return '#71717a';
    return _ratioColor(r.ratio_20d);
}
function _volCellTitle(r) {
    const tr = t();
    if (r.intraday_state === 'too_early') {
        return (tr.vol_intraday_early || 'Intraday <30m — volume read suppressed')
             + ` (elapsed ${r.elapsed_min || 0}m)`;
    }
    if (r.intraday_state === 'partial') {
        return (tr.vol_intraday_scaled || 'Intraday — projected full-day ratio')
             + ` (elapsed ${r.elapsed_min || 0}m)`;
    }
    return '';
}

function rowHTML(r) {
    const above200 = r.above_ma200_pct;
    const above200Txt = above200 == null ? '—'
                       : `${above200 >= 0 ? '+' : ''}${above200.toFixed(1)}%`;
    const above200Color = above200 == null ? 'color:#71717a'
                         : above200 >= 0 ? 'color:#86efac' : 'color:#fca5a5';

    const sigHTML = (r.signals || []).slice(0, 4)
        .map(s => `<span class="signal-pill pill-clickable" data-pill-type="signal" data-pill-value="${s}" data-sig-tip="${s}">${sigLabel(s)}</span>`).join('')
      + (r.warnings || []).slice(0, 2)
        .map(w => `<span class="warning-pill pill-clickable" data-pill-type="warning" data-pill-value="${w}" data-warn-tip="${w}">${warnLabel(w)}</span>`).join('');

    const shortTxt = r.short_pct_float == null ? '—'
                    : `${r.short_pct_float.toFixed(1)}%`;
    const shortColor = r.short_interpretation === 'very_high'     ? '#ef4444'
                     : r.short_interpretation === 'high'          ? '#fbbf24'
                     : r.short_interpretation === 'low'           ? '#71717a'
                     : '#a1a1aa';

    const sectorTxt = r.sector && r.sector !== 'Unknown'
        ? `<div class="text-[9px] font-normal leading-none mt-0.5 pill-clickable sector-subscript" data-pill-type="sector" data-pill-value="${r.sector}">${sectorLabel(r.sector)}</div>`
        : '';

    // Priority: Watchlist (Purple) > Nasdaq100 (Blue) > SP500 (Base)
    const isWatchlist = r.in_sp500 === false && r.in_nasdaq100 === false && r.in_sox === false;
    const isNasdaq    = r.in_nasdaq100 === true;

    let rowClass = 'mom-row';
    if (isWatchlist) rowClass += ' row-watchlist-only';
    else if (isNasdaq) rowClass += ' row-nasdaq-only';

    const watchBadge = isWatchlist
        ? `<span class="text-[11px]" title="${t().watchlist_badge_tooltip || '自選清單'}">⭐</span>`
        : '';
    return `<tr class="${rowClass}" data-ticker="${r.ticker}">
        <td class="text-zinc-500 font-mono text-xs">${r.rank ?? '—'}</td>
        <td>
            <div class="flex items-center gap-1.5">
                <span class="font-bold">${r.ticker}</span>
                ${watchBadge}
                <button class="analyze-btn" data-analyze-ticker="${r.ticker}" title="${(t().analyze_tooltip || '加入個股分析佇列')}">
                    <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>
                </button>
            </div>
            ${sectorTxt}
        </td>
        <td class="text-right font-mono">$${r.price != null ? r.price.toFixed(2) : '—'}</td>
        <td class="text-right score-cell">${scoreBatteryHTML(r.score)}</td>
        <td><span class="mlabel label-${r.label || 'NEUTRAL'} pill-clickable" data-pill-type="label" data-pill-value="${r.label || ''}" title="${r.label || ''}">${labelText(r.label)}</span></td>
        <td class="text-xs text-zinc-400 stage-cell" data-ticker-stage="${r.ticker}" style="cursor:pointer;text-decoration:underline dotted rgba(161,161,170,0.4)" title="${r.stage || ''}">${stageLabel(r.stage)}</td>
        <td class="text-right font-mono text-xs vol-cell" data-ticker-vol="${r.ticker}" style="cursor:pointer;text-decoration:underline dotted rgba(161,161,170,0.4);color:${_volCellColor(r)};font-weight:700" title="${_volCellTitle(r)}">${_volCellText(r)}</td>
        <td class="text-right font-mono text-xs" style="${above200Color}">${above200Txt}</td>
        <td class="text-right rsi-cell" data-ticker-rsi="${r.ticker}" style="cursor:pointer">${rsiCell(r.rsi_14)}</td>
        <td class="text-right macd-cell" data-ticker-macd="${r.ticker}" style="cursor:pointer">${macdCell(r)}</td>
        <td>${sigHTML || '<span class="text-zinc-600 text-xs">—</span>'}</td>
        <td class="text-xs" style="color:${shortColor}">${shortTxt}</td>
    </tr>`;
}

function emptyRow() {
    return `<tr><td colspan="12" class="text-center text-zinc-500 py-8 text-xs">
        ${t().no_data || 'No matches'}</td></tr>`;
}

// Inline SVG icons for sort state — rendered immediately, no lucide hydration needed.
// Paths copied from lucide (arrow-up / arrow-down / chevrons-up-down, stroke-width 2.5).
const SVG_OPEN = '<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">';
const SORT_ICONS = {
    desc:     `${SVG_OPEN}<path d="M12 5v14"/><path d="m19 12-7 7-7-7"/></svg>`,
    asc:      `${SVG_OPEN}<path d="M12 19V5"/><path d="m5 12 7-7 7 7"/></svg>`,
    inactive: `${SVG_OPEN}<path d="m7 15 5 5 5-5"/><path d="m7 9 5-5 5 5"/></svg>`,
};

function _updateSortHeaders() {
    document.querySelectorAll('.mom-th.sortable').forEach(th => {
        const field = th.dataset.sort;
        const arrow = th.querySelector('.sort-arrow');
        if (!arrow) return;
        if (_state.sort.field === field) {
            th.classList.add('active-sort');
            arrow.classList.remove('sort-arrow-inactive');
            arrow.innerHTML = _state.sort.dir === 'desc' ? SORT_ICONS.desc : SORT_ICONS.asc;
        } else {
            th.classList.remove('active-sort');
            arrow.classList.add('sort-arrow-inactive');
            arrow.innerHTML = SORT_ICONS.inactive;
        }
    });
}

function _bindSortHeaders() {
    document.querySelectorAll('.mom-th.sortable').forEach(th => {
        th.addEventListener('click', () => {
            const field = th.dataset.sort;
            if (_state.sort.field === field) {
                // Same column → toggle direction
                _state.sort.dir = _state.sort.dir === 'desc' ? 'asc' : 'desc';
            } else {
                // New column → default desc (highest first is usually what you want)
                _state.sort.field = field;
                _state.sort.dir = 'desc';
            }
            renderTable();
        });
    });
}

/* ── RSI-14 popup (macaron blood bar) ────────────────────────── */
// Pastel palette for the four zones (Tailwind 300-400 shades feel macaron).
const RSI_PALETTE = {
    oversold:   '#93c5fd',   // soft sky blue
    neutral:    '#fcd34d',   // butter yellow
    bullish:    '#86efac',   // mint green
    overbought: '#fca5a5',   // pink coral
};

function _rsiZoneKey(v) {
    if (v == null) return null;
    if (v < 30) return 'oversold';
    if (v < 50) return 'neutral';
    if (v < 70) return 'bullish';
    return 'overbought';
}

function openRsiPopup(r) {
    const tr = t();
    const v = r.rsi_14;
    document.getElementById('rsi-modal-title').textContent =
        `${r.ticker} — ${tr.rsi_modal_title || 'RSI-14 分析'}`;

    if (v == null) {
        document.getElementById('rsi-modal-body').innerHTML =
            `<div class="text-zinc-500">${tr.rsi_msg_unknown || 'RSI 無法判定（資料不足）。'}</div>`;
        document.getElementById('rsi-modal').classList.remove('hidden');
        UI.icons();
        return;
    }

    const zoneKey = _rsiZoneKey(v);
    const zoneLabel = {
        oversold:   tr.rsi_bar_oversold   || '超賣',
        neutral:    tr.rsi_bar_neutral    || '偏弱',
        bullish:    tr.rsi_bar_bullish    || '健康',
        overbought: tr.rsi_bar_overbought || '超買',
    }[zoneKey];
    const zoneTag = {
        oversold:   'OVERSOLD',
        neutral:    'NEUTRAL',
        bullish:    'BULLISH',
        overbought: 'OVERBOUGHT',
    }[zoneKey];

    // Personalised message, with {rsi} substitution
    const msgKey = `rsi_msg_${zoneKey}`;
    const msgTpl = tr[msgKey] || '';
    const personalMsg = msgTpl.replace(/\{rsi\}/g, v.toFixed(1));

    // Pointer label — number sits above a triangle and a vertical line
    // dropping through the bar at the exact RSI%.
    const pct = Math.max(0, Math.min(100, v));

    document.getElementById('rsi-modal-body').innerHTML = `
      <!-- Header: current value + zone tag -->
      <div class="flex items-baseline gap-3">
        <span class="text-[10px] font-black uppercase tracking-widest text-zinc-500">${tr.rsi_zone_title || '目前 RSI-14'}</span>
        <span class="font-mono font-black" style="font-size:22px;color:${RSI_PALETTE[zoneKey]}">${v.toFixed(1)}</span>
        <span class="text-[10px] font-black uppercase tracking-widest" style="color:${RSI_PALETTE[zoneKey]}">${zoneTag} · ${zoneLabel}</span>
      </div>

      <!-- Blood bar with pointer -->
      <div class="rsi-bar-wrap">
        <div class="rsi-pointer" style="left:${pct}%">
          <div class="rsi-pointer-num">${v.toFixed(1)}</div>
          <div class="rsi-pointer-tri">▼</div>
        </div>
        <div class="rsi-bar">
          <div class="rsi-zone" style="width:30%;background:${RSI_PALETTE.oversold}">${tr.rsi_bar_oversold || '超賣'}</div>
          <div class="rsi-zone" style="width:20%;background:${RSI_PALETTE.neutral}">${tr.rsi_bar_neutral || '偏弱'}</div>
          <div class="rsi-zone" style="width:20%;background:${RSI_PALETTE.bullish}">${tr.rsi_bar_bullish || '健康'}</div>
          <div class="rsi-zone" style="width:30%;background:${RSI_PALETTE.overbought}">${tr.rsi_bar_overbought || '超買'}</div>
        </div>
        <div class="rsi-pointer-line" style="left:${pct}%"></div>
        <div class="rsi-ticks">
          <span class="rsi-tick" style="left:0%">0</span>
          <span class="rsi-tick" style="left:30%">30</span>
          <span class="rsi-tick" style="left:50%">50</span>
          <span class="rsi-tick" style="left:70%">70</span>
          <span class="rsi-tick" style="left:100%">100</span>
        </div>
      </div>

      <!-- Zone legend -->
      <div>
        <div class="text-[10px] font-black uppercase tracking-widest text-zinc-500 mb-2">
          ${tr.rsi_zones_title || '分區意義'}
        </div>
        <div class="space-y-1.5 text-[11px] leading-snug">
          <div><span class="inline-block w-3 h-3 rounded-sm align-middle mr-2" style="background:${RSI_PALETTE.oversold}"></span>${tr.rsi_zone_0_30   || '0-30 超賣'}</div>
          <div><span class="inline-block w-3 h-3 rounded-sm align-middle mr-2" style="background:${RSI_PALETTE.neutral}"></span>${tr.rsi_zone_30_50  || '30-50 偏弱'}</div>
          <div><span class="inline-block w-3 h-3 rounded-sm align-middle mr-2" style="background:${RSI_PALETTE.bullish}"></span>${tr.rsi_zone_50_70  || '50-70 健康'}</div>
          <div><span class="inline-block w-3 h-3 rounded-sm align-middle mr-2" style="background:${RSI_PALETTE.overbought}"></span>${tr.rsi_zone_70_100 || '70-100 超買'}</div>
        </div>
      </div>

      <!-- Personalised advice -->
      <div class="pt-3 border-t border-zinc-200 dark:border-zinc-800">
        <div class="text-[10px] font-black uppercase tracking-widest text-zinc-500 mb-1.5">
          ${tr.rsi_your_situation || '你目前的狀況'}
        </div>
        <div class="text-zinc-300 leading-snug text-[11px]" style="color:var(--text-main)">${personalMsg}</div>
      </div>
    `;

    document.getElementById('rsi-modal').classList.remove('hidden');
    UI.icons();
}

function closeRsiPopup() {
    document.getElementById('rsi-modal').classList.add('hidden');
}

/* ── MACD detail popup ──────────────────────────────────────── */
// Mirrors the RSI popup structure: header values + visual + 4 regimes + your-situation.
// MACD has 2 axes instead of RSI's 1:
//   axis 1: MACD line above or below zero (bull/bear regime)
//   axis 2: Histogram rising or falling (momentum accelerating or decelerating)
// → 4 quadrants.
const MACD_PALETTE = {
    strongest_bull:  { rgb: '34,197,94',    hex: '#22c55e' },
    weakening_bull:  { rgb: '234,179,8',    hex: '#eab308' },
    reversal_bull:   { rgb: '59,130,246',   hex: '#3b82f6' },
    strongest_bear:  { rgb: '239,68,68',    hex: '#ef4444' },
};
const MACD_REGIME = {
    strongest_bull: {
        tag: 'STRONGEST BULL',
        title_zh: '最強多頭', title_en: 'Strongest Bull',
        desc_zh: 'MACD 線在零軸上方 + 柱狀圖擴大。動能全面加速，趨勢延續機率最高。',
        desc_en: 'MACD above zero + histogram rising. Fully accelerating bull momentum.',
        advice_zh: '趨勢交易最佳狀態；已持倉可抱緊，未持倉回檔至 MA20 / 50 是加碼點。',
        advice_en: 'Prime trend-following state. Hold existing positions; add on pullbacks to MA20/50.',
    },
    weakening_bull: {
        tag: 'WEAKENING BULL',
        title_zh: '多頭動能衰退', title_en: 'Weakening Bull',
        desc_zh: 'MACD 線在零軸上方但柱狀圖縮短。趨勢仍多但動能放緩，常出現在頂部前夕。',
        desc_en: 'MACD above zero but histogram shrinking. Still bull, but momentum decelerating — often precedes tops.',
        advice_zh: '不急著賣但別加碼；注意是否跌破 MA20 + 出量，那就是 Stage 3 訊號。',
        advice_en: "Don't rush to sell but stop adding. Watch for MA20 break on volume — that's the Stage-3 signal.",
    },
    reversal_bull: {
        tag: 'REVERSAL BULL',
        title_zh: '空頭轉多訊號', title_en: 'Bullish Reversal',
        desc_zh: 'MACD 線在零軸下方但柱狀圖擴大。熊市末尾、築底反彈的早期訊號。',
        desc_en: 'MACD below zero but histogram rising. Early signal of bottom-forming reversal.',
        advice_zh: '不要搶先進場；等 MACD 上穿零軸 + 股價突破 MA50 才是確認訊號。',
        advice_en: "Don't front-run. Wait for MACD to cross zero + price to break MA50 for confirmation.",
    },
    strongest_bear: {
        tag: 'STRONGEST BEAR',
        title_zh: '最強空頭', title_en: 'Strongest Bear',
        desc_zh: 'MACD 線在零軸下方 + 柱狀圖擴大（負值變大）。空頭動能加速，下跌趨勢最強。',
        desc_en: 'MACD below zero + histogram growing (more negative). Fully accelerating bear momentum.',
        advice_zh: '持有中強烈建議減碼或止損。「逆勢抄底」歷史勝率極低，等 reversal_bull 出現再說。',
        advice_en: 'Strong sell / stop-out signal. Catching falling knives has poor odds — wait for reversal signal.',
    },
};

function _macdRegime(r) {
    const hist = r.macd_hist;
    const mLine = r.macd_line;
    if (hist == null || mLine == null) return null;
    const above_zero = mLine >= 0;   // true bull regime = MACD line above zero
    // Histogram direction: use stored histogram_trend if available, else infer
    // from hist sign + magnitude (rising = |hist| increasing → we don't have
    // prior-bar hist in the row, so fall back to hist sign — hist > 0 is an
    // approximation of "rising" when in bull territory).
    const rising = hist >= 0;  // simplified: positive hist = "rising" in the quadrant sense
    if (above_zero && rising)   return 'strongest_bull';
    if (above_zero && !rising)  return 'weakening_bull';
    if (!above_zero && rising)  return 'reversal_bull';
    return 'strongest_bear';
}

function openMacdPopup(r) {
    const isEn = UI.currentLang === 'en';
    const titleKey = isEn ? 'title_en' : 'title_zh';
    const descKey  = isEn ? 'desc_en'  : 'desc_zh';
    const advKey   = isEn ? 'advice_en': 'advice_zh';

    document.getElementById('macd-modal-title').textContent =
        `${r.ticker} — ${isEn ? 'MACD Analysis' : 'MACD 分析'}`;

    const body = document.getElementById('macd-modal-body');
    const hist = r.macd_hist;
    if (hist == null || r.macd_line == null) {
        body.innerHTML = `<div class="text-zinc-500">${isEn ? 'MACD unavailable (insufficient history).' : 'MACD 無法判定（歷史資料不足）。'}</div>`;
        document.getElementById('macd-modal').classList.remove('hidden');
        UI.icons();
        return;
    }

    const regime = _macdRegime(r);
    const palette = MACD_PALETTE[regime];
    const entry = MACD_REGIME[regime];
    const mLine = r.macd_line;
    const sLine = r.macd_signal;

    // Zero-axis bar: map histogram value → 0-100% position on bar.
    // Cap at ±5 for visual sanity; extreme outliers clip to edges.
    const CAP = 5;
    const clamped = Math.max(-CAP, Math.min(CAP, hist));
    const pct = 50 + (clamped / CAP) * 50;   // 50% = zero axis

    // Cross banner if fresh cross today
    let crossBanner = '';
    if (r.macd_bullish_cross) {
        crossBanner = `<div class="text-[11px] p-2 rounded" style="background:rgba(34,197,94,0.12);border:1px solid rgba(34,197,94,0.35);color:#22c55e">
            ⚡↑ ${isEn ? 'Bullish cross today (MACD crossed above Signal)' : '今日黃金交叉（MACD 上穿 Signal 線）'}
          </div>`;
    } else if (r.macd_bearish_cross) {
        crossBanner = `<div class="text-[11px] p-2 rounded" style="background:rgba(239,68,68,0.12);border:1px solid rgba(239,68,68,0.35);color:#ef4444">
            ⚡↓ ${isEn ? 'Bearish cross today (MACD crossed below Signal)' : '今日死叉（MACD 下穿 Signal 線）'}
          </div>`;
    }

    // 4-quadrant map — visual representation of the 4 regimes
    const quadrants = [
        { key: 'weakening_bull', pos: 'top-left'     },
        { key: 'strongest_bull', pos: 'top-right'    },
        { key: 'strongest_bear', pos: 'bottom-left'  },
        { key: 'reversal_bull',  pos: 'bottom-right' },
    ];
    const quadHTML = quadrants.map(q => {
        const p = MACD_PALETTE[q.key];
        const e = MACD_REGIME[q.key];
        const active = (q.key === regime);
        return `<div class="macd-quad-cell ${active ? 'active' : ''}" style="--quad-rgb:${p.rgb}">
            <div class="mq-tag">${e.tag}</div>
            <div class="mq-title">${e[titleKey]}</div>
            <div class="mq-desc">${e[descKey]}</div>
          </div>`;
    }).join('');

    body.innerHTML = `
      ${crossBanner}

      <!-- Header: 3 core values -->
      <div class="grid grid-cols-3 gap-3">
        <div class="text-center">
          <div class="text-[9px] font-black uppercase tracking-widest text-zinc-500 mb-1">MACD ${isEn ? 'Line' : '線'}</div>
          <div class="font-mono font-black" style="font-size:18px;color:${mLine >= 0 ? '#22c55e' : '#ef4444'}">${mLine.toFixed(3)}</div>
        </div>
        <div class="text-center">
          <div class="text-[9px] font-black uppercase tracking-widest text-zinc-500 mb-1">Signal ${isEn ? 'Line' : '線'}</div>
          <div class="font-mono font-black" style="font-size:18px;color:var(--text-main)">${sLine != null ? sLine.toFixed(3) : '—'}</div>
        </div>
        <div class="text-center">
          <div class="text-[9px] font-black uppercase tracking-widest text-zinc-500 mb-1">Histogram</div>
          <div class="font-mono font-black" style="font-size:18px;color:${hist >= 0 ? '#22c55e' : '#ef4444'}">${hist >= 0 ? '+' : ''}${hist.toFixed(3)}</div>
        </div>
      </div>

      <!-- Zero-axis bar: histogram position relative to zero -->
      <div>
        <div class="flex items-baseline justify-between mb-0.5">
          <span class="text-[9px] font-black uppercase tracking-widest text-zinc-500">${isEn ? 'Histogram vs Zero' : 'Histogram 相對零軸'}</span>
          <span class="text-[10px] text-zinc-500 font-mono">${isEn ? 'scaled to ±5' : '刻度 ±5'}</span>
        </div>
        <div class="macd-bar-wrap">
          <span class="macd-bar-label zero">0</span>
          <span class="macd-bar-label bear">${isEn ? 'BEAR' : '空頭'}</span>
          <span class="macd-bar-label bull">${isEn ? 'BULL' : '多頭'}</span>
          <div class="macd-bar-zero"></div>
          <div class="macd-bar-marker" style="left:${pct}%;color:${palette.hex};background:${palette.hex}">
            <div class="macd-bar-marker-label" style="color:${palette.hex}">${hist >= 0 ? '+' : ''}${hist.toFixed(2)}</div>
          </div>
        </div>
      </div>

      <!-- 4-quadrant regime map -->
      <div>
        <div class="text-[10px] font-black uppercase tracking-widest text-zinc-500 mb-1.5">
          ${isEn ? 'Four MACD Regimes' : '四個 MACD 狀態'}
        </div>
        <div class="macd-quadrant">${quadHTML}</div>
      </div>

      <!-- Personalised advice -->
      <div class="pt-3 border-t border-zinc-200 dark:border-zinc-800">
        <div class="text-[10px] font-black uppercase tracking-widest text-zinc-500 mb-1.5">
          ${isEn ? 'Your Situation' : '你目前的狀況'}
        </div>
        <div class="text-[11px] leading-relaxed mb-2" style="color:var(--text-main)">
          <span class="font-bold" style="color:${palette.hex}">${entry[titleKey]}</span> — ${entry[descKey]}
        </div>
        <div class="text-[11px] leading-relaxed" style="color:var(--text-main)">
          💡 ${entry[advKey]}
        </div>
      </div>
    `;

    document.getElementById('macd-modal').classList.remove('hidden');
    UI.icons();
}

function closeMacdPopup() {
    document.getElementById('macd-modal').classList.add('hidden');
}

/* ── Stage classification popup ──────────────────────────────── */
// Mirrors momentum.py _classify_stage logic so users see WHY a ticker is in a given stage.
// Rules (from the Python side):
//   Stage 2 uptrend:   ma20 > ma50 > ma200  AND price > ma20
//   Stage 4 downtrend: ma20 < ma50 < ma200  AND price < ma20
//   Stage 3 top:       ma50 > ma200  AND price < ma20  AND ma20 < ma50
//   Stage 1 basing:    otherwise
function _stageRules(r) {
    const p = r.price, m20 = r.ma_20, m50 = r.ma_50, m200 = r.ma_200;
    const tr = t();
    const yes = (ok, txt) => ({ok, txt});
    const rules = {
        'Stage 2 uptrend': [
            yes(m20 != null && m50 != null && m200 != null && m20 > m50 && m50 > m200,
                `MA 20 > MA 50 > MA 200 (${tr.stage_cond_trend || '趨勢排列正確'})`),
            yes(p != null && m20 != null && p > m20,
                `${tr.stage_cond_price_above_20 || '價格 > MA 20（短期動能向上）'}`),
        ],
        'Stage 4 downtrend': [
            yes(m20 != null && m50 != null && m200 != null && m20 < m50 && m50 < m200,
                `MA 20 < MA 50 < MA 200 (${tr.stage_cond_bear || '空頭排列'})`),
            yes(p != null && m20 != null && p < m20,
                tr.stage_cond_price_below_20 || '價格 < MA 20（短期跌勢中）'),
        ],
        'Stage 3 top': [
            yes(m50 != null && m200 != null && m50 > m200,
                `MA 50 > MA 200 (${tr.stage_cond_lt_still_up || '長期趨勢仍向上'})`),
            yes(p != null && m20 != null && p < m20,
                tr.stage_cond_price_below_20 || '價格 < MA 20（短期失守）'),
            yes(m20 != null && m50 != null && m20 < m50,
                `MA 20 < MA 50 (${tr.stage_cond_short_below_mid || '短期均線走弱'})`),
        ],
        'Stage 1 basing': [
            {ok: true, txt: tr.stage_1_note || '不符合 Stage 2/3/4，屬整理或基底期（無明確方向）'},
        ],
        'unknown': [
            {ok: false, txt: tr.stage_unknown_note || '歷史不足（< 200 天），無法分類'},
        ],
    };
    const next = {
        'Stage 2 uptrend':   tr.stage_transition_2_to_3 || '價格跌破 MA 20 → 轉向 Stage 3（需觀察 MA 50 是否續 > 200）',
        'Stage 3 top':       tr.stage_transition_3_to_4 || 'MA 50 跌破 MA 200 → 轉向 Stage 4 空頭排列',
        'Stage 4 downtrend': tr.stage_transition_4_to_1 || '價格 > MA 20 + MA 20 反轉向上 → 可能進入 Stage 1 築底',
        'Stage 1 basing':    tr.stage_transition_1_to_2 || 'MA 20 > MA 50 > MA 200 + 價格 > MA 20 → 進入 Stage 2 上升',
        'unknown':           '',
    };
    return {rules: rules[r.stage] || rules.unknown, nextCond: next[r.stage] || ''};
}

function _maStackHTML(r) {
    // Sort the 4 price-points by value descending, render each as a bar
    // with width relative to the max. Color-coded for quick visual parse.
    const items = [
        {label: 'Price',   value: r.price,  color: '#22c55e', key: 'price'},
        {label: 'MA 20',   value: r.ma_20,  color: '#3b82f6', key: 'ma20'},
        {label: 'MA 50',   value: r.ma_50,  color: '#eab308', key: 'ma50'},
        {label: 'MA 200',  value: r.ma_200, color: '#fb923c', key: 'ma200'},
    ].filter(x => x.value != null);
    if (!items.length) return '<div class="text-zinc-500">—</div>';

    items.sort((a, b) => b.value - a.value);
    const maxV = items[0].value;
    const minV = items[items.length - 1].value;
    const span = Math.max(maxV - minV, maxV * 0.01); // avoid zero-span flat bars

    return items.map(it => {
        const pct = ((it.value - minV) / span) * 80 + 20;  // 20-100% width
        const deltaPct = r.price != null && it.key !== 'price'
            ? ` <span class="text-[10px] text-zinc-500">(${((r.price / it.value - 1) * 100).toFixed(1)}%)</span>`
            : '';
        return `<div class="flex items-center gap-2">
            <span class="w-14 text-[10px] font-bold" style="color:${it.color}">${it.label}</span>
            <div class="flex-1 h-4 rounded" style="background:rgba(161,161,170,0.08)">
                <div class="h-full rounded" style="width:${pct}%; background:${it.color}; opacity:0.85"></div>
            </div>
            <span class="w-24 text-right font-mono font-bold">$${it.value.toFixed(2)}${deltaPct}</span>
        </div>`;
    }).join('');
}

function openStagePopup(r) {
    const tr = t();
    document.getElementById('stage-modal-title').textContent =
        `${r.ticker} — ${tr.stage_modal_title || '階段分類解釋'}`;

    const {rules, nextCond} = _stageRules(r);
    const stageColor = r.stage === 'Stage 2 uptrend'   ? '#22c55e'
                     : r.stage === 'Stage 3 top'       ? '#fbbf24'
                     : r.stage === 'Stage 4 downtrend' ? '#ef4444'
                     : r.stage === 'Stage 1 basing'    ? '#a1a1aa'
                     : '#71717a';

    const checklist = rules.map(x => {
        const icon = x.ok ? '☑' : '☐';
        const color = x.ok ? '#22c55e' : '#71717a';
        const dim = x.ok ? '' : 'opacity:0.6;';
        return `<div style="${dim}"><span style="color:${color};font-weight:bold;margin-right:6px">${icon}</span>${x.txt}</div>`;
    }).join('');

    document.getElementById('stage-modal-body').innerHTML = `
      <div class="flex items-center gap-2">
        <span class="text-[10px] font-black uppercase tracking-widest text-zinc-500">${tr.stage_modal_current || '目前階段'}</span>
        <span class="mlabel" style="color:${stageColor};background:${stageColor}1a;padding:2px 10px;border-radius:4px;font-size:11px">
          ${stageLabel(r.stage)}
        </span>
      </div>

      <div>
        <div class="text-[10px] font-black uppercase tracking-widest text-zinc-500 mb-2">
          ${tr.stage_modal_stack || 'MA 結構（由高至低排序）'}
        </div>
        <div class="space-y-1.5">${_maStackHTML(r)}</div>
      </div>

      <div>
        <div class="text-[10px] font-black uppercase tracking-widest text-zinc-500 mb-2">
          ${tr.stage_modal_conditions || '此階段成立的條件'}
        </div>
        <div class="space-y-1">${checklist}</div>
      </div>

      ${nextCond ? `<div class="pt-3 border-t border-zinc-200 dark:border-zinc-800">
        <div class="text-[10px] font-black uppercase tracking-widest text-zinc-500 mb-1.5">
          ${tr.stage_modal_transition || '何時會轉換到下一階段'}
        </div>
        <div class="text-zinc-400 leading-snug">${nextCond}</div>
      </div>` : ''}
    `;
    document.getElementById('stage-modal').classList.remove('hidden');
    UI.icons();
}

function closeStagePopup() {
    document.getElementById('stage-modal').classList.add('hidden');
}

/* ── Volume detail popup ─────────────────────────────────────── */
// Compute NY Eastern Time breakdown: current date/time, whether market is open,
// and the fraction of the regular session (9:30–16:00 ET) elapsed.
function _etNowInfo() {
    const nyStr = new Date().toLocaleString('en-US', {
        timeZone: 'America/New_York', hour12: false,
        year: 'numeric', month: '2-digit', day: '2-digit',
        hour: '2-digit', minute: '2-digit', weekday: 'short',
    });
    // "Mon, 04/19/2026, 11:45"
    const m = nyStr.match(/(\w{3}),\s*(\d{2})\/(\d{2})\/(\d{4}),\s*(\d{2}):(\d{2})/);
    if (!m) return { openNow: false, hhmm: nyStr, elapsed: 0, total: 390 };
    const [, wday, , , , hh, mm] = m;
    const mins = parseInt(hh, 10) * 60 + parseInt(mm, 10);
    const isWeekday = ['Mon','Tue','Wed','Thu','Fri'].includes(wday);
    const open = isWeekday && mins >= 570 && mins < 960;  // 9:30 - 16:00
    const elapsed = Math.max(0, mins - 570);
    return {
        openNow: open,
        hhmm:    `${hh}:${mm}`,
        weekday: wday,
        elapsed: Math.min(elapsed, 390),
        total:   390,
        fraction: Math.min(1, Math.max(0, elapsed / 390)),
    };
}

function _fmtShares(n) {
    if (n == null) return '—';
    if (n >= 1e9) return (n / 1e9).toFixed(2) + 'B';
    if (n >= 1e6) return (n / 1e6).toFixed(2) + 'M';
    if (n >= 1e3) return (n / 1e3).toFixed(1) + 'K';
    return String(Math.round(n));
}

function openVolumePopup(r) {
    const tr = t();
    const body = document.getElementById('volume-modal-body');
    document.getElementById('volume-modal-title').textContent =
        `${r.ticker} — ${tr.vol_modal_title || '量比細項'}`;

    const today = r.volume_today;
    const avg20 = r.avg_20d;
    const ratio = r.ratio_20d;
    const spike = r.spike_label;

    // Backend intraday state (applied at scan time — may differ from the client
    // "live projection" block below if ET clock has advanced since scan).
    let stateBanner = '';
    if (r.intraday_state === 'too_early') {
        stateBanner = `<div class="text-[11px] p-2 mb-2 rounded" style="background:rgba(113,113,122,0.12);color:#a1a1aa">
            ⏱ ${tr.vol_intraday_early || 'Intraday <30m at scan — volume signals suppressed'}
            <span class="text-zinc-500"> · elapsed ${r.elapsed_min || 0}m</span>
          </div>`;
    } else if (r.intraday_state === 'partial') {
        stateBanner = `<div class="text-[11px] p-2 mb-2 rounded" style="background:rgba(234,179,8,0.10);color:#eab308">
            ⏱ ${tr.vol_intraday_scaled || 'Intraday — ratio is projected from elapsed session'}
            <span class="text-zinc-500"> · elapsed ${r.elapsed_min || 0}m · ×${(390/(r.elapsed_min||390)).toFixed(2)} scale</span>
          </div>`;
    }

    const et = _etNowInfo();
    const isIntraday = et.openNow && et.fraction > 0.02 && et.fraction < 0.98;

    // Projection (only meaningful intraday):
    //   projected_today = today / fraction
    //   projected_ratio = projected_today / avg20
    let projBlock = '';
    if (isIntraday && today && avg20) {
        const projectedToday = today / et.fraction;
        const projectedRatio = projectedToday / avg20;
        const projSpike = projectedRatio >= 3.0 ? 'HEAVY_SPIKE'
                        : projectedRatio >= 2.0 ? 'MILD_SPIKE'
                        : 'NORMAL';
        const spikeColor = projSpike === 'HEAVY_SPIKE' ? '#ef4444'
                         : projSpike === 'MILD_SPIKE'  ? '#eab308'
                         : '#71717a';
        projBlock = `
          <div class="pt-3 border-t border-zinc-200 dark:border-zinc-800">
            <div class="text-[10px] font-black uppercase tracking-widest text-zinc-500 mb-2">
              ${tr.vol_modal_projected || '全日推估（盤中）'}
            </div>
            <div class="grid grid-cols-2 gap-y-1.5">
              <span class="text-zinc-500">${tr.vol_modal_et_now || '目前 ET 時間'}</span>
              <span class="font-mono text-right">${et.hhmm} ET (${et.weekday})</span>
              <span class="text-zinc-500">${tr.vol_modal_elapsed || '盤中經過比例'}</span>
              <span class="font-mono text-right">${(et.fraction * 100).toFixed(0)}% (${(et.elapsed/60).toFixed(2)}h / 6.5h)</span>
              <span class="text-zinc-500">${tr.vol_modal_projected_vol || '依速度推估全日量'}</span>
              <span class="font-mono text-right">${_fmtShares(projectedToday)} ${tr.vol_modal_shares || '股'}</span>
              <span class="text-zinc-500 font-bold">${tr.vol_modal_projected_ratio || '推估全日量比'}</span>
              <span class="font-mono text-right font-bold" style="color:${spikeColor}">${projectedRatio.toFixed(2)}× (${projSpike})</span>
            </div>
            <div class="mt-2 text-[10px] text-zinc-500 leading-snug">
              ⚠ ${tr.vol_modal_warning || '推估假設成交量線性分布；實際多為開盤與收盤集中，早盤估值常偏高。'}
            </div>
          </div>`;
    } else if (et.openNow) {
        projBlock = `<div class="pt-3 border-t border-zinc-200 dark:border-zinc-800 text-[10px] text-zinc-500">
            ${tr.vol_modal_too_early || '盤中經過比例過低或過高，推估不穩定，略過。'}
          </div>`;
    } else {
        projBlock = `<div class="pt-3 border-t border-zinc-200 dark:border-zinc-800 text-[10px] text-zinc-500">
            ${tr.vol_modal_closed || '當前非 ET 盤中（9:30–16:00），僅顯示收盤比率。'} ${et.hhmm} ET (${et.weekday})
          </div>`;
    }

    const ratioColor = _ratioColor(ratio);

    body.innerHTML = `
      ${stateBanner}
      <div class="grid grid-cols-2 gap-y-1.5">
        <span class="text-zinc-500">${tr.vol_modal_today || '今日成交量'}</span>
        <span class="font-mono text-right">${_fmtShares(today)} ${tr.vol_modal_shares || '股'}</span>
        <span class="text-zinc-500">${tr.vol_modal_avg20 || '20 日均量（不含今日）'}</span>
        <span class="font-mono text-right">${_fmtShares(avg20)} ${tr.vol_modal_shares || '股'}</span>
      </div>
      <div class="flex items-baseline justify-between pt-2 border-t border-zinc-200 dark:border-zinc-800">
        <span class="text-zinc-500 font-bold">${tr.vol_modal_ratio || '量比'}</span>
        <span class="font-mono text-lg font-black" style="color:${ratioColor}">
          ${ratio != null ? ratio.toFixed(2) + '×' : '—'}
          <span class="text-[10px] font-normal ml-2 text-zinc-500">${spike || ''}</span>
        </span>
      </div>
      ${projBlock}
    `;

    document.getElementById('volume-modal').classList.remove('hidden');
    UI.icons();
}

function closeVolumePopup() {
    document.getElementById('volume-modal').classList.add('hidden');
}

/* ── History modal ────────────────────────────────────────────── */
function openHistory(ticker) {
    const hist = _state.history[ticker] || [];
    document.getElementById('history-ticker-title').textContent = ticker;
    document.getElementById('history-subtitle').textContent =
        `${hist.length} ${t().history_title ? '' : ''} data points`;

    const modal = document.getElementById('history-modal');
    modal.classList.remove('hidden');

    const emptyEl = document.getElementById('history-empty');
    const canvas = document.getElementById('history-chart');
    if (hist.length < 2) {
        canvas.style.display = 'none';
        emptyEl.classList.remove('hidden');
        emptyEl.textContent = t().history_empty || 'No history';
        return;
    }
    canvas.style.display = 'block';
    emptyEl.classList.add('hidden');

    // Parse snap_id → date (YYYYMMDD_HHMM)
    const labels = hist.map(h => {
        const m = h.snap_id.match(/_(\d{4})(\d{2})(\d{2})_(\d{2})(\d{2})$/);
        return m ? `${m[2]}/${m[3]} ${m[4]}:${m[5]}` : h.snap_id;
    });
    const scores = hist.map(h => h.score);

    if (_state.historyChart) { _state.historyChart.destroy(); }
    _state.historyChart = new Chart(canvas.getContext('2d'), {
        type: 'line',
        data: {
            labels,
            datasets: [{
                label: 'Score',
                data: scores,
                borderColor: '#22c55e',
                backgroundColor: 'rgba(34,197,94,0.08)',
                fill: true,
                tension: 0.3,
                pointRadius: 3,
                pointBackgroundColor: '#22c55e',
            }],
        },
        options: {
            responsive: true, maintainAspectRatio: false,
            plugins: { legend: { display: false } },
            scales: {
                y: { min: 0, max: 100, ticks: { color: '#71717a', font: { size: 10 } },
                     grid:  { color: 'rgba(161,161,170,0.12)' } },
                x: { ticks: { color: '#71717a', font: { size: 9 }, maxRotation: 0 },
                     grid:  { display: false } },
            },
        },
    });
    UI.icons();
}

function closeHistory() {
    document.getElementById('history-modal').classList.add('hidden');
    if (_state.historyChart) { _state.historyChart.destroy(); _state.historyChart = null; }
}

/* ── Journal stats ────────────────────────────────────────────── */
function renderJournalStats(journal) {
    const tr = t();
    document.getElementById('journal-title').textContent = tr.journal_title || 'Journal stats';
    document.getElementById('journal-note').textContent  = tr.journal_note || '';
    document.getElementById('stats-signal-title').textContent = tr.stats_signal || 'By signal (20d win rate)';
    document.getElementById('stats-bin-title').textContent    = tr.stats_bin || 'By score bin';
    document.getElementById('stats-col-signal').textContent   = 'Signal';
    document.getElementById('stats-col-n').textContent        = tr.stats_n || 'n';
    document.getElementById('stats-col-winrate').textContent  = tr.stats_winrate || 'Win%';
    document.getElementById('stats-col-mean').textContent     = tr.stats_mean || 'Mean';
    document.getElementById('stats-col-median').textContent   = tr.stats_median || 'Median';

    const stats = journal?.stats;
    const hasData = stats && stats.by_signal
                  && Object.values(stats.by_signal).some(s => s['20d']?.n > 0);

    if (!hasData) {
        document.getElementById('journal-empty').classList.remove('hidden');
        document.getElementById('journal-content').classList.add('hidden');
        document.getElementById('journal-empty-text').textContent = tr.journal_empty || 'No data yet';
        return;
    }
    document.getElementById('journal-empty').classList.add('hidden');
    document.getElementById('journal-content').classList.remove('hidden');

    document.getElementById('journal-fills-label').textContent =
        `${tr.fills_label || 'Filled'}: 20d=${stats.fill_counts?.['20d'] || 0}`;

    // By signal
    const sigRows = [];
    Object.entries(stats.by_signal || {}).forEach(([sig, byH]) => {
        const d20 = byH['20d'];
        if (d20 && d20.n >= 3) sigRows.push([sig, d20]);
    });
    sigRows.sort((a, b) => b[1].win_rate - a[1].win_rate);
    document.getElementById('stats-signal-tbody').innerHTML = sigRows.slice(0, 12).map(([sig, d]) => {
        const wrPct = (d.win_rate * 100).toFixed(0);
        const wrColor = d.win_rate >= 0.6 ? '#22c55e'
                      : d.win_rate >= 0.5 ? '#86efac'
                      : d.win_rate >= 0.4 ? '#fbbf24' : '#ef4444';
        return `<tr class="stats-row">
            <td class="text-xs" title="${sig}">${sigLabel(sig)}</td>
            <td class="text-right text-xs text-zinc-400">${d.n}</td>
            <td>
                <div class="flex items-center gap-2">
                    <div class="winrate-bar flex-1" style="min-width:60px">
                        <div class="winrate-fill" style="width:${wrPct}%; background:${wrColor}"></div>
                    </div>
                    <span class="text-[10px] font-mono" style="color:${wrColor}">${wrPct}%</span>
                </div>
            </td>
            <td class="text-right font-mono text-xs" style="color:${d.mean >= 0 ? '#86efac' : '#fca5a5'}">${d.mean >= 0 ? '+' : ''}${d.mean}</td>
            <td class="text-right font-mono text-xs" style="color:${d.median >= 0 ? '#86efac' : '#fca5a5'}">${d.median >= 0 ? '+' : ''}${d.median}</td>
        </tr>`;
    }).join('');

    // By score bin
    const binOrder = ['90-100', '80-90', '70-80', '60-70', '50-60', '<50'];
    const binRows = binOrder
        .filter(b => stats.by_score_bin?.[b])
        .map(b => [b, stats.by_score_bin[b]]);
    document.getElementById('stats-bin-tbody').innerHTML = binRows.map(([bin, byH]) => {
        const d5 = byH['5d'] || {};
        const d20 = byH['20d'] || {};
        const d60 = byH['60d'] || {};
        const n = d20.n || d5.n || d60.n || 0;
        const wr = d20.win_rate != null ? `${(d20.win_rate*100).toFixed(0)}%` : '—';
        const fmt = v => v == null ? '—' : (v >= 0 ? '+' : '') + v.toFixed(1);
        return `<tr class="stats-row">
            <td class="text-xs font-mono font-bold">${bin}</td>
            <td class="text-right text-xs text-zinc-400">${n}</td>
            <td class="text-xs">${wr}</td>
            <td class="text-right font-mono text-xs">${fmt(d5.mean)}</td>
            <td class="text-right font-mono text-xs">${fmt(d20.mean)}</td>
            <td class="text-right font-mono text-xs">${fmt(d60.mean)}</td>
        </tr>`;
    }).join('');
}

/* ── Refresh action (async + polling) ────────────────────────── */
let _scanPollTimer = null;

function _fmtElapsed(sec) {
    const mm = String(Math.floor(sec / 60)).padStart(2, '0');
    const ss = String(sec % 60).padStart(2, '0');
    return `${mm}:${ss}`;
}

let _indicatorHideTimer = null;

// Palette for the scan card (left-border + pulse-dot + status tag).
const SCAN_CARD_COLORS = {
    running:  { fg: '#22c55e', bg: 'rgba(34,197,94,0.15)' },
    bridging: { fg: '#eab308', bg: 'rgba(234,179,8,0.15)' },
    done:     { fg: '#22c55e', bg: 'rgba(34,197,94,0.15)' },
    error:    { fg: '#ef4444', bg: 'rgba(239,68,68,0.15)' },
};

function showScanCard(status, phase, elapsedSec, progress, logTail) {
    const card = document.getElementById('scan-card');
    if (!card) return;
    card.classList.remove('hidden');

    const tr = t();
    const labels = {
        running:  tr.scan_card_running  || 'Scan running…',
        bridging: tr.scan_card_bridging || 'Refreshing data…',
        done:     tr.scan_card_done     || 'Scan complete',
        error:    tr.scan_card_error    || 'Scan failed',
    };
    const statusTags = {
        running: tr.banner_scanning || 'SCANNING',
        bridging:tr.banner_bridging || 'REFRESHING',
        done:    tr.banner_done     || 'DONE',
        error:   tr.banner_error    || 'ERROR',
    };
    const c = SCAN_CARD_COLORS[status] || SCAN_CARD_COLORS.running;

    card.style.setProperty('--scan-accent', c.fg);
    document.getElementById('scan-card-pulse').style.background = c.fg;
    // Pause the pulse when terminal
    document.getElementById('scan-card-pulse').style.animation =
        (status === 'done' || status === 'error') ? 'none' : '';

    // Title + progress inline (e.g. "Scan running… 150/503")
    let title = labels[status] || status;
    if (status === 'running' && progress && progress.total > 0) {
        title += `  ${progress.done || 0}/${progress.total}`;
    }
    document.getElementById('scan-card-title').textContent = title;

    const statusEl = document.getElementById('scan-card-status');
    statusEl.textContent = statusTags[status] || status.toUpperCase();
    statusEl.style.background = c.bg;
    statusEl.style.color      = c.fg;

    // Detail line: phase + cache/error counts
    const bits = [];
    if (phase) bits.push(phase);
    if (progress && progress.total > 0) {
        bits.push(`cache ${progress.cache_hits_count || 0}`);
        if (progress.errors_count) bits.push(`errors ${progress.errors_count}`);
    }
    document.getElementById('scan-card-detail').textContent = bits.join(' · ');

    document.getElementById('scan-card-elapsed').textContent = _fmtElapsed(elapsedSec || 0);

    // Log tail — only rebuild when changed, to preserve scroll position
    const logEl = document.getElementById('scan-card-log');
    if (logEl && Array.isArray(logTail)) {
        const text = logTail.join('\n');
        if (logEl.textContent !== text) {
            const pinnedToBottom = Math.abs(logEl.scrollHeight - logEl.clientHeight - logEl.scrollTop) < 40;
            logEl.textContent = text;
            if (pinnedToBottom) logEl.scrollTop = logEl.scrollHeight;
        }
    }

    // Dismiss only makes sense in terminal states
    const dismiss = document.getElementById('scan-card-dismiss');
    if (status === 'done' || status === 'error') dismiss.classList.remove('hidden');
    else                                         dismiss.classList.add('hidden');

    // Card stays up in terminal states — user dismisses via the ✕ (#scan-card-dismiss) button.
    if (_indicatorHideTimer) { clearTimeout(_indicatorHideTimer); _indicatorHideTimer = null; }
}

function hideScanCard() {
    const el = document.getElementById('scan-card');
    if (!el) return;
    el.classList.add('hidden');
    // Also collapse the log panel so next run starts collapsed
    document.getElementById('scan-card-body')?.classList.add('hidden');
    const expandLabel = document.getElementById('scan-card-expand-label');
    if (expandLabel) expandLabel.textContent = (t().scan_card_expand || '展開');
    if (_indicatorHideTimer) { clearTimeout(_indicatorHideTimer); _indicatorHideTimer = null; }
}

function toggleScanCardBody() {
    const body = document.getElementById('scan-card-body');
    if (!body) return;
    const open = body.classList.toggle('hidden') === false;
    const lbl = document.getElementById('scan-card-expand-label');
    if (lbl) lbl.textContent = open ? (t().scan_card_collapse || '收起') : (t().scan_card_expand || '展開');
    // When opening, scroll log to bottom so latest is visible
    if (open) {
        const logEl = document.getElementById('scan-card-log');
        if (logEl) logEl.scrollTop = logEl.scrollHeight;
    }
}

// Legacy aliases so existing callers keep working without churn
const showScanIndicator = showScanCard;
const hideScanIndicator = hideScanCard;
const showScanBanner    = showScanCard;
const hideScanBanner    = hideScanCard;

async function triggerRescan(overrideParams) {
    const btn = document.getElementById('refresh-momentum');
    if (btn.dataset.busy === '1') return;
    btn.dataset.busy = '1';
    btn.disabled = true;
    const label = document.getElementById('refresh-btn-label');
    const origLabel = label.textContent;
    label.textContent = (t().banner_scanning || '掃描中…');

    // Default: full S&P 500 + Nasdaq 100 + Watchlist scan.
    // Watchlist rescan passes {tickers:'AAPL,NVDA,...'}.
    const params = overrideParams
        ? { journal: true, ...overrideParams }
        : { universe: 'all', journal: true };

    try {
        const res = await fetch('/api/run-momentum-screen', {
            method:  'POST',
            headers: { 'Content-Type': 'application/json' },
            body:    JSON.stringify(params),
        });
        const j = await res.json();
        if (res.status === 409) {
            // Already running — just start polling
            UI.logToUI('Rescan: another scan already running, polling status…', 'warn');
        } else if (!res.ok) {
            throw new Error(j.error || `HTTP ${res.status}`);
        }
        startScanPolling(btn, label, origLabel);
    } catch (e) {
        UI.logToUI('Rescan failed: ' + e.message, 'error');
        showScanBanner('error', e.message, 0);
        btn.dataset.busy = '0';
        btn.disabled = false;
        label.textContent = origLabel;
    }
}

function startScanPolling(btn, label, origLabel) {
    if (_scanPollTimer) clearInterval(_scanPollTimer);

    const poll = async () => {
        try {
            const res = await fetch('/api/run-momentum-screen/status');
            if (!res.ok) throw new Error(`HTTP ${res.status}`);
            const s = await res.json();
            showScanBanner(s.status, s.phase || '', s.elapsed_sec || 0, {
                done: s.done, total: s.total,
                cache_hits_count: s.cache_hits_count,
                errors_count: s.errors_count,
            }, s.log_tail || []);

            if (s.status === 'done') {
                clearInterval(_scanPollTimer); _scanPollTimer = null;
                UI.logToUI(`Momentum: scan done → ${s.csv_path || 'no CSV'}`);
                try {
                    await DataStore.refresh();
                    await loadMomentumData();
                } catch (e) {
                    UI.logToUI('Reload after scan failed: ' + e.message, 'error');
                }
                btn.dataset.busy = '0';
                btn.disabled = false;
                label.textContent = origLabel;
            } else if (s.status === 'error') {
                clearInterval(_scanPollTimer); _scanPollTimer = null;
                UI.logToUI('Scan errored: ' + s.error, 'error');
                btn.dataset.busy = '0';
                btn.disabled = false;
                label.textContent = origLabel;
            }
        } catch (e) {
            UI.logToUI('Status poll failed: ' + e.message, 'error');
        }
    };

    poll();                                   // immediate first tick
    _scanPollTimer = setInterval(poll, 1500); // 1.5s cadence
}

async function checkExistingScan() {
    // On page load, if a scan is already in progress (from another tab or page),
    // show the banner so user sees it.
    try {
        const res = await fetch('/api/run-momentum-screen/status');
        if (!res.ok) return;
        const s = await res.json();
        if (s.status === 'running' || s.status === 'bridging') {
            const btn = document.getElementById('refresh-momentum');
            const label = document.getElementById('refresh-btn-label');
            const origLabel = label.textContent;
            btn.dataset.busy = '1';
            btn.disabled = true;
            showScanBanner(s.status, s.phase || '', s.elapsed_sec || 0, {
                done: s.done, total: s.total,
                cache_hits_count: s.cache_hits_count,
                errors_count: s.errors_count,
            }, s.log_tail || []);
            startScanPolling(btn, label, origLabel);
        }
    } catch (e) { /* server may not have endpoint yet — ignore */ }
}

/* ── Translations ─────────────────────────────────────────────── */
function translate() {
    const tr = t();
    const set = (id, val) => { const el = document.getElementById(id); if (el && val) el.textContent = val; };
    set('momentum-title',     tr.title);
    set('momentum-subtitle',  tr.subtitle);
    set('refresh-btn-label',  tr.refresh_btn);
    set('th-rank',      tr.col_rank);
    set('th-ticker',    tr.col_ticker);
    set('th-price',     tr.col_price);
    set('th-score',     tr.col_score);
    set('th-label',     tr.col_label);
    set('th-stage',     tr.col_stage);
    set('th-volume',    tr.col_volume);
    set('th-above-200', tr.col_above_200);
    set('th-rsi',       tr.col_rsi);
    set('th-signals',   tr.col_signals);
    set('th-short',     tr.col_short);
    set('th-macd',      tr.col_macd);
    const macdTh = document.getElementById('th-macd');
    if (macdTh && tr.col_macd_tip) macdTh.title = tr.col_macd_tip;
    set('no-data-text', tr.no_data);
    set('filter-title',          tr.filter_title);
    set('filter-reset-label',    tr.filter_reset);
    set('filter-score-label',    tr.filter_score);
    set('filter-rsi-label',      tr.filter_rsi);
    set('filter-stage-label',    tr.filter_stage);
    set('filter-sector-label',   tr.filter_sector);
    set('filter-search-label',   tr.filter_search);
    set('filter-preset-label',    tr.filter_preset_title);
    set('filter-match-label',     tr.filter_match_label);
    set('filter-advanced-label',  tr.filter_advanced);
    set('filter-req-sig-label',   tr.filter_req_sig);
    set('filter-req-warn-label',  tr.filter_req_warn);
    set('filter-excl-warn-label', tr.filter_excl_warn);
    set('filter-label-label',     tr.filter_label);
    set('filter-watchlist-scope-label', tr.filter_watchlist_scope);
    set('watchlist-btn-label',    tr.watchlist_btn_label);
    set('watchlist-modal-title',  tr.watchlist_modal_title);
    set('watchlist-modal-hint',   tr.watchlist_modal_hint);
    set('watchlist-add-label',    tr.watchlist_add_label);
    set('watchlist-current-label', tr.watchlist_current_label);
    set('watchlist-footer-hint',  tr.watchlist_footer_hint);
    set('watchlist-done-label',   tr.watchlist_done_label);
    set('watchlist-rescan-label', tr.watchlist_rescan_label);
    const wlInput = document.getElementById('watchlist-add-input');
    if (wlInput && tr.watchlist_add_placeholder) wlInput.placeholder = tr.watchlist_add_placeholder;
    // Re-render watchlist chips + scope chips on language toggle
    renderWatchlistScope();
    renderUniverseToggle();
    if (document.getElementById('watchlist-chips')) _renderWatchlistChips();

    // Re-label toggles based on i18n
    const uniToggle = document.getElementById('f-universe-toggle');
    if (uniToggle) {
        uniToggle.querySelector('[data-value="any"]').textContent = tr.universe_all || 'All';
        uniToggle.querySelector('[data-value="sp500"]').textContent = 'S&P 500';
        uniToggle.querySelector('[data-value="nasdaq100"]').textContent = 'Nasdaq 100';
        const soxBtn = uniToggle.querySelector('[data-value="sox"]');
        if (soxBtn) soxBtn.textContent = (UI.currentLang === 'zh') ? '費半 SOX' : 'PHLX SOX';
    }
    const wlToggle = document.getElementById('f-watchlist-toggle');
    if (wlToggle) {
        wlToggle.querySelector('[data-value="all"]').textContent     = tr.watchlist_scope_all     || 'Show All';
        wlToggle.querySelector('[data-value="only"]').textContent    = tr.watchlist_scope_only    || 'Only Watchlist';
        wlToggle.querySelector('[data-value="exclude"]').textContent = tr.watchlist_scope_exclude || 'Exclude Watchlist';
    }
    // Translate label dropdown options via labels_map
    const labelSel = document.getElementById('f-label');
    if (labelSel) {
        const anyOpt = labelSel.querySelector('option[value="any"]');
        if (anyOpt) anyOpt.textContent = tr.stage_any || 'Any';
        ['STRONGLY_BULLISH','BULLISH','NEUTRAL','WEAK','BEARISH'].forEach(k => {
            const opt = labelSel.querySelector(`option[value="${k}"]`);
            if (opt) opt.textContent = labelText(k);
        });
    }
    // Re-render preset row so tooltips translate on language toggle
    if (_state.rows.length) renderPresetRow();
    const search = document.getElementById('search-ticker');
    if (search && tr.search_placeholder) search.placeholder = tr.search_placeholder;
    const stageSel = document.getElementById('f-stage');
    if (stageSel && tr.stage_any) {
        const anyOpt = stageSel.querySelector('option[value="any"]');
        if (anyOpt) anyOpt.textContent = tr.stage_any;
        stageSel.querySelectorAll('option[value^="Stage"]').forEach(opt => {
            opt.textContent = stageLabel(opt.value);
        });
    }
    const sectorSel = document.getElementById('f-sector');
    if (sectorSel) {
        const anyOpt = sectorSel.querySelector('option[value="any"]');
        if (anyOpt) anyOpt.textContent = tr.stage_any || 'Any';
        SECTOR_KEYS.forEach(key => {
            const opt = sectorSel.querySelector(`option[value="${key}"]`);
            if (opt) opt.textContent = sectorLabel(key);
        });
    }
    const btn = document.getElementById('refresh-momentum');
    if (btn && tr.refresh_hint) btn.title = tr.refresh_hint;
}

/* ── Boot ─────────────────────────────────────────────────────── */
document.addEventListener('DOMContentLoaded', () => {
    UI.boot('momentum', { translate, reload: loadMomentumData });

    document.getElementById('refresh-momentum').addEventListener('click', triggerRescan);
    document.getElementById('history-close').addEventListener('click', closeHistory);
    document.getElementById('history-modal-bg').addEventListener('click', closeHistory);
    document.getElementById('volume-modal-close')?.addEventListener('click', closeVolumePopup);
    document.getElementById('volume-modal-bg')?.addEventListener('click', closeVolumePopup);
    document.getElementById('stage-modal-close')?.addEventListener('click', closeStagePopup);
    document.getElementById('stage-modal-bg')?.addEventListener('click', closeStagePopup);
    document.getElementById('rsi-modal-close')?.addEventListener('click', closeRsiPopup);
    document.getElementById('rsi-modal-bg')?.addEventListener('click', closeRsiPopup);
    document.getElementById('macd-modal-close')?.addEventListener('click', closeMacdPopup);
    document.getElementById('macd-modal-bg')?.addEventListener('click', closeMacdPopup);
    // Scan card — expand log / dismiss
    document.getElementById('scan-card-expand')?.addEventListener('click', toggleScanCardBody);
    document.getElementById('scan-card-dismiss')?.addEventListener('click', hideScanCard);
    document.addEventListener('keydown', e => {
        if (e.key === 'Escape') { closeHistory(); closeVolumePopup(); closeStagePopup(); closeRsiPopup(); closeMacdPopup(); }
    });

    // ── Filter panel bindings ───────────────────────────────────
    document.getElementById('f-min-score').addEventListener('input', e => {
        _state.filter.minScore = Number(e.target.value);
        document.getElementById('filter-score-val').textContent = `≥ ${_state.filter.minScore}`;
        renderTable();
    });
    const rsiBind = (id, key) => {
        document.getElementById(id).addEventListener('input', e => {
            const v = e.target.value.trim();
            _state.filter[key] = v === '' ? null : Number(v);
            renderTable();
        });
    };
    rsiBind('f-min-rsi', 'minRsi');
    rsiBind('f-max-rsi', 'maxRsi');
    document.getElementById('f-min-vol').addEventListener('input', e => {
        const v = e.target.value.trim();
        _state.filter.minVolumeRatio = v === '' ? null : Number(v);
        renderTable();
    });
    document.getElementById('f-only-hot').addEventListener('change', e => {
        _state.filter.onlyHotSectors = e.target.value === 'true';
        renderTable();
    });
    document.getElementById('f-stage').addEventListener('change', e => {
        _state.filter.stage = e.target.value;
        renderTable();
    });
    document.getElementById('f-sector').addEventListener('change', e => {
        _state.filter.sector = e.target.value;
        renderTable();
    });
    document.getElementById('f-label')?.addEventListener('change', e => {
        _state.filter.label = e.target.value;
        renderTable();
    });
    document.getElementById('search-ticker').addEventListener('input', e => {
        _state.filter.search = e.target.value;
        renderTable();
    });
    document.getElementById('filter-reset').addEventListener('click', () => {
        _state.filter = defaultFilter();
        renderFilterPanel();
        renderTable();
    });

    _bindSortHeaders();

    // Persist advanced-filter expand state across reloads
    const details = document.getElementById('filter-advanced');
    if (details) {
        if (localStorage.getItem('momentum_advanced_open') === '1') details.open = true;
        details.addEventListener('toggle', () => {
            localStorage.setItem('momentum_advanced_open', details.open ? '1' : '0');
        });
    }

    // Watchlist management — load count on boot + wire modal buttons
    _initWatchlistUI();

    loadMomentumData();
    checkExistingScan();
});

/* ── Watchlist management ──────────────────────────────────────────
 * `watchlist.txt` on disk stores user-picked non-SP500 tickers that get
 * merged into each momentum scan. This section owns the modal UI that
 * lets the user add/remove without touching the file.
 */
const _watchlistState = { tickers: [], dirty: false };

async function _refreshWatchlistBtn() {
    try {
        const r = await fetch('/api/momentum-watchlist');
        const j = await r.json();
        _watchlistState.tickers = j.tickers || [];
    } catch (e) {
        _watchlistState.tickers = [];
    }
    const countEl = document.getElementById('watchlist-count');
    if (countEl) countEl.textContent = `(${_watchlistState.tickers.length})`;
}

function _renderWatchlistChips() {
    const wrap = document.getElementById('watchlist-chips');
    const countEl = document.getElementById('watchlist-current-count');
    if (!wrap) return;
    const tr = t();
    if (_watchlistState.tickers.length === 0) {
        wrap.innerHTML = `<span class="text-[11px] text-zinc-500 italic">${tr.watchlist_empty || '尚未加入任何代號'}</span>`;
    } else {
        wrap.innerHTML = _watchlistState.tickers.map(tk =>
            `<span class="watchlist-chip" data-tk="${tk}">${tk} <span class="remove" data-remove="${tk}">×</span></span>`
        ).join('');
        wrap.querySelectorAll('[data-remove]').forEach(el => {
            el.onclick = () => _removeWatchlistTicker(el.dataset.remove);
        });
    }
    if (countEl) countEl.textContent = `(${_watchlistState.tickers.length})`;
}

function _showWatchlistError(msg) {
    const err = document.getElementById('watchlist-error');
    if (!err) return;
    err.textContent = msg;
    err.classList.remove('hidden');
    setTimeout(() => err.classList.add('hidden'), 2800);
}

async function _addWatchlistTicker() {
    const input = document.getElementById('watchlist-add-input');
    const raw = (input.value || '').trim().toUpperCase();
    if (!raw) return;
    if (!/^[A-Z][A-Z0-9.\-]{0,5}$/.test(raw)) {
        _showWatchlistError(`格式錯誤：${raw}（需 A-Z 開頭、1-6 字元）`);
        return;
    }
    try {
        const r = await fetch('/api/momentum-watchlist', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ ticker: raw }),
        });
        const j = await r.json();
        if (r.status === 409) {
            _showWatchlistError(`已存在：${raw}`);
            return;
        }
        if (!r.ok) {
            _showWatchlistError(j.error || `HTTP ${r.status}`);
            return;
        }
        _watchlistState.tickers = j.tickers || [];
        _watchlistState.dirty = true;
        input.value = '';
        _renderWatchlistChips();
        _refreshWatchlistBtn();
    } catch (e) {
        _showWatchlistError('新增失敗：' + e.message);
    }
}

async function _removeWatchlistTicker(ticker) {
    const chip = document.querySelector(`.watchlist-chip[data-tk="${ticker}"]`);
    if (chip) chip.classList.add('removing');
    try {
        const r = await fetch(`/api/momentum-watchlist/${encodeURIComponent(ticker)}`, {
            method: 'DELETE',
        });
        const j = await r.json();
        if (!r.ok) {
            _showWatchlistError(j.error || `HTTP ${r.status}`);
            if (chip) chip.classList.remove('removing');
            return;
        }
        _watchlistState.tickers = j.tickers || [];
        _watchlistState.dirty = true;
        _renderWatchlistChips();
        _refreshWatchlistBtn();
    } catch (e) {
        _showWatchlistError('移除失敗：' + e.message);
        if (chip) chip.classList.remove('removing');
    }
}

function _openWatchlistModal() {
    _watchlistState.dirty = false;
    _refreshWatchlistBtn().then(() => {
        _renderWatchlistChips();
        document.getElementById('watchlist-modal').classList.remove('hidden');
        document.getElementById('watchlist-add-input').focus();
        UI.icons();
    });
}
function _closeWatchlistModal() {
    document.getElementById('watchlist-modal').classList.add('hidden');
    document.getElementById('watchlist-error')?.classList.add('hidden');
}

function _initWatchlistUI() {
    _refreshWatchlistBtn();
    document.getElementById('watchlist-btn')?.addEventListener('click', _openWatchlistModal);
    document.getElementById('watchlist-modal-close')?.addEventListener('click', _closeWatchlistModal);
    document.getElementById('watchlist-modal-bg')?.addEventListener('click', _closeWatchlistModal);
    document.getElementById('watchlist-modal-done')?.addEventListener('click', _closeWatchlistModal);
    document.getElementById('watchlist-modal-rescan')?.addEventListener('click', () => {
        _closeWatchlistModal();
        const tickers = (_watchlistState.tickers || []).join(',');
        if (tickers) triggerRescan({ tickers });
        else triggerRescan();
    });
    document.getElementById('watchlist-add-btn')?.addEventListener('click', _addWatchlistTicker);
    document.getElementById('watchlist-add-input')?.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') { e.preventDefault(); _addWatchlistTicker(); }
    });
    // ESC closes modal
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') {
            const m = document.getElementById('watchlist-modal');
            if (m && !m.classList.contains('hidden')) _closeWatchlistModal();
        }
    });
}
