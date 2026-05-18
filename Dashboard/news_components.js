/**
 * news_components.js — shared primitives for news.html + break-news.html.
 * Pure functions returning HTML strings; no DOM ownership, no global state.
 * Exposed as window.NewsComponents.
 */
(function (global) {
  'use strict';

  function currentLang() {
    return (global.UI && global.UI.currentLang) || 'zh';
  }

  // Resolve a label that can be either a plain string, a {zh, en} dict,
  // or an enum key looked up in `dict` keyed by current language.
  function pickLabel(maybeDictOrString, fallback) {
    if (maybeDictOrString == null) return fallback || '';
    if (typeof maybeDictOrString === 'string') return maybeDictOrString;
    if (typeof maybeDictOrString === 'object') {
      const lang = currentLang();
      return maybeDictOrString[lang] || maybeDictOrString.en || maybeDictOrString.zh || fallback || '';
    }
    return String(maybeDictOrString);
  }

  // Enum tables — render-time lookup keyed by current language.
  const STATE_LABELS = {
    pending_debate: { zh: '待辯論',     en: 'queued',     color: '#a1a1aa' },
    debating:       { zh: '🤖 辯論中',   en: '🤖 debating', color: '#3b82f6' },
    closed:         { zh: '✓ 辯論結束', en: '✓ finished', color: '#22c55e' },
    partial_closed: { zh: '◐ 部分結束', en: '◐ partial',  color: '#eab308' },
    failed:         { zh: '✕ 失敗',     en: '✕ failed',   color: '#ef4444' },
    gated_cost:     { zh: '預算上限',   en: 'gated',      color: '#71717a' },
  };
  const VERDICT_LABELS = {
    BULLISH: { zh: '看多', en: 'BULLISH' },
    BEARISH: { zh: '看空', en: 'BEARISH' },
    BINARY:  { zh: '二元', en: 'BINARY'  },
    NEUTRAL: { zh: '中性', en: 'NEUTRAL' },
    SPLIT:   { zh: '分歧', en: 'SPLIT'   },
  };
  const CLOSE_REASON_LABELS = {
    both_done:    { zh: '雙方完成',     en: 'both_done' },
    max_rounds:   { zh: '達上限輪數',   en: 'max_rounds' },
    timeout:      { zh: '逾時',         en: 'timeout' },
    cli_failures: { zh: 'CLI 連續失敗', en: 'cli_failures' },
    server_shutdown: { zh: '伺服器重啟', en: 'server_shutdown' },
    parse_failures:  { zh: '解析失敗',   en: 'parse_failures' },
  };

  function escapeHtml(s) {
    if (s == null) return '';
    return String(s)
      .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;').replace(/'/g, '&#39;');
  }

  function relTime(iso) {
    if (!iso) return '';
    const t = new Date(iso).getTime();
    if (!isFinite(t)) return '';
    const diff = (Date.now() - t) / 1000;
    if (diff < 0)     return 'now';
    if (diff < 60)    return Math.floor(diff) + 's';
    if (diff < 3600)  return Math.floor(diff / 60) + 'm';
    if (diff < 86400) return Math.floor(diff / 3600) + 'h';
    return Math.floor(diff / 86400) + 'd';
  }

  // Score badge: -5..+5 scale. Green positive, red negative, gray near zero.
  function renderScoreBadge(score) {
    const v = Number(score);
    if (!isFinite(v)) return '';
    const sign = v > 0 ? '+' : '';
    const color = v >= 2 ? '#22c55e'
                : v <= -2 ? '#ef4444'
                : Math.abs(v) >= 1 ? '#eab308'
                : '#6b7280';
    return `<span class="bn-score" style="background:color-mix(in srgb,${color},transparent 85%);
      border:1px solid color-mix(in srgb,${color},transparent 60%);color:${color};
      padding:2px 8px;border-radius:999px;font-weight:700;font-size:11px;font-variant-numeric:tabular-nums;">
      ${sign}${v.toFixed(1)}</span>`;
  }

  function renderSourcePill(name, credibility) {
    if (!name) return '';
    const credColor = credibility === 'HIGH' ? '#22c55e'
                    : credibility === 'MEDIUM' ? '#eab308'
                    : '#6b7280';
    return `<span class="bn-source" style="display:inline-flex;align-items:center;gap:4px;
      padding:2px 8px;border-radius:6px;background:color-mix(in srgb,var(--text-main),transparent 92%);
      border:1px solid color-mix(in srgb,var(--text-main),transparent 85%);font-size:11px;color:var(--text-muted);">
      <span style="width:6px;height:6px;border-radius:999px;background:${credColor};"></span>
      ${escapeHtml(name)}</span>`;
  }

  function renderAgePill(iso) {
    if (!iso) return '';
    const rt = relTime(iso);
    return `<span class="bn-age" style="font-size:11px;color:var(--text-muted);font-variant-numeric:tabular-nums;">${rt} ago</span>`;
  }

  function renderStatePill(state) {
    const meta = STATE_LABELS[state] || { zh: state || '?', en: state || '?', color: '#71717a' };
    const lang = currentLang();
    const label = meta[lang] || meta.en || state || '?';
    const color = meta.color;
    return `<span class="bn-state" style="font-size:10px;font-weight:700;letter-spacing:0.05em;
      text-transform:uppercase;padding:2px 8px;border-radius:6px;
      background:color-mix(in srgb,${color},transparent 85%);
      border:1px solid color-mix(in srgb,${color},transparent 60%);
      color:${color};">${label}</span>`;
  }

  function pickVerdictLabel(verdict) {
    const m = VERDICT_LABELS[verdict];
    if (!m) return verdict || '';
    return m[currentLang()] || m.en || verdict;
  }

  function pickCloseReasonLabel(reason) {
    const m = CLOSE_REASON_LABELS[reason];
    if (!m) return reason || '';
    return m[currentLang()] || m.en || reason;
  }

  // Entity chips — tickers blue, sectors purple, themes orange, tech-keywords magenta.
  // Flat layout — used inside per-comment thread bubbles where space is tight.
  function renderEntityChips(entities) {
    if (!entities) return '';
    function chips(list, color) {
      if (!list || list.length === 0) return '';
      return list.map(s => `<span style="font-size:10px;padding:1px 6px;border-radius:4px;
        background:color-mix(in srgb,${color},transparent 85%);
        border:1px solid color-mix(in srgb,${color},transparent 65%);color:${color};
        margin:2px 4px 2px 0;display:inline-block;">${escapeHtml(s)}</span>`).join('');
    }
    return [
      chips(entities.tickers,       '#3b82f6'),
      chips(entities.sectors,       '#a855f7'),
      chips(entities.themes,        '#f97316'),
      chips(entities.tech_keywords, '#ec4899'),
    ].filter(Boolean).join(' ');
  }

  // Categorized entity chips — used in the summary side panel. Each entity
  // type gets its own labeled section so the user can read what feeds the
  // knowledge graph at a glance.
  const ENTITY_CATEGORIES = [
    { key: 'tickers',       color: '#3b82f6', zh: '🏢 個股',     en: '🏢 Tickers' },
    { key: 'sectors',       color: '#a855f7', zh: '🏭 產業',     en: '🏭 Sectors' },
    { key: 'themes',        color: '#f97316', zh: '🔥 主題',     en: '🔥 Themes' },
    { key: 'tech_keywords', color: '#ec4899', zh: '🔬 技術節點', en: '🔬 Tech Keywords' },
  ];

  function renderEntityChipsGrouped(entities) {
    if (!entities) return '';
    const lang = currentLang();
    const sections = ENTITY_CATEGORIES.map(cat => {
      const list = entities[cat.key];
      if (!list || list.length === 0) return '';
      const label = lang === 'zh' ? cat.zh : cat.en;
      const chips = list.map(s => `<span style="font-size:11px;padding:2px 8px;border-radius:6px;
        background:color-mix(in srgb,${cat.color},transparent 84%);
        border:1px solid color-mix(in srgb,${cat.color},transparent 62%);
        color:${cat.color};margin:2px 4px 2px 0;display:inline-block;font-weight:500;">${escapeHtml(s)}</span>`).join('');
      return `<div style="margin-bottom:8px;">
        <div style="font-size:10px;font-weight:800;letter-spacing:0.06em;text-transform:uppercase;
          color:${cat.color};margin-bottom:4px;">
          ${label} <span style="color:var(--text-muted);font-weight:600;">(${list.length})</span>
        </div>
        <div>${chips}</div>
      </div>`;
    });
    return sections.filter(Boolean).join('');
  }

  function entityTotal(entities) {
    if (!entities) return { tickers: 0, sectors: 0, themes: 0, tech_keywords: 0, total: 0 };
    const tickers = (entities.tickers || []).length;
    const sectors = (entities.sectors || []).length;
    const themes  = (entities.themes  || []).length;
    const techs   = (entities.tech_keywords || []).length;
    return { tickers, sectors, themes, tech_keywords: techs, total: tickers + sectors + themes + techs };
  }

  // Thread bubble — one comment from one agent.
  function renderThreadBubble(comment) {
    if (!comment) return '';
    const agent = comment.agent || 'unknown';
    // Side (A/B) is positional truth from the debater — drives left/right + color.
    // Fallback for legacy comments with no `side`: parse the role label, then
    // last-resort the old claude===left heuristic.
    let side = comment.side;
    if (side !== 'A' && side !== 'B') {
      const lbl = comment.agent_role_label || {};
      const lblStr = (lbl.en || lbl.zh || '');
      side = /-B\b|分析師 B/.test(lblStr) ? 'B'
           : /-A\b|分析師 A/.test(lblStr) ? 'A'
           : (agent === 'claude' ? 'A' : 'B');
    }
    const isA = side === 'A';
    const AVATARS = { claude: '🤖', gemini: '💎', codex: '🧠' };
    const avatar  = AVATARS[agent] || (isA ? '🤖' : '💎');
    const color   = isA ? '#f97316' : '#3b82f6';
    const align   = isA ? 'flex-start' : 'flex-end';
    const parsed  = comment.parsed || {};
    const commentary = parsed.commentary || '(no commentary)';
    const done = parsed.done === true ||
                 (parsed.commentary && parsed.commentary.includes('<DONE>'));
    const conf = parsed.confidence;
    const entities = parsed.entities;
    const rationale = parsed.rationale_short;
    const parseWarn = comment.parse_status !== 'ok'
      ? `<span style="font-size:10px;color:#ef4444;margin-left:6px;">[parse:${comment.parse_status}]</span>` : '';
    const roleLabel = pickLabel(comment.agent_role_label, agent);
    const lang = currentLang();
    const roundWord = lang === 'zh' ? '第' : 'round';
    const roundSuffix = lang === 'zh' ? ' 輪' : '';
    const confWord = lang === 'zh' ? '信心' : 'conf';
    return `<div class="bn-bubble" style="display:flex;justify-content:${align};margin:8px 0;">
      <div style="max-width:78%;background:color-mix(in srgb,${color},transparent 92%);
        border:1px solid color-mix(in srgb,${color},transparent 70%);
        border-radius:12px;padding:10px 12px;">
        <div style="display:flex;align-items:center;gap:6px;margin-bottom:6px;flex-wrap:wrap;">
          <span style="font-size:14px;">${avatar}</span>
          <span style="font-weight:700;font-size:12px;color:${color};">
            ${escapeHtml(roleLabel)}</span>
          <span style="font-size:10px;color:var(--text-muted);">${roundWord} ${comment.round ?? '?'}${roundSuffix}</span>
          ${conf != null ? `<span style="font-size:10px;color:var(--text-muted);">${confWord} ${Number(conf).toFixed(2)}</span>` : ''}
          ${done ? '<span style="font-size:10px;color:#22c55e;font-weight:700;">&lt;DONE&gt;</span>' : ''}
          ${parseWarn}
        </div>
        <div style="font-size:13px;color:var(--text-main);line-height:1.5;white-space:pre-wrap;">${escapeHtml(commentary)}</div>
        ${rationale ? `<div style="font-size:11px;color:var(--text-muted);margin-top:6px;font-style:italic;">${escapeHtml(rationale)}</div>` : ''}
        ${renderEntityChips(entities)
          ? `<div style="margin-top:8px;">${renderEntityChips(entities)}</div>` : ''}
      </div>
    </div>`;
  }

  // Generic news card. opts.compact = true → break-news streaming view.
  // For full-detail digest cards, use the existing page-news.js renderer
  // (this primitive is kept lean intentionally).
  function renderNewsCard(item, opts) {
    opts = opts || {};
    const score = item.shallow_score ?? item.net_impact_score ?? item.score;
    const headline = escapeHtml(item.headline || '(no headline)');
    const headlineZh = item.headline_zh ? escapeHtml(item.headline_zh) : '';
    const verdict = item.consensus_verdict || item.verdict;
    const verdictColor = verdict === 'BULLISH' ? '#22c55e'
                       : verdict === 'BEARISH' ? '#ef4444'
                       : verdict === 'BINARY'  ? '#eab308'
                       : verdict === 'SPLIT'   ? '#a855f7'
                       : '#71717a';
    const verdictLabel = pickVerdictLabel(verdict);
    const verdictBadge = verdict
      ? `<span style="font-size:10px;font-weight:800;padding:2px 8px;border-radius:6px;
        background:color-mix(in srgb,${verdictColor},transparent 85%);color:${verdictColor};
        border:1px solid color-mix(in srgb,${verdictColor},transparent 60%);
        letter-spacing:0.04em;">${escapeHtml(verdictLabel)}</span>` : '';
    const commentBadge = (item.comment_count > 0)
      ? `<span style="font-size:11px;color:var(--text-muted);">💬 ${item.comment_count}</span>` : '';

    return `<div class="glass-card bn-card" data-news-id="${escapeHtml(item.news_id || '')}"
      style="padding:14px 16px;margin-bottom:12px;cursor:pointer;transition:all 0.2s;">
      <div style="display:flex;justify-content:space-between;align-items:flex-start;gap:12px;margin-bottom:8px;">
        <div style="display:flex;align-items:center;gap:8px;flex-wrap:wrap;">
          ${renderStatePill(item.state)}
          ${renderScoreBadge(score)}
          ${verdictBadge}
          ${renderSourcePill(item.source, item.credibility)}
          ${item.binary_flag ? '<span style="font-size:10px;color:#eab308;font-weight:700;">⚡ BINARY</span>' : ''}
        </div>
        <div style="display:flex;align-items:center;gap:8px;">
          ${commentBadge}
          ${renderAgePill(item.published || item.fetched_at)}
        </div>
      </div>
      <div style="font-size:14px;font-weight:600;color:var(--text-card-title);line-height:1.4;">${headline}</div>
      ${headlineZh ? `<div style="font-size:12px;color:var(--text-muted);margin-top:4px;">${headlineZh}</div>` : ''}
    </div>`;
  }

  global.NewsComponents = {
    escapeHtml, relTime, pickLabel, currentLang,
    renderScoreBadge, renderSourcePill, renderAgePill, renderStatePill,
    renderEntityChips, renderEntityChipsGrouped, entityTotal,
    renderThreadBubble, renderNewsCard,
    pickVerdictLabel, pickCloseReasonLabel,
  };
})(window);
