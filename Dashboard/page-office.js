/*
 * page-office.js — AI Office: autonomous multi-agent collaboration board.
 * Depends on: utils.js (UI.renderSidebar), i18n.js, marked.js (CDN).
 *
 * Streams a run's structured events over SSE and renders each role turn as a
 * card. No terminal, no raw bytes — the engine is the programmatic team loop
 * (scripts/office/orchestrator.py).
 */
document.addEventListener('DOMContentLoaded', () => {
  const $ = (id) => document.getElementById(id);
  if (typeof UI !== 'undefined') {
    try { UI.initTheme && UI.initTheme(); } catch (e) {}
    try { UI.renderSidebar && UI.renderSidebar('office'); } catch (e) {}
    try { UI.applyNavTranslations && UI.applyNavTranslations(); } catch (e) {}
    try { UI.icons && UI.icons(); } catch (e) {}
  }

  let token = null;
  let es = null;
  let currentRun = null;
  let lastRound = -1;

  const md = (s) => { try { return marked.parse(s || ''); } catch (e) { return (s || ''); } };
  const setErr = (m) => { $('of-err').textContent = m || ''; };

  // ── status + chrome ───────────────────────────────────────────────────
  const PHASE_LABEL = {
    research: '⓪ 資料蒐集', draft: '① 獨立觀點', adjudicate: '② 分歧萃取',
    rebuttal: '③ 定點交鋒', verdict: '④ 終局裁決',
  };
  const ROLE_COLORS = {
    lead: ['#3b82f6', '#60a5fa'], critic: ['#f59e0b', '#fbbf24'],
    verifier: ['#22c55e', '#4ade80'], trader: ['#ec4899', '#f472b6'],
    researcher: ['#14b8a6', '#2dd4bf'],
  };
  // Roles define perspectives; the broker assigns actual providers per call.
  function renderRolePills(meta) {
    const host = $('of-role-pills');
    if (!host || !meta || !meta.roles || !meta.roles.length) return;
    const pills = [`<span class="of-pill researcher" style="border-color:#14b8a6;color:#2dd4bf">Researcher · Broker</span>`]
      .concat(meta.roles.map(r => {
        const c = ROLE_COLORS[r.key] || ['#a1a1aa', '#d4d4d8'];
        return `<span class="of-pill ${r.key}" style="border-color:${c[0]};color:${c[1]}">${r.name} · ${r.engine}</span>`;
      }));
    host.innerHTML = pills.join('');
  }
  function setStatus(meta) {
    if (!meta) return;
    renderRolePills(meta);
    $('of-statusbar').classList.remove('hidden');
    const pill = $('of-status-pill');
    pill.className = 'of-pill ' + (meta.status || '');
    pill.textContent = meta.status || '—';
    const spend = meta.spend || {};
    const spendStr = Object.keys(spend).length
      ? ' · 呼叫 ' + Object.entries(spend).map(([k, v]) => `${k}:${v}`).join(' ') : '';
    const stage = meta.phase ? (PHASE_LABEL[meta.phase] || meta.phase)
      : `輪 ${meta.rounds_completed || 0}`;
    $('of-status-meta').textContent =
      `${stage}${meta.close_reason ? ' · ' + meta.close_reason : ''}${spendStr}`;
    const running = meta.status === 'running';
    $('of-start').disabled = running;
    $('of-stop').classList.toggle('hidden', !running);
  }

  function roundSep(n) {
    const d = document.createElement('div');
    d.className = 'of-round-sep';
    d.innerHTML = `<span>Round ${n + 1}</span>`;
    $('of-board').appendChild(d);
  }

  function thinking(text) {
    let t = $('of-thinking-row');
    if (!text) { if (t) t.remove(); return; }
    if (!t) {
      t = document.createElement('div');
      t.id = 'of-thinking-row';
      t.className = 'of-thinking';
      $('of-board').appendChild(t);
    }
    t.textContent = '⋯ ' + text;
    $('of-board').appendChild(t); // keep at bottom
  }

  // Live elapsed ticker so a slow CLI turn (claude -p can take 1-3 min) reads as
  // alive, not frozen.
  let thinkTimer = null, thinkStart = 0, thinkLabel = '';
  function startThinking(label) {
    stopThinking();
    thinkLabel = label;
    thinkStart = Date.now();
    const tick = () => {
      const s = Math.floor((Date.now() - thinkStart) / 1000);
      const mmss = s >= 60 ? `${Math.floor(s / 60)}m${String(s % 60).padStart(2, '0')}s` : `${s}s`;
      thinking(`${thinkLabel}… ${mmss}`);
    };
    tick();
    thinkTimer = setInterval(tick, 1000);
  }
  function stopThinking() {
    if (thinkTimer) { clearInterval(thinkTimer); thinkTimer = null; }
    thinking(null);
  }

  function renderTurn(ev) {
    stopThinking();
    const card = document.createElement('div');
    card.className = 'of-card ' + (ev.role || '');
    const eng = ev.engine_used || ev.engine || '';
    const fb = ev.fell_back ? ` <span class="of-badge">↩ ${eng}</span>` : ` <span class="of-badge">${eng}</span>`;
    const doneBadge = ev.done ? '<span class="of-badge done">done</span>' : '';
    const concerns = (ev.concerns && ev.concerns.length)
      ? `<div class="of-concerns">⚠ ${ev.concerns.map(c => String(c)).join(' · ')}</div>` : '';
    card.innerHTML =
      `<div class="flex items-center justify-between">
         <div><span class="of-role ${ev.role}">${ev.name || ev.role}</span>${fb}</div>
         ${doneBadge}
       </div>
       <div class="of-summary">${(ev.summary || '').replace(/</g, '&lt;')}</div>
       <div class="of-detail">${md(ev.detail)}</div>
       ${concerns}`;
    $('of-board').appendChild(card);
  }

  // ── v2 pipeline renderers ─────────────────────────────────────────────
  const esc = (s) => String(s || '').replace(/</g, '&lt;');

  function phaseSep(title) {
    const d = document.createElement('div');
    d.className = 'of-round-sep';
    d.innerHTML = `<span>${esc(title)}</span>`;
    $('of-board').appendChild(d);
  }

  function renderDraft(ev) {
    const card = document.createElement('div');
    card.className = 'of-card ' + (ev.role || '');
    const failed = ev.ok === false ? ' <span class="of-badge" style="color:#f87171">失敗</span>' : '';
    const claims = (ev.claims && ev.claims.length)
      ? `<div class="of-concerns" style="color:var(--text-muted)">主張：${ev.claims.map(esc).join('｜')}</div>` : '';
    card.innerHTML =
      `<div><span class="of-role ${ev.role}">${esc(ev.name || ev.role)}</span>
         <span class="of-badge">${esc(ev.engine_used || ev.engine)}</span>${failed}</div>
       <div class="of-summary">${esc(ev.summary)}</div>
       <div class="of-detail">${md(ev.detail)}</div>
       ${claims}`;
    $('of-board').appendChild(card);
  }

  function renderResearch(ev) {
    const card = document.createElement('div');
    card.className = 'of-card researcher';
    const failed = ev.ok === false ? ' <span class="of-badge" style="color:#f87171">無事實可用</span>' : '';
    const facts = (ev.facts || []).map(f =>
      `<li>${esc(f.fact)} <span style="color:var(--text-muted)">（${esc(f.source)}）</span></li>`).join('');
    const gaps = (ev.gaps && ev.gaps.length)
      ? `<div class="of-concerns">缺口：${ev.gaps.map(esc).join('｜')}</div>` : '';
    card.innerHTML =
      `<div><span class="of-role researcher">${esc(ev.name || 'Researcher')}</span>
         <span class="of-badge">${esc(ev.engine_used || 'broker')}</span>${failed}</div>
       <div class="of-summary">${esc(ev.summary)}</div>
       <div class="of-detail"><ul>${facts}</ul></div>
       ${gaps}`;
    $('of-board').appendChild(card);
  }

  function renderAdjudication(ev) {
    const card = document.createElement('div');
    card.className = 'of-card';
    const cons = (ev.consensus && ev.consensus.length)
      ? `<div class="of-detail"><b>✅ 共識</b><ul>${ev.consensus.map(c => `<li>${esc(c)}</li>`).join('')}</ul></div>`
      : '<div class="of-detail">（無共識條目）</div>';
    const dis = (ev.disagreements || []).map(d =>
      `<div class="of-card" id="of-dis-${esc(d.id)}" style="margin:8px 0 0;border-left-color:#a855f7">
         <div class="of-summary">⚔ ${esc(d.id)} · ${esc(d.topic)}</div>
         <div class="of-detail">${Object.entries(d.positions || {}).map(([k, v]) =>
           `<div><span class="of-role ${k}">${k}</span>：${esc(v)}</div>`).join('')}
           <div style="margin-top:4px;color:var(--text-muted)">關鍵：${esc(d.crux)}</div>
         </div>
       </div>`).join('');
    card.innerHTML = `<div class="of-summary">分歧萃取 — 共識 ${ (ev.consensus || []).length } 條 · 分歧 ${(ev.disagreements || []).length} 點</div>${cons}${dis}`;
    $('of-board').appendChild(card);
  }

  const STANCE_ZH = { maintain: '維持', revise: '修正', concede: '讓步', no_reply: '無回應' };
  function renderRebuttal(ev) {
    const host = document.getElementById(`of-dis-${ev.dis_id}`) || $('of-board');
    const d = document.createElement('div');
    d.className = 'of-detail';
    d.style.cssText = 'margin-top:6px;padding-top:6px;border-top:1px dashed rgba(161,161,170,.25)';
    const evid = ev.evidence && ev.evidence !== '無' ? `｜證據：${esc(ev.evidence)}` : '';
    d.innerHTML = `<span class="of-role ${ev.role}">${esc(ev.name || ev.role)}</span>
      <span class="of-badge">${esc(STANCE_ZH[ev.stance] || ev.stance)}</span>
      ${esc(ev.position)}<div style="color:var(--text-muted)">${esc(ev.argument)}${evid}</div>`;
    host.appendChild(d);
  }

  function handleEvent(ev) {
    if (ev.round != null && ev.round !== lastRound &&
        (ev.type === 'turn_started' || ev.type === 'turn')) {
      lastRound = ev.round;
      roundSep(ev.round);
    }
    switch (ev.type) {
      // v2 pipeline events
      case 'phase':
        stopThinking();
        phaseSep(ev.title || ev.phase);
        startThinking(`${ev.title || ev.phase} 進行中`);
        break;
      case 'research': renderResearch(ev); break;
      case 'draft': renderDraft(ev); break;
      case 'adjudication': renderAdjudication(ev); break;
      case 'rebuttal': renderRebuttal(ev); break;
      case 'research_started': case 'draft_started': case 'rebuttal_started': break; // phase ticker covers these
      // legacy round-robin events (old runs replay correctly)
      case 'turn_started': startThinking(`${ev.name || ev.role}（${ev.engine}）思考中`); break;
      case 'turn': renderTurn(ev); break;
      case 'composing': startThinking('Lead 整理交付物中'); break;
      case 'deliverable':
        stopThinking();
        $('of-deliverable-wrap').classList.remove('hidden');
        $('of-deliverable').innerHTML = md(ev.markdown);
        break;
      case 'error':
        stopThinking();
        setErr(ev.message || 'error');
        break;
      case 'run_finished': stopThinking(); refreshFinal(); break;
    }
  }

  // ── streaming ─────────────────────────────────────────────────────────
  function resetBoard() {
    $('of-board').innerHTML = '';
    $('of-deliverable-wrap').classList.add('hidden');
    $('of-deliverable').innerHTML = '';
    lastRound = -1;
    setErr('');
  }

  function openStream(runId) {
    if (es) { es.close(); es = null; }
    currentRun = runId;
    const stream = new EventSource(`/api/office/run/${runId}/stream?token=${encodeURIComponent(token)}`);
    es = stream;
    stream.onmessage = (m) => {
      if (!m.data) return;
      try { handleEvent(JSON.parse(m.data)); } catch (e) {}
    };
    stream.addEventListener('end', () => { stream.close(); refreshFinal(); });
    stream.onerror = () => { /* EventSource auto-retries; final state via refreshFinal */ };
  }

  async function refreshFinal() {
    if (!currentRun) return;
    try {
      const r = await fetch(`/api/office/run/${currentRun}`, { headers: { 'X-Office-Token': token } });
      if (!r.ok) return;
      const full = await r.json();
      setStatus(full.meta);
      if (full.deliverable) {
        $('of-deliverable-wrap').classList.remove('hidden');
        $('of-deliverable').innerHTML = md(full.deliverable);
      }
    } catch (e) {}
  }

  // Render a finished/past run from its full snapshot.
  function renderSnapshot(full) {
    resetBoard();
    (full.events || []).forEach(handleEvent);
    setStatus(full.meta);
    if (full.deliverable) {
      $('of-deliverable-wrap').classList.remove('hidden');
      $('of-deliverable').innerHTML = md(full.deliverable);
    }
  }

  // ── actions ───────────────────────────────────────────────────────────
  $('of-start').addEventListener('click', async () => {
    const task = $('of-task').value.trim();
    if (!task) { setErr('請先輸入任務'); return; }
    setErr('');
    resetBoard();
    try {
      const r = await fetch('/api/office/run', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-Office-Token': token },
        body: JSON.stringify({ task }),
      });
      const meta = await r.json();
      if (!r.ok) { setErr(meta.error || ('啟動失敗 ' + r.status)); return; }
      setStatus(meta);
      openStream(meta.run_id);
      loadRuns();
    } catch (e) { setErr('伺服器未連線'); }
  });

  $('of-stop').addEventListener('click', async () => {
    if (!currentRun) return;
    try {
      await fetch(`/api/office/run/${currentRun}/stop`, {
        method: 'POST', headers: { 'X-Office-Token': token },
      });
    } catch (e) {}
  });

  $('of-run-select').addEventListener('change', async (e) => {
    const id = e.target.value;
    if (!id) { resetBoard(); $('of-statusbar').classList.add('hidden'); currentRun = null; if (es) es.close(); return; }
    try {
      const r = await fetch(`/api/office/run/${id}`, { headers: { 'X-Office-Token': token } });
      const full = await r.json();
      if (!r.ok) { setErr(full.error || 'load failed'); return; }
      currentRun = id;
      renderSnapshot(full);
      if (full.meta && full.meta.status === 'running') openStream(id);
    } catch (err) { setErr('load failed'); }
  });

  async function loadRuns() {
    try {
      const r = await fetch('/api/office/runs', { headers: { 'X-Office-Token': token } });
      if (!r.ok) return;
      const { runs, active } = await r.json();
      const sel = $('of-run-select');
      const keep = sel.value;
      sel.innerHTML = '<option value="">— 新任務 —</option>' +
        runs.map(rn => `<option value="${rn.run_id}">${(rn.task || '').slice(0, 40)} · ${rn.status}</option>`).join('');
      sel.value = keep;
      // Auto-attach to an in-flight run on load.
      if (active && !currentRun) {
        sel.value = active;
        sel.dispatchEvent(new Event('change'));
      }
    } catch (e) {}
  }

  // ── boot ──────────────────────────────────────────────────────────────
  (async () => {
    try {
      const r = await fetch('/api/office/token');
      if (!r.ok) { setErr('無法取得 token (' + r.status + ')'); return; }
      token = (await r.json()).token;
    } catch (e) { setErr('伺服器未連線'); return; }
    loadRuns();
  })();
});
