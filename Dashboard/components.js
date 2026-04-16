/**
 * components.js — INTEL COMMAND Shared Render Components
 * ARCH-2: Pure HTML-string render functions for reuse across pages.
 * All functions return DOM elements or HTML strings; no side-effects.
 */
(function () {
  'use strict';

  window.Components = {

    // ── Progress Bar ──────────────────────────────────────────────────────
    // Returns an HTML string for a thin progress bar.
    progressBar(pct, color, height = '1.5') {
      const w = Math.min(100, Math.max(0, pct));
      return `<div class="w-full h-${height} rounded-full bg-zinc-200 dark:bg-zinc-800">
        <div class="h-${height} rounded-full transition-all duration-700" style="width:${w}%;background-color:${color}"></div>
      </div>`;
    },

    // ── Badge ─────────────────────────────────────────────────────────────
    // Returns an HTML string for a small status badge.
    badge(label, color, extraClass = '') {
      return `<span class="px-2 py-0.5 rounded text-[10px] font-black border ${extraClass}"
        style="background-color:color-mix(in srgb,${color},transparent 88%);border-color:color-mix(in srgb,${color},transparent 78%);color:${color}">
        ${UI.escapeHTML(label)}
      </span>`;
    },

    // ── Flag Badge ────────────────────────────────────────────────────────
    // Returns an HTML string for a warning-flag badge (critical vs. caution).
    flagBadge(flagKey, translations) {
      const tw = translations || {};
      const label = tw[flagKey] || flagKey.replace(/_/g, ' ');
      const isCrit = flagKey.includes('Death_Cross') || flagKey.includes('Extreme_Fear') || flagKey.includes('Critical');
      return `<div class="text-[9px] font-bold px-2 py-1 rounded border truncate ${
        isCrit ? 'bg-red-500/10 text-red-400 border-red-500/25' : 'bg-yellow-500/8 text-yellow-500 border-yellow-500/20'
      }">${UI.escapeHTML(label)}</div>`;
    },

    // ── Audit Card ────────────────────────────────────────────────────────
    // Returns a DOM element. compact=true → single-row list item; false → full card.
    renderAuditCard(item, compact = false) {
      const isBuy     = item.decision === 'BUY' || item.decision === 'EXECUTE';
      const isStaged  = item.decision === 'STAGED' || item.decision === 'STAGED_ENTRY' || item.decision === 'STAGED_EXIT';
      const isCancel  = item.decision === 'CANCEL' || item.decision === 'PASS' || item.decision === 'SELL';
      const statusColor = isBuy ? 'var(--status-bullish)'
                        : isStaged ? 'var(--status-binary)'
                        : isCancel ? 'var(--status-bearish)' : 'var(--text-muted)';
      const t = window.i18n?.[UI.currentLang] || {};
      const translatedDecision = t.status?.[item.decision] || item.decision;

      const el = document.createElement('div');

      if (compact) {
        el.className = 'glass-card px-4 py-3 flex items-center justify-between gap-4 hover:border-zinc-600/50 transition-all cursor-pointer';
        el.innerHTML = `
          <div class="flex items-center gap-3 min-w-0">
            <span class="text-lg font-black tracking-tighter shrink-0" style="color:var(--text-card-title)">${UI.escapeHTML(item.ticker)}</span>
            <span class="text-[9px] font-black px-2 py-0.5 rounded border shrink-0"
                  style="background:color-mix(in srgb,${statusColor},transparent 90%);border-color:color-mix(in srgb,${statusColor},transparent 75%);color:${statusColor}">
              ${UI.escapeHTML(translatedDecision)}
            </span>
            ${item.key_risks?.length ? `<span class="text-[9px] text-zinc-600 truncate hidden sm:block">${UI.escapeHTML(item.key_risks[0].replace(/_/g,' '))}</span>` : ''}
          </div>
          <div class="flex items-center gap-3 shrink-0">
            <span class="text-xl font-black tracking-tighter font-mono" style="color:var(--text-card-title)">${UI.escapeHTML(String(item.score))}</span>
            <button onclick="UI.viewReport('${UI.escapeHTML(item.report_url)}')"
                    class="w-8 h-8 rounded-lg bg-white dark:bg-zinc-900 border border-emerald-200 dark:border-zinc-800 text-emerald-600 dark:text-zinc-400 shadow-sm flex items-center justify-center hover:bg-emerald-500 hover:border-emerald-500 hover:text-white dark:hover:text-black hover:shadow-none transition-all">
              <i data-lucide="file-text" class="w-3.5 h-3.5"></i>
            </button>
          </div>`;
        return el;
      }

      // ── Full card ─────────────────────────────────────────────────────
      const s = t.sentiment_labels || {};
      const perfColor = (item.performance?.change ?? 0) >= 0 ? 'var(--status-bullish)' : 'var(--status-bearish)';
      const perfIcon  = (item.performance?.change ?? 0) >= 0 ? 'trending-up' : 'trending-down';

      const perfUI = item.performance
        ? `<div class="mt-4 pt-4 border-t border-zinc-900 flex justify-between items-center">
             <div class="text-[10px] text-zinc-500 font-bold uppercase tracking-wider">${window.i18n?.[UI.currentLang]?.overview?.backtest_pl || 'Backtest P/L'}</div>
             <div class="flex items-center gap-1 font-mono font-bold text-sm" style="color:${perfColor}">
               <i data-lucide="${perfIcon}" class="w-3 h-3"></i>
               ${item.performance.change > 0 ? '+' : ''}${item.performance.change}%
             </div>
           </div>` : '';

      const targetUI = item.targets?.tp
        ? `<div class="mt-4 flex gap-4 border-t border-zinc-200 dark:border-zinc-900/50 pt-3">
             <div class="flex-1">
               <p class="text-[8px] text-zinc-600 font-bold uppercase">${UI.escapeHTML(s.tp || 'TP')}</p>
               <p class="text-xs font-mono font-bold" style="color:var(--status-bullish)">$${UI.escapeHTML(String(item.targets.tp))}</p>
             </div>
             <div class="flex-1 border-l border-zinc-200 dark:border-zinc-900/50 pl-4">
               <p class="text-[8px] text-zinc-600 font-bold uppercase">${UI.escapeHTML(s.sl || 'SL')}</p>
               <p class="text-xs font-mono font-bold" style="color:var(--status-bearish)">$${UI.escapeHTML(String(item.targets.sl))}</p>
             </div>
           </div>`
        : (item.targets?.watch || item.targets?.entry
            ? `<div class="mt-4 border-t border-zinc-200 dark:border-zinc-900/50 pt-3">
                 <p class="text-[8px] text-zinc-600 font-bold uppercase">${UI.escapeHTML(item.targets.watch ? (s.watch || 'Watch') : (s.entry || 'Entry'))}</p>
                 <p class="text-xs font-mono font-bold" style="color:var(--status-binary)">${UI.escapeHTML(item.targets.watch || item.targets.entry)}</p>
               </div>` : '');

      const risksUI = item.key_risks?.length
        ? `<div class="mt-3 pt-3 border-t border-zinc-200 dark:border-zinc-900/50">
             <div class="flex flex-wrap gap-1.5">${item.key_risks.map(r =>
               `<span class="text-[9px] font-bold px-2 py-0.5 rounded bg-red-500/10 text-red-400 border border-red-500/20">${UI.escapeHTML(r.replace(/_/g,' '))}</span>`
             ).join('')}</div>
           </div>` : '';

      const condUI = ((item.decision === 'CANCEL' || isStaged) && item.watch_conditions)
        ? `<div class="mt-3 pt-3 border-t border-zinc-200 dark:border-zinc-900/50 space-y-1.5">
             <p class="text-[9px] font-black text-yellow-500 uppercase tracking-widest flex items-center gap-1">
               <i data-lucide="crosshair" class="w-3 h-3"></i> ${UI.escapeHTML(t.watchlist?.entry_triggers || '進場觸發條件')}
             </p>
             ${Object.entries(item.watch_conditions).map(([k,v]) =>
               `<div class="flex gap-2 items-start">
                  <span class="text-[9px] font-black uppercase tracking-widest mt-0.5 shrink-0 w-14" style="color:var(--status-binary)">${UI.escapeHTML(k.toUpperCase())}</span>
                  <span class="text-[10px] leading-relaxed" style="color:var(--text-main)">${UI.escapeHTML(v)}</span>
                </div>`
             ).join('')}
           </div>` : '';

      el.className = 'glass-card p-6 flex flex-col justify-between group hover:border-zinc-500/50 transition-all cursor-default';
      el.innerHTML = `
        <div class="flex justify-between items-start mb-4">
          <div>
            <h4 class="text-2xl font-black tracking-tighter" style="color:var(--text-card-title)">${UI.escapeHTML(item.ticker)}</h4>
            <p class="text-[10px] text-zinc-500 font-mono">${UI.escapeHTML(item.time)}</p>
          </div>
          <span class="px-2 py-1 rounded text-[10px] font-black border transition-all"
                style="background-color:color-mix(in srgb,${statusColor},transparent 90%);border-color:color-mix(in srgb,${statusColor},transparent 80%);color:${statusColor}">
            ${UI.escapeHTML(translatedDecision)}
          </span>
        </div>
        <div class="flex items-end justify-between mt-2">
          <div class="relative group/score inline-block">
            <p class="text-[9px] text-zinc-500 font-bold uppercase tracking-widest border-b-2 border-dotted border-zinc-700 cursor-help pb-0.5 mb-1 hover:border-emerald-500/50 transition-colors">
              Model Score
            </p>
            <p class="text-3xl font-bold tracking-tighter" style="color:var(--text-card-title)">${UI.escapeHTML(String(item.score))}</p>
            <div class="absolute bottom-full left-0 mb-4 w-72 p-5 border border-zinc-200 dark:border-zinc-800 rounded-2xl shadow-xl opacity-0 group-hover/score:opacity-100 transition-all duration-300 pointer-events-none z-[999] backdrop-blur-2xl translate-y-4 group-hover/score:translate-y-0" style="background-color:var(--bg-card);color:var(--text-main)">
              <div class="text-[10px] font-black text-emerald-500 uppercase mb-3 flex items-center gap-2 tracking-widest">
                <div class="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse"></div>
                Scoring Protocol V4.5
              </div>
              <ul class="text-[10px] text-zinc-500 dark:text-zinc-400 space-y-2.5 list-none p-0 leading-relaxed">
                <li class="flex gap-3"><span class="text-zinc-700 font-mono">01</span><span>Σ(Weight × Score × Conf)</span></li>
                <li class="flex gap-3"><span class="text-zinc-700 font-mono">02</span><span>Weights: Fundamental(30%), Tech(30%), News(20%), Sent(20%)</span></li>
                <li class="flex gap-3"><span class="text-zinc-700 font-mono">03</span><span>Analyst Range: -5 to +5 based on core skills</span></li>
                <li class="flex gap-3"><span class="text-zinc-700 font-mono">04</span><span>Market Regime Multiplier: 0.6x to 1.2x adjustment</span></li>
                <li class="flex gap-3"><span class="text-zinc-700 font-mono">05</span><span>Burry Gap Veto: Mandatory cancellation on extreme valuation misalign</span></li>
              </ul>
            </div>
          </div>
          <button onclick="UI.viewReport('${UI.escapeHTML(item.report_url)}')"
                  class="w-12 h-12 rounded-xl bg-white dark:bg-zinc-900 border border-emerald-200 dark:border-zinc-800 text-emerald-600 dark:text-zinc-100 flex items-center justify-center hover:bg-emerald-500 hover:border-emerald-500 hover:text-white dark:hover:text-black transition-all shadow-sm dark:shadow-xl active:scale-95 group/btn">
            <i data-lucide="file-text" class="w-5 h-5 group-hover/btn:scale-110 transition-transform"></i>
          </button>
        </div>
        ${targetUI}${risksUI}${condUI}${perfUI}`;
      return el;
    },
  };
})();
