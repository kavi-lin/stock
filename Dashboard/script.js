lucide.createIcons();

let currentTheme = localStorage.getItem('dash_theme') || 'dark';

function initTheme() {
  document.documentElement.setAttribute('data-theme', currentTheme);
  if (currentTheme === 'dark') {
    document.documentElement.classList.add('dark');
  } else {
    document.documentElement.classList.remove('dark');
  }
  const icon = document.getElementById('theme-icon');
  if (icon) {
    icon.setAttribute('data-lucide', currentTheme === 'dark' ? 'moon' : 'sun');
    if (window.lucide) lucide.createIcons();
  }
}

function toggleTheme() {
  currentTheme = currentTheme === 'dark' ? 'light' : 'dark';
  localStorage.setItem('dash_theme', currentTheme);
  initTheme();
}

initTheme();

let currentLang = localStorage.getItem('dash_lang') || 'zh';
const debugPanel = document.getElementById('debug-console');

function logToUI(msg, type = 'info') {
  const out = document.getElementById('log-output');
  if (!out) return;
  const line = document.createElement('div');
  const time = new Date().toLocaleTimeString();
  const color = type === 'error' ? 'text-red-500' : (type === 'warn' ? 'text-yellow-500' : 'text-zinc-500');
  line.innerHTML = `<span>[${time}]</span> <span class="${color}">${msg}</span>`;
  out.appendChild(line);
}

function applyTranslations() {
  if (!window.i18n) return;
  const t = window.i18n[currentLang];
  const o = t.overview;

  // Nav
  document.querySelectorAll('[data-i18n^="nav_"]').forEach(el => {
    const key = el.getAttribute('data-i18n').replace('nav_', '');
    if (t.nav[key]) el.textContent = t.nav[key];
  });
  
  document.getElementById('lang-text').textContent = currentLang === 'zh' ? 'English' : '繁體中文';

  // Overview
  const keys = ['market_regime', 'hot_themes', 'sentiment', 'recent_audit', 'catalyst', 'quick_launch', 'launch_desc', 'start_btn'];
  keys.forEach(k => {
    const el = document.querySelector(`[data-i18n="${k}"]`);
    if (el) el.textContent = o[k];
  });
}

function toggleLang() {
  currentLang = currentLang === 'zh' ? 'en' : 'zh';
  localStorage.setItem('dash_lang', currentLang);
  applyTranslations();
  updateDashboard();
}

function updateMarketStatus() {
  const statusEl = document.getElementById('market-status-text');
  if (!statusEl) return;
  const nyTime = new Date().toLocaleString("en-US", {timeZone: "America/New_York"});
  const date = new Date(nyTime);
  const hours = date.getHours();
  const minutes = date.getMinutes();
  const day = date.getDay();
  const isWeekday = day >= 1 && day <= 5;
  const timeInMinutes = (hours * 60) + minutes;
  const isOpen = isWeekday && (timeInMinutes >= 570 && timeInMinutes < 960);
  
  if (isOpen) {
    statusEl.textContent = currentLang === 'zh' ? '開盤中' : 'OPEN';
    statusEl.className = 'text-sm font-semibold text-green-400';
  } else {
    statusEl.textContent = currentLang === 'zh' ? '已收盤' : 'CLOSED';
    statusEl.className = 'text-sm font-semibold text-red-500';
  }
}

async function viewReport(path) {
  const modal = document.getElementById('report-modal');
  const content = document.getElementById('report-content');
  if (!path || path === 'null') {
      alert("Report pending generated...");
      return;
  }
  modal.classList.remove('hidden');
  content.innerHTML = '<div class="flex items-center justify-center h-full p-20 animate-pulse text-zinc-500">Loading audit report...</div>';
  try {
    const fullPath = '../' + path + '?t=' + Date.now();
    if (path.endsWith('.html')) {
      content.innerHTML = `<iframe src="${fullPath}" class="w-full h-full border-0 bg-white rounded-lg"></iframe>`;
    } else {
      const res = await fetch(fullPath);
      const md = await res.text();
      content.innerHTML = `<div class="p-8 prose prose-invert prose-zinc max-w-none text-zinc-300">${marked.parse(md)}</div>`;
    }
  } catch (e) {
    content.innerHTML = `<div class="p-10 text-center text-red-500">Failed to load: ${e.message}</div>`;
  }
}

function renderAuditCard(item) {
    const isBuy = item.decision === 'BUY' || item.decision === 'EXECUTE';
    const statusColor = isBuy ? 'var(--status-bullish)' : (item.decision === 'CANCEL' ? 'var(--status-bearish)' : 'var(--text-muted)');
    const perfColor = item.performance?.change >= 0 ? 'var(--status-bullish)' : 'var(--status-bearish)';
    const perfIcon = item.performance?.change >= 0 ? 'trending-up' : 'trending-down';

    const card = document.createElement('div');
    card.className = "glass-card p-6 flex flex-col justify-between group hover:border-zinc-500/50 transition-all cursor-default";
    
    const perfUI = item.performance 
      ? `<div class="mt-4 pt-4 border-t border-zinc-900 flex justify-between items-center">
           <div class="text-[10px] text-zinc-500 font-bold uppercase tracking-wider">Backtest P/L</div>
           <div class="flex items-center gap-1 ${perfColor} font-mono font-bold text-sm">
             <i data-lucide="${perfIcon}" class="w-3 h-3"></i>
             ${item.performance.change > 0 ? '+' : ''}${item.performance.change}%
           </div>
         </div>`
      : '';

    const t = window.i18n[currentLang];
    const s = t.sentiment_labels;
    const translatedDecision = t.status[item.decision] || item.decision;

    const targetUI = item.targets?.tp 
      ? `<div class="mt-4 flex gap-4 border-t border-zinc-200 dark:border-zinc-900/50 pt-3">
           <div class="flex-1">
             <p class="text-[8px] text-zinc-600 font-bold uppercase">${s.tp}</p>
             <p class="text-xs font-mono font-bold" style="color: var(--status-bullish)">$${item.targets.tp}</p>
           </div>
           <div class="flex-1 border-l border-zinc-200 dark:border-zinc-900/50 pl-4">
             <p class="text-[8px] text-zinc-600 font-bold uppercase">${s.sl}</p>
             <p class="text-xs font-mono font-bold" style="color: var(--status-bearish)">$${item.targets.sl}</p>
           </div>
         </div>`
      : (item.targets?.watch || item.targets?.entry ? `<div class="mt-4 border-t border-zinc-200 dark:border-zinc-900/50 pt-3">
            <p class="text-[8px] text-zinc-600 font-bold uppercase">${item.targets.watch ? s.watch : s.entry}</p>
            <p class="text-xs font-mono font-bold" style="color: var(--status-binary)">${item.targets.watch || item.targets.entry}</p>
        </div>` : '');

    // A5-RISKS: key_risks tags
    const risksUI = (item.key_risks && item.key_risks.length)
      ? `<div class="mt-3 pt-3 border-t border-zinc-200 dark:border-zinc-900/50">
           <div class="flex flex-wrap gap-1.5">${item.key_risks.map(r =>
             `<span class="text-[9px] font-bold px-2 py-0.5 rounded bg-red-500/10 text-red-400 border border-red-500/20">${r.replace(/_/g,' ')}</span>`
           ).join('')}</div>
         </div>`
      : '';

    // A5-COND: watch_conditions for CANCEL cards
    const condUI = (item.decision === 'CANCEL' && item.watch_conditions)
      ? `<div class="mt-3 pt-3 border-t border-zinc-200 dark:border-zinc-900/50 space-y-1.5">
           <p class="text-[9px] font-black text-yellow-500 uppercase tracking-widest flex items-center gap-1">
             <i data-lucide="crosshair" class="w-3 h-3"></i> ${t.watchlist?.entry_triggers || '進場觸發條件'}
           </p>
           ${Object.entries(item.watch_conditions).map(([k,v]) =>
             `<div class="flex gap-2 items-start"><span class="text-[9px] font-black uppercase tracking-widest mt-0.5 shrink-0 w-14" style="color:var(--status-binary)">${k.toUpperCase()}</span><span class="text-[10px] leading-relaxed" style="color:var(--text-main)">${v}</span></div>`
           ).join('')}
         </div>`
      : '';

    card.innerHTML = `
      <div class="flex justify-between items-start mb-4">
        <div>
          <h4 class="text-2xl font-black tracking-tighter" style="color: var(--text-card-title)">${item.ticker}</h4>
          <p class="text-[10px] text-zinc-500 font-mono">${item.time}</p>
        </div>
        <span class="px-2 py-1 rounded text-[10px] font-black border transition-all" style="background-color: color-mix(in srgb, ${statusColor}, transparent 90%); border-color: color-mix(in srgb, ${statusColor}, transparent 80%); color: ${statusColor}">${translatedDecision}</span>
      </div>
      <div class="flex items-end justify-between mt-2">
        <div class="relative group/score inline-block">
          <p class="text-[9px] text-zinc-500 font-bold uppercase tracking-widest border-b-2 border-dotted border-zinc-700 cursor-help pb-0.5 mb-1 hover:border-emerald-500/50 transition-colors" title="Click or hover for scoring logic">
            Model Score
          </p>
          <p class="text-3xl font-bold tracking-tighter" style="color: var(--text-card-title)">${item.score}</p>

          <!-- Tooltip Popup -->
          <div class="absolute bottom-full left-0 mb-4 w-72 p-5 border border-zinc-200 dark:border-zinc-800 rounded-2xl shadow-xl opacity-0 group-hover/score:opacity-100 transition-all duration-300 pointer-events-none z-[999] backdrop-blur-2xl translate-y-4 group-hover/score:translate-y-0" style="background-color: var(--bg-card); color: var(--text-main)">
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
        <button onclick="viewReport('${item.report_url}')" class="w-12 h-12 rounded-xl bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 flex items-center justify-center hover:bg-emerald-500 hover:text-black hover:border-emerald-500 transition-all shadow-md dark:shadow-xl active:scale-95 group/btn" title="View Full Report">
          <i data-lucide="file-text" class="w-5 h-5 text-zinc-700 dark:text-zinc-100 group-hover/btn:scale-110 transition-transform"></i>
        </button>
      </div>
      ${targetUI}
      ${risksUI}
      ${condUI}
      ${perfUI}
    `;
    return card;
}

async function updateDashboard() {
  logToUI("Refreshing system synchronization...");
  updateMarketStatus();
  
  try {
    const response = await fetch('data.json?t=' + Date.now());
    const data = await response.json();
    
    // 0. Warning Flags Banner
    const banner = document.getElementById('warning-banner');
    if (banner && data.market?.warning_flags?.length) {
        banner.classList.remove('hidden');
        banner.classList.add('flex');
        const tw = window.i18n?.[currentLang]?.warnings || {};
        const flagTranslations = tw.flags || {};
        const flagList = document.getElementById('warning-flags-list');
        flagList.innerHTML = data.market.warning_flags.map(f => {
            const label = flagTranslations[f] || f.replace(/_/g, ' ');
            const isCritical = f.includes('Death_Cross') || f.includes('Extreme_Fear');
            return `<span class="text-[9px] font-bold px-2 py-0.5 rounded border ${
                isCritical ? 'bg-red-500/15 text-red-400 border-red-500/30'
                           : 'bg-yellow-500/10 text-yellow-500 border-yellow-500/20'}">${label}</span>`;
        }).join('');
        // Banner title + uptrend label
        const bannerTitle = document.getElementById('warning-banner-title');
        if (bannerTitle) bannerTitle.textContent = tw.banner_title || 'Risk Flags Active';
        const uptrendLabel = document.getElementById('uptrend-label');
        if (uptrendLabel) uptrendLabel.textContent = tw.uptrend_label || 'Uptrend Ratio';
        const uptrendEl = document.getElementById('uptrend-ratio-val');
        if (uptrendEl && data.market.uptrend_ratio != null) {
            const pct = Math.round(data.market.uptrend_ratio * 100);
            uptrendEl.textContent = pct + '%';
            uptrendEl.style.color = pct < 40 ? 'var(--status-bearish)' : pct > 60 ? 'var(--status-bullish)' : '#eab308';
        }
    }

    // 1. Market Data (Dashboard only)
    if (document.getElementById('regime-text')) {
        document.getElementById('regime-text').textContent = data.market.regime;
        document.getElementById('regime-desc').textContent = data.market.notes || "Live Analysis Active";
        document.getElementById('fear-greed-val').textContent = data.market.fear_greed;
        const fgVal = data.market.fear_greed;
        const fgDesc = fgVal < 25 ? "EXTREME FEAR" : (fgVal < 45 ? "FEAR" : (fgVal < 55 ? "NEUTRAL" : (fgVal < 75 ? "GREED" : "EXTREME GREED")));
        document.getElementById('sentiment-desc').textContent = fgDesc;

        // A2-BREADTH: Uptrend Ratio mini gauge
        const gaugeWrap = document.getElementById('uptrend-gauge-wrap');
        if (gaugeWrap && data.market.uptrend_ratio != null) {
            gaugeWrap.classList.remove('hidden');
            const pct = Math.round(data.market.uptrend_ratio * 100);
            const barColor = pct < 35 ? '#ef4444' : pct < 50 ? '#eab308' : '#22c55e';
            const gaugeLabel = document.getElementById('uptrend-gauge-label');
            if (gaugeLabel) gaugeLabel.textContent = window.i18n?.[currentLang]?.overview?.uptrend_ratio || 'Uptrend Ratio';
            document.getElementById('uptrend-gauge-val').textContent = pct + '%';
            document.getElementById('uptrend-gauge-val').style.color = barColor;
            const bar = document.getElementById('uptrend-gauge-bar');
            if (bar) { bar.style.width = pct + '%'; bar.style.backgroundColor = barColor; }
        }
        
        const themesContainer = document.getElementById('themes-container');
        themesContainer.innerHTML = '';
        data.market.themes.slice(0, 3).forEach(theme => {
          const div = document.createElement('div');
          div.className = "flex justify-between items-center text-sm";
          div.innerHTML = `<span style="color: var(--text-main)"># ${theme.replace(/_/g, ' ')}</span><span class="text-green-500 font-mono text-[10px]">ACTIVE</span>`;
          themesContainer.appendChild(div);
        });
    }

    // 2. Audit Displays
    const condensedGrid = document.getElementById('audit-grid-condensed');
    const fullGrid = document.getElementById('audit-grid-full');
    
    if (condensedGrid) {
        condensedGrid.innerHTML = '';
        data.recent_analysis?.slice(0, 3).forEach(item => condensedGrid.appendChild(renderAuditCard(item)));
    }
    if (fullGrid) {
        fullGrid.innerHTML = '';
        data.recent_analysis?.forEach(item => fullGrid.appendChild(renderAuditCard(item)));
    }

    // 3. Catalysts News
    const newsContainer = document.getElementById('news-list');
    if (newsContainer && data.news) {
        newsContainer.innerHTML = '';
        data.news.slice(0, 5).forEach(news => {
            const div = document.createElement('div');
            div.className = 'flex items-start gap-4 p-3 rounded-lg hover:bg-zinc-100 dark:hover:bg-zinc-900/50 transition-all cursor-pointer';
            
            // Refined Impact Logic
            const impact = news.impact ? news.impact.toUpperCase() : '';
            const impactVal = parseInt(news.impact) || 0;
            const isPos = impactVal >= 3 || impact === 'BULLISH';
            const isNeg = (impactVal < 0 && impactVal > -10) || impact === 'BEARISH';
            const isBinary = impact === 'BINARY' || impact === 'VOLATILE';
            const icon = isPos ? 'trending-up' : (isNeg ? 'trending-down' : (isBinary ? 'alert-triangle' : 'zap'));
            const statusColor = isPos ? 'var(--status-bullish)' : (isNeg ? 'var(--status-bearish)' : (isBinary ? 'var(--status-binary)' : 'var(--status-binary)'));
            
            div.innerHTML = `
                <div class="mt-1">
                    <div class="w-8 h-8 rounded-lg bg-zinc-100 dark:bg-zinc-900 flex items-center justify-center border border-zinc-200 dark:border-zinc-800">
                        <i data-lucide="${icon}" style="color: ${statusColor}" class="w-4 h-4"></i>
                    </div>
                </div>
                <div class="flex-1 min-w-0">
                    <p class="text-sm font-medium truncate" style="color: var(--text-card-title)">${news.headline}</p>
                    <div class="flex items-center gap-2 mt-1">
                        <span class="text-[9px] font-bold text-zinc-500 uppercase">${news.sector || 'GENERAL'}</span>
                        <div class="w-1 h-1 rounded-full bg-zinc-700"></div>
                        <span class="text-[9px] font-bold uppercase" style="color: ${statusColor}">Impact: ${news.impact}</span>
                    </div>
                </div>
            `;
            newsContainer.appendChild(div);
        });
    }

  } catch (error) {
    logToUI(error.message, "error");
    console.error("Dashboard update failed:", error);
  } finally {
    // CRITICAL: Refresh icons for ALL dynamically added content
    if (window.lucide) {
      lucide.createIcons();
    }
    const syncEl = document.getElementById('last-update');
    if (syncEl && data?.last_updated) syncEl.textContent = `SYNC: ${data.last_updated}`;
    logToUI("System update cycle complete.");
  }
}

// Launch Engine
function launchAnalysis() {
  const input = document.getElementById('ticker-input');
  const hint = document.getElementById('launch-hint');
  const cmdEl = document.getElementById('launch-cmd');
  if (!input) return;
  const ticker = input.value.trim().toUpperCase();
  if (!ticker) return;
  const cmd = `分析 ${ticker}`;
  cmdEl.textContent = cmd;
  hint.classList.remove('hidden');
  logToUI(`Launch command generated: "${cmd}"`, 'info');
}

// Handlers
document.getElementById('theme-toggle')?.addEventListener('click', toggleTheme);
document.getElementById('lang-toggle')?.addEventListener('click', toggleLang);
document.getElementById('show-logs')?.addEventListener('click', () => debugPanel.classList.toggle('hidden'));
document.getElementById('close-modal')?.addEventListener('click', () => document.getElementById('report-modal').classList.add('hidden'));
document.getElementById('launch-btn')?.addEventListener('click', launchAnalysis);
document.getElementById('ticker-input')?.addEventListener('keydown', (e) => { if (e.key === 'Enter') launchAnalysis(); });
document.getElementById('copy-cmd')?.addEventListener('click', () => {
  const cmd = document.getElementById('launch-cmd')?.textContent;
  if (cmd) navigator.clipboard.writeText(cmd).then(() => {
    const btn = document.getElementById('copy-cmd');
    btn.innerHTML = '<i data-lucide="check" class="w-3 h-3"></i> COPIED';
    btn.classList.add('text-green-400', 'border-green-500');
    if (window.lucide) lucide.createIcons();
    setTimeout(() => { btn.innerHTML = '<i data-lucide="copy" class="w-3 h-3"></i> COPY'; btn.classList.remove('text-green-400', 'border-green-500'); if (window.lucide) lucide.createIcons(); }, 2000);
  });
});

// Boot
applyTranslations();
updateDashboard();
setInterval(updateDashboard, 60000);
