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
    invest:   ['新聞推薦的深度分析候選', 'News-sourced analysis candidates'],
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
  // The card face carries no prose: strength, direction and provenance are all
  // drawn. Every sentence lives in the peek popover, opened by hover, focus or
  // tap on the source glyphs.
  const DIR = {
    bullish: { cls: 'up',   glyph: '▲', zh: '看多',   en: 'bullish' },
    bearish: { cls: 'down', glyph: '▼', zh: '看空',   en: 'bearish' },
    neutral: { cls: 'flat', glyph: '◆', zh: '待判讀', en: 'unread' },
  };
  const CLAIM_STATUS = {
    supported: ['證據支持', 'Supported'],
    contested: ['仍有爭議', 'Contested'],
  };
  const CLAIM_KIND = { fact: ['事實', 'Fact'], inference: ['推論', 'Inference'], question: ['待回答', 'Open question'] };

  const dirOf = c => DIR[c.direction] || DIR.neutral;
  const pick = pair => (zh() ? pair[0] : pair[1]);

  function safeUrl(value) {
    try {
      const u = new URL(value);
      return ['https:', 'http:'].includes(u.protocol) ? u.href : '';
    } catch (_) { return ''; }
  }

  // Strength meter. Fill length is the score; a split candidate is drawn as the
  // bull/bear share of its debates so the disagreement is visible, not a label.
  function renderMeter(candidate) {
    const pct = Math.max(4, Math.min(100, Number(candidate.score) || 0));
    const total = (candidate.bullish_hits || 0) + (candidate.bearish_hits || 0);
    const fill = candidate.conflict && total
      ? `<span class="sq-fill sq-fill-split" style="width:${pct}%;--bull:${
          Math.round(100 * candidate.bullish_hits / total)}%"></span>`
      : `<span class="sq-fill sq-fill-${dirOf(candidate).cls}" style="width:${pct}%"></span>`;
    return `<span class="sq-meter" role="meter" aria-valuemin="0" aria-valuemax="100"
        aria-valuenow="${esc(candidate.score)}" aria-label="${zh() ? '訊號強度' : 'Signal strength'}">${fill}</span>`;
  }

  // One glyph per piece of provenance: ▲/▼ for a debate, ◆ for a research
  // claim (solid = supported, hollow = contested).
  function renderGlyphs(candidate) {
    const debates = (candidate.evidence || []).map(ev =>
      `<span class="sq-g sq-g-${ev.direction === 'bullish' ? 'up' : 'down'}">${
        ev.direction === 'bullish' ? '▲' : '▼'}</span>`);
    const extra = Math.max(0, (candidate.hits || 0) - debates.length);
    if (extra) debates.push(`<span class="sq-g-more">+${extra}</span>`);
    const claims = (candidate.research?.claims || []).map(cl =>
      `<span class="sq-g sq-g-claim sq-g-${cl.status}">◆</span>`);
    return [...debates, ...claims].join('');
  }

  function renderPeek(candidate) {
    const debates = (candidate.evidence || []).map(ev => {
      const title = zh() && ev.headline_zh ? ev.headline_zh : ev.headline;
      const d = ev.direction === 'bullish' ? DIR.bullish : DIR.bearish;
      return `<li class="sq-pop-row">
        <span class="sq-g sq-g-${d.cls}" aria-label="${pick([d.zh, d.en])}">${d.glyph}</span>
        <a class="sq-pop-link" href="break-news.html?news_id=${encodeURIComponent(ev.artifact_id)}">${esc(title)}</a>
        <span class="sq-pop-src">${esc(ev.source_name)}</span>
      </li>`;
    }).join('');

    const claims = (candidate.research?.claims || []).map(cl => {
      const url = safeUrl(cl.url);
      const kind = CLAIM_KIND[cl.kind] ? pick(CLAIM_KIND[cl.kind]) : '';
      return `<li class="sq-pop-row">
        <span class="sq-g sq-g-claim sq-g-${esc(cl.status)}" title="${esc(pick(CLAIM_STATUS[cl.status] || ['', '']))}">◆</span>
        <div class="sq-pop-claim">
          <p>${esc(cl.text)}</p>
          <details>
            <summary>${esc(kind)} · ${esc(pick(CLAIM_STATUS[cl.status] || ['', '']))}</summary>
            ${cl.quote ? `<blockquote>${esc(cl.quote)}</blockquote>` : ''}
            ${cl.falsifier ? `<p class="sq-pop-falsifier"><b>${zh() ? '若此成立則推翻' : 'Falsified if'}</b>${esc(cl.falsifier)}</p>` : ''}
            ${url ? `<a class="sq-pop-link" href="${esc(url)}" target="_blank" rel="noopener noreferrer">${
              esc(cl.source_name || (zh() ? '原始來源' : 'Source'))} ↗</a>` : ''}
          </details>
        </div>
      </li>`;
    }).join('');

    const flags = [
      candidate.conflict && (zh() ? '各場辯論結論不一致：這是分歧訊號，不是買賣訊號。'
                                  : 'Debates disagree: a divergence signal, not a trade signal.'),
      candidate.research_disagrees && (zh() ? '查證主張的方向與辯論結論相反。'
                                            : 'Research points the other way from the debates.'),
      candidate.direction === 'neutral' && (zh() ? '查證屬實但方向未定，交給深度分析判讀。'
                                                 : 'Verified, direction undecided: the analysis decides.'),
    ].filter(Boolean).map(t => `<p class="sq-pop-flag">${esc(t)}</p>`).join('');

    return `${flags}
      ${debates ? `<h4>${zh() ? '辯論' : 'Debates'}<span>${candidate.hits || 0}</span></h4><ul>${debates}</ul>` : ''}
      ${claims ? `<h4>${zh() ? '查證' : 'Research'}<span>${candidate.research.claims.length}</span></h4><ul>${claims}</ul>` : ''}`;
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
      ? `<span class="sq-failed sq-retry" title="${esc(
          (zh() ? '上次執行失敗，可重試' : 'Last run failed; retry available')
          + (candidate.delivery.error ? `\n${candidate.delivery.error}` : ''))}"
          aria-label="${zh() ? '上次執行失敗' : 'Last run failed'}">!</span>`
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
    // The eligibility note used to be a line of grey prose on the card; it is
    // the button's tooltip now.
    return `${retryNote}<button class="sq-btn" data-act="accept" data-protocol="${rule.protocol}"
        title="${esc(zh() ? rule.note[0] : rule.note[1])}">${esc(label)}</button>`;
  }

  function renderCard(candidate) {
    const d = dirOf(candidate);
    const popId = `sq-pop-${String(candidate.candidate_id).replace(/[^A-Za-z0-9_-]/g, '_')}`;
    const scoreTip = zh()
      ? `${candidate.hits || 0} 場辯論 · ${candidate.research?.claims?.length || 0} 則查證 · 一致度 ${candidate.agreement}`
      : `${candidate.hits || 0} debates · ${candidate.research?.claims?.length || 0} claims · agreement ${candidate.agreement}`;
    const split = candidate.conflict || candidate.research_disagrees;

    return `<article class="sq-card sq-card-${d.cls}${split ? ' sq-card-split' : ''}"
        data-id="${esc(candidate.candidate_id)}" data-rev="${esc(candidate.revision)}">
      <div class="sq-head">
        <span class="sq-ticker">${esc(candidate.ticker)}</span>
        <span class="sq-dir sq-${d.cls}"><span aria-hidden="true">${d.glyph}</span> ${pick([d.zh, d.en])}</span>
        ${split ? `<span class="sq-split" title="${zh() ? '多空分歧' : 'Split'}" aria-label="${zh() ? '多空分歧' : 'Split'}">⇅</span>` : ''}
        <span class="sq-score" title="${esc(scoreTip)}">${esc(Math.round(candidate.score))}</span>
        <button class="sq-dismiss" data-act="dismiss" title="${
          zh() ? '忽略此候選' : 'Dismiss'}" aria-label="${zh() ? '忽略' : 'Dismiss'} ${esc(candidate.ticker)}">×</button>
      </div>
      ${renderMeter(candidate)}
      <div class="sq-foot">
        <span class="sq-peek-wrap">
          <button type="button" class="sq-peek" data-peek aria-expanded="false" aria-controls="${popId}"
              aria-label="${zh() ? '顯示依據' : 'Show sources'}">${renderGlyphs(candidate)}</button>
          <div class="sq-pop" id="${popId}" role="dialog" aria-label="${esc(candidate.ticker)} ${
            zh() ? '依據' : 'sources'}">${renderPeek(candidate)}</div>
        </span>
        <span class="sq-act">${renderAction(candidate)}</span>
      </div>
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
    // A pinned (tapped) popover survives the 60s poll re-render.
    let pinned = null;

    function legend(items) {
      const hasResearch = items.some(c => c.research?.claims?.length);
      return `<span class="sq-legend" aria-hidden="true">
        <span><span class="sq-g sq-g-up">▲</span><span class="sq-g sq-g-down">▼</span>${zh() ? '辯論' : 'debate'}</span>
        ${hasResearch ? `<span><span class="sq-g sq-g-claim sq-g-supported">◆</span>${zh() ? '查證' : 'verified'}</span>` : ''}
      </span>`;
    }

    function render() {
      const items = latest?.lanes?.[lane] || [];
      const title = LANE_TITLE[lane] || ['候選', 'Candidates'];
      host.innerHTML = `<section class="sq-wrap">
        <h3 class="sq-title">
          ${zh() ? title[0] : title[1]}
          <span class="sq-count">${items.length}</span>
          ${items.length ? legend(items) : ''}
          <a class="sq-src" href="break-news.html">${zh() ? '即時辯論' : 'Live debates'} →</a>
        </h3>
        <div class="sq-list">${
          items.length ? items.map(renderCard).join('') : renderEmpty(latest, lane)}</div>
      </section>`;
      if (pinned) {
        const card = [...host.querySelectorAll('.sq-card')].find(c => c.dataset.id === pinned);
        if (card) setOpen(card, true); else pinned = null;
      }
    }

    // Flip the popover to the card's right edge when it would leave the viewport.
    function place(card) {
      const pop = card.querySelector('.sq-pop');
      if (!pop) return;
      pop.classList.remove('sq-pop-end');
      const left = card.getBoundingClientRect().left;
      if (left + Math.min(380, window.innerWidth - 32) > window.innerWidth - 16) {
        pop.classList.add('sq-pop-end');
      }
    }

    function setOpen(card, open) {
      const btn = card.querySelector('[data-peek]');
      card.classList.toggle('sq-open', open);
      if (btn) btn.setAttribute('aria-expanded', String(open));
      if (open) place(card);
    }

    function closeAll(except) {
      host.querySelectorAll('.sq-card.sq-open').forEach(c => { if (c !== except) setOpen(c, false); });
    }

    host.addEventListener('pointerover', e => {
      const card = e.target.closest('.sq-peek-wrap')?.closest('.sq-card');
      if (card) place(card);
    });
    host.addEventListener('focusin', e => {
      const card = e.target.closest('.sq-peek-wrap')?.closest('.sq-card');
      if (card) place(card);
    });
    document.addEventListener('click', e => {
      if (!pinned || host.contains(e.target) && e.target.closest('.sq-peek-wrap')) return;
      pinned = null;
      closeAll();
    });
    document.addEventListener('keydown', e => {
      if (e.key !== 'Escape' || !host.querySelector('.sq-open')) return;
      const card = host.querySelector('.sq-open');
      pinned = null;
      closeAll();
      card?.querySelector('[data-peek]')?.focus();
    });

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
      const peek = e.target.closest('[data-peek]');
      if (peek) {
        const card = peek.closest('.sq-card');
        const open = !card.classList.contains('sq-open');
        closeAll(card);
        setOpen(card, open);
        pinned = open ? card.dataset.id : null;
        return;
      }
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
