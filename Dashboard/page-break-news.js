/**
 * page-break-news.js — Break News live stream + Claude × Gemini debate viewer.
 * Polls /api/break-news/{feed,state,item/<id>} every BN_POLL_MS.
 * Depends on: utils.js (UI.renderSidebar), i18n.js, news_components.js.
 */

document.addEventListener('DOMContentLoaded', () => {
  const BN_POLL_MS         = 30000;   // feed list
  const BN_DETAIL_POLL_MS  = 5000;    // selected item while still debating

  let currentFilter = 'all';
  let currentItems = [];
  let selectedId = null;
  let detailTimer = null;

  let bnTrend = null;   // TrendChart instance (full mode)

  function $(id) { return document.getElementById(id); }
  function isZh() { return UI && UI.currentLang === 'zh'; }
  function t(zh, en) { return isZh() ? zh : en; }

  function applyTranslations() {
    $('bn-title').textContent = t('突發新聞辯論室', 'Break News War Room');
    $('bn-subtitle').textContent = t('Break News War Room', '突發新聞辯論室');
    $('bn-refresh-label').textContent = t('立即輪詢', 'Poll Now');
    $('bn-loading-label').textContent = t('載入即時新聞中…', 'Loading break news feed…');
    $('bn-thread-empty-label').textContent = t(
      '點選左側新聞卡查看 Claude × Gemini 辯論',
      'Click a card to view the Claude × Gemini debate'
    );
    $('bn-next-label').textContent     = t('下次輪詢', 'Next poll');
    $('bn-queue-label').textContent    = t('排隊', 'Queue');
    $('bn-flight-label').textContent   = t('進行中', 'In flight');
    $('bn-budget-label').textContent   = t('自動辯論額度', 'Auto debate left');
    $('bn-last-poll-label').textContent = t('上次輪詢', 'last poll');
    $('bn-health-label').textContent   = 'LIVE';
    $('bn-raw-title').textContent = t('未閘 Raw 流', 'Un-gated Raw Stream');
    $('bn-raw-hint').textContent  = t('所有抓到的新聞，繞過 score gate', 'All fetched news, bypassing the score gate');
    // Labels rendered fresh on every feed update so counts stay current.
    updateFilterTabs();
    if (bnTrend) bnTrend.refresh();
  }

  function filterTabLabel(key) {
    const labels = isZh()
      ? { all: '全部', debating: '辯論中', closed: '已結束', pending_debate: '待辯論', failed: '失敗' }
      : { all: 'All',  debating: 'Debating', closed: 'Finished', pending_debate: 'Queued', failed: 'Failed' };
    return labels[key] || key;
  }

  function countByState() {
    const counts = { all: 0, debating: 0, closed: 0, pending_debate: 0, failed: 0 };
    for (const it of currentItems) {
      counts.all += 1;
      const s = it.state;
      if (s === 'debating') counts.debating += 1;
      else if (s === 'closed' || s === 'partial_closed') counts.closed += 1;
      else if (s === 'pending_debate') counts.pending_debate += 1;
      else if (s === 'failed' || s === 'gated_cost') counts.failed += 1;
    }
    return counts;
  }

  function updateFilterTabs() {
    const counts = countByState();
    document.querySelectorAll('.bn-filter-tab').forEach(el => {
      const f = el.dataset.filter;
      const n = counts[f] ?? 0;
      el.innerHTML = `${filterTabLabel(f)} <span style="color:var(--text-muted);font-weight:600;font-variant-numeric:tabular-nums;">(${n})</span>`;
    });
  }

  function fmtTime(iso) {
    if (!iso) return '--';
    try {
      const d = new Date(iso);
      return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
    } catch { return iso; }
  }

  async function fetchJson(url, opts) {
    const r = await fetch(url, opts || {});
    if (!r.ok) throw new Error(`${r.status} ${r.statusText}`);
    return r.json();
  }

  async function loadState() {
    try {
      const s = await fetchJson('/api/break-news/state');
      const poller = (s.persisted && s.persisted.poller) || {};
      const debater = (s.persisted && s.persisted.debater) || {};
      // Next-poll display: when next_run is in the past, treat the cycle as
      // overdue (likely a fresh server boot left a stale state file). Show
      // the scheduled time crossed-out with a "等待中" hint so the user
      // doesn't see a past time pretending to be future.
      const nextEl = $('bn-next-poll');
      if (poller.next_run) {
        const next = new Date(poller.next_run).getTime();
        const now  = Date.now();
        if (isFinite(next) && next < now - 30000) {
          const overdueSec = Math.floor((now - next) / 1000);
          nextEl.innerHTML =
            `<span style="text-decoration:line-through;color:var(--text-muted);">${fmtTime(poller.next_run)}</span> ` +
            `<span style="color:#eab308;">${t('等待中', 'waiting')} +${overdueSec}s</span>`;
        } else {
          nextEl.textContent = fmtTime(poller.next_run);
          nextEl.style.color = '';
        }
      } else {
        nextEl.textContent = '--';
      }
      $('bn-last-poll').textContent = poller.last_run
        ? fmtTime(poller.last_run) : '--';
      $('bn-queue-depth').textContent = (debater.queue_depth ?? '0');
      $('bn-in-flight').textContent = (debater.in_flight && debater.in_flight.length) || 0;
      const admission = poller.admission_remaining ?? poller.cost_guard_remaining;
      const capacity = poller.model_debate_capacity;
      const budgetText = (admission == null)
        ? '--'
        : (capacity == null ? `${admission}` : `${admission}/${capacity}`);
      $('bn-budget-left').textContent = budgetText;
      const pair = Array.isArray(poller.break_news_pair) ? poller.break_news_pair.join('×') : '';
      const calls = poller.estimated_calls_per_debate;
      const fb = poller.fallback_backed_capacity ? ` · ${t('含 fallback 容量', 'fallback-backed')}` : '';
      $('bn-budget-left').title = pair
        ? `${pair} · ${calls || '?'} calls/debate · ${t('已扣待辯論 backlog', 'pending backlog deducted')}${fb}`
        : '';
      const ok = poller.last_status === 'ok';
      $('bn-health-dot').style.background = ok ? '#22c55e' : '#eab308';
      $('bn-health-dot').style.boxShadow = ok ? '0 0 8px rgba(34,197,94,0.6)' : '0 0 8px rgba(234,179,8,0.6)';
      $('bn-health-label').textContent = ok ? 'LIVE' : (poller.last_status || 'IDLE').toUpperCase();
    } catch (e) {
      $('bn-health-dot').style.background = '#ef4444';
      $('bn-health-label').textContent = 'OFFLINE';
    }
  }

  function applyFilter() {
    const stream = $('bn-stream');
    if (!currentItems.length) {
      stream.innerHTML = `<div style="text-align:center;padding:60px 20px;color:var(--text-muted);font-size:12px;">
        ${t('暫無突發新聞', 'No break news yet')}</div>`;
      return;
    }
    let items = currentItems;
    if (currentFilter !== 'all') {
      const groups = {
        debating:       new Set(['debating']),
        closed:         new Set(['closed', 'partial_closed']),
        pending_debate: new Set(['pending_debate']),
        failed:         new Set(['failed', 'gated_cost']),
      };
      const want = groups[currentFilter] || new Set([currentFilter]);
      items = items.filter(i => want.has(i.state));
    }
    if (!items.length) {
      stream.innerHTML = `<div style="text-align:center;padding:40px 20px;color:var(--text-muted);font-size:12px;">
        ${t('此分類沒有項目', 'No items in this filter')}</div>`;
      return;
    }
    stream.innerHTML = items.map(it => NewsComponents.renderNewsCard(it)).join('');
    stream.querySelectorAll('.bn-card').forEach(el => {
      el.addEventListener('click', () => selectItem(el.dataset.newsId));
      if (el.dataset.newsId === selectedId) el.classList.add('bn-selected');
    });
  }

  async function loadFeed() {
    try {
      const r = await fetchJson('/api/break-news/feed?limit=100');
      currentItems = r.items || [];
      applyFilter();
      updateFilterTabs();
    } catch (e) {
      $('bn-stream').innerHTML =
        `<div style="text-align:center;padding:40px 20px;color:#ef4444;">Feed error: ${e.message}</div>`;
    }
  }

  // ── Shared HTML-escape helper ────────────────────────────────────
  const esc = (s) => NewsComponents.escapeHtml(s == null ? '' : String(s));

  // ── Un-gated raw breaking-news stream ────────────────────────────
  // Shows every item the poller fetched, gated or not. Each card offers a
  // manual "🔥 Debate" trigger that bypasses the score gate.
  let rawStreamItems = [];

  function rawAge(iso) {
    if (!iso) return '';
    const d = new Date(iso);
    if (isNaN(d)) return '';
    const s = (Date.now() - d.getTime()) / 1000;
    if (s < 0) return 'now';
    if (s < 3600)  return Math.floor(s / 60) + 'm';
    if (s < 86400) return Math.floor(s / 3600) + 'h';
    return Math.floor(s / 86400) + 'd';
  }

  function rawTimeMs(it) {
    const d = new Date(it?.published || it?.fetched_at || 0);
    const ms = d.getTime();
    return Number.isFinite(ms) ? ms : 0;
  }

  function renderRawCard(it) {
    const sc = Number(it.shallow_score) || 0;
    const score = it.shallow_score == null ? '—'
      : (sc > 0 ? '+' : '') + sc.toFixed(1);
    const scoreColor = sc >= 2 ? 'background:rgba(34,197,94,0.16);color:#4ade80;'
      : sc <= -2 ? 'background:rgba(239,68,68,0.16);color:#f87171;'
      : 'background:rgba(161,161,170,0.14);color:var(--text-muted);';
    const passed = !!it.gate_passed;
    const promoted = !!it.news_id;
    const gateBadge = passed
      ? `<span class="bn-raw-gate pass">${t('過閘', 'pass')}</span>`
      : `<span class="bn-raw-gate block">${t('未閘', 'gated')}</span>`;
    const age = rawAge(it.published || it.fetched_at);
    const cls = ['bn-raw-card'];
    if (!passed) cls.push('gated');
    if (promoted) cls.push('promoted');
    const btn = promoted
      ? `<button class="bn-raw-debate-btn" data-key="${esc(it.key)}" disabled>${t('已辯論', 'debated')}</button>`
      : `<button class="bn-raw-debate-btn" data-key="${esc(it.key)}">${t('🔥 辯論', '🔥 Debate')}</button>`;
    const hl = it.url
      ? `<a class="bn-raw-headline" href="${esc(it.url)}" target="_blank" rel="noopener" title="${esc(it.headline)}" style="text-decoration:none;">${esc(it.headline)}</a>`
      : `<span class="bn-raw-headline" title="${esc(it.headline)}">${esc(it.headline)}</span>`;
    return `<div class="${cls.join(' ')}">
      <span class="bn-raw-score" style="${scoreColor}">${score}</span>
      ${hl}
      <span class="bn-raw-meta">${esc(it.source || '')}</span>
      <span class="bn-raw-meta">${age}</span>
      ${gateBadge}
      ${btn}
    </div>`;
  }

  function renderRawStream() {
    const list = $('bn-raw-list');
    const empty = $('bn-raw-empty');
    if (!list || !empty) return;
    $('bn-raw-count').textContent = rawStreamItems.length;
    if (!rawStreamItems.length) {
      list.innerHTML = '';
      empty.style.display = '';
      empty.textContent = t('暫無 raw 新聞', 'No raw news yet');
      return;
    }
    empty.style.display = 'none';
    list.innerHTML = rawStreamItems.map(renderRawCard).join('');
    list.querySelectorAll('.bn-raw-debate-btn').forEach(btn => {
      if (!btn.disabled) btn.addEventListener('click', () => triggerRawDebate(btn));
    });
  }

  async function triggerRawDebate(btn) {
    const key = btn.dataset.key;
    if (!key) return;
    btn.disabled = true;
    const orig = btn.textContent;
    btn.textContent = t('排入中…', 'queuing…');
    try {
      const res = await fetchJson('/api/break-news/raw/debate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ key }),
      });
      btn.textContent = t('已排入辯論', 'queued');
      btn.dataset.nid = res.news_id || '';
      // Surface the new debate item in the main feed shortly after.
      setTimeout(() => { loadFeed(); loadState(); }, 1500);
    } catch (e) {
      btn.disabled = false;
      btn.textContent = orig;
      alert(t('觸發辯論失敗: ', 'Debate trigger failed: ') + e.message);
    }
  }

  async function loadRawStream() {
    try {
      const r = await fetchJson('/api/break-news/raw-stream?limit=120');
      rawStreamItems = (r.items || []).slice().sort((a, b) => rawTimeMs(b) - rawTimeMs(a));
      renderRawStream();
    } catch (e) {
      const empty = $('bn-raw-empty');
      if (empty) { empty.style.display = ''; empty.textContent = 'Raw stream error: ' + e.message; }
    }
  }

  async function loadDetail(id) {
    const panel = $('bn-thread-panel');
    if (!id) {
      panel.innerHTML = `<div class="bn-thread-empty"><i data-lucide="message-circle" class="w-8 h-8 mx-auto mb-3 text-zinc-600"></i>
        <div>${t('點選左側新聞卡查看 Claude × Gemini 辯論', 'Click a card to view the Claude × Gemini debate')}</div></div>`;
      if (window.lucide && lucide.createIcons) lucide.createIcons();
      return;
    }
    try {
      const item = await fetchJson(`/api/break-news/item/${id}`);
      renderDetail(item);
    } catch (e) {
      panel.innerHTML = `<div style="color:#ef4444;padding:14px;">Error: ${e.message}</div>`;
    }
  }

  function renderDetail(item) {
    const panel = $('bn-thread-panel');
    const C = window.NewsComponents;
    const src = item.source || {};
    const summary = item.summary || {};
    const header = `<div class="bn-thread-header">
      <div style="flex:1;min-width:0;">
        <div style="display:flex;gap:8px;align-items:center;flex-wrap:wrap;margin-bottom:6px;">
          ${C.renderStatePill(item.state)}
          ${C.renderScoreBadge((item.triage||{}).shallow_score)}
          ${C.renderSourcePill(src.name, src.credibility)}
        </div>
        <div style="font-size:14px;font-weight:600;color:var(--text-card-title);line-height:1.4;">
          ${C.escapeHtml(item.headline || '')}
        </div>
        ${(src.url && !src.url.startsWith('futu://'))
          ? `<a href="${C.escapeHtml(src.url)}" target="_blank" rel="noopener"
              style="font-size:11px;color:#3b82f6;display:inline-block;margin-top:6px;">
              ${t('開啟原文', 'open source')} ↗</a>`
          : ''}
      </div>
      <button class="bn-replay-btn" data-replay="${C.escapeHtml(item.news_id)}">⟳ ${t('重跑', 'Replay')}</button>
    </div>`;

    const thread = (item.thread || []).map(c => C.renderThreadBubble(c)).join('') ||
      `<div class="bn-thread-empty">${t('尚無辯論留言', 'No debate yet — waiting for the next debate scan…')}</div>`;

    let summaryBlock = '';
    if (summary && (summary.consensus_verdict || (summary.merged_entities && summary.merged_entities.tickers))) {
      const ent = summary.merged_entities || {};
      const counts = C.entityTotal(ent);
      const verdictLabel = C.pickVerdictLabel(summary.consensus_verdict) || '?';
      const closeLabel = C.pickCloseReasonLabel(summary.close_reason) || '?';
      const bullList = Array.isArray(summary.bull_summary) ? summary.bull_summary : [];
      const bearList = Array.isArray(summary.bear_summary) ? summary.bear_summary : [];
      const finalTake = summary.final_take;
      const finalBy = summary.final_take_by;
      const finalByLabel = finalBy === 'claude' ? 'Claude' : finalBy === 'gemini' ? 'Gemini' : '';

      const bulletList = (arr, color, headerZh, headerEn) => {
        if (!arr || arr.length === 0) return '';
        const lis = arr.map(p => `<li style="margin:4px 0;color:var(--text-main);line-height:1.55;">${C.escapeHtml(p)}</li>`).join('');
        return `<div style="margin-top:10px;padding:8px 10px 8px 12px;border-left:3px solid ${color};
          background:color-mix(in srgb,${color},transparent 92%);border-radius:4px;">
          <div style="font-size:10px;font-weight:800;letter-spacing:0.06em;text-transform:uppercase;
            color:${color};margin-bottom:4px;">${t(headerZh, headerEn)}</div>
          <ul style="margin:0;padding-left:18px;font-size:12px;">${lis}</ul>
        </div>`;
      };

      // Knowledge Graph footer
      const newsId = item.news_id || '';
      const isClosed = item.state === 'closed' || item.state === 'partial_closed';
      const graphStatus = item.graph_status || 'pending';
      const graphFooter = isClosed
        ? `<div style="margin-top:14px;padding:10px 12px;border-radius:8px;
            background:rgba(59,130,246,0.06);border:1px solid rgba(59,130,246,0.30);">
            <div style="font-size:10px;font-weight:800;letter-spacing:0.06em;text-transform:uppercase;
              color:#60a5fa;margin-bottom:6px;">🌐 ${t('知識圖譜入口', 'Knowledge Graph')}</div>
            <div style="font-size:11px;color:var(--text-muted);line-height:1.55;">
              ${t('此次辯論已歸納為節點', 'This debate registers as node')}
              <code style="background:rgba(255,255,255,0.06);padding:1px 5px;border-radius:3px;
                color:var(--text-main);font-size:10px;">catalyst:news_${C.escapeHtml(newsId)}</code><br>
              ${t('將連到', 'Will connect to')}
              <strong style="color:var(--text-main);">${counts.tickers}</strong> ${t('檔個股', 'tickers')} ·
              <strong style="color:var(--text-main);">${counts.sectors}</strong> ${t('個產業', 'sectors')} ·
              <strong style="color:var(--text-main);">${counts.themes}</strong> ${t('個主題', 'themes')} ·
              <strong style="color:var(--text-main);">${counts.tech_keywords}</strong> ${t('個技術節點', 'narratives')}<br>
              <span style="color:var(--text-muted);">${t('狀態', 'Status')}:
                <strong style="color:${graphStatus === 'promoted' ? '#22c55e' : '#eab308'};">${C.escapeHtml(graphStatus)}</strong>
                <span style="color:var(--text-muted);">(${t('下次 daily_update.sh Step 8 寫入', 'commits on next daily_update.sh Step 8')})</span>
              </span>
            </div>
            <a href="/graph.html" style="display:inline-block;margin-top:8px;font-size:11px;
              color:#60a5fa;text-decoration:none;font-weight:600;">${t('在圖譜中查看', 'View in graph')} →</a>
          </div>`
        : '';

      summaryBlock = `<div class="bn-summary-block" style="margin-top:14px;">
        <div style="font-size:11px;font-weight:800;letter-spacing:0.06em;text-transform:uppercase;
          color:#22c55e;margin-bottom:8px;display:flex;align-items:center;gap:6px;">
          🟢 ${t('合議摘要', 'Consensus Summary')}
        </div>
        <div style="font-size:13px;color:var(--text-main);margin-bottom:6px;">
          <strong style="font-size:14px;">${C.escapeHtml(verdictLabel)}</strong>
          <span style="color:var(--text-muted);margin-left:6px;font-size:11px;">
            · ${summary.rounds_completed ?? '?'} ${t('輪', 'rounds')}
            · ${t('收斂方式', 'close')}: ${C.escapeHtml(closeLabel)}
          </span>
        </div>
        ${finalTake ? `<div style="font-size:12px;color:var(--text-main);margin:8px 0 6px;padding:8px 10px;
          background:rgba(34,197,94,0.06);border-left:3px solid #22c55e;border-radius:4px;">
          <span style="color:#22c55e;font-weight:700;">🎯 ${t('最終結論', 'Final Take')}${finalByLabel ? ` (${finalByLabel})` : ''}:</span>
          <span style="margin-left:4px;">${C.escapeHtml(finalTake)}</span>
        </div>` : ''}
        ${summary.divergence_note ? `<div style="font-size:11px;color:var(--text-muted);margin-top:6px;font-style:italic;">
          ${t('分歧', 'Divergence')}: ${C.escapeHtml(summary.divergence_note)}</div>` : ''}
        ${bulletList(bullList, '#22c55e', '✅ 正方意見 (Bull Case)', '✅ Bull Case')}
        ${bulletList(bearList, '#ef4444', '❌ 反方意見 (Bear Case)', '❌ Bear Case')}
        <div style="margin-top:14px;padding-top:10px;border-top:1px solid rgba(161,161,170,0.18);">
          <div style="font-size:10px;font-weight:800;letter-spacing:0.06em;text-transform:uppercase;
            color:var(--text-muted);margin-bottom:8px;">
            🧩 ${t('萃取實體', 'Extracted Entities')}
            <span style="color:var(--text-muted);font-weight:500;text-transform:none;letter-spacing:0;">— ${t('知識圖譜輸入源', 'Knowledge Graph inputs')}</span>
          </div>
          ${C.renderEntityChipsGrouped(ent) || `<div style="color:var(--text-muted);font-size:11px;">${t('無萃取實體', 'No entities extracted')}</div>`}
        </div>
        ${graphFooter}
      </div>`;
    } else if (item.state === 'debating' || item.state === 'pending_debate') {
      summaryBlock = `<div class="bn-summary-block" style="margin-top:14px;color:var(--text-muted);font-size:12px;
        font-style:italic;text-align:center;padding:14px;">
        ${t('辯論進行中，結論將於收斂後產生…', 'Debate in progress — summary will appear when closed.')}
      </div>`;
    }

    panel.innerHTML = header + thread + summaryBlock;
    const replay = panel.querySelector('[data-replay]');
    if (replay) replay.addEventListener('click', async (e) => {
      e.stopPropagation();
      const id = replay.dataset.replay;
      replay.disabled = true; replay.textContent = '⟳ …';
      try {
        await fetchJson(`/api/break-news/item/${id}/replay`, { method: 'POST' });
        setTimeout(() => loadDetail(id), 500);
      } catch (err) {
        replay.textContent = t('失敗', 'fail');
      }
    });
    if (window.lucide && lucide.createIcons) lucide.createIcons();
  }

  function selectItem(id) {
    selectedId = id;
    document.querySelectorAll('.bn-card').forEach(el => {
      el.classList.toggle('bn-selected', el.dataset.newsId === id);
    });
    loadDetail(id);
    if (detailTimer) clearInterval(detailTimer);
    detailTimer = setInterval(() => {
      const it = currentItems.find(i => i.news_id === id);
      if (it && (it.state === 'debating' || it.state === 'pending_debate')) {
        loadDetail(id);
      }
    }, BN_DETAIL_POLL_MS);
  }

  // Filter tab clicks
  document.querySelectorAll('.bn-filter-tab').forEach(el => {
    el.addEventListener('click', () => {
      document.querySelectorAll('.bn-filter-tab').forEach(x => x.classList.remove('active'));
      el.classList.add('active');
      currentFilter = el.dataset.filter;
      applyFilter();
    });
  });

  // Manual refresh button
  $('bn-refresh-btn').addEventListener('click', async () => {
    const btn = $('bn-refresh-btn');
    btn.disabled = true;
    btn.style.opacity = '0.6';
    try {
      await fetchJson('/api/break-news/refresh', { method: 'POST' });
      await loadFeed();
      await loadState();
      if (bnTrend) await bnTrend.reload();
      await loadRawStream();
    } finally {
      btn.disabled = false;
      btn.style.opacity = '';
    }
  });

  // Boot
  if (typeof UI !== 'undefined' && UI.renderSidebar) {
    try { UI.renderSidebar(); } catch (e) { console.warn('sidebar', e); }
  }
  // Raw-stream collapse toggle
  $('bn-raw-toggle').addEventListener('click', () => {
    $('bn-raw-strip').classList.toggle('collapsed');
  });

  // Full-mode sentiment-trend chart (entity selector + legend + hover cursor)
  bnTrend = TrendChart.mount({
    root: $('bn-trend-mount'), compact: false, withSelector: true,
  });

  applyTranslations();
  loadFeed();
  loadState();
  loadRawStream();
  setInterval(loadFeed, BN_POLL_MS);
  setInterval(loadState, BN_POLL_MS);
  setInterval(() => { if (bnTrend) bnTrend.reload(); }, BN_POLL_MS);
  setInterval(loadRawStream, BN_POLL_MS);
  if (window.lucide && lucide.createIcons) lucide.createIcons();
});
