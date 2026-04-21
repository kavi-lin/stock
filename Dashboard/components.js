/**
 * components.js — INTEL COMMAND Shared Render Components
 * ARCH-2: Pure HTML-string render functions for reuse across pages.
 * All functions return DOM elements or HTML strings; no side-effects.
 */
(function () {
  'use strict';

  window.Components = {

    // ── Today's Verdict hero card ─────────────────────────────────────────
    // Mutates #today-verdict-card and its tv-* children. Used by both
    // index.html (總體儀表板) and sector.html (產業掃描).
    // i18n pulled from sector_page namespace (both pages share it).
    renderTodayVerdict(market) {
      const card = document.getElementById('today-verdict-card');
      if (!card || !market) return;
      const tr   = window.i18n?.[UI.currentLang]?.sector_page || {};
      const isZh = UI.currentLang === 'zh';

      const STANCE_STYLE = {
        AGGRESSIVE: { fg: '#22c55e', bg: 'rgba(34,197,94,0.15)', border: '#22c55e' },
        NEUTRAL:    { fg: '#eab308', bg: 'rgba(234,179,8,0.15)', border: '#eab308' },
        DEFENSIVE:  { fg: '#ef4444', bg: 'rgba(239,68,68,0.15)', border: '#ef4444' },
      };
      const ACTION_STYLE = {
        overweight:  { fg: '#22c55e', icon: '🟢', label: tr.tv_action_overweight  || '加碼' },
        underweight: { fg: '#fbbf24', icon: '🟠', label: tr.tv_action_underweight || '減碼' },
        avoid:       { fg: '#ef4444', icon: '🔴', label: tr.tv_action_avoid       || '避開' },
        wait:        { fg: '#eab308', icon: '🟡', label: tr.tv_action_wait        || '觀望' },
        neutral:     { fg: '#a1a1aa', icon: '⚪', label: tr.tv_action_neutral     || '中性' },
      };

      const tv = market.today_verdict;
      const $ = (id) => document.getElementById(id);

      // Build staleness badge — same logic on both pages so user always sees freshness.
      const vdateStr = market.verdict_date || (market.generated_at || '').slice(0, 10);
      let stalenessHTML = '';
      if (vdateStr) {
        const vd = new Date(vdateStr + 'T00:00:00');
        const today = new Date(); today.setHours(0, 0, 0, 0);
        const daysAgo = Math.round((today - vd) / 86400000);
        let col, label;
        if      (daysAgo <= 0)  { col = '#22c55e'; label = isZh ? '今日'        : 'today'; }
        else if (daysAgo === 1) { col = '#eab308'; label = isZh ? '昨日'        : '1d ago'; }
        else                    { col = '#ef4444'; label = isZh ? `${daysAgo} 天前` : `${daysAgo}d ago`; }
        const dateLabel = market.generated_at || vdateStr;
        stalenessHTML =
          `<span class="text-[10px] font-mono px-2 py-0.5 rounded inline-flex items-center gap-1"
                 style="background:${col}18;color:${col};border:1px solid ${col}40"
                 title="${UI.escapeHTML(dateLabel)}">📅 ${UI.escapeHTML(dateLabel.slice(0, 16))} · ${label}</span>`;
      }
      const confEl = $('tv-confidence');

      // Fallback path: no structured verdict — show session_notes prose if present
      if (!tv) {
        if (!market.notes) { card.classList.add('hidden'); return; }
        card.classList.remove('hidden');
        card.style.borderLeftColor = '#a1a1aa';
        $('tv-stance') && ($('tv-stance').textContent = '—');
        $('tv-headline') && ($('tv-headline').textContent = tr.tv_no_structured || '今日裁決（舊版快取，待下次掃描升級）');
        $('tv-one-liner') && ($('tv-one-liner').textContent = '');
        ['tv-takeaways','tv-actions','tv-watch'].forEach(id => { const el = $(id); if (el) el.innerHTML = ''; });
        if (confEl) confEl.innerHTML = stalenessHTML;
        const fb = $('tv-fallback');
        if (fb) { fb.classList.remove('hidden'); $('tv-fallback-text') && ($('tv-fallback-text').textContent = market.notes); }
        return;
      }

      // Structured path
      card.classList.remove('hidden');
      $('tv-fallback') && $('tv-fallback').classList.add('hidden');

      const stance = tv.stance || 'NEUTRAL';
      const sty = STANCE_STYLE[stance] || STANCE_STYLE.NEUTRAL;
      card.style.borderLeftColor = sty.border;

      const stanceEl = $('tv-stance');
      if (stanceEl) {
        stanceEl.textContent      = stance;
        stanceEl.style.background = sty.bg;
        stanceEl.style.color      = sty.fg;
      }

      $('tv-headline')  && ($('tv-headline').textContent  = tv.headline  || '');
      $('tv-one-liner') && ($('tv-one-liner').textContent = tv.one_liner || '');

      if (confEl) {
        const confHTML = tv.confidence != null
          ? `<span>conf ${(tv.confidence * 100).toFixed(0)}%</span>` : '';
        confEl.innerHTML = `${stalenessHTML ? stalenessHTML + '&nbsp;&nbsp;' : ''}${confHTML}`;
      }

      $('tv-takeaways') && ($('tv-takeaways').innerHTML =
        (tv.key_takeaways || []).map(k => `<li class="flex items-start gap-1.5"><span class="text-emerald-500 shrink-0">•</span><span>${UI.escapeHTML(k)}</span></li>`).join('') ||
        `<li class="text-zinc-600 italic">—</li>`);

      $('tv-actions') && ($('tv-actions').innerHTML =
        (tv.sector_actions || []).map(a => {
          const as = ACTION_STYLE[a.action] || ACTION_STYLE.neutral;
          const conf = a.confidence ? `<span class="text-[9px] text-zinc-500 ml-1">(${UI.escapeHTML(a.confidence)})</span>` : '';
          return `<li><div class="flex items-start gap-1.5"><span class="shrink-0">${as.icon}</span><div>
            <span class="font-bold" style="color:${as.fg}">${as.label}</span>
            <span class="font-medium" style="color:var(--text-main)">${UI.escapeHTML((a.sector||'').replace(/_/g,' '))}</span>${conf}
            ${a.reason ? `<div class="text-[10px] text-zinc-500 leading-snug mt-0.5">${UI.escapeHTML(a.reason)}</div>` : ''}
          </div></div></li>`;
        }).join('') || `<li class="text-zinc-600 italic">—</li>`);

      $('tv-watch') && ($('tv-watch').innerHTML =
        (tv.watch_next || []).map(w => `<li class="flex items-start gap-1.5"><span class="text-zinc-500 shrink-0">▸</span><span>${UI.escapeHTML(w)}</span></li>`).join('') ||
        `<li class="text-zinc-600 italic">—</li>`);
    },

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
        // Click anywhere on card → jump to decisions center + open history drill for this ticker
        el.addEventListener('click', (ev) => {
          if (ev.target.closest('button, a')) return;
          window.location.href = `decisions.html?ticker=${encodeURIComponent(item.ticker)}`;
        });
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
            <button onclick="event.stopPropagation(); UI.viewReport('${UI.escapeHTML(item.report_url)}')"
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
