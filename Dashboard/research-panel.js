/* Shared exploratory research cards. Formal analysis stays in its own workflow. */
(function () {
  'use strict';
  const lanes = { 'decisions.html': 'invest', 'earnings.html': 'earnings',
    'earnings-detail.html': 'earnings', 'momentum.html': 'momentum',
    'graph.html': 'nexus' };
  const page = location.pathname.split('/').pop();
  const lane = lanes[page];
  if (!lane) return;
  const esc = value => String(value ?? '').replace(/[&<>"']/g, c =>
    ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  const safeUrl = value => {
    try { const u = new URL(value); return ['https:', 'http:'].includes(u.protocol) ? u.href : '#'; }
    catch { return '#'; }
  };
  const status = { supported: '證據支持', contested: '仍有爭議', insufficient: '證據不足', retracted: '已撤回' };
  const kind = { fact: '來源事實', inference: '推論', question: '待回答' };
  const trigger = { news: '新聞', filing: '公告／申報', calendar: '排程發布', followup: '研究追蹤' };
  const panel = document.createElement('section');
  panel.className = 'research-panel';
  panel.innerHTML = `<style>
    .research-panel{margin:18px 0;padding:20px;border:1px solid #34465c;border-radius:16px;background:rgba(20,30,46,.92);color:#e2e8f0}
    .research-panel h2{font-size:18px;font-weight:700;margin:0 0 8px}.research-panel p{margin:6px 0}
    .research-panel form{display:flex;gap:8px;flex-wrap:wrap;margin:12px 0}.research-panel input{background:#101b2b;color:#fff;border:1px solid #52657b;border-radius:6px;padding:7px;width:150px}
    .research-panel button,.research-panel a.rp-action{display:inline-block;color:#b9e6ff;background:#20374d;border:1px solid #405b76;padding:5px 9px;border-radius:6px;margin:4px 4px 0 0;cursor:pointer}
    .rp-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,300px),1fr));gap:12px}.rp-card{border:1px solid #41506a;border-radius:10px;padding:14px;min-width:0}
    .rp-card[data-status="contested"]{border-color:#ba8b3d}.rp-card[data-status="retracted"]{opacity:.6}
    .rp-meta{font-size:12px;color:#b4bfd0}.rp-card blockquote{border-left:2px solid #657c98;padding-left:9px;font-size:12px;margin:8px 0;overflow-wrap:anywhere}
    .research-panel details{margin-top:10px;font-size:12px}.rp-health{white-space:pre-wrap}.rp-error{color:#fbbf94}
    </style><h2>事件研究｜${lane === 'all' ? '最新主張與反證' : '本頁研究線索'}</h2>
    <p class="rp-meta">探索資訊。主張保留原文、反證與追蹤條件；A/B 使用同一模型，不代表獨立來源確認。</p>
    <form><label>個股 <input name="ticker" placeholder="例如 NVDA" maxlength="10" aria-label="研究股票代號"></label><button>查詢</button><button type="button" data-all>全部事件</button></form>
    <p class="rp-state rp-meta" aria-live="polite">載入研究資料…</p><div class="rp-grid"></div>
    <details><summary>來源與觀察狀態</summary><div class="rp-health"></div></details>`;
  const mount = document.getElementById('sq-mount');
  if (mount) mount.before(panel);
  else (document.querySelector('main') || document.body).prepend(panel);
  const input = panel.querySelector('input');
  input.value = (new URLSearchParams(location.search).get('ticker') || '').toUpperCase();
  let current = null;
  async function load() {
    try {
      const ticker = input.value.trim().toUpperCase();
      const response = await fetch(`/api/research?lane=${lane}&ticker=${encodeURIComponent(ticker)}&limit=12`);
      const data = await response.json();
      if (!response.ok) throw new Error(data.error || '研究資料讀取失敗');
      current = data;
      panel.querySelector('.rp-state').textContent = data.cards.length
        ? `${ticker ? ticker + '｜' : ''}${data.since ? '自上次分析 ' + data.since + ' 起｜' : ''}${data.cards.length} 個研究主張`
        : (data.enabled ? '目前沒有符合條件的新研究主張。' : '研究機制尚未啟用；驗證完成後開始觀察。');
      panel.querySelector('.rp-grid').innerHTML = data.cards.map(card => {
        const refs = [...card.evidence_refs, ...card.challenge_refs];
        const excerpts = refs.slice(0, 3).map(ref => {
          const source = card.evidence.find(e => e.id === ref.evidence_id);
          const provenance = source?.content_type === 'original_page_excerpt' ? '原始網頁片段' : '來源摘要';
          return `<blockquote>${esc(ref.quote)}<br><a href="${esc(safeUrl(source?.url))}" target="_blank" rel="noopener noreferrer">${esc(source?.source || '來源')} ↗</a> · ${provenance}</blockquote>`;
        }).join('');
        return `<article class="rp-card" data-status="${esc(card.status)}">
          <div class="rp-meta">${esc(status[card.status])} · ${esc(kind[card.kind])} · ${esc(trigger[card.trigger])}</div>
          ${card.new_evidence_pending ? '<p class="rp-error">已有新證據，等待重新審查。</p>' : ''}
          <p><strong>${esc(card.text)}</strong></p><p class="rp-meta">${esc(card.tickers.join(' · '))}｜${esc(card.horizon)}</p>
          <p class="rp-meta">來源發布：${esc(card.published_at || '時間未明')}</p>
          <p>審查：${esc(card.challenge)}</p><details><summary>原文依據與反證</summary>${excerpts}<p>反證條件：${esc(card.falsifier)}</p></details>
          <p class="rp-meta">下一步：${esc(card.followup.condition)}</p>
          <button type="button" data-track="${esc(card.id)}">追蹤新證據</button>
          ${card.tickers.slice(0, 3).map(t => `<a class="rp-action" href="decisions.html?ticker=${encodeURIComponent(t)}">${esc(t)} 個股</a>`).join('')}
        </article>`;
      }).join('');
      const exp = data.experiment;
      const service = data.service;
      if (service) {
        const state = {live: '正式研究運行中', live_blocked: '正式研究暫停新推論', stopped: '正式研究已停止'};
        panel.querySelector('.rp-state').textContent += `｜${service.worker_pid ? (state[service.status] || service.status) : '正式研究程序未運行'}`;
      } else if (exp?.status?.startsWith('complete')) {
        panel.querySelector('.rp-state').textContent += '｜六小時觀察已結束，目前未啟動新的辯論。';
      }
      const lines = Object.entries(data.source_health).map(([name, h]) =>
        `${name}：${h.status}｜取得 ${h.fetched ?? 0}｜6 小時內 ${h.fresh ?? 0}${h.http_status ? '｜HTTP ' + h.http_status : ''}`);
      const production = service ? [`正式研究｜${service.status}｜最後更新 ${service.heartbeat_at || '待定'}`,
        `每次預估 ${service.estimated_tokens_per_call ?? '未知'} token｜滾動 24 小時 ${service.budget?.calls ?? 0} 次呼叫`,
        ...(service.wait_until ? [`Broker 冷卻至：${service.wait_until}`] : []),
        ...(service.blocker ? [`暫停原因：${service.blocker}`] : [])] : [];
      panel.querySelector('.rp-health').textContent = [...production,
        exp ? `實驗 ${exp.id}｜${exp.status}｜${exp.started_at || '尚未起算'} → ${exp.deadline || '待定'}` : '尚未開始實驗', ...lines].join('\n');
    } catch (error) { panel.querySelector('.rp-state').textContent = error.message; }
  }
  panel.querySelector('form').addEventListener('submit', event => { event.preventDefault(); load(); });
  panel.querySelector('[data-all]').addEventListener('click', () => { input.value = ''; load(); });
  panel.addEventListener('click', async event => {
    const button = event.target.closest('[data-track]');
    if (!button || !current) return;
    const card = current.cards.find(c => c.id === button.dataset.track);
    button.disabled = true;
    try {
      const response = await fetch('/api/research/track', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ claim_id: card.id, revision: card.revision }) });
      const result = await response.json();
      if (!response.ok) throw new Error(result.error);
      button.textContent = '已追蹤';
    } catch (error) { button.disabled = false; panel.querySelector('.rp-state').textContent = error.message; }
  });
  load();
  setInterval(() => { if (!document.hidden) load(); }, 60000);
})();
