/* ════════════════════════════════════════════════════════════════════════
 * page-index-extra.js  (V4.55.0)
 * ────────────────────────────────────────────────────────────────────────
 * Master-dashboard "全新資訊架構" widgets — surfaces the newest data feeds that
 * previously had NO home on index.html. Loaded AFTER script.js; invoked once
 * per refresh via window.IndexExtras.render(data) from updateDashboard().
 *
 * Feeds wired here:
 *   data.market_mood        (embedded in data.json)  → Market Mood composite
 *   trending_tickers.json   (fetched)                → Social Buzz
 *   intraday_mood.json +
 *   intraday_spikes.json    (fetched)                → Intraday Tape
 *   retail_sector_pulse.json(fetched)                → Retail Sector Pulse
 *   playbook.json           (fetched)                → This Week's Playbook
 *
 * Discipline: pure presentation/read-only. Never mutates feeds or decisions.
 * ════════════════════════════════════════════════════════════════════════ */
(function () {
  'use strict';

  const isZh = () => (window.UI?.currentLang || 'zh') === 'zh';
  const esc = (s) => String(s == null ? '' : s)
    .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
  const num = (v, d = 1) => (v == null || Number.isNaN(Number(v))) ? '—' : Number(v).toFixed(d);
  const setText = (id, t) => { const e = document.getElementById(id); if (e) e.textContent = t; };
  const show = (id) => { const e = document.getElementById(id); if (e) e.classList.remove('hidden'); };

  // Diverging color for a -100..100 (or signed) sentiment score
  const moodColor = (s) => s == null ? '#71717a'
    : s <= -50 ? '#ef4444' : s <= -20 ? '#f59e0b' : s < 20 ? '#a1a1aa'
    : s < 50 ? '#34d399' : '#22c55e';

  const fetchJSON = (f) => fetch(f, { cache: 'no-store' })
    .then(r => r.ok ? r.json() : null).catch(() => null);

  const ageHr = (iso) => {
    if (!iso) return null;
    const t = Date.parse(iso); if (Number.isNaN(t)) return null;
    return (Date.now() - t) / 3.6e6;
  };
  const ageLabel = (iso) => {
    const h = ageHr(iso); if (h == null) return '';
    if (h < 1) return `${Math.round(h * 60)}m`;
    if (h < 48) return `${Math.round(h)}h`;
    return `${Math.round(h / 24)}d`;
  };

  /* ═══ 1. MARKET MOOD — market_mood.json (embedded as data.market_mood) ═══ */
  function renderMarketMood(data) {
    const el = document.getElementById('mood-composite-card');
    if (!el) return;
    const mm = data.market_mood;
    if (!mm || !mm.mood) { el.innerHTML = emptyCard(isZh() ? '市場氛圍資料缺' : 'No mood data'); return; }
    const zh = isZh();
    const score = mm.mood.score;
    const col = moodColor(score);
    const label = zh ? (mm.mood.label_zh || mm.mood.label) : mm.mood.label;
    const pct = Math.max(0, Math.min(100, (Number(score) + 100) / 2)); // -100..100 → 0..100

    const sub = [
      { k: 'VIX', v: num(mm.vix?.current, 1), tag: mm.vix?.regime,
        c: (mm.vix?.current >= 30 ? '#f97316' : mm.vix?.current >= 20 ? '#eab308' : '#22c55e') },
      { k: 'SKEW', v: num(mm.skew?.current, 0), tag: mm.skew?.label,
        c: (mm.skew?.label === 'high' ? '#f59e0b' : '#a1a1aa') },
      { k: 'F&G', v: num(mm.fear_greed?.index, 0), tag: mm.fear_greed?.label,
        c: moodColor((Number(mm.fear_greed?.index) - 50) * 2) },
      { k: 'P/C', v: (mm.options?.tilt || '—'), tag: (zh ? '期權傾向' : 'opt tilt'),
        c: (mm.options?.tilt_signed < 0 ? '#ef4444' : mm.options?.tilt_signed > 0 ? '#22c55e' : '#a1a1aa') },
    ];

    el.innerHTML = `
      <a href="mood.html" class="block no-underline">
        <div class="ix-card-head">
          <i data-lucide="gauge" class="w-3.5 h-3.5" style="color:${col}"></i>
          <span class="ix-card-title">${zh ? '市場氛圍' : 'Market Mood'}</span>
          <span class="ix-fresh ml-auto">${ageLabel(mm.generated_at)}</span>
        </div>
        <div class="flex items-baseline gap-2 mb-1">
          <span class="text-2xl font-black tabular-nums" style="color:${col}">${score > 0 ? '+' : ''}${esc(score)}</span>
          <span class="text-[11px] font-bold" style="color:${col}">${esc(label)}</span>
        </div>
        <div class="ix-bar mb-3"><div class="ix-bar-fill" style="width:${pct}%;background:${col}"></div></div>
        <div class="grid grid-cols-4 gap-1.5">
          ${sub.map(s => `
            <div class="ix-sub">
              <div class="ix-sub-k">${esc(s.k)}</div>
              <div class="ix-sub-v" style="color:${s.c}">${esc(s.v)}</div>
              <div class="ix-sub-t">${esc(s.tag || '')}</div>
            </div>`).join('')}
        </div>
      </a>`;
  }

  /* ═══ 2. SOCIAL BUZZ — trending_tickers.json ═══ */
  function renderSocialBuzz(tt) {
    const el = document.getElementById('social-buzz-card');
    if (!el) return;
    const zh = isZh();
    if (!tt) { el.innerHTML = emptyCard(zh ? '社群資料缺' : 'No social data'); return; }

    const tickers = (tt.tickers || []).slice(0, 6);
    const buzz = (tt.market_wide_buzz || []).slice(0, 3);
    const srcN = tt.post_count || 0;

    const tickerRows = tickers.length ? tickers.map(t => {
      const pol = Number(t.polarity_score);
      const c = moodColor(pol * 20); // polarity roughly -5..5
      const lean = pol > 0.5 ? (zh ? '偏多' : 'bull') : pol < -0.5 ? (zh ? '偏空' : 'bear') : (zh ? '中性' : 'flat');
      return `<div class="ix-buzz-row">
        <span class="ix-buzz-tk">${esc(t.ticker)}</span>
        <span class="ix-buzz-mc">${esc(t.mention_count)}×</span>
        <span class="ix-buzz-lean" style="color:${c}">${lean}</span>
        <span class="ix-buzz-sec">${esc(t.sector || '')}</span>
      </div>`;
    }).join('') : `<div class="ix-empty-row">${zh ? '24h 內無達標個股 buzz' : 'No gated ticker buzz (24h)'}</div>`;

    const buzzChips = buzz.length ? `<div class="ix-chip-row">${buzz.map(b =>
      `<span class="ix-chip" title="${esc(b.post_count)} posts">${esc(b.topic)}</span>`).join('')}</div>` : '';

    el.innerHTML = `
      <a href="mood.html" class="block no-underline">
        <div class="ix-card-head">
          <i data-lucide="message-circle" class="w-3.5 h-3.5 text-sky-400"></i>
          <span class="ix-card-title">${zh ? '社群熱度' : 'Social Buzz'}</span>
          <span class="ix-fresh ml-auto">${srcN} posts · ${ageLabel(tt.as_of)}</span>
        </div>
        <div class="space-y-1">${tickerRows}</div>
        ${buzzChips}
      </a>`;
  }

  /* ═══ 3. INTRADAY TAPE — intraday_mood.json + intraday_spikes.json ═══ */
  function renderIntradayTape(mood, spikes) {
    const el = document.getElementById('intraday-tape-card');
    if (!el) return;
    const zh = isZh();
    const agg = mood?.aggregate || {};
    const sc = agg.score;
    const col = moodColor(sc);
    const open = spikes?.market_open;

    const movers = []
      .concat((spikes?.spikes || []).map(x => ({ ...x, kind: 'spike' })))
      .concat((spikes?.reversals || []).map(x => ({ ...x, kind: 'rev' })))
      .slice(0, 6);

    const moverRows = movers.length ? movers.map(m => {
      const up = (m.direction || '').toLowerCase().includes('up') || m.direction === 'bull';
      const c = up ? '#22c55e' : '#ef4444';
      const kindTag = m.kind === 'spike' ? (zh ? '異動' : 'spike') : (zh ? '反轉' : 'rev');
      // spikes carry % magnitude (mag/m1), reversals carry last price.
      const mag = m.mag != null ? m.mag : m.m1;
      const val = m.last != null ? esc(num(m.last, 2))
                : mag != null ? `${mag > 0 ? '+' : ''}${num(mag, 1)}%` : '';
      return `<div class="ix-tape-row">
        <span class="ix-tape-tk">${esc(m.symbol)}</span>
        <span class="ix-tape-dir" style="color:${c}">${esc(m.dir_zh || m.direction || '')}</span>
        <span class="ix-tape-kind">${kindTag}</span>
        <span class="ix-tape-last">${val}</span>
      </div>`;
    }).join('') : `<div class="ix-empty-row">${open ? (zh ? '盤中暫無顯著異動' : 'No notable moves') : (zh ? '美股已收盤' : 'Market closed')}</div>`;

    el.innerHTML = `
      <a href="intraday-eval.html#mood" class="block no-underline">
        <div class="ix-card-head">
          <i data-lucide="activity" class="w-3.5 h-3.5 text-emerald-400"></i>
          <span class="ix-card-title">${zh ? '盤中異動帶' : 'Intraday Tape'}</span>
          <span class="ix-dot ${open ? 'ix-dot-live' : ''}"></span>
          <span class="ix-fresh ml-auto" style="color:${col}">${sc == null ? '' : (sc > 0 ? '+' : '') + sc} ${esc(agg.risk_label || '')}</span>
        </div>
        ${agg.headline_zh ? `<div class="ix-tape-headline" style="color:var(--text-muted)">${esc(agg.headline_zh)}</div>` : ''}
        <div class="space-y-1 mt-1">${moverRows}</div>
      </a>`;
  }

  /* ═══ 4. RETAIL SECTOR PULSE — retail_sector_pulse.json ═══ */
  function renderRetailPulse(rsp) {
    const el = document.getElementById('retail-pulse-card');
    if (!el) return;
    const zh = isZh();
    if (!rsp || !rsp.sectors) { el.innerHTML = emptyCard(zh ? '零售脈動資料缺' : 'No retail pulse'); return; }

    // Rank by forward-looking 5d outlook (retail_engagement is mostly null in quiet
    // tape); the live colour signal is news_sentiment_score (~ -2..2 scale).
    const rank = (s) => s.predicted_5d_median_pct == null ? -1e9 : s.predicted_5d_median_pct;
    const sectors = [...rsp.sectors].sort((a, b) => rank(b) - rank(a)).slice(0, 7);

    const rows = sectors.map(s => {
      const sent = s.news_sentiment_score;
      const c = sent == null ? '#a1a1aa' : moodColor(Number(sent) * 50);   // -2..2 → -100..100
      const pred = s.predicted_5d_median_pct;
      const predC = pred == null ? '#a1a1aa' : pred > 0 ? '#22c55e' : pred < 0 ? '#ef4444' : '#a1a1aa';
      const w = sent == null ? 4 : Math.max(8, Math.min(100, Math.abs(Number(sent)) * 45 + 8));
      const lab = s.news_label || (sent == null ? '—' : sent > 0.2 ? 'pos' : sent < -0.2 ? 'neg' : 'flat');
      return `<div class="ix-pulse-row">
        <span class="ix-pulse-sec">${esc(sectorShort(s.sector))}</span>
        <div class="ix-pulse-bar"><div class="ix-pulse-fill" style="width:${w}%;background:${c}"></div></div>
        <span class="ix-pulse-lab" style="color:${c}">${esc(lab)}</span>
        <span class="ix-pulse-pred" style="color:${predC}" title="${zh ? '預測 5 日中位' : 'pred 5d median'}">${pred == null ? '·' : (pred > 0 ? '+' : '') + num(pred, 1) + '%'}</span>
      </div>`;
    }).join('');

    el.innerHTML = `
      <div class="ix-card-head">
        <i data-lucide="users" class="w-3.5 h-3.5 text-amber-400"></i>
        <span class="ix-card-title">${zh ? '零售產業脈動' : 'Retail Sector Pulse'}</span>
        <span class="ix-fresh ml-auto">${esc(rsp.horizon || '5d')} · ${ageLabel(rsp.as_of)}</span>
      </div>
      <div class="space-y-1">${rows}</div>`;
  }

  /* ═══ 5. THIS WEEK'S PLAYBOOK — playbook.json ═══ */
  function renderPlaybook(pb) {
    const el = document.getElementById('playbook-card');
    if (!el) return;
    const zh = isZh();
    if (!pb || !pb.baskets) { el.innerHTML = emptyCard(zh ? '投資方案資料缺' : 'No playbook'); return; }

    const order = ['conservative', 'hybrid', 'aggressive'];
    const baskets = order.filter(k => pb.baskets[k]).map(k => {
      const b = pb.baskets[k];
      const picks = (b.picks || []).slice(0, 4).map(p => esc(p.ticker)).join(' · ');
      const tone = k === 'conservative' ? '#22c55e' : k === 'aggressive' ? '#f97316' : '#a78bfa';
      return `<div class="ix-pb-basket" style="border-left-color:${tone}">
        <div class="ix-pb-head">
          <span class="ix-pb-label" style="color:${tone}">${esc(zh ? b.label_zh : (b.label_en || k))}</span>
          <span class="ix-pb-n">${(b.picks || []).length} 檔</span>
        </div>
        <div class="ix-pb-picks">${picks || '—'}</div>
      </div>`;
    }).join('');

    const verdict = pb.codex_review?.verdict;
    el.innerHTML = `
      <a href="playbook.html" class="block no-underline">
        <div class="ix-card-head">
          <i data-lucide="layout-grid" class="w-3.5 h-3.5 text-violet-400"></i>
          <span class="ix-card-title">${zh ? '本週投資方案' : "This Week's Playbook"}</span>
          <span class="ix-fresh ml-auto">${esc(pb.week_label || pb.as_of || '')}</span>
        </div>
        <div class="ix-pb-grid">${baskets}</div>
        ${verdict ? `<div class="ix-pb-verdict"><span class="ix-pb-verdict-tag">Codex</span>${esc(verdict)}</div>` : ''}
      </a>`;
  }

  /* ═══ 6. EXPLORE TEASER — supply-chain + nexus graph nav ═══ */
  function renderExplore() {
    const el = document.getElementById('explore-teaser');
    if (!el) return;
    const zh = isZh();
    el.innerHTML = `
      <a href="graph.html" class="ix-explore-card no-underline">
        <i data-lucide="share-2" class="w-4 h-4 text-indigo-400"></i>
        <div><div class="ix-explore-t">${zh ? '知識圖譜' : 'Knowledge Graph'}</div>
        <div class="ix-explore-d">${zh ? 'ticker ↔ 敘事 ↔ 催化關聯' : 'ticker ↔ narrative ↔ catalyst'}</div></div>
        <i data-lucide="chevron-right" class="w-3.5 h-3.5 ml-auto text-zinc-600"></i>
      </a>
      <a href="supply-chain.html" class="ix-explore-card no-underline">
        <i data-lucide="git-fork" class="w-4 h-4 text-teal-400"></i>
        <div><div class="ix-explore-t">${zh ? '供應鏈探索' : 'Supply Chain'}</div>
        <div class="ix-explore-d">${zh ? '事件傳導與上下游關係' : 'event propagation & links'}</div></div>
        <i data-lucide="chevron-right" class="w-3.5 h-3.5 ml-auto text-zinc-600"></i>
      </a>`;
  }

  /* ─── helpers ─── */
  function emptyCard(msg) { return `<div class="ix-empty">${esc(msg)}</div>`; }
  function sectorShort(s) {
    const map = { Consumer_Discretionary: '非必需消費', Consumer_Staples: '必需消費',
      Communication_Services: '通訊服務', Communication: '通訊服務', Real_Estate: '房地產',
      Information_Technology: '科技', Technology: '科技', Health_Care: '醫療', Healthcare: '醫療',
      Financials: '金融', Industrials: '工業', Materials: '原物料', Energy: '能源',
      Utilities: '公用事業' };
    return isZh() ? (map[s] || String(s).replace(/_/g, ' ')) : String(s).replace(/_/g, ' ');
  }

  /* ─── feed cache (fetched once per session-ish; refreshed each render) ─── */
  let _feeds = null;
  async function loadFeeds() {
    const [tt, mood, spikes, rsp, pb] = await Promise.all([
      fetchJSON('trending_tickers.json'),
      fetchJSON('intraday_mood.json'),
      fetchJSON('intraday_spikes.json'),
      fetchJSON('retail_sector_pulse.json'),
      fetchJSON('playbook.json'),
    ]);
    _feeds = { tt, mood, spikes, rsp, pb };
    return _feeds;
  }

  /* ─── public entry ─── */
  async function render(data) {
    try {
      // Mood reads embedded data.market_mood — no fetch needed, render immediately.
      renderMarketMood(data || {});
      renderExplore();
      // Independent feeds.
      const f = await loadFeeds();
      renderSocialBuzz(f.tt);
      renderIntradayTape(f.mood, f.spikes);
      renderRetailPulse(f.rsp);
      renderPlaybook(f.pb);
    } catch (e) {
      console.error('[IndexExtras] render failed', e);
    } finally {
      if (window.UI?.icons) window.UI.icons();
    }
  }

  window.IndexExtras = { render };
})();
