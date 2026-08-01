/* page-intraday-eval.js — 盤中策略 (Intraday Evaluation hub)
 * Reads the consolidated snapshot from /api/intraday-eval/data (the single hub
 * accessor) + /history for the recurrence timeline. Renders regime, strategy
 * cards with repeated-strategy effects (consecutive-window glow + ×N day badge),
 * sector ranking, group rotation, stock ideas, and the day timeline.
 * Exploration layer — does not feed investment_protocol.
 */
(function () {
  'use strict';
  const esc = (s) => (window.UI ? UI.escapeHTML(String(s ?? '')) : String(s ?? ''));
  const $ = (id) => document.getElementById(id);
  const POLL_MS = 60000;

  const num = (v, d = 2) => (v === null || v === undefined || isNaN(v)) ? '—' : Number(v).toFixed(d);
  const pctClass = (v) => (v === null || v === undefined) ? 'ie-mut' : (v > 0 ? 'ie-pos' : (v < 0 ? 'ie-neg' : 'ie-mut'));
  const signed = (v, d = 2) => (v === null || v === undefined || isNaN(v)) ? '—' : (v > 0 ? '+' : '') + Number(v).toFixed(d);

  let lastStrategies = [];

  async function fetchJson(url) {
    const r = await fetch(url, { cache: 'no-store' });
    if (!r.ok) throw new Error(r.status);
    return r.json();
  }

  async function load() {
    let data = null;
    try { data = await fetchJson('/api/intraday-eval/data'); }
    catch (e) { try { data = await fetchJson('intraday_eval.json'); } catch (e2) {} }
    if (!data || data.error) { renderEmpty(); return; }
    render(data);
    // timeline from history (best-effort)
    try { renderTimeline(await fetchJson('/api/intraday-eval/history'), data.strategies || []); }
    catch (e) { /* keep last */ }
  }

  function renderEmpty() {
    $('ie-narrative').textContent = '尚未產生盤中評估（伺服器啟動後每 10 分鐘於美股時段自動更新）。';
    if (window.lucide) lucide.createIcons();
  }

  function render(d) {
    lastStrategies = d.strategies || [];
    renderStatus(d);
    renderRegime(d.regime || {});
    $('ie-narrative').innerHTML = esc(d.narrative_zh || '—');
    renderStats(d.mood || {}, d.breadth || {});
    renderStrategies(d.strategies || [], d.recurrence || {});
    renderSectors(d.sectors || []);
    renderGroups(d.groups || {}, d.rotation || []);
    renderIdeas(d.ideas || []);
    if (window.lucide) lucide.createIcons();
  }

  function renderStatus(d) {
    const open = d.market_open;
    const frac = d.session_fraction != null ? Math.round(d.session_fraction * 100) : null;
    const st = $('ie-status');
    st.textContent = open ? `盤中 ${frac != null ? frac + '%' : ''}` : '休市';
    st.style.color = open ? '#22c55e' : 'var(--text-muted)';
    if (d.as_of_et) $('ie-updated').textContent = '更新 ' + d.as_of_et.replace('T', ' ').slice(0, 16) + ' ET';
  }

  function renderRegime(r) {
    const posture = r.posture || 'neutral';
    const drivers = (r.drivers || []).map(x => `<span class="ie-chip">${esc(x)}</span>`).join('');
    const cautions = (r.cautions || []).map(x => `<span class="ie-chip caution">⚠ ${esc(x)}</span>`).join('');
    $('ie-regime').className = 'ie-regime ' + posture;
    $('ie-regime').innerHTML = `
      <div class="ie-regime-label">${esc(r.label || '—')}</div>
      <div class="text-sm mt-1" style="color:var(--text-muted)">建議曝險上限 <span class="ie-ceiling" style="color:var(--text-main)">${esc(r.exposure_ceiling || '—')}</span>
        ${r.committee_stance ? `· 委員會 <b>${esc(r.committee_stance)}</b>` : ''}</div>
      <div class="flex flex-wrap gap-1.5 mt-3">${drivers}${cautions}</div>`;
  }

  function renderStats(m, b) {
    // [label, value, sub, signedFlag, unit, tip] — sub 已中文化，tip 為 hover 白話說明
    const cells = [
      ['盤中分數', m.intraday_score, m.intraday_label, false, '',
        '盤中價量綜合分數（−100 破底 ～ +100 強勢）。整合市寬、出貨日、開盤型態等訊號，數字越高盤面越強。'],
      ['市寬 上漲%', b.adv_pct, `${b.advancers ?? '—'}/${b.n ?? '—'}`, false, '%',
        '市場廣度：追蹤的成分股中今日上漲的比例。>50% 代表多數股票在漲（普漲），越高代表漲勢越全面。'],
      ['SPY', m.spy_chg, null, true, '%', 'SPY＝S&P 500 大盤 ETF，今日相對昨收的漲跌幅。代表整體美股。'],
      ['QQQ', m.qqq_chg, null, true, '%', 'QQQ＝那斯達克 100 ETF，今日漲跌幅。偏科技/成長股的溫度計。'],
      ['IWM', m.iwm_chg, null, true, '%', 'IWM＝羅素 2000 小型股 ETF，今日漲跌幅。代表中小型股的風險偏好。'],
      ['VIX', m.vix, vixRegimeZh(m.vix_regime), false, '',
        'VIX＝恐慌指數（S&P 500 未來 30 天隱含波動率）。<15 平靜、15–22 正常、22–32 偏高、>32 恐慌。'],
      ['SKEW', m.skew, skewZh(m.skew_label), false, '',
        'SKEW＝尾部風險指數。越高代表機構越積極買進「黑天鵝」下跌保護；>135 通常視為偏高警訊。'],
      ['F&G', m.fear_greed, fearGreedZh(m.fear_greed_label), false, '',
        'F&G＝CNN 恐懼與貪婪指數（0 極度恐懼 ～ 100 極度貪婪）。低檔常是逢低買點、高檔常是過熱訊號。'],
    ];
    $('ie-stats').innerHTML = cells.map(([k, v, sub, signedFlag, unit, tip]) => {
      const cls = signedFlag ? pctClass(v) : '';
      const val = signedFlag ? signed(v) : (v == null ? '—' : (typeof v === 'number' ? num(v, v >= 100 ? 0 : 1) : v));
      return `<div class="ie-stat" title="${esc(tip || '')}" style="cursor:help"><div class="k">${esc(k)}</div>
        <div class="v ${cls}">${esc(val)}${unit && v != null ? unit : ''}</div>
        ${sub ? `<div class="k" style="margin-top:2px">${esc(sub)}</div>` : ''}</div>`;
    }).join('');
  }

  function renderStrategies(list, rec) {
    $('ie-strat-meta').textContent = `${list.length} 張 · 當日第 ${rec.window_index || '?'} 個視窗`;
    if (!list.length) { $('ie-scards').innerHTML = '<div class="ie-chip">目前無觸發策略</div>'; return; }
    $('ie-scards').innerHTML = list.map(c => {
      const streak = c.streak || 1;
      const repeatCls = c.day_motif ? 'repeat-strong' : (c.highlight ? 'repeat' : '');
      const dayBadge = (c.day_count > 1)
        ? `<span class="ie-repeat-badge" title="當日出現 ${c.day_count} 次">×${c.day_count}</span>` : '';
      const motifBadge = c.day_motif ? `<span class="ie-motif-badge">全日主旋律</span>` : '';
      const streakDots = streak > 1
        ? `<span class="ie-streak-dots" title="連續 ${streak} 個視窗">${'<i></i>'.repeat(Math.min(streak, 6))}</span>` : '';
      const tickers = (c.tickers || []).map(t => `<span class="ie-tk">${esc(t)}</span>`).join('');
      return `<div class="ie-scard ${repeatCls}">
        <div class="ie-sc-top">
          <div class="ie-sc-title">${esc(c.title)}</div>
          <span class="ie-stance ${esc(c.stance)}">${esc(stanceZh(c.stance))}</span>
        </div>
        <div class="flex items-center gap-2 flex-wrap">
          ${dayBadge}${motifBadge}${streakDots}
          <span class="ie-conf">信心 ${num(c.confidence, 2)}</span>
        </div>
        <div class="ie-sc-rat">${esc(c.rationale || '')}</div>
        ${tickers ? `<div class="ie-sc-tickers">${tickers}</div>` : ''}
      </div>`;
    }).join('');
  }

  function stanceZh(s) {
    return ({ favor: '偏多', avoid: '迴避', defensive: '防禦', rotation: '輪動' })[s] || s || '';
  }

  function renderSectors(list) {
    if (!list.length) { $('ie-sectors').innerHTML = '<div class="ie-chip">無資料</div>'; return; }
    const max = Math.max(1, ...list.map(s => Math.abs(s.intraday_avg || 0)));
    $('ie-sectors').innerHTML = list.slice(0, 11).map(s => {
      const v = s.intraday_avg || 0;
      const w = Math.min(100, Math.abs(v) / max * 100);
      const color = v >= 0 ? '#22c55e' : '#f87171';
      return `<div class="ie-bar-row">
        <div class="ie-bar-name">${esc(zhSector(s.sector))} <span class="ie-vd ${esc(s.verdict)}" title="${esc(verdictTip(s.verdict))}">${esc(verdictZh(s.verdict))}</span></div>
        <div class="ie-bar-track"><div class="ie-bar-fill" style="left:${v >= 0 ? '50%' : (50 - w / 2) + '%'};width:${w / 2}%;background:${color}"></div>
          <div style="position:absolute;left:50%;top:0;bottom:0;width:1px;background:var(--border)"></div></div>
        <div class="ie-bar-val ${pctClass(v)}">${signed(v, 1)}%</div>
      </div>`;
    }).join('');
  }

  function renderGroups(g, rotation) {
    const labels = { semiconductors: '半導體', software_platforms: '軟體/平台', crypto_fintech: '加密/fintech' };
    const rows = Object.keys(labels).filter(k => g[k]).map(k => {
      const v = g[k].avg;
      return `<div class="ie-bar-row">
        <div class="ie-bar-name">${labels[k]} <span class="ie-conf">${g[k].up}↑/${g[k].down}↓</span></div>
        <div class="ie-bar-track"><div class="ie-bar-fill" style="left:${v >= 0 ? '50%' : '0%'};width:${Math.min(50, Math.abs(v || 0) * 4)}%;background:${v >= 0 ? '#22c55e' : '#f87171'}"></div>
          <div style="position:absolute;left:50%;top:0;bottom:0;width:1px;background:var(--border)"></div></div>
        <div class="ie-bar-val ${pctClass(v)}">${signed(v, 1)}%</div>
      </div>`;
    }).join('');
    const notes = (rotation || []).map(r =>
      `<div class="ie-chip" style="display:flex;white-space:normal;text-align:left">↻ ${esc(r.from)} → ${esc(r.to)}：${esc(r.note)}</div>`).join('');
    $('ie-groups').innerHTML = rows;
    $('ie-rotation').innerHTML = notes;
  }

  function renderIdeas(list) {
    if (!list.length) { $('ie-ideas').innerHTML = '<tr><td class="ie-mut" style="font-size:12px">無</td></tr>'; return; }
    const tagZh = { trend: '順勢', reversal: '反轉', leader: '領漲' };
    $('ie-ideas').innerHTML = list.map(i => `<tr class="ie-idea-row">
      <td style="font-family:'JetBrains Mono',monospace;font-weight:800">${esc(i.ticker)}</td>
      <td><span class="ie-tk">${esc(tagZh[i.tag] || i.tag)}</span></td>
      <td class="${pctClass(i.chg)}" style="font-family:'JetBrains Mono',monospace;text-align:right">${i.chg == null ? '—' : signed(i.chg, 1) + '%'}</td>
      <td style="color:var(--text-muted)">${esc(i.reason || '')}${i.sector ? ' · ' + esc(zhSector(i.sector)) : ''}</td>
    </tr>`).join('');
  }

  function renderTimeline(hist, strategies) {
    const windows = hist.windows || [];
    const counts = hist.counts || {};
    if (!windows.length) { $('ie-timeline').innerHTML = '<div class="ie-chip">尚無視窗紀錄</div>'; return; }
    // title lookup from current payload
    const titleOf = {};
    (strategies || []).forEach(s => { titleOf[s.id] = s.title; });
    // rows: strategy ids ordered by total count desc
    const ids = Object.keys(counts).sort((a, b) => counts[b] - counts[a]);
    const MOTIF = (hist.day_motif_min || 3);
    $('ie-timeline').innerHTML = ids.map(id => {
      const total = counts[id];
      const motif = total >= 3;
      const cells = windows.map(w => {
        const on = (w.strategy_ids || []).includes(id);
        return `<div class="ie-tl-cell ${on ? 'on' : ''} ${on && motif ? 'motif' : ''}" title="${esc((w.as_of || '').slice(11, 16))}"></div>`;
      }).join('');
      return `<div class="ie-tl-row">
        <div class="ie-tl-label" title="${esc(titleOf[id] || id)}">${esc(titleOf[id] || id)} <b>×${total}</b></div>
        <div class="ie-tl-cells">${cells}</div>
      </div>`;
    }).join('');
  }

  function zhSector(s) {
    return ({
      Technology: '科技', Financials: '金融', Healthcare: '醫療', Energy: '能源',
      Industrials: '工業', Materials: '原物料', Utilities: '公用', Communication: '通訊',
      Real_Estate: '房地產', Consumer_Discretionary: '非核心消費', Consumer_Staples: '核心消費',
    })[s] || s;
  }

  // ── 英文標籤中文化 ──────────────────────────────────────────────
  function verdictZh(v) {
    return ({ HOT: '強勢', FAVOR: '偏多', WARM: '溫和', NEUTRAL: '中性', COOL: '偏弱', AVOID: '迴避' })[v] || v || '';
  }
  function verdictTip(v) {
    return ({
      HOT: '產業最強：盤中漲幅與 5 日前瞻俱佳，可優先布局。',
      FAVOR: '偏多：盤中表現與前瞻正向，可留意。',
      WARM: '溫和偏多：略強於大盤，但訊號未全面。',
      NEUTRAL: '中性：多空訊號混雜，無明顯方向。',
      COOL: '偏弱：略弱於大盤，宜觀望。',
      AVOID: '迴避：盤中走弱且前瞻不佳，暫時避開。',
    })[v] || '產業盤中強弱評等';
  }
  function vixRegimeZh(x) {
    return ({ LOW: '平靜', NORMAL: '正常', ELEVATED: '偏高', CRISIS: '恐慌' })[x] || x || '';
  }
  function skewZh(x) {
    return ({ normal: '正常', elevated: '偏高', high: '偏高警訊' })[x] || x || '';
  }
  function fearGreedZh(x) {
    return ({
      'Extreme Fear': '極度恐懼', 'Fear': '恐懼', 'Neutral': '中性',
      'Greed': '貪婪', 'Extreme Greed': '極度貪婪',
    })[x] || x || '';
  }

  // refresh button
  const btn = $('ie-refresh');
  if (btn) btn.addEventListener('click', async () => {
    btn.style.opacity = '.5'; btn.disabled = true;
    try { await fetch('/api/intraday-eval/refresh', { method: 'POST' }); } catch (e) {}
    setTimeout(async () => { await load(); btn.style.opacity = '1'; btn.disabled = false; }, 5000);
  });

  load();
  setInterval(load, POLL_MS);
})();
