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
// Schema (mirrors AI verdict zone style on index/sector pages):
//   title / desc / hint — required
//   stages (optional)   — numeric tier table; each row {range:[lo,hi], range_label, tag, action, detail}
//                         showRadarTip highlights the row matching `liveValue` when provided.
const RADAR_TERMS = {
    mid_heat: {
        zh: {
            title: '中期熱度 · 1-3 月主題資金流',
            desc: 'theme-detector 從 FINVIZ 產業 momentum + volume + breadth 合成的 1-3 月熱度分數，反映「有沒有資金在滾這個題材」。冷的題材即使個股漂亮也容易被同類拖累。',
            stages: [
                { key: 'mh_hot',  range: [60,100], range_label: '> 60',  tag: '熱',   action: '主追擊區', detail: '產業有資金共振，題材 movers 往往一起漲，順勢加碼勝率高' },
                { key: 'mh_warm', range: [30,59],  range_label: '30-60', tag: '溫',   action: '選股',     detail: '題材未領跑但仍健康，挑高 RS 的 mover、避免重押' },
                { key: 'mh_cool', range: [0,29],   range_label: '< 30',  tag: '冷',   action: '避開',     detail: '產業缺乏資金，個股漂亮也會被同類拖累，除非有 idiosyncratic catalyst' },
            ],
            hint: '與 short_bull 互補：mid_heat 看「題材熱不熱」，short_bull 看「movers 接下來漲不漲」',
        },
        en: {
            title: 'Mid-term Heat · 1-3M theme money flow',
            desc: 'theme-detector composite from FINVIZ industry momentum/volume/breadth — answers "is money flowing into this theme?". Cold themes drag even good single-name setups.',
            stages: [
                { key: 'mh_hot',  range: [60,100], range_label: '> 60',  tag: 'Hot',  action: 'Hunt zone', detail: 'Capital flowing in, movers tend to rally together — momentum-add wins' },
                { key: 'mh_warm', range: [30,59],  range_label: '30-60', tag: 'Warm', action: 'Selective', detail: 'Theme not leading but still healthy — pick high-RS movers, avoid concentration' },
                { key: 'mh_cool', range: [0,29],   range_label: '< 30',  tag: 'Cool', action: 'Avoid',     detail: 'No theme money — clean charts get dragged with peers (unless idiosyncratic catalyst)' },
            ],
            hint: 'Complementary to short_bull: mid_heat = "is theme hot?", short_bull = "will movers rally?"',
        },
    },
    short_bull: {
        zh: {
            title: '短期看多率 · 5d 預測正報酬比例',
            desc: '主題內 5 個 mover 中，5 日預測為正報酬的 % 比例（已套用 regime factor 大盤調整）。直接代表「這個題材接下來 1 週多空共識」。',
            stages: [
                { key: 'sb_full',     range: [80,100], range_label: '80-100%', tag: '一致看多', action: '全題材搶', detail: '5 movers 全綠，題材內共識最強，分散買 1-2 檔最穩' },
                { key: 'sb_majority', range: [60,79],  range_label: '60-80%',  tag: '多數看多', action: '挑領頭',   detail: '5 中有 3-4 檔看多，挑 confidence 最高的 1 檔，避免重複曝險' },
                { key: 'sb_split',    range: [40,59],  range_label: '40-60%',  tag: '分歧',     action: '保守',     detail: '一半半，建議只買最強那 1 檔，倉位降標準 -25%' },
                { key: 'sb_bearish',  range: [0,39],   range_label: '< 40%',   tag: '看空',     action: '不進',     detail: '多數 movers 預測下跌，題材有問題，當週 skip' },
            ],
            hint: 'Theme card 預設按此 metric 排序；regime_factor < 1 時這個分數會被自動 dampen',
        },
        en: {
            title: 'Short Bullish Breadth · % movers w/ + 5d prediction',
            desc: '% of theme\'s 5 movers with positive 5d prediction (already adjusted by regime factor). Directly reflects 1-week directional consensus inside the theme.',
            stages: [
                { key: 'sb_full',     range: [80,100], range_label: '80-100%', tag: 'Unanimous', action: 'Spread bet',  detail: 'Nearly all movers green — strongest theme conviction, diversify across 1-2 names' },
                { key: 'sb_majority', range: [60,79],  range_label: '60-80%',  tag: 'Majority',  action: 'Pick leader', detail: '3-4 of 5 bullish — pick highest-confidence name, avoid redundant exposure' },
                { key: 'sb_split',    range: [40,59],  range_label: '40-60%',  tag: 'Split',     action: 'Cautious',    detail: 'Mixed — only buy the strongest, size −25%' },
                { key: 'sb_bearish',  range: [0,39],   range_label: '< 40%',   tag: 'Bearish',   action: 'Skip',        detail: 'Most movers negative — theme broken, sit out this week' },
            ],
            hint: 'Theme cards sort by this metric by default; regime_factor < 1 auto-dampens it',
        },
    },
    avg_conv: {
        zh: {
            title: '平均信心 · theme 內模型確定度',
            desc: '主題內 5 個 mover 的 5 日預測信心平均（0-1）。低 = 模型本身對這個題材的預測就沒把握；高 = 訊號穩定可信。',
            stages: [
                { key: 'ac_high', range: [0.55,1],    range_label: '> 0.55',    tag: '高',   action: '可重押',   detail: '模型訊號清晰，可考慮稍重倉位（仍守 stop）' },
                { key: 'ac_med',  range: [0.40,0.54], range_label: '0.40-0.55', tag: '中等', action: '標準操作', detail: '訊號一般，依規則進場、標準倉位、不要 outsmart 模型' },
                { key: 'ac_low',  range: [0,0.39],    range_label: '< 0.40',    tag: '低',   action: '不要進',   detail: '模型沒主見，幾乎隨機猜測，不應該下注' },
            ],
            hint: '與 confidence (個股) 區別：avg_conv 是同主題 5 movers 的平均、看題材整體可信度',
        },
        en: {
            title: 'Avg Conviction · model certainty across theme',
            desc: 'Average 5d prediction confidence across the theme\'s 5 movers (0-1). Low = model uncertain on this theme; high = signals stable and trustworthy.',
            stages: [
                { key: 'ac_high', range: [0.55,1],    range_label: '> 0.55',    tag: 'High', action: 'Size up',  detail: 'Clear signals — can size slightly larger (still respect stops)' },
                { key: 'ac_med',  range: [0.40,0.54], range_label: '0.40-0.55', tag: 'Med',  action: 'Standard', detail: 'Normal — execute the rule, standard size, no outsmarting' },
                { key: 'ac_low',  range: [0,0.39],    range_label: '< 0.40',    tag: 'Low',  action: 'Skip',     detail: 'Model has no conviction — essentially random, not actionable' },
            ],
            hint: 'Different from per-stock confidence: avg_conv = mean across 5 theme movers (theme-level trust)',
        },
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
        zh: {
            title: 'Confidence · 0-1 個股信心分數',
            desc: '7 個 component 加總的個股 5 日預測信心（點開 expanded panel 有 breakdown）。低信心 = 模型自己也不確定，不應重押。',
            stages: [
                { key: 'cf_high', range: [0.55,1],    range_label: '> 0.55',    tag: '強訊號', action: '可加碼',     detail: '模型對這檔個股訊號明確，可考慮重倉（仍嚴守 stop）' },
                { key: 'cf_med',  range: [0.40,0.54], range_label: '0.40-0.55', tag: '中等',   action: '標準操作',   detail: '訊號一般，依規則進場、標準倉位、不要 outsmart 模型' },
                { key: 'cf_low',  range: [0,0.39],    range_label: '< 0.40',    tag: '弱',     action: '僅供參考',   detail: '模型不確定，預測值僅供參考，不下單或最低倉位' },
            ],
            hint: '7 component breakdown: news / sector / momentum / atr / breadth / regime / history',
        },
        en: {
            title: 'Confidence · 0-1 per-stock signal strength',
            desc: 'Composite from 7 components for the 5d prediction (expand for breakdown). Low = model itself uncertain, do not size up.',
            stages: [
                { key: 'cf_high', range: [0.55,1],    range_label: '> 0.55',    tag: 'Strong', action: 'Size up',     detail: 'Clear signal — can size larger (still respect stops)' },
                { key: 'cf_med',  range: [0.40,0.54], range_label: '0.40-0.55', tag: 'Med',    action: 'Standard',    detail: 'Normal — execute the rule, standard size' },
                { key: 'cf_low',  range: [0,0.39],    range_label: '< 0.40',    tag: 'Weak',   action: 'Reference',   detail: 'Model uncertain — informational only, no trade or minimum size' },
            ],
            hint: '7 components: news / sector / momentum / ATR / breadth / regime / history (expand mover card)',
        },
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
        zh: {
            title: 'ATR · 14 日波動度',
            desc: 'Average True Range 14 日，以當前股價的 % 表示。決定倉位大小：高 ATR = 小倉、低 ATR = 大倉（讓每筆 trade 的金額損失上限固定）。',
            stages: [
                { key: 'da_high', range: [5,100],  range_label: '> 5%', tag: '高波動', action: '小倉位',   detail: 'Quantum / 小型股 / earnings 前後常見，confidence 自動降低、停損距離拉開' },
                { key: 'da_med',  range: [2,4.99], range_label: '2-5%', tag: '中等',   action: '標準倉位', detail: '一般 large-cap 範圍，可用標準倉位公式 (0.33 / ATR%)' },
                { key: 'da_low',  range: [0,1.99], range_label: '< 2%', tag: '低波動', action: '大倉位',   detail: 'utilities / staples 等防禦類，可開大倉位但 upside 也有限' },
            ],
            hint: '個股建議倉位 = 0.33 / ATR%（cap 0.5-5%），假設你接受每筆 0.5% 投組風險',
        },
        en: {
            title: 'ATR · 14-day volatility',
            desc: '14-day ATR as % of price. Drives position size: high ATR → small size, low ATR → large size (so each trade has a fixed dollar-risk ceiling).',
            stages: [
                { key: 'da_high', range: [5,100],  range_label: '> 5%', tag: 'High',   action: 'Small size',   detail: 'Quantum / small-cap / pre-post earnings — auto-lowers confidence, wider stop' },
                { key: 'da_med',  range: [2,4.99], range_label: '2-5%', tag: 'Medium', action: 'Standard',     detail: 'Typical large-cap range — use standard size formula (0.33 / ATR%)' },
                { key: 'da_low',  range: [0,1.99], range_label: '< 2%', tag: 'Low',    action: 'Larger size',  detail: 'Utilities / staples — can size up, but upside also limited' },
            ],
            hint: 'Position = 0.33 / ATR% (cap 0.5-5%); assumes 0.5% portfolio risk per trade',
        },
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
        zh: {
            title: 'Regime Factor · 大盤調整係數',
            desc: '依 SPY RSI 與 VIX 計算的 dampen/amplify 係數，作用在所有 bullish_breadth 訊號上。意義：「今天大盤適不適合做多」的乘數。',
            stages: [
                { key: 'rf_amplify', range: [1.01,5],    range_label: '> 1.0', tag: 'Amplify', action: '反彈機會', detail: 'VIX 高 + SPY RSI 超賣 → 大盤可能反彈，bullish 訊號被放大' },
                { key: 'rf_normal',  range: [1,1],       range_label: '= 1.0', tag: '正常',    action: '不調整',   detail: 'VIX 與 RSI 都在中性區間，訊號照原值' },
                { key: 'rf_dampen',  range: [0.5,0.99],  range_label: '< 1.0', tag: 'Dampen',  action: '降規模',   detail: 'SPY 過熱 (RSI > 70) 或 VIX 升高 → bullish 訊號自動降，避免追頂' },
            ],
            hint: '套用後的 short_bull 已經是 dampened 值，不需要再手動調整',
        },
        en: {
            title: 'Regime Factor · macro multiplier',
            desc: 'Dampen/amplify factor from SPY RSI + VIX, applied to all bullish_breadth signals. "Is today\'s tape right for going long?".',
            stages: [
                { key: 'rf_amplify', range: [1.01,5],    range_label: '> 1.0', tag: 'Amplify', action: 'Rebound chance', detail: 'High VIX + oversold SPY RSI → rebound likely, bullish signals amplified' },
                { key: 'rf_normal',  range: [1,1],       range_label: '= 1.0', tag: 'Normal',  action: 'No adjust',      detail: 'VIX and RSI both neutral — signals at face value' },
                { key: 'rf_dampen',  range: [0.5,0.99],  range_label: '< 1.0', tag: 'Dampen',  action: 'Cut size',       detail: 'SPY overbought (RSI > 70) or VIX spiking → bullish auto-dampened, avoid chasing tops' },
            ],
            hint: 'Applied short_bull is already dampened — no need to manually adjust',
        },
    },
    spy_rsi: {
        zh: {
            title: 'SPY RSI 14 · S&P 500 短線強弱',
            desc: 'S&P 500 14 日相對強弱指標 (0-100)。市場「累積動能」的衡量，極端值往往是反轉訊號。',
            stages: [
                { key: 'rsi_extreme_ob', range: [85,100], range_label: '> 85',  tag: '極端超買', action: '逆向防禦', detail: '歷史上 > 85 後 1-2 週多見修正，bullish 訊號夾雜頂部風險' },
                { key: 'rsi_ob',         range: [70,84],  range_label: '70-85', tag: '超買',     action: '謹慎',     detail: '強勢趨勢中可持續，但不應追高，等回到 65-70 再入場' },
                { key: 'rsi_normal',     range: [30,69],  range_label: '30-70', tag: '正常',     action: '主操作區', detail: '健康範圍，靠其他 driver 決策、不需額外 dampen' },
                { key: 'rsi_os',         range: [25,29],  range_label: '25-30', tag: '超賣',     action: '可分批買', detail: '回調買入區，逐步進場、avoid all-in' },
                { key: 'rsi_extreme_os', range: [0,24],   range_label: '< 25',  tag: '極端超賣', action: '逆向買點', detail: '崩盤級別 → 機構通常開始抄底，高勝率 contrarian 區（仍守 stop）' },
            ],
            hint: 'RSI 是短線指標 (14d)，不適合用來判斷大趨勢；配合 trend (MA200) 做最終決策',
        },
        en: {
            title: 'SPY RSI 14 · S&P 500 short-term strength',
            desc: 'S&P 500 14-day RSI (0-100). Measures market\'s "accumulated momentum" — extremes often mark reversals.',
            stages: [
                { key: 'rsi_extreme_ob', range: [85,100], range_label: '> 85',  tag: 'Extreme OB', action: 'Defensive',     detail: '> 85 historically followed by 1-2 week pullback, bullish signals mixed with top risk' },
                { key: 'rsi_ob',         range: [70,84],  range_label: '70-85', tag: 'Overbought', action: 'Caution',       detail: 'Strong trend can persist, but no chasing — wait for return to 65-70' },
                { key: 'rsi_normal',     range: [30,69],  range_label: '30-70', tag: 'Normal',     action: 'Main zone',     detail: 'Healthy range — trust other drivers, no extra dampening needed' },
                { key: 'rsi_os',         range: [25,29],  range_label: '25-30', tag: 'Oversold',   action: 'Scale in',      detail: 'Pullback buy zone — scale in, avoid all-in entries' },
                { key: 'rsi_extreme_os', range: [0,24],   range_label: '< 25',  tag: 'Extreme OS', action: 'Contrarian buy', detail: 'Crash-level → institutions usually step in, high-win-rate contrarian zone' },
            ],
            hint: 'RSI is short-term (14d); not for big-trend calls — pair with trend (MA200) for final decision',
        },
    },
    vix: {
        zh: {
            title: 'VIX · 30 日隱含波動率',
            desc: 'CBOE 計算的 SPX 期權 30 日年化隱含波動率。意義：投資者對未來 30 天波動的「預期」。極端值是反轉訊號。',
            stages: [
                { key: 'vix_panic',    range: [40,200],   range_label: '> 40',  tag: '投降底', action: '反向佈局',   detail: '極端恐慌通常臨近底部，高勝率 contrarian zone（FTD confirm 後再大量進）' },
                { key: 'vix_high',     range: [25,39.99], range_label: '25-40', tag: '緊張',   action: '防禦',       detail: '恐慌升溫，cash 至少 50%，僅持高 conviction，準備抄底訊號' },
                { key: 'vix_elevated', range: [20,24.99], range_label: '20-25', tag: '升高',   action: '謹慎',       detail: '市場開始緊張，倉位降 20-30%、停損收緊、避免追高' },
                { key: 'vix_normal',   range: [13,19.99], range_label: '13-20', tag: '正常',   action: '標準操作',   detail: '正常波動環境，無特別訊號，依其他指標決策' },
                { key: 'vix_calm',     range: [0,12.99],  range_label: '< 13',  tag: '自滿',   action: '留意頂部',   detail: '波動低、市場自滿 — 「過於平靜」也是頂部訊號之一，密切觀察' },
            ],
            hint: '參考：5 年中位數約 16-18，> 30 多在崩盤期間，> 40 為極端恐慌（COVID, 2008, etc.）',
        },
        en: {
            title: 'VIX · 30-day implied volatility',
            desc: 'CBOE\'s 30-day annualized implied volatility on SPX options — what investors expect the next 30 days to look like. Extremes are reversal signals.',
            stages: [
                { key: 'vix_panic',    range: [40,200],   range_label: '> 40',  tag: 'Capitulation', action: 'Contrarian zone', detail: 'Extreme fear usually near bottom — high-win-rate zone (full size only after FTD confirms)' },
                { key: 'vix_high',     range: [25,39.99], range_label: '25-40', tag: 'Tense',        action: 'Defensive',       detail: 'Fear rising, cash 50%+, high-conviction only, prep for capitulation buy' },
                { key: 'vix_elevated', range: [20,24.99], range_label: '20-25', tag: 'Elevated',     action: 'Caution',         detail: 'Market getting tense — cut size 20-30%, tighten stops, no chasing' },
                { key: 'vix_normal',   range: [13,19.99], range_label: '13-20', tag: 'Normal',       action: 'Standard',        detail: 'Normal vol environment — defer to other indicators' },
                { key: 'vix_calm',     range: [0,12.99],  range_label: '< 13',  tag: 'Complacent',   action: 'Watch top',       detail: 'Low vol, complacent market — "too calm" is a topping signal itself' },
            ],
            hint: 'Reference: 5y median ~16-18, > 30 in crash periods, > 40 = extreme fear (COVID, 2008)',
        },
    },
    yield_curve: {
        zh: {
            title: '殖利率曲線 T10Y2Y · 衰退領先指標',
            desc: '10 年公債殖利率 - 2 年公債殖利率（%）。歷史上負值倒掛領先衰退 12-18 個月，是最可靠的衰退領先指標之一。',
            stages: [
                { key: 'yc_steep',    range: [1,10],     range_label: '> 1.0',     tag: '健康陡峭', action: '進攻',   detail: '經濟擴張期典型曲線，銀行利潤好、信用寬鬆，risk-on 環境' },
                { key: 'yc_flat',     range: [0,0.99],   range_label: '0-1',       tag: '平坦',     action: '留意',   detail: '中性偏謹慎，曲線正在 flatten 中（未倒掛但有警訊）' },
                { key: 'yc_inverted', range: [-5,-0.01], range_label: '< 0 (倒掛)', tag: '倒掛',     action: '降槓桿', detail: '12-18 個月衰退預警，歷史上 7/9 次倒掛後出現衰退（COVID 提早結束、1995 軟著陸是例外）' },
            ],
            hint: '倒掛 ≠ 立即崩盤；通常從倒掛到實際衰退有 12-18 月 lead time，這段期間股市仍可能上漲',
        },
        en: {
            title: 'Yield Curve T10Y2Y · recession leading indicator',
            desc: '10Y minus 2Y Treasury yield (%). Inversion historically leads recessions by 12-18 months — one of the most reliable leading indicators.',
            stages: [
                { key: 'yc_steep',    range: [1,10],     range_label: '> 1.0',     tag: 'Steep',    action: 'Attack',  detail: 'Typical expansion shape — bank profits good, credit easy, risk-on environment' },
                { key: 'yc_flat',     range: [0,0.99],   range_label: '0-1',       tag: 'Flat',     action: 'Watch',   detail: 'Neutral-cautious, curve flattening (not yet inverted but warning)' },
                { key: 'yc_inverted', range: [-5,-0.01], range_label: '< 0 (inv)', tag: 'Inverted', action: 'De-risk', detail: '12-18m recession warning — 7/9 inversions historically preceded recession (COVID, 1995 soft-landing exceptions)' },
            ],
            hint: 'Inversion ≠ immediate crash; usually 12-18m lead time before recession, market often rallies in between',
        },
    },
    credit_spread: {
        zh: {
            title: '信用利差百分位 · 信用市場壓力',
            desc: '高收益債利差在過去 1 年的百分位。直接反映「市場願不願意借錢給弱信用公司」 — 高百分位 = 信用緊縮、risk-off 跡象。',
            stages: [
                { key: 'cs_easy',   range: [0,29],   range_label: '< 30',  tag: '寬鬆', action: '滿倉可',     detail: '市場願意承擔信用風險，risk-on 環境，公司債發行容易' },
                { key: 'cs_normal', range: [30,74],  range_label: '30-75', tag: '正常', action: '標準操作',   detail: '信用市場中性，無特別風險訊號' },
                { key: 'cs_stress', range: [75,100], range_label: '> 75',  tag: '緊縮', action: '降風險',     detail: '信用市場緊縮 (risk-off 警示)，弱信用公司發債困難，潛在違約風險上升' },
            ],
            hint: '信用利差通常領先股市轉折 1-2 月；歷史上 spread 暴衝多在 2008 / COVID / 2022 risk-off 期間',
        },
        en: {
            title: 'Credit Spread Percentile (1Y) · credit stress',
            desc: 'High-yield credit spread vs past year percentile. Direct read on "does the market want to lend to weak credits?" — high = credit tightening, risk-off.',
            stages: [
                { key: 'cs_easy',   range: [0,29],   range_label: '< 30',  tag: 'Easy',   action: 'Full size', detail: 'Market willing to take credit risk, risk-on, easy debt issuance' },
                { key: 'cs_normal', range: [30,74],  range_label: '30-75', tag: 'Normal', action: 'Standard',  detail: 'Credit market neutral, no special risk signal' },
                { key: 'cs_stress', range: [75,100], range_label: '> 75',  tag: 'Stress', action: 'De-risk',   detail: 'Credit tightening (risk-off warning), weak credits struggle to issue, default risk rising' },
            ],
            hint: 'Credit spreads often lead equity turns by 1-2 months; spikes historically in 2008 / COVID / 2022 risk-off periods',
        },
    },
};

function getTermTip(key) {
    const lang = UI.currentLang === 'en' ? 'en' : 'zh';
    return RADAR_TERMS[key]?.[lang] || null;
}

// ── Stage helpers (mirrors signal-tip-tooltip in utils.js) ──────────
// Color dot per tier — same palette as the AI verdict zone tooltips for
// visual consistency across pages.
const RADAR_STAGE_DOTS = {
    // mid_heat
    mh_hot: '🟢', mh_warm: '🟡', mh_cool: '🔴',
    // short_bull
    sb_full: '🟢', sb_majority: '🟡', sb_split: '🟠', sb_bearish: '🔴',
    // avg_conv / confidence
    ac_high: '🟢', ac_med: '🟡', ac_low: '🔴',
    cf_high: '🟢', cf_med: '🟡', cf_low: '🔴',
    // driver_atr (high vol = caution; low vol = green for sizing)
    da_high: '🟠', da_med: '🟡', da_low: '🟢',
    // factor (amplify = good rebound, dampen = caution)
    rf_amplify: '🟢', rf_normal: '🟡', rf_dampen: '🟠',
    // SPY RSI (extreme contrarian zones tagged green for the contrarian opportunity, red for top risk)
    rsi_extreme_ob: '🔴', rsi_ob: '🟠', rsi_normal: '🟢', rsi_os: '🟡', rsi_extreme_os: '🟢',
    // VIX
    vix_panic: '🟢', vix_high: '🟠', vix_elevated: '🟡', vix_normal: '🟢', vix_calm: '🟡',
    // yield curve
    yc_steep: '🟢', yc_flat: '🟡', yc_inverted: '🔴',
    // credit spread
    cs_easy: '🟢', cs_normal: '🟡', cs_stress: '🔴',
};

function classifyRadarStage(stages, value) {
    if (value == null || value === '' || isNaN(value)) return null;
    const n = Number(value);
    return stages.find(s => n >= s.range[0] && n <= s.range[1]) || null;
}

function renderRadarStageRows(stages, activeStage) {
    return stages.map(s => {
        const active = activeStage && s.key === activeStage.key;
        return `<div class="rtt-stage-row${active ? ' rtt-stage-active' : ''}">
            <span class="rtt-stage-dot">${RADAR_STAGE_DOTS[s.key] || '⚪'}</span>
            <span class="rtt-stage-range">${s.range_label}</span>
            <span class="rtt-stage-tag">${s.tag}</span>
            <span class="rtt-stage-action">${s.action}</span>
            <div class="rtt-stage-detail">${s.detail}</div>
        </div>`;
    }).join('');
}

// Tooltip element handler (mirrors momentum's mom-pill-tooltip pattern).
// When `entry.stages` is present, also render a stage-row table — the active
// row is determined by the data-tip-value attribute (set by the renderer that
// emits the hover target). For tips without a live numeric value, no row is
// highlighted but the table still serves as a "interpretation guide".
let _radarHideTimer = null;
function showRadarTip(el) {
    const tip = $('radar-term-tooltip');
    if (!tip) return;
    const key = el.dataset.radarTip;
    const entry = getTermTip(key);
    if (!entry) return;
    let stagesHTML = '';
    if (Array.isArray(entry.stages) && entry.stages.length) {
        const liveValue = el.dataset.tipValue;  // optional — set by renderer for live highlight
        const active = classifyRadarStage(entry.stages, liveValue);
        stagesHTML = `<div class="rtt-stages">${renderRadarStageRows(entry.stages, active)}</div>`;
    }
    tip.innerHTML = `
        <div class="rtt-title">${escapeHtml(entry.title)}</div>
        <div class="rtt-desc">${entry.desc}</div>
        ${stagesHTML}
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

            <!-- V2.12.0 — mini intraday heatmap (filled by loadThemeHeatmap) -->
            <div class="mini-heatmap-slot" data-theme-name="${escapeHtml(theme.name)}"
                 style="height: 110px; margin-top: 6px; position: relative; border-radius: 4px; overflow: hidden;">
                <div class="text-[9px] text-zinc-600 absolute inset-0 flex items-center justify-center">即時熱力圖載入中…</div>
            </div>

            <div class="flex items-center justify-end text-[9px] mt-1 pt-1 border-t border-zinc-800/50">
                <span class="text-indigo-400">${escapeHtml(isExpanded ? (t().card_movers_close || '▲ close') : (t().card_movers_open || '▼ movers'))}</span>
            </div>
        `;
        // Click on card body (not on heatmap tile) toggles expansion
        card.addEventListener('click', (e) => {
            if (e.target.closest('.mini-heatmap-slot')) return;   // ticker tile handles its own click
            toggleExpand(theme.name);
        });
        grid.appendChild(card);
    });
    // After theme cards mount, fill mini heatmaps
    if (_lastThemeHeatmap) renderAllThemeMiniHeatmaps(_lastThemeHeatmap.themes);
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
    // V2.12.0 — explanation banner (user feedback: 不知道 top 5 movers 意義)
    const isZh = UI.currentLang === 'zh';
    const explainText = isZh
        ? '排序方式：模型對該主題內個股的「未來 5 日預期報酬 × 信心度」由高到低排序，取前 5。代表「玩這個主題最乾淨的進場點」。'
        : 'Ranked by model\'s 5-day predicted return × confidence (descending). The top 5 represent the cleanest entry candidates within this theme.';
    const explainHtml = `
        <div class="col-span-full mb-2 p-2 rounded border border-indigo-400/20 bg-indigo-500/5 text-[10px] text-zinc-400 leading-relaxed flex items-start gap-2">
            <i data-lucide="info" class="w-3 h-3 text-indigo-400 mt-0.5 shrink-0"></i>
            <span>${explainText}</span>
        </div>`;
    const moversHtml = (theme.top_movers || []).map(m => renderMoverCard(m)).join('');
    wrap.innerHTML = explainHtml + (moversHtml || `<div class="text-zinc-500 text-sm">${noMovers}</div>`);
    if (window.lucide?.createIcons) window.lucide.createIcons();
}

// ── Per-mover card (strict §11.D) ─────────────────────────────
// V2.12.0 — enrichment pill row (market_cap_tier + earnings/quality/smart-money/analyst)
function renderEnrichmentPills(enr, finalScore, rawScore) {
    if (!enr || Object.keys(enr).length === 0) return '';
    const isZh = UI.currentLang === 'zh';
    const pills = [];

    // Market-cap tier — small/micro highlighted (user wants to spot these in top picks)
    const tier = enr.market_cap_tier;
    if (tier && tier !== 'unknown') {
        const tierMap = {
            large_cap:  { label: isZh ? '大型股' : 'Large',  bg: 'rgba(100,116,139,0.15)', fg: '#94a3b8' },
            mid_cap:    { label: isZh ? '中型股' : 'Mid',    bg: 'rgba(59,130,246,0.18)',  fg: '#60a5fa' },
            small_cap:  { label: isZh ? '⚡小型股' : '⚡Small', bg: 'rgba(245,158,11,0.22)', fg: '#fbbf24' },
            micro_cap:  { label: isZh ? '⚡⚡微型股' : '⚡⚡Micro', bg: 'rgba(239,68,68,0.20)', fg: '#fca5a5' },
        };
        const tinfo = tierMap[tier] || tierMap.large_cap;
        const mcUsd = enr.market_cap_usd;
        const mcStr = mcUsd ? (mcUsd >= 1e12 ? `$${(mcUsd/1e12).toFixed(2)}T`
                               : mcUsd >= 1e9 ? `$${(mcUsd/1e9).toFixed(1)}B`
                               : `$${(mcUsd/1e6).toFixed(0)}M`) : '';
        const tip = isZh ? `市值 ${mcStr}` : `Market cap ${mcStr}`;
        pills.push(`<span class="enr-pill" title="${escapeHtml(tip)}" style="background:${tinfo.bg};color:${tinfo.fg};font-weight:700">${escapeHtml(tinfo.label)} ${mcStr}</span>`);
    }

    // Earnings landmine
    const e = enr.earnings || {};
    if (e.within_5d) {
        const t = isZh ? `📅 ${e.days_to_earnings}d 內財報` : `📅 Earnings in ${e.days_to_earnings}d`;
        pills.push(`<span class="enr-pill" title="${escapeHtml(e.next_date || '')}" style="background:rgba(239,68,68,0.20);color:#fca5a5;font-weight:700">${escapeHtml(t)}</span>`);
    } else if (e.within_10d) {
        const t = isZh ? `📅 ${e.days_to_earnings}d` : `📅 ${e.days_to_earnings}d`;
        pills.push(`<span class="enr-pill" title="${escapeHtml(e.next_date || '')}" style="background:rgba(245,158,11,0.18);color:#fbbf24">${escapeHtml(t)}</span>`);
    }

    // Quality
    const q = enr.quality || {};
    if (q.red_flag) {
        const tip = `Altman Z=${q.altmanZScore?.toFixed(1) ?? '?'}, Piotroski F=${q.piotroskiScore ?? '?'}`;
        pills.push(`<span class="enr-pill" title="${escapeHtml(tip)}" style="background:rgba(239,68,68,0.18);color:#fca5a5">${isZh ? '⚠ 品質紅旗' : '⚠ Quality risk'}</span>`);
    } else if (q.premium) {
        const tip = `Altman Z=${q.altmanZScore?.toFixed(1) ?? '?'}, Piotroski F=${q.piotroskiScore ?? '?'}`;
        pills.push(`<span class="enr-pill" title="${escapeHtml(tip)}" style="background:rgba(34,197,94,0.18);color:#86efac">${isZh ? '✓ 品質佳' : '✓ Premium quality'}</span>`);
    }

    // Smart money
    const sm = enr.smart_money || {};
    if (sm.insider_signal === 'buying') {
        pills.push(`<span class="enr-pill" style="background:rgba(34,197,94,0.18);color:#86efac" title="Insider net-buy 90d">${isZh ? '💰 內部人買' : '💰 Insider buy'}</span>`);
    } else if (sm.insider_signal === 'selling') {
        pills.push(`<span class="enr-pill" style="background:rgba(245,158,11,0.18);color:#fbbf24" title="Insider net-sell 90d">${isZh ? '↓ 內部人賣' : '↓ Insider sell'}</span>`);
    }
    if (sm.institutional_accumulation) {
        const t = isZh ? '🏦 機構加碼' : '🏦 Inst accum';
        pills.push(`<span class="enr-pill" style="background:rgba(34,197,94,0.15);color:#86efac" title="Institutional QoQ +${sm.institutional_pct_delta?.toFixed(1) || '?'}%">${escapeHtml(t)}</span>`);
    }

    // Analyst
    const a = enr.analyst || {};
    if (a.upside_pct != null) {
        const up = a.upside_pct;
        const color = up >= 10 ? '#86efac' : up >= 0 ? '#a1a1aa' : '#fca5a5';
        const bg = up >= 10 ? 'rgba(34,197,94,0.15)' : up >= 0 ? 'rgba(100,116,139,0.15)' : 'rgba(239,68,68,0.15)';
        const tip = a.pt_target ? `PT $${a.pt_target} vs $${a.current_price}` : '';
        pills.push(`<span class="enr-pill" title="${escapeHtml(tip)}" style="background:${bg};color:${color}">PT ${up >= 0 ? '+' : ''}${up.toFixed(1)}%</span>`);
    }
    if (a.tailwind) {
        pills.push(`<span class="enr-pill" style="background:rgba(34,197,94,0.15);color:#86efac" title="Recent rating upgrades > downgrades">${isZh ? '↑ 評等升' : '↑ Upgrades'}</span>`);
    }

    // Score multiplier indicator (small grey, only when meaningful)
    const m = enr.enrichment_multiplier;
    if (m != null && Math.abs(m - 1.0) > 0.05 && finalScore != null && rawScore != null) {
        const tip = isZh
            ? `原始 ${rawScore.toFixed(2)} × 加成 ${m.toFixed(2)} = ${finalScore.toFixed(2)}`
            : `Raw ${rawScore.toFixed(2)} × ${m.toFixed(2)} = ${finalScore.toFixed(2)}`;
        const color = m > 1.0 ? '#86efac' : '#fbbf24';
        pills.push(`<span class="enr-pill" title="${escapeHtml(tip)}" style="background:rgba(63,63,70,0.5);color:${color};font-family:monospace;font-size:9px">×${m.toFixed(2)}</span>`);
    }

    return pills.join('');
}

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
    // V2.12.0 — enrichment pills (market cap tier + earnings/quality/smart-money/analyst)
    const enr = mover.enrichment || {};
    const enrPills = renderEnrichmentPills(enr, mover.final_score, mover.raw_score);

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

            ${enrPills ? `<div class="enrichment-pills flex flex-wrap gap-1">${enrPills}</div>` : ''}

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

    // V2.12.0 — bootstrap per-theme mini heatmaps (after theme grid renders)
    setTimeout(() => { loadThemeHeatmap(); startThemeHeatmapPolling(); }, 800);
});


/* ════════════════════════════════════════════════════════════════════
 * V2.12.0 — Per-theme Mini Heatmap + K-line drill (radar page)
 *
 * Each theme card embeds a small D3 treemap of its representative_stocks
 * (from theme-detector cache, joined with /api/heatmap/data quotes).
 * Data source: /api/theme-heatmap (server-side composite, 3min cache).
 *
 * Click ticker tile → /api/heatmap/intraday/<TICKER> → Chart.js K-line +
 * volume; 15s polling while market open, single-watcher (new click cancels).
 * ════════════════════════════════════════════════════════════════════ */

const THEME_HEATMAP_POLL_MS = 180000;   // 3 min
const RADAR_KLINE_POLL_MS   = 15000;    // 15s open / 5min closed (server enforces TTL)

let _lastThemeHeatmap   = null;          // {themes: [...], market_open, ...}
let _themeHeatmapTimer  = null;

let _radarKlineTicker   = null;
let _radarKlineTimer    = null;
let _radarKlineChart    = null;
let _radarVolumeChart   = null;

function _radarHeatmapColorFor(changePct) {
    if (changePct === null || changePct === undefined || isNaN(changePct)) return '#d4d4d8';
    const clamped = Math.max(-3, Math.min(3, changePct));
    const t = Math.abs(clamped) / 3;
    const center = [212, 212, 216];
    let mid, peak;
    if (clamped >= 0) {
        mid  = [134, 239, 172];
        peak = [16, 185, 129];
    } else {
        mid  = [252, 165, 165];
        peak = [239, 68, 68];
    }
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

function _radarHeatmapTextColor(changePct) {
    if (changePct === null || isNaN(changePct)) return '#52525b';
    return Math.abs(changePct) >= 1.8 ? '#ffffff' : '#18181b';
}

function _radarTruncate(text, availPx, charPx) {
    if (!text) return '';
    const maxChars = Math.floor(availPx / charPx);
    if (maxChars < 2) return '';
    if (text.length <= maxChars) return text;
    return text.slice(0, Math.max(1, maxChars - 1)) + '…';
}

function _radarFormatMcap(mcap) {
    if (!mcap) return '--';
    if (mcap >= 1e12) return (mcap / 1e12).toFixed(2) + 'T';
    if (mcap >= 1e9)  return (mcap / 1e9).toFixed(1)  + 'B';
    if (mcap >= 1e6)  return (mcap / 1e6).toFixed(0)  + 'M';
    return mcap.toFixed(0);
}

function _radarFormatVol(v) {
    if (!v) return '--';
    if (v >= 1e9) return (v / 1e9).toFixed(2) + 'B';
    if (v >= 1e6) return (v / 1e6).toFixed(2) + 'M';
    if (v >= 1e3) return (v / 1e3).toFixed(1) + 'K';
    return String(v);
}

async function loadThemeHeatmap() {
    try {
        const r = await fetch('/api/theme-heatmap');
        if (!r.ok) throw new Error('HTTP ' + r.status);
        const data = await r.json();
        _lastThemeHeatmap = data;
        renderAllThemeMiniHeatmaps(data.themes || []);
    } catch (e) {
        console.error('Theme heatmap load error:', e.message);
    }
}

function renderAllThemeMiniHeatmaps(themes) {
    const byName = new Map(themes.map(t => [t.name, t]));
    document.querySelectorAll('.mini-heatmap-slot').forEach(slot => {
        const name = slot.dataset.themeName;
        const theme = byName.get(name);
        if (!theme || !theme.tickers || !theme.tickers.length) {
            slot.innerHTML = `<div class="text-[9px] text-zinc-600 absolute inset-0 flex items-center justify-center">無覆蓋資料</div>`;
            return;
        }
        renderThemeMiniHeatmap(slot, theme);
    });
}

function renderThemeMiniHeatmap(container, theme) {
    if (!window.d3) return;
    container.innerHTML = '';
    const w = container.clientWidth;
    const h = container.clientHeight;
    if (w <= 0 || h <= 0) return;

    const root = {
        name: theme.name,
        children: theme.tickers.map(t => ({ ...t, name: t.ticker })),
    };
    const hierarchy = d3.hierarchy(root)
        // Use sqrt of market_cap so smaller-cap tiles aren't crushed; +1 floor avoids 0
        .sum(d => Math.sqrt(Math.max(1, d.market_cap || 1)))
        .sort((a, b) => (b.value || 0) - (a.value || 0));

    d3.treemap()
        .size([w, h])
        .paddingInner(1)
        .paddingOuter(1)
        .round(true)(hierarchy);

    const svg = d3.select(container)
        .append('svg')
        .attr('width', w).attr('height', h)
        .style('display', 'block')
        .style('font-family', 'Inter, sans-serif');

    const cells = svg.selectAll('g.cell')
        .data(hierarchy.leaves())
        .enter().append('g')
        .attr('class', 'cell')
        .attr('transform', d => `translate(${d.x0},${d.y0})`)
        .style('cursor', 'pointer');

    cells.append('rect')
        .attr('width', d => Math.max(0, d.x1 - d.x0))
        .attr('height', d => Math.max(0, d.y1 - d.y0))
        .attr('fill', d => _radarHeatmapColorFor(d.data.change_pct))
        .attr('stroke', 'rgba(0,0,0,0.4)')
        .attr('stroke-width', 0.5);

    cells.each(function(d) {
        const cw = d.x1 - d.x0, ch = d.y1 - d.y0;
        const ticker = d.data.ticker || '';
        if (cw < 18 || ch < 12) return;       // too small for label
        const baseSize = Math.min(11, Math.max(7, Math.sqrt(cw * ch) / 4.5));
        const fill = _radarHeatmapTextColor(d.data.change_pct);
        const pct = d.data.change_pct;
        const showPct = ch >= baseSize * 2 + 4 && cw >= 30;
        if (showPct) {
            d3.select(this).append('text')
                .attr('x', cw / 2).attr('y', ch / 2 - 1)
                .attr('text-anchor', 'middle').attr('font-size', baseSize)
                .attr('font-weight', 800).attr('fill', fill)
                .text(ticker);
            d3.select(this).append('text')
                .attr('x', cw / 2).attr('y', ch / 2 + baseSize - 1)
                .attr('text-anchor', 'middle').attr('font-size', baseSize * 0.78)
                .attr('font-weight', 600).attr('fill', fill)
                .text(pct == null ? '--' : (pct >= 0 ? '+' : '') + pct.toFixed(2) + '%');
        } else {
            d3.select(this).append('text')
                .attr('x', cw / 2).attr('y', ch / 2 + baseSize / 3)
                .attr('text-anchor', 'middle').attr('font-size', baseSize)
                .attr('font-weight', 800).attr('fill', fill).text(ticker);
        }
    });

    cells.on('mouseenter', function(event, d) { _radarShowTooltip(d.data, event); event.stopPropagation(); })
         .on('mousemove',  function(event)    { _radarPositionTooltip(event); })
         .on('mouseleave', function()         { _radarHideTooltip(); })
         .on('click',      function(event, d) {
             event.stopPropagation();    // don't trigger card's toggleExpand
             selectRadarKline(d.data);
         });
}

function _radarShowTooltip(ticker, event) {
    const tip = document.getElementById('radar-heatmap-tooltip');
    if (!tip) return;
    const pct = ticker.change_pct;
    const pctColor = pct == null ? '#a1a1aa' : (pct >= 0 ? '#22c55e' : '#ef4444');
    const pctStr   = pct == null ? '--' : (pct >= 0 ? '+' : '') + pct.toFixed(2) + '%';
    const priceStr = ticker.price == null ? '--' : '$' + ticker.price.toFixed(2);
    const rangeStr = (ticker.day_low != null && ticker.day_high != null)
        ? `$${ticker.day_low.toFixed(2)} – $${ticker.day_high.toFixed(2)}` : '--';
    tip.innerHTML = `
        <div class="text-[10px] text-zinc-500 mb-1">${_radarEsc(ticker.sector)} · ${_radarEsc(ticker.industry)}</div>
        <div class="flex items-baseline gap-2 mb-2">
            <span class="text-base font-black text-white">${_radarEsc(ticker.ticker)}</span>
            <span class="text-[10px] text-zinc-400 truncate">${_radarEsc(ticker.name || '')}</span>
        </div>
        <div class="space-y-1 text-[11px] text-zinc-300">
            <div class="flex justify-between"><span class="text-zinc-500">現價</span><span class="font-mono font-bold text-white">${priceStr}</span></div>
            <div class="flex justify-between"><span class="text-zinc-500">漲跌</span><span class="font-mono font-bold" style="color: ${pctColor}">${pctStr}</span></div>
            <div class="flex justify-between"><span class="text-zinc-500">市值</span><span class="font-mono">${_radarFormatMcap(ticker.market_cap)}</span></div>
            <div class="flex justify-between"><span class="text-zinc-500">日內區間</span><span class="font-mono">${rangeStr}</span></div>
            <div class="flex justify-between"><span class="text-zinc-500">成交量</span><span class="font-mono">${_radarFormatVol(ticker.volume)}</span></div>
        </div>
        <div class="mt-2 pt-2 border-t border-zinc-700/40 text-[10px] text-zinc-400 italic">
            點擊看 5min K 線 + 成交量
        </div>`;
    tip.classList.remove('hidden');
    _radarPositionTooltip(event);
}

function _radarPositionTooltip(event) {
    const tip = document.getElementById('radar-heatmap-tooltip');
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

function _radarHideTooltip() {
    const tip = document.getElementById('radar-heatmap-tooltip');
    if (tip) tip.classList.add('hidden');
}

function _radarEsc(s) {
    return String(s == null ? '' : s).replace(/[&<>"']/g, c => ({ '&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;' }[c]));
}

/* ── K-line drill ─────────────────────────────────────────────────── */
function selectRadarKline(tickerData) {
    const isNewTicker = (_radarKlineTicker !== tickerData.ticker);
    _radarKlineTicker = tickerData.ticker;
    const panel = document.getElementById('radar-kline-panel');
    if (panel) panel.classList.remove('hidden');
    document.getElementById('radar-kline-ticker').textContent = tickerData.ticker;
    document.getElementById('radar-kline-name').textContent   = tickerData.name || '';
    if (tickerData.price != null) {
        document.getElementById('radar-kline-price').textContent = '$' + tickerData.price.toFixed(2);
    } else {
        document.getElementById('radar-kline-price').textContent = '—';
    }
    const pct = tickerData.change_pct;
    const chgEl = document.getElementById('radar-kline-change');
    if (pct != null) {
        chgEl.textContent = (pct >= 0 ? '+' : '') + pct.toFixed(2) + '%';
        chgEl.style.color = pct >= 0 ? '#22c55e' : '#ef4444';
    } else {
        chgEl.textContent = '—';
        chgEl.style.color = '';
    }
    document.getElementById('radar-kline-status').textContent = '載入中…';
    document.getElementById('radar-kline-updated').textContent = '';
    if (window.lucide) lucide.createIcons();

    // V2.12.0 — when switching to a different ticker, immediately clear the
    // previous chart so user doesn't see stale data during the 1-3s fetch.
    if (isNewTicker) {
        if (_radarKlineChart)  { _radarKlineChart.destroy();  _radarKlineChart  = null; }
        if (_radarVolumeChart) { _radarVolumeChart.destroy(); _radarVolumeChart = null; }
        const overlay = document.getElementById('radar-kline-loading');
        const overlayTicker = document.getElementById('radar-kline-loading-ticker');
        if (overlayTicker) overlayTicker.textContent = tickerData.ticker;
        if (overlay) overlay.classList.remove('hidden');
    }

    if (_radarKlineTimer) clearInterval(_radarKlineTimer);
    loadRadarKline();
    _radarKlineTimer = setInterval(() => {
        if (document.visibilityState === 'visible' && _radarKlineTicker) loadRadarKline();
    }, RADAR_KLINE_POLL_MS);
}

async function loadRadarKline() {
    if (!_radarKlineTicker) return;
    try {
        const r = await fetch(`/api/heatmap/intraday/${_radarKlineTicker}`);
        if (!r.ok) throw new Error('HTTP ' + r.status);
        const data = await r.json();
        renderRadarKline(data);
    } catch (e) {
        console.error('Radar K-line load error:', e.message);
    }
}

function renderRadarKline(data) {
    const bars = data.bars || [];
    // Hide loading overlay (data arrived; even empty bars means fetch completed)
    const overlay = document.getElementById('radar-kline-loading');
    if (overlay) overlay.classList.add('hidden');
    if (!bars.length) {
        document.getElementById('radar-kline-status').textContent = '無資料';
        return;
    }
    const labels = bars.map(b => (b.time || '').slice(11, 16));   // HH:MM
    const closes = bars.map(b => b.c);
    const vols   = bars.map(b => b.v);
    const colors = bars.map((b, i) => {
        const prev = i === 0 ? b.o : bars[i-1].c;
        return b.c >= prev ? 'rgba(34,197,94,0.7)' : 'rgba(239,68,68,0.7)';
    });

    document.getElementById('radar-kline-status').textContent =
        data.market_open ? '盤中 · 15s 更新' : '收盤 · 5min 更新';
    if (data.as_of) {
        const dt = new Date(data.as_of);
        document.getElementById('radar-kline-updated').textContent =
            'updated ' + dt.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
    }

    // Price line chart
    const priceCanvas = document.getElementById('radar-kline-canvas');
    if (_radarKlineChart) _radarKlineChart.destroy();
    _radarKlineChart = new Chart(priceCanvas, {
        type: 'line',
        data: {
            labels,
            datasets: [{
                label: data.symbol,
                data: closes,
                borderColor: '#6366f1',
                backgroundColor: 'rgba(99,102,241,0.08)',
                fill: true,
                pointRadius: 0,
                borderWidth: 1.5,
                tension: 0.15,
            }],
        },
        options: {
            responsive: true, maintainAspectRatio: false, animation: false,
            plugins: { legend: { display: false }, tooltip: { mode: 'index', intersect: false } },
            scales: {
                x: { ticks: { maxTicksLimit: 8, color: '#71717a', font: { size: 9 } }, grid: { color: 'rgba(82,82,91,0.15)' } },
                y: { ticks: { color: '#71717a', font: { size: 9 } }, grid: { color: 'rgba(82,82,91,0.15)' } },
            },
        },
    });

    // Volume bar chart
    const volCanvas = document.getElementById('radar-volume-canvas');
    if (_radarVolumeChart) _radarVolumeChart.destroy();
    _radarVolumeChart = new Chart(volCanvas, {
        type: 'bar',
        data: { labels, datasets: [{ label: 'Volume', data: vols, backgroundColor: colors, borderWidth: 0 }] },
        options: {
            responsive: true, maintainAspectRatio: false, animation: false,
            plugins: { legend: { display: false }, tooltip: { mode: 'index', intersect: false,
                callbacks: { label: (ctx) => 'Vol: ' + _radarFormatVol(ctx.raw) } } },
            scales: {
                x: { display: false },
                y: { ticks: { color: '#71717a', font: { size: 8 }, callback: (v) => _radarFormatVol(v) },
                     grid: { color: 'rgba(82,82,91,0.15)' } },
            },
        },
    });
}

function closeRadarKline() {
    _radarKlineTicker = null;
    if (_radarKlineTimer) { clearInterval(_radarKlineTimer); _radarKlineTimer = null; }
    if (_radarKlineChart) { _radarKlineChart.destroy(); _radarKlineChart = null; }
    if (_radarVolumeChart) { _radarVolumeChart.destroy(); _radarVolumeChart = null; }
    const panel = document.getElementById('radar-kline-panel');
    if (panel) panel.classList.add('hidden');
}

/* ── Polling ──────────────────────────────────────────────────────── */
function startThemeHeatmapPolling() {
    if (_themeHeatmapTimer) clearInterval(_themeHeatmapTimer);
    _themeHeatmapTimer = setInterval(() => {
        if (document.visibilityState === 'visible') loadThemeHeatmap();
    }, THEME_HEATMAP_POLL_MS);
}

document.addEventListener('visibilitychange', () => {
    if (document.visibilityState === 'visible') {
        loadThemeHeatmap();
        if (_radarKlineTicker) loadRadarKline();
    }
});

window.addEventListener('resize', () => {
    if (_lastThemeHeatmap) renderAllThemeMiniHeatmaps(_lastThemeHeatmap.themes || []);
});

document.addEventListener('DOMContentLoaded', () => {
    document.getElementById('radar-kline-close')?.addEventListener('click', closeRadarKline);
});
