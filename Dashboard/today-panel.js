// ── V4.6 — Today 工作台 (index.html #today-workbench) ─────────────────────
// Three cards: 今日該做的事 (#tw-actions) / 最新產出 (#tw-outputs) / 晨報 (#tw-brief).
// Server aggregation from /api/today; client merges kill_triggers.json,
// data.json upcoming_events (≤7d earnings on positions/watchlist) and
// break-news stale-pending. Read-only; actions deep-link to existing pages.
(function () {
  'use strict';

  const esc = s => String(s == null ? '' : s)
    .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/"/g, '&quot;');

  function isZh() {
    return (typeof UI !== 'undefined' && UI.currentLang === 'zh');
  }

  async function fetchJson(url) {
    try {
      const r = await fetch(url);
      if (!r.ok) return null;
      return await r.json();
    } catch (e) { return null; }
  }

  // ── 今日該做的事 ────────────────────────────────────────────────────────
  function buildActions(today, kt, stalePending, data) {
    const zh = isZh();
    const acts = [];

    // 0. triggered kill conditions (red, top priority)
    const ktItems = (kt && kt.items) || [];
    ktItems.filter(i => i.status === 'triggered').forEach(i => {
      acts.push({
        prio: 0, icon: '🔴',
        text: (zh ? '推翻條件已觸發：' : 'Kill trigger fired: ') + (i.ticker || i.sector || ''),
        meta: (i.condition || '').slice(0, 90),
        href: 'decisions.html',
      });
    });

    // 1. stale Claude protocols (sector / news)
    (today.due_actions || []).filter(a => a.kind === 'protocol_stale').forEach(a => {
      acts.push({
        prio: 1, icon: '🛰️',
        text: (zh ? a.label : (a.label_en || a.label)) + (zh ? ' 過期' : ' stale'),
        meta: (zh ? '上次 ' : 'last ') + a.age_str,
        onclick: "document.getElementById('preflight-btn')?.click()",
      });
    });

    // 2. due ops scripts (runnable entries get a one-click ▶)
    (today.due_actions || []).filter(a => a.kind === 'ops_script').forEach(a => {
      const age = a.age_hours != null ? Math.round(a.age_hours / 24) : null;
      acts.push({
        prio: 2, icon: '⏰',
        text: (a.name || a.id) + (a.status === 'never_run'
          ? (zh ? '（從未跑過）' : ' (never run)')
          : (zh ? ' 到期' : ' due')),
        meta: age != null ? (zh ? `上次 ${age} 天前 · ${a.cadence}` : `${age}d ago · ${a.cadence}`) : (a.cadence || ''),
        href: 'ops.html',
        run: (a.protocol_id || a.endpoint) ? { protocol_id: a.protocol_id, endpoint: a.endpoint } : null,
      });
    });

    // 3. earnings ≤7d on positions / structural watchlist / recent on-watch tickers
    const watch = new Set();
    ((data && data.positions) || []).filter(p => p.status !== 'closed').forEach(p => watch.add(p.ticker));
    (((data || {}).structural_watchlist || {}).candidates || []).forEach(c => watch.add(c.ticker));
    ((data && data.recent_analysis) || []).forEach(r => { if (r.on_watchlist && r.ticker) watch.add(r.ticker); });
    const todayStr = new Date().toISOString().slice(0, 10);
    const limitStr = new Date(Date.now() + 7 * 864e5).toISOString().slice(0, 10);
    ((data && data.upcoming_events) || [])
      .filter(e => e.category === 'earnings' && e.date >= todayStr && e.date <= limitStr)
      .filter(e => (e.tickers || []).some(t => watch.has(t)))
      .slice(0, 5)
      .forEach(e => {
        const t = (e.tickers || [])[0] || '';
        acts.push({
          prio: 3, icon: '📋',
          text: t + (zh ? ' 財報 ' : ' earnings ') + e.date,
          meta: e.description || '',
          href: 'earnings.html',
        });
      });

    // 4. kill conditions expiring ≤2d (manual review)
    ktItems.filter(i => (i.status === 'armed' || i.status === 'manual') && i.days_left >= 0 && i.days_left <= 2)
      .slice(0, 4)
      .forEach(i => {
        acts.push({
          prio: 4, icon: '⏳',
          text: (i.ticker || i.sector || '') + (zh ? ` 推翻條件剩 ${i.days_left} 天` : ` kill cond ${i.days_left}d left`),
          meta: (i.condition || '').slice(0, 90),
          href: 'decisions.html',
        });
      });

    // 5. break-news stale pending
    if (stalePending && stalePending.count > 0) {
      acts.push({
        prio: 5, icon: '📻',
        text: zh ? `${stalePending.count} 條突發新聞待辯論 >2h` : `${stalePending.count} break-news pending >2h`,
        meta: '',
        href: 'break-news.html',
      });
    }

    acts.sort((a, b) => a.prio - b.prio);
    return acts;
  }

  async function runDue(runSpec, btn) {
    btn.disabled = true;
    btn.textContent = '⏳';
    try {
      const r = runSpec.endpoint
        ? await fetch(runSpec.endpoint, { method: 'POST' })
        : await fetch('/api/protocol-queue', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name: runSpec.protocol_id }),
          });
      const d = await r.json().catch(() => ({}));
      btn.textContent = (!r.ok || d.error) ? '⚠' : '✓';
    } catch (e) { btn.textContent = '⚠'; }
  }

  function renderActions(host, acts) {
    const zh = isZh();
    const rows = acts.length ? acts.map((a, i) => `
      <a class="tw-row" ${a.href ? `href="${a.href}"` : 'href="#"'} ${a.onclick ? `onclick="${a.onclick};return false"` : ''}>
        <span class="tw-ico">${a.icon}</span>
        <span class="tw-main"><span class="tw-text">${esc(a.text)}</span>
        ${a.meta ? `<span class="tw-meta">${esc(a.meta)}</span>` : ''}</span>
        ${a.run ? `<button class="tw-run" data-i="${i}" title="${zh ? '立即執行' : 'run now'}">▶</button>` : ''}
      </a>`).join('')
      : `<div class="tw-empty">${zh ? '✅ 今天沒有待辦 — 系統乾淨' : '✅ Nothing due — all clean'}</div>`;
    host.innerHTML = `
      <div class="tw-card-title">${zh ? '📌 今日該做的事' : '📌 Today’s Actions'}
        <span class="tw-count">${acts.length || ''}</span></div>
      <div class="tw-list">${rows}</div>`;
    host.querySelectorAll('.tw-run').forEach(btn => {
      btn.addEventListener('click', (e) => {
        e.preventDefault();
        e.stopPropagation();
        runDue(acts[Number(btn.dataset.i)].run, btn);
      });
    });
  }

  // ── 最新產出 feed ──────────────────────────────────────────────────────
  function renderOutputs(host, outputs) {
    const zh = isZh();
    const rows = (outputs || []).slice(0, 8).map(o => {
      const label = zh ? (o.label_zh || o.type) : (o.label_en || o.type);
      const sum = (o.summary_lines || [])[0] || '';
      return `
      <a class="tw-row" href="reports.html#report=${encodeURIComponent(o.filename)}">
        <span class="rli-type rli-type-${esc(o.type)} tw-chip">${esc(label)}</span>
        <span class="tw-main">
          <span class="tw-text">${esc(o.ticker ? o.ticker + ' · ' : '')}${esc(o.date || '')}<span class="tw-file"> ${esc(o.filename)}</span></span>
          ${sum ? `<span class="tw-meta">${esc(sum)}</span>` : ''}
        </span>
      </a>`;
    }).join('');
    host.innerHTML = `
      <div class="tw-card-title">${zh ? '🗂 最新產出' : '🗂 Latest Outputs'}
        <a class="tw-more" href="reports.html">${zh ? '全部 →' : 'all →'}</a></div>
      <div class="tw-list">${rows || `<div class="tw-empty">—</div>`}</div>`;
  }

  // ── 晨報 digest ───────────────────────────────────────────────────────
  function renderBrief(host, mb) {
    const zh = isZh();
    if (!mb) {
      host.innerHTML = `<div class="tw-card-title">${zh ? '🌅 盤前晨報' : '🌅 Morning Brief'}</div>
        <div class="tw-empty">${zh ? '尚無晨報 — 跑盤前檢查產生' : 'No brief yet — run pre-market check'}</div>`;
      return;
    }
    const staleNote = mb.is_today ? '' : `
      <div class="tw-stale" onclick="document.getElementById('preflight-btn')?.click()">
        ⚠️ ${zh ? `晨報為 ${esc(mb.date)} — 點此跑盤前檢查` : `Brief is from ${esc(mb.date)} — click to refresh`}</div>`;
    const regime = (mb.regime_lines || []).map(l => `<div class="tw-regime">${esc(l)}</div>`).join('');
    const col = (title, rows, cls) => `
      <div class="tw-mov-col"><div class="tw-mov-title ${cls}">${title}</div>
        ${(rows || []).map(r => `<div class="tw-mov-row"><span>${esc(r[0])}</span><span class="${cls}">${esc(r[1])}</span></div>`).join('')}</div>`;
    host.innerHTML = `
      <div class="tw-card-title">${zh ? '🌅 盤前晨報' : '🌅 Morning Brief'}
        <a class="tw-more" href="reports.html#report=${encodeURIComponent(mb.filename)}">${zh ? '完整 →' : 'full →'}</a></div>
      ${staleNote}
      <div class="tw-list">${regime}</div>
      <div class="tw-movers">
        ${col(zh ? '領漲' : 'Gainers', mb.gainers, 'tw-up')}
        ${col(zh ? '領跌' : 'Losers', mb.losers, 'tw-down')}
      </div>`;
  }

  async function boot() {
    const section = document.getElementById('today-workbench');
    if (!section) return;
    const [today, kt, sp] = await Promise.all([
      fetchJson('/api/today'),
      fetchJson('kill_triggers.json?t=' + Date.now()),
      fetchJson('/api/break-news/stale-pending'),
    ]);
    if (!today) return; // server route missing (old daemon) — keep section hidden
    let data = null;
    try { data = await DataStore.get(); } catch (e) { /* workbench still renders without data.json */ }

    section.classList.remove('hidden');
    renderActions(document.getElementById('tw-actions'), buildActions(today, kt, sp, data));
    renderOutputs(document.getElementById('tw-outputs'), today.latest_outputs);
    renderBrief(document.getElementById('tw-brief'), today.morning_brief);
  }

  document.addEventListener('DOMContentLoaded', boot);
})();
