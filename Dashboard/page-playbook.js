/**
 * page-playbook.js — Weekly Tech Playbook
 *
 * Renders Dashboard/playbook.json (produced by
 * skills/weekly-tech-playbook/scripts/render.py).
 *
 * Three $100k baskets (conservative / aggressive / hybrid), conviction-tiered
 * sizing, with reasons + data + kill triggers + a next-week review scaffold.
 * Exploration layer — does NOT enter investment_protocol decisions.
 */
const $ = (id) => document.getElementById(id);
const esc = (s) => UI.escapeHtml ? UI.escapeHtml(String(s ?? '')) : String(s ?? '');
const usd = (x) => '$' + Math.round(Number(x) || 0).toLocaleString('en-US');

const BASKET_META = {
  conservative: { icon: '🛡️', accent: 'emerald' },
  aggressive:   { icon: '🔥', accent: 'rose' },
  hybrid:       { icon: '⚖️', accent: 'sky' },
};
const TIER_STYLE = {
  core:     { label: '核心', cls: 'text-emerald-400 border-emerald-500/40 bg-emerald-500/10' },
  standard: { label: '標準', cls: 'text-sky-400 border-sky-500/40 bg-sky-500/10' },
  light:    { label: '輕倉', cls: 'text-amber-400 border-amber-500/40 bg-amber-500/10' },
};

let PB = null;
let activeBasket = 'all';

async function load() {
  try {
    const r = await fetch('playbook.json?v=' + Date.now());
    if (!r.ok) throw new Error('http ' + r.status);
    PB = await r.json();
  } catch (e) {
    $('pb-no-data')?.classList.remove('hidden');
    return;
  }
  render();
}

function momChip(v) {
  if (v === null || v === undefined) return '';
  const up = Number(v) >= 0;
  const col = up ? 'text-emerald-400' : 'text-rose-400';
  return `<span class="font-mono ${col}">${up ? '+' : ''}${v}%</span>`;
}

function pickRow(p) {
  const ts = TIER_STYLE[p.tier] || { label: p.tier || '', cls: 'text-zinc-400 border-zinc-600 bg-zinc-700/20' };
  const sleeve = p.sleeve
    ? `<span class="text-[9px] px-1 rounded bg-zinc-700/40 text-zinc-400 ml-1">${esc(p.sleeve)}</span>` : '';
  const committee = p.committee
    ? `<span class="text-[10px] text-violet-400">委員會: ${esc(p.committee)}</span>` : '';
  return `
    <div class="border-t border-zinc-200/60 dark:border-zinc-800 py-2.5">
      <div class="flex items-center justify-between gap-2">
        <div class="flex items-center gap-2 min-w-0">
          <span class="text-[10px] px-1.5 py-0.5 rounded border ${ts.cls}">${ts.label}</span>
          <span class="font-bold text-sm">${esc(p.ticker)}</span>${sleeve}
          <span class="text-[10px] text-zinc-500 truncate">${esc(p.theme)}</span>
        </div>
        <div class="text-right shrink-0">
          <div class="font-mono text-sm font-bold">${usd(p.weight_usd)} <span class="text-[10px] text-zinc-500">(${p.weight_pct}%)</span></div>
          <div class="text-[10px] text-zinc-500 font-mono">${p.shares} 股 · ${usd(p.actual_cost)}</div>
        </div>
      </div>
      <div class="mt-1 text-[11px] text-zinc-600 dark:text-zinc-400 leading-snug">
        ${esc(p.reason)}<span class="text-zinc-500">；${esc(p.data)}</span>
      </div>
      <div class="mt-1 flex items-center flex-wrap gap-x-3 gap-y-0.5 text-[10px]">
        <span class="text-zinc-500">5d ${momChip(p.mom_5d)}</span>
        <span class="text-zinc-500">1mo ${momChip(p.mom_1mo)}</span>
        ${committee}
        <span class="text-rose-400/80">⛔ ${esc(p.kill)}</span>
      </div>
    </div>`;
}

function basketCard(key, b) {
  const meta = BASKET_META[key] || { icon: '', accent: 'zinc' };
  const s = b.summary || {};
  const tb = s.tier_breakdown || {};
  const themes = Object.entries(s.theme_allocation || {})
    .slice(0, 6)
    .map(([t, w]) => `<span class="text-[10px] px-1.5 py-0.5 rounded bg-zinc-700/30 text-zinc-400">${esc(t)} ${usd(w)}</span>`)
    .join(' ');
  return `
    <section class="glass-card p-4 flex flex-col" data-basket-card="${key}">
      <div class="flex items-center justify-between">
        <h3 class="font-bold text-base flex items-center gap-2">
          <span>${meta.icon}</span>${esc(b.label_zh)}籃子
          <span class="text-[10px] text-zinc-500 uppercase tracking-wide">${esc(b.label_en)}</span>
        </h3>
        <span class="font-mono text-sm font-bold text-${meta.accent}-400">${usd(s.target_capital)}</span>
      </div>
      <p class="mt-1.5 text-[11px] text-zinc-500 leading-snug">${esc(b.thesis)}</p>
      <div class="mt-2 flex items-center flex-wrap gap-x-3 gap-y-1 text-[10px] font-mono text-zinc-500">
        <span>部署 <span class="text-zinc-300">${usd(s.actual_deployed)}</span></span>
        <span>餘現金 <span class="text-zinc-300">${usd(s.leftover_cash)}</span></span>
        <span>核心 ${tb.core || 0} / 標準 ${tb.standard || 0} / 輕 ${tb.light || 0}</span>
      </div>
      <div class="mt-2 flex flex-wrap gap-1">${themes}</div>
      <div class="mt-1">${b.picks.map(pickRow).join('')}</div>
    </section>`;
}

function renderMacro() {
  const m = PB.macro || {};
  const el = $('pb-macro');
  if (!el) return;
  const ev = (m.key_events || []).map(e => `<li>${esc(e)}</li>`).join('');
  el.innerHTML = `
    <div class="flex items-start justify-between gap-4 flex-wrap">
      <div class="space-y-1 text-[12px]">
        <div class="font-bold text-sm flex items-center gap-2"><i data-lucide="compass" class="w-4 h-4 text-emerald-500"></i>市場背景</div>
        <div><span class="text-zinc-500">Regime:</span> ${esc(m.regime)} · ${esc(m.exposure_ceiling)}</div>
        <div><span class="text-zinc-500">Breadth:</span> ${esc(m.breadth)} · <span class="text-zinc-500">Top:</span> ${esc(m.market_top)}</div>
        <div><span class="text-zinc-500">情緒:</span> ${esc(m.sentiment)}</div>
        <div class="text-amber-400/90">⚠️ 實質利率: ${esc(m.real_rate_10y)}</div>
      </div>
      <div class="text-[12px]">
        <div class="font-bold text-zinc-400 mb-1">關鍵事件</div>
        <ul class="list-disc list-inside text-zinc-500 space-y-0.5">${ev}</ul>
      </div>
    </div>
    ${m.playbook_logic ? `<div class="mt-2 pt-2 border-t border-zinc-800 text-[11px] text-zinc-400 leading-snug">${esc(m.playbook_logic)}</div>` : ''}`;
  el.classList.remove('hidden');
}

function renderCodexReview() {
  const el = $('pb-codex-review');
  const review = PB.codex_review;
  if (!el || !review) {
    el?.classList.add('hidden');
    return;
  }

  const comparisons = (review.comparison_notes || []).map(item => `
    <div class="border-t border-zinc-200/60 dark:border-zinc-800 py-3">
      <div class="text-xs font-bold text-amber-400">${esc(item.title)}</div>
      <div class="mt-2 grid grid-cols-1 lg:grid-cols-2 gap-3">
        <div class="rounded-lg border border-zinc-200 dark:border-zinc-800 bg-zinc-500/5 p-3">
          <div class="text-[10px] font-bold uppercase tracking-wider text-zinc-500">原報告</div>
          <p class="mt-1 text-[11px] leading-relaxed text-zinc-600 dark:text-zinc-400">${esc(item.original)}</p>
        </div>
        <div class="rounded-lg border border-amber-500/30 bg-amber-500/5 p-3">
          <div class="text-[10px] font-bold uppercase tracking-wider text-amber-400">Codex Review 附註</div>
          <p class="mt-1 text-[11px] leading-relaxed text-zinc-600 dark:text-zinc-300">${esc(item.note)}</p>
        </div>
      </div>
    </div>`).join('');

  const allocation = (review.recommended_allocation || []).map(item => `
    <tr class="border-t border-zinc-200/60 dark:border-zinc-800">
      <td class="py-1.5 pr-3 font-bold">${esc(item.ticker)}</td>
      <td class="py-1.5 pr-3 font-mono text-amber-400">${Number(item.weight_pct) || 0}%</td>
      <td class="py-1.5 text-zinc-500">${esc(item.role)}</td>
    </tr>`).join('');
  const execution = (review.execution || []).map(item => `<li>${esc(item)}</li>`).join('');
  const sources = (review.sources || []).map(item =>
    `<a class="text-sky-400 hover:underline" href="${esc(item.url)}" target="_blank" rel="noopener noreferrer">${esc(item.label)}</a>`
  ).join(' · ');

  el.innerHTML = `
    <div class="flex items-center justify-between gap-3 flex-wrap">
      <div class="font-bold text-sm flex items-center gap-2">
        <i data-lucide="file-search" class="w-4 h-4 text-amber-500"></i>${esc(review.label || 'Codex Review')}
      </div>
      <span class="text-[10px] font-mono text-zinc-500">複核 ${esc(review.reviewed_on || '')}</span>
    </div>
    <p class="mt-2 text-[12px] leading-relaxed text-zinc-600 dark:text-zinc-300">${esc(review.verdict || '')}</p>
    <div class="mt-2 rounded-lg border border-violet-500/30 bg-violet-500/5 p-3 text-[11px] leading-relaxed">
      <div class="flex items-center gap-2 flex-wrap">
        <span class="font-mono text-violet-400">${esc(review.review_mode || '')}</span>
        <span class="text-zinc-500">委員會依賴度</span>
        <span class="font-bold text-amber-400">${esc(review.committee_dependency || '')}</span>
      </div>
      <p class="mt-1 text-zinc-500">${esc(review.dependency_note || '')}</p>
    </div>
    <div class="mt-2">${comparisons}</div>
    <div class="mt-3 grid grid-cols-1 xl:grid-cols-[minmax(0,1.3fr)_minmax(280px,0.7fr)] gap-5">
      <div>
        <div class="text-xs font-bold mb-2">Codex 替代配置</div>
        <table class="w-full text-[11px]">
          <thead class="text-[10px] text-zinc-500"><tr><th class="text-left pr-3">標的</th><th class="text-left pr-3">配重</th><th class="text-left">定位</th></tr></thead>
          <tbody>${allocation}</tbody>
        </table>
      </div>
      <div>
        <div class="text-xs font-bold mb-2">執行紀律</div>
        <ul class="list-disc pl-4 space-y-1.5 text-[11px] leading-relaxed text-zinc-500">${execution}</ul>
      </div>
    </div>
    ${sources ? `<div class="mt-3 pt-3 border-t border-zinc-200 dark:border-zinc-800 text-[10px] text-zinc-500">資料來源: ${sources}</div>` : ''}`;
  el.classList.remove('hidden');
}

function renderReview() {
  const el = $('pb-review');
  if (!el) return;
  el.innerHTML = `
    <div class="font-bold text-sm flex items-center gap-2"><i data-lucide="clipboard-check" class="w-4 h-4 text-sky-500"></i>下週 LLM 檢討 Scaffold</div>
    <p class="mt-1.5 text-[11px] text-zinc-500 leading-snug">
      進場參考價 = 資料快照日 ${esc(PB.as_of)} 的 price 欄，實際交易前須核對最新成交價。下週同日抓收盤，逐檔計算報酬、各籃與 Codex 替代配置 vs SPY、命中率，
      對照每檔 ⛔ Kill 訊號判斷論點是否被打破，並回答「原三籃 vs Codex Review 哪個贏 + 為什麼」。
      完整報告: <code class="text-[10px] text-zinc-400">reports/${esc(PB.as_of)}_TECH_PLAYBOOK.md</code>
    </p>
    <p class="mt-1 text-[10px] text-zinc-600">${esc(PB.discipline_note || '')}</p>`;
  el.classList.remove('hidden');
}

async function renderLastReview() {
  const el = $('pb-lastreview');
  if (!el) return;
  let rv;
  try {
    const r = await fetch('playbook_review.json?v=' + Date.now());
    if (!r.ok) throw 0;
    rv = await r.json();
  } catch (e) { el.classList.add('hidden'); return; }
  // only show a real review (entry date differs from review date)
  if (!rv || rv.entry_date === rv.asof) { el.classList.add('hidden'); return; }

  const rows = (rv.ranking || []).map((b, i) => {
    const alpha = (b.return_pct - rv.bench_return_pct);
    const col = b.return_pct >= 0 ? 'text-emerald-400' : 'text-rose-400';
    const acol = alpha >= 0 ? 'text-emerald-400' : 'text-rose-400';
    const kills = (b.kills_fired || []).join(', ') || '—';
    return `<tr class="border-t border-zinc-800">
      <td class="py-1 pr-3 text-zinc-500">${i + 1}</td>
      <td class="py-1 pr-3 font-bold">${esc(b.label_zh)}</td>
      <td class="py-1 pr-3 font-mono ${col}">${b.return_pct >= 0 ? '+' : ''}${b.return_pct}%</td>
      <td class="py-1 pr-3 font-mono ${acol}">${alpha >= 0 ? '+' : ''}${alpha.toFixed(1)}%</td>
      <td class="py-1 pr-3 font-mono text-zinc-400">${b.hit_rate}%</td>
      <td class="py-1 text-rose-400/80">${esc(kills)}</td></tr>`;
  }).join('');

  el.innerHTML = `
    <div class="flex items-center justify-between flex-wrap gap-2">
      <div class="font-bold text-sm flex items-center gap-2"><i data-lucide="history" class="w-4 h-4 text-sky-500"></i>
        上週方案檢討 — ${esc(rv.entry_date)} 方案 @ ${esc(rv.asof)} 收盤</div>
      <span class="text-[10px] font-mono text-zinc-500">${esc(rv.bench)} ${rv.bench_return_pct >= 0 ? '+' : ''}${rv.bench_return_pct}%</span>
    </div>
    <table class="mt-2 w-full text-[12px]">
      <thead class="text-[10px] text-zinc-500 uppercase">
        <tr><th class="text-left pr-3">#</th><th class="text-left pr-3">籃子</th>
        <th class="text-left pr-3">報酬</th><th class="text-left pr-3">vs ${esc(rv.bench)}</th>
        <th class="text-left pr-3">命中率</th><th class="text-left">觸發 Kill</th></tr>
      </thead><tbody>${rows}</tbody>
    </table>
    <p class="mt-2 text-[10px] text-zinc-600">完整檢討（含 LLM 質性判讀）: <code class="text-zinc-400">reports/${esc(rv.asof)}_TECH_PLAYBOOK_REVIEW.md</code></p>`;
  el.classList.remove('hidden');
  if (window.lucide?.createIcons) window.lucide.createIcons();
}

function render() {
  if (!PB) return;
  $('pb-no-data')?.classList.add('hidden');
  const dt = PB.as_of || '';
  $('pb-asof').textContent = `${UI.currentLang === 'zh' ? '方案日' : 'as_of'} ${dt} · 每籃 ${usd(PB.capital_per_basket)}`;

  renderMacro();
  renderCodexReview();
  renderLastReview();

  const order = ['conservative', 'aggressive', 'hybrid'];
  const wrap = $('pb-baskets');
  wrap.innerHTML = order
    .filter(k => PB.baskets[k] && (activeBasket === 'all' || activeBasket === k))
    .map(k => basketCard(k, PB.baskets[k]))
    .join('');
  // single-basket view → full width
  wrap.classList.toggle('2xl:grid-cols-3', activeBasket === 'all');
  wrap.classList.toggle('2xl:grid-cols-1', activeBasket !== 'all');

  renderReview();
  if (window.lucide?.createIcons) window.lucide.createIcons();
}

function bindToggle() {
  document.querySelectorAll('#pb-basket-toggle button').forEach(btn => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('#pb-basket-toggle button').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      activeBasket = btn.dataset.basket;
      render();
    });
  });
}

document.addEventListener('DOMContentLoaded', () => {
  UI.boot('playbook', { reload: render });
  bindToggle();
  load();
});
