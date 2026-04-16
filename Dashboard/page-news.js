/**
 * page-news.js — News page presenter (ARCH-8)
 * Depends on: utils.js (window.UI, window.logToUI), i18n.js, data-store.js (window.DataStore)
 */

document.addEventListener('DOMContentLoaded', () => {
  UI.logToUI("Initializing System...");

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
    if (lastSync && /^LAST SYNC: NONE$/i.test(lastSync.textContent)) {
      lastSync.textContent = t.news_page?.last_sync_none || 'LAST SYNC: NONE';
    }
    const brList = document.getElementById('binary-risks-list');
    if (brList && brList.firstElementChild?.classList?.contains('animate-pulse')) {
      brList.innerHTML = `<div class="text-xs text-zinc-600 animate-pulse">${t.news_page?.loading || 'Loading...'}</div>`;
    }
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
              <div class="text-[10px] font-mono text-zinc-500">${item.date || ''}</div>
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
      document.getElementById('last-sync-time').textContent = `${t.last_sync}: ${data.last_updated || 'N/A'}`;

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

  // ── Review Filter Tabs ───────────────────────────────────────
  let activeNewsFilter = 'all';

  function applyNewsFilter() {
    const cards = document.querySelectorAll('#news-feed-detailed > .glass-card');
    cards.forEach(c => {
      const st = c.dataset.reviewStatus || 'reviewed';
      if (activeNewsFilter === 'all') c.style.display = '';
      else c.style.display = (st === activeNewsFilter) ? '' : 'none';
    });
  }

  document.getElementById('news-filter-tabs')?.addEventListener('click', e => {
    const btn = e.target.closest('[data-filter]');
    if (!btn) return;
    activeNewsFilter = btn.dataset.filter;
    document.querySelectorAll('.news-filter-tab').forEach(b => {
      const on = b.dataset.filter === activeNewsFilter;
      b.className = `news-filter-tab px-4 py-1.5 rounded-lg text-xs font-bold border transition-all ${
        on ? 'bg-emerald-500 text-black border-emerald-500'
           : 'border-zinc-200 dark:border-zinc-800 text-zinc-500 hover:border-zinc-400'}`;
    });
    applyNewsFilter();
  });

  // Init tab styles
  document.querySelectorAll('.news-filter-tab').forEach(b => {
    const on = b.dataset.filter === activeNewsFilter;
    b.className = `news-filter-tab px-4 py-1.5 rounded-lg text-xs font-bold border transition-all ${
      on ? 'bg-emerald-500 text-black border-emerald-500'
         : 'border-zinc-200 dark:border-zinc-800 text-zinc-500 hover:border-zinc-400'}`;
  });

  // Copy review prompt to clipboard
  window.copyReviewPrompt = async function(btnEl, headline) {
    const prompt = `新聞分析 審核 "${headline}"`;
    await UI.copyToClipboard(prompt);
    const t = window.i18n?.[UI.currentLang] || {};
    const np = t.news_page || {};
    UI.showToast(
      np.review_toast || (UI.currentLang === 'zh'
        ? `<span class="text-emerald-400 font-bold">「${prompt}」</span><br>已複製到剪貼簿，貼回 Claude Code 執行正式委員會審核`
        : `<span class="text-emerald-400 font-bold">"${prompt}"</span><br>Copied — paste into Claude Code for formal committee review`),
      'info', 5500
    );
  };

  // Shortcut to toggle Debug Console: Shift + D
  document.addEventListener('keydown', (e) => {
    if (e.shiftKey && e.key === 'D') {
      document.getElementById('debug-console')?.classList.toggle('hidden');
    }
  });

  document.getElementById('refresh-news').addEventListener('click', async () => {
    // Dual behavior: reload data.json immediately + copy DIGEST prompt to clipboard
    // so user can paste into Claude Code to trigger a fresh v2 news DIGEST run.
    await loadNews();
    const prompt = '新聞分析 DIGEST';
    await UI.copyToClipboard(prompt);
    const t = window.i18n?.[UI.currentLang] || {};
    const np = t.news_page || {};
    const msg = np.digest_toast ||
      (UI.currentLang === 'zh'
        ? `資料已重新載入。<br><span class="text-emerald-400 font-bold">「${prompt}」</span> 已複製到剪貼簿，<br>貼回 Claude Code 執行完整 DIGEST 更新（需 1–2 分鐘）`
        : `Dashboard reloaded.<br><span class="text-emerald-400 font-bold">"${prompt}"</span> copied to clipboard.<br>Paste into Claude Code to run full DIGEST (1–2 min).`);
    UI.showToast(msg, 'info', 6000);
  });

  UI.boot('news', { translate: applyTranslations, reload: loadNews });
  loadNews();
});
