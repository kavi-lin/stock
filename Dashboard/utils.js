/**
 * utils.js — INTEL COMMAND Shared Utilities
 * ARCH-1: theme / lang / log / viewReport / market status / icons / sidebar
 * All shared state & logic lives under window.UI
 */
(function () {
  'use strict';

  // Semantic release tag shown in sidebar footer. Bump on meaningful releases.
  // Cache-busting is handled separately by dashboard_server.py (mtime injection).
  const VERSION = 'V2.19.0';

  // V1.71.x — group field enables sectioned sidebar layout
  const NAV_ITEMS = [
    { id: 'index',     href: 'index.html',     icon: 'layout-dashboard', i18n: 'nav_dash',      zh: '總體儀表板', group: 'market' },
    { id: 'sector',    href: 'sector.html',    icon: 'pie-chart',        i18n: 'nav_sector',    zh: '產業掃描',   group: 'market' },
    { id: 'news',      href: 'news.html',      icon: 'newspaper',        i18n: 'nav_news',      zh: '即時新聞',   group: 'market' },

    { id: 'momentum',  href: 'momentum.html',  icon: 'trending-up',      i18n: 'nav_momentum',  zh: '動能選股',   group: 'stock' },
    { id: 'radar',     href: 'radar.html',     icon: 'radar',            i18n: 'nav_radar',     zh: '短期雷達',   group: 'stock' },
    { id: 'earnings',  href: 'earnings.html',  icon: 'bar-chart-3',      i18n: 'nav_earnings',  zh: '財報分析',   group: 'stock' },

    { id: 'decisions', href: 'decisions.html', icon: 'gavel',            i18n: 'nav_decisions', zh: '決策中心',   group: 'portfolio' },
    { id: 'calendar',  href: 'calendar.html',  icon: 'calendar-days',    i18n: 'nav_calendar',  zh: '決策日曆',   group: 'portfolio' },
  ];

  const NAV_GROUPS = [
    { key: 'market',    zh: '市場',  en: 'MARKET',    icon: 'globe-2' },
    { key: 'stock',     zh: '個股',  en: 'STOCK',     icon: 'target' },
    { key: 'portfolio', zh: '組合',  en: 'PORTFOLIO', icon: 'briefcase' },
  ];

  window.UI = {
    VERSION,

    // ── Theme ────────────────────────────────────────────────────────────
    currentTheme: localStorage.getItem('dash_theme') || 'dark',

    initTheme() {
      document.documentElement.setAttribute('data-theme', UI.currentTheme);
      UI.currentTheme === 'dark'
        ? document.documentElement.classList.add('dark')
        : document.documentElement.classList.remove('dark');
      const ic = document.getElementById('theme-icon');
      if (ic) {
        ic.setAttribute('data-lucide', UI.currentTheme === 'dark' ? 'moon' : 'sun');
        UI.icons();
      }
    },

    toggleTheme() {
      UI.currentTheme = UI.currentTheme === 'dark' ? 'light' : 'dark';
      localStorage.setItem('dash_theme', UI.currentTheme);
      UI.initTheme();
      if (UI._onThemeChange) UI._onThemeChange();
    },

    // ── Language ─────────────────────────────────────────────────────────
    currentLang: localStorage.getItem('dash_lang') || 'zh',

    toggleLang() {
      UI.currentLang = UI.currentLang === 'zh' ? 'en' : 'zh';
      localStorage.setItem('dash_lang', UI.currentLang);
      UI.applyNavTranslations();
      if (UI._onLangChange) UI._onLangChange();
    },

    // Only the nav/shared parts — page-specific applyTranslations stays per-page
    applyNavTranslations() {
      const t = window.i18n?.[UI.currentLang];
      if (!t) return;
      const nav = t.nav || {};
      const langEl = document.getElementById('lang-text');
      if (langEl) langEl.textContent = UI.currentLang === 'zh' ? 'English' : '繁體中文';
      document.querySelectorAll('[data-i18n^="nav_"]').forEach(el => {
        const key = el.getAttribute('data-i18n').replace('nav_', '');
        if (nav[key]) el.textContent = nav[key];
      });
      // V1.71.x — sidebar group section labels + brand subtitle (custom data attrs)
      document.querySelectorAll('[data-nav-group], [data-nav-brand-sub]').forEach(el => {
        el.textContent = UI.currentLang === 'zh'
          ? (el.dataset.zh || el.textContent)
          : (el.dataset.en || el.textContent);
      });
    },

    // ── Icons (rAF-debounced) ─────────────────────────────────────────────
    _iconsPending: false,
    icons() {
      if (UI._iconsPending) return;
      UI._iconsPending = true;
      requestAnimationFrame(() => {
        try { lucide.createIcons(); } catch (e) { console.warn('[UI.icons]', e); }
        UI._iconsPending = false;
      });
    },

    // ── Toast (minimal, theme-aware, manually dismissible) ──────────────
    // Defaults tuned per type: info 6s / warn 8s / error 10s — long enough to
    // actually read. A small ✕ on the right lets the user close early.
    // Pass ms=0 to make the toast persistent until manually dismissed.

    // Renders a coloured status dot into `el` based on how old `lastUpdated` is,
    // and attaches a hover tooltip explaining the colour + sync time.
    applySyncLight(el, lastUpdated, customWhat, sourceTimestamps) {
      if (!el) return;
      const nowMs  = Date.now();
      const syncMs = lastUpdated ? new Date(lastUpdated.replace(' ', 'T')).getTime() : 0;
      const ageMin = syncMs ? Math.floor((nowMs - syncMs) / 60000) : Infinity;

      // Compute per-source ages if provided; each item: { label, ts, ttl?, hint? }
      // ttl = stale threshold in minutes (default 180). hint = action text shown when stale.
      let staleSources = [];
      if (Array.isArray(sourceTimestamps)) {
        sourceTimestamps.forEach(({ label, ts, ttl = 180, hint }) => {
          if (!ts) return;
          const ms = new Date(ts.length <= 10 ? ts + 'T00:00:00' : ts.replace(' ', 'T')).getTime();
          if (!ms || isNaN(ms)) return;
          const srcMin = Math.floor((nowMs - ms) / 60000);
          staleSources.push({ label, srcMin, ttl, hint });
        });
      }
      // stale = exceeded its own ttl
      const staleSrcItems = staleSources.filter(s => s.srcMin > s.ttl);
      const oldestSrcMin  = staleSrcItems.length
        ? Math.max(...staleSrcItems.map(s => s.srcMin))
        : 0;

      let color, label, reason, sourceNote = '';
      if (!syncMs || ageMin > 720) {
        color  = '#ef4444';
        label  = UI.currentLang === 'zh' ? '資料過期' : 'Data stale';
        reason = ageMin === Infinity
          ? (UI.currentLang === 'zh' ? '尚未同步任何資料，請執行 bridge.py' : 'No sync yet — run bridge.py')
          : (UI.currentLang === 'zh' ? `已超過 ${Math.floor(ageMin/60)} 小時未更新` : `Over ${Math.floor(ageMin/60)}h since last sync`);
      } else if (ageMin > 180) {
        color  = '#f59e0b';
        label  = UI.currentLang === 'zh' ? '資料稍舊' : 'Data aging';
        reason = UI.currentLang === 'zh'
          ? `${Math.floor(ageMin/60)} 小時 ${ageMin % 60} 分前同步，建議重新執行 bridge.py`
          : `Synced ${Math.floor(ageMin/60)}h ${ageMin % 60}m ago — consider re-running bridge.py`;
      } else if (oldestSrcMin > 0) {
        // data.json is fresh but some source caches exceeded their individual ttl
        color  = '#f97316';
        label  = UI.currentLang === 'zh' ? '來源已過期' : 'Sources stale';
        reason = UI.currentLang === 'zh'
          ? `data.json 已更新，但部分來源 cache 超過 ${Math.floor(oldestSrcMin/60)} 小時未更新`
          : `data.json fresh, but source caches ${Math.floor(oldestSrcMin/60)}h+ old`;
        const staleList = staleSrcItems
          .map(s => {
            const h = Math.floor(s.srcMin / 60), m = s.srcMin % 60;
            const hintHtml = s.hint ? `<br><span style="color:#6b7280">→ ${s.hint}</span>` : '';
            return `<span style="color:#fca5a5">${s.label}</span>：${h}h${m}m 前${hintHtml}`;
          }).join('<br>');
        if (staleList) sourceNote = `<div style="color:#a1a1aa;font-size:10px;margin-top:4px;border-top:1px solid #3f3f46;padding-top:4px">${staleList}</div>`;
      } else {
        color  = '#22c55e';
        label  = UI.currentLang === 'zh' ? '資料新鮮' : 'Data fresh';
        reason = ageMin < 2
          ? (UI.currentLang === 'zh' ? '剛剛同步完成' : 'Just synced')
          : (UI.currentLang === 'zh' ? `${ageMin} 分鐘前同步` : `Synced ${ageMin}m ago`);
      }

      const syncTimeStr = lastUpdated || (UI.currentLang === 'zh' ? '未知' : 'unknown');
      const lastSyncLbl = UI.currentLang === 'zh' ? '上次同步' : 'Last sync';
      const whatLbl = customWhat || (UI.currentLang === 'zh'
        ? '同步內容：廣度分析 / FTD / 市場頂部 / 產業掃描 / 動能選股等所有 cache → data.json'
        : 'Syncs: breadth / FTD / market top / sector scan / momentum → data.json');
      const tipHtml = `
        <div style="font-weight:700;color:${color};margin-bottom:4px">${label}</div>
        <div style="color:#d4d4d8;margin-bottom:6px;font-size:11px">${reason}</div>
        <div style="color:#a1a1aa;font-size:10px;margin-bottom:4px">${whatLbl}</div>
        <div style="color:#71717a;font-size:10px">${lastSyncLbl}：${syncTimeStr}</div>
        ${sourceNote}`;

      el.innerHTML = `<span style="display:inline-block;width:8px;height:8px;border-radius:50%;background:${color};box-shadow:0 0 5px ${color}99;flex-shrink:0"></span>`;
      el.style.cssText = 'display:inline-flex;align-items:center;cursor:default';
      el._syncTip = tipHtml;

      let tip = document.getElementById('_sync_tooltip');
      if (!tip) {
        tip = document.createElement('div');
        tip.id = '_sync_tooltip';
        tip.style.cssText = 'position:fixed;z-index:9999;background:var(--bg-card,#18181b);border:1px solid #3f3f46;border-radius:10px;padding:10px 14px;font-size:12px;line-height:1.6;pointer-events:none;opacity:0;transition:opacity 0.12s;max-width:240px';
        document.body.appendChild(tip);
      }
      el.onmouseenter = function(e) {
        tip.innerHTML = this._syncTip;
        tip.style.opacity = '1';
        const r = this.getBoundingClientRect();
        tip.style.top  = (r.bottom + 8) + 'px';
        tip.style.left = Math.max(8, r.right - 240) + 'px';
      };
      el.onmouseleave = () => { tip.style.opacity = '0'; };
    },

    showToast(msg, type = 'info', ms = null) {
      if (ms === null) ms = type === 'error' ? 10000 : type === 'warn' ? 8000 : 6000;
      let host = document.getElementById('ui-toast-host');
      if (!host) {
        host = document.createElement('div');
        host.id = 'ui-toast-host';
        host.className = 'fixed top-5 right-5 z-[200] flex flex-col gap-2 pointer-events-none';
        document.body.appendChild(host);
      }
      const accent = type === 'error' ? 'border-l-red-500'
                   : type === 'warn'  ? 'border-l-yellow-500'
                                      : 'border-l-emerald-500';
      const icon = type === 'error' ? 'alert-circle'
                 : type === 'warn'  ? 'alert-triangle'
                                    : 'info';
      const iconColor = type === 'error' ? 'text-red-500'
                      : type === 'warn'  ? 'text-yellow-500'
                                         : 'text-emerald-500';
      const el = document.createElement('div');
      el.className =
        `pointer-events-auto max-w-sm rounded-lg border border-l-4 ${accent} ` +
        `border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-900 ` +
        `shadow-lg text-xs animate-[slideIn_.3s_ease] flex items-start gap-2 pl-3 pr-2 py-2.5`;
      el.innerHTML = `
        <i data-lucide="${icon}" class="w-3.5 h-3.5 shrink-0 mt-0.5 ${iconColor}"></i>
        <div class="flex-1 text-zinc-800 dark:text-zinc-200 leading-snug break-words">${msg}</div>
        <button class="toast-close shrink-0 text-zinc-400 hover:text-red-500 transition-colors -mt-0.5" title="Close">
          <i data-lucide="x" class="w-3 h-3"></i>
        </button>`;
      host.appendChild(el);
      if (window.lucide) lucide.createIcons();

      const close = () => {
        if (el._closed) return;
        el._closed = true;
        el.style.opacity = '0';
        el.style.transition = 'opacity .25s';
        setTimeout(() => el.remove(), 250);
      };
      el.querySelector('.toast-close').onclick = close;

      if (ms > 0) {
        setTimeout(close, ms);
      }
    },

    copyToClipboard(text) {
      if (navigator.clipboard?.writeText) return navigator.clipboard.writeText(text);
      // Fallback for insecure contexts
      const ta = document.createElement('textarea');
      ta.value = text; ta.style.position = 'fixed'; ta.style.opacity = '0';
      document.body.appendChild(ta); ta.focus(); ta.select();
      try { document.execCommand('copy'); } finally { ta.remove(); }
      return Promise.resolve();
    },

    // Prefix line for protocol-launch confirm() dialogs that depend on caches
    // produced by daily_update.sh (breadth/ftd/market_top/macro/sector_intel).
    // Reads /api/preflight and reports breadth cache age as proxy for last
    // successful daily_update.sh run (breadth is step 1).
    async dailyUpdatePrefix() {
      const isZh = UI.currentLang === 'zh';
      try {
        const r = await fetch('/api/preflight');
        if (!r.ok) return '';
        const d = await r.json();
        const breadth = (d.items || []).find(it => it.key === 'breadth');
        if (!breadth || breadth.status === 'MISSING') {
          return isZh ? '⚠️ daily_update 未跑過\n\n' : '⚠️ daily_update never ran\n\n';
        }
        return isZh
          ? `📌 daily_update：${breadth.age_str} 前\n\n`
          : `📌 daily_update: ${breadth.age_str} ago\n\n`;
      } catch (_) { return ''; }
    },

    // ── Persistent Debug Logger (localStorage ring buffer) ───────────────
    // Previously: logs were DOM-only, so switching pages wiped them. Now every
    // log line is appended to localStorage (cap 300) and replayed on page boot.
    // Additional persistent sources (bridge.py handshake + protocol state) are
    // monitored globally from the IIFE tail below.
    _LOG_KEY:  'ui_log_v1',
    _LOG_CAP:  300,

    _logBufferLoad() {
      try {
        const raw = localStorage.getItem(UI._LOG_KEY);
        return raw ? JSON.parse(raw) : [];
      } catch { return []; }
    },
    _logBufferSave(buf) {
      try {
        if (buf.length > UI._LOG_CAP) buf = buf.slice(-UI._LOG_CAP);
        localStorage.setItem(UI._LOG_KEY, JSON.stringify(buf));
      } catch {}
    },
    _logRenderLine(entry) {
      const out = document.getElementById('log-output');
      if (!out) return;
      const color = entry.type === 'error' ? 'text-red-500'
                   : entry.type === 'warn' ? 'text-yellow-500'
                   : entry.type === 'success' ? 'text-emerald-500'
                   : 'text-zinc-500';
      const line = document.createElement('div');
      const pageTag = entry.page ? `<span class="text-zinc-700">[${entry.page}]</span> ` : '';
      line.innerHTML = `<span class="text-zinc-600">[${entry.ts}]</span> ${pageTag}<span class="${color}">${entry.msg}</span>`;
      out.appendChild(line);
      // Auto-scroll to bottom so newest is visible
      out.scrollTop = out.scrollHeight;
    },

    logToUI(msg, type = 'info') {
      const entry = {
        ts:   new Date().toLocaleTimeString(),
        page: document.body?.dataset?.page || null,
        type,
        msg:  String(msg),
      };
      const buf = UI._logBufferLoad();
      buf.push(entry);
      UI._logBufferSave(buf);
      UI._logRenderLine(entry);
    },

    // Render entire ring buffer into the console (called on DOMContentLoaded)
    replayLog() {
      const out = document.getElementById('log-output');
      if (!out) return;
      out.innerHTML = '';
      const buf = UI._logBufferLoad();
      for (const entry of buf) UI._logRenderLine(entry);
    },

    clearLog() {
      try { localStorage.removeItem(UI._LOG_KEY); } catch {}
      const out = document.getElementById('log-output');
      if (out) out.innerHTML = '<div class="text-zinc-600 text-[9px]">(log cleared)</div>';
    },

    // ── Report Modal ─────────────────────────────────────────────────────
    async viewReport(path) {
      if (!path || path === 'null') { alert('Report pending...'); return; }
      const modal   = document.getElementById('report-modal');
      const content = document.getElementById('report-content');
      if (!modal || !content) return;
      modal.classList.remove('hidden');
      content.innerHTML = '<div class="flex items-center justify-center h-full p-20 animate-pulse text-zinc-500">Loading...</div>';
      try {
        const full = '../' + path + '?t=' + Date.now();
        if (path.endsWith('.html')) {
          content.innerHTML = `<iframe src="${full}" class="w-full h-full border-0 bg-white rounded-lg"></iframe>`;
        } else {
          const md = await (await fetch(full)).text();
          const isDark = document.documentElement.classList.contains('dark');
          const proseTheme = isDark
            ? 'prose-invert text-zinc-300 prose-headings:text-zinc-100 prose-strong:text-zinc-100 prose-code:text-emerald-400 prose-a:text-emerald-400'
            : 'text-zinc-800 prose-headings:text-zinc-900 prose-strong:text-zinc-900 prose-code:text-emerald-700 prose-a:text-emerald-700 prose-li:text-zinc-700 prose-p:text-zinc-700';
          content.innerHTML = `<div class="p-8 prose prose-zinc max-w-none ${proseTheme}">${marked.parse(md)}</div>`;
        }
      } catch (e) {
        content.innerHTML = `<div class="p-10 text-center text-red-500">Failed: ${UI.escapeHTML(e.message)}</div>`;
      }
    },

    // ── Market Status (NYSE hours) ────────────────────────────────────────
    updateMarketStatus() {
      const el = document.getElementById('market-status-text');
      if (!el) return;
      const d = new Date(new Date().toLocaleString('en-US', { timeZone: 'America/New_York' }));
      const mins = d.getHours() * 60 + d.getMinutes();
      const isWeekday = d.getDay() >= 1 && d.getDay() <= 5;
      const isOpen = isWeekday && mins >= 570 && mins < 960;
      el.textContent = isOpen ? (UI.currentLang === 'zh' ? '開盤中' : 'OPEN')
                               : (UI.currentLang === 'zh' ? '已收盤' : 'CLOSED');
      el.className = 'text-xs font-bold ' + (isOpen ? 'text-green-400' : 'text-red-500');
    },

    // ── Fetch cancellation detector ────────────────────────────────────
    // Browsers abort in-flight fetches when the user navigates away.
    // Chrome throws AbortError (clean); Safari surfaces "Load failed" or
    // "The string did not match the expected pattern" (various messages).
    // Treating these as real errors spams the log with noise from page-unload
    // cleanup that the user can't do anything about.
    isFetchCancellation(e) {
      if (!e) return false;
      if (e.name === 'AbortError') return true;
      const msg = String(e.message || '');
      return /Load failed|did not match the expected pattern|NetworkError when attempting/i.test(msg);
    },

    // ── HTML Escape ────────────────────────────────────────────────────────
    escapeHTML(str) {
      return String(str ?? '')
        .replace(/&/g, '&amp;').replace(/</g, '&lt;')
        .replace(/>/g, '&gt;').replace(/"/g, '&quot;');
    },

    // ── Sidebar Render (V1.71.x — grouped, polished active, compact footer) ─
    renderSidebar(activePage) {
      const aside = document.getElementById('sidebar');
      if (!aside) return;
      const isZh = UI.currentLang === 'zh';

      // Build grouped nav HTML
      const groupsHTML = NAV_GROUPS.map(g => {
        const items = NAV_ITEMS.filter(n => n.group === g.key);
        if (!items.length) return '';
        const itemsHTML = items.map(n => `
          <a href="${n.href}" class="sidebar-item${n.id === activePage ? ' active' : ''}">
            <i data-lucide="${n.icon}" class="sidebar-item-icon w-4 h-4"></i>
            <span data-i18n="${n.i18n}">${n.zh}</span>
          </a>`).join('');
        return `
          <div class="sidebar-group">
            <div class="sidebar-group-label" data-nav-group="${g.key}" data-zh="${g.zh}" data-en="${g.en}">${isZh ? g.zh : g.en}</div>
            ${itemsHTML}
          </div>`;
      }).join('');

      aside.innerHTML = `
        <!-- Header: brand + theme toggle (V1.71.x — AUGUR / 識微 brand) -->
        <div class="sidebar-header">
          <div class="sidebar-brand">
            <div class="sidebar-brand-mark" aria-label="AUGUR logo" title="AUGUR · 識微">
              <!-- Augur's-eye diamond / compass: rotated square + cross + concentric pupil -->
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke-linejoin="round">
                <!-- Outer diamond (rotated square) -->
                <path d="M12 2.5 L21.5 12 L12 21.5 L2.5 12 Z" fill="#ecfdf5" stroke="#052e16" stroke-width="1.8"/>
                <!-- Compass cross -->
                <path d="M12 6 L12 18 M6 12 L18 12" stroke="#065f46" stroke-width="1.3" stroke-linecap="round"/>
                <!-- Augur's eye (concentric pupil) -->
                <circle cx="12" cy="12" r="2.6" fill="#065f46"/>
                <circle cx="12" cy="12" r="1.05" fill="#fef3c7"/>
              </svg>
            </div>
            <div class="sidebar-brand-textwrap">
              <h1 class="sidebar-brand-text">A<span class="sidebar-brand-accent">UGUR</span></h1>
              <div class="sidebar-brand-sub" data-nav-brand-sub data-zh="識微 · AI 投資委員會" data-en="AI Investment Committee">${isZh ? '識微 · AI 投資委員會' : 'AI Investment Committee'}</div>
            </div>
          </div>
          <button id="theme-toggle" class="sidebar-icon-btn" title="${isZh ? '切換主題' : 'Toggle theme'}">
            <i data-lucide="moon" class="w-3.5 h-3.5" id="theme-icon"></i>
          </button>
        </div>

        <!-- Nav (grouped) -->
        <nav class="sidebar-nav">${groupsHTML}</nav>

        <!-- Footer: prominent risk pill + icon row + version -->
        <div class="sidebar-footer">
          <button id="risk-toggle" class="sidebar-risk" title="${isZh ? '點擊循環 LOW → MEDIUM → HIGH' : 'Click to cycle LOW → MEDIUM → HIGH'}">
            <span class="sidebar-risk-label">${isZh ? '風險容忍' : 'RISK'}</span>
            <span id="risk-chip" class="sidebar-risk-chip">${UI.riskTolerance}</span>
          </button>
          <div class="sidebar-icon-row">
            <button id="lang-toggle" class="sidebar-icon-btn sidebar-icon-btn-wide" title="${isZh ? '切換語言' : 'Toggle language'}">
              <i data-lucide="languages" class="w-3.5 h-3.5"></i>
              <span id="lang-text" class="text-[10px] font-bold">English</span>
            </button>
            <button id="show-logs" class="sidebar-icon-btn" title="${isZh ? '系統日誌' : 'System logs'}">
              <i data-lucide="terminal" class="w-3.5 h-3.5"></i>
            </button>
          </div>
          <div class="sidebar-version">${VERSION}</div>
        </div>`;

      // Wire sidebar buttons immediately after DOM insertion
      document.getElementById('theme-toggle')?.addEventListener('click', () => UI.toggleTheme());
      document.getElementById('lang-toggle')?.addEventListener('click',  () => UI.toggleLang());
      document.getElementById('show-logs')?.addEventListener('click',    () =>
        document.getElementById('debug-console')?.classList.toggle('hidden'));
      document.getElementById('risk-toggle')?.addEventListener('click',  () => UI.cycleRiskTolerance());
      UI._paintRiskChip();
    },

    // ── Risk Tolerance (sent with every invest protocol invocation) ──────
    // Stored in localStorage so the choice survives page nav. Cycles LOW → MEDIUM → HIGH.
    get riskTolerance() {
      const v = (localStorage.getItem('dash_risk_tolerance') || '').toUpperCase();
      return ['LOW', 'MEDIUM', 'HIGH'].includes(v) ? v : 'MEDIUM';
    },
    cycleRiskTolerance() {
      const order = ['LOW', 'MEDIUM', 'HIGH'];
      const next  = order[(order.indexOf(UI.riskTolerance) + 1) % 3];
      localStorage.setItem('dash_risk_tolerance', next);
      UI._paintRiskChip();
      UI.showToast((UI.currentLang === 'zh' ? '風險容忍度：' : 'Risk tolerance: ') + next, 'info', 2500);
    },
    _paintRiskChip() {
      const chip = document.getElementById('risk-chip');
      if (!chip) return;
      const v = UI.riskTolerance;
      chip.textContent = v;
      chip.className = 'sidebar-risk-chip risk-' + v.toLowerCase();
    },

    // ── Page Boot ──────────────────────────────────────────────────────────
    // Call once per page: UI.boot(activePage, { translate?, reload?, onThemeChange? })
    //   translate : page-specific applyTranslations fn (called on lang change)
    //   reload    : page-specific data load fn (called on lang change AFTER translate)
    //   onThemeChange: extra action on theme toggle (e.g. re-render chart)
    boot(activePage, { translate = null, reload = null, onThemeChange = null } = {}) {
      UI._onThemeChange = onThemeChange;
      UI._onLangChange  = () => {
        UI.applyNavTranslations();
        if (translate) translate();
        if (reload)    reload();
      };

      UI.renderSidebar(activePage);
      UI.initTheme();
      UI.applyNavTranslations();
      // Run page-specific translations once at boot so hardcoded HTML labels
      // reflect the current language on first paint (not only on lang toggle).
      if (translate) {
        try { translate(); } catch (e) { UI.logToUI('translate error: ' + e.message, 'error'); }
      }

      // Modal ESC / close button
      document.getElementById('close-modal')?.addEventListener('click', () =>
        document.getElementById('report-modal')?.classList.add('hidden'));
      document.addEventListener('keydown', e => {
        if (e.key === 'Escape') document.getElementById('report-modal')?.classList.add('hidden');
      });

      // Catch & show JS errors in debug console
      window.onerror = (msg) => {
        UI.logToUI(String(msg), 'error');
        document.getElementById('debug-console')?.classList.remove('hidden');
      };

      UI.icons();
    },
  };

  // ── Global aliases (backward-compat for onclick="viewReport(...)" in rendered cards) ──
  window.viewReport = (path) => UI.viewReport(path);
  window.logToUI    = (msg, type) => UI.logToUI(msg, type);

  // ── Persistent log: replay on page load + inject Clear button ────────────
  document.addEventListener('DOMContentLoaded', () => {
    UI.replayLog();

    // Inject a "Clear" button into the debug console header if not present
    const console_ = document.getElementById('debug-console');
    if (console_ && !console_.querySelector('.log-clear-btn')) {
      const header = console_.querySelector('.flex.items-center.justify-between');
      if (header) {
        const btn = document.createElement('button');
        btn.className = 'log-clear-btn text-[9px] font-bold uppercase tracking-widest text-zinc-500 hover:text-red-400 transition-colors mr-2';
        btn.textContent = 'Clear';
        btn.title = 'Clear persistent log buffer';
        btn.onclick = () => UI.clearLog();
        // insert before the X close button (last child of header-right group)
        const rightGroup = header.lastElementChild;
        if (rightGroup && rightGroup.tagName === 'BUTTON') {
          header.insertBefore(btn, rightGroup);
        } else {
          header.appendChild(btn);
        }
      }
    }
  });

  // ── Bridge.py handshake monitor (persistent log across pages) ────────────
  // Polls /api/refresh_status every 5s. Emits a log entry ONLY when the server
  // has reported a new last_ok or new last_error since we last logged (dedup via
  // localStorage-backed sentinels so switching pages won't re-log the same event).
  const BRIDGE_SEEN_OK  = 'bridge_last_ok_logged';
  const BRIDGE_SEEN_ERR = 'bridge_last_err_logged';
  async function pollBridge() {
    try {
      const r = await fetch('/api/refresh_status');
      if (!r.ok) return;
      const s = await r.json();
      const seenOk  = localStorage.getItem(BRIDGE_SEEN_OK);
      const seenErr = localStorage.getItem(BRIDGE_SEEN_ERR);
      if (s.last_ok && s.last_ok !== seenOk) {
        UI.logToUI(`bridge.py OK — ${s.last_reason || 'periodic'} (${s.last_ok.slice(11, 19)})`, 'success');
        localStorage.setItem(BRIDGE_SEEN_OK, s.last_ok);
      }
      if (s.last_error) {
        // Key error log by the error string itself to avoid loss when timestamp absent
        const errSig = (s.last_error || '').slice(0, 200);
        if (errSig && errSig !== seenErr) {
          UI.logToUI(`bridge.py ERROR — ${errSig}`, 'error');
          localStorage.setItem(BRIDGE_SEEN_ERR, errSig);
        }
      }
    } catch { /* server unreachable — silent */ }
  }
  setInterval(pollBridge, 5000);
  setTimeout(pollBridge, 1000);

  // ── Protocol (invest/flash/sector) handshake monitor ─────────────────────
  // Emits log on state transitions: running → done / error / cancelled.
  const PROTO_SEEN_JOB = 'protocol_last_job_logged';
  async function pollProtocolStateMonitor() {
    try {
      const r = await fetch('/api/run-protocol/status');
      if (!r.ok) return;
      const s = await r.json();
      const seenJob = localStorage.getItem(PROTO_SEEN_JOB);
      const thisJob = s.job_id ? `${s.job_id}:${s.status}` : null;
      if (!thisJob || thisJob === seenJob) return;
      // Only log terminal states (avoid spamming "running" every 3s)
      if (['done', 'error', 'cancelled'].includes(s.status)) {
        const type = s.status === 'done' ? 'success' : 'error';
        const elapsed = s.elapsed_sec || 0;
        const m = Math.floor(elapsed / 60), sec = elapsed % 60;
        const timeStr = `${m}:${String(sec).padStart(2,'0')}`;
        const suffix = s.status === 'done' ? `completed in ${timeStr}` : (s.error || s.status);
        UI.logToUI(`protocol ${s.name} [${s.job_id}] — ${suffix}`, type);
        localStorage.setItem(PROTO_SEEN_JOB, thisJob);
        // Force DataStore refresh so earnings/sector cards reflect new cache immediately
        if (s.status === 'done') setTimeout(() => window.DataStore?.refresh(), 3000);
      } else if (s.status === 'running' && thisJob !== seenJob) {
        // Log start once
        UI.logToUI(`protocol ${s.name} started [${s.job_id}]`, 'info');
        localStorage.setItem(PROTO_SEEN_JOB, thisJob);
      }
    } catch { /* silent */ }
  }
  setInterval(pollProtocolStateMonitor, 3000);
  setTimeout(pollProtocolStateMonitor, 1500);

  // ── V2.7.16 — Global protocol status pill (cross-page persistent indicator) ──
  // Floating bottom-right pill that surfaces current running protocol + queue
  // count on every page so user doesn't lose visibility after navigating away
  // from earnings.html or wherever they queued the job.
  function ensureProtoPill() {
    let pill = document.getElementById('proto-status-pill');
    if (pill) return pill;
    pill = document.createElement('div');
    pill.id = 'proto-status-pill';
    pill.className = 'proto-status-pill hidden';
    pill.innerHTML = `
      <div class="proto-pill-main">
        <span class="proto-pill-icon">🔄</span>
        <div class="proto-pill-text">
          <div class="proto-pill-label" id="proto-pill-label">—</div>
          <div class="proto-pill-meta" id="proto-pill-meta">—</div>
        </div>
        <button class="proto-pill-toggle" id="proto-pill-toggle" title="展開詳情">
          <i data-lucide="chevron-up" class="w-3 h-3"></i>
        </button>
      </div>
      <div class="proto-pill-detail hidden" id="proto-pill-detail"></div>`;
    document.body.appendChild(pill);
    pill.querySelector('#proto-pill-toggle').addEventListener('click', () => {
      const det = pill.querySelector('#proto-pill-detail');
      det.classList.toggle('hidden');
      const ic = pill.querySelector('#proto-pill-toggle i');
      if (ic) ic.setAttribute('data-lucide', det.classList.contains('hidden') ? 'chevron-up' : 'chevron-down');
      if (window.lucide) lucide.createIcons();
    });
    return pill;
  }

  function fmtElapsed(sec) {
    if (sec == null) return '—';
    const m = Math.floor(sec / 60);
    const s = sec % 60;
    if (m === 0) return `${s}s`;
    return `${m}m ${String(s).padStart(2, '0')}s`;
  }

  async function pollProtoPill() {
    try {
      const r = await fetch('/api/protocol-queue', { cache: 'no-store' });
      if (!r.ok) return;
      const state = await r.json();
      const pill = ensureProtoPill();
      const active = state.active;
      const queue = state.queue || [];
      const lbl = pill.querySelector('#proto-pill-label');
      const meta = pill.querySelector('#proto-pill-meta');
      const det = pill.querySelector('#proto-pill-detail');

      if (!active && queue.length === 0) {
        pill.classList.add('hidden');
        pill.classList.remove('proto-pill-running');
        return;
      }
      pill.classList.remove('hidden');

      if (active) {
        const name = active.name || '?';
        const ticker = active.ticker || active.label || '';
        lbl.innerHTML = ticker
          ? `<strong>${name}</strong> · <span class="proto-pill-ticker">${ticker}</span>`
          : `<strong>${name}</strong>`;
        meta.textContent = `running · ${fmtElapsed(active.elapsed_sec)}` +
                           (queue.length ? ` · queue +${queue.length}` : '');
        pill.classList.add('proto-pill-running');
      } else {
        lbl.innerHTML = `<strong>queue</strong>`;
        meta.textContent = `${queue.length} pending`;
        pill.classList.remove('proto-pill-running');
      }

      // Detail panel: list active log_tail (truncated) + pending queue items
      const lines = [];
      if (active) {
        lines.push(`<div class="proto-pill-row"><span class="proto-pill-row-icon">▶</span><span><strong>${active.name}</strong>${active.ticker ? ' · ' + active.ticker : ''} · ${fmtElapsed(active.elapsed_sec)}</span></div>`);
      }
      for (const q of queue.slice(0, 5)) {
        lines.push(`<div class="proto-pill-row"><span class="proto-pill-row-icon">⏳</span><span><strong>${q.name || '?'}</strong>${q.params?.ticker ? ' · ' + q.params.ticker : ''}</span></div>`);
      }
      if (queue.length > 5) lines.push(`<div class="proto-pill-row proto-pill-row-more">+${queue.length - 5} more</div>`);
      det.innerHTML = lines.join('');
    } catch { /* silent */ }
  }
  setInterval(pollProtoPill, 5000);
  setTimeout(pollProtoPill, 1200);

  // ── V2.17.5 — Premarket chain status pill (single unit with 3 sub-rows) ──
  // Surfaces /api/run-premarket-chain/status across every page so when user
  // closes the preflight modal mid-run, they still see daily/news/sector
  // progress as ONE pill (cannot dismiss individual rows — chain is atomic).
  function ensureChainPill() {
    let pill = document.getElementById('chain-status-pill');
    if (pill) return pill;
    pill = document.createElement('div');
    pill.id = 'chain-status-pill';
    pill.className = 'chain-status-pill hidden';
    pill.innerHTML = `
      <div class="chain-pill-head">
        <span class="chain-pill-head-icon">🔄</span>
        <span class="chain-pill-head-title">盤前檢查</span>
        <span class="chain-pill-head-elapsed" id="chain-pill-elapsed">—</span>
      </div>
      <div class="chain-pill-rows">
        <div class="chain-pill-row" data-key="daily">
          <span class="chain-pill-row-icon">⏳</span>
          <span class="chain-pill-row-label">daily</span>
          <span class="chain-pill-row-meta">—</span>
        </div>
        <div class="chain-pill-row" data-key="news">
          <span class="chain-pill-row-icon">⏳</span>
          <span class="chain-pill-row-label">news</span>
          <span class="chain-pill-row-meta">—</span>
        </div>
        <div class="chain-pill-row" data-key="sector">
          <span class="chain-pill-row-icon">⏳</span>
          <span class="chain-pill-row-label">sector</span>
          <span class="chain-pill-row-meta">—</span>
        </div>
      </div>`;
    document.body.appendChild(pill);
    return pill;
  }

  const _CHAIN_GLYPH = { skipped: '✅', queued: '⏳', running: '🔄', done: '✅', error: '❌' };
  function _chainMeta(it, isZh) {
    const el = fmtElapsed(it.elapsed_sec || 0);
    switch (it.status) {
      case 'skipped': return isZh ? '已新鮮 · 跳過' : 'fresh · skipped';
      case 'queued':  return isZh ? '排隊中' : 'queued';
      case 'running': return `${isZh ? '執行中' : 'running'} · ${el}`;
      case 'done':    return `${isZh ? '完成' : 'done'} · ${el}`;
      case 'error':   return (it.error || '').slice(0, 60) || (isZh ? '錯誤' : 'error');
      default:        return '—';
    }
  }

  // V2.17.11 — terminal-state auto-hide is computed each tick from server's
  // `ended_at` (no setTimeout needed). Previous setTimeout-based approach kept
  // re-showing the pill after the timer fired because the next poll saw
  // status='done' (server keeps the terminal state until next chain run) and
  // unconditionally removed the hidden class. Computing the age fresh per tick
  // gives a stable "show while running, then 60s, then hide forever" behavior.
  const TERMINAL_GRACE_MS = 60000;
  async function pollChainPill() {
    try {
      const r = await fetch('/api/run-premarket-chain/status', { cache: 'no-store' });
      if (!r.ok) return;
      const s = await r.json();
      const pill = ensureChainPill();
      const isZh = (window.UI && UI.currentLang === 'zh') || (document.documentElement.lang || '').startsWith('zh');

      const modalOpen = !document.getElementById('preflight-modal')?.classList.contains('hidden');
      const terminal  = (s.status === 'done' || s.status === 'error');
      const terminalAgedOut = terminal && s.ended_at &&
        (Date.now() - new Date(s.ended_at).getTime()) > TERMINAL_GRACE_MS;

      if (s.status === 'idle' || modalOpen || terminalAgedOut) {
        pill.classList.add('hidden');
        return;
      }
      pill.classList.remove('hidden');

      const protoPill = document.getElementById('proto-status-pill');
      pill.classList.toggle('has-proto-pill', !!protoPill && !protoPill.classList.contains('hidden'));

      pill.querySelector('.chain-pill-head-title').textContent = isZh ? '盤前檢查' : 'Pre-market check';
      pill.querySelector('#chain-pill-elapsed').textContent = fmtElapsed(s.elapsed_sec || 0);

      const items = s.items || {};
      for (const k of ['daily', 'news', 'sector']) {
        const row = pill.querySelector(`.chain-pill-row[data-key="${k}"]`);
        if (!row) continue;
        const it = items[k] || {};
        row.querySelector('.chain-pill-row-icon').textContent = _CHAIN_GLYPH[it.status] || '⏳';
        row.querySelector('.chain-pill-row-meta').textContent = _chainMeta(it, isZh);
      }
    } catch { /* silent */ }
  }
  setInterval(pollChainPill, 3000);
  setTimeout(pollChainPill, 1400);

})();


// ── Shared Signal Tip Tooltip Engine ──────────────────────────────────────
// Renders the "AI 裁決區" rich tooltip style (title + desc + live banner +
// stage table + hint) across any page that includes a #signal-tip-tooltip
// element. Used on index (4 verdict pills) and sector (7 status pills).
//
// Wire-up on a page:
//   1. Add `<div id="signal-tip-tooltip" aria-hidden="true"></div>` once.
//   2. Add `data-signal-tip="ftd|breadth|market_top|synth|regime|exposure|fg|cycle|vix"`
//      to the hover target.
//   3. Set `data-*` live attributes (see SIGNAL_LIVE_BUILDERS for each key).
(function initSharedSignalTipEngine() {
  function init() {
    const tip = document.getElementById('signal-tip-tooltip');
    if (!tip) return;  // page didn't opt in
    let _hideTimer = null;

    const SIGNAL_TIPS = {
      ftd: {
        zh: {
          title: 'FTD · 市場底部確認訊號',
          desc:  '市場大跌觸底後開始反彈，從反彈第 1 天開始計算 rally day。若第 4-7 天主要指數出現「漲幅 ≥ +1% + 成交量比前日放大」→ 那天就標為 FTD，代表機構資金在這天介入抄底。從 FTD 起算，越早進場勝率越高（領導股剛起飛）；越晚進場屬於「補漲」性質，風險升高。',
          stages: [
            { key: 'prime',      range: [1,5],   range_label: 'day 1-5',   tag: '黃金期', action: '可以買',         detail: '領導股剛起飛，新趨勢確立，標準倉位最高勝率' },
            { key: 'standard',   range: [6,12],  range_label: 'day 6-12',  tag: '主升期', action: '仍可參與',       detail: '主升段未終結，標準倉位 + 標準停損，選擇 RS 強的個股' },
            { key: 'late_cycle', range: [13,20], range_label: 'day 13-20', tag: '補漲期', action: '晚但仍有機會',   detail: '行情進入後段，補漲股風險上升 — 倉位降 25%、停損收緊 1pp' },
            { key: 'exhausted',  range: [21,99], range_label: 'day 21+',   tag: '過熱期', action: '等下一輪',       detail: '多數領導股已 stage 2 末期，倉位降 50% 或拒單，等下一波 FTD' },
          ],
          no_active: '尚未出現有效 FTD（rally 仍在 attempt 階段、或前次 FTD 已失效）',
          hint: 'Reset 條件：跌破 swing low / 累積 6+ distribution days / 出現新一輪修正',
        },
        en: {
          title: 'FTD · Market Bottom Signal',
          desc:  'After a sell-off bottoms and a rally begins, count from rally day 1. If the index closes ≥+1% on heavier volume on rally days 4-7 → that day is marked as the FTD, signaling institutions are stepping in to buy. From that date, earlier entries have higher win rates (leadership stocks break out first); later entries become "chase trades" with elevated risk.',
          stages: [
            { key: 'prime',      range: [1,5],   range_label: 'day 1-5',   tag: 'Prime',     action: 'Buy zone',         detail: 'Leadership stocks just breaking out — full size, highest win rate' },
            { key: 'standard',   range: [6,12],  range_label: 'day 6-12',  tag: 'Standard',  action: 'Still tradeable',  detail: 'Uptrend intact — standard size + stop, focus on high-RS names' },
            { key: 'late_cycle', range: [13,20], range_label: 'day 13-20', tag: 'Late',      action: 'Chase, cut size',  detail: 'Late phase, chase trades — size −25%, stop tighter by 1pp' },
            { key: 'exhausted',  range: [21,99], range_label: 'day 21+',   tag: 'Exhausted', action: 'Wait for next',    detail: 'Most leaders late stage 2 — size −50% or reject, wait for next FTD' },
          ],
          no_active: 'No active FTD (rally still in attempt phase, or previous FTD invalidated)',
          hint: 'Reset triggers: close below swing low / 6+ distribution days / new correction begins',
        },
      },
      breadth: {
        zh: {
          title: '市場廣度 · 多少股票還在強勢區',
          desc:  '計算成分股「在 200 日均線之上的比例 + 8 日均線變化 + 突破/破底家數比 + 漲跌家數差」等多個指標，合成 0-100 分。分數高 = 大盤健康（不是只有少數權值股撐盤）；分數低 = 多數個股已轉弱、行情危險。建議倉位由分數決定。',
          stages: [
            { key: 'br_strong',    range: [75,100], range_label: 'score 75+',    tag: '健康強勢', action: '全力進攻', detail: '多數成分股健康突破，可以高倉位、新進不限制' },
            { key: 'br_healthy',   range: [60,74],  range_label: 'score 60-75',  tag: '主升中段', action: '標準參與', detail: '行情仍在主升段，標準倉位 + 一般停損即可' },
            { key: 'br_neutral',   range: [40,59],  range_label: 'score 40-60',  tag: '訊號混合', action: '選股、降倉', detail: '多空交雜，僅選 RS 強標的 + 倉位降 25%' },
            { key: 'br_weakening', range: [25,39],  range_label: 'score 25-40',  tag: '走弱中',   action: '防禦為主',  detail: '個股普遍轉弱，避免新進、現有倉位收緊停損' },
            { key: 'br_critical',  range: [0,24],   range_label: 'score < 25',   tag: '行情危險', action: '退守 cash', detail: '多數股票破位，cash 為王、保留資金等下次 FTD' },
          ],
          no_active: '廣度資料缺失或來源失敗',
          hint: '資料源：TraderMonty CSV (每日盤後更新，盤前看到的可能是 D-1 收盤值)',
        },
        en: {
          title: 'Market Breadth · How many stocks are still strong',
          desc:  'Composite of "% stocks above 200-day MA + 8-day MA delta + new highs vs lows + advance/decline gap" → 0-100 score. High = market is healthy (not just a few mega-caps holding it up); low = most stocks already weakening, dangerous.',
          stages: [
            { key: 'br_strong',    range: [75,100], range_label: 'score 75+',    tag: 'Strong',     action: 'Full attack',  detail: 'Most stocks healthy & breaking out — full size, no entry restrictions' },
            { key: 'br_healthy',   range: [60,74],  range_label: 'score 60-75',  tag: 'Healthy',    action: 'Standard',     detail: 'Uptrend intact — standard size + stop' },
            { key: 'br_neutral',   range: [40,59],  range_label: 'score 40-60',  tag: 'Neutral',    action: 'Selective',    detail: 'Mixed signals — high-RS only + size −25%' },
            { key: 'br_weakening', range: [25,39],  range_label: 'score 25-40',  tag: 'Weakening',  action: 'Defensive',    detail: 'Stocks broadly weakening — no new entries + tighten stops' },
            { key: 'br_critical',  range: [0,24],   range_label: 'score < 25',   tag: 'Critical',   action: 'Cash priority',detail: 'Most stocks breaking down — cash priority, wait for next FTD' },
          ],
          no_active: 'Breadth data unavailable / source failed',
          hint: 'Source: TraderMonty CSV (updated post-close — pre-market values may be D-1)',
        },
      },
      synth: {
        zh: {
          title: '綜合曝險 · 三訊號合成的倉位上限',
          desc:  '把廣度建議倉位、FTD 倉位、頂部風控三個來源的中位數取「最保守者（最小值）」 → 得出可承受倉位上限。意義：當三訊號彼此衝突時（例如 breadth 還健康但頂部風險爆表），系統會自動偏向最保守那一個，避免單一訊號誤判。實際個股建倉以這個上限為基準再乘 sector / FTD timeline / tail risk 等其他乘數。',
          stages: [
            { key: 'sy_aggressive', range: [75,100], range_label: '75-100%', tag: '進攻',     action: '滿倉操作',     detail: '三訊號全綠，可開高倉位、新進不限、停損標準' },
            { key: 'sy_standard',   range: [50,74],  range_label: '50-75%',  tag: '標準',     action: '正常配置',     detail: '主升段或訊號小幅雜訊，一般倉位 + 一般停損' },
            { key: 'sy_defensive',  range: [25,49],  range_label: '25-50%',  tag: '防守',     action: '降倉、選股',   detail: '至少一個訊號明顯轉弱，倉位降至 50% 以下、僅留高 conviction' },
            { key: 'sy_crisis',     range: [0,24],   range_label: '0-25%',   tag: '危機模式', action: 'Cash 主導',    detail: '三訊號之一已 critical，幾乎不開新倉、保留資金等下次 FTD' },
          ],
          no_active: '至少一個訊號缺失，無法合成曝險上限',
          hint: '計算：min( breadth_ceiling中位數, ftd_range中位數, market_top_budget中位數 )',
        },
        en: {
          title: 'Synthesized Ceiling · Position cap from 3 signals',
          desc:  'Takes the midpoint of breadth ceiling, FTD range, and market top budget — uses the most conservative (lowest) one as your position cap. Why: when signals disagree (e.g. breadth healthy but topping signals are loud), the system auto-defers to the most cautious. Per-trade size = this cap × sector / FTD-timeline / tail-risk multipliers downstream.',
          stages: [
            { key: 'sy_aggressive', range: [75,100], range_label: '75-100%', tag: 'Aggressive', action: 'Full size',    detail: 'All 3 signals green — full size, no entry restrictions, normal stops' },
            { key: 'sy_standard',   range: [50,74],  range_label: '50-75%',  tag: 'Standard',   action: 'Normal',       detail: 'Uptrend or minor signal noise — normal size + stop' },
            { key: 'sy_defensive',  range: [25,49],  range_label: '25-50%',  tag: 'Defensive',  action: 'Cut & select',  detail: 'At least one signal weakening — cut size <50%, high-conviction only' },
            { key: 'sy_crisis',     range: [0,24],   range_label: '0-25%',   tag: 'Crisis',     action: 'Cash priority', detail: 'One signal is critical — barely any new entries, hold cash for next FTD' },
          ],
          no_active: 'At least one signal missing — cap cannot be synthesized',
          hint: 'Formula: min( breadth_ceiling_mid, ftd_range_mid, market_top_budget_mid )',
        },
      },
      market_top: {
        zh: {
          title: '頂部風險 · 大盤是否已過熱',
          desc:  '綜合 distribution day（高量殺低天數）、領導股是否轉弱、防禦類股是否輪動進場、新高家數萎縮、Russell 2000 落後 SPY 程度等多類指標 → 合成 0-100 分。分數越高代表頂部訊號越多，需要降倉防範。與 breadth 互補：breadth 看「現在健康嗎」，這個看「快崩了嗎」。',
          stages: [
            { key: 'mt_normal',     range: [0,29],   range_label: 'score 0-30',   tag: '正常',     action: '可進攻',      detail: '暫無頂部訊號，廣度與領導同步，倉位上限可拉滿' },
            { key: 'mt_warning',    range: [30,49],  range_label: 'score 30-50',  tag: '早期警告', action: '留意',        detail: '個別訊號出現（如 distribution day 累積），上限不變但需密切觀察' },
            { key: 'mt_elevated',   range: [50,64],  range_label: 'score 50-65',  tag: '風險升高', action: '降倉、收緊',  detail: '訊號累積中，倉位上限調降至 60-80%、停損收緊' },
            { key: 'mt_high',       range: [65,79],  range_label: 'score 65-80',  tag: '高機率頂部', action: '撤退中',     detail: '明確頂部訊號，倉位上限 40-60%、僅留高 conviction 標的' },
            { key: 'mt_top',        range: [80,100], range_label: 'score 80+',    tag: '頂部成形', action: 'Cash 優先',  detail: '訊號全到位，倉位上限 ≤ 30%、現金為主等修正' },
          ],
          no_active: '頂部資料缺失或來源失敗',
          hint: '組合內部：distribution day / leadership / defensive rotation / 新高萎縮 等子分數',
        },
        en: {
          title: 'Market Top Risk · Is the market overheated',
          desc:  'Composite of distribution days, leadership deterioration, defensive sector rotation, new-high contraction, Russell 2000 lagging SPY, etc. → 0-100 risk score. Higher = more topping signals stacked, time to de-risk. Complementary to breadth: breadth = "is it healthy now", market top = "is it about to crack".',
          stages: [
            { key: 'mt_normal',     range: [0,29],   range_label: 'score 0-30',   tag: 'Normal',         action: 'Attack',       detail: 'No topping signals, breadth + leadership aligned, full size OK' },
            { key: 'mt_warning',    range: [30,49],  range_label: 'score 30-50',  tag: 'Early warning',  action: 'Watch',        detail: 'Isolated signals (e.g. distribution days) — size unchanged but monitor' },
            { key: 'mt_elevated',   range: [50,64],  range_label: 'score 50-65',  tag: 'Elevated',       action: 'Cut & tighten',detail: 'Signals stacking — cap at 60-80%, tighten stops' },
            { key: 'mt_high',       range: [65,79],  range_label: 'score 65-80',  tag: 'High risk',      action: 'Retreat',      detail: 'Clear top signals — cap at 40-60%, keep only high-conviction names' },
            { key: 'mt_top',        range: [80,100], range_label: 'score 80+',    tag: 'Top formed',     action: 'Cash priority',detail: 'All signals tripped — cap ≤30%, cash priority, wait for correction' },
          ],
          no_active: 'Market top data unavailable / source failed',
          hint: 'Sub-scores include: distribution days / leadership / defensive rotation / new-high contraction',
        },
      },
      // ── New bundles for sector page status pills ────────────────────────
      regime: {
        zh: {
          title: '市場體制 · 整體環境定位',
          desc:  '由 FTD、廣度、頂部風險、Fear&Greed、VIX 等多訊號合成的「整體進攻 vs 防禦」基調。決定投資組合的方向（攻/守/中性/震盪），個股操作再從這個基調做加減乘除。比單一訊號穩定，但反應較慢。',
          stages: [
            { key: 'rg_risk_on',  range: [0,99], range_label: 'RISK_ON',  tag: '可進攻',     action: '滿倉、新進',     detail: '多訊號偏多、廣度健康、無頂部風險，整體可往攻擊方向走、選 RS 強標的' },
            { key: 'rg_neutral',  range: [0,99], range_label: 'NEUTRAL',  tag: '中性',       action: '均衡配置',       detail: '多空訊號交雜、無明確方向，標準倉位 + 標準停損，避免重押任一方' },
            { key: 'rg_volatile', range: [0,99], range_label: 'VOLATILE', tag: '震盪',       action: '縮小規模',       detail: 'VIX 偏高 + 訊號雜訊，避免追高、倉位降 25%、停損收緊' },
            { key: 'rg_risk_off', range: [0,99], range_label: 'RISK_OFF', tag: '防禦',       action: 'Cash 為主',      detail: '訊號明顯偏空，廣度與頂部風險都告警，現金為王、等下一輪 FTD' },
          ],
          no_active: '體制資料缺失',
          hint: '個股實際倉位 = 體制基調 × 廣度上限 × FTD timeline × tail risk 等多重乘數',
        },
        en: {
          title: 'Market Regime · Overall posture',
          desc:  'Synthesized from FTD, breadth, top risk, Fear&Greed, and VIX into one of 4 postures (attack / defensive / neutral / volatile). Sets the portfolio bias; individual trades then apply further multipliers on top. More stable than any single signal but slower to flip.',
          stages: [
            { key: 'rg_risk_on',  range: [0,99], range_label: 'RISK_ON',  tag: 'Attack',     action: 'Full size, new entries',  detail: 'Multi-signal bullish, breadth healthy, no top risk — pick high-RS names' },
            { key: 'rg_neutral',  range: [0,99], range_label: 'NEUTRAL',  tag: 'Balanced',   action: 'Standard',                 detail: 'Mixed signals — normal size + stop, avoid heavy bets either way' },
            { key: 'rg_volatile', range: [0,99], range_label: 'VOLATILE', tag: 'Choppy',     action: 'Cut size −25%',            detail: 'VIX elevated + noisy signals — no chasing, tighten stops' },
            { key: 'rg_risk_off', range: [0,99], range_label: 'RISK_OFF', tag: 'Defensive',  action: 'Cash priority',            detail: 'Multi-signal bearish — cash is king, wait for next FTD' },
          ],
          no_active: 'Regime data unavailable',
          hint: 'Final position = regime bias × breadth ceiling × FTD timeline × tail-risk multipliers',
        },
      },
      exposure: {
        zh: {
          title: '曝險上限 · 整體可承受倉位',
          desc:  '由廣度、FTD、頂部三訊號合成的「整體投資組合最大倉位百分比」。意義：當前環境若你開到這個比例就是上限，不應再加碼；個股單筆建倉再從這個上限往下分配（依 sector 集中度、tail risk）。通常顯示為區間（如 60-75%）→ 取中位數定位。',
          stages: [
            { key: 'ex_full',      range: [85,100], range_label: '85-100%', tag: '滿倉',     action: '可全力進攻',  detail: '三訊號全綠，cash 比例 0-15%，新進不限制，可加碼領導股' },
            { key: 'ex_standard',  range: [60,84],  range_label: '60-85%',  tag: '標準',     action: '正常配置',    detail: '主升段，留 15-40% 現金應對波動，新進需挑高 RS 標的' },
            { key: 'ex_defensive', range: [30,59],  range_label: '30-60%',  tag: '防禦',     action: '降倉、選股',  detail: '訊號轉弱，cash 至少 40-70%，僅留高 conviction 個股、新進高度選擇性' },
            { key: 'ex_minimal',   range: [0,29],   range_label: '0-30%',   tag: '極低',     action: 'Cash 為主',   detail: '訊號明顯偏空，cash 至少 70%、等下次 FTD 才加倉' },
          ],
          no_active: '曝險上限資料缺失',
          hint: '與綜合曝險（synth）連動 — 個股倉位 = 此上限 × tail risk × sector cap × FTD multiplier',
        },
        en: {
          title: 'Exposure Cap · Max portfolio size',
          desc:  'Composite ceiling from breadth + FTD + top risk → max % of portfolio that should be deployed. Treat as a cap: do not add beyond this; per-trade size is allocated below this cap with further sector / tail-risk haircuts. Usually shown as a range (e.g. 60-75%) → midpoint determines stage.',
          stages: [
            { key: 'ex_full',      range: [85,100], range_label: '85-100%', tag: 'Full',       action: 'Full attack',    detail: '3 signals green, cash 0-15%, no entry restrictions, can add to leaders' },
            { key: 'ex_standard',  range: [60,84],  range_label: '60-85%',  tag: 'Standard',   action: 'Normal',         detail: 'Uptrend, hold 15-40% cash for volatility, prefer high-RS names' },
            { key: 'ex_defensive', range: [30,59],  range_label: '30-60%',  tag: 'Defensive',  action: 'Cut & select',   detail: 'Signals weakening, cash 40-70%, high-conviction only, very selective entries' },
            { key: 'ex_minimal',   range: [0,29],   range_label: '0-30%',   tag: 'Minimal',    action: 'Cash priority',  detail: 'Bearish signals, cash 70%+, wait for next FTD before adding' },
          ],
          no_active: 'Exposure cap data unavailable',
          hint: 'Per-trade size = this cap × tail risk × sector cap × FTD timeline multiplier',
        },
      },
      fg: {
        zh: {
          title: '恐慌貪婪 · 短線情緒逆向指標',
          desc:  'CNN Fear & Greed Index 0-100，由 VIX、Put/Call、市場動量、避險需求等綜合。**逆向**指標：情緒走極端時往往是反轉訊號 — 極度恐慌通常是中短線買點，極度貪婪則是賣出 / 觀望時機。注意：不能順著做，要配合 FTD 確認。',
          stages: [
            { key: 'fg_extreme_fear', range: [0,24],   range_label: '0-25',   tag: '極度恐慌', action: '逆向買點',     detail: '市場恐慌極致 → 機構搶反彈，建倉勝率高（注意要 FTD confirm 後再進）' },
            { key: 'fg_fear',         range: [25,44],  range_label: '25-45',  tag: '恐慌',     action: '可分批進場',   detail: '情緒偏空，逐步建倉、避免一次重押，等 FTD' },
            { key: 'fg_neutral',      range: [45,54],  range_label: '45-55',  tag: '中性',     action: '看其他訊號',   detail: '情緒不明朗，FG 不再主導，靠廣度 / 頂部訊號決策' },
            { key: 'fg_greed',        range: [55,74],  range_label: '55-75',  tag: '貪婪',     action: '保持紀律',     detail: '情緒偏多但未過熱，可繼續持倉，追蹤是否走向 extreme' },
            { key: 'fg_extreme_greed',range: [75,100], range_label: '75+',    tag: '極度貪婪', action: '減碼/觀望',    detail: '逆向訊號 → 容易觸頂，鎖部分獲利、停損收緊、避免新進' },
          ],
          no_active: 'Fear & Greed 資料缺失',
          hint: '資料源：CNN Fear & Greed（VIX、Put/Call、市場動量、避險需求等綜合）',
        },
        en: {
          title: 'Fear & Greed · Contrarian sentiment',
          desc:  'CNN Fear & Greed Index 0-100, blending VIX, Put/Call, market momentum, safe-haven demand. **Contrarian** indicator: extremes often mark reversals — extreme fear is typically a buy zone, extreme greed signals sell/hold. Do NOT trade with the sentiment; pair with FTD for confirmation.',
          stages: [
            { key: 'fg_extreme_fear', range: [0,24],   range_label: '0-25',   tag: 'Extreme Fear', action: 'Contrarian buy',  detail: 'Peak panic → institutions step in, high entry win rate (confirm with FTD first)' },
            { key: 'fg_fear',         range: [25,44],  range_label: '25-45',  tag: 'Fear',         action: 'Scale in',         detail: 'Bearish sentiment, build slowly, await FTD before going heavy' },
            { key: 'fg_neutral',      range: [45,54],  range_label: '45-55',  tag: 'Neutral',      action: 'Use other signals',detail: 'Sentiment ambiguous, defer to breadth / top signals' },
            { key: 'fg_greed',        range: [55,74],  range_label: '55-75',  tag: 'Greed',        action: 'Stay disciplined', detail: 'Bullish but not extreme, hold positions, monitor for extreme greed' },
            { key: 'fg_extreme_greed',range: [75,100], range_label: '75+',    tag: 'Extreme Greed',action: 'Trim / wait',       detail: 'Contrarian signal → top likely, take some profits, tighten stops, no new entries' },
          ],
          no_active: 'Fear & Greed data unavailable',
          hint: 'Source: CNN Fear & Greed (VIX, Put/Call, momentum, safe-haven demand)',
        },
      },
      cycle: {
        zh: {
          title: '市場週期 · 大盤位置 (Early/Mid/Late/Distribution)',
          desc:  '基於 breadth、FTD 距今天數、leadership 健康度等推估「目前是新一輪牛市的早/中/晚期，還是分配派發階段」。策略含意：早期 = 滿倉佈局新領導股、晚期 = 鎖獲利轉防禦、Distribution = 機構出貨中、退守 cash。',
          stages: [
            { key: 'cy_early',        range: [0,99], range_label: 'Early',        tag: '初升段', action: '積極佈局',    detail: 'FTD 剛確認、廣度快速回升，新領導股嶄露頭角 → 滿倉、選新高 + 強 RS' },
            { key: 'cy_mid',          range: [0,99], range_label: 'Mid',          tag: '主升段', action: '標準持倉',    detail: '趨勢確立、領導股仍健康，標準倉位 + 一般停損，避免重押個股' },
            { key: 'cy_late',         range: [0,99], range_label: 'Late',         tag: '末升段', action: '鎖獲利',      detail: '領導股漲幅已大、breadth 開始走弱 → 倉位降 25%、收緊停損、避免新進' },
            { key: 'cy_distribution', range: [0,99], range_label: 'Distribution', tag: '派發中', action: '退守 cash',   detail: 'Distribution day 累積、機構出貨，cash 為主、僅留高 conviction，等下輪 FTD' },
          ],
          no_active: '週期資料缺失',
          hint: '與 regime 互補：regime 看「攻或守」，cycle 看「在牛/熊的什麼階段」',
        },
        en: {
          title: 'Market Cycle · Stage in the bull/bear cycle',
          desc:  'Inferred from breadth, days since FTD, and leadership health: where we are in the bull→top→bear progression. Strategy: Early = build size in new leaders, Late = lock gains and defend, Distribution = institutions selling, go to cash.',
          stages: [
            { key: 'cy_early',        range: [0,99], range_label: 'Early',        tag: 'Early',        action: 'Build size',     detail: 'Fresh FTD, breadth recovering, new leaders emerging → full size, new highs + high RS' },
            { key: 'cy_mid',          range: [0,99], range_label: 'Mid',          tag: 'Mid',          action: 'Standard',       detail: 'Trend established, leaders healthy → standard size + stop, no concentration' },
            { key: 'cy_late',         range: [0,99], range_label: 'Late',         tag: 'Late',         action: 'Lock gains',     detail: 'Leaders extended, breadth weakening → cut size −25%, tighten stops, no new entries' },
            { key: 'cy_distribution', range: [0,99], range_label: 'Distribution', tag: 'Distribution', action: 'Cash priority',  detail: 'Distribution days stacking, institutions selling — cash only, high-conviction holds, wait for next FTD' },
          ],
          no_active: 'Cycle data unavailable',
          hint: 'Complementary to regime: regime = attack/defend, cycle = where in the bull/bear timeline',
        },
      },
      vix: {
        zh: {
          title: 'VIX · S&P 500 隱含波動率（恐慌指數）',
          desc:  'CBOE 計算的 SPX 期權 30 天年化隱含波動率。意義：投資者**對未來 30 天波動的預期**。VIX 高 = 預期動盪 / 恐慌；VIX 低 = 預期平穩 / 自滿。極端值往往是反轉訊號（VIX 飆 → 接近底部；VIX 過低 → 容易突發崩跌）。',
          stages: [
            { key: 'vx_calm',     range: [0,14.99],  range_label: '< 15',    tag: '平靜',     action: '正常操作',       detail: '波動低、市場自滿，可標準倉位但留意「過於平靜」也是頂部訊號之一' },
            { key: 'vx_normal',   range: [15,19.99], range_label: '15-20',   tag: '一般',     action: '標準配置',       detail: '正常波動環境，無特別訊號，依其他指標決策' },
            { key: 'vx_elevated', range: [20,29.99], range_label: '20-30',   tag: '升高',     action: '謹慎、降倉',     detail: '市場開始緊張，倉位降 20-30%、停損收緊、避免追高' },
            { key: 'vx_high',     range: [30,39.99], range_label: '30-40',   tag: '高',       action: '防禦/觀望',      detail: '恐慌升溫，cash 至少 50%、僅持高 conviction，準備逆向買點（待 FTD 確認）' },
            { key: 'vx_panic',    range: [40,200],   range_label: '40+',     tag: '恐慌',     action: '反向操作機會',   detail: '極端恐慌往往臨近底部 → 開始分批佈局，但須 FTD confirm 才大量進場' },
          ],
          no_active: 'VIX 資料缺失',
          hint: '參考：VIX 過去 5 年中位數約 16-18，> 30 多在崩盤期間，> 40 為極端恐慌',
        },
        en: {
          title: 'VIX · 30-day implied volatility (fear gauge)',
          desc:  'CBOE\'s 30-day annualized implied volatility on SPX options — what investors **expect** the next 30 days to look like. High VIX = expected turbulence/fear; low VIX = complacency. Extremes are reversal signals (VIX spike → near bottom; VIX too low → vulnerable to sudden crashes).',
          stages: [
            { key: 'vx_calm',     range: [0,14.99],  range_label: '< 15',  tag: 'Calm',      action: 'Normal',          detail: 'Low vol, complacent market — standard size but "too calm" is itself a topping signal' },
            { key: 'vx_normal',   range: [15,19.99], range_label: '15-20', tag: 'Normal',    action: 'Standard',        detail: 'Normal vol environment, no particular signal — use other indicators' },
            { key: 'vx_elevated', range: [20,29.99], range_label: '20-30', tag: 'Elevated',  action: 'Caution',         detail: 'Market getting tense — cut size 20-30%, tighten stops, no chasing' },
            { key: 'vx_high',     range: [30,39.99], range_label: '30-40', tag: 'High',      action: 'Defensive',       detail: 'Fear rising, cash 50%+, high-conviction only, prep for contrarian buy (await FTD)' },
            { key: 'vx_panic',    range: [40,200],   range_label: '40+',   tag: 'Panic',     action: 'Contrarian zone', detail: 'Extreme fear → bottom likely near, start scaling in (full size only after FTD confirms)' },
          ],
          no_active: 'VIX data unavailable',
          hint: 'Reference: 5-year median ~16-18, >30 typical of crash periods, >40 = extreme panic',
        },
      },
      // ── Warning flag tooltips (V1.72.8 — for sector page risk-flag-cards) ──
      bearish_signal: {
        zh: {
          title: '空頭信號啟動 · CRITICAL',
          desc:  '系統內建的空頭觸發子系統偵測到風險訊號(可能是 distribution day 累積、領導股 breakdown、或多重技術破位疊加)。注意:這個訊號跟廣度分數 Breadth 是**獨立計算**,Breadth 健康時也可能觸發。',
          stages: [],
          hint: '應對:降低新建倉、收緊既有部位停損、保留現金等更明確的市場底部訊號(FTD)。',
        },
        en: {
          title: 'Bearish Signal Active · CRITICAL',
          desc:  'Internal bearish trigger subsystem detected risk signals (e.g. distribution day count, leadership breakdown, multi-indicator breaks). Note: this signal is **computed independently** from the Breadth score — can fire even when Breadth looks healthy.',
          stages: [],
          hint: 'Action: cut new entries, tighten stops, hold cash and wait for a confirmed bottom signal (FTD).',
        },
      },
      low_historical_percentile: {
        zh: {
          title: '歷史低百分位 · WARNING',
          desc:  '當前廣度分數在過去 5 年的分布中處於低位(<30 percentile)。提供「歷史相對位置」這個獨立 dimension(不同於當下 breadth 絕對分數)。歷史低點通常會接著震盪 + 反彈,但也可能是更大跌段的中繼。',
          stages: [],
          hint: '參考:歷史低分後 60 天內,約 75% 機率出現反彈,但反轉訊號要靠 FTD 才確認。',
        },
        en: {
          title: 'Low Historical Percentile · WARNING',
          desc:  'Current breadth score sits in the bottom 30 percentile of its 5-year distribution. Adds a "historical relative position" dimension separate from the absolute Breadth score. Historic lows usually precede chop + bounce, but can also be a midpoint in larger declines.',
          stages: [],
          hint: 'Reference: ~75% of historical lows see a bounce within 60 days, but actual reversal needs FTD confirmation.',
        },
      },
      divergence: {
        zh: {
          title: '早期背離警告 · WARNING',
          desc:  '價格在創新高(或維持高位),但廣度 / 動能等內部指標已在下滑 — 「指數在飛、底下個股已倒一片」的典型 distribution 前兆。並非馬上要崩,但領先指標已轉弱。',
          stages: [],
          hint: '應對:選股提高 RS 門檻、避開 stage 3 標的、降低槓桿曝險。',
        },
        en: {
          title: 'Early Warning Divergence · WARNING',
          desc:  'Price makes (or holds) new highs while internal breadth/momentum indicators slope down — the classic "index flies while stocks die underneath" distribution precursor. Not an imminent crash signal, but leading indicators have rolled over.',
          stages: [],
          hint: 'Action: raise RS bar on entries, avoid stage-3 names, reduce leverage exposure.',
        },
      },
      // ── V2.7.16 — Earnings detail trend chart tips ─────────────────
      ed_chart_revenue_ni: {
        zh: {
          title: '營收 · 淨利 · 5 季趨勢',
          desc:  '**Revenue（營收）**：當季總賣多少。**Net Income（淨利）**：扣完所有費用 + 稅後最終賺多少。看雙條趨勢能判斷「規模是否擴張 + 利潤同步增長」。健康公司兩條同向上、距離保持；若 Revenue 上但 Net Income 下 → 成本失控（毛利侵蝕、SG&A 暴增、稅務 / 一次性費用）。',
          stages: [],
          hint: '看點：兩條斜率是否一致 / Net Income / Revenue 比率（即 net margin）是否擴張。Apple 通常 Net Income 約 25-27% Revenue。',
        },
        en: {
          title: 'Revenue · Net Income · 5Q Trend',
          desc:  '**Revenue**: total quarterly sales. **Net Income**: profit after all costs and taxes. Both trending up + spread holding = scaling cleanly. If Revenue rises but Net Income falls → costs running away (margin compression, SG&A spike, one-time charges).',
          stages: [],
          hint: 'Watch: slope alignment + Net/Revenue ratio (net margin) trend. Apple typically nets ~25-27%.',
        },
      },
      ed_chart_eps: {
        zh: {
          title: 'EPS · 5 季趨勢',
          desc:  '**Earnings Per Share（每股盈餘）** = Net Income ÷ 流通股數。是「股東實際分到的單位獲利」，市場最看的就是這條。EPS 趨勢上揚 + buyback 縮股本（分母縮小）= 雙重利多。EPS 跳水但 Net Income 沒跳 → 可能是新股增發稀釋。EPS 比 Net Income 還重要因為它直接綁估值（PE = Price / EPS）。',
          stages: [],
          hint: '財報日 surprise 比預期多 1-2% 都可能漲，比預期少甚至持平就跌。看點：YoY EPS 增速、是否符合 forward PE 暗示成長率。',
        },
        en: {
          title: 'EPS · 5Q Trend',
          desc:  '**Earnings Per Share** = Net Income ÷ shares outstanding. The "per-shareholder profit" — what the market actually prices. EPS up + buybacks shrinking share count = double tailwind. EPS dropping while Net Income flat → likely share dilution. EPS matters more than Net Income because valuation directly anchors to it (PE = Price / EPS).',
          stages: [],
          hint: 'On report day, beating estimates by 1-2% can pump; meeting or missing typically drops. Watch YoY EPS growth vs forward PE-implied growth.',
        },
      },
      ed_chart_cashflow: {
        zh: {
          title: 'OCF · FCF · 5 季趨勢',
          desc:  '**OCF（Operating Cash Flow，營業現金流）**：本業實際收進來的現金。比 Net Income 真，因為排除非現金科目（折舊、應收灌水）。\n\n**FCF（Free Cash Flow，自由現金流）** = OCF − CapEx（資本支出）。「股東可自由運用」的現金，用來算 buyback / dividend / 還債 / DCF 估值。\n\nFCF 強且穩 = 公司有護城河、護城河賺錢、且不需要狂砸錢維持。FCF 為負 = 燒錢成長期或結構問題。',
          stages: [],
          hint: 'OCF 和 Net Income 差很多時要警覺（盈餘品質問題）。FCF / Revenue 比率叫 FCF margin，30%+ 屬軟體業，10-20% 為健康製造業。',
        },
        en: {
          title: 'OCF · FCF · 5Q Trend',
          desc:  '**OCF (Operating Cash Flow)**: actual cash from core business. More truthful than Net Income — excludes non-cash items (depreciation, AR inflation).\n\n**FCF (Free Cash Flow)** = OCF − CapEx. The "shareholder-free" cash used for buybacks / dividends / debt paydown / DCF valuation.\n\nStrong stable FCF = real moat with cash conversion. Negative FCF = growth-stage burn or structural problem.',
          stages: [],
          hint: 'Big OCF vs Net Income gap = earnings quality red flag. FCF / Revenue (FCF margin) ≥30% = software-class, 10-20% healthy industrials.',
        },
      },
      ed_chart_margins: {
        zh: {
          title: '毛利率 · 營業利益率 · 5 季趨勢',
          desc:  '**Gross Margin（毛利率，GM）** = (Revenue − COGS) / Revenue。產品本身賺不賺。NVDA 75%+ 屬軟體級護城河，傳產 20-30%。\n\n**Operating Margin（營業利益率，OM）** = Operating Income / Revenue。扣完 R&D + SG&A 後的營運效率。同業比 OM 比 GM 直接，因為 OM 反映「整家公司」的執行力。\n\n趨勢看點：GM 突然下滑 → 成本端出問題（COGS 漲、產品 mix 惡化、降價競爭）；GM 穩但 OM 下滑 → R&D / SG&A 暴增（可能擴張中或浪費）。',
          stages: [],
          hint: 'Apple GM 約 45-49%、OM 約 30-32%。Margin 連 2 季下滑是早期警訊；連 3 季 = 結構性問題。',
        },
        en: {
          title: 'Gross · Operating Margin · 5Q Trend',
          desc:  '**Gross Margin (GM)** = (Revenue − COGS) / Revenue. Product-level profitability. NVDA 75%+ = software-class moat, industrials 20-30%.\n\n**Operating Margin (OM)** = Operating Income / Revenue. After R&D + SG&A — full-company execution. OM is more direct than GM for peer comparison.\n\nGM dropping → cost-side problem (COGS up, mix worse, price competition). GM stable but OM dropping → R&D / SG&A spiking (expansion or waste).',
          stages: [],
          hint: 'Apple GM ~45-49%, OM ~30-32%. Two consecutive quarters of margin decline = early warning; three = structural.',
        },
      },
      ed_chart_segment_growth: {
        zh: {
          title: '分部 YoY 成長 · 哪個業務在拉車',
          desc:  '把當季營收按產品線 / 業務分部拆開，看每塊的同期年增率（YoY %）。例如 Apple：iPhone +21.7%、Services +16.3%、Mac +5.7%。\n\n用法：找出**主成長引擎**（哪塊 +20%+）vs **拖累項**（哪塊負成長）。新引擎冒出 = 估值重估理由；舊主力萎縮 = 結構性風險。\n\n資料來自 transcript（CFO 段）LLM 抽，比 FMP 結構化資料多了 Q-level 細粒度。',
          stages: [],
          hint: '單季數字波動大，要看 2-3 季趨勢才確認；單一業務 +50% 也可能是 base 效應。',
        },
        en: {
          title: 'Segment YoY Growth · Who\'s pulling the wagon',
          desc:  'Quarterly revenue split by product line / segment with YoY %. E.g. Apple: iPhone +21.7%, Services +16.3%, Mac +5.7%.\n\nUsage: identify **growth engines** (which segments +20%+) vs **drags** (negative). New engines emerging = re-rating thesis; legacy core shrinking = structural risk.\n\nData extracted from transcript CFO commentary by LLM — finer-grained than FMP structured data.',
          stages: [],
          hint: 'Single quarter is noisy — confirm with 2-3 quarter trend. +50% in one segment may just be base effect.',
        },
      },
      // ── V2.8.4 — Earnings card 4-component score bar tips ───────────
      ed_score_quality: {
        zh: {
          title: 'QUALITY · 體質分數 (0-30)',
          desc:  '衡量公司**財報體質乾淨度**。看 4 大項：\n\n**1. Margin 趨勢**：毛利率 / 營業利益率 8Q 是否穩定或下滑\n**2. Accruals**：應計項佔資產比，過高 = 盈餘灌水嫌疑\n**3. Cash Conversion**：OCF / Net Income，偏低 = 帳面獲利沒變現金\n**4. Altman-Z**：破產風險指標，>3 安全 / <1.8 危險\n\n滿分 30 = 全部 4 項 clean。低於 20 = 至少 1 項紅燈，要看 quality_flags 條目。',
          stages: [],
          hint: 'Quality 與 Growth 同時高分 = 罕見的「乾淨成長股」。Quality 高 + Growth 低 = 成熟現金牛。',
        },
        en: {
          title: 'QUALITY · Financial Hygiene (0-30)',
          desc:  'Measures **how clean the financials are**. 4 sub-components:\n\n**1. Margin Trend**: 8Q gross/op margin stability or compression\n**2. Accruals**: accrual ratio (asset-scaled); high = earnings inflation suspect\n**3. Cash Conversion**: OCF / Net Income; low = paper profits not converting to cash\n**4. Altman-Z**: bankruptcy risk; >3 safe / <1.8 distress\n\nFull 30 = all 4 clean. Below 20 = ≥1 red flag, check quality_flags chips.',
          stages: [],
          hint: 'High Quality + High Growth = rare clean compounder. High Quality + low Growth = mature cash cow.',
        },
      },
      ed_score_growth: {
        zh: {
          title: 'GROWTH · 成長分數 (0-30)',
          desc:  '衡量**多軸成長動能**：\n\n**1. YoY Revenue 成長**：當季 vs 去年同季營收增幅\n**2. YoY EPS 成長**：每股盈餘年增率\n**3. Segment / Geo 成長**：transcript 抽出的分部 / 地理 YoY%（哪塊在拉、哪塊在拖）\n**4. 加速度**：QoQ 成長是否在加速 (re-rating signal) 還是減速 (saturation)\n\n滿分 30 = 多軸都 +20%+。20-25 = 健康成長。<15 = 成長疲軟或衰退。',
          stages: [],
          hint: 'Growth 30 + Quality 25+ = 黃金組合（NVDA、LLY 等型）。Growth 30 + Quality <15 = 成長代價高（燒錢、accrual 灌水）。',
        },
        en: {
          title: 'GROWTH · Growth Momentum (0-30)',
          desc:  'Multi-axis growth scoring:\n\n**1. YoY Revenue**: current quarter vs same quarter last year\n**2. YoY EPS**: earnings per share growth\n**3. Segment / Geographic Growth**: transcript-extracted segment & region YoY% (what\'s pulling vs dragging)\n**4. Acceleration**: QoQ growth — accelerating (re-rating) vs decelerating (saturation)\n\nFull 30 = all axes +20%+. 20-25 = healthy. <15 = stalling or shrinking.',
          stages: [],
          hint: 'Growth 30 + Quality 25+ = compounder gold (NVDA, LLY style). Growth 30 + Quality <15 = growth at a cost (cash burn, accrual inflation).',
        },
      },
      ed_score_value: {
        zh: {
          title: 'VALUE · 估值分數 (0-25)',
          desc:  '衡量**目前股價相對基本面便宜或貴**：\n\n**1. PE Ratio**：目前股價 / EPS，越低越便宜\n**2. PB Ratio**：股價 / 帳面價值\n**3. DCF Fair Value**：現金流折現算合理價，目前股價 vs 合理價差距\n**4. FCF Yield**：FCF / Market Cap，越高代表單位市值產生越多現金\n\n滿分 25 = 多指標顯示便宜（很少見，通常市場有原因）。15-20 = 合理估值。<10 = 估值偏貴 / 已 priced in 成長。',
          stages: [],
          hint: '高成長股 Value 通常 5-15（市場已 priced in）。傳產 / 金融常 20-25。VALUE 高 ≠ 便宜貨機會，要配 Quality / Growth 看是否 value trap。',
        },
        en: {
          title: 'VALUE · Valuation Score (0-25)',
          desc:  'Measures **how cheap or expensive the current price is vs fundamentals**:\n\n**1. PE Ratio**: price / EPS — lower = cheaper\n**2. PB Ratio**: price / book value\n**3. DCF Fair Value**: discounted cash flow vs current price gap\n**4. FCF Yield**: FCF / Market Cap — higher = more cash per market cap dollar\n\nFull 25 = multi-indicator cheap (rare, usually for a reason). 15-20 = fair. <10 = expensive / growth priced in.',
          stages: [],
          hint: 'High-growth names usually score 5-15 on Value (priced in). Industrials / financials often 20-25. High Value alone ≠ buy — must pair with Quality/Growth or risk value trap.',
        },
      },
      ed_score_analyst: {
        zh: {
          title: 'ANALYST · 分析師共識 (0-15)',
          desc:  '衡量**Wall Street 對此股的信心**：\n\n**1. Consensus PT**：分析師目標價 vs 現價的隱含 upside%\n**2. Rating Distribution**：strong buy / buy / hold / sell 比例\n**3. Recent Surprise**：最近 4 季 EPS 是否 beat estimate\n**4. PT Revisions**：最近 30 天目標價上調 vs 下調家數\n\n滿分 15 = 分析師強烈看多 + 連續 beat + 目標價持續上調。中位數 8-12。<5 = 分析師偏空或下調潮。',
          stages: [],
          hint: '分析師滿分要小心 — 通常代表已是 consensus long，邊際 surprise 空間小。Analyst 低 + Quality/Growth 高 = contrarian opportunity。',
        },
        en: {
          title: 'ANALYST · Wall Street Consensus (0-15)',
          desc:  'Measures **how bullish analysts are**:\n\n**1. Consensus Price Target**: implied upside % vs current price\n**2. Rating Distribution**: strong buy / buy / hold / sell mix\n**3. Recent Surprise**: last 4 quarters EPS beat rate\n**4. PT Revisions**: 30-day upgrade vs downgrade count\n\nFull 15 = analysts strongly bullish + serial beats + PT trending up. Median 8-12. <5 = bearish or downgrade wave.',
          stages: [],
          hint: 'Max Analyst score = caution: already consensus long, marginal surprise room limited. Low Analyst + high Quality/Growth = contrarian setup.',
        },
      },
      ed_chart_geo_growth: {
        zh: {
          title: '地理 YoY 成長 · 哪個地區在貢獻',
          desc:  '把當季營收按地理區域拆開（USA / EU / Greater China / Japan / APAC），看每地區同期年增率。\n\n用法：偵測**地緣 / 匯率 / 區域消費風險**。中國 -20% + 美國 +10% = 中國市場萎縮（policy / consumer），不是全公司有問題。對 AAPL 特別重要：iPhone 在 Greater China 變化幅度通常領先全球。\n\n注意：FMP 只給 FY 年度資料，Q-level 須從 transcript 抽（Apple CFO 段通常會講「Greater China revenue down 8%」這種數字）。',
          stages: [],
          hint: '地理 YoY 缺值 = 該季 transcript 沒講具體數字（Apple CFO 偶爾不講）。對中國市場敏感的公司（消費電子、汽車、奢侈品）這條最關鍵。',
        },
        en: {
          title: 'Geography YoY Growth · Where is the demand',
          desc:  'Quarterly revenue split by region (USA / EU / Greater China / Japan / APAC) with YoY %.\n\nUsage: detect **geopolitical / FX / regional demand risk**. China −20% + US +10% = China softness (policy / consumer), not company-wide problem. Especially key for AAPL: iPhone Greater China leads global.\n\nNote: FMP only provides FY annual; Q-level pulled from transcript (Apple CFO usually states "Greater China revenue down 8%").',
          stages: [],
          hint: 'Missing YoY = transcript didn\'t state explicit numbers that quarter (Apple CFO sometimes omits). Most critical for China-sensitive names (consumer electronics, autos, luxury).',
        },
      },
    };

    function classifyStage(stages, daysSince) {
      if (daysSince == null || daysSince === '' || isNaN(daysSince)) return null;
      const n = Number(daysSince);
      return stages.find(s => n >= s.range[0] && n <= s.range[1]) || null;
    }

    const STAGE_DOTS = {
      // FTD
      prime: '🟢', standard: '🟡', late_cycle: '🟠', exhausted: '🔴',
      // Breadth
      br_strong: '🟢', br_healthy: '🟢', br_neutral: '🟡', br_weakening: '🟠', br_critical: '🔴',
      // Market top
      mt_normal: '🟢', mt_warning: '🟡', mt_elevated: '🟠', mt_high: '🟠', mt_top: '🔴',
      // Synth ceiling
      sy_aggressive: '🟢', sy_standard: '🟡', sy_defensive: '🟠', sy_crisis: '🔴',
      // Regime
      rg_risk_on: '🟢', rg_neutral: '🟡', rg_volatile: '🟠', rg_risk_off: '🔴',
      // Exposure
      ex_full: '🟢', ex_standard: '🟡', ex_defensive: '🟠', ex_minimal: '🔴',
      // Fear & Greed (contrarian: extreme fear = green/buy, extreme greed = red/sell)
      fg_extreme_fear: '🟢', fg_fear: '🟡', fg_neutral: '🟡', fg_greed: '🟠', fg_extreme_greed: '🔴',
      // Cycle
      cy_early: '🟢', cy_mid: '🟡', cy_late: '🟠', cy_distribution: '🔴',
      // VIX
      vx_calm: '🟢', vx_normal: '🟢', vx_elevated: '🟡', vx_high: '🟠', vx_panic: '🔴',
    };

    function renderStageRows(stages, activeStage) {
      return stages.map(s => {
        const active = activeStage && s.key === activeStage.key;
        return `<div class="stt-stage-row${active ? ' stt-stage-active' : ''}">
          <span class="stt-stage-dot">${STAGE_DOTS[s.key] || '⚪'}</span>
          <span class="stt-stage-range">${s.range_label}</span>
          <span class="stt-stage-tag">${s.tag}</span>
          <span class="stt-stage-action">${s.action}</span>
          <div class="stt-stage-detail">${s.detail}</div>
        </div>`;
      }).join('');
    }

    const noActiveHTML = (t) => `<div class="stt-live"><span>${t.no_active}</span></div>`;

    // Per-signal live banner builders. Return { liveHTML, stage } for the active state.
    function ftdLive(el, t, lang) {
      const state = el.dataset.ftdState || '';
      const date  = el.dataset.ftdDate || '';
      const day   = el.dataset.ftdDay;
      if (state !== 'FTD_CONFIRMED' || !date) return { liveHTML: noActiveHTML(t), stage: null };
      const stage = classifyStage(t.stages, day);
      if (!stage) return { liveHTML: noActiveHTML(t), stage: null };
      const dayLabel = lang === 'en' ? `day ${day}` : `已過 ${day} 天`;
      const liveHTML = `<div class="stt-live">
        <span class="stt-live-dot">${STAGE_DOTS[stage.key] || '⚪'}</span>
        <span>📅 ${date}</span>
        <span class="stt-live-day">· ${dayLabel}</span>
        <span class="stt-live-stage">${stage.tag} — ${stage.action}</span>
      </div>`;
      return { liveHTML, stage };
    }

    function breadthLive(el, t, lang) {
      const score = el.dataset.brScore;
      const zone  = el.dataset.brZone || '';
      const ceil  = el.dataset.brCeiling || '';
      if (score === '' || score == null) return { liveHTML: noActiveHTML(t), stage: null };
      const stage = classifyStage(t.stages, score);
      const ceilLabel = lang === 'en' ? `ceiling ${ceil}` : `建議倉位 ${ceil}`;
      const liveHTML = `<div class="stt-live">
        <span class="stt-live-dot">${STAGE_DOTS[stage?.key] || '⚪'}</span>
        <span>📊 ${Number(score).toFixed(1)}</span>
        <span class="stt-live-day">· ${zone}</span>
        <span class="stt-live-stage">${ceilLabel}</span>
      </div>`;
      return { liveHTML, stage };
    }

    function marketTopLive(el, t, lang) {
      const score  = el.dataset.mtScore;
      const zone   = (el.dataset.mtZone || '').replace(/\(.*\)/, '').trim();
      const budget = el.dataset.mtBudget || '';
      if (score === '' || score == null) return { liveHTML: noActiveHTML(t), stage: null };
      const stage = classifyStage(t.stages, score);
      const budgetLabel = lang === 'en' ? `budget ${budget}` : `風控 ${budget}`;
      const liveHTML = `<div class="stt-live">
        <span class="stt-live-dot">${STAGE_DOTS[stage?.key] || '⚪'}</span>
        <span>⚠️ ${Number(score).toFixed(1)}</span>
        <span class="stt-live-day">· ${zone}</span>
        <span class="stt-live-stage">${budgetLabel}</span>
      </div>`;
      return { liveHTML, stage };
    }

    function synthLive(el, t, lang) {
      const mid    = el.dataset.synthMid;
      const label  = el.dataset.synthLabel || '';
      const brC    = el.dataset.brCeiling || '—';
      const ftdR   = el.dataset.ftdRange || '—';
      const mtB    = el.dataset.mtBudget || '—';
      if (mid === '' || mid == null) return { liveHTML: noActiveHTML(t), stage: null };
      const stage = classifyStage(t.stages, mid);
      const sourceLabel = lang === 'en'
        ? `breadth ${brC} · FTD ${ftdR} · top ${mtB}`
        : `廣度 ${brC} · FTD ${ftdR} · 頂部 ${mtB}`;
      const liveHTML = `<div class="stt-live">
        <span class="stt-live-dot">${STAGE_DOTS[stage?.key] || '⚪'}</span>
        <span>🎯 ${label}</span>
        <span class="stt-live-stage">${stage?.tag || ''} — ${stage?.action || ''}</span>
      </div>
      <div class="stt-live-sources">${sourceLabel}</div>`;
      return { liveHTML, stage };
    }

    function regimeLive(el, t, lang) {
      const val = (el.dataset.regime || '').toUpperCase();
      if (!val) return { liveHTML: noActiveHTML(t), stage: null };
      const keyMap = { RISK_ON:'rg_risk_on', BULL:'rg_risk_on',
                       NEUTRAL:'rg_neutral', SIDEWAYS:'rg_neutral',
                       VOLATILE:'rg_volatile',
                       RISK_OFF:'rg_risk_off', BEAR:'rg_risk_off' };
      const stage = t.stages.find(s => s.key === keyMap[val]) || null;
      const liveHTML = `<div class="stt-live">
        <span class="stt-live-dot">${STAGE_DOTS[stage?.key] || '⚪'}</span>
        <span>🌐 ${val.replace(/_/g,' ')}</span>
        <span class="stt-live-stage">${stage?.tag || ''} — ${stage?.action || ''}</span>
      </div>`;
      return { liveHTML, stage };
    }

    function exposureLive(el, t, lang) {
      const raw = el.dataset.exposure || '';
      if (!raw) return { liveHTML: noActiveHTML(t), stage: null };
      const nums = raw.match(/\d+/g);
      if (!nums) return { liveHTML: noActiveHTML(t), stage: null };
      const mid = nums.length > 1 ? (Number(nums[0]) + Number(nums[1])) / 2 : Number(nums[0]);
      const stage = classifyStage(t.stages, mid);
      const liveHTML = `<div class="stt-live">
        <span class="stt-live-dot">${STAGE_DOTS[stage?.key] || '⚪'}</span>
        <span>📦 ${raw}</span>
        <span class="stt-live-stage">${stage?.tag || ''} — ${stage?.action || ''}</span>
      </div>`;
      return { liveHTML, stage };
    }

    function fgLive(el, t, lang) {
      const score = el.dataset.fgScore;
      const label = el.dataset.fgLabel || '';
      if (score === '' || score == null) return { liveHTML: noActiveHTML(t), stage: null };
      const stage = classifyStage(t.stages, score);
      const liveHTML = `<div class="stt-live">
        <span class="stt-live-dot">${STAGE_DOTS[stage?.key] || '⚪'}</span>
        <span>😨 ${Number(score).toFixed(1)}</span>
        <span class="stt-live-day">· ${label}</span>
        <span class="stt-live-stage">${stage?.tag || ''} — ${stage?.action || ''}</span>
      </div>`;
      return { liveHTML, stage };
    }

    function cycleLive(el, t, lang) {
      const phase = (el.dataset.cycle || '').trim();
      if (!phase) return { liveHTML: noActiveHTML(t), stage: null };
      const keyMap = { Early:'cy_early', EARLY:'cy_early',
                       Mid:'cy_mid', MID:'cy_mid',
                       Late:'cy_late', LATE:'cy_late',
                       Distribution:'cy_distribution', DISTRIBUTION:'cy_distribution' };
      const stage = t.stages.find(s => s.key === keyMap[phase]) || null;
      const liveHTML = `<div class="stt-live">
        <span class="stt-live-dot">${STAGE_DOTS[stage?.key] || '⚪'}</span>
        <span>🔄 ${phase}</span>
        <span class="stt-live-stage">${stage?.tag || ''} — ${stage?.action || ''}</span>
      </div>`;
      return { liveHTML, stage };
    }

    function vixLive(el, t, lang) {
      const v = el.dataset.vix;
      if (v === '' || v == null) return { liveHTML: noActiveHTML(t), stage: null };
      const stage = classifyStage(t.stages, v);
      const liveHTML = `<div class="stt-live">
        <span class="stt-live-dot">${STAGE_DOTS[stage?.key] || '⚪'}</span>
        <span>📉 ${Number(v).toFixed(1)}</span>
        <span class="stt-live-stage">${stage?.tag || ''} — ${stage?.action || ''}</span>
      </div>`;
      return { liveHTML, stage };
    }

    // V1.72.8 — Warning flag live builders (read data-flag-metric, single-line banner)
    function _flagMetricLive(emoji) {
        return function(el, t, lang) {
            const metric = el.dataset.flagMetric || '';
            if (!metric) return { liveHTML: noActiveHTML(t), stage: null };
            const liveHTML = `<div class="stt-live">
                <span class="stt-live-dot">⚠</span>
                <span>${emoji} ${metric}</span>
            </div>`;
            return { liveHTML, stage: null };
        };
    }

    const LIVE_BUILDERS = {
      ftd: ftdLive, breadth: breadthLive, market_top: marketTopLive, synth: synthLive,
      regime: regimeLive, exposure: exposureLive, fg: fgLive, cycle: cycleLive, vix: vixLive,
      bearish_signal:            _flagMetricLive('🚨'),
      low_historical_percentile: _flagMetricLive('📊'),
      divergence:                _flagMetricLive('↘'),
    };

    // V2.17.7 — markdown → HTML for tooltip body text. Tooltip source uses
    // `**bold**` + `\n\n` paragraph + `\n` line breaks; previously injected raw
    // so `**1. Margin 趨勢**` rendered literally. Pipeline: escape HTML first
    // (defense-in-depth even though source is dev-controlled), then add back
    // trusted markup.
    function _escapeTipHTML(s) {
      return String(s ?? '')
        .replace(/&/g, '&amp;').replace(/</g, '&lt;')
        .replace(/>/g, '&gt;').replace(/"/g, '&quot;');
    }
    function _renderTipMarkdown(s) {
      if (s == null) return '';
      let html = _escapeTipHTML(s);
      // **bold** — non-greedy, single pair (avoid eating across paragraphs)
      html = html.replace(/\*\*([^*]+?)\*\*/g, '<strong>$1</strong>');
      // \n\n → paragraph break, \n → <br>
      const paragraphs = html.split(/\n\n+/).map(p => p.replace(/\n/g, '<br>'));
      return paragraphs.length > 1
        ? paragraphs.map(p => `<p>${p}</p>`).join('')
        : paragraphs[0];
    }

    function buildSignalTipHTML(el, lang) {
      const key = el.dataset.signalTip;
      const tBundle = SIGNAL_TIPS[key];
      if (!tBundle) return '';
      const t = tBundle[lang === 'en' ? 'en' : 'zh'];
      const builder = LIVE_BUILDERS[key];
      const { liveHTML, stage } = builder ? builder(el, t, lang) : { liveHTML: '', stage: null };
      return `
        <div class="stt-title">${t.title}</div>
        <div class="stt-desc">${_renderTipMarkdown(t.desc)}</div>
        ${liveHTML}
        <div class="stt-stages">${renderStageRows(t.stages, stage)}</div>
        <div class="stt-hint">${_renderTipMarkdown(t.hint)}</div>
      `;
    }

    function showSignalTip(el) {
      const key = el.dataset.signalTip;
      if (!SIGNAL_TIPS[key]) return;
      const lang = (window.UI && window.UI.currentLang) || 'zh';
      tip.innerHTML = buildSignalTipHTML(el, lang);

      tip.style.opacity = '0';
      tip.style.top = '-9999px';
      tip.classList.add('visible');
      requestAnimationFrame(() => {
        const rect = el.getBoundingClientRect();
        const tRect = tip.getBoundingClientRect();
        const gap = 8;
        let top = rect.bottom + gap;
        if (top + tRect.height > window.innerHeight - 8) top = rect.top - tRect.height - gap;
        let left = rect.left + (rect.width - tRect.width) / 2;
        left = Math.max(8, Math.min(left, window.innerWidth - tRect.width - 8));
        tip.style.top = top + 'px';
        tip.style.left = left + 'px';
        tip.style.opacity = '';
      });
    }

    function hideSignalTip() {
      tip.classList.remove('visible');
    }

    document.addEventListener('mouseover', e => {
      const el = e.target.closest('[data-signal-tip]');
      if (!el) return;
      if (_hideTimer) { clearTimeout(_hideTimer); _hideTimer = null; }
      showSignalTip(el);
    });
    document.addEventListener('mouseout', e => {
      const el = e.target.closest('[data-signal-tip]');
      if (!el) return;
      _hideTimer = setTimeout(hideSignalTip, 80);
    });
  }

  // Defer init until the #signal-tip-tooltip element exists in the DOM
  // (utils.js is loaded in <head>, before body content).
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
