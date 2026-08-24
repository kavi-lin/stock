/**
 * page-backtest.js — 策略回測 (V4.63.0)
 *
 * skills/quant-backtest/scripts/backtest.py 的前端。策略卡片 dialog 選模板
 * → 動態參數表單 → POST /api/protocol-queue {name:'quant_backtest',
 * params_json} (SCRIPT_PROTOCOLS 路徑, 0 LLM) → 輪詢 /api/run-protocol/status
 * → GET /api/backtest/result 渲染。
 *
 * TEMPLATES 與 engine STRATEGIES registry 同步 (11 模板);bench 欄為
 * rank_strategies.py 12 檔 5y 基準的烘焙值,載入時嘗試以
 * /api/backtest/strategies 最新值覆蓋。
 *
 * 探索層 — 結果不入 investment_protocol 決策。data_caveats 永遠顯示。
 */
const $ = (id) => document.getElementById(id);
const esc = (s) => UI.escapeHtml ? UI.escapeHtml(String(s ?? '')) : String(s ?? '');

const COLORS = {
  strat: '#8b5cf6',      // violet — 策略
  bh: '#71717a',         // zinc — 買進持有基準
  entry: '#10b981',      // emerald — 進場
  exit: '#f43f5e',       // rose — 出場
  grid: 'rgba(161,161,170,0.14)',
  posGood: '#10b981',
  posBad: '#f43f5e',
};

let _charts = {};        // canvasId -> Chart (destroy on re-render)
let _pollTimer = null;
let _activeTicker = null;
let _activeTemplate = null;
let _activeQueueId = null;
let _pollStarted = 0;
let _template = 'ma_cross';   // 目前選中的策略模板 (預設 = 基準排名第 1)

const fmtPct = (v, dp = 1) => (v > 0 ? '+' : '') + Number(v).toFixed(dp) + '%';
const cls = (v) => (v >= 0 ? 'text-emerald-500' : 'text-rose-500');

// ── 策略模板 metadata (與 engine STRATEGIES registry 同步) ───────────
// sketch: 100×40 viewBox 迷你示意圖。bench: 12 檔 × 5y × 10bps 中位數基準。
const CAT = {
  trend:     { label: '趨勢跟蹤', cls: 'bt-cat-trend' },
  reversion: { label: '均值回歸', cls: 'bt-cat-reversion' },
  volume:    { label: '量價確認', cls: 'bt-cat-volume' },
  house:     { label: '自家引擎', cls: 'bt-cat-house' },
};
const VIOLET = '#8b5cf6', ZINC = '#71717a';
const sk = (inner) => `<svg class="sketch" viewBox="0 0 100 40" fill="none" xmlns="http://www.w3.org/2000/svg">${inner}</svg>`;
const pl = (pts, color, extra = '') => `<polyline points="${pts}" stroke="${color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" ${extra}/>`;

const TEMPLATES = {
  ma_cross: {
    name: '均線交叉', en: 'MA Cross', cat: 'trend', icon: 'trending-up',
    desc: '快均線站上慢均線就買、跌破就賣 — 最經典的長線趨勢策略。',
    sketch: sk(pl('5,22 30,21 55,19 80,16 95,14', ZINC) + pl('5,34 25,31 45,25 58,19 75,12 95,6', VIOLET) + `<circle cx="57" cy="19.5" r="3" fill="${VIOLET}"/>`),
    bench: { rank: 1, sharpe: 0.61, cagr: 9.6, maxdd: -30.6 },
    params: [
      { key: 'fast', label: '快線 MA', options: [10, 20, 50], def: 50 },
      { key: 'slow', label: '慢線 MA', options: [100, 150, 200], def: 200 },
    ],
    note: (p) => `▲ 進場:MA${p.fast} 上穿 MA${p.slow} ▼ 出場:下穿`,
    validate: (p) => (p.fast >= p.slow ? '快線必須小於慢線' : null),
  },
  roc_trend: {
    name: '時序動能', en: 'TSMOM', cat: 'trend', icon: 'timer',
    desc: '過去半年有漲就續抱、轉跌就出場 — 對沖基金常用的時間序列動能。',
    sketch: sk(pl('5,20 95,20', ZINC, 'stroke-dasharray="3 4" stroke-width="1.5"') + pl('5,30 20,26 32,28 48,20 62,14 74,16 95,7', VIOLET) + `<path d="M88,7 L95,7 L92,13" stroke="${VIOLET}" stroke-width="2" fill="none"/>`),
    bench: { rank: 2, sharpe: 0.61, cagr: 8.7, maxdd: -35.0 },
    params: [
      { key: 'lookback', label: '回看天數', options: [63, 126, 189, 252], def: 126 },
      { key: 'entry_th_pct', label: '進場門檻 %', options: [0, 2, 5], def: 0 },
    ],
    note: (p) => `▲ 進場:${p.lookback} 日報酬 > ${p.entry_th_pct}% ▼ 出場:${p.lookback} 日報酬轉負`,
  },
  donchian: {
    name: '唐奇安通道', en: 'Donchian / 海龜', cat: 'trend', icon: 'chevrons-up',
    desc: '創 20 天新高就買、跌破 10 天新低就賣 — 傳奇海龜交易法。',
    sketch: sk(pl('5,14 35,14 35,11 62,11', ZINC, 'stroke-width="1.5"') + pl('5,32 35,32 35,30 62,30', ZINC, 'stroke-width="1.5"') + pl('8,26 25,20 45,17 62,11 78,8 95,5', VIOLET) + `<circle cx="62" cy="11" r="3" fill="${VIOLET}"/>`),
    bench: { rank: 3, sharpe: 0.56, cagr: 8.8, maxdd: -26.9 },
    params: [
      { key: 'n_entry', label: '突破天數', options: [10, 20, 40, 55], def: 20 },
      { key: 'n_exit', label: '出場天數', options: [5, 10, 20], def: 10 },
    ],
    note: (p) => `▲ 進場:創 ${p.n_entry} 日新高 ▼ 出場:跌破 ${p.n_exit} 日新低`,
  },
  obv_trend: {
    name: 'OBV 量能趨勢', en: 'OBV Trend', cat: 'volume', icon: 'bar-chart-3',
    desc: '量比價先行:資金流入 (OBV) 與價格同步走強才進場。',
    sketch: sk('<rect x="8" y="30" width="6" height="6" fill="' + ZINC + '" opacity=".5"/><rect x="22" y="27" width="6" height="9" fill="' + ZINC + '" opacity=".55"/><rect x="36" y="28" width="6" height="8" fill="' + ZINC + '" opacity=".5"/><rect x="50" y="23" width="6" height="13" fill="' + ZINC + '" opacity=".7"/><rect x="64" y="19" width="6" height="17" fill="' + ZINC + '" opacity=".8"/><rect x="78" y="15" width="6" height="21" fill="' + ZINC + '"/>' + pl('5,18 25,16 45,14 65,9 95,4', VIOLET)),
    bench: { rank: 4, sharpe: 0.54, cagr: 6.7, maxdd: -31.4 },
    params: [
      { key: 'obv_ma', label: 'OBV 均線', options: [10, 20, 50], def: 20 },
      { key: 'price_ma', label: '價格均線', options: [20, 50, 100], def: 50 },
    ],
    note: (p) => `▲ 進場:OBV > ${p.obv_ma} 日均且價格 > MA${p.price_ma} ▼ 出場:OBV 跌破均線`,
  },
  boll_reversion: {
    name: '布林回歸', en: 'Bollinger Reversion', cat: 'reversion', icon: 'waves',
    desc: '長期上升趨勢中跌太深 (碰布林下軌) 就撿便宜,反彈回均值就走。',
    sketch: sk(pl('5,12 30,11 55,10 80,9 95,9', ZINC, 'stroke-width="1.5" opacity=".6"') + pl('5,20 30,19 55,18 80,17 95,17', ZINC, 'stroke-dasharray="3 4" stroke-width="1.5"') + pl('5,28 30,27 55,26 80,25 95,25', ZINC, 'stroke-width="1.5" opacity=".6"') + pl('5,17 22,21 38,31 52,33 68,26 84,18 95,17', VIOLET) + `<circle cx="52" cy="33" r="3" fill="${VIOLET}"/>`),
    bench: { rank: 5, sharpe: 0.53, cagr: 4.2, maxdd: -11.9 },
    params: [
      { key: 'n', label: '布林天數', options: [10, 20, 30], def: 20 },
      { key: 'k', label: '標準差倍數', options: [1.5, 2, 2.5], def: 2 },
    ],
    note: (p) => `▲ 進場:MA200 之上跌破布林 (${p.n}, ${p.k}σ) 下軌 ▼ 出場:回到中軌`,
  },
  supertrend: {
    name: 'SuperTrend', en: 'ATR 趨勢翻轉', cat: 'trend', icon: 'zap',
    desc: '用波動度 (ATR) 畫出會跟著走的停損線:翻多就抱、翻空就走。',
    sketch: sk(pl('5,33 20,29 35,24 50,27 65,18 80,12 95,8', VIOLET) + pl('5,38 20,35 35,31 50,33 65,26 80,20 95,15', ZINC, 'stroke-dasharray="4 3" stroke-width="1.5"')),
    bench: { rank: 6, sharpe: 0.49, cagr: 8.2, maxdd: -30.4 },
    params: [
      { key: 'n', label: 'ATR 天數', options: [7, 10, 14], def: 10 },
      { key: 'mult', label: 'ATR 倍數', options: [2, 3, 4], def: 3 },
    ],
    note: (p) => `▲ 進場:SuperTrend(${p.n}, ${p.mult}) 翻多 ▼ 出場:翻空`,
  },
  triple_ma: {
    name: '三均線排列', en: 'Triple MA', cat: 'trend', icon: 'layers',
    desc: '短中長三條均線由上而下排好隊 (多頭排列) 才進場的順勢策略。',
    sketch: sk(pl('5,34 30,32 55,29 80,26 95,24', ZINC, 'stroke-width="1.5" opacity=".5"') + pl('5,30 30,27 55,22 80,17 95,15', ZINC, 'stroke-width="1.5"') + pl('5,26 30,22 55,15 80,9 95,6', VIOLET)),
    bench: { rank: 7, sharpe: 0.49, cagr: 5.7, maxdd: -25.1 },
    params: [
      { key: 'fast', label: '快線 MA', options: [10, 20, 30], def: 20 },
      { key: 'mid', label: '中線 MA', options: [50, 100, 150], def: 50 },
    ],
    note: (p) => `▲ 進場:MA${p.fast} > MA${p.mid} > MA200 且價格 > MA${p.fast} ▼ 出場:MA${p.fast} 跌破 MA${p.mid}`,
    validate: (p) => (p.fast >= p.mid ? '快線必須小於中線' : null),
  },
  rsi_reversion: {
    name: 'RSI 超賣反轉', en: 'RSI Reversion', cat: 'reversion', icon: 'heart-pulse',
    desc: 'RSI 跌破 30 = 市場恐慌超賣時買進,回到常態區就賣出。',
    sketch: sk(pl('5,12 95,12', ZINC, 'stroke-dasharray="3 4" stroke-width="1.5"') + pl('5,30 95,30', ZINC, 'stroke-dasharray="3 4" stroke-width="1.5"') + pl('5,16 18,22 30,34 44,36 58,26 72,14 84,10 95,13', VIOLET) + `<circle cx="44" cy="36" r="3" fill="${VIOLET}"/>`),
    bench: { rank: 8, sharpe: 0.45, cagr: 5.5, maxdd: -19.4 },
    params: [
      { key: 'buy_th', label: '超賣買進 <', options: [20, 25, 30, 35], def: 30 },
      { key: 'sell_th', label: '出場 >', options: [50, 55, 60, 65], def: 55 },
    ],
    note: (p) => `▲ 進場:RSI14 < ${p.buy_th} ▼ 出場:RSI14 > ${p.sell_th}`,
  },
  high_52w: {
    name: '52週新高', en: '52-Week High', cat: 'trend', icon: 'mountain',
    desc: '敢買創一年新高的強勢股 — 學術驗證過的 52 週新高動能效應。',
    sketch: sk(pl('5,8 95,8', ZINC, 'stroke-dasharray="3 4" stroke-width="1.5"') + pl('5,32 22,26 36,29 52,20 68,14 82,9 92,8', VIOLET) + `<circle cx="92" cy="8" r="3" fill="${VIOLET}"/>`),
    bench: { rank: 9, sharpe: 0.45, cagr: 6.8, maxdd: -32.4 },
    params: [
      { key: 'near_pct', label: '距新高 % 內', options: [2, 5, 10], def: 5 },
      { key: 'exit_pct', label: '回落 % 出場', options: [10, 15, 20], def: 15 },
    ],
    note: (p) => `▲ 進場:收盤距 52 週高點 ${p.near_pct}% 內 ▼ 出場:自高點回落 ${p.exit_pct}%`,
  },
  keltner: {
    name: '肯特納突破', en: 'Keltner Breakout', cat: 'trend', icon: 'arrow-up-from-line',
    desc: '價格衝出 ATR 通道上緣 = 動能爆發訊號,跌回均線就出場。',
    sketch: sk(pl('5,14 30,13 55,12 80,10 95,9', ZINC, 'stroke-width="1.5" opacity=".6"') + pl('5,24 30,23 55,22 80,20 95,19', ZINC, 'stroke-dasharray="3 4" stroke-width="1.5"') + pl('5,27 25,25 45,20 62,12 78,7 95,4', VIOLET) + `<circle cx="62" cy="12" r="3" fill="${VIOLET}"/>`),
    bench: { rank: 10, sharpe: 0.43, cagr: 4.3, maxdd: -22.6 },
    params: [
      { key: 'n', label: 'EMA 天數', options: [10, 20, 30], def: 20 },
      { key: 'mult', label: 'ATR 倍數', options: [1.5, 2, 2.5], def: 2 },
    ],
    note: (p) => `▲ 進場:收盤突破 EMA${p.n} + ${p.mult}×ATR ▼ 出場:跌破 EMA${p.n}`,
  },
  momentum: {
    name: '動能重放', en: 'Momentum Replay', cat: 'house', icon: 'gauge',
    desc: 'AI 委員會自家動能引擎:量能 + 均線結構 + 趨勢加速綜合計分重放。',
    sketch: sk(pl('5,15 95,15', ZINC, 'stroke-dasharray="3 4" stroke-width="1.5"') + pl('5,28 18,24 32,26 46,18 60,12 74,14 88,8 95,9', VIOLET) + `<rect x="46" y="4" width="49" height="32" fill="${VIOLET}" opacity=".08"/>`),
    bench: { rank: 11, sharpe: 0.42, cagr: 4.0, maxdd: -22.6 },
    params: [
      { key: 'entry_score', label: '進場分數 ≥', options: [55, 60, 65, 70, 75, 80], def: 65 },
      { key: 'exit_score', label: '出場分數 <', options: [30, 35, 40, 45, 50, 55], def: 45 },
    ],
    note: (p) => `▲ 進場:score ≥ ${p.entry_score} 且 Stage 2 ▼ 出場:跌破 MA50 或 score < ${p.exit_score}`,
  },
};
// 卡片顯示順序 = 20 候選策略基準排名前 10 + 自家 momentum 引擎
const TEMPLATE_ORDER = ['ma_cross', 'roc_trend', 'donchian', 'obv_trend',
  'boll_reversion', 'supertrend', 'triple_ma', 'rsi_reversion', 'high_52w',
  'keltner', 'momentum'];
let _benchMeta = '12 檔 (SPY/QQQ + 跨產業 mega-cap) × 5 年 × 單邊 10 bps,中位數';

// ── 表單 ────────────────────────────────────────────────────────────
function templateParams() {
  const p = {};
  (TEMPLATES[_template].params || []).forEach((spec) => {
    const el = $(`bt-p-${spec.key}`);
    p[spec.key] = Number(el ? el.value : spec.def);
  });
  return p;
}

function currentParams() {
  return {
    ticker: ($('bt-ticker').value || '').trim().toUpperCase(),
    template: _template,
    period: $('bt-period').value,
    cost_bps: Math.max(0, Number($('bt-cost').value) || 0),
    params: templateParams(),
  };
}

function renderParamForm() {
  const t = TEMPLATES[_template];
  $('bt-params').innerHTML = (t.params || []).map((spec) => `
    <div>
      <label class="text-[10px] font-bold text-zinc-500 uppercase tracking-widest block mb-1">${esc(spec.label)}</label>
      <select id="bt-p-${esc(spec.key)}" class="bg-transparent border border-zinc-300 dark:border-zinc-700 rounded-lg px-3 py-1.5 text-sm font-mono outline-none focus:border-violet-500">
        ${spec.options.map((o) => `<option${o === spec.def ? ' selected' : ''}>${o}</option>`).join('')}
      </select>
    </div>`).join('');
}

function syncStrategyButton() {
  const t = TEMPLATES[_template];
  $('bt-strategy-label').textContent = t.name;
  $('bt-strategy-rank').textContent = t.cat === 'house' ? '自家' : `基準 #${t.bench.rank}`;
}

// ── 策略卡片 dialog ─────────────────────────────────────────────────
function renderStrategyCards() {
  $('bt-modal-note').textContent =
    `基準績效 = ${_benchMeta}(rank_strategies.py 產出;探索層參考,非未來報酬保證)。`;
  $('bt-modal-grid').innerHTML = TEMPLATE_ORDER.map((key) => {
    const t = TEMPLATES[key];
    const c = CAT[t.cat];
    return `
    <div class="bt-strategy-card${key === _template ? ' selected' : ''}" data-key="${esc(key)}" role="button" tabindex="0">
      <div class="flex items-center justify-between">
        <div class="flex items-center gap-2 min-w-0">
          <i data-lucide="${esc(t.icon)}" class="w-4 h-4 text-violet-500 shrink-0"></i>
          <span class="font-bold text-sm truncate">${esc(t.name)}</span>
        </div>
        <span class="bt-cat-badge ${c.cls} shrink-0">${c.label}</span>
      </div>
      <div class="text-[10px] text-zinc-500 font-mono -mt-1">${esc(t.en)}</div>
      ${t.sketch}
      <p class="text-[11px] text-zinc-500 leading-relaxed flex-1">${esc(t.desc)}</p>
      <div class="flex items-center justify-between text-[10px] font-mono pt-1 border-t border-zinc-200 dark:border-zinc-800">
        <span class="bt-rank-chip">${t.cat === 'house' ? '自家引擎' : '基準 #' + t.bench.rank}</span>
        <span class="text-zinc-500">Sharpe <b class="${cls(t.bench.sharpe)}">${t.bench.sharpe.toFixed(2)}</b></span>
        <span class="text-zinc-500">CAGR <b class="${cls(t.bench.cagr)}">${fmtPct(t.bench.cagr)}</b></span>
      </div>
    </div>`;
  }).join('');
  if (window.lucide?.createIcons) window.lucide.createIcons();
}

function openModal() {
  renderStrategyCards();
  $('bt-modal').classList.remove('hidden');
}

function closeModal() {
  $('bt-modal').classList.add('hidden');
}

function selectTemplate(key) {
  if (!TEMPLATES[key]) return;
  _template = key;
  syncStrategyButton();
  renderParamForm();
  closeModal();
}

// 以 rank_strategies.py 最新 artifact 覆蓋烘焙 bench 值 (失敗則保留烘焙值)
async function overlayBench() {
  try {
    const r = await fetch('/api/backtest/strategies');
    if (!r.ok) return;
    const d = await r.json();
    (d.ranking || []).forEach((row) => {
      const t = TEMPLATES[row.template];
      if (!t) return;
      t.bench = { rank: row.rank, sharpe: row.median_sharpe,
                  cagr: row.median_cagr_pct, maxdd: row.median_max_dd_pct };
    });
    if (d.methodology) _benchMeta = d.methodology;
    syncStrategyButton();
  } catch (_) { /* 烘焙值 fallback */ }
}

// ── 執行 ────────────────────────────────────────────────────────────
async function runBacktest() {
  const p = currentParams();
  if (!/^[A-Z][A-Z0-9.\-]{0,8}$/.test(p.ticker)) {
    UI.showToast('Ticker 格式不正確', 'error');
    return;
  }
  const vErr = TEMPLATES[p.template].validate?.(p.params);
  if (vErr) {
    UI.showToast(vErr, 'error');
    return;
  }
  try {
    const r = await fetch('/api/protocol-queue', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        name: 'quant_backtest',
        ticker: p.ticker, template: p.template, period: p.period,
        cost_bps: p.cost_bps, params_json: JSON.stringify(p.params),
      }),
    });
    const body = await r.json();
    if (r.status === 202 && body.queued) {
      _activeTicker = p.ticker;
      _activeTemplate = p.template;
      _activeQueueId = body.id || null;
      _pollStarted = Date.now();
      setRunning(true, `已排入 (${p.ticker} ${p.template})…`);
      if (_pollTimer) clearInterval(_pollTimer);
      _pollTimer = setInterval(pollStatus, 2000);
    } else if (r.status === 409) {
      UI.showToast(body.reason === 'duplicate_active' ? '相同回測已在執行中' : (body.error || '佇列衝突'), 'warn');
    } else {
      UI.showToast(`加入失敗:${body.error || r.status}`, 'error');
    }
  } catch (e) {
    UI.showToast(`網路錯誤:${e.message}`, 'error');
  }
}

function setRunning(running, statusText) {
  $('bt-run').disabled = running;
  $('bt-run-label').textContent = running ? '執行中…' : '執行回測';
  $('bt-status').textContent = statusText || '';
}

async function pollStatus() {
  // 6 分鐘安全上限 — 佇列被長任務卡住時放手,結果之後可從 recent chips 撈
  if (Date.now() - _pollStarted > 6 * 60 * 1000) {
    stopPolling('等候逾時 — 稍後可從下方歷史結果載入');
    return;
  }
  try {
    const suffix = _activeQueueId
      ? `?queue_id=${encodeURIComponent(_activeQueueId)}`
      : '?name=quant_backtest';
    const r = await fetch('/api/run-protocol/status' + suffix);
    if (!r.ok) return;
    const s = await r.json();
    const mine = s.name === 'quant_backtest' &&
      (s.ticker === _activeTicker || !s.ticker);
    if (s.status === 'running' && mine) {
      $('bt-status').textContent = `執行中… ${s.elapsed_sec || 0}s`;
      return;
    }
    if (!mine && s.status === 'running') return; // 別人的 job,繼續等佇列
    if (mine && (s.status === 'done' || s.status === 'error')) {
      stopPolling('');
      if (s.status === 'error') {
        // rc=2 degraded 也走 error 路徑 — artifact 可能仍已寫出,照樣嘗試載入
        UI.showToast(`回測結束(${esc(s.error || 'error')}),嘗試載入結果`, 'warn');
      }
      await loadResult(_activeTicker, _activeTemplate, true);
      await loadRecent();
    }
  } catch (_) { /* 輪詢失敗靜默重試 */ }
}

function stopPolling(statusText) {
  if (_pollTimer) { clearInterval(_pollTimer); _pollTimer = null; }
  setRunning(false, statusText);
}

// ── 結果載入 ────────────────────────────────────────────────────────
async function loadRecent() {
  try {
    const r = await fetch('/api/backtest/list');
    if (!r.ok) return [];
    const { results } = await r.json();
    $('bt-recent').innerHTML = (results || []).slice(0, 12).map((x) => `
      <button class="bt-chip glass-card px-3 py-1.5 rounded-lg text-[11px] font-mono flex items-center gap-2"
              data-ticker="${esc(x.ticker)}" data-template="${esc(x.template)}">
        <span class="font-bold">${esc(x.ticker)}</span>
        <span class="text-zinc-500">${esc(TEMPLATES[x.template]?.name || x.template_label || x.template)} · ${esc(x.period || '')}</span>
        <span class="${cls(x.metrics?.total_return_pct ?? 0)}">${fmtPct(x.metrics?.total_return_pct ?? 0)}</span>
      </button>`).join('');
    return results || [];
  } catch (_) { return []; }
}

async function loadResult(ticker, template, toast) {
  try {
    const r = await fetch(`/api/backtest/result?ticker=${encodeURIComponent(ticker)}&template=${encodeURIComponent(template)}`);
    if (!r.ok) {
      if (toast) UI.showToast(`找不到 ${ticker}/${template} 的結果`, 'error');
      return;
    }
    const d = await r.json();
    render(d);
    if (toast) UI.showToast(`已載入 ${ticker} ${template} 回測`, 'success');
  } catch (e) {
    if (toast) UI.showToast(`載入失敗:${e.message}`, 'error');
  }
}

// ── 渲染 ────────────────────────────────────────────────────────────
function render(d) {
  // 表單同步到載入的結果 (recent chip 可能是別的模板)
  if (TEMPLATES[d.template]) {
    _template = d.template;
    syncStrategyButton();
    renderParamForm();
    (TEMPLATES[d.template].params || []).forEach((spec) => {
      const el = $(`bt-p-${spec.key}`);
      const v = d.params?.[spec.key];
      if (el && v !== undefined && spec.options.some((o) => Number(o) === Number(v))) el.value = String(v);
    });
  }
  $('bt-result').classList.remove('hidden');
  $('bt-asof').textContent = `${d.window.from} → ${d.window.to} · ${d.window.bars} bars · ${(d.generated_at || '').slice(0, 16)}Z`;

  // Caveats + 驗證 + degraded
  const v = d.validation_vs_live_cache;
  const vOk = v && v.ma_stage_match && v.trend_accel_match && v.stage_match;
  $('bt-caveats').innerHTML =
    (d.degraded ? `<div class="text-rose-400 font-bold mb-1">⚠ 窗口不足 252 bars — 統計信度低</div>` : '') +
    (v ? `<div class="mb-1 ${vOk ? 'text-emerald-500' : 'text-amber-500'}">${vOk ? '✓ 重放口徑驗證:與 live cache 一致' : '△ 重放口徑與 live cache 有差異'}(${esc(v.cache_date || '')})</div>` : '') +
    (d.data_caveats || []).map((c) => `<div>· ${esc(c)}</div>`).join('');

  // Tiles
  const m = d.metrics;
  const tiles = [
    ['策略總報酬', fmtPct(m.total_return_pct), `B&H ${fmtPct(m.bh_total_return_pct)}`, cls(m.total_return_pct)],
    ['CAGR', fmtPct(m.cagr_pct), `B&H ${fmtPct(m.bh_cagr_pct)}`, cls(m.cagr_pct)],
    ['Sharpe', m.sharpe.toFixed(2), `B&H ${m.bh_sharpe.toFixed(2)}`, cls(m.sharpe)],
    ['最大回撤', m.max_dd_pct.toFixed(1) + '%', `B&H ${m.bh_max_dd_pct.toFixed(1)}%`, 'text-rose-500'],
    ['曝險時間', m.exposure_pct.toFixed(0) + '%', '空手時 0 報酬', ''],
    ['交易 / 勝率', `${m.n_trades} / ${m.win_rate_pct ?? '—'}%`, '含未平倉', ''],
  ];
  $('bt-tiles').innerHTML = tiles.map(([k, val, sub, c]) => `
    <div class="glass-card p-4">
      <div class="text-[10px] font-bold text-zinc-500 uppercase tracking-widest mb-1">${k}</div>
      <div class="bt-tile-value text-xl font-bold ${c}">${val}</div>
      <div class="text-[10px] text-zinc-500 mt-0.5">${sub}</div>
    </div>`).join('');

  const noteFn = TEMPLATES[d.template]?.note;
  $('bt-rule-note').textContent =
    (noteFn ? noteFn(d.params || {}) : `模板 ${d.template}`) +
    `;訊號日收盤成交,單邊 ${d.cost_bps_per_side} bps`;

  renderCharts(d);
  renderHeatmap(d);
  renderTables(d);
  if (window.lucide?.createIcons) window.lucide.createIcons();
}

function mkChart(canvasId, cfg) {
  if (_charts[canvasId]) _charts[canvasId].destroy();
  _charts[canvasId] = new Chart($(canvasId), cfg);
}

function baseOpts(labels) {
  return {
    maintainAspectRatio: false,
    animation: false,
    interaction: { mode: 'index', intersect: false },
    plugins: {
      legend: { labels: { boxWidth: 10, boxHeight: 10, color: '#71717a', font: { size: 10 } } },
    },
    scales: {
      x: {
        grid: { display: false },
        ticks: {
          maxRotation: 0, autoSkip: true, maxTicksLimit: 8, color: '#71717a', font: { size: 9 },
          callback(v) { return labels[v] ? labels[v].slice(0, 7) : ''; },
        },
      },
      y: { grid: { color: COLORS.grid }, ticks: { color: '#71717a', font: { size: 9 } } },
    },
  };
}

const line = (data, color, label, extra = {}) => ({
  label, data, borderColor: color, backgroundColor: color,
  borderWidth: 1.8, pointRadius: 0, pointHitRadius: 6, tension: 0, ...extra,
});

function renderCharts(d) {
  const s = d.series;
  const labels = s.dates;

  // 1. 權益曲線 (log)
  const eqOpts = baseOpts(labels);
  eqOpts.scales.y.type = 'logarithmic';
  eqOpts.scales.y.ticks.callback = (v) =>
    [0.25, 0.5, 1, 2, 4, 8, 16, 32].includes(v) ? v + '×' : null;
  eqOpts.plugins.tooltip = { callbacks: { label: (c) => ` ${c.dataset.label}: ${c.parsed.y.toFixed(2)}×` } };
  mkChart('bt-ch-equity', {
    type: 'line',
    data: { labels, datasets: [line(s.eq_strat, COLORS.strat, '策略'), line(s.eq_bh, COLORS.bh, '買進持有')] },
    options: eqOpts,
  });

  // 2. 價格 + 進出場 (null-masked point datasets — category 軸安全)
  const entrySet = new Set(), exitSet = new Set();
  (d.trades || []).forEach((t) => { entrySet.add(t.entry); exitSet.add(t.exit); });
  const entryPts = labels.map((dt, i) => (entrySet.has(dt) ? s.close[i] : null));
  const exitPts = labels.map((dt, i) => (exitSet.has(dt) ? s.close[i] : null));
  const priceOpts = baseOpts(labels);
  priceOpts.interaction = { mode: 'nearest', intersect: false };
  priceOpts.scales.y.ticks.callback = (v) => '$' + v;
  mkChart('bt-ch-price', {
    type: 'line',
    data: {
      labels,
      datasets: [
        line(s.close, COLORS.bh, `${d.ticker} 收盤`, { borderWidth: 1.2 }),
        { label: '進場', data: entryPts, showLine: false, pointStyle: 'triangle',
          pointRadius: 6, pointHoverRadius: 8, backgroundColor: COLORS.entry, borderColor: COLORS.entry },
        { label: '出場', data: exitPts, showLine: false, pointStyle: 'triangle', rotation: 180,
          pointRadius: 6, pointHoverRadius: 8, backgroundColor: COLORS.exit, borderColor: COLORS.exit },
      ],
    },
    options: priceOpts,
  });

  // 3. 回撤
  const ddOpts = baseOpts(labels);
  ddOpts.plugins.tooltip = { callbacks: { label: (c) => ` ${c.dataset.label}: ${c.parsed.y.toFixed(1)}%` } };
  ddOpts.scales.y.ticks.callback = (v) => v + '%';
  mkChart('bt-ch-dd', {
    type: 'line',
    data: {
      labels,
      datasets: [
        line(s.drawdown, COLORS.strat, '策略', { fill: true, backgroundColor: COLORS.strat + '22' }),
        line(s.drawdown_bh, COLORS.bh, '買進持有'),
      ],
    },
    options: ddOpts,
  });

  // 4. 動能分 + 持倉底色 (momentum 模板限定)
  const isMomentum = d.template === 'momentum';
  $('bt-score-panel').classList.toggle('hidden', !isMomentum);
  if (isMomentum) {
    const scOpts = baseOpts(labels);
    scOpts.scales.y.min = 0; scOpts.scales.y.max = 100;
    scOpts.plugins.legend.labels.filter = (i) => i.text !== '持倉';
    scOpts.plugins.tooltip = {
      filter: (c) => c.dataset.label === '綜合分',
      callbacks: { label: (c) => ` 分數: ${c.parsed.y}` },
    };
    mkChart('bt-ch-score', {
      type: 'line',
      data: {
        labels,
        datasets: [
          line(s.score, COLORS.strat, '綜合分'),
          line(s.pos.map((p) => p * 100), COLORS.strat + '12', '持倉',
            { fill: 'origin', borderWidth: 0, stepped: true, backgroundColor: COLORS.strat + '12' }),
          line(labels.map(() => d.params.entry_score), '#71717a', `進場 ${d.params.entry_score}`, { borderWidth: 1, borderDash: [4, 4] }),
          line(labels.map(() => d.params.exit_score), '#71717a', `出場 ${d.params.exit_score}`, { borderWidth: 1, borderDash: [2, 4] }),
        ],
      },
      options: scOpts,
    });
  } else if (_charts['bt-ch-score']) {
    _charts['bt-ch-score'].destroy(); delete _charts['bt-ch-score'];
  }
}

// 參數掃描熱力圖 — Sharpe 發散色階 (負紅正綠,0 為中點)
function renderHeatmap(d) {
  const el = $('bt-heatmap');
  if (!d.sweep) { el.innerHTML = '<div class="text-xs text-zinc-500">此次執行未含參數掃描</div>'; return; }
  const { x_name, y_name, xs, ys, cells } = d.sweep;
  const sharpes = cells.filter((c) => !c.invalid).map((c) => c.sharpe);
  const maxAbs = Math.max(0.01, ...sharpes.map(Math.abs));
  const byKey = {};
  cells.forEach((c) => { byKey[`${c.x}|${c.y}`] = c; });
  const cur = d.params;

  el.style.gridTemplateColumns = `70px repeat(${xs.length}, minmax(58px, 1fr))`;
  let html = `<div class="bt-heat-axis">${esc(y_name)} \\ ${esc(x_name)}</div>` +
    xs.map((x) => `<div class="bt-heat-axis font-bold">${x}</div>`).join('');
  ys.forEach((y) => {
    html += `<div class="bt-heat-axis font-bold">${y}</div>`;
    xs.forEach((x) => {
      const c = byKey[`${x}|${y}`];
      if (!c || c.invalid) {
        html += `<div class="bt-heat-cell text-zinc-600" style="background:rgba(161,161,170,0.06)">—</div>`;
        return;
      }
      const a = Math.min(0.85, Math.abs(c.sharpe) / maxAbs * 0.85 + 0.08);
      const bg = c.sharpe >= 0 ? `rgba(16,185,129,${a})` : `rgba(244,63,94,${a})`;
      const isCur = cur[x_name] === x && cur[y_name] === y;
      html += `<div class="bt-heat-cell${isCur ? ' current' : ''}" style="background:${bg}"
        title="${x_name}=${x} ${y_name}=${y} | Sharpe ${c.sharpe} | CAGR ${fmtPct(c.cagr_pct)} | MaxDD ${c.max_dd_pct}% | ${c.n_trades} 筆">${c.sharpe.toFixed(2)}</div>`;
    });
  });
  el.innerHTML = html;
}

function renderTables(d) {
  const years = Object.keys(d.yearly || {});
  $('bt-yearly').innerHTML =
    '<tr><th>年度</th><th>策略</th><th>買進持有</th><th>差額</th></tr>' +
    years.map((y) => {
      const r = d.yearly[y], diff = r.strat - r.bh;
      return `<tr><td>${y}</td><td class="${cls(r.strat)}">${fmtPct(r.strat)}</td>` +
        `<td class="${cls(r.bh)}">${fmtPct(r.bh)}</td>` +
        `<td class="${cls(diff)}">${fmtPct(diff)}</td></tr>`;
    }).join('');

  $('bt-trades').innerHTML =
    '<tr><th>#</th><th>進場</th><th>出場</th><th>天數</th><th>報酬</th></tr>' +
    (d.trades || []).map((t, i) =>
      `<tr><td>${i + 1}</td><td class="font-mono">${esc(t.entry)}</td>` +
      `<td class="font-mono">${esc(t.exit)}</td><td>${t.days}</td>` +
      `<td class="${cls(t.pct)}">${fmtPct(t.pct, 2)}</td></tr>`).join('');
}

// ── Init ────────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', async () => {
  UI.boot('backtest', {});
  syncStrategyButton();
  renderParamForm();
  $('bt-strategy-btn').addEventListener('click', openModal);
  $('bt-modal-close').addEventListener('click', closeModal);
  $('bt-modal-backdrop').addEventListener('click', closeModal);
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && !$('bt-modal').classList.contains('hidden')) closeModal();
  });
  $('bt-modal-grid').addEventListener('click', (e) => {
    const card = e.target.closest('.bt-strategy-card');
    if (card) selectTemplate(card.dataset.key);
  });
  $('bt-modal-grid').addEventListener('keydown', (e) => {
    const card = e.target.closest('.bt-strategy-card');
    if (card && (e.key === 'Enter' || e.key === ' ')) { e.preventDefault(); selectTemplate(card.dataset.key); }
  });
  $('bt-run').addEventListener('click', runBacktest);
  $('bt-ticker').addEventListener('keydown', (e) => { if (e.key === 'Enter') runBacktest(); });
  $('bt-recent').addEventListener('click', (e) => {
    const chip = e.target.closest('.bt-chip');
    if (chip) loadResult(chip.dataset.ticker, chip.dataset.template, true);
  });

  overlayBench();
  const results = await loadRecent();
  if (results.length) loadResult(results[0].ticker, results[0].template, false);
});
