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
    renderTodayVerdict(market, dashboardData = null) {
      const card = document.getElementById('today-verdict-card');
      if (!card || !market) return;
      const data = dashboardData || { market };
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
      const fmt = (v, suffix = '') => {
        if (v === null || v === undefined || v === '') return '—';
        return `${typeof v === 'number' ? Number(v).toFixed(v % 1 ? 1 : 0) : v}${suffix}`;
      };
      const colorByScore = (score, inverse = false) => {
        if (score === null || score === undefined || Number.isNaN(Number(score))) return '#a1a1aa';
        const n = Number(score);
        const good = inverse ? n <= 35 : n >= 60;
        const bad = inverse ? n >= 65 : n < 40;
        if (good) return '#22c55e';
        if (bad) return '#ef4444';
        return '#eab308';
      };
      const asList = (items, mapper) => (items || []).map(mapper).join('');
      const attrStr = (attrs) => Object.entries(attrs || {})
        .filter(([, v]) => v !== null && v !== undefined && v !== '')
        .map(([k, v]) => `${k}="${UI.escapeHTML(String(v))}"`)
        .join(' ');
      const miniGauge = ({ value, color, display, suffix }) => {
        const n = Number.isFinite(Number(value)) ? Math.max(0, Math.min(100, Number(value))) : 0;
        const C = 100;
        const dash = (n / 100) * C;
        return `<div class="relative w-14 h-14 shrink-0" style="color:${color}">
          <svg viewBox="0 0 36 36" class="w-14 h-14 -rotate-90">
            <circle cx="18" cy="18" r="15.9" fill="none" stroke="currentColor" stroke-opacity="0.14" stroke-width="3"></circle>
            <circle cx="18" cy="18" r="15.9" fill="none" stroke="currentColor" stroke-width="3"
              stroke-linecap="round" stroke-dasharray="${dash.toFixed(1)} ${C}"></circle>
          </svg>
          <div class="absolute inset-0 flex flex-col items-center justify-center leading-none">
            <span class="text-[11px] font-black">${UI.escapeHTML(display)}</span>
            ${suffix ? `<span class="text-[8px] font-bold mt-0.5 opacity-80">${UI.escapeHTML(suffix)}</span>` : ''}
          </div>
        </div>`;
      };
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
        ['tv-briefing','tv-conflict-card','tv-catalysts-card'].forEach(id => $(id)?.classList.add('hidden'));
        ['tv-signal-grid'].forEach(id => { const el = $(id); if (el) el.innerHTML = ''; });
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

      const br = data.breadth || {};
      const ftd = data.ftd || {};
      const mt = data.market_top || {};
      const fred = data.fred_macro || {};
      const fredSignals = fred.regime_signals || {};
      const fredScores = fred.macro_scores || {};
      const signalGrid = $('tv-signal-grid');
      const briefing = $('tv-briefing');
      const ftdDay = ftd.days_since_ftd;
      const ftdConfirmed = ftd.state === 'FTD_CONFIRMED' && ftdDay != null;
      const ftdStage = !ftdConfirmed ? null
        : ftdDay <= 5 ? { zh: '黃金', en: 'PRIME', pct: 100, color: '#22c55e' }
        : ftdDay <= 12 ? { zh: '主升', en: 'STD', pct: 78, color: '#eab308' }
        : ftdDay <= 20 ? { zh: '補漲', en: 'LATE', pct: 52, color: '#f97316' }
        : { zh: '過熱', en: 'HOT', pct: 22, color: '#ef4444' };
      const signalCards = [
        {
          label: isZh ? '建議曝險' : 'Exposure',
          value: market.exposure_ceiling || br.exposure_ceiling || '—',
          sub: isZh ? '裁決上限' : 'verdict cap',
          color: sty.fg,
          gaugeValue: (() => {
            const nums = String(market.exposure_ceiling || br.exposure_ceiling || '').match(/\d+/g);
            return nums?.length > 1 ? (Number(nums[0]) + Number(nums[1])) / 2 : Number(nums?.[0] || 0);
          })(),
          gaugeDisplay: (() => {
            const nums = String(market.exposure_ceiling || br.exposure_ceiling || '').match(/\d+/g);
            return nums?.length ? `${nums[nums.length - 1]}%` : '—';
          })(),
          tip: 'exposure',
          attrs: { 'data-exposure': market.exposure_ceiling || br.exposure_ceiling || '' },
        },
        {
          label: isZh ? '廣度' : 'Breadth',
          value: fmt(br.score ?? market.breadth_score),
          sub: br.zone || market.cycle_phase || '—',
          color: colorByScore(br.score ?? market.breadth_score),
          gaugeValue: br.score ?? market.breadth_score,
          gaugeDisplay: fmt(br.score ?? market.breadth_score),
          tip: 'breadth',
          attrs: {
            'data-br-score': br.score ?? market.breadth_score ?? '',
            'data-br-zone': br.zone || '',
            'data-br-ceiling': br.exposure_ceiling || market.exposure_ceiling || '',
          },
        },
        {
          label: 'FTD',
          value: ftdConfirmed ? `Day ${ftdDay}` : (ftd.state || '—').replace(/_/g, ' '),
          sub: ftdStage ? (isZh ? `${ftdStage.zh}期` : ftdStage.en) : (ftd.signal || '—'),
          color: ftdStage?.color || colorByScore(ftd.quality_score),
          gaugeValue: ftdStage?.pct ?? 0,
          gaugeDisplay: ftdConfirmed ? `D${ftdDay}` : '—',
          gaugeSuffix: ftdStage ? (isZh ? ftdStage.zh : ftdStage.en) : '',
          tip: 'ftd',
          attrs: {
            'data-ftd-state': ftd.state || '',
            'data-ftd-date': ftd.ftd_date || '',
            'data-ftd-day': ftd.days_since_ftd ?? '',
          },
        },
        {
          label: isZh ? '頂部風控' : 'Top Risk',
          value: fmt(mt.composite_score),
          sub: mt.zone || mt.risk_budget || '—',
          color: colorByScore(mt.composite_score, true),
          gaugeValue: mt.composite_score,
          gaugeDisplay: fmt(mt.composite_score),
          tip: 'market_top',
          attrs: {
            'data-mt-score': mt.composite_score ?? '',
            'data-mt-zone': mt.zone || '',
            'data-mt-budget': mt.risk_budget || '',
          },
        },
        {
          label: 'Macro',
          value: fred.regime_label || '—',
          sub: fredSignals.real_rate_preferred != null ? `real ${Number(fredSignals.real_rate_preferred).toFixed(2)}%` : `score ${fmt(fredScores.composite)}`,
          color: fred.regime_label === 'Overheating' ? '#f97316' : colorByScore(fredScores.composite),
          gaugeValue: fredScores.composite ?? 50,
          gaugeDisplay: fred.regime_label === 'Overheating' ? (isZh ? '熱' : 'HOT') : fmt(fredScores.composite),
          gaugeSuffix: fredSignals.real_rate_preferred != null ? `${Number(fredSignals.real_rate_preferred).toFixed(1)}%` : '',
          attrs: {
            'data-tip-key': 'macro_briefing_tip',
            'data-tip-text': isZh
              ? `FRED macro regime = ${fred.regime_label || '—'}。綜合利率、通膨、就業、信用與金融條件；Overheating 代表通膨/利率壓力偏高，通常壓抑高估值成長股與長天期資產。Real rate ${fmt(fredSignals.real_rate_preferred, '%')}。`
              : `FRED macro regime = ${fred.regime_label || '—'}. Composite of rates, inflation, employment, credit, and financial conditions; Overheating means rate/inflation pressure is elevated and usually weighs on high-multiple growth and duration assets. Real rate ${fmt(fredSignals.real_rate_preferred, '%')}.`,
            title: isZh
              ? `FRED macro regime: ${fred.regime_label || '—'} · composite ${fmt(fredScores.composite)} · real rate ${fmt(fredSignals.real_rate_preferred, '%')}`
              : `FRED macro regime: ${fred.regime_label || '—'} · composite ${fmt(fredScores.composite)} · real rate ${fmt(fredSignals.real_rate_preferred, '%')}`,
          },
        },
        {
          label: isZh ? '二元事件' : 'Binary',
          value: fmt((data.binary_risks || []).filter(r => r.within_48h).length),
          sub: isZh ? '48h 內' : 'within 48h',
          color: (data.binary_risks || []).some(r => r.within_48h) ? '#f59e0b' : '#22c55e',
          gaugeValue: (data.binary_risks || []).some(r => r.within_48h) ? 80 : 15,
          gaugeDisplay: fmt((data.binary_risks || []).filter(r => r.within_48h).length),
          attrs: {
            'data-tip-key': 'binary_derated_tip',
            title: isZh ? '48 小時內二元風險事件數' : 'Binary risk events within 48 hours',
          },
        },
      ];
      if (signalGrid) {
        signalGrid.innerHTML = signalCards.map(s => `
          <div class="rounded-lg border px-3 py-2 min-h-[76px] flex items-center gap-3" ${s.tip ? `data-signal-tip="${s.tip}"` : ''} ${attrStr(s.attrs)}
               style="border-color:${s.color}38;background:${s.color}10">
            ${miniGauge({ value: s.gaugeValue, color: s.color, display: s.gaugeDisplay || s.value, suffix: s.gaugeSuffix })}
            <div class="min-w-0">
              <div class="text-[9px] font-black uppercase tracking-widest text-zinc-500">${UI.escapeHTML(s.label)}</div>
              <div class="text-[14px] font-black leading-tight mt-1 truncate" style="color:${s.color}" title="${UI.escapeHTML(String(s.value))}">${UI.escapeHTML(String(s.value))}</div>
              <div class="text-[10px] text-zinc-500 truncate mt-0.5" title="${UI.escapeHTML(String(s.sub))}">${UI.escapeHTML(String(s.sub))}</div>
            </div>
          </div>`).join('');
      }

      const conflictCard = $('tv-conflict-card');
      if (conflictCard) {
        const conflictBits = [];
        if (ftd.exposure_range && (br.exposure_ceiling || market.exposure_ceiling)) {
          conflictBits.push(`${isZh ? 'FTD 建議' : 'FTD'} ${ftd.exposure_range} vs ${isZh ? '廣度/裁決' : 'breadth/verdict'} ${br.exposure_ceiling || market.exposure_ceiling}`);
        }
        if ((market.warning_flags_v2 || market.warning_flags || []).length) {
          const flags = (market.warning_flags_v2 || []).map(f => f.key).concat(market.warning_flags || []).slice(0, 3);
          conflictBits.push(flags.join(' · '));
        }
        if (br.components_full?.divergence?.signal) conflictBits.push(br.components_full.divergence.signal);
        conflictCard.classList.toggle('hidden', !conflictBits.length);
        if (conflictBits.length) conflictCard.setAttribute('title', conflictBits.join('\n'));
        conflictCard.innerHTML = conflictBits.length ? `
          <div class="text-[9px] font-black uppercase tracking-widest text-zinc-500 mb-2">${isZh ? '為什麼不是 Risk-On' : 'Why not risk-on'}</div>
          <ul class="space-y-1 text-[11px] leading-snug">
            ${asList(conflictBits.slice(0, 3), b => `<li class="flex gap-1.5"><span class="text-amber-500 shrink-0">!</span><span>${UI.escapeHTML(b)}</span></li>`)}
          </ul>` : '';
      }

      const catalystsCard = $('tv-catalysts-card');
      const catalysts = (market.top_catalysts || []).slice(0, 3);
      if (catalystsCard) {
        catalystsCard.classList.toggle('hidden', !catalysts.length);
        if (catalysts.length) catalystsCard.setAttribute('title', catalysts.map(c => c.event || '').join('\n'));
        catalystsCard.innerHTML = catalysts.length ? `
          <div class="text-[9px] font-black uppercase tracking-widest text-zinc-500 mb-2">${isZh ? '今日市場在交易什麼' : 'What market trades today'}</div>
          <ul class="space-y-1 text-[11px] leading-snug">
            ${asList(catalysts, c => `<li class="flex gap-1.5"><span class="text-blue-400 shrink-0">#${UI.escapeHTML(c.rank || '')}</span><span>${UI.escapeHTML(c.event || '')}</span></li>`)}
          </ul>` : '';
      }

      briefing?.classList.toggle('hidden', !(signalGrid || conflictCard || catalystsCard));

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
      const isPreview = item.decision === 'PREVIEW' || item.report_type === 'pre_earnings';
      const statusColor = isBuy ? 'var(--status-bullish)'
                        : isStaged ? 'var(--status-binary)'
                        : isCancel ? 'var(--status-bearish)'
                        : isPreview ? '#f59e0b'  // amber-500: matches 📋 前瞻 button
                        : 'var(--text-muted)';
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
