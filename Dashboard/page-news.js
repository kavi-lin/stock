/**
 * page-news.js — News page presenter (ARCH-8)
 * Depends on: utils.js (window.UI, window.logToUI), i18n.js, data-store.js (window.DataStore)
 */

document.addEventListener('DOMContentLoaded', () => {
  UI.logToUI("Initializing System...");

  // Relative-time helper shared across deep verdict / triage / Futu push renders.
  // Returns "12s" / "5m" / "3h" / "2d" — caller appends " ago" if needed.
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

  function applyTranslations() {
    if (!window.i18n) return;
    const t = window.i18n[UI.currentLang];
    const set = (id, val) => { const el = document.getElementById(id); if (el && val != null) el.textContent = val; };

    // Header — Chinese title + English subtitle (decisions.html pattern)
    if (UI.currentLang === 'zh') {
      set('news-title',    '新聞戰情室');
      set('news-subtitle', 'News War Room');
    } else {
      set('news-title',    'News War Room');
      set('news-subtitle', '新聞戰情室');
    }
    set('refresh-news-label', UI.currentLang === 'zh' ? '更新' : 'Refresh');

    document.querySelector('[data-stat-label="total"]').textContent = t.total;
    document.querySelector('[data-stat-label="bull"]').textContent = t.bullish;
    document.querySelector('[data-stat-label="bear"]').textContent = t.bearish;
    document.querySelector('[data-stat-label="binary"]').textContent = t.binary;

    const brt = document.getElementById('binary-risks-title');
    if (brt) brt.textContent = t.calendar?.binary_risks_title || 'Upcoming Binary Risks';
    const tst = document.getElementById('trump-signals-title');
    if (tst) tst.textContent = t.trump_signals?.title || 'Policy Trade Signals';

    // Initial placeholders (only if still showing the untranslated default)
    const lastSync = document.getElementById('last-sync-time');
    if (lastSync) UI.applySyncLight(lastSync, null);
    const brList = document.getElementById('binary-risks-list');
    if (brList && brList.firstElementChild?.classList?.contains('animate-pulse')) {
      brList.innerHTML = `<div class="text-xs text-zinc-600 animate-pulse">${t.news_page?.loading || 'Loading...'}</div>`;
    }

    // Futu push card i18n keys (live in t.overview namespace)
    const o = t.overview || {};
    ['futu_push_title', 'futu_reload', 'futu_loading'].forEach(k => {
      const el = document.querySelector(`[data-i18n="${k}"]`);
      if (el && o[k]) el.textContent = o[k];
    });

    // V1.71.x — filter tab labels + search placeholder + reset button
    const isZh = UI.currentLang === 'zh';
    const tabLabels = isZh
      ? { all: '全部', reviewed: '已審核 ✅', pending: '待審核 ⏳' }
      : { all: 'All',  reviewed: 'Reviewed ✅', pending: 'Pending ⏳' };
    document.querySelectorAll('.news-tab[data-i18n-tab]').forEach(b => {
      const span = b.querySelector('[data-i18n-tab]');
      if (span) span.textContent = tabLabels[span.dataset.i18nTab] || span.textContent;
    });
    const searchInput = document.getElementById('news-search');
    if (searchInput) searchInput.placeholder = isZh ? '搜尋 ticker / 標題...' : 'Search ticker / headline...';
    const resetBtn = document.getElementById('news-controls-reset');
    if (resetBtn) resetBtn.textContent = isZh ? '重置' : 'Reset';
  }

  async function loadNews() {
    const feed = document.getElementById('news-feed-detailed');
    if (!window.i18n) return;
    const t = window.i18n[UI.currentLang];

    const np = t.news_page || {};
    feed.innerHTML = `<div class="text-center p-20 text-zinc-600 animate-pulse">${np.loading || 'Loading data...'}</div>`;

    try {
      logToUI("Loading data from DataStore...");
      const data = await DataStore.get();
      logToUI(`Data loaded. Found ${data.news?.length || 0} news items.`);

      feed.innerHTML = '';

      if (!data.news || data.news.length === 0) {
        feed.innerHTML = `<div class="p-20 text-center text-zinc-500">${t.no_data}</div>`;
        return;
      }

      let counts = { bullish: 0, bearish: 0, binary: 0 };

      data.news.forEach((item, idx) => {
        const impact = (item.impact || 'neutral').toLowerCase();
        const isBull = impact === 'bullish' || impact === 'positive';
        const isBear = impact === 'bearish' || impact === 'negative';
        const isBin  = impact === 'binary';

        if (isBull) counts.bullish++;
        else if (isBear) counts.bearish++;
        else if (isBin)  counts.binary++;

        const statusColor = isBull ? 'var(--status-bullish)'
                          : isBear ? 'var(--status-bearish)'
                          : isBin  ? 'var(--status-binary)'
                          :          'var(--text-muted)';
        const icon = isBull ? 'trending-up' : isBear ? 'trending-down' : isBin ? 'git-branch' : 'minus';
        const typeIconMap = { fomc:'landmark', earnings:'bar-chart-2', geopolitical:'globe', macro_data:'activity', political:'flag', sector_specific:'layers' };
        const typeIcon = typeIconMap[(item.type||'').toLowerCase()] || 'file-text';

        const translatedStatus = t.status?.[impact] || impact.toUpperCase();

        // Sector tags — improved contrast
        const sectorTags = (item.sectors || []).map(s => {
          const key = s.toUpperCase().replace(/ /g, '_');
          const name = UI.currentLang === 'zh' ? (t.sectors?.[key] || s) : s;
          return `<span style="background:color-mix(in srgb,${statusColor},transparent 88%);border-color:color-mix(in srgb,${statusColor},transparent 65%);color:${statusColor}" class="border text-[9px] px-2 py-0.5 rounded-md font-bold whitespace-nowrap">${name}</span>`;
        }).join('');

        // Score badge
        const scoreVal = (item.score ?? 0);
        const scoreStr = (scoreVal > 0 ? '+' : '') + scoreVal;

        // Binary risk badge
        const binaryBadge = item.binary_risk
          ? `<span class="text-[9px] font-black px-2 py-0.5 rounded-full border ${item.within_48h ? 'text-red-400 border-red-500/40 bg-red-500/10 animate-pulse' : 'text-yellow-400 border-yellow-500/40 bg-yellow-500/10'}">${np.binary_badge || '⚡ BINARY RISK'}</span>`
          : '';

        // Bull / Bear / Arbiter section
        const hasBullBear = item.bull_case || item.bear_case;
        const bullBearSection = hasBullBear ? `
          <div class="grid grid-cols-2 gap-3 mt-3">
            ${item.bull_case ? `
            <div class="rounded-lg p-2.5" style="background:color-mix(in srgb,var(--status-bullish),transparent 92%);border:1px solid color-mix(in srgb,var(--status-bullish),transparent 75%)">
              <div class="flex items-center gap-1 mb-1">
                <i data-lucide="trending-up" class="w-3 h-3" style="color:var(--status-bullish)"></i>
                <span class="text-[9px] font-black uppercase tracking-widest" style="color:var(--status-bullish)">${np.bull_label || 'Bull'}</span>
              </div>
              <p class="text-[11px] leading-relaxed" style="color:var(--text-card-title)">${item.bull_case}</p>
            </div>` : ''}
            ${item.bear_case ? `
            <div class="rounded-lg p-2.5" style="background:color-mix(in srgb,var(--status-bearish),transparent 92%);border:1px solid color-mix(in srgb,var(--status-bearish),transparent 75%)">
              <div class="flex items-center gap-1 mb-1">
                <i data-lucide="trending-down" class="w-3 h-3" style="color:var(--status-bearish)"></i>
                <span class="text-[9px] font-black uppercase tracking-widest" style="color:var(--status-bearish)">${np.bear_label || 'Bear'}</span>
              </div>
              <p class="text-[11px] leading-relaxed" style="color:var(--text-card-title)">${item.bear_case}</p>
            </div>` : ''}
          </div>` : '';

        const arbiterSection = item.arbiter_reasoning ? `
          <div class="mt-2.5 rounded-lg px-3 py-2 flex items-start gap-2" style="background:color-mix(in srgb,${statusColor},transparent 93%);border:1px solid color-mix(in srgb,${statusColor},transparent 78%)">
            <i data-lucide="gavel" class="w-3 h-3 mt-0.5 shrink-0" style="color:${statusColor}"></i>
            <p class="text-[11px] leading-relaxed" style="color:var(--text-card-title)"><span class="font-bold" style="color:${statusColor}">${np.arbiter_prefix || 'Arbiter → '}</span>${item.arbiter_reasoning}</p>
          </div>` : '';

        const debateNote = item.debate_note ? `
          <div class="mt-1.5 flex items-center gap-1.5">
            <i data-lucide="message-square" class="w-3 h-3 text-zinc-500 shrink-0"></i>
            <p class="text-[10px] text-zinc-500 italic leading-snug">${item.debate_note}</p>
          </div>` : '';

        // review_status: DIGEST=reviewed, FLASH=pending, legacy=reviewed (no field)
        const reviewStatus = item.review_status || 'reviewed';
        const isPending = reviewStatus === 'pending';

        // Review badge + submit-for-review button
        const reviewBadge = isPending
          ? `<span class="text-[9px] font-black px-2 py-0.5 rounded-full border text-amber-400 border-amber-500/40 bg-amber-500/10">⏳ ${np.pending_label || 'PENDING'}</span>`
          : `<span class="text-[9px] font-black px-2 py-0.5 rounded-full border text-emerald-400 border-emerald-500/40 bg-emerald-500/10">✅ ${np.reviewed_label || 'REVIEWED'}</span>`;

        const reviewBtn = isPending
          ? `<button onclick="copyReviewPrompt(this, '${(item.headline||'').replace(/'/g, "\\'").replace(/"/g, '&quot;')}')" class="mt-2 flex items-center gap-1.5 text-[10px] font-bold px-3 py-1.5 rounded-lg border border-amber-500/40 text-amber-400 hover:bg-amber-500 hover:text-black hover:border-amber-500 transition-all">
              <i data-lucide="send" class="w-3 h-3"></i> ${np.review_btn || '送審'}
            </button>`
          : '';

        const card = document.createElement('div');
        card.className = 'glass-card p-5 hover:border-zinc-500/50 transition-all mb-4';
        card.dataset.reviewStatus = reviewStatus;
        // V1.71.x — verdict for left-edge stripe + chip filter
        card.dataset.verdict = (item.verdict || '').toLowerCase();
        // Searchable key: headline + headline_zh + tickers + sectors (lowercased)
        const tickers = Array.isArray(item.tickers_mentioned) ? item.tickers_mentioned.join(' ') : '';
        const sectors = Array.isArray(item.affected_sectors) ? item.affected_sectors.join(' ') : '';
        card.dataset.searchKey = `${item.headline||''} ${item.headline_zh||''} ${tickers} ${sectors}`.toLowerCase();
        card.innerHTML = `
          <!-- Header row -->
          <div class="flex items-start justify-between gap-3 mb-3">
            <div class="flex items-center gap-2.5 flex-wrap">
              <!-- Verdict badge -->
              <div class="flex items-center gap-1.5 rounded-full px-3 py-1" style="background:color-mix(in srgb,${statusColor},transparent 85%);border:1px solid color-mix(in srgb,${statusColor},transparent 60%)">
                <i data-lucide="${icon}" class="w-3.5 h-3.5" style="color:${statusColor}"></i>
                <span class="text-[10px] font-black uppercase tracking-widest" style="color:${statusColor}">${translatedStatus}</span>
                <span class="text-[11px] font-mono font-bold ml-0.5" style="color:${statusColor}">${scoreStr}</span>
              </div>
              <!-- Type badge -->
              ${item.type ? `<div class="flex items-center gap-1 rounded-full px-2 py-0.5 bg-zinc-100 dark:bg-zinc-800 border border-zinc-200 dark:border-zinc-700">
                <i data-lucide="${typeIcon}" class="w-2.5 h-2.5 text-zinc-500 dark:text-zinc-400"></i>
                <span class="text-[9px] font-bold uppercase tracking-widest text-zinc-500 dark:text-zinc-400">${np.news_type?.[(item.type||'').toLowerCase()] || item.type}</span>
              </div>` : ''}
              ${binaryBadge}
              ${reviewBadge}
            </div>
            <!-- Date + source -->
            <div class="text-right shrink-0">
              ${(() => {
                const ageStr = relTime(item.published);
                if (!ageStr) {
                  return `<div class="text-[10px] font-mono text-zinc-500">${item.date || ''}</div>`;
                }
                const ageSec = (Date.now() - new Date(item.published).getTime()) / 1000;
                const ageColor = ageSec < 3600 ? 'text-emerald-400'
                              : ageSec < 21600 ? 'text-zinc-400'
                              : ageSec >= 43200 ? 'text-zinc-600'
                              : 'text-zinc-500';
                return `
                  <div class="text-[10px] font-mono ${ageColor}" title="${UI.escapeHTML(item.published || '')}">${ageStr} ${UI.currentLang === 'zh' ? '前' : 'ago'}</div>
                  <div class="text-[9px] font-mono text-zinc-600">${item.date || ''}</div>`;
              })()}
              ${item.source_label ? `<div class="text-[9px] text-zinc-600">${item.source_label}</div>` : ''}
            </div>
          </div>

          <!-- Headline EN -->
          <h3 class="text-[15px] font-semibold leading-snug mb-1" style="color:var(--text-card-title)">${item.headline}</h3>
          <!-- Headline ZH -->
          ${item.headline_zh ? `<p class="text-[12px] text-zinc-500 leading-snug mb-2">${item.headline_zh}</p>` : ''}

          <!-- Sector tags -->
          ${sectorTags ? `<div class="flex flex-wrap gap-1.5 mb-1">${sectorTags}</div>` : ''}

          <!-- Bull / Bear grid -->
          ${bullBearSection}

          <!-- Arbiter -->
          ${arbiterSection}

          <!-- Debate note -->
          ${debateNote}

          <!-- Review submit button (pending only) -->
          ${reviewBtn}
        `;
        feed.appendChild(card);
      });

      document.getElementById('total-news').textContent = data.news.length;
      document.getElementById('bull-news').textContent = counts.bullish;
      document.getElementById('bear-news').textContent = counts.bearish;
      document.getElementById('binary-news').textContent = counts.binary;

      // Pass news_content_date as a source so the sync light turns orange when digest is stale
      const newsSources = data.news_content_date ? [{
          label: UI.currentLang === 'en' ? 'News digest' : '新聞 digest',
          ts:    data.news_content_date,
          ttl:   1439,   // flag if older than 24h (i.e. not today)
          hint:  UI.currentLang === 'en' ? 'Run "新聞分析 DIGEST" to refresh' : '執行「新聞分析 DIGEST」更新',
      }] : [];
      UI.applySyncLight(document.getElementById('last-sync-time'), data.last_updated, null, newsSources);

      // Binary Risks Sidebar
      const binaryList = document.getElementById('binary-risks-list');
      const calT = t.calendar || {};
      if (binaryList && data.binary_risks?.length) {
          binaryList.innerHTML = data.binary_risks.map(ev => {
              const days = ev.days_until;
              const urgency = ev.within_48h ? 'text-red-400 border-red-500/30 bg-red-500/5'
                            : days != null && days <= 7 ? 'text-yellow-400 border-yellow-500/30 bg-yellow-500/5'
                            : 'text-zinc-500 dark:text-zinc-400 border-zinc-200 dark:border-zinc-700 bg-zinc-50 dark:bg-zinc-900/30';
              const daysLabel = days == null ? '' : days < 0 ? (calT.past || 'PAST') : days === 0 ? (calT.today || 'TODAY') : `T-${days}d`;
              const sectorTags = (ev.affected_sectors || []).map(s =>
                  `<span class="text-[8px] px-1.5 py-0.5 rounded bg-zinc-100 dark:bg-zinc-800 text-zinc-500 dark:text-zinc-400 font-mono">${s}</span>`
              ).join('');
              return `
              <div class="glass-card p-3 border ${urgency} rounded-xl">
                  <div class="flex items-start justify-between gap-2 mb-2">
                      <p class="text-[11px] font-semibold leading-snug flex-1" style="color:var(--text-card-title)">${ev.event}</p>
                      ${daysLabel ? `<span class="text-[9px] font-black shrink-0 ${ev.within_48h ? 'text-red-400 animate-pulse' : 'text-zinc-500'}">${daysLabel}</span>` : ''}
                  </div>
                  <div class="text-[9px] text-zinc-600 font-mono mb-2">${ev.date}</div>
                  <div class="flex flex-wrap gap-1">${sectorTags}</div>
              </div>`;
          }).join('');
      } else if (binaryList) {
          binaryList.innerHTML = `<div class="text-xs text-zinc-600">${calT.no_events || 'No upcoming events.'}</div>`;
      }

      // Trump Trade Signals (A4-TRUMP)
      const trumpSection = document.getElementById('trump-signals-section');
      const trumpList = document.getElementById('trump-signals-list');
      const trumpT = t.trump_signals || {};
      const dirT = trumpT.direction || {};
      if (trumpList && data.market?.trump_signals?.length) {
          trumpSection.style.display = '';
          trumpList.innerHTML = data.market.trump_signals.map(sig => {
              const dir = (sig.direction || 'binary').toLowerCase();
              const isBull = dir === 'bullish';
              const isBear = dir === 'bearish';
              const sigColor = isBull ? 'var(--status-bullish)' : isBear ? 'var(--status-bearish)' : 'var(--status-binary)';
              const dirLabel = dirT[dir] || sig.direction || dir;
              const icon = isBull ? 'trending-up' : isBear ? 'trending-down' : 'alert-circle';
              const sectors = (sig.affected_sectors || []).map(s =>
                  `<span class="text-[8px] px-1.5 py-0.5 rounded bg-zinc-100 dark:bg-zinc-800 text-zinc-500 dark:text-zinc-400 font-mono">${s}</span>`
              ).join('');
              return `
              <div class="glass-card p-3 rounded-xl border border-zinc-200 dark:border-zinc-700/50">
                  <div class="flex items-center justify-between mb-2">
                      <span class="text-[9px] font-black uppercase tracking-widest" style="color:${sigColor}">
                          <i data-lucide="${icon}" class="w-3 h-3 inline-block mr-0.5"></i> ${dirLabel}
                      </span>
                  </div>
                  <p class="text-[10px] leading-relaxed mb-2" style="color:var(--text-card-title)">${sig.headline || sig.trade_idea || ''}</p>
                  <div class="flex flex-wrap gap-1">${sectors}</div>
              </div>`;
          }).join('');
      } else if (trumpSection) {
          trumpSection.style.display = 'none';
      }

      lucide.createIcons();
    } catch (e) {
      logToUI(e.message, 'error');
      document.getElementById('debug-console')?.classList.remove('hidden');
      feed.innerHTML = `
        <div class="glass-card p-10 border-red-500/20 bg-red-500/5 text-center">
          <h3 class="text-red-500 font-bold mb-2">${t.failed}</h3>
          <p class="text-xs text-zinc-500 mb-4">${e.message}</p>
          <button onclick="location.reload()" class="mt-4 px-4 py-2 bg-zinc-200 dark:bg-zinc-800 rounded text-xs font-bold transition-all hover:bg-zinc-300 dark:hover:bg-zinc-700">${(t.news_page?.retry_btn) || 'RETRY'}</button>
        </div>`;
    }
  }

  // ── Review Filter Tabs + Search + Verdict Chips (V1.71.x) ────
  let activeNewsFilter = 'all';
  // Verdict chip state — restore from localStorage; default = all 4 active
  const VERDICT_KEYS = ['bullish', 'bearish', 'binary', 'neutral'];
  const verdictFilter = new Set(
    (() => {
      try {
        const v = JSON.parse(localStorage.getItem('news_verdicts') || 'null');
        return Array.isArray(v) ? v : VERDICT_KEYS;
      } catch { return VERDICT_KEYS; }
    })()
  );
  let searchTerm = (localStorage.getItem('news_search') || '').toLowerCase();

  function applyNewsFilter() {
    const deepFeed   = document.getElementById('news-feed-detailed');
    const triageFeed = document.getElementById('news-triage-feed');
    if (activeNewsFilter === 'triage') {
      // Switch to triage view: hide deep feed, show triage feed.
      if (deepFeed)   deepFeed.classList.add('hidden');
      if (triageFeed) {
        triageFeed.classList.remove('hidden');
        renderTriageFeed();
      }
      updateMatchCount(0, 0);
      return;
    }
    // Default: deep feed visible, triage feed hidden
    if (deepFeed)   deepFeed.classList.remove('hidden');
    if (triageFeed) triageFeed.classList.add('hidden');

    const cards = document.querySelectorAll('#news-feed-detailed > .glass-card');
    let shown = 0;
    cards.forEach(c => {
      const st = c.dataset.reviewStatus || 'reviewed';
      const v = (c.dataset.verdict || 'neutral').toLowerCase();
      const sk = c.dataset.searchKey || '';

      const reviewOK = activeNewsFilter === 'all' || activeNewsFilter === st;
      const verdictOK = verdictFilter.has(v) || (!VERDICT_KEYS.includes(v) && verdictFilter.has('neutral'));
      const searchOK = !searchTerm || sk.includes(searchTerm);

      if (reviewOK && verdictOK && searchOK) {
        c.style.display = '';
        shown++;
      } else {
        c.style.display = 'none';
      }
    });
    updateMatchCount(shown, cards.length);
  }

  function updateMatchCount(now, total) {
    const nowEl = document.getElementById('news-match-now');
    const totEl = document.getElementById('news-match-total');
    if (nowEl) nowEl.textContent = now;
    if (totEl) totEl.textContent = total;
  }

  function updateTabCounts() {
    const cards = document.querySelectorAll('#news-feed-detailed > .glass-card');
    let total = 0, reviewed = 0, pending = 0;
    cards.forEach(c => {
      total++;
      const st = c.dataset.reviewStatus || 'reviewed';
      if (st === 'reviewed') reviewed++;
      else if (st === 'pending') pending++;
    });
    const set = (id, v) => { const el = document.getElementById(id); if (el) el.textContent = v; };
    set('nf-all-count', total);
    set('nf-reviewed-count', reviewed);
    set('nf-pending-count', pending);

    // Triage count from data.shallow_news (best-effort)
    if (window.DataStore?._cache?.shallow_news) {
      set('nf-triage-count', window.DataStore._cache.shallow_news.length);
    }
  }

  function refreshActiveTabClass() {
    document.querySelectorAll('.news-tab[data-filter]').forEach(b => {
      b.classList.toggle('active', b.dataset.filter === activeNewsFilter);
    });
  }

  function refreshVerdictChips() {
    document.querySelectorAll('.news-vchip[data-verdict]').forEach(b => {
      b.classList.toggle('active', verdictFilter.has(b.dataset.verdict));
    });
  }

  // Right-rail collapse: when Trump signals empty, mark 2col data attr
  function updateRailVisibility() {
    const wrap = document.querySelector('.news-2col');
    if (!wrap) return;
    const trumpSection = document.getElementById('trump-signals-section');
    const trumpVisible = trumpSection && trumpSection.style.display !== 'none';
    wrap.dataset.rail = trumpVisible ? 'has' : 'empty';
  }

  // ── Triage Feed (Stage-1 shallow verdicts from data.shallow_news) ─────
  async function renderTriageFeed() {
    const container = document.getElementById('news-triage-feed');
    if (!container) return;
    const isZh = UI.currentLang === 'zh';
    const t  = window.i18n?.[UI.currentLang] || {};
    const np = t.news_page || {};

    container.innerHTML = `<div class="text-center p-10 text-zinc-500 animate-pulse">${np.loading || 'Loading...'}</div>`;
    let data;
    try { data = await DataStore.get(); } catch (e) {
      container.innerHTML = `<div class="glass-card p-6 border-red-500/20 bg-red-500/5 text-red-500 text-xs">${UI.escapeHTML(e.message)}</div>`;
      return;
    }
    const items = data.shallow_news || [];

    // Freshness dot reflects FEED freshness (max published in shallow_news),
    // NOT raw.json mtime. Raw.json mtime is misleading: it advances when you
    // re-fetch news sources, but the rendered feed only updates after the
    // triage protocol re-runs the shallow snap. Aligning the dot to feed
    // content avoids the "12m updated / 16h items" contradiction.
    let feedAgeSec = null, feedAgeStr = '?';
    if (items.length) {
      let newestMs = 0;
      for (const it of items) {
        const t = Date.parse(it.published || '');
        if (isFinite(t) && t > newestMs) newestMs = t;
      }
      if (newestMs) {
        feedAgeSec = Math.max(0, (Date.now() - newestMs) / 1000);
        feedAgeStr = relTime(new Date(newestMs).toISOString());
      }
    }

    // raw.json mtime — kept for the "stale triage cache" warning in tooltip
    // (when raw.json is materially newer than feed, user should re-run triage).
    let rawAgeSec = null, rawAgeStr = '?';
    try {
      const pr = await fetch('/api/preflight');
      if (pr.ok) {
        const pd = await pr.json();
        const rss = (pd.items || []).find(it => it.key === 'rss');
        if (rss) { rawAgeSec = rss.age_sec; rawAgeStr = rss.age_str || '?'; }
      }
    } catch (_) { /* ignore */ }

    // 4-tier dot color based on feed freshness
    let dotColor, dotLabel;
    if (feedAgeSec == null) {
      dotColor = '#71717a'; dotLabel = isZh ? '未知' : 'unknown';
    } else if (feedAgeSec < 3600)   { dotColor = '#22c55e'; dotLabel = isZh ? '新鮮' : 'fresh'; }
    else if   (feedAgeSec < 10800)  { dotColor = '#facc15'; dotLabel = isZh ? '尚可' : 'recent'; }
    else if   (feedAgeSec < 21600)  { dotColor = '#f97316'; dotLabel = isZh ? '偏舊' : 'fading'; }
    else                            { dotColor = '#ef4444'; dotLabel = isZh ? '過期' : 'stale'; }

    // Stale-cache hint: raw.json materially newer than feed → triage 需重跑
    const triageStale = (rawAgeSec != null && feedAgeSec != null && (feedAgeSec - rawAgeSec) > 1800);
    const staleHintHtml = triageStale
      ? `<div style="color:#facc15;font-size:11px;margin-top:6px;border-top:1px solid #3f3f46;padding-top:6px">${isZh
          ? '⚠ 新聞源已更新（' + rawAgeStr + ' 前），但下面 feed 是上次 triage 結果（' + feedAgeStr + ' 前）— 點「更新新聞源」重跑 Stage 1 才會反映新內容'
          : '⚠ News sources fetched ' + rawAgeStr + ' ago, but feed below is from previous triage (' + feedAgeStr + ' ago) — click "Refresh News" to re-run Stage 1'}</div>`
      : '';

    // Tooltip content (rendered into shared #_sync_tooltip via JS handler).
    // Uses canonical utils.js pattern (position:fixed + z:9999) instead of the
    // old absolute/group-hover approach that was clipped by glass-card stacking.
    const tipTitle = isZh ? '新聞 Feed Freshness' : 'News Feed Freshness';
    const tipFeedLine = isZh
      ? '下方 feed 最新一則：<b style="color:' + dotColor + '">' + feedAgeStr + ' 前</b>（' + dotLabel + '）'
      : 'Newest item shown: <b style="color:' + dotColor + '">' + feedAgeStr + ' ago</b> (' + dotLabel + ')';
    const tipRawLine = (rawAgeSec != null)
      ? (isZh
          ? '<div style="color:#a1a1aa;font-size:10px;margin-top:4px">新聞源 raw.json 上次抓取：' + rawAgeStr + ' 前</div>'
          : '<div style="color:#a1a1aa;font-size:10px;margin-top:4px">News sources raw.json fetched: ' + rawAgeStr + ' ago</div>')
      : '';
    const tipSourcesLine = isZh
      ? '<div style="color:#a1a1aa;font-size:10px;margin-top:4px">來源：RSS · Finnhub · FMP · SEC EDGAR</div>'
      : '<div style="color:#a1a1aa;font-size:10px;margin-top:4px">Sources: RSS · Finnhub · FMP · SEC EDGAR</div>';
    const tipRuleLine = '<div style="color:#71717a;font-size:10px;margin-top:4px">' + (isZh ? '規則' : 'Rule') + ': &lt;1h 🟢 / &lt;3h 🟡 / &lt;6h 🟠 / ≥6h 🔴</div>';
    const tipHtml =
      '<div style="font-weight:700;color:' + dotColor + ';margin-bottom:4px">' + tipTitle + '</div>' +
      '<div style="color:#d4d4d8;margin-bottom:6px;font-size:11px">' + tipFeedLine + '</div>' +
      tipSourcesLine + tipRawLine + tipRuleLine + staleHintHtml;
    container._triageTipHtml = tipHtml;

    // Header: title + news-feed dot+age + 更新按鈕.
    // The dot has id=triage-freshness-dot — wireTriageButtons() attaches the
    // hover handler that pipes container._triageTipHtml into the shared
    // #_news_tooltip element (utils.js applySyncLight pattern).
    const headerHtml = `
      <div class="glass-card p-4 flex items-center gap-3">
        <i data-lucide="layers" class="w-4 h-4 text-amber-400"></i>
        <div class="flex-1 min-w-0">
          <h4 class="text-sm font-bold" data-i18n="triage_section_title">${isZh ? 'Stage 1 新聞 Triage（RSS + Finnhub + FMP + SEC EDGAR）' : 'Stage 1 News Triage (RSS + Finnhub + FMP + SEC EDGAR)'}</h4>
          <p class="text-[10px] text-zinc-500">${isZh ? '初步篩選 — 對有興趣的可送 Phase 2 inline debate' : 'Initial classification — send interesting items to Phase 2 inline debate'}</p>
        </div>
        <span class="text-[10px] font-mono text-zinc-500 shrink-0">${items.length} ${isZh ? '則' : 'items'}</span>
        <span id="triage-freshness-dot" class="inline-flex items-center gap-1.5 px-1.5 py-0.5 rounded shrink-0" style="cursor:default">
          <span style="display:inline-block;width:8px;height:8px;border-radius:50%;background:${dotColor};box-shadow:0 0 5px ${dotColor}99;flex-shrink:0"></span>
          <span class="text-[10px] font-mono text-zinc-400">${UI.escapeHTML(feedAgeStr)}</span>
          ${triageStale ? '<span style="color:#facc15;font-size:11px;margin-left:2px" title="新聞源已更新但 triage 未重跑">⚠</span>' : ''}
        </span>
        <button id="triage-run-btn" class="text-[10px] font-black uppercase tracking-widest px-3 py-1.5 rounded border border-amber-500/40 text-amber-400 hover:bg-amber-500 hover:text-black hover:border-amber-500 transition-all flex items-center gap-1.5 shrink-0" data-i18n="triage_run_btn">
          <i data-lucide="refresh-cw" class="w-3 h-3"></i>${isZh ? '更新新聞源' : 'Refresh News'}
        </button>
      </div>`;

    if (items.length === 0) {
      container.innerHTML = headerHtml + `<div class="text-center p-10 text-zinc-500 text-xs italic" data-i18n="triage_no_data">${isZh ? '尚無 triage 資料 — 點「更新新聞源」開始' : 'No triage data yet — click "Refresh News" to start'}</div>`;
      wireTriageButtons();
      if (window.lucide) lucide.createIcons();
      container.dataset.rendered = '1';
      return;
    }

    const cardsHtml = items.map(it => {
      const impact = (it.impact || 'neutral').toLowerCase();
      const score  = it.score == null ? '—' : (it.score >= 0 ? '+' : '') + Number(it.score).toFixed(1);
      const scoreColor = impact === 'bullish' ? 'text-emerald-400 border-emerald-500/40 bg-emerald-500/10'
                        : impact === 'bearish' ? 'text-red-400 border-red-500/40 bg-red-500/10'
                        : impact === 'binary'  ? 'text-yellow-400 border-yellow-500/40 bg-yellow-500/10'
                        : 'text-zinc-400 border-zinc-500/40 bg-zinc-500/10';
      const headlineDisplay = isZh ? (it.headline_zh || it.headline) : it.headline;
      const headlineForFlash = (it.headline || '').replace(/"/g, '&quot;');
      const sectorPills = (it.sectors || []).slice(0, 3).map(s =>
        `<span class="text-[9px] px-1.5 py-0.5 rounded bg-zinc-200 dark:bg-zinc-800 text-zinc-600 dark:text-zinc-400">${UI.escapeHTML(s)}</span>`
      ).join('');
      const tickerPills = (it.tickers_mentioned || []).slice(0, 5).map(tk =>
        `<span class="text-[9px] font-bold px-1.5 py-0.5 rounded bg-blue-500/15 text-blue-400 border border-blue-500/30">${UI.escapeHTML(tk)}</span>`
      ).join('');
      const binaryFlag = it.binary_risk
        ? `<span class="text-[9px] font-black px-1.5 py-0.5 rounded bg-yellow-500/15 text-yellow-400 border border-yellow-500/30">⚡${it.within_48h ? ' 48h' : ''}</span>`
        : '';
      const sourceFlag = it.source === 'triage'
        ? `<span class="text-[9px] text-amber-500/70 font-mono">[triage]</span>`
        : `<span class="text-[9px] text-zinc-500/70 font-mono">[digest]</span>`;
      // Per-item freshness — published comes from raw.json via bridge.py join.
      // Color cue: <1h emerald, <6h zinc, >=12h dim — lets user spot fresh items at a glance.
      const ageStr = relTime(it.published);
      let ageColor = 'text-zinc-500';
      if (ageStr) {
        const ageSec = (Date.now() - new Date(it.published).getTime()) / 1000;
        if (ageSec < 3600)        ageColor = 'text-emerald-400';
        else if (ageSec < 21600)  ageColor = 'text-zinc-400';
        else if (ageSec >= 43200) ageColor = 'text-zinc-600';
      }
      const ageHtml = ageStr
        ? `<span class="text-[10px] font-mono ${ageColor}" title="${UI.escapeHTML(it.published || '')}">${ageStr} ${isZh ? '前' : 'ago'}</span>`
        : '';

      return `
        <div class="glass-card p-3 hover:border-amber-500/40 transition-all">
          <div class="flex items-center gap-2 mb-1.5 flex-wrap">
            <span class="text-[10px] font-black px-2 py-0.5 rounded border ${scoreColor}">${score}</span>
            ${binaryFlag}
            ${sourceFlag}
            ${ageHtml}
            <button class="triage-phase2-btn ml-auto text-[10px] font-bold px-2.5 py-1 rounded border border-amber-500/40 text-amber-400 hover:bg-amber-500 hover:text-black hover:border-amber-500 transition-all"
                    data-headline="${headlineForFlash}" data-i18n="triage_phase2_btn" title="${isZh ? '送 Phase 2 inline debate' : 'Send to Phase 2 inline debate'}">
              ${isZh ? '⚡ Phase 2' : '⚡ Phase 2'}
            </button>
          </div>
          <p class="text-[12px] leading-relaxed mb-2" style="color:var(--text-main)">${UI.escapeHTML(headlineDisplay || '')}</p>
          <div class="flex flex-wrap gap-1 items-center">
            ${sectorPills}
            ${tickerPills}
          </div>
        </div>`;
    }).join('');

    container.innerHTML = headerHtml + cardsHtml;
    wireTriageButtons();
    if (window.lucide) lucide.createIcons();
    container.dataset.rendered = '1';
  }

  function wireTriageButtons() {
    document.getElementById('triage-run-btn')?.addEventListener('click', async () => {
      const isZh = UI.currentLang === 'zh';
      const confirmMsg = isZh
        ? `更新新聞源？會平行重抓 4 個源（RSS + Finnhub + FMP + SEC EDGAR，~30s）+ 對 100+ 則跑 Stage 1 shallow snap。\n約 6-10 分鐘 / ~$0.8 tokens`
        : `Refresh news sources?\nParallel re-fetch 4 sources (RSS + Finnhub + FMP + SEC EDGAR, ~30s) + shallow-snap 100+ items.\n~6-10 min / ~$0.8 tokens`;
      if (!confirm(confirmMsg)) return;
      triggerProtocol('triage', {}, isZh ? '跑 Stage 1 新聞 triage' : 'Running Stage 1 news triage');
    });

    // Wire freshness dot hover → shared #_news_tooltip (canonical fixed/z9999
    // pattern from utils.js applySyncLight, escapes glass-card stacking).
    const dot = document.getElementById('triage-freshness-dot');
    const container = document.getElementById('news-triage-feed');
    const tipHtml = container?._triageTipHtml;
    if (dot && tipHtml) {
      let tip = document.getElementById('_news_tooltip');
      if (!tip) {
        tip = document.createElement('div');
        tip.id = '_news_tooltip';
        tip.style.cssText = 'position:fixed;z-index:9999;background:var(--bg-card,#18181b);border:1px solid #3f3f46;border-radius:10px;padding:10px 14px;font-size:12px;line-height:1.6;pointer-events:none;opacity:0;transition:opacity 0.12s;max-width:320px;color:#e4e4e7';
        document.body.appendChild(tip);
      }
      dot.onmouseenter = function () {
        tip.innerHTML = tipHtml;
        tip.style.opacity = '1';
        const r = this.getBoundingClientRect();
        // Prefer below; flip above if would clip viewport bottom
        const tipH = 160;  // generous estimate; tooltip auto-shrinks
        const top = (r.bottom + tipH + 16 < window.innerHeight) ? (r.bottom + 8) : (r.top - tipH - 8);
        tip.style.top  = Math.max(8, top) + 'px';
        tip.style.left = Math.max(8, Math.min(r.right - 320, window.innerWidth - 328)) + 'px';
      };
      dot.onmouseleave = () => { tip.style.opacity = '0'; };
    }
    document.querySelectorAll('.triage-phase2-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        const headline = (btn.dataset.headline || '').replace(/&quot;/g, '"');
        if (!headline) return;
        window.goFlashText(headline);
      });
    });
  }

  // ── Filter wiring (V1.71.x: tabs + search + verdict chips) ────
  document.getElementById('news-filter-tabs')?.addEventListener('click', e => {
    const btn = e.target.closest('[data-filter]');
    if (!btn) return;
    activeNewsFilter = btn.dataset.filter;
    refreshActiveTabClass();
    applyNewsFilter();
  });
  refreshActiveTabClass();

  // Search input — debounced to 120ms
  const searchInput = document.getElementById('news-search');
  if (searchInput) {
    searchInput.value = searchTerm;
    let _searchT;
    searchInput.addEventListener('input', () => {
      clearTimeout(_searchT);
      _searchT = setTimeout(() => {
        searchTerm = (searchInput.value || '').toLowerCase().trim();
        localStorage.setItem('news_search', searchTerm);
        applyNewsFilter();
      }, 120);
    });
  }
  document.getElementById('news-search-clear')?.addEventListener('click', () => {
    if (!searchInput) return;
    searchInput.value = '';
    searchTerm = '';
    localStorage.removeItem('news_search');
    applyNewsFilter();
    searchInput.focus();
  });

  // Verdict chip toggles
  document.querySelectorAll('.news-vchip[data-verdict]').forEach(b => {
    b.addEventListener('click', () => {
      const v = b.dataset.verdict;
      if (verdictFilter.has(v)) verdictFilter.delete(v);
      else verdictFilter.add(v);
      localStorage.setItem('news_verdicts', JSON.stringify([...verdictFilter]));
      refreshVerdictChips();
      applyNewsFilter();
    });
  });
  refreshVerdictChips();

  // Reset button
  document.getElementById('news-controls-reset')?.addEventListener('click', () => {
    activeNewsFilter = 'all';
    VERDICT_KEYS.forEach(k => verdictFilter.add(k));
    searchTerm = '';
    if (searchInput) searchInput.value = '';
    localStorage.removeItem('news_search');
    localStorage.removeItem('news_verdicts');
    refreshActiveTabClass();
    refreshVerdictChips();
    applyNewsFilter();
  });

  // After every render, refresh tab counts + match count + rail visibility
  // Hook into a MutationObserver on the deep feed so any re-render updates counts.
  const _newsFeedObserver = new MutationObserver(() => {
    updateTabCounts();
    updateRailVisibility();
    applyNewsFilter();  // re-apply filter to newly added cards
  });
  const _deepFeedEl = document.getElementById('news-feed-detailed');
  if (_deepFeedEl) _newsFeedObserver.observe(_deepFeedEl, { childList: true });

  window.copyReviewPrompt = async function(btnEl, headline) {
    const isZh = UI.currentLang === 'zh';
    const prefix = await UI.dailyUpdatePrefix();
    const confirmMsg = prefix + (isZh
      ? `透過 Claude 執行正式委員會審核？（約 2-3 分鐘，消耗 tokens）`
      : `Run formal committee review via Claude? (~2-3 min, consumes tokens)`);
    if (!confirm(confirmMsg)) return;
    triggerProtocol('review', { headline }, isZh ? `審核中: ${headline.slice(0, 40)}...` : `Reviewing: ${headline.slice(0, 40)}...`);
  };

  // Run FLASH analysis on a free-text Futu push notification (free-text headline mode)
  window.goFlashText = async function(headline) {
    const isZh = UI.currentLang === 'zh';
    const preview = headline.slice(0, 30) + (headline.length > 30 ? '...' : '');
    const prefix = await UI.dailyUpdatePrefix();
    const confirmMsg = prefix + (isZh
      ? `送 FLASH 分析這則推播？\n「${preview}」\n約 5-10 分鐘 / ~$0.5-1 tokens`
      : `Run FLASH on this push?\n"${preview}"\n~5-10 min / ~$0.5-1 tokens`);
    if (!confirm(confirmMsg)) return;
    triggerProtocol('flash_text', { headline },
      isZh ? `FLASH 分析中: ${preview}` : `FLASH analyzing: ${preview}`);
  };

  // ── Protocol run banner (shared by DIGEST / FLASH / REVIEW) ──────
  let _newsPollTimer = null;

  function formatElapsed(sec) {
    const m = String(Math.floor(sec / 60)).padStart(2, '0');
    const s = String(sec % 60).padStart(2, '0');
    return `${m}:${s}`;
  }

  function showRunBanner(title, detail) {
    const banner = document.getElementById('news-run-banner');
    if (!banner) return;
    banner.classList.remove('hidden');
    banner.classList.remove('border-l-emerald-500', 'border-l-red-500');
    banner.classList.add('border-l-blue-500');
    document.getElementById('news-run-icon').innerHTML = '<span class="inline-block w-2 h-2 rounded-full bg-blue-500 animate-pulse"></span>';
    document.getElementById('news-run-title').textContent = title;
    document.getElementById('news-run-detail').textContent = detail || '';
    document.getElementById('news-run-elapsed').textContent = '00:00';
    document.getElementById('news-run-cancel').classList.remove('hidden');
    // While running, hide reload — clicking it would interrupt the live elapsed timer.
    document.getElementById('news-run-reload')?.classList.add('hidden');
  }

  function setRunBannerDone(msg) {
    const banner = document.getElementById('news-run-banner');
    if (!banner) return;
    banner.classList.remove('border-l-blue-500', 'border-l-red-500');
    banner.classList.add('border-l-emerald-500');
    document.getElementById('news-run-icon').innerHTML = '<span class="text-emerald-400 font-bold">✓</span>';
    document.getElementById('news-run-title').textContent = msg || 'Done';
    // Clear lingering "Claude is processing..." detail on done — otherwise the
    // banner displays both "分析完成，資料已更新" + "Claude 正在處理中..." which is contradictory.
    const detailEl = document.getElementById('news-run-detail');
    if (detailEl) detailEl.textContent = '';
    document.getElementById('news-run-cancel').classList.add('hidden');
    // Reload only meaningful once the elapsed timer has stopped accumulating.
    document.getElementById('news-run-reload')?.classList.remove('hidden');
    // Kept visible — user dismisses via the ✕ (#news-run-dismiss) button.
  }

  function setRunBannerError(msg) {
    const banner = document.getElementById('news-run-banner');
    if (!banner) return;
    banner.classList.remove('border-l-blue-500', 'border-l-emerald-500');
    banner.classList.add('border-l-red-500');
    document.getElementById('news-run-icon').innerHTML = '<span class="text-red-400 font-bold">✗</span>';
    document.getElementById('news-run-title').textContent = msg || 'Error';
    const detailEl = document.getElementById('news-run-detail');
    if (detailEl) detailEl.textContent = '';
    document.getElementById('news-run-cancel').classList.add('hidden');
    // Allow reload after error too — user often wants to retry / refetch.
    document.getElementById('news-run-reload')?.classList.remove('hidden');
  }

  async function pollNewsRunStatus() {
    try {
      const r = await fetch('/api/run-protocol/status');
      if (!r.ok) return;
      const s = await r.json();
      document.getElementById('news-run-elapsed').textContent = formatElapsed(s.elapsed_sec || 0);

      // Live log tail — pin-to-bottom unless user scrolled up
      const logEl = document.getElementById('news-run-log');
      if (logEl && typeof s.log_tail === 'string' && s.log_tail !== logEl.textContent) {
        const pinned = Math.abs(logEl.scrollHeight - logEl.clientHeight - logEl.scrollTop) < 40;
        logEl.textContent = s.log_tail;
        if (pinned) logEl.scrollTop = logEl.scrollHeight;
      }

      if (s.status !== 'running') {
        if (_newsPollTimer) { clearInterval(_newsPollTimer); _newsPollTimer = null; }
        const isZh = UI.currentLang === 'zh';
        if (s.status === 'done') {
          setRunBannerDone(isZh ? '分析完成，資料已更新' : 'Done — data refreshed');
          setTimeout(() => loadNews(), 2000);
        } else {
          setRunBannerError(s.error || s.status);
        }
      }
    } catch (e) { /* ignore */ }
  }

  // Expand / collapse the live-log panel
  document.getElementById('news-run-expand')?.addEventListener('click', () => {
    const panel = document.getElementById('news-run-panel');
    const btn   = document.getElementById('news-run-expand');
    if (!panel) return;
    const open = panel.classList.toggle('hidden') === false;
    if (btn) btn.textContent = open ? '收起' : '展開';
    if (open) {
      const log = document.getElementById('news-run-log');
      if (log) log.scrollTop = log.scrollHeight;
    }
  });

  // v1.61: protocol queue — POST /api/protocol-queue, NOT /api/run-protocol.
  // Banner only appears when this request actually starts running. While queued,
  // we just show a toast with position info.
  let _activeQueueId = null;  // tracks "my" current queued/running job for banner gate

  async function triggerProtocol(name, params, title) {
    const isZh = UI.currentLang === 'zh';
    let r;
    try {
      const res = await fetch('/api/protocol-queue', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name, ...params }),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({ error: res.statusText }));
        throw new Error(err.error || `HTTP ${res.status}`);
      }
      r = await res.json();
    } catch (e) {
      UI.showToast((isZh ? '排隊失敗：' : 'Enqueue failed: ') + e.message, 'error');
      return;
    }
    _activeQueueId = r.id;
    const lbl = r.label || name;
    const pos = r.position;
    const ahead = r.total_ahead;

    if (ahead === 0) {
      // Will start within ~2s — show banner immediately so progress is visible
      showRunBanner(title, isZh ? 'Claude 啟動中...' : 'Claude starting...');
      UI.showToast((isZh ? '開始執行 ' : 'Starting ') + lbl, 'info', 3000);
    } else {
      // Queued behind others — toast tells user position, no banner yet
      const msg = isZh
        ? `${lbl} 已排隊（第 ${pos} 個，前面 ${ahead} 個進行/排隊中）`
        : `${lbl} queued (#${pos}, ${ahead} ahead)`;
      UI.showToast(msg, 'info', 6000);
    }

    // Single global poller — replaces pollNewsRunStatus's old setInterval
    if (_newsPollTimer) { clearInterval(_newsPollTimer); _newsPollTimer = null; }
    _newsPollTimer = setInterval(() => pollForMyJob(_activeQueueId, title), 2000);
  }

  // Polls /api/run-protocol/status, gates banner by queue_id match.
  // Replaces direct call to pollNewsRunStatus from triggerProtocol — but
  // existing pollNewsRunStatus is still called by other paths (URL deep-link,
  // page-resume IIFE) which already implicitly assume their own job is active.
  async function pollForMyJob(myId, title) {
    if (!myId) return;
    try {
      const r = await fetch('/api/run-protocol/status');
      if (!r.ok) return;
      const s = await r.json();
      const isMine = s.queue_id === myId;
      if (!isMine) {
        // Still queued — keep waiting silently. (Could refresh queue position
        // from /api/protocol-queue here, omitted for simplicity.)
        return;
      }
      // It's my turn. If banner not yet shown, show it now.
      const banner = document.getElementById('news-run-banner');
      if (banner && banner.classList.contains('hidden') && s.status === 'running') {
        showRunBanner(title, UI.currentLang === 'zh' ? 'Claude 正在處理中...' : 'Claude is processing...');
      }
      // Delegate live status update (elapsed/log/done/error) to existing poller
      pollNewsRunStatus();
      if (s.status !== 'running' && s.ended_at) {
        // Finished — stop polling for this job
        clearInterval(_newsPollTimer); _newsPollTimer = null;
        _activeQueueId = null;
      }
    } catch (e) { /* ignore */ }
  }

  document.getElementById('news-run-cancel')?.addEventListener('click', async () => {
    try { await fetch('/api/run-protocol/cancel', { method: 'POST' }); } catch (e) { /* ignore */ }
  });
  document.getElementById('news-run-dismiss')?.addEventListener('click', () => {
    document.getElementById('news-run-banner')?.classList.add('hidden');
  });
  document.getElementById('news-run-reload')?.addEventListener('click', () => {
    // Mark banner as dismissed so the post-reload resume IIFE skips re-showing it.
    // sessionStorage = scoped to this tab, cleared on tab close — exactly what we want.
    try { sessionStorage.setItem('news_banner_dismissed', String(Date.now())); } catch (e) { /* ignore */ }
    location.reload();
  });

  // Deep-link: ?running=flash&ticker=NVDA (from decisions page POST)
  // or ?running=digest (auto-triggered)
  const _urlParams = new URLSearchParams(window.location.search);
  const _runningType = _urlParams.get('running');
  const _runningTicker = _urlParams.get('ticker');
  if (_runningType) {
    const isZh = UI.currentLang === 'zh';
    const title = _runningType === 'flash'
      ? (isZh ? `FLASH 新聞分析 — ${_runningTicker || ''}` : `FLASH News — ${_runningTicker || ''}`)
      : (isZh ? '新聞 DIGEST 更新中' : 'News DIGEST running');
    showRunBanner(title, isZh ? 'Claude 正在處理中...' : 'Claude is processing...');
    _newsPollTimer = setInterval(pollNewsRunStatus, 2000);
    pollNewsRunStatus();
  }

  // Resume banner on page load. Covers running *and* recently-finished runs
  // so navigating away mid-run and back doesn't lose the progress card / result.
  // Terminal states (done/error) only resume if ended within the last 5 min.
  // Exception: if user just clicked "重新整理" (sessionStorage flag set < 30s ago),
  // honor their dismiss intent and skip resume for terminal states. Running state
  // still resumes — user wouldn't expect to lose progress visibility on an active job.
  (async () => {
    try {
      const r = await fetch('/api/run-protocol/status');
      const s = await r.json();
      const isNews = s.name === 'news' || s.name === 'flash' || s.name === 'flash_text' || s.name === 'review' || s.name === 'triage';
      if (!isNews) return;
      let dismissedRecently = false;
      try {
        const t = parseInt(sessionStorage.getItem('news_banner_dismissed') || '0', 10);
        if (t && (Date.now() - t) < 30000) dismissedRecently = true;
        sessionStorage.removeItem('news_banner_dismissed');  // one-shot
      } catch (e) { /* ignore */ }
      if (dismissedRecently && s.status !== 'running') return;
      const isZh = UI.currentLang === 'zh';
      const RESUME_TERMINAL_WINDOW_MS = 5 * 60 * 1000;
      const endedRecently = s.ended_at
          && (Date.now() - new Date(s.ended_at).getTime()) < RESUME_TERMINAL_WINDOW_MS;
      if (s.status === 'running') {
        showRunBanner(isZh ? `${s.name} 執行中...` : `${s.name} running...`, '');
        _newsPollTimer = setInterval(pollNewsRunStatus, 2000);
      } else if (s.status === 'done' && endedRecently) {
        showRunBanner(isZh ? `${s.name} 完成` : `${s.name} done`, '');
        setRunBannerDone(isZh ? '分析完成，資料已更新' : 'Done — data refreshed');
      } else if (s.status === 'error' && endedRecently) {
        showRunBanner(isZh ? `${s.name} 失敗` : `${s.name} error`, '');
        setRunBannerError(s.error || s.status);
      }
    } catch (e) { /* ignore */ }
  })();

  // Shortcut to toggle Debug Console: Shift + D
  document.addEventListener('keydown', (e) => {
    if (e.shiftKey && e.key === 'D') {
      document.getElementById('debug-console')?.classList.toggle('hidden');
    }
  });

  document.getElementById('refresh-news').addEventListener('click', async () => {
    const isZh = UI.currentLang === 'zh';
    const prefix = await UI.dailyUpdatePrefix();
    const confirmMsg = prefix + (isZh
      ? '透過 Claude 執行「新聞分析 DIGEST」？（約 11-13 分鐘，~$2 tokens；超過 20 分鐘會被伺服器硬殺）'
      : 'Run "新聞分析 DIGEST" via Claude? (~11-13 min, ~$2 tokens; server hard-kills after 20 min)');
    if (!confirm(confirmMsg)) return;
    triggerProtocol('news', {}, isZh ? '新聞 DIGEST 更新中' : 'News DIGEST running');
  });

  // ── Futu push notifications (lazy fetch + 60s auto-refresh + per-row FLASH btn) ──
  (function initFutuPush() {
    const list = document.getElementById('futu-list');
    if (!list) return;
    const statusEl = document.getElementById('futu-status');
    const filterStatsEl = document.getElementById('futu-filter-stats');
    const reloadBtn = document.getElementById('futu-reload');

    function renderItems(items) {
      const isZh = UI.currentLang === 'zh';
      if (!items.length) {
        list.innerHTML = `<div class="text-[11px] text-zinc-500 italic" data-i18n="futu_no_data">${isZh ? '無新推播' : 'No recent pushes'}</div>`;
        return;
      }
      // Stash full text on each row's data attribute for the FLASH button to read.
      list.innerHTML = items.map((it, idx) => {
        const text = UI.escapeHTML(it.text || '');
        const rawText = (it.text || '').replace(/"/g, '&quot;');
        const time = UI.escapeHTML(relTime(it.time_iso));
        const tickers = (it.tickers || []).map(tk => `
          <span class="text-[10px] font-bold px-2 py-0.5 rounded bg-amber-500/15 text-amber-400 border border-amber-500/30">
            ${UI.escapeHTML(tk)}
          </span>`).join('');
        const flashLabel = isZh ? '⚡ FLASH' : '⚡ FLASH';
        const flashTitle = isZh ? '送 FLASH 分析這則推播' : 'Run FLASH on this push';
        return `
          <div class="border-l-2 border-amber-500/40 pl-3 py-1.5 hover:border-amber-400 transition-all" data-futu-row="${idx}">
            <div class="flex items-center gap-2 mb-1">
              <span class="text-[9px] font-mono text-zinc-500">${time}</span>
              <div class="flex flex-wrap gap-1">${tickers}</div>
              <button class="futu-flash-btn ml-auto text-[10px] font-bold px-2.5 py-1 rounded border border-amber-500/40 text-amber-400 hover:bg-amber-500 hover:text-black hover:border-amber-500 transition-all"
                      data-headline="${rawText}" title="${flashTitle}">
                ${flashLabel}
              </button>
            </div>
            <div class="text-[11px] leading-relaxed" style="color:var(--text-main)">${text}</div>
          </div>`;
      }).join('');

      list.querySelectorAll('.futu-flash-btn').forEach(btn => {
        btn.addEventListener('click', () => {
          // Decode HTML entities back to original quotes for the prompt
          const headline = (btn.dataset.headline || '').replace(/&quot;/g, '"');
          if (!headline) return;
          window.goFlashText(headline);
        });
      });
    }

    async function load() {
      try {
        if (statusEl) statusEl.textContent = '...';
        const r = await fetch('/api/futu-notifications?limit=5', { cache: 'no-store' });
        const data = await r.json();
        const isZh = UI.currentLang === 'zh';
        if (!data.available) {
          list.innerHTML = `<div class="text-[11px] text-zinc-500 italic" data-i18n="futu_unavailable">${isZh ? '富途客戶端未安裝或無資料' : 'Futu client not installed / no data'}</div>`;
          if (statusEl) statusEl.textContent = '';
          if (filterStatsEl) filterStatsEl.textContent = '';
          return;
        }
        renderItems(data.notifications || []);
        if (statusEl) statusEl.textContent = (isZh ? '已更新 ' : 'updated ') + new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
        if (filterStatsEl) {
          const filt = data.filtered_count || 0;
          filterStatsEl.textContent = filt > 0
            ? `· ${isZh ? '已過濾' : 'filtered'} ${filt} ${isZh ? '則 HK/A 股' : 'HK/CN'}`
            : '';
        }
      } catch (e) {
        const isZh = UI.currentLang === 'zh';
        list.innerHTML = `<div class="text-[11px] text-red-500">${UI.escapeHTML((isZh ? '載入失敗：' : 'Load failed: ') + e.message)}</div>`;
        if (statusEl) statusEl.textContent = '';
      }
      if (window.lucide) lucide.createIcons();
    }

    reloadBtn?.addEventListener('click', load);
    load();
    setInterval(load, 60000);
  })();

  UI.boot('news', { translate: applyTranslations, reload: loadNews });
  loadNews();
});
