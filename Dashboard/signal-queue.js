/**
 * signal-queue.js — Shared client for the cross-page candidate strip.
 *
 * One page's conclusions arrive here as another page's candidates: a debate
 * that closed BULLISH on FN shows up on the earnings page with a link back to
 * the debate and, when the quarter is not already analysed, a button that
 * pushes the ticker into the existing protocol queue.
 *
 * Mount with:
 *   SignalQueue.mount(document.getElementById('sq-mount'), { lane: 'earnings' });
 *
 * Discipline: this is a delivery layer. It starts an independent analysis and
 * nothing more — it never carries a verdict, a target or a position size.
 */
(function () {
  'use strict';

  const POLL_MS = 60000;
  const DEFAULT_DAYS = 3;

  function esc(s) {
    return String(s == null ? '' : s).replace(/[&<>"']/g, c => (
      { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]
    ));
  }

  function zh() { return (window.UI?.currentLang || 'zh') === 'zh'; }

  function toast(msg, kind) {
    if (window.UI?.showToast) window.UI.showToast(msg, kind || 'info');
  }

  // ── Copy ───────────────────────────────────────────────────────────
  const LANE_TITLE = {
    earnings: ['辯論推薦的財報候選', 'Debate-sourced earnings candidates'],
    invest:   ['辯論推薦的深度分析候選', 'Debate-sourced analysis candidates'],
    momentum: ['辯論點名的動能標的', 'Tickers the debates flagged'],
  };

  // Each state names the action, because "why is this button disabled" is the
  // question the card exists to answer.
  const ELIGIBILITY = {
    pre_earnings_window: {
      zh: t => `📋 財報前瞻（${t.days_until}天後公布）`,
      en: t => `📋 Preview (reports in ${t.days_until}d)`,
      protocol: 'earnings_preview',
      note: ['財報將公布，先跑前瞻而非分析上一季', 'Earnings imminent — preview, not last quarter'],
    },
    cache_stale: {
      zh: () => '🔄 重跑財報分析', en: () => '🔄 Re-run analysis',
      protocol: 'earnings',
      note: ['已有新一季財報，快取過期', 'A newer quarter has reported'],
    },
    no_cache: {
      zh: () => '📊 執行財報分析', en: () => '📊 Run analysis',
      protocol: 'earnings',
      note: ['尚未分析過', 'Never analysed'],
    },
    cache_current: {
      zh: () => '已是最新', en: () => 'Up to date',
      protocol: null,
      note: ['最新一季已分析過，不重跑', 'Latest quarter already analysed'],
    },
    unknown: { zh: () => '—', en: () => '—', protocol: null, note: ['', ''] },
  };

  function eligibilityFor(candidate) {
    const state = candidate.eligibility?.state || 'unknown';
    return ELIGIBILITY[state] || ELIGIBILITY.unknown;
  }

  // ── Rendering ──────────────────────────────────────────────────────
  function renderEvidence(candidate) {
    return (candidate.evidence || []).map(ev => {
      const title = zh() && ev.headline_zh ? ev.headline_zh : ev.headline;
      const arrow = ev.direction === 'bullish' ? '▲' : '▼';
      const cls = ev.direction === 'bullish' ? 'sq-up' : 'sq-down';
      return `<li>
        <a class="sq-ev" href="break-news.html?news_id=${encodeURIComponent(ev.artifact_id)}">
          <span class="${cls}">${arrow}</span> ${esc(title)}
        </a>
        <span class="sq-ev-meta">${esc(ev.source_name)}</span>
      </li>`;
    }).join('');
  }

  function renderDelivered(candidate) {
    const done = (candidate.consumed_by || [])[0];
    // The ledger is authoritative. `consumed_by` is only a backlink: an older
    // source stays stamped after new evidence arrives and must not hide the new
    // revision's action button.
    if (candidate.delivery?.status === 'consumed') {
      const path = candidate.delivery?.report_path || done?.report_path;
      const label = zh() ? '已產出分析' : 'Analysis produced';
      return path
        ? `<a class="sq-done" href="/${esc(path)}">${label} →</a>`
        : `<span class="sq-done">${label}</span>`;
    }
    if (candidate.delivery?.status === 'queued') {
      return `<span class="sq-pending">${zh() ? '已排入佇列…' : 'Queued…'}</span>`;
    }
    if (candidate.delivery?.status === 'failed') {
      return `<span class="sq-failed" title="${esc(candidate.delivery.error || '')}">${
        zh() ? '上次執行失敗' : 'Last run failed'}</span>`;
    }
    return '';
  }

  function renderAction(candidate) {
    const delivered = renderDelivered(candidate);
    if (delivered) return delivered;
    const retryNote = candidate.delivery?.previous_status === 'failed'
      ? `<span class="sq-failed" title="${esc(candidate.delivery.error || '')}">${
          zh() ? '上次執行失敗，可重試' : 'Last run failed; retry available'}</span>`
      : '';

    if (candidate.lane === 'momentum') {
      return `<a class="sq-btn sq-btn-ghost" href="momentum.html?ticker=${
        encodeURIComponent(candidate.ticker)}">${zh() ? '在動能頁查看' : 'View in screener'}</a>`;
    }
    if (candidate.lane === 'invest') {
      return `${retryNote}<button class="sq-btn" data-act="accept" data-protocol="invest">${
        zh() ? '🔬 加入深度分析' : '🔬 Analyse'}</button>`;
    }

    const rule = eligibilityFor(candidate);
    const label = zh() ? rule.zh(candidate.eligibility || {}) : rule.en(candidate.eligibility || {});
    if (!rule.protocol) {
      const report = candidate.eligibility?.report_path;
      const link = report
        ? `<a class="sq-btn sq-btn-ghost" href="/${esc(report)}">${zh() ? '開啟報告' : 'Open report'} →</a>`
        // No report on disk but the cache is current: send them to the detail
        // view rather than re-running an analysis we already have.
        : `<a class="sq-btn sq-btn-ghost" href="earnings-detail.html?ticker=${
            encodeURIComponent(candidate.ticker)}">${zh() ? '查看財報詳情' : 'Earnings detail'} →</a>`;
      return `${retryNote}<span class="sq-btn sq-btn-off" title="${esc((zh() ? rule.note[0] : rule.note[1]))}">${
        esc(label)}</span>${link}`;
    }
    return `${retryNote}<button class="sq-btn" data-act="accept" data-protocol="${rule.protocol}">${
      esc(label)}</button>`;
  }

  function renderCard(candidate) {
    const up = candidate.direction === 'bullish';
    const rule = candidate.lane === 'earnings' ? eligibilityFor(candidate) : null;
    const note = rule ? (zh() ? rule.note[0] : rule.note[1]) : '';
    const conflict = candidate.conflict
      ? `<span class="sq-flag" title="${esc(zh()
          ? '各場辯論結論不一致，這是分歧訊號而非買賣訊號'
          : 'Debates disagreed — a divergence signal, not a trade signal')}">${
          zh() ? '多空分歧' : 'split'}</span>`
      : '';

    return `<article class="sq-card ${up ? 'sq-card-up' : 'sq-card-down'}"
        data-id="${esc(candidate.candidate_id)}" data-rev="${esc(candidate.revision)}">
      <header class="sq-head">
        <span class="sq-ticker">${esc(candidate.ticker)}</span>
        <span class="sq-dir ${up ? 'sq-up' : 'sq-down'}">${up
          ? (zh() ? '看多' : 'bullish') : (zh() ? '看空' : 'bearish')}</span>
        ${conflict}
        <span class="sq-score" title="${esc(zh()
          ? `${candidate.hits} 場辯論（原始提及 ${candidate.raw_mentions}）· 一致度 ${candidate.agreement}`
          : `${candidate.hits} debates (${candidate.raw_mentions} mentions) · agreement ${candidate.agreement}`)}"
          >${candidate.score}</span>
        <button class="sq-dismiss" data-act="dismiss" title="${
          zh() ? '忽略此候選' : 'Dismiss'}">×</button>
      </header>
      ${note ? `<p class="sq-note">${esc(note)}</p>` : ''}
      <ul class="sq-evidence">${renderEvidence(candidate)}</ul>
      <footer class="sq-foot">${renderAction(candidate)}</footer>
    </article>`;
  }

  function renderEmpty(data, lane) {
    // Distinguish "filtered to nothing" from "broken": the dropped counters are
    // the only thing that tells those apart at a glance.
    const dropped = data?.dropped || {};
    const total = Object.values(dropped).reduce((a, b) => a + b, 0);
    return `<p class="sq-empty">${zh()
      ? `目前沒有候選（近 ${data?.window_days ?? DEFAULT_DAYS} 天 ${data?.usable_events ?? 0} 場辯論，${total} 則未達門檻）`
      : `No candidates (${data?.usable_events ?? 0} debates in ${data?.window_days ?? DEFAULT_DAYS}d, ${total} filtered)`}</p>`;
  }

  // ── Actions ────────────────────────────────────────────────────────
  async function postAction(candidateId, revision, action, protocol) {
    const res = await fetch('/api/signal-queue/action', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ candidate_id: candidateId, revision, action, protocol }),
    });
    let body = {};
    try { body = await res.json(); } catch (_) {}
    return { res, body };
  }

  // ── Mount ──────────────────────────────────────────────────────────
  function mount(host, opts) {
    if (!host) return null;
    const lane = (opts && opts.lane) || 'earnings';
    const days = (opts && opts.days) || DEFAULT_DAYS;
    const limit = (opts && opts.limit) || 8;
    let latest = null;
    let timer = null;

    function render() {
      const items = latest?.lanes?.[lane] || [];
      const title = LANE_TITLE[lane] || ['候選', 'Candidates'];
      host.innerHTML = `<section class="sq-wrap">
        <h3 class="sq-title">
          ${zh() ? title[0] : title[1]}
          <span class="sq-count">${items.length}</span>
          <a class="sq-src" href="break-news.html">${zh() ? '來源：即時辯論' : 'from live debates'} →</a>
        </h3>
        <div class="sq-list">${
          items.length ? items.map(renderCard).join('') : renderEmpty(latest, lane)}</div>
      </section>`;
    }

    async function load() {
      try {
        const res = await fetch(
          `/api/signal-queue?lane=${encodeURIComponent(lane)}&days=${days}&limit=${limit}`);
        if (!res.ok) { host.innerHTML = ''; return; }
        latest = await res.json();
        render();
      } catch (_) {
        // A signal strip that cannot load should vanish, not shout: it is
        // supplementary to every page it appears on.
        host.innerHTML = '';
      }
    }

    host.addEventListener('click', async (e) => {
      const btn = e.target.closest('[data-act]');
      if (!btn) return;
      const card = btn.closest('.sq-card');
      if (!card) return;
      const id = card.dataset.id;
      const rev = card.dataset.rev;
      const action = btn.dataset.act;

      btn.disabled = true;
      const { res, body } = await postAction(id, rev, action, btn.dataset.protocol);
      if (res.status === 409 && body.error === 'stale revision') {
        toast(zh() ? '這則候選已有新證據，正在重新整理' : 'New evidence — refreshing', 'warn');
        return load();
      }
      if (res.status === 409) {
        toast(zh() ? `${card.dataset.id} 已在佇列中` : 'Already queued', 'warn');
        btn.disabled = false;
        return;
      }
      if (!res.ok) {
        toast(zh() ? `失敗：${body.error || res.status}` : `Failed: ${body.error || res.status}`, 'error');
        btn.disabled = false;
        return;
      }
      if (action === 'accept') {
        const pos = body.queue?.position;
        toast(zh() ? `已排入分析${pos ? `（第 ${pos} 位）` : ''}` : `Queued${pos ? ` (#${pos})` : ''}`, 'info');
      }
      load();
    });

    load();
    timer = setInterval(load, POLL_MS);

    // `UI._onLangChange` is a single callback slot the host page already owns,
    // so chain onto it rather than claiming it — overwriting would silently
    // kill that page's own re-translation.
    const priorLangHook = window.UI?._onLangChange;
    if (window.UI) {
      window.UI._onLangChange = () => {
        if (priorLangHook) { try { priorLangHook(); } catch (_) {} }
        render();
      };
    }

    return { reload: load, destroy: () => clearInterval(timer) };
  }

  window.SignalQueue = { mount };
})();
