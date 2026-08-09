/**
 * utils.js — INTEL COMMAND Shared Utilities
 * ARCH-1: theme / lang / log / viewReport / market status / icons / sidebar
 * All shared state & logic lives under window.UI
 */
(function () {
  'use strict';

  // Semantic release tag shown in sidebar footer. Bump on meaningful releases.
  // Cache-busting is handled separately by dashboard_server.py (mtime injection).
  const VERSION = 'V4.116.2';

  // V1.71.x — group field enables sectioned sidebar layout
  const NAV_ITEMS = [
    { id: 'index',     href: 'index.html',     icon: 'layout-dashboard', i18n: 'nav_dash',      zh: '總體儀表板', group: 'market' },
    { id: 'sector',    href: 'sector.html',    icon: 'pie-chart',        i18n: 'nav_sector',    zh: '產業掃描',   group: 'market' },
    { id: 'news',      href: 'news.html',      icon: 'newspaper',        i18n: 'nav_news',      zh: '即時新聞',   group: 'market' },
    { id: 'break-news',href: 'break-news.html',icon: 'radio',            i18n: 'nav_break_news',zh: '突發辯論',   group: 'market' },
    { id: 'mood',      href: 'mood.html',      icon: 'gauge',            i18n: 'nav_mood',      zh: '市場氛圍',   group: 'market' },
    { id: 'intraday-eval', href: 'intraday-eval.html', icon: 'crosshair', i18n: 'nav_intraday_eval', zh: '盤中', group: 'market' },
    { id: 'x-kol',     href: 'x-kol.html',     icon: 'megaphone',        i18n: 'nav_x_kol',     zh: 'X KOL',      group: 'market' },

    { id: 'momentum',  href: 'momentum.html',  icon: 'trending-up',      i18n: 'nav_momentum',  zh: '動能選股',   group: 'stock' },
    { id: 'radar',     href: 'radar.html',     icon: 'radar',            i18n: 'nav_radar',     zh: '短期雷達',   group: 'stock' },
    { id: 'earnings',  href: 'earnings.html',  icon: 'bar-chart-3',      i18n: 'nav_earnings',  zh: '財報分析',   group: 'stock' },
    { id: 'backtest',  href: 'backtest.html',  icon: 'flask-conical',    i18n: 'nav_backtest',  zh: '策略回測',   group: 'stock' },

    { id: 'decisions', href: 'decisions.html', icon: 'gavel',            i18n: 'nav_decisions', zh: '決策中心',   group: 'portfolio' },
    { id: 'reports',   href: 'reports.html',   icon: 'file-text',        i18n: 'nav_reports',   zh: '投資報告',   group: 'portfolio' },
    { id: 'calendar',  href: 'calendar.html',  icon: 'calendar-days',    i18n: 'nav_calendar',  zh: '決策日曆',   group: 'portfolio' },
    { id: 'graph',     href: 'graph.html',     icon: 'network',          i18n: 'nav_graph',     zh: '知識圖譜',   group: 'portfolio' },
    { id: 'supply-chain', href: 'supply-chain.html', icon: 'git-fork',    i18n: 'nav_supply_chain', zh: '供應鏈', group: 'portfolio' },
    { id: 'playbook',  href: 'playbook.html',  icon: 'wallet',           i18n: 'nav_playbook',  zh: '投資方案',   group: 'portfolio' },

    { id: 'office',    href: 'office.html',    icon: 'building-2',        i18n: 'nav_office',    zh: 'AI 辦公室',  group: 'ops' },
    { id: 'ops',       href: 'ops.html',       icon: 'terminal',          i18n: 'nav_ops',       zh: 'Script 工具箱', group: 'ops' },
  ];

  const NAV_GROUPS = [
    { key: 'market',    zh: '市場',  en: 'MARKET',    icon: 'globe-2' },
    { key: 'stock',     zh: '個股',  en: 'STOCK',     icon: 'target' },
    { key: 'portfolio', zh: '組合',  en: 'PORTFOLIO', icon: 'briefcase' },
    { key: 'ops',       zh: '工具',  en: 'OPS',       icon: 'wrench' },
  ];

  // ── Exposure ceiling tiers — THE single threshold table (V4.111.0) ───────
  // One number ("what % of the portfolio may be deployed") used to carry four
  // disagreeing definitions: the exposure guide said 85/60/30, the synth guide
  // and the sector pill said 75/50/25, and the verdict card ignored the value
  // entirely and coloured itself by the verdict *stance* — which is why a
  // 75-90% ceiling rendered red while its own tooltip called it standard.
  //
  // 75/50/25 wins because two of the three tables already used it, and because
  // it is the boundary the synth formula (min of three midpoints) was written
  // against. Everything that classifies an exposure figure now reads this list:
  // the tooltip stage tables, the sector pill scale, and the verdict card.
  //
  // Ranges are on the **midpoint** of the ceiling: a cap is published as a band
  // ("75-90%") and the midpoint is what positions it. Colour, gauge fill, and
  // gauge number all derive from that one value, so they cannot drift apart.
  const EXPOSURE_TIERS = [
    { key: 'ex_full', min: 75, max: 100, color: '#22c55e', dot: '🟢',
      zh: { range_label: '75-100%', tag: '進攻', action: '滿倉操作',
            detail: '三訊號全綠，cash 0-25%，新進不限制，可加碼領導股' },
      en: { range_label: '75-100%', tag: 'Aggressive', action: 'Full size',
            detail: 'All 3 signals green, cash 0-25%, no entry limits, can add to leaders' } },
    { key: 'ex_standard', min: 50, max: 74, color: '#eab308', dot: '🟡',
      zh: { range_label: '50-75%', tag: '標準', action: '正常配置',
            detail: '主升段或訊號小幅雜訊，留 25-50% 現金，新進需挑高 RS 標的' },
      en: { range_label: '50-75%', tag: 'Standard', action: 'Normal',
            detail: 'Uptrend or minor signal noise — hold 25-50% cash, prefer high-RS names' } },
    { key: 'ex_defensive', min: 25, max: 49, color: '#f97316', dot: '🟠',
      zh: { range_label: '25-50%', tag: '防禦', action: '降倉、選股',
            detail: '至少一個訊號明顯轉弱，cash 50-75%，僅留高 conviction 個股' },
      en: { range_label: '25-50%', tag: 'Defensive', action: 'Cut & select',
            detail: 'At least one signal clearly weakening — cash 50-75%, high-conviction only' } },
    { key: 'ex_minimal', min: 0, max: 24, color: '#ef4444', dot: '🔴',
      zh: { range_label: '0-25%', tag: '極低', action: 'Cash 為主',
            detail: '訊號明顯偏空或已 critical，幾乎不開新倉、等下次 FTD' },
      en: { range_label: '0-25%', tag: 'Minimal', action: 'Cash priority',
            detail: 'Bearish or already critical — barely any new entries, wait for next FTD' } },
  ];

  // ── Signal tiers — THE threshold tables for the verdict cards (V4.111.1) ─
  // Same disease EXPOSURE_TIERS cured, two cards over: the tooltips carried
  // real 5-tier tables while the cards coloured themselves with a generic
  // `colorByScore(n, inverse)` whose only breakpoints were 35/65. Market top
  // 31.6 therefore rendered green while its own tooltip — and its own
  // `zone: "Yellow (Early Warning)"` — called it an early warning. None of the
  // generic helper's cut points matched any tooltip's, and it had no orange
  // tier at all where market top has two.
  //
  // `range` tiers classify a 0-100 score; `label` tiers classify a categorical
  // regime string. Both carry the prose the tooltip stage table renders, so a
  // tier cannot be recoloured without its explanation moving with it.
  const SIGNAL_TIERS = {
    // Higher = healthier. Unchanged thresholds — these were already correct in
    // the tooltip; it is the card that was reading a different table.
    breadth: { kind: 'range', tiers: [
      { key: 'br_strong', min: 75, max: 100, color: '#22c55e', dot: '🟢',
        zh: { range_label: 'score 75+', tag: '健康強勢', action: '全力進攻', detail: '多數成分股健康突破，可以高倉位、新進不限制' },
        en: { range_label: 'score 75+', tag: 'Strong', action: 'Full attack', detail: 'Most stocks healthy & breaking out — full size, no entry restrictions' } },
      { key: 'br_healthy', min: 60, max: 74, color: '#22c55e', dot: '🟢',
        zh: { range_label: 'score 60-75', tag: '主升中段', action: '標準參與', detail: '行情仍在主升段，標準倉位 + 一般停損即可' },
        en: { range_label: 'score 60-75', tag: 'Healthy', action: 'Standard', detail: 'Uptrend intact — standard size + stop' } },
      { key: 'br_neutral', min: 40, max: 59, color: '#eab308', dot: '🟡',
        zh: { range_label: 'score 40-60', tag: '訊號混合', action: '選股、降倉', detail: '多空交雜，僅選 RS 強標的 + 倉位降 25%' },
        en: { range_label: 'score 40-60', tag: 'Neutral', action: 'Selective', detail: 'Mixed signals — high-RS only + size −25%' } },
      { key: 'br_weakening', min: 25, max: 39, color: '#f97316', dot: '🟠',
        zh: { range_label: 'score 25-40', tag: '走弱中', action: '防禦為主', detail: '個股普遍轉弱，避免新進、現有倉位收緊停損' },
        en: { range_label: 'score 25-40', tag: 'Weakening', action: 'Defensive', detail: 'Stocks broadly weakening — no new entries + tighten stops' } },
      { key: 'br_critical', min: 0, max: 24, color: '#ef4444', dot: '🔴',
        zh: { range_label: 'score < 25', tag: '行情危險', action: '退守 cash', detail: '多數股票破位，cash 為王、保留資金等下次 FTD' },
        en: { range_label: 'score < 25', tag: 'Critical', action: 'Cash priority', detail: 'Most stocks breaking down — cash priority, wait for next FTD' } },
    ] },

    // Higher = MORE topping risk. The inversion lives in the table, not in a
    // boolean argument at each call site — which is how the card ended up
    // asking for `inverse` and still getting the wrong tier.
    market_top: { kind: 'range', tiers: [
      { key: 'mt_normal', min: 0, max: 29, color: '#22c55e', dot: '🟢',
        zh: { range_label: 'score 0-30', tag: '正常', action: '可進攻', detail: '暫無頂部訊號，廣度與領導同步，倉位上限可拉滿' },
        en: { range_label: 'score 0-30', tag: 'Normal', action: 'Attack', detail: 'No topping signals, breadth + leadership aligned, full size OK' } },
      { key: 'mt_warning', min: 30, max: 49, color: '#eab308', dot: '🟡',
        zh: { range_label: 'score 30-50', tag: '早期警告', action: '留意', detail: '個別訊號出現（如 distribution day 累積），上限不變但需密切觀察' },
        en: { range_label: 'score 30-50', tag: 'Early warning', action: 'Watch', detail: 'Isolated signals (e.g. distribution days) — size unchanged but monitor' } },
      { key: 'mt_elevated', min: 50, max: 64, color: '#f97316', dot: '🟠',
        zh: { range_label: 'score 50-65', tag: '風險升高', action: '降倉、收緊', detail: '訊號累積中，倉位上限調降至 60-80%、停損收緊' },
        en: { range_label: 'score 50-65', tag: 'Elevated', action: 'Cut & tighten', detail: 'Signals stacking — cap at 60-80%, tighten stops' } },
      { key: 'mt_high', min: 65, max: 79, color: '#f97316', dot: '🟠',
        zh: { range_label: 'score 65-80', tag: '高機率頂部', action: '撤退中', detail: '明確頂部訊號，倉位上限 40-60%、僅留高 conviction 標的' },
        en: { range_label: 'score 65-80', tag: 'High risk', action: 'Retreat', detail: 'Clear top signals — cap at 40-60%, keep only high-conviction names' } },
      { key: 'mt_top', min: 80, max: 100, color: '#ef4444', dot: '🔴',
        zh: { range_label: 'score 80+', tag: '頂部成形', action: 'Cash 優先', detail: '訊號全到位，倉位上限 ≤ 30%、現金為主等修正' },
        en: { range_label: 'score 80+', tag: 'Top formed', action: 'Cash priority', detail: 'All signals tripped — cap ≤30%, cash priority, wait for correction' } },
    ] },

    // Categorical. `labels` are the ten values validate_phase0.VALID_REGIMES
    // admits; anything outside that set classifies as null rather than being
    // bucketed by guesswork, so a renamed regime shows grey instead of a
    // confident wrong colour. Grouping approved by the user 2026-08-08.
    macro: { kind: 'label', tiers: [
      { key: 'mc_benign', color: '#22c55e', dot: '🟢',
        labels: ['Goldilocks', 'Soft Landing', 'Reflation', 'Benign Easing'],
        zh: { range_label: 'benign', tag: '順風', action: '正常配置', detail: 'Goldilocks / Soft Landing / Reflation / Benign Easing — 通膨與利率壓力不強，成長股與長天期資產不受壓抑' },
        en: { range_label: 'benign', tag: 'Tailwind', action: 'Normal', detail: 'Goldilocks / Soft Landing / Reflation / Benign Easing — rate & inflation pressure contained, growth and duration unpenalised' } },
      { key: 'mc_transition', color: '#eab308', dot: '🟡',
        labels: ['Transitional', 'Recession Easing'],
        zh: { range_label: 'transition', tag: '過渡', action: '看其他訊號', detail: 'Transitional / Recession Easing — 體制未定或衰退中政策已轉鬆（落底過程），macro 不主導，靠廣度與 FTD 決策' },
        en: { range_label: 'transition', tag: 'In flux', action: 'Defer to others', detail: 'Transitional / Recession Easing — regime unsettled or policy easing into a downturn; let breadth and FTD lead' } },
      { key: 'mc_tightening', color: '#f97316', dot: '🟠',
        labels: ['Overheating', 'Late Cycle Tightening'],
        zh: { range_label: 'tightening', tag: '緊縮', action: '壓抑成長股', detail: 'Overheating / Late Cycle Tightening — 通膨或利率壓力偏高，高估值成長與長天期資產首當其衝，偏好現金流與定價權' },
        en: { range_label: 'tightening', tag: 'Tightening', action: 'Growth penalised', detail: 'Overheating / Late Cycle Tightening — rate/inflation pressure elevated; high-multiple growth and duration hit first, favour cash flow and pricing power' } },
      { key: 'mc_stress', color: '#ef4444', dot: '🔴',
        labels: ['Stagflation', 'Recession Risk'],
        zh: { range_label: 'stress', tag: '壓力', action: '防禦', detail: 'Stagflation / Recession Risk — 成長與通膨同時不利或信用轉壞，降低整體曝險、避開高槓桿與景氣循環股' },
        en: { range_label: 'stress', tag: 'Stress', action: 'Defensive', detail: 'Stagflation / Recession Risk — growth and inflation both adverse or credit deteriorating; cut exposure, avoid leverage and cyclicals' } },
    ] },
  };

  window.UI = {
    VERSION,
    EXPOSURE_TIERS,
    SIGNAL_TIERS,

    // ── Signal tier helpers ──────────────────────────────────────────────
    // `value` is a 0-100 score for range signals, a regime string for label
    // signals. Returns null for missing/unknown input so callers render grey
    // rather than committing to a tier they cannot justify.
    signalTier(signal, value) {
      const spec = SIGNAL_TIERS[signal];
      if (!spec || value === null || value === undefined || value === '') return null;
      if (spec.kind === 'label') {
        const v = String(value).trim().toLowerCase();
        return spec.tiers.find(t => t.labels.some(l => l.toLowerCase() === v)) || null;
      }
      const n = Number(value);
      if (Number.isNaN(n)) return null;
      return spec.tiers.find(t => n >= t.min && n <= t.max)
          || (n > 100 ? spec.tiers.find(t => t.max === 100) : spec.tiers.find(t => t.min === 0))
          || null;
    },

    // Colour for a card/gauge. Grey when the tier is unknown — the one honest
    // answer when the value is missing or the regime name is unrecognised.
    signalColor(signal, value) {
      return UI.signalTier(signal, value)?.color || '#a1a1aa';
    },

    // Tier rows in the shape the tooltip stage tables expect.
    signalStages(signal, lang) {
      const spec = SIGNAL_TIERS[signal];
      if (!spec) return [];
      const l = lang === 'en' ? 'en' : 'zh';
      return spec.tiers.map(t => ({
        key: t.key,
        range: spec.kind === 'range' ? [t.min, t.max] : null,
        labels: t.labels || null,
        ...t[l],
      }));
    },

    // ── Exposure ceiling helpers ─────────────────────────────────────────
    // `"75-90%"` → 82.5. A ceiling is published as a band; the midpoint is the
    // single number every consumer positions on (see EXPOSURE_TIERS). Returns
    // null for anything unparseable so callers can show "—" instead of a 0%
    // that would read as "go to cash".
    exposureMid(raw) {
      const nums = String(raw ?? '').match(/\d+(?:\.\d+)?/g);
      if (!nums || !nums.length) return null;
      return nums.length > 1
        ? (Number(nums[0]) + Number(nums[1])) / 2
        : Number(nums[0]);
    },

    // Tier for a numeric midpoint (not a raw band string — call exposureMid
    // first). Clamps rather than returning null for out-of-range input: a
    // ceiling above 100 or below 0 is bad data, but "off the top" is still
    // unambiguously the top tier.
    exposureTier(mid) {
      if (mid === null || mid === undefined || Number.isNaN(Number(mid))) return null;
      const v = Number(mid);
      return EXPOSURE_TIERS.find(t => v >= t.min && v <= t.max)
          || (v > 100 ? EXPOSURE_TIERS[0] : EXPOSURE_TIERS[EXPOSURE_TIERS.length - 1]);
    },

    // Tier rows in the shape the tooltip stage tables expect.
    exposureStages(lang) {
      const l = lang === 'en' ? 'en' : 'zh';
      return EXPOSURE_TIERS.map(t => ({ key: t.key, range: [t.min, t.max], ...t[l] }));
    },

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
      // Shows the language currently in force, not the one clicking switches
      // to. It used to be a standalone toggle button where "English" meant
      // "switch to English"; as a settings row next to "主題 · 深色" the same
      // text would read as a statement of current state, so now it is one.
      const langEl = document.getElementById('lang-text');
      if (langEl) langEl.textContent = UI.currentLang === 'zh' ? '繁體中文' : 'English';
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
          <button id="settings-toggle" class="sidebar-icon-btn" title="${isZh ? '設定' : 'Settings'}">
            <i data-lucide="settings" class="w-3.5 h-3.5"></i>
          </button>

          <!-- V4.111.2 — theme / risk / language / logs all moved off the
               footer and behind this one gear. They are set-once controls; the
               footer they used to occupy is now the always-on quota panel,
               which is read constantly. -->
          <div id="settings-popup" class="sidebar-pop hidden">
            <button id="theme-toggle" class="sidebar-pop-row" type="button">
              <span class="sidebar-pop-label">
                <i data-lucide="moon" class="w-3 h-3" id="theme-icon"></i>
                ${isZh ? '主題' : 'Theme'}
              </span>
              <span id="theme-value" class="sidebar-pop-value"></span>
            </button>
            <button id="risk-toggle" class="sidebar-pop-row" type="button"
                    title="${isZh ? '點擊循環 LOW → MEDIUM → HIGH' : 'Click to cycle LOW → MEDIUM → HIGH'}">
              <span class="sidebar-pop-label">
                <i data-lucide="shield" class="w-3 h-3"></i>
                ${isZh ? '風險容忍' : 'Risk'}
              </span>
              <span id="risk-chip" class="sidebar-risk-chip">${UI.riskTolerance}</span>
            </button>
            <button id="lang-toggle" class="sidebar-pop-row" type="button">
              <span class="sidebar-pop-label">
                <i data-lucide="languages" class="w-3 h-3"></i>
                ${isZh ? '語言' : 'Language'}
              </span>
              <span id="lang-text" class="sidebar-pop-value">${isZh ? '繁體中文' : 'English'}</span>
            </button>
            <button id="show-logs" class="sidebar-pop-row" type="button">
              <span class="sidebar-pop-label">
                <i data-lucide="terminal" class="w-3 h-3"></i>
                ${isZh ? '系統日誌' : 'System logs'}
              </span>
              <span class="sidebar-pop-value">${isZh ? '開/關' : 'toggle'}</span>
            </button>
            <div class="sidebar-llm-help">
              <div>${isZh
                ? '額度由 quota broker 授權，它只派還有額度的一家，所以沒有「降級順序」可設。要改指派請編輯 <code>config/llm_config.json</code>。'
                : 'Quota is authorised by the broker, which only ever assigns a provider that has quota — there is no fallback order to configure. Edit <code>config/llm_config.json</code> to change assignments.'}</div>
              <div>${isZh
                ? '長條 = 該家最緊的窗口<strong>已用</strong>多少（越長越滿）；虛線是 broker 的硬保留線，越過它就不再派工。滑過任一家可看各窗口（5h / 週 / 本節）各自的長條、重置時間與今日花費。窗口百分比帶虛線底線的，代表該家只回報剩餘量、消費數字是推算的。'
                : 'Each bar is how much of that provider\'s tightest window is <strong>used</strong> — longer means fuller; the dashed line is the broker hard reserve, past which nothing is dispatched. Hover a provider for a bar per window (5h / weekly / session), reset times and spend. A dotted-underlined percentage means that provider reports only what is left, so consumption was inferred.'}</div>
              <div>${isZh
                ? '花費只有本地帳本有（broker 不報金額）。呼叫次數上限只有在 broker 關掉或連不上時才是真的限制，所以平常不顯示。'
                : 'Spend comes from the local ledger only — the broker does not report cost. The per-day call caps bind only when the broker is off or unreachable, so they stay hidden until then.'}</div>
            </div>
          </div>
        </div>

        <!-- Nav (grouped) -->
        <nav class="sidebar-nav">${groupsHTML}</nav>

        <!-- Footer: the quota panel and nothing else. Everything that used to
             sit above it is a set-once control and now lives behind the header
             gear; this is the part that is read on every glance. -->
        <div class="sidebar-footer">
          <div id="llm-panel" class="sidebar-llm">
            <div class="sidebar-llm-head">
              <span class="sidebar-llm-title">${isZh ? 'LLM 額度' : 'LLM QUOTA'}</span>
              <span id="llm-panel-state" class="sidebar-llm-state"></span>
            </div>
            <div id="llm-providers"></div>
            <div id="llm-foot" class="sidebar-llm-foot"></div>
          </div>
          <div class="sidebar-version">${VERSION}</div>
        </div>`;

      // Wire sidebar buttons immediately after DOM insertion
      const pop = document.getElementById('settings-popup');
      const closePop = () => pop?.classList.add('hidden');
      // Theme and language re-render the whole sidebar, which destroys this
      // popup mid-click. Reopening it afterwards keeps the menu where the user
      // left it — toggling theme should not also dismiss the menu they are in.
      document.getElementById('theme-toggle')?.addEventListener('click', () => {
        UI.toggleTheme(); UI._reopenSettings = true;
      });
      document.getElementById('lang-toggle')?.addEventListener('click', () => {
        UI.toggleLang(); UI._reopenSettings = true;
      });
      document.getElementById('show-logs')?.addEventListener('click', () => {
        document.getElementById('debug-console')?.classList.toggle('hidden');
        closePop();
      });
      document.getElementById('risk-toggle')?.addEventListener('click', () => UI.cycleRiskTolerance());
      document.getElementById('settings-toggle')?.addEventListener('click', (e) => {
        e.stopPropagation();
        pop?.classList.toggle('hidden');
      });
      // Dismiss on outside click / Escape. Bound once per page — renderSidebar
      // runs again on every theme and language toggle.
      if (!UI._settingsPopBound) {
        UI._settingsPopBound = true;
        document.addEventListener('click', (e) => {
          const p = document.getElementById('settings-popup');
          if (!p || p.classList.contains('hidden')) return;
          if (!e.target.closest?.('#settings-popup, #settings-toggle')) p.classList.add('hidden');
        });
        document.addEventListener('keydown', (e) => {
          if (e.key === 'Escape') document.getElementById('settings-popup')?.classList.add('hidden');
        });
      }
      if (UI._reopenSettings) { UI._reopenSettings = false; pop?.classList.remove('hidden'); }
      UI._paintRiskChip();
      UI._paintThemeValue();
      UI._initLlmPanel();
    },

    // Current theme spelled out in the settings row — the moon/sun icon alone
    // never said whether it meant "you are in dark" or "switch to dark".
    _paintThemeValue() {
      const el = document.getElementById('theme-value');
      if (!el) return;
      const zh = UI.currentLang === 'zh';
      el.textContent = UI.currentTheme === 'dark' ? (zh ? '深色' : 'Dark') : (zh ? '淺色' : 'Light');
    },

    // ── LLM quota panel (V4.111.0 — always visible) ──────────────────────
    // V4.109.0 made the broker the quota authority and turned this into a
    // read-only readout; it stayed folded inside the gear because it had been a
    // settings form. But quota is not a setting — it is the answer to "can I
    // launch a protocol right now", which is worth knowing before you click,
    // not after opening a panel. So it is always on, and the gear now holds
    // only the explanation.
    //
    // What each provider gets is a bar of its **tightest** window plus the
    // individual windows underneath, because the headline min hides the thing
    // you act on: claude at 54% is a weekly pool that will not move until
    // Aug 13, while gemini at 78% sits beside a 5h window that refills tonight.
    //
    // Assignments still live in config/llm_config.json (Python scripts read it,
    // so it was never localStorage) and POST /api/llm-config still works; only
    // this UI stopped writing to it.
    async _initLlmPanel() {
      const hostEl = document.getElementById('llm-providers');
      if (!hostEl) return;
      const stateEl = document.getElementById('llm-panel-state');
      const footEl  = document.getElementById('llm-foot');

      const ROUTE_LABELS = {
        general:  { zh: '一般',     en: 'general' },
        debate:   { zh: '辯手',     en: 'debate' },
        protocol: { zh: 'protocol', en: 'protocol' },
      };

      const esc = (s) => UI.escapeHTML(s);
      const pct = (p) => (p === null || p === undefined) ? '—' : `${Number(p).toFixed(0)}%`;

      // "gemini.weekly" → "gemini·週". Provider bucket names are namespaced and
      // inconsistent across CLIs; the segments that carry meaning are mapped and
      // the rest passed through rather than dropped, so an unfamiliar bucket
      // still shows up instead of silently vanishing.
      const bucketLabel = (b, zh) => {
        const parts = String(b.name || '').split('.').map(seg => {
          if (seg === 'five_hour')  return '5h';
          if (seg === 'weekly')     return zh ? '週' : 'wk';
          if (seg === 'session')    return zh ? '本節' : 'session';
          if (seg === 'all_models') return '';
          if (seg === 'claude_gpt') return 'gpt';
          if (seg === 'primary') {
            const w = Number(b.window_minutes);
            if (w >= 10080) return zh ? '週' : 'wk';
            if (w >= 1440)  return zh ? '日' : 'day';
            return zh ? '主池' : 'main';
          }
          return seg;
        }).filter(Boolean);
        return parts.join('·') || String(b.name || '?');
      };

      // One coarse unit, never two, never a decimal: "4d", "19h", "45m".
      // A quota panel is read to answer "roughly when does this free up" — the
      // ".6" in "3.6d" is precision the reading itself does not have, since the
      // snapshot behind it can already be minutes old.
      // 23h–24h collapses to "1d" so the hour branch never prints "24h".
      const shortDuration = (sec) => {
        const s = Number(sec);
        if (!Number.isFinite(s) || s <= 0) return '';
        if (s < 3600)  return `${Math.max(1, Math.round(s / 60))}m`;
        if (s < 82800) return `${Math.round(s / 3600)}h`;
        return `${Math.max(1, Math.round(s / 86400))}d`;
      };

      // Consumption, which is what the bars now draw. `used_percent` is the
      // provider's own reading and is used verbatim where it exists (claude,
      // codex). agy reports only what is left, so 100 − remaining is an
      // inference — flagged as `derived` so the hover card can say so instead
      // of passing it off as the provider's number.
      const usedOf = (b) => {
        const u = b.used_percent;
        if (u !== null && u !== undefined && Number.isFinite(Number(u))) {
          return { pct: Number(u), derived: false };
        }
        const r = b.remaining_percent;
        if (r === null || r === undefined || !Number.isFinite(Number(r))) {
          return { pct: null, derived: false };
        }
        return { pct: 100 - Number(r), derived: true };
      };

      // Providers report resets three different ways and never all three, and
      // the string form arrives however that CLI happened to print it — the
      // same broker payload carries both "Aug13at12pm" and "Aug 13 at 11:59am".
      // Normalised to one short form so a column of them can be compared at a
      // glance; the raw text stays in the row's title attribute.
      const MONTHS = { jan:1, feb:2, mar:3, apr:4, may:5, jun:6,
                       jul:7, aug:8, sep:9, oct:10, nov:11, dec:12 };
      // "Aug13at12pm(Asia/Taipei)" / "Aug 13 at 11:59am (Asia/Taipei)" /
      // "9:40am(Asia/Taipei)" → a Date, so an absolute label can be shown as
      // "4d" like every other window. Only claude reports this way and it gives
      // no seconds, so without this its rows are the only ones that cannot say
      // how far off the reset is.
      //
      // The label carries no year, and its timezone is the provider's rather
      // than the browser's. Both are tolerable at one-unit resolution, and the
      // raw string stays in the row's `title` as the thing to trust when they
      // disagree.
      const parseResetLabel = (raw) => {
        const s = String(raw || '').replace(/\s*\([^)]*\)\s*/g, '').trim();
        if (!s) return null;
        const time = s.match(/(\d{1,2})(?::(\d{2}))?\s*(am|pm)/i);
        if (!time) return null;
        let hh = Number(time[1]) % 12;
        if (/pm/i.test(time[3])) hh += 12;
        const md = s.match(/^([a-z]{3})[a-z]*\s*(\d{1,2})/i);
        const now = new Date();
        const at = new Date(now);
        if (md && MONTHS[md[1].toLowerCase()]) {
          at.setMonth(MONTHS[md[1].toLowerCase()] - 1, Number(md[2]));
        }
        at.setHours(hh, Number(time[2] || 0), 0, 0);
        // A reset is always ahead of now, so a time that lands in the past
        // belongs to the next occurrence — tomorrow for a bare clock time, next
        // year for a month/day that has already passed.
        if (at.getTime() <= now.getTime()) {
          if (md) at.setFullYear(at.getFullYear() + 1);
          else    at.setDate(at.getDate() + 1);
        }
        return at;
      };

      const resetHint = (b) => {
        const d = shortDuration(b.refresh_in_seconds);
        if (d) return d;
        const at = parseResetLabel(b.reset_label);
        if (at) {
          const rel = shortDuration((at.getTime() - Date.now()) / 1000);
          if (rel) return rel;
        }
        // Unparseable but present: show it as-is rather than blank. A window
        // whose reset is simply unknown and one whose label this code failed to
        // read must not look the same.
        return String(b.reset_label || '').replace(/\s*\([^)]*\)\s*/g, '').trim().replace(/\s+/g, ' ');
      };

      const ageLabel = (sec, zh) => {
        const s = Number(sec);
        if (!Number.isFinite(s)) return '';
        if (s < 90) return zh ? '剛更新' : 'just now';
        const d = shortDuration(s);
        return zh ? `${d}前` : `${d} ago`;
      };

      // One bar per provider. `state` drives colour: cooled-down and
      // reserve-only providers are dimmed because the broker will not send them
      // work, and a full-looking green bar on a provider nothing can use is the
      // single most misleading thing this panel could show.
      const providerRow = (model, info, routeTags, reserveLine, zh) => {
        // V4.115.0 — bars draw CONSUMPTION, matching the hover card and the
        // Claude Code usage panel this was modelled on. They used to draw what
        // was left, so a long green bar meant "healthy" here and "nearly out"
        // in every other quota UI the operator sees. One direction, everywhere.
        const remaining = info.remaining_percent;
        const has = remaining !== null && remaining !== undefined;
        const used = has ? 100 - Number(remaining) : null;
        const width = has ? Math.max(0, Math.min(100, used)) : 0;
        let state = 'ok', flag = '';
        if (info.cooldown_until)   { state = 'cool'; flag = zh ? '冷卻中' : 'cooldown'; }
        else if (info.reserve_only) { state = 'cool'; flag = zh ? '保留區' : 'reserve'; }
        else if (has && reserveLine !== null && width >= reserveLine) {
          state = 'low'; flag = zh ? '低於保留線' : 'below reserve';
        } else if (info.authenticated === false) {
          state = 'off'; flag = zh ? '未登入' : 'no auth';
        }

        // Only route tags this provider does NOT share with every other one —
        // a chip that appears on every row cannot tell the rows apart. See the
        // universal-route filter in render().
        const tags = routeTags.length
          ? `<div class="sidebar-llm-tags">${routeTags
              .map(t => `<span class="sidebar-llm-tag">${esc(t)}</span>`).join('')}</div>`
          : '';

        // The always-on row is deliberately just: who, what state, how much
        // left. Window-by-window detail, freshness and spend all live in the
        // hover card (llmTipHTML) — kept out of the sidebar so the three bars
        // stay scannable, which is the whole point of the panel being pinned.
        return `<div class="sidebar-llm-prov sidebar-llm-${state}" data-llm-prov="${esc(model)}"
                     title="${esc(zh ? `已用 ${pct(used)}／剩餘 ${pct(remaining)}`
                                     : `${pct(used)} used / ${pct(remaining)} left`)}">
          <div class="sidebar-llm-prov-head">
            <span class="sidebar-llm-prov-name">${esc(model)}</span>
            ${flag ? `<span class="sidebar-llm-flag">${esc(flag)}</span>` : ''}
            <span class="sidebar-llm-prov-pct">${pct(used)}</span>
          </div>
          <div class="sidebar-llm-bar">
            <div class="sidebar-llm-bar-fill" style="width:${width}%"></div>
            ${reserveLine !== null ? `<div class="sidebar-llm-bar-reserve" style="left:${reserveLine}%"></div>` : ''}
          </div>
          ${tags}
        </div>`;
      };

      // Hover card for one provider: every window it has (not just the two
      // tightest), where each resets, how old the reading is, and what this
      // provider has cost today. `usage` is the local ledger row — the broker
      // reports percentages and never money, so spend can only come from here.
      const llmTipHTML = (model, info, usage, reserveLine, routeTags, zh) => {
        // Each window gets its own bar. The windows were text-only rows, which
        // made "63% weekly" and "6% session" scan as the same size of problem;
        // the whole reason a provider's rows are worth opening is that they are
        // not. Bars draw consumption, same direction as the pinned panel.
        const rows = (info.buckets || []).map(b => {
          const u = usedOf(b);
          const width = u.pct === null ? 0 : Math.max(0, Math.min(100, u.pct));
          const hint = resetHint(b);
          const raw = String(b.reset_label || '').trim();
          const tip = [
            u.derived ? (zh ? '由剩餘量推算' : 'derived from remaining') : '',
            raw,
          ].filter(Boolean).join(' · ');
          return `<div class="llm-tip-bkt"${tip ? ` title="${esc(tip)}"` : ''}>
            <span class="llm-tip-bkt-name">${esc(bucketLabel(b, zh))}</span>
            <span class="llm-tip-bkt-pct${u.derived ? ' llm-tip-bkt-derived' : ''}">${pct(u.pct)}</span>
            <span class="llm-tip-bkt-reset">${esc(hint)}</span>
          </div>
          <div class="llm-tip-bkt-bar"><div class="llm-tip-bkt-fill" style="width:${width}%"></div></div>`;
        }).join('') || `<div class="llm-tip-dim">${zh ? '無窗口資料' : 'no window data'}</div>`;

        // Head is name + plan + freshness on one line. The separate meta row
        // held `plan · confidence · age`; confidence moved into the title
        // because it qualifies the reading rather than being one, and the
        // headline percentage came out because the per-window numbers directly
        // below are the ones acted on.
        const age = ageLabel(info.age_seconds, zh);
        const headTip = info.confidence ? String(info.confidence) : '';
        // Product identity is neutral metadata, not quota health. The raw
        // provider plan code is intentionally ignored: only the broker's
        // public label and its best-known current model belong in UI copy.
        // A generic provider alias (`codex` under the CODEX heading) adds no
        // information. Keep transporting it for diagnostics, but show the
        // model only when the broker knows a more specific name.
        const currentModel = info.current_model
          && String(info.current_model).toLowerCase() !== String(model).toLowerCase()
          ? info.current_model : null;
        const identity = [info.plan_label, currentModel]
          .filter(Boolean).map(v => esc(String(v))).join(' · ');

        const t = (usage && usage.tokens) || {};
        const tok = (t.input || 0) + (t.output || 0) + (t.cache_read || 0) + (t.cache_write || 0);
        const fmtK = n => n >= 1e6 ? (n / 1e6).toFixed(1) + 'M' : n >= 1e3 ? Math.round(n / 1e3) + 'K' : String(n);
        const spend = (usage || tok)
          ? `<div class="llm-tip-foot">${zh ? '今日' : 'today'} ${(usage && usage.calls) || 0} ${zh ? '次' : 'calls'}`
            + `${tok ? ` · ${fmtK(tok)} tok` : ''}`
            + `${t.cost_usd ? ` · $${Number(t.cost_usd).toFixed(2)}` : ''}</div>`
          : '';

        // No hard-reserve line here: the user asked for that sentence gone, and
        // the gear help already explains what the dashed marker on the bar is.
        return `<div class="llm-tip-head"${headTip ? ` title="${esc(headTip)}"` : ''}>
            <span class="llm-tip-name">${esc(model)}</span>
            <span class="llm-tip-age">${esc(age)}</span>
          </div>
          ${identity ? `<div class="llm-tip-identity">${identity}</div>` : ''}
          <div class="llm-tip-bkts">${rows}</div>
          ${routeTags.length ? `<div class="llm-tip-routes">${esc(routeTags.join(' · '))}</div>` : ''}
          ${spend}`;
      };

      const notice = (cls, main, sub) =>
        `<div class="sidebar-llm-notice sidebar-llm-${cls}"><span>${esc(main)}</span><span>${esc(sub)}</span></div>`;

      // Local call counters. Only rendered when the broker is NOT the authority
      // — that is the one situation where `calls / daily_max` is the limit that
      // actually stops a run. While the broker is up they describe a fallback
      // nobody is on, and showing "2/300" next to a refusing broker is how an
      // operator concludes there is plenty of room when there is none.
      const localCallsHTML = (status, zh) => {
        const models = (status && status.models) || {};
        return ['claude', 'gemini', 'codex', 'grok'].map(m => {
          const s = models[m] || {};
          let tag = '', cls = 'ok';
          if (!s.enabled)                                { tag = zh ? '停用' : 'off';   cls = 'off'; }
          else if (s.unavailable_reason === 'cooldown')  { tag = zh ? '冷卻中' : 'cooldown'; cls = 'cool'; }
          else if (s.unavailable_reason === 'budget')    { tag = zh ? '額度滿' : 'maxed'; cls = 'cool'; }
          return `<div class="sidebar-llm-row sidebar-llm-${cls}"><span>${esc(m)}</span>`
            + `<span>${s.calls || 0}/${s.daily_max || 0}${tag ? ' · ' + tag : ''}</span></div>`;
        }).join('');
      };

      // Spend is local-ledger-only — the broker reports percentages, never
      // money — so this line stays regardless of which path is in force.
      const spendHTML = (status, zh) => {
        const models = (status && status.models) || {};
        let tok = 0, cost = 0;
        Object.values(models).forEach(s => {
          const t = (s && s.tokens) || {};
          tok += (t.input || 0) + (t.output || 0) + (t.cache_read || 0) + (t.cache_write || 0);
          cost += Number(t.cost_usd || 0);
        });
        if (!tok && !cost) return '';
        const fmtK = n => n >= 1e6 ? (n / 1e6).toFixed(1) + 'M' : n >= 1e3 ? Math.round(n / 1e3) + 'K' : String(n);
        return `<div class="sidebar-llm-spend">`
          + `<span>${zh ? '今日' : 'today'}</span>`
          + `<span>$${cost.toFixed(2)} · ${fmtK(tok)} tok</span></div>`;
      };

      const render = (status) => {
        const zh = UI.currentLang === 'zh';
        const broker = (status || {}).broker;

        if (!broker) {
          // No `broker` key at all — not the same as "switched off". The usual
          // cause is a dashboard_server still running an older module (static
          // files reload per request, Python does not), so say the one thing
          // that fixes it rather than reporting a state nobody chose.
          if (stateEl) stateEl.textContent = '';
          hostEl.innerHTML = notice('cool', zh ? '讀不到 broker 狀態' : 'no broker status',
                                            zh ? '請重啟 dashboard_server' : 'restart dashboard_server');
          if (footEl) footEl.innerHTML = spendHTML(status, zh);
          return;
        }

        const authoritative = broker.enabled && broker.reachable === true;
        if (!authoritative) {
          const [main, sub] = !broker.enabled
            ? [zh ? 'broker 已關閉' : 'broker disabled', zh ? '改走本地預算' : 'local budget in force']
            // No last-known percentages on purpose: a number from an unknown
            // time reads as current and is exactly the false precision to avoid.
            : [zh ? 'broker 連不上' : 'broker unreachable', zh ? '決策流程停派' : 'decision flows halted'];
          if (stateEl) { stateEl.textContent = zh ? '降級' : 'degraded'; stateEl.className = 'sidebar-llm-state sidebar-llm-state-warn'; }
          hostEl.innerHTML = notice('cool', main, sub)
            + `<div class="sidebar-llm-sub">${zh ? '本地呼叫上限（此時才是真限制）' : 'Local call caps (binding now)'}</div>`
            + localCallsHTML(status, zh);
          if (footEl) footEl.innerHTML = spendHTML(status, zh);
          return;
        }

        const providers = broker.providers || {};
        // The broker states its hard reserve as a floor on what must remain
        // (20%). The bars now run on a consumption axis, so the same rule is the
        // ceiling 100 − 20 = 80% used. Converted once, here, rather than at each
        // use: leaving it as 20 while the bar fills the other way would put the
        // marker at the wrong end and flag every healthy provider as depleted.
        const reserveRaw = broker.hard_reserve_percent;
        const reserveLine = (reserveRaw === null || reserveRaw === undefined)
          ? null : Math.max(0, Math.min(100, 100 - Number(reserveRaw)));

        const names = Object.keys(providers);

        // Which dispatch paths each provider serves. Broker-decided routes list
        // candidates, not a winner — model_router.routes() explains why the UI
        // must not predict one — so those render as eligibility, not a promise.
        //
        // A route every provider is eligible for is dropped from the always-on
        // rows entirely: `debate` accepts all three, so it printed "辯手 候選·2"
        // on claude, gemini and codex alike — three chips that could not tell
        // the rows apart. What distinguishes them is the narrower routes
        // (general is pinned to claude, protocol excludes codex), and only
        // those stay on the row. The full list, universal routes included,
        // still shows in each provider's hover card.
        const tagsFor = {};      // row chips — distinguishing routes only
        const allTagsFor = {};   // hover card — every route this provider serves
        (broker.routes || []).forEach(route => {
          const label = (ROUTE_LABELS[route.key] || {})[zh ? 'zh' : 'en'] || route.key;
          if (route.decided_by === 'broker') {
            // "候選" not "will run": the broker picks at dispatch time from
            // whoever still has quota, and this list is the eligible set.
            const eligible = (route.eligible || []).filter(m => names.includes(m));
            const cand = zh ? '候選' : 'cand';
            const chip = route.picks > 1 ? `${label} ${cand}·${route.picks}` : `${label} ${cand}`;
            const isUniversal = names.length && eligible.length === names.length;
            eligible.forEach(m => {
              (allTagsFor[m] = allTagsFor[m] || []).push(chip);
              if (!isUniversal) (tagsFor[m] = tagsFor[m] || []).push(chip);
            });
          } else if (route.model) {
            (tagsFor[route.model] = tagsFor[route.model] || []).push(label);
            (allTagsFor[route.model] = allTagsFor[route.model] || []).push(label);
          }
        });
        if (!names.length) {
          hostEl.innerHTML = notice('cool', zh ? 'broker 無 provider' : 'no providers',
                                            zh ? '檢查 lqb 設定' : 'check lqb config');
        } else {
          // Tightest first — same order as the buckets, and the provider about
          // to run out is the one worth seeing without scrolling.
          names.sort((a, b) => {
            const pa = providers[a].remaining_percent, pb = providers[b].remaining_percent;
            return (pa === null || pa === undefined ? 101 : pa) - (pb === null || pb === undefined ? 101 : pb);
          });
          hostEl.innerHTML = names
            .map(m => providerRow(m, providers[m], tagsFor[m] || [], reserveLine, zh))
            .join('');
          // Hover content is built now, while the payload is in hand, and
          // stashed per model — the mouseover handler must not re-derive it
          // from the DOM it just wrote.
          UI._llmTips = {};
          names.forEach(m => {
            UI._llmTips[m] = llmTipHTML(
              m, providers[m], ((status || {}).models || {})[m],
              reserveLine, allTagsFor[m] || [], zh);
          });
        }

        if (stateEl) {
          const ages = names.map(m => Number(providers[m].age_seconds)).filter(Number.isFinite);
          const oldest = ages.length ? Math.max(...ages) : null;
          stateEl.textContent = oldest === null ? '' : ageLabel(oldest, zh);
          stateEl.className = 'sidebar-llm-state';
        }
        // Spend and the reserve-line legend moved into the hover cards; the
        // pinned panel keeps only bars.
        if (footEl) footEl.innerHTML = '';
      };

      const refresh = async () => {
        try {
          const cfg = await (await fetch('/api/llm-config')).json();
          render(cfg.status);
        } catch (e) {
          // A dashboard-server hiccup is not a quota statement. Leave whatever
          // is on screen and try again next tick rather than inventing a state.
        }
      };

      // Hover card. Bound once per page — renderSidebar() may run again on a
      // language toggle, and a second set of listeners would each show and hide
      // the same element, leaving it flickering.
      if (!UI._llmTipBound) {
        UI._llmTipBound = true;
        let tipEl = document.getElementById('llm-tip');
        if (!tipEl) {
          tipEl = document.createElement('div');
          tipEl.id = 'llm-tip';
          tipEl.className = 'llm-tip hidden';
          document.body.appendChild(tipEl);
        }
        let hideTimer = null;
        const show = (row) => {
          const html = (UI._llmTips || {})[row.dataset.llmProv];
          if (!html) return;
          if (hideTimer) { clearTimeout(hideTimer); hideTimer = null; }
          tipEl.innerHTML = html;
          tipEl.classList.remove('hidden');
          // Anchored to the right of the sidebar, then pulled back up if the
          // card would run off the bottom — the lowest provider row sits near
          // the viewport floor, which is exactly where it opens downward.
          const r = row.getBoundingClientRect();
          const h = tipEl.offsetHeight;
          tipEl.style.left = `${r.right + 10}px`;
          tipEl.style.top = `${Math.max(8, Math.min(r.top, window.innerHeight - h - 8))}px`;
        };
        const hide = () => { hideTimer = setTimeout(() => tipEl.classList.add('hidden'), 80); };
        document.addEventListener('mouseover', (e) => {
          const row = e.target.closest?.('[data-llm-prov]');
          if (row) show(row);
        });
        document.addEventListener('mouseout', (e) => {
          if (e.target.closest?.('[data-llm-prov]')) hide();
        });
      }

      await refresh();
      // Quota moves while the page sits open. The panel is always visible now,
      // so it always polls — but not while the tab is in the background, where
      // nobody can read it and every tick is a wasted broker round-trip.
      if (UI._llmPanelTimer) clearInterval(UI._llmPanelTimer);
      UI._llmPanelTimer = setInterval(() => { if (!document.hidden) refresh(); }, 30000);
      document.addEventListener('visibilitychange', () => { if (!document.hidden) refresh(); });
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
        const activeLabel = active.label || active.ticker || active.name || '?';
        lines.push(`<div class="proto-pill-row"><span class="proto-pill-row-icon">▶</span><span><strong>${activeLabel}</strong> · ${fmtElapsed(active.elapsed_sec)}</span></div>`);
      }
      for (const q of queue.slice(0, 5)) {
        const qLabel = q.label || q.params?.ticker || q.name || '?';
        lines.push(`<div class="proto-pill-row"><span class="proto-pill-row-icon">⏳</span><span><strong>${qLabel}</strong></span></div>`);
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

  const _CHAIN_GLYPH = { skipped: '✅', queued: '⏳', running: '🔄', done: '✅', degraded: '⚠️', error: '❌' };
  function _chainMeta(it, isZh) {
    const el = fmtElapsed(it.elapsed_sec || 0);
    switch (it.status) {
      case 'skipped': return isZh ? '已新鮮 · 跳過' : 'fresh · skipped';
      case 'queued':  return isZh ? '排隊中' : 'queued';
      case 'running': return `${isZh ? '執行中' : 'running'} · ${el}`;
      case 'done':    return `${isZh ? '完成' : 'done'} · ${el}`;
      case 'degraded': return `${isZh ? '降級完成，繼續' : 'degraded, continuing'} · ${el}`;
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
          stages: UI.signalStages('breadth', 'zh'),
          no_active: '廣度資料缺失或來源失敗',
          hint: '資料源：TraderMonty CSV (每日盤後更新，盤前看到的可能是 D-1 收盤值)',
        },
        en: {
          title: 'Market Breadth · How many stocks are still strong',
          desc:  'Composite of "% stocks above 200-day MA + 8-day MA delta + new highs vs lows + advance/decline gap" → 0-100 score. High = market is healthy (not just a few mega-caps holding it up); low = most stocks already weakening, dangerous.',
          stages: UI.signalStages('breadth', 'en'),
          no_active: 'Breadth data unavailable / source failed',
          hint: 'Source: TraderMonty CSV (updated post-close — pre-market values may be D-1)',
        },
      },
      synth: {
        zh: {
          title: '綜合曝險 · 三訊號合成的倉位上限',
          desc:  '把廣度建議倉位、FTD 倉位、頂部風控三個來源的中位數取「最保守者（最小值）」 → 得出可承受倉位上限。意義：當三訊號彼此衝突時（例如 breadth 還健康但頂部風險爆表），系統會自動偏向最保守那一個，避免單一訊號誤判。實際個股建倉以這個上限為基準再乘 sector / FTD timeline / tail risk 等其他乘數。',
          stages: UI.exposureStages('zh'),
          no_active: '至少一個訊號缺失，無法合成曝險上限',
          hint: '計算：min( breadth_ceiling中位數, ftd_range中位數, market_top_budget中位數 )',
        },
        en: {
          title: 'Synthesized Ceiling · Position cap from 3 signals',
          desc:  'Takes the midpoint of breadth ceiling, FTD range, and market top budget — uses the most conservative (lowest) one as your position cap. Why: when signals disagree (e.g. breadth healthy but topping signals are loud), the system auto-defers to the most cautious. Per-trade size = this cap × sector / FTD-timeline / tail-risk multipliers downstream.',
          stages: UI.exposureStages('en'),
          no_active: 'At least one signal missing — cap cannot be synthesized',
          hint: 'Formula: min( breadth_ceiling_mid, ftd_range_mid, market_top_budget_mid )',
        },
      },
      market_top: {
        zh: {
          title: '頂部風險 · 大盤是否已過熱',
          desc:  '綜合 distribution day（高量殺低天數）、領導股是否轉弱、防禦類股是否輪動進場、新高家數萎縮、Russell 2000 落後 SPY 程度等多類指標 → 合成 0-100 分。分數越高代表頂部訊號越多，需要降倉防範。與 breadth 互補：breadth 看「現在健康嗎」，這個看「快崩了嗎」。',
          stages: UI.signalStages('market_top', 'zh'),
          no_active: '頂部資料缺失或來源失敗',
          hint: '組合內部：distribution day / leadership / defensive rotation / 新高萎縮 等子分數',
        },
        en: {
          title: 'Market Top Risk · Is the market overheated',
          desc:  'Composite of distribution days, leadership deterioration, defensive sector rotation, new-high contraction, Russell 2000 lagging SPY, etc. → 0-100 risk score. Higher = more topping signals stacked, time to de-risk. Complementary to breadth: breadth = "is it healthy now", market top = "is it about to crack".',
          stages: UI.signalStages('market_top', 'en'),
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
          desc:  '由廣度、FTD、頂部三訊號合成的「整體投資組合最大倉位百分比」。意義：當前環境若你開到這個比例就是上限，不應再加碼；個股單筆建倉再從這個上限往下分配（依 sector 集中度、tail risk）。通常顯示為區間（如 75-90%）→ 取中位數定位。',
          stages: UI.exposureStages('zh'),
          no_active: '曝險上限資料缺失',
          hint: '與綜合曝險（synth）連動 — 個股倉位 = 此上限 × tail risk × sector cap × FTD multiplier',
        },
        en: {
          title: 'Exposure Cap · Max portfolio size',
          desc:  'Composite ceiling from breadth + FTD + top risk → max % of portfolio that should be deployed. Treat as a cap: do not add beyond this; per-trade size is allocated below this cap with further sector / tail-risk haircuts. Usually shown as a range (e.g. 75-90%) → midpoint determines stage.',
          stages: UI.exposureStages('en'),
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
      macro: {
        zh: {
          title: 'Macro 體制 · 利率與信用環境',
          desc:  'FRED 資料合成的總體體制判定，綜合利率、通膨、就業、信用與金融條件五個子分數。它不預測方向，而是說明**哪一類資產這段時間吃虧**：緊縮體制壓抑高估值成長與長天期資產，壓力體制則是整體降曝險。與其他訊號的分工——廣度/FTD 看盤面，這個看盤面背後的資金成本。',
          stages: UI.signalStages('macro', 'zh'),
          no_active: 'FRED macro 資料缺失或體制名稱無法辨識',
          hint: '子分數：rates / inflation / employment / credit / financial_conditions（加權合成 composite）',
        },
        en: {
          title: 'Macro Regime · Rates & credit backdrop',
          desc:  'FRED-derived regime call composed from five sub-scores: rates, inflation, employment, credit, and financial conditions. It does not predict direction — it says **which assets are penalised right now**: tightening regimes punish high-multiple growth and duration, stress regimes call for lower exposure outright. Division of labour: breadth and FTD read the tape; this reads the cost of money behind it.',
          stages: UI.signalStages('macro', 'en'),
          no_active: 'FRED macro data unavailable or regime label unrecognised',
          hint: 'Sub-scores: rates / inflation / employment / credit / financial_conditions (weighted into composite)',
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
      // ── V2.18 / V2.19 / V2.20 — Structural Shift + Lane Cross-Talk badges ──
      structural_shift_confirmed: {
        zh: {
          title: 'SHIFT⚡⚡ · 結構性轉變確認 (V2.18 CONFIRMED)',
          desc:  '**連 2 季皆 ≥2/3 signals 達標**，公司進入 paradigm shift 階段：\n\n**1. EPS QoQ ≥ 30%**：連兩季每股盈餘環比跳升\n**2. 毛利率 ≥ 歷史 8Q 平均 + 2σ**：margin breakout 不是噪音\n**3. 營收 YoY ≥ 25% AND 加速**：成長軌跡向上而非退坡\n\n**→ Phase 3 自動 modulation**：\n• Analyst PT 完全 unanchor (×0)\n• Red Team mean-reversion 攻擊 BLOCKED\n• sector_avoid 對個股失效 (macro_floor=1.0)\n• Position cap 100% (不縮)\n• Dynamic threshold: BUY ≥ 1.0 (從 1.2 降，更敢進)',
          stages: [],
          hint: 'CONFIRMED 是 MU/QCOM 類超級週期的訊號。V2.18 解的就是過去這類股票被 backward-looking lane 三重壓制錯失主升段的問題。',
        },
        en: {
          title: 'SHIFT⚡⚡ · Structural Shift CONFIRMED (V2.18)',
          desc:  '**2 consecutive quarters with ≥2/3 signals firing** — company entered paradigm shift:\n\n**1. EPS QoQ ≥ 30%** for both quarters\n**2. Gross margin ≥ historical 8Q mean + 2σ** (not noise)\n**3. Revenue YoY ≥ 25% AND accelerating**\n\n**→ Phase 3 auto-modulation**:\n• Analyst PT fully unanchored (×0)\n• Red Team mean-reversion attack BLOCKED\n• sector_avoid bypassed (macro_floor=1.0)\n• Position cap 100% (no cut)\n• Dynamic threshold: BUY ≥ 1.0 (lowered from 1.2)',
          stages: [],
          hint: 'CONFIRMED catches MU/QCOM-style super-cycles. V2.18 fixed the systemic miss where these stocks got crushed by backward-looking lanes.',
        },
      },
      structural_shift_candidate: {
        zh: {
          title: 'SHIFT⚡ · 結構性轉變候選 (V2.18 CANDIDATE)',
          desc:  '**最新 1 季 ≥2/3 signals 達標**，但上一季沒同步 → 待 confirm。\n\n**3 個 signals**：\n• EPS QoQ ≥ 30%\n• 毛利率 ≥ 歷史 +2σ\n• 營收 YoY ≥ 25% AND 加速\n\n**→ Phase 3 modulation (放寬不解除)**：\n• Analyst PT weight ×0.3 (stale 半折)\n• Red Team STRONG_COUNTER penalty ×0.925 (而非 0.85)\n• Macro multiplier floor = 0.95\n• Position cap 50% (半倉防 noise)\n• Dynamic threshold: BUY ≥ 1.1',
          stages: [],
          hint: '等下次 earnings 報出來：第二季再達標 → 升 CONFIRMED 解除全部 lock；第二季退潮 → 降回 NONE。',
        },
        en: {
          title: 'SHIFT⚡ · Structural Shift CANDIDATE (V2.18)',
          desc:  '**Latest quarter ≥2/3 signals fired**, but prior quarter did not — pending confirmation.\n\n**3 signals**:\n• EPS QoQ ≥ 30%\n• Gross margin ≥ historical +2σ\n• Revenue YoY ≥ 25% AND accelerating\n\n**→ Phase 3 modulation (relaxed, not removed)**:\n• Analyst PT weight ×0.3 (stale)\n• Red Team STRONG_COUNTER penalty ×0.925 (not 0.85)\n• Macro multiplier floor = 0.95\n• Position cap 50% (controls noise)\n• Dynamic threshold: BUY ≥ 1.1',
          stages: [],
          hint: 'Wait for next earnings: second quarter confirms → upgrade to CONFIRMED unlocks all caps; second quarter fizzles → revert to NONE.',
        },
      },
      polarization_bipolar: {
        zh: {
          title: 'BIPOLAR · 訊號兩極衝突 (V2.19)',
          desc:  '**5 lane 勢均力敵衝突**：\n• range ≥ 4 (max − min)\n• ≥2 lanes ≥ +1 AND ≥2 lanes ≤ −1\n• 至少 1 個 ≥+2 AND 1 個 ≤−2\n\n**→ Phase 3 Step 1.7 modulation**：\n• avg_confidence × 0.5 (CONFIRMED+bull macro 例外 ×0.7)\n• Position cap = 25% (砍倉至 1/4)\n• BUY → STAGED_ENTRY 強制降階\n• Dynamic threshold: BUY ≥ 1.5 (從 1.2 拉)',
          stages: [],
          hint: 'BIPOLAR + STAGED_ENTRY = 系統承認看不懂，用小部位試水溫。買對了少賺，買錯了少套。',
        },
        en: {
          title: 'BIPOLAR · Lane Polarization (V2.19)',
          desc:  '**5 lanes in genuine deadlock**:\n• range ≥ 4 (max − min)\n• ≥2 lanes ≥ +1 AND ≥2 lanes ≤ −1\n• ≥1 lane ≥+2 AND ≥1 lane ≤−2\n\n**→ Phase 3 Step 1.7 modulation**:\n• avg_confidence × 0.5 (CONFIRMED+bull macro: ×0.7)\n• Position cap = 25% (cut to 1/4)\n• Force BUY → STAGED_ENTRY\n• Dynamic threshold: BUY ≥ 1.5',
          stages: [],
          hint: 'BIPOLAR + STAGED_ENTRY = system admits low confidence, takes small toehold. Bounded loss either way.',
        },
      },
      polarization_outlier: {
        zh: {
          title: 'OUTLIER · 單一 lane 離群 (V2.20.0)',
          desc:  '**4-vs-1 離群值，不是真衝突**：\n• range ≥ 4 但少數方只有 1 lane\n• 例：[+4, +3, +3, +2, −2] — 4 lane 同向，1 個 outlier 站對立面\n\n**→ Phase 3 Step 1.7 modulation (輕微降，不像 BIPOLAR 砍倉)**：\n• avg_confidence × 0.85\n• Position cap 不動\n• Dynamic threshold: BUY ≥ 1.3\n• 標記 outlier_lane_id 給 user 檢視哪 lane 反對',
          stages: [],
          hint: 'V2.20.0 新增。修 V2.10 老 polarization rule 的 bug — 把 [+4,+3,+3,+2,-2] 誤判 BIPOLAR 砍倉，現在正確標 OUTLIER 輕微降權。',
        },
        en: {
          title: 'OUTLIER · Single-lane dissent (V2.20.0)',
          desc:  '**4-vs-1 outlier — not real deadlock**:\n• range ≥ 4 but minority side only 1 lane\n• Example: [+4, +3, +3, +2, −2] — 4 lanes aligned, 1 outlier dissents\n\n**→ Phase 3 Step 1.7 modulation (mild, not BIPOLAR-style cut)**:\n• avg_confidence × 0.85\n• Position cap unchanged\n• Dynamic threshold: BUY ≥ 1.3\n• Flags outlier_lane_id for user review',
          stages: [],
          hint: 'V2.20.0 fix for V2.10 polarization bug — [+4,+3,+3,+2,-2] used to be mislabeled BIPOLAR (cut position 75%); now correctly OUTLIER (mild penalty).',
        },
      },
      polarization_mixed: {
        zh: {
          title: 'MIXED · 訊號分歧 (V2.10)',
          desc:  '**雙邊都有但無極端值**：\n• range ≥ 3 AND 至少 1 正 1 負\n• 沒有 lane 達 ±2 極端\n\n**→ Phase 3 Step 1.7 modulation**：\n• avg_confidence × 0.75\n• Position cap 不動\n• Dynamic threshold 不改 (default 1.2)',
          stages: [],
          hint: 'MIXED 是中等不確定 — 比 OUTLIER 嚴 (×0.75 vs ×0.85)，比 BIPOLAR 鬆 (不砍倉)。',
        },
        en: {
          title: 'MIXED · Lane Disagreement (V2.10)',
          desc:  '**Both directions present, no extremes**:\n• range ≥ 3 AND ≥1 positive AND ≥1 negative\n• No lane reaches ±2\n\n**→ Phase 3 Step 1.7 modulation**:\n• avg_confidence × 0.75\n• Position cap unchanged\n• Dynamic threshold: default 1.2',
          stages: [],
          hint: 'MIXED is middle ground — stricter than OUTLIER (×0.75 vs ×0.85), looser than BIPOLAR (no position cut).',
        },
      },
      red_team_basis_mr_only: {
        zh: {
          title: 'RT MR-ONLY · Red Team 純歷史攻擊 (V2.19)',
          desc:  '**counter_thesis 只用 mean-reversion 關鍵字**：\n• "歷史均值" / "mean reversion"\n• "週期見頂" / "Peak Cycle"\n• "P/E ceiling" / "歷史毛利"\n• "回到歷史中位"\n\n**→ CONFIRMED tier 下自動降級**：\n• STRONG_COUNTER → MODERATE_COUNTER\n• Penalty 折半 (0.85 → 0.925)\n• 反方論點不放棄但威力減半',
          stages: [],
          hint: '這是 V2.18 設計時觀察到的 MU 案例核心問題：Red Team 用「歷史毛利只有 35%」殺掉 paradigm shift thesis。V2.19 anti-spoofing 直接 disable。',
        },
        en: {
          title: 'RT MR-ONLY · Red Team Pure Mean-Reversion Attack (V2.19)',
          desc:  '**counter_thesis uses only mean-reversion keywords**:\n• "historical mean" / "mean reversion"\n• "cycle peak" / "Peak Cycle"\n• "P/E ceiling" / "historical margin"\n\n**→ Auto-downgrade if CONFIRMED tier**:\n• STRONG_COUNTER → MODERATE_COUNTER\n• Penalty halved (0.85 → 0.925)\n• Counter not discarded but neutralized',
          stages: [],
          hint: 'Core MU pattern V2.18 was built to fix: Red Team killing paradigm shift theses with "historical margin only 35%". V2.19 anti-spoofing disables this attack.',
        },
      },
      red_team_basis_contaminated: {
        zh: {
          title: 'RT CONTAM · Red Team 偷渡 mr (V2.19)',
          desc:  '**counter_thesis 同時含 forward + mean-reversion 關鍵字**：\n• 表面 forward attack (新進入者 / 客戶庫存)\n• 偷渡 mr (歷史均值 / 週期高點)\n\n**→ V2.19 鐵律 — mr 一票否決**：\n• 不視為 mixed，視為 contaminated（污染）\n• CONFIRMED tier 下視同 pure_mean_reversion 自動降級\n• 1 個 fw 關鍵字無法救回 mr 否決權\n\n**設計理由**：防 LLM 故意塞 1 個 forward keyword 偽裝成 pure_forward 保留 STRONG_COUNTER 殺傷力。',
          stages: [],
          hint: 'Anti-spoofing 鐵律：mr keyword 一旦出現都觸發 dampening，無論搭配多少 fw keyword。命名強調污染而非平衡。',
        },
        en: {
          title: 'RT CONTAM · Red Team Smuggled mr (V2.19)',
          desc:  '**counter_thesis has BOTH forward + mean-reversion keywords**:\n• Surface looks forward (competitor / inventory)\n• Smuggles mr (historical mean / cycle peak)\n\n**→ V2.19 rule — mr veto**:\n• Treated as contaminated (not mixed)\n• Same handling as pure_mean_reversion under CONFIRMED tier\n• One fw keyword cannot rescue the veto\n\n**Why**: prevents LLM from gaming via 1 forward keyword wrapper to retain STRONG_COUNTER strength.',
          stages: [],
          hint: 'Anti-spoofing rule: any mr keyword present triggers dampening regardless of fw count. "Contamination" not "mix" — emphasis on pollution.',
        },
      },
      red_team_basis_pure_forward: {
        zh: {
          title: 'RT FWD · Red Team 純前瞻攻擊 (V2.19)',
          desc:  '**counter_thesis 只用 forward mechanism breakage 關鍵字**：\n• "competitor" / 量產時程 / 新進入者\n• 客戶庫存 / inventory days\n• 需求飽和 / 技術替代 / share loss\n\n**→ 健康反方論證 — V2.19 唯一保留 STRONG_COUNTER 殺傷力**：\n• standard penalty 0.85\n• 任何 tier 都 effective\n• Red Team 通過 anti-spoofing 檢驗',
          stages: [],
          hint: '看到 RT FWD 就放心 — Red Team 在做正確的事 (壓力測試未來 catalysts)，不是用過時歷史 pattern 攻擊。',
        },
        en: {
          title: 'RT FWD · Red Team Pure Forward Attack (V2.19)',
          desc:  '**counter_thesis uses only forward mechanism keywords**:\n• "competitor" / production timeline / new entrants\n• customer inventory / inventory days\n• demand saturation / tech substitution / share loss\n\n**→ Healthy counter — V2.19 only basis preserving STRONG_COUNTER**:\n• standard penalty 0.85\n• Effective at any tier\n• Passed anti-spoofing classifier',
          stages: [],
          hint: 'Seeing RT FWD = Red Team doing correct work (stress-testing future catalysts), not relying on stale historical patterns.',
        },
      },
      watchlist_bolt: {
        zh: {
          title: '⚡ · News Watchlist 候選 (V2.19)',
          desc:  '**News leading signal** — 過去 14 天 ≥2 個獨立 source 提及結構性 keyword：\n• "sold out" / "capacity constrained" / "supercycle"\n• "供不應求" / "structural deficit"\n• "capacity expansion"\n\n**→ V2.19 設計約束**：\n• 不入 Phase 3 modulation（純警覺 metadata）\n• 等 earnings-analyst 確認 CANDIDATE/CONFIRMED tier 才入決策\n• 21 天無新 hit 自動 evict\n\n**→ 跟 SHIFT badge 並現** = news + earnings 雙確認 = 最強 paradigm shift signal。',
          stages: [],
          hint: '⚡ 是 leading (news 早 1-2 週)，SHIFT 是 confirming (earnings 已實現)。Watchlist 提早警覺，等 earnings 確認才行動。',
        },
        en: {
          title: '⚡ · News Watchlist Candidate (V2.19)',
          desc:  '**News leading signal** — past 14 days ≥2 independent sources cite structural keywords:\n• "sold out" / "capacity constrained" / "supercycle"\n• "structural deficit" / "capacity expansion"\n\n**→ V2.19 design constraints**:\n• Does NOT drive Phase 3 modulation (advisory metadata only)\n• Earnings-analyst CANDIDATE/CONFIRMED required for decision impact\n• 21 days without new hit → auto-evict\n\n**→ Co-occurrence with SHIFT badge** = news + earnings double-confirm = strongest paradigm shift signal.',
          stages: [],
          hint: '⚡ is leading (news 1-2w early), SHIFT is confirming (earnings realized). Watchlist alerts early, earnings tier authorizes action.',
        },
      },
      watchlist_traj_confirmed: {
        zh: {
          title: '✓ CONFIRMED · Watchlist 已確認軌跡 (V2.20)',
          desc:  '**News leading signal 升至最高 confidence**：\n• earnings-analyst structural_shift.tier = CONFIRMED\n• 連 2 季 ≥2/3 signals (EPS QoQ / GM σ / rev accel) 達標\n\n**→ V2.18 Phase 3 全套 modulation 生效**\n**→ Watchlist 任務完成**：signal 已被 earnings 兌現',
          stages: [],
          hint: '這個 ticker 從 news leading signal 走完整 lifecycle 到 earnings 確認。最強形式的 paradigm shift 訊號。',
        },
        en: {
          title: '✓ CONFIRMED · Watchlist Trajectory (V2.20)',
          desc:  '**News leading signal upgraded to highest confidence**:\n• earnings-analyst structural_shift.tier = CONFIRMED\n• 2 consecutive quarters with ≥2/3 signals firing\n\n**→ V2.18 Phase 3 full modulation active**\n**→ Watchlist mission complete** — signal realized in earnings',
          stages: [],
          hint: 'Ticker walked full lifecycle from news leading signal to earnings confirmation. Strongest paradigm shift signal possible.',
        },
      },
      watchlist_traj_candidate: {
        zh: {
          title: '✓ CANDIDATE · Watchlist 候選軌跡 (V2.20)',
          desc:  '**News leading signal 已被 earnings 確認 CANDIDATE**：\n• earnings-analyst structural_shift.tier = CANDIDATE\n• 最新 1 季 ≥2/3 signals 達標\n\n**→ V2.18 Phase 3 modulation 已生效**\n**→ 等下次 earnings 升 CONFIRMED 或退回 NONE**',
          stages: [],
          hint: '中段確認。News 跟 earnings 已對齊，但需要連 2 季才升頂級。',
        },
        en: {
          title: '✓ CANDIDATE · Watchlist Trajectory (V2.20)',
          desc:  '**News leading signal confirmed at CANDIDATE tier**:\n• earnings-analyst structural_shift.tier = CANDIDATE\n• Latest 1 quarter with ≥2/3 signals\n\n**→ V2.18 Phase 3 modulation active**\n**→ Awaiting next earnings: upgrade to CONFIRMED or revert to NONE**',
          stages: [],
          hint: 'Mid-tier confirmation. News and earnings aligned, but 2 consecutive quarters required for top tier.',
        },
      },
      watchlist_traj_aging: {
        zh: {
          title: 'AGING · Watchlist 老化 (V2.20)',
          desc:  '**持續 watchlist 中 5+ 天但未升 tier**：\n• News 持續提到 (keyword hit count > 5)\n• earnings-analyst 還沒看到結構性跳躍\n\n**→ 兩種可能**：\n• 真 paradigm shift 醞釀中（等下次 earnings）\n• False positive 老化（IR boilerplate accumulation）\n\n**→ 21 天無新 hit 自動 evict**',
          stages: [],
          hint: 'AGING 是觀察指標 — 不是 buy 訊號。等 earnings 報出來才能判斷是真 shift 還是 noise。',
        },
        en: {
          title: 'AGING · Watchlist Aging (V2.20)',
          desc:  '**5+ days continued in watchlist without tier upgrade**:\n• News keeps citing (keyword hit count > 5)\n• earnings-analyst sees no structural break yet\n\n**→ Two possibilities**:\n• Real paradigm shift brewing (wait for next earnings)\n• False positive aging (IR boilerplate accumulation)\n\n**→ Auto-evict at 21 days without new hit**',
          stages: [],
          hint: 'AGING is observational — not a buy signal. Wait for earnings to distinguish real shift from noise.',
        },
      },
      watchlist_traj_new: {
        zh: {
          title: 'NEW · Watchlist 新進 (V2.20)',
          desc:  '**新進 watchlist (≤2 lifecycle events)**：\n• 還在累積 keyword hits\n• 14 天 hit 窗口\n\n**→ 觀察期**：\n• 21 天內若沒新 hit 會被 evict\n• 累積到 5+ continued 變 AGING\n• earnings 升 tier 變 CANDIDATE/CONFIRMED',
          stages: [],
          hint: '剛進場，還沒驗證。建議放 watchlist 觀察 1-2 週看走向。',
        },
        en: {
          title: 'NEW · Watchlist New Entry (V2.20)',
          desc:  '**Just entered watchlist (≤2 lifecycle events)**:\n• Still accumulating keyword hits\n• 14-day hit window active\n\n**→ Observation period**:\n• Evicts in 21 days without new hit\n• Becomes AGING after 5+ continued events\n• Becomes CANDIDATE/CONFIRMED if earnings upgrades tier',
          stages: [],
          hint: 'Fresh entry, unverified. Recommend 1-2 weeks of observation before any action.',
        },
      },
      verdict_strong: {
        zh: {
          title: 'STRONG · 體質強勁 (composite 80+)',
          desc:  '**4 大評分子項加總 ≥ 80/100**：\n• Quality (0-30) + Growth (0-30) + Value (0-25) + Analyst (0-15)\n\n**意義**：財報品質乾淨、成長動能足、估值合理、分析師看多 — 4 維度同時站住的罕見組合。',
          stages: [],
          hint: '罕見組合。Earnings 滿分區。投資論點要找的就是這種股。',
        },
        en: {
          title: 'STRONG · Robust (composite 80+)',
          desc:  '**4 score components total ≥ 80/100**:\n• Quality (0-30) + Growth (0-30) + Value (0-25) + Analyst (0-15)\n\n**Meaning**: clean financials + growth momentum + fair valuation + bullish analysts — rare 4-axis convergence.',
          stages: [],
          hint: 'Rare convergence. Top earnings tier. Target zone for thesis hunting.',
        },
      },
      verdict_solid: {
        zh: {
          title: 'SOLID · 穩健 (composite 65-79)',
          desc:  '**4 大評分子項加總 65-79**：多數面向健康但至少 1 軸有瑕疵（quality flag / 成長放緩 / 估值偏貴 / 分析師中性）。\n\n**意義**：值得分析但需聚焦弱項是否會擴大。',
          stages: [],
          hint: '主流區間，多數值得追蹤的股票落在這裡。看 score_components 哪一塊扣分。',
        },
        en: {
          title: 'SOLID · Stable (composite 65-79)',
          desc:  '**4 components total 65-79**: most axes healthy but ≥1 has weakness (quality flag / decelerating growth / rich valuation / neutral analysts).\n\n**Meaning**: worth analyzing but focus on whether weakness expands.',
          stages: [],
          hint: 'Mainstream range. Most watchlist-worthy names land here. Check score_components for the dragging axis.',
        },
      },
      verdict_mixed: {
        zh: {
          title: 'MIXED · 混合訊號 (composite 50-64)',
          desc:  '**4 大評分子項加總 50-64**：多軸出現警訊，至少 2 軸偏弱。\n\n**意義**：thesis 必須直面 trade-off — 為什麼還要進場？要看具體哪幾項在拉、哪些在拖。',
          stages: [],
          hint: 'MIXED 區間進場需要清楚的 catalyst 或 contrarian 論述，不能只憑「便宜」或「成長」。',
        },
        en: {
          title: 'MIXED · Mixed Signals (composite 50-64)',
          desc:  '**4 components total 50-64**: multi-axis warning signs, ≥2 axes weak.\n\n**Meaning**: thesis must address trade-offs — why enter despite weakness? Check which axes pull vs drag.',
          stages: [],
          hint: 'MIXED entry needs clear catalyst or contrarian thesis — cannot rely on "cheap" or "growth" alone.',
        },
      },
      verdict_weak: {
        zh: {
          title: 'WEAK · 體質疲軟 (composite 35-49)',
          desc:  '**4 大評分子項加總 35-49**：多軸偏弱、至少 1 軸亮紅燈（quality flag / 衰退成長 / 估值偏貴 / 分析師看空）。\n\n**意義**：除非有極強 contrarian 論述，否則不應為投資對象。可考慮列入 short / pair-trade short side 候選。',
          stages: [],
          hint: 'WEAK 是 quality screen 該排除的區間。少數例外：deep contrarian + 強 catalyst（e.g. activism / spinoff / 巨額回購）。',
        },
        en: {
          title: 'WEAK · Deteriorating (composite 35-49)',
          desc:  '**4 components total 35-49**: multi-axis weakness, ≥1 red flag (quality flag / shrinking growth / rich valuation / bearish analysts).\n\n**Meaning**: should not be investment target unless deep contrarian thesis with strong catalyst. Possible short / pair-trade short side candidate.',
          stages: [],
          hint: 'WEAK is the screen-out zone. Exceptions: deep contrarian + strong catalyst (activism / spinoff / large buyback).',
        },
      },
      theme_override_bolt: {
        zh: {
          title: '⚡ · 結構性轉變主題 (V2.20.0)',
          desc:  '**此 theme 內 ≥1 個代表性個股的 earnings 有 structural_shift tier**：\n• CANDIDATE: 1 季 ≥2/3 signals\n• CONFIRMED: 連 2 季 ≥2/3 signals\n\n**→ Theme heat 加分 (V2.19.2)**：\n• ≥1 CONFIRMED → +10\n• ≥2 CONFIRMED → +15 (cap)\n• ≥1 CANDIDATE 無 CONFIRMED → +5\n\n**→ Lifecycle stage 不誤判 Exhausting (V2.18)**：\n• maturity > 80 但有 paradigm shift → 降回 Mature\n• 防 sector_avoid 連坐殺好股\n\nHover badge 旁邊文字看哪些 ticker 觸發。',
          stages: [],
          hint: 'Theme 出現 ⚡ 代表 sector 內有 paradigm shift 進行中。對配置 sector 倉位、避免錯殺都有意義。',
        },
        en: {
          title: '⚡ · Paradigm Shift Theme (V2.20.0)',
          desc:  '**≥1 representative stock in this theme has earnings structural_shift tier**:\n• CANDIDATE: 1 quarter ≥2/3 signals\n• CONFIRMED: 2 consecutive quarters ≥2/3 signals\n\n**→ Theme heat bonus (V2.19.2)**:\n• ≥1 CONFIRMED → +10\n• ≥2 CONFIRMED → +15 (cap)\n• ≥1 CANDIDATE no CONFIRMED → +5\n\n**→ Lifecycle stage protected from Exhausting (V2.18)**:\n• maturity > 80 with paradigm shift → revert to Mature\n• Prevents sector_avoid from miscategorizing healthy stocks\n\nHover near badge to see triggering tickers.',
          stages: [],
          hint: 'Theme ⚡ = paradigm shift active in sector. Useful for sector allocation and avoiding false-positive sector avoid.',
        },
      },
      verdict_deteriorating: {
        zh: {
          title: 'DETERIORATING · 體質惡化 (composite < 35)',
          desc:  '**4 大評分子項加總 < 35**：多軸全面惡化，至少 2 軸亮紅燈。\n\n**意義**：避開區。除非是極端 deep value + activist catalyst，否則應視為地雷股。\n\n**典型場景**：\n• Quality flag 連發（accruals + capex burning + DSO + 負 FCF）\n• 衰退成長 + 估值仍貴（multiples 還沒 priced in）\n• 分析師大規模下調',
          stages: [],
          hint: 'DETERIORATING 是要避開的明確訊號。歷史上這區間股票 6-12 月期 alpha 多為負值。',
        },
        en: {
          title: 'DETERIORATING · Distressed (composite < 35)',
          desc:  '**4 components total < 35**: broad-based deterioration, ≥2 red flags.\n\n**Meaning**: avoid zone. Treat as toxic unless deep value + activist catalyst.\n\n**Typical scenario**:\n• Multiple quality flags (accruals + capex burn + DSO + negative FCF)\n• Shrinking growth with rich multiples (not yet priced in)\n• Mass analyst downgrades',
          stages: [],
          hint: 'DETERIORATING is a clear avoid signal. Historically this zone shows negative 6-12mo alpha.',
        },
      },
    };

    function classifyStage(stages, daysSince) {
      if (daysSince == null || daysSince === '' || isNaN(daysSince)) return null;
      const n = Number(daysSince);
      // Categorical stage tables (macro) carry `range: null` and are classified
      // by UI.signalTier instead. Skipping them rather than indexing null keeps
      // a mistaken call here from throwing inside a hover handler.
      return stages.find(s => s.range && n >= s.range[0] && n <= s.range[1]) || null;
    }

    const STAGE_DOTS = {
      // FTD
      prime: '🟢', standard: '🟡', late_cycle: '🟠', exhausted: '🔴',
      // Breadth / market top / macro — sourced from UI.SIGNAL_TIERS so a tier
      // edit cannot leave the dots behind (see the Exposure note below).
      ...Object.fromEntries(Object.values(UI.SIGNAL_TIERS)
        .flatMap(spec => spec.tiers.map(t => [t.key, t.dot]))),
      // Regime
      rg_risk_on: '🟢', rg_neutral: '🟡', rg_volatile: '🟠', rg_risk_off: '🔴',
      // Exposure — shared by the synth ceiling too, since V4.111.0 gave both
      // guides the same tier table (UI.EXPOSURE_TIERS). Sourced from there so a
      // future tier edit cannot leave the dots behind.
      ...Object.fromEntries(UI.EXPOSURE_TIERS.map(t => [t.key, t.dot])),
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

    function macroLive(el, t, lang) {
      const label = (el.dataset.macroLabel || '').trim();
      if (!label) return { liveHTML: noActiveHTML(t), stage: null };
      const stage = UI.signalTier('macro', label);
      const comp = el.dataset.macroComposite;
      const real = el.dataset.macroReal;
      const bits = [];
      if (comp !== '' && comp != null) bits.push(`composite ${Number(comp).toFixed(0)}`);
      if (real !== '' && real != null) bits.push(`real ${Number(real).toFixed(2)}%`);
      const liveHTML = `<div class="stt-live">
        <span class="stt-live-dot">${STAGE_DOTS[stage?.key] || '⚪'}</span>
        <span>🏦 ${label}</span>
        <span class="stt-live-stage">${stage ? `${stage[lang === 'en' ? 'en' : 'zh'].tag} — ${stage[lang === 'en' ? 'en' : 'zh'].action}`
          : (lang === 'en' ? 'regime unrecognised' : '體制名稱無法辨識')}</span>
      </div>
      ${bits.length ? `<div class="stt-live-sources">${bits.join(' · ')}</div>` : ''}`;
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
      macro: macroLive,
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
      // V2.20.0 — share _hideTimer via tip element so page-decisions.js
      // data-tip-key handler doesn't kill our just-shown tooltip (and vice versa)
      if (tip._hideTimer) { clearTimeout(tip._hideTimer); tip._hideTimer = null; }
      if (_hideTimer)     { clearTimeout(_hideTimer);     _hideTimer = null; }
      showSignalTip(el);
    });
    document.addEventListener('mouseout', e => {
      const el = e.target.closest('[data-signal-tip]');
      if (!el) return;
      tip._hideTimer = setTimeout(() => { hideSignalTip(); tip._hideTimer = null; }, 120);
      _hideTimer = tip._hideTimer;
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
