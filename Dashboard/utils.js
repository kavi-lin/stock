/**
 * utils.js — INTEL COMMAND Shared Utilities
 * ARCH-1: theme / lang / log / viewReport / market status / icons / sidebar
 * All shared state & logic lives under window.UI
 */
(function () {
  'use strict';

  // Semantic release tag shown in sidebar footer. Bump on meaningful releases.
  // Cache-busting is handled separately by dashboard_server.py (mtime injection).
  const VERSION = 'V1.9.4';

  const NAV_ITEMS = [
    { id: 'index',     href: 'index.html',     icon: 'layout-dashboard', i18n: 'nav_dash',      zh: '總體儀表板' },
    { id: 'decisions', href: 'decisions.html', icon: 'gavel',            i18n: 'nav_decisions', zh: '決策中心' },
    { id: 'sector',    href: 'sector.html',    icon: 'pie-chart',        i18n: 'nav_sector',    zh: '產業掃描' },
    { id: 'news',      href: 'news.html',      icon: 'newspaper',        i18n: 'nav_news',      zh: '即時新聞' },
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

    // ── Toast + Clipboard Helper ─────────────────────────────────────────
    showToast(msg, type = 'info', ms = 4500) {
      let host = document.getElementById('ui-toast-host');
      if (!host) {
        host = document.createElement('div');
        host.id = 'ui-toast-host';
        host.className = 'fixed top-5 right-5 z-[200] flex flex-col gap-2 pointer-events-none';
        document.body.appendChild(host);
      }
      const color = type === 'error' ? 'border-red-500 text-red-300 bg-red-900/30'
                  : type === 'warn'  ? 'border-yellow-500 text-yellow-200 bg-yellow-900/30'
                                     : 'border-emerald-500 text-emerald-200 bg-emerald-900/30';
      const el = document.createElement('div');
      el.className = `px-4 py-3 rounded-xl border backdrop-blur-xl text-xs font-mono max-w-sm shadow-2xl pointer-events-auto animate-[slideIn_.3s_ease] ${color}`;
      el.innerHTML = msg;
      host.appendChild(el);
      setTimeout(() => { el.style.opacity = '0'; el.style.transition = 'opacity .3s'; }, ms - 300);
      setTimeout(() => el.remove(), ms);
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

    // ── HTML Escape ────────────────────────────────────────────────────────
    escapeHTML(str) {
      return String(str ?? '')
        .replace(/&/g, '&amp;').replace(/</g, '&lt;')
        .replace(/>/g, '&gt;').replace(/"/g, '&quot;');
    },

    // ── Sidebar Render ─────────────────────────────────────────────────────
    renderSidebar(activePage) {
      const aside = document.getElementById('sidebar');
      if (!aside) return;

      const navHTML = NAV_ITEMS.map(n => `
        <a href="${n.href}" class="sidebar-item${n.id === activePage ? ' active' : ''} flex items-center gap-3 px-3 py-2 rounded-md transition-all">
          <i data-lucide="${n.icon}" class="w-4 h-4"></i>
          <span data-i18n="${n.i18n}">${n.zh}</span>
        </a>`).join('');

      aside.innerHTML = `
        <div class="p-4 flex items-center justify-between gap-1">
          <div class="flex items-center gap-2">
            <div class="w-8 h-8 bg-green-500 rounded-lg flex items-center justify-center shrink-0">
              <i data-lucide="activity" class="text-black w-5 h-5"></i>
            </div>
            <h1 class="text-base font-black tracking-tighter uppercase italic line-clamp-1 pr-2">INTEL<span class="text-green-500">COMMAND</span></h1>
          </div>
          <button id="theme-toggle" class="p-1.5 rounded-lg border border-transparent hover:border-zinc-200 dark:hover:border-zinc-800 hover:bg-zinc-100 dark:hover:bg-zinc-900/50 transition-all group/theme">
            <i data-lucide="moon" class="w-3.5 h-3.5 text-zinc-500 group-hover/theme:text-yellow-500 transition-colors" id="theme-icon"></i>
          </button>
        </div>
        <nav class="flex-1 px-4 space-y-1">${navHTML}</nav>
        <div class="p-4 border-t border-zinc-200 dark:border-zinc-800 space-y-2">
          <button id="lang-toggle" class="w-full flex items-center justify-between px-3 py-2 rounded-md hover:bg-zinc-100 dark:hover:bg-zinc-900 transition-all text-xs font-bold text-zinc-400">
            <span id="lang-text">English</span>
            <i data-lucide="languages" class="w-3 h-3"></i>
          </button>
          <button id="show-logs" class="w-full flex items-center justify-between px-3 py-2 rounded-md hover:bg-zinc-100 dark:hover:bg-zinc-900 transition-all text-[10px] font-bold text-zinc-500 uppercase tracking-tighter">
            <span>System Logs</span><i data-lucide="terminal" class="w-3 h-3"></i>
          </button>
          <div class="pt-2 px-3 text-[8px] text-zinc-400 dark:text-zinc-700 font-mono tracking-widest border-t border-zinc-200 dark:border-zinc-900/50 mt-2">${VERSION}</div>
        </div>`;

      // Wire sidebar buttons immediately after DOM insertion
      document.getElementById('theme-toggle')?.addEventListener('click', () => UI.toggleTheme());
      document.getElementById('lang-toggle')?.addEventListener('click',  () => UI.toggleLang());
      document.getElementById('show-logs')?.addEventListener('click',    () =>
        document.getElementById('debug-console')?.classList.toggle('hidden'));
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
      } else if (s.status === 'running' && thisJob !== seenJob) {
        // Log start once
        UI.logToUI(`protocol ${s.name} started [${s.job_id}]`, 'info');
        localStorage.setItem(PROTO_SEEN_JOB, thisJob);
      }
    } catch { /* silent */ }
  }
  setInterval(pollProtocolStateMonitor, 3000);
  setTimeout(pollProtocolStateMonitor, 1500);

})();
