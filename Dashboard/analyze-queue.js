/**
 * analyze-queue.js — Global per-ticker invest-protocol queue client.
 *
 * Exposes:
 *   AnalyzeQueue.enqueue(ticker)           POST /api/analyze-queue
 *   AnalyzeQueue.remove(ticker)            DELETE /api/analyze-queue/:ticker
 *   AnalyzeQueue.poll()                    GET → updates _state + calls subscribers
 *   AnalyzeQueue.subscribe(fn)             fn(state) whenever state changes
 *   AnalyzeQueue.renderWidget(container)   mount the full widget (re-renders on state change)
 *   AnalyzeQueue.startPolling(intervalMs)  begin periodic polling (default 4000ms)
 *
 * State shape:
 *   { active: { ticker, elapsed_sec, started_at } | null,
 *     queue:  [{ ticker, risk_tolerance, enqueued_at }],
 *     recent: [{ ticker, status, ended_at, error? }] }
 */
(function () {
  'use strict';

  const _subs = new Set();
  let _state = { active: null, queue: [], recent: [] };
  let _pollTimer = null;

  function _notify() { _subs.forEach(fn => { try { fn(_state); } catch (_) {} }); }

  function _toast(msg, kind = 'info') {
    if (window.UI?.showToast) window.UI.showToast(msg, kind);
  }

  function _t() {
    return (window.i18n?.[window.UI?.currentLang]?.analyze_queue) || {};
  }

  async function poll() {
    try {
      const res = await fetch('/api/analyze-queue');
      if (!res.ok) return _state;
      const next = await res.json();
      // v1.61: queue is now unified across all protocols. This widget cares
      // about invest only (ticker analyses on index.html). Filter the rest out.
      const isInvestEntry = q => q && (q.name === 'invest' || !q.name) && (q.ticker || (q.params || {}).ticker);
      const investActive = next.active && (next.active.name === 'invest' || !next.active.name) && next.active.ticker;
      const investQueue  = (Array.isArray(next.queue) ? next.queue : []).filter(isInvestEntry).map(q => ({
        ...q, ticker: q.ticker || (q.params || {}).ticker,
      }));
      const investRecent = (Array.isArray(next.recent) ? next.recent : []).filter(r => r && r.ticker);
      _state = {
        active: investActive ? next.active : null,
        queue:  investQueue,
        recent: investRecent,
      };
      _notify();
      return _state;
    } catch (_) { return _state; }
  }

  async function enqueue(ticker) {
    if (!ticker) return { ok: false, reason: 'missing_ticker' };
    const tk = String(ticker).toUpperCase().trim();
    const rt = window.UI?.riskTolerance || 'MEDIUM';
    const tr = _t();
    try {
      const res = await fetch('/api/analyze-queue', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ticker: tk, risk_tolerance: rt }),
      });
      const body = await res.json().catch(() => ({}));
      if (res.status === 202 && body.queued) {
        const msg = (tr.toast_enqueued || '已加入佇列：{tk}（第 {pos} 位）')
            .replace('{tk}', tk)
            .replace('{pos}', body.position);
        _toast(msg, 'success');
        poll();
        return { ok: true, position: body.position };
      }
      if (res.status === 409 && body.reason) {
        const msg = body.reason === 'duplicate_active'
          ? (tr.toast_dup_active || `${tk} 正在分析中，忽略重複請求`)
          : (tr.toast_dup_pending || `${tk} 已在佇列中，忽略重複請求`);
        _toast(msg.replace('{tk}', tk), 'warning');
        return { ok: false, reason: body.reason };
      }
      _toast((tr.toast_enqueue_fail || `加入佇列失敗：{err}`).replace('{err}', body.error || res.status), 'error');
      return { ok: false, reason: body.error || `HTTP ${res.status}` };
    } catch (e) {
      _toast(`${tr.toast_enqueue_fail || '加入佇列失敗'}：${e.message}`, 'error');
      return { ok: false, reason: e.message };
    }
  }

  async function remove(ticker) {
    const tk = String(ticker).toUpperCase().trim();
    const tr = _t();
    try {
      const res = await fetch(`/api/analyze-queue/${encodeURIComponent(tk)}`, { method: 'DELETE' });
      if (res.ok) {
        _toast((tr.toast_removed || `已從佇列移除：${tk}`).replace('{tk}', tk), 'success');
        poll();
        return true;
      }
      _toast(tr.toast_remove_fail || '移除失敗', 'error');
      return false;
    } catch (e) {
      _toast(`${tr.toast_remove_fail || '移除失敗'}：${e.message}`, 'error');
      return false;
    }
  }

  function subscribe(fn) {
    _subs.add(fn);
    // Seed subscriber with current state immediately
    try { fn(_state); } catch (_) {}
    return () => _subs.delete(fn);
  }

  function _fmtElapsed(sec) {
    sec = Math.max(0, Math.floor(sec || 0));
    return `${String(Math.floor(sec / 60)).padStart(2,'0')}:${String(sec % 60).padStart(2,'0')}`;
  }

  function _renderInto(el) {
    const tr = _t();
    const s = _state;
    const hasAny = (s.active && s.active.ticker) || s.queue.length || s.recent.length;

    // Completely idle → single dim one-liner, no card
    if (!hasAny) {
      el.innerHTML = `
        <div class="flex items-center gap-1.5 text-[10px] text-zinc-500 font-mono pt-1 border-t border-zinc-200/40 dark:border-zinc-800/60">
          <span class="inline-block w-1.5 h-1.5 rounded-full bg-zinc-600 shrink-0"></span>
          <span>${tr.idle || '佇列閒置中'}</span>
        </div>`;
      return;
    }

    // Active line (or a neutral pending-only line when no active)
    let activeLine = '';
    if (s.active && s.active.ticker) {
      activeLine = `
        <div class="flex items-center gap-2 text-[11px]">
          <span class="inline-block w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse shrink-0"></span>
          <span class="font-black text-emerald-400">${tr.now_analyzing || '分析中'}</span>
          <span class="font-black tracking-tight" style="color: var(--text-card-title)">${s.active.ticker}</span>
          <span class="ml-auto font-mono text-emerald-300">${_fmtElapsed(s.active.elapsed_sec)}</span>
        </div>`;
    }

    // Pending queue pills — tight row
    let queueLine = '';
    if (s.queue.length) {
      const pills = s.queue.map(q => `
        <span class="inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] font-bold bg-zinc-800/60 border border-zinc-700/50" style="color: var(--text-main)">
          ${q.ticker}
          <button data-aq-remove="${q.ticker}" class="text-zinc-500 hover:text-red-400 leading-none" title="${tr.remove_tooltip || '從佇列移除'}">✕</button>
        </span>`).join('');
      queueLine = `
        <div class="flex items-center gap-1.5 flex-wrap text-[10px]">
          <span class="font-black uppercase tracking-wider text-zinc-500">${tr.pending || '待分析'}（${s.queue.length}）</span>
          ${pills}
        </div>`;
    }

    // Recent history — one compact inline line
    let recentLine = '';
    if (s.recent.length) {
      const items = s.recent.slice(0, 4).map(r => {
        const color = r.status === 'done' ? '#22c55e' : r.status === 'error' ? '#ef4444' : '#71717a';
        const icon  = r.status === 'done' ? '✓' : r.status === 'error' ? '✗' : '○';
        return `<span class="font-mono" style="color:${color}">${icon}${r.ticker}</span>`;
      }).join(' · ');
      recentLine = `
        <div class="flex items-center gap-1.5 text-[10px] text-zinc-500">
          <span class="font-black uppercase tracking-wider">${tr.recent || '最近'}</span>
          ${items}
        </div>`;
    }

    el.innerHTML = `
      <div class="flex flex-col gap-1.5 pt-2 border-t border-zinc-200/40 dark:border-zinc-800/60">
        ${activeLine}
        ${queueLine}
        ${recentLine}
      </div>`;

    el.querySelectorAll('[data-aq-remove]').forEach(btn => {
      btn.addEventListener('click', (ev) => {
        ev.stopPropagation();
        remove(btn.dataset.aqRemove);
      });
    });
  }

  function renderWidget(container) {
    const el = typeof container === 'string' ? document.querySelector(container) : container;
    if (!el) return;
    subscribe(() => _renderInto(el));
    _renderInto(el);
  }

  function startPolling(intervalMs = 4000) {
    if (_pollTimer) clearInterval(_pollTimer);
    poll();
    _pollTimer = setInterval(poll, intervalMs);
  }

  window.AnalyzeQueue = { enqueue, remove, poll, subscribe, renderWidget, startPolling,
                         get state() { return _state; } };
  // Auto-start polling on load
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => startPolling());
  } else {
    startPolling();
  }
})();
