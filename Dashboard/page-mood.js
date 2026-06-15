/* ════════════════════════════════════════════════════════════════════
   page-mood.js — 市場氛圍 / Market Mood (decision-funnel redesign)

   Funnel, top → bottom:
     1. Verdict band   — deterministic 偏多/偏空/觀望 + break-news market brief
     2. 3-day trend    — TrendChart (break-news sentiment rollup) + brief
                         regime timeline + daily anchors
     3. Live tape      — client-side aggregate of heatmap.json (market hours)
     4. Social radar   — Reddit/HN/Bluesky ticker chips + buzz + post feed
     4b. Trump radar   — Truth Social posts, policy/U-turn lexicon + debate
                         verdict attach (TACO watch)
     5. Debate signals — closed break-news debates + hot clusters
     6. Sector ranking — retail_sector_pulse one-row-per-sector list
     7. Gauges strip   — Put/Call · VIX/SKEW · F&G (demoted, daily)

   All sources are pre-paid artifacts (brief/debates/trends) or $0 feeds
   (heatmap/trending_tickers) — this page issues 0 LLM calls and only GETs.
   Exploration layer: never feeds investment_protocol.
   ════════════════════════════════════════════════════════════════════ */
const $ = id => document.getElementById(id);
const _t = () => (window.i18n?.[UI.currentLang]?.mood) || {};
const _zh = () => UI.currentLang !== 'en';

const C_BULL = '#22c55e';
const C_BEAR = '#ef4444';
const C_NEU  = '#a8a29e';

const esc = s => String(s == null ? '' : s).replace(/[&<>"]/g, c =>
    ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));

function fmtTime(iso) {
    if (!iso) return '';
    const d = new Date(iso);
    if (isNaN(d)) return '';
    return `${String(d.getMonth() + 1)}/${d.getDate()} ${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`;
}
function signed(v, digits = 2) {
    if (v == null || isNaN(v)) return '—';
    return `${v > 0 ? '+' : ''}${v.toFixed(digits)}`;
}
function polColor(v, lo = -0.05, hi = 0.05) {
    if (v == null) return C_NEU;
    return v > hi ? C_BULL : v < lo ? C_BEAR : C_NEU;
}

// ── Verdict weights (user-approved defaults; tune here) ─────────────────────
const VERDICT_WEIGHTS_OPEN   = { tape: 0.35, news: 0.25, brief: 0.20, mood: 0.20 };
const VERDICT_WEIGHTS_CLOSED = { news: 0.35, brief: 0.30, mood: 0.35 };
const VERDICT_NEUTRAL_BAND   = 0.15;
const DIVERGENCE_GAP         = 0.5;

// ── Trump policy lexicon (deterministic, 0 LLM) ─────────────────────────────
const POLICY_TERMS = [
    'tariff', 'trade', 'china', 'chip', 'semiconductor', 'fed', 'powell',
    'rate', 'tax', 'export', 'import', 'sanction', 'oil', 'energy', 'dollar',
    'deal', 'nvidia', 'tiktok', 'subsidy', 'inflation', 'jobs', 'manufacturing',
];
const FLIP_TERMS = [
    'pause', 'delay', 'postpone', 'exempt', 'suspend', 'extend', 'extension',
    'off the table', 'no longer', 'reconsider', 'roll back', 'rollback',
    'walk back', 'cancel', 'lower the', 'reduce the', 'deal reached',
    'agreement', 'agreed', 'truce',
];

const RSP_LABEL_TEXT = {
    strong_bull: { zh: '強多', en: 'Strong Bull' }, mod_bull: { zh: '偏多', en: 'Mod Bull' },
    neutral_mixed: { zh: '分歧', en: 'Mixed' }, mod_bear: { zh: '偏空', en: 'Mod Bear' },
    strong_bear: { zh: '強空', en: 'Strong Bear' }, neutral: { zh: '中性', en: 'Neutral' },
    insufficient_data: { zh: '資料不足', en: 'No Data' },
    spike: { zh: '爆量', en: 'spike' }, elevated: { zh: '升溫', en: 'elevated' },
    normal: { zh: '正常', en: 'normal' }, calm: { zh: '冷清', en: 'calm' },
    strong_bull_dir: { zh: '強多', en: 'Strong Bull' },
};
const RSP_TEXT_BY_DIR = {
    strong_bull: '#15803d', mod_bull: '#15803d', neutral_mixed: '#78716c',
    mod_bear: '#c2410c', strong_bear: '#b91c1c',
};
function _rspLabelText(label) {
    return RSP_LABEL_TEXT[label]?.[_zh() ? 'zh' : 'en'] || label || '—';
}

const VERDICT_BADGE = {
    BULLISH: { color: C_BULL, zh: '看多', en: 'BULL' },
    BEARISH: { color: C_BEAR, zh: '看空', en: 'BEAR' },
    NEUTRAL: { color: C_NEU,  zh: '中性', en: 'NEUT' },
    SPLIT:   { color: '#f59e0b', zh: '分歧', en: 'SPLIT' },
};
function verdictBadge(v) {
    const b = VERDICT_BADGE[v] || VERDICT_BADGE.NEUTRAL;
    return `<span class="mood-verdict-badge" style="background:${b.color}22;color:${b.color};border:1px solid ${b.color}55;">${_zh() ? b.zh : b.en}</span>`;
}

// ── Page state ───────────────────────────────────────────────────────────────
const S = {
    data: null,        // data.json (DataStore)
    brief: null,       // /api/break-news/brief?history=1
    trends: null,      // /api/break-news/trends
    feed: null,        // /api/break-news/feed (closed + partial_closed)
    clusters: null,    // /api/break-news/clusters
    rawStream: null,   // /api/break-news/raw-stream (Trump posts)
    trendingFull: null,// trending_tickers.json (full posts w/ source+engagement)
    heatmap: null,     // /api/heatmap/data
};
let _trendInst = null;
let _heatmapTimer = null;

async function fetchJson(url) {
    const r = await fetch(url);
    if (!r.ok) throw new Error(`${r.status} ${r.statusText}`);
    return r.json();
}

// ═════════════════════════ 1. VERDICT BAND ══════════════════════════════════

// Heatmap aggregate: cap-weighted % + adv/dec + per-sector cap-weighted %.
function computeTape(hm) {
    const tickers = hm?.tickers || [];
    if (!tickers.length) return null;
    let wSum = 0, wPct = 0, adv = 0, dec = 0, flat = 0;
    const sec = {};
    for (const t of tickers) {
        const pct = t.change_pct, cap = t.market_cap || 0;
        if (pct == null) continue;
        if (pct > 0.05) adv++; else if (pct < -0.05) dec++; else flat++;
        if (cap > 0) { wSum += cap; wPct += cap * pct; }
        const s = t.sector || 'Other';
        (sec[s] = sec[s] || { cap: 0, capPct: 0, n: 0 }).cap += cap;
        sec[s].capPct += cap * pct;
        sec[s].n++;
    }
    if (!wSum) return null;
    const sectors = Object.entries(sec)
        .filter(([, v]) => v.cap > 0 && v.n >= 3)
        .map(([name, v]) => ({ name, pct: v.capPct / v.cap }))
        .sort((a, b) => b.pct - a.pct);
    return {
        capWeightedPct: wPct / wSum, adv, dec, flat,
        sectors, marketOpen: !!hm.market_open, lastUpdate: hm.last_update,
        tickers,
    };
}

function computeVerdict() {
    const t = _t();
    const tape = computeTape(S.heatmap);
    const open = !!tape?.marketOpen;

    const comps = {};
    // tape (market hours only)
    if (open && tape) comps.tape = Math.max(-1, Math.min(1, tape.capWeightedPct / 1.5));
    // news sentiment = last bucket of the break-news whole-market index
    const allSeries = S.trends?.series?.__ALL__;
    if (allSeries && allSeries.length) comps.news = allSeries[allSeries.length - 1];
    // debate tilt from the market brief verdict tally
    const tally = S.brief?.current?.stats?.verdict_tally;
    if (tally) {
        const n = Math.max(1, S.brief.current.stats.closed_debate_count || 0);
        comps.brief = Math.max(-1, Math.min(1, ((tally.BULLISH || 0) - (tally.BEARISH || 0)) / n));
    }
    // daily options/vol mood gauge
    const moodScore = S.data?.market_mood?.mood?.score;
    if (moodScore != null) comps.mood = Math.max(-1, Math.min(1, moodScore / 100));

    const weights = open ? VERDICT_WEIGHTS_OPEN : VERDICT_WEIGHTS_CLOSED;
    let wSum = 0, acc = 0;
    const used = [];
    for (const [k, w] of Object.entries(weights)) {
        if (comps[k] == null) continue;
        wSum += w; acc += w * comps[k];
        used.push(k);
    }
    if (!wSum) return { verdict: null, comps, used, open, tape };
    const score = acc / wSum;   // missing lanes renormalize
    const verdict = score >= VERDICT_NEUTRAL_BAND ? 'bull'
        : score <= -VERDICT_NEUTRAL_BAND ? 'bear' : 'wait';
    const diverged = comps.tape != null && comps.news != null
        && comps.tape * comps.news < 0 && Math.abs(comps.tape - comps.news) > DIVERGENCE_GAP;
    return { verdict, score, comps, used, weights, open, tape, diverged, t };
}

function briefCol(title, items, color) {
    if (!items || !items.length) return '';
    const lis = items.map(x => `<li>${esc(x)}</li>`).join('');
    return `<div class="mood-brief-col" style="border-left-color:${color};">
      <div class="mood-brief-col-title" style="color:${color};">${title}</div>
      <ul>${lis}</ul>
    </div>`;
}

function renderVerdict() {
    const t = _t();
    const sec = $('mood-verdict');
    const v = computeVerdict();
    const cur = S.brief?.current;
    if (!v.verdict && !cur) { sec.classList.add('hidden'); return false; }
    sec.classList.remove('hidden');

    $('mood-verdict-q').textContent = t.verdict_title || '今天該不該進場？';
    const labelEl = $('mood-verdict-label');
    if (v.verdict) {
        const map = { bull: [t.verdict_bull || '偏多', C_BULL], bear: [t.verdict_bear || '偏空', C_BEAR], wait: [t.verdict_wait || '觀望', '#f59e0b'] };
        const [txt, color] = map[v.verdict];
        labelEl.textContent = txt;
        labelEl.style.color = color;
        $('mood-verdict-score').textContent =
            `${signed(v.score)} · ${v.used.length}/${Object.keys(v.weights).length} signals · ${v.open ? 'LIVE' : 'EOD'}`;
    } else {
        labelEl.textContent = t.verdict_nodata || '訊號不足';
        labelEl.style.color = C_NEU;
        $('mood-verdict-score').textContent = '';
    }

    // transparent component chips: value + weight
    const compNames = { tape: t.comp_tape || '盤面', news: t.comp_news || '新聞情緒', brief: t.comp_brief || '辯論傾向', mood: t.comp_mood || '情緒指標' };
    const chips = [];
    for (const [k, w] of Object.entries(v.weights || {})) {
        const val = v.comps[k];
        const c = polColor(val);
        chips.push(`<span class="mood-chip" style="${val == null ? 'opacity:.45;' : ''}">
            ${esc(compNames[k] || k)}
            <strong style="color:${c};">${val == null ? '—' : signed(val)}</strong>
            <span style="color:var(--text-muted);">×${w.toFixed(2)}</span></span>`);
    }
    const ms = S.data?.market_mood?.mood;
    if (ms?.score != null) {
        chips.push(`<span class="mood-chip">${esc(t.mood_chip || '情緒分數')}
            <strong style="color:${ms.score >= 20 ? C_BULL : ms.score <= -20 ? C_BEAR : C_NEU};">${ms.score}</strong>
            <span style="color:var(--text-muted);">${esc((_zh() ? ms.label_zh : ms.label) || '')}</span></span>`);
    }
    $('mood-verdict-chips').innerHTML = chips.join('');

    const div = $('mood-divergence');
    div.classList.toggle('hidden', !v.diverged);
    if (v.diverged) div.textContent = t.divergence_warn || '⚠ 盤面與消息面分歧';

    // brief (already-paid LLM artifact — display only)
    const regime = $('mood-brief-regime'), meta = $('mood-brief-meta'), body = $('mood-brief-body');
    if (cur) {
        if (cur.regime) {
            regime.style.display = '';
            regime.textContent = cur.regime;
            regime.style.color = polColor(v.comps.brief, -0.02, 0.02);
        } else regime.style.display = 'none';
        const stats = cur.stats || {};
        meta.textContent = `${stats.closed_debate_count ?? '?'} ${_zh() ? '場辯論' : 'debates'} · ${fmtTime(cur.generated_at)}`;
        body.innerHTML = `
            <div class="mood-brief-text">${esc(cur.brief_text || '')}</div>
            <div class="mood-brief-cols">
              ${briefCol(_zh() ? '🔥 主導事件' : '🔥 Drivers', cur.drivers, '#60a5fa')}
              ${briefCol(_zh() ? '✅ 多方力量' : '✅ Bull Pressure', cur.bull_pressure, C_BULL)}
              ${briefCol(_zh() ? '❌ 空方力量' : '❌ Bear Pressure', cur.bear_pressure, C_BEAR)}
              ${briefCol(_zh() ? '👁 觀察點' : '👁 Watch', cur.watch, '#eab308')}
            </div>`;
    } else {
        regime.style.display = 'none';
        meta.textContent = '';
        body.innerHTML = `<div class="mood-empty">${esc(t.brief_empty || '尚無市場導讀')}</div>`;
    }
    return true;
}

// ═════════════════════════ 2. TREND + ANCHORS ═══════════════════════════════

function renderTrendExtras() {
    const t = _t();
    $('mood-trend-wrap').classList.remove('hidden');
    $('mood-trend-title').querySelector('span').textContent = t.trend_section || '近 3 天市場走向';

    // regime timeline from brief history (newest last)
    const tl = $('mood-regime-timeline');
    const hist = [...(S.brief?.history || [])];
    const cur = S.brief?.current;
    if (cur) hist.push(cur);
    if (hist.length) {
        hist.sort((a, b) => String(a.generated_at || '').localeCompare(String(b.generated_at || '')));
        const pills = hist.slice(-8).map((h, i, arr) => {
            const tally = h.stats?.verdict_tally || {};
            const tilt = (tally.BULLISH || 0) - (tally.BEARISH || 0);
            const c = tilt > 0 ? C_BULL : tilt < 0 ? C_BEAR : C_NEU;
            const isLast = i === arr.length - 1;
            return `<span class="mood-chip" style="${isLast ? `border-color:${c};` : 'opacity:.75;'}" title="${esc(h.brief_text || '')}">
                <span style="color:var(--text-muted);">${fmtTime(h.generated_at)}</span>
                <strong style="color:${c};">${esc(h.regime || '—')}</strong></span>`;
        });
        tl.innerHTML = `<span class="text-[10px] uppercase tracking-wider mr-1" style="color:var(--text-muted);">${esc(t.regime_timeline || '導讀時間軸')}</span>` + pills.join('');
        tl.style.display = '';
    } else tl.style.display = 'none';

    // daily anchors
    const d = S.data || {};
    const anchors = [];
    const add = (label, val, color) => anchors.push(
        `<span class="mood-chip">${esc(label)} <strong style="color:${color || 'var(--text-main)'};">${esc(val)}</strong></span>`);
    const br = d.breadth || {};
    if (br.score != null) add('Breadth', `${br.score} ${br.zone || ''}`,
        br.zone_color === 'green' ? C_BULL : br.zone_color === 'red' ? C_BEAR : '#f59e0b');
    const ftd = d.ftd || {};
    if (ftd.state) add('FTD', ftd.state, ftd.state.includes('CONFIRMED') ? C_BULL : C_NEU);
    const mt = d.market_top || {};
    if (mt.zone) add('Top Risk', mt.zone, /red|orange/i.test(mt.zone) ? C_BEAR : C_NEU);
    const fo = (d.market || {}).fred_overlay || {};
    if (fo.regime_label) add('FRED', fo.regime_label, C_NEU);
    const spy = d.market_mood?.spy_momentum || {};
    if (spy.rsi_14 != null) add('SPY', `RSI ${spy.rsi_14} · MA50 ${signed(spy.pct_above_ma50, 1)}%`,
        polColor(spy.pct_above_ma50, -0.5, 0.5));
    $('mood-anchors').innerHTML = anchors.length
        ? `<span class="text-[10px] uppercase tracking-wider mr-1" style="color:var(--text-muted);">${esc(t.anchors_label || '每日錨點')}</span>` + anchors.join('')
        : '';
}

// ═════════════════════════ 3. INTRADAY TAPE ═════════════════════════════════

function renderIntraday() {
    const t = _t();
    const sec = $('mood-intraday');
    const tape = computeTape(S.heatmap);
    if (!tape) { sec.classList.add('hidden'); return; }
    sec.classList.remove('hidden');

    const open = tape.marketOpen;
    $('mood-intraday-title').querySelector('span').textContent =
        open ? (t.intraday_section || '盤中即時') : (t.intraday_closed || '上一交易日收盤');
    const badge = $('mood-market-badge');
    badge.textContent = open ? 'OPEN' : 'CLOSED';
    badge.style.cssText = open
        ? `background:${C_BULL}22;color:${C_BULL};border:1px solid ${C_BULL}55;`
        : `background:var(--border);color:var(--text-muted);`;
    $('mood-intraday-asof').textContent = tape.lastUpdate ? fmtTime(tape.lastUpdate) : '';

    const pctC = polColor(tape.capWeightedPct, -0.05, 0.05);
    const advC = tape.adv >= tape.dec ? C_BULL : C_BEAR;
    const line = `
        <span class="mood-chip">${esc(t.cap_weighted || '市值加權')}
            <strong style="color:${pctC};font-size:13px;">${signed(tape.capWeightedPct)}%</strong></span>
        <span class="mood-chip">${esc(t.adv_dec || '漲跌家數')}
            <strong style="color:${advC};">${tape.adv}</strong> / <strong style="color:${C_BEAR};">${tape.dec}</strong></span>`;

    if (!open) {
        // collapsed one-liner when closed (auto-expands during market hours)
        const best = tape.sectors[0], worst = tape.sectors[tape.sectors.length - 1];
        $('mood-intraday-body').innerHTML = `<div class="flex flex-wrap items-center gap-1.5">${line}
            ${best ? `<span class="mood-chip">${esc(t.strongest || '最強')} <strong style="color:${C_BULL};">${esc(best.name)} ${signed(best.pct, 1)}%</strong></span>` : ''}
            ${worst ? `<span class="mood-chip">${esc(t.weakest || '最弱')} <strong style="color:${C_BEAR};">${esc(worst.name)} ${signed(worst.pct, 1)}%</strong></span>` : ''}
        </div>`;
        return;
    }

    const secChip = s => `<span class="mood-chip">${esc(s.name)}
        <strong style="color:${polColor(s.pct, -0.05, 0.05)};">${signed(s.pct, 1)}%</strong></span>`;
    const top3 = tape.sectors.slice(0, 3).map(secChip).join('');
    const bot3 = tape.sectors.slice(-3).reverse().map(secChip).join('');
    // $-volume leaders give the "where is the action" read
    const volLeaders = [...tape.tickers]
        .filter(x => x.volume && x.price)
        .sort((a, b) => (b.volume * b.price) - (a.volume * a.price))
        .slice(0, 5)
        .map(x => `<span class="mood-chip">${esc(x.ticker)}
            <strong style="color:${polColor(x.change_pct, -0.05, 0.05)};">${signed(x.change_pct, 1)}%</strong></span>`)
        .join('');
    $('mood-intraday-body').innerHTML = `
        <div class="flex flex-wrap items-center gap-1.5">${line}</div>
        <div class="flex flex-wrap items-center gap-1.5 mt-2">
            <span class="text-[10px] uppercase tracking-wider" style="color:var(--text-muted);">${esc(t.strongest || '最強')}</span>${top3}
            <span class="text-[10px] uppercase tracking-wider ml-2" style="color:var(--text-muted);">${esc(t.weakest || '最弱')}</span>${bot3}
        </div>
        <div class="flex flex-wrap items-center gap-1.5 mt-2">
            <span class="text-[10px] uppercase tracking-wider" style="color:var(--text-muted);">${esc(t.vol_leaders || '成交熱門')}</span>${volLeaders}
        </div>`;
}

// ═════════════════════════ 4. SOCIAL RADAR ══════════════════════════════════

function _sourceBadge(src) {
    const s = String(src || '');
    if (s.startsWith('Reddit')) return ['Reddit', '#f97316'];
    if (s.startsWith('Hacker')) return ['HN', '#f59e0b'];
    if (s.startsWith('Bluesky')) return ['Bluesky', '#3b82f6'];
    if (s.startsWith('Truth Social')) return ['Truth', '#a855f7'];
    return [s.slice(0, 8) || '—', '#71717a'];
}

function renderSocial() {
    const t = _t();
    const sec = $('mood-social');
    const tr = S.data?.tactical?.trending;
    const full = S.trendingFull;
    const tickers = (full?.tickers?.length ? full.tickers : tr?.tickers) || [];
    if (!tickers.length) { sec.classList.add('hidden'); return; }
    sec.classList.remove('hidden');
    $('mood-social-title').querySelector('span').textContent = t.social_section || '社群雷達';

    // aggregate tilt
    const pols = tickers.map(x => x.polarity_score).filter(p => p != null);
    const avg = pols.length ? pols.reduce((a, b) => a + b, 0) / pols.length : 0;
    const tiltEl = $('mood-retail-tilt');
    if (avg > 0.1) { tiltEl.textContent = _zh() ? '🚀 偏多' : '🚀 Bullish'; tiltEl.style.color = C_BULL; }
    else if (avg < -0.1) { tiltEl.textContent = _zh() ? '💥 偏空' : '💥 Bearish'; tiltEl.style.color = C_BEAR; }
    else { tiltEl.textContent = _zh() ? '⚖️ 分歧' : '⚖️ Mixed'; tiltEl.style.color = C_NEU; }

    // hot ticker chips
    const maxEng = Math.max(...tickers.map(x => x.engagement_score || 0), 1);
    $('mood-hot-tickers').innerHTML = tickers.slice(0, 12).map(x => {
        const pol = x.polarity_score ?? 0;
        const icon = pol > 0.2 ? '🚀' : pol < -0.2 ? '💥' : '•';
        const engPct = Math.round((x.engagement_score || 0) / maxEng * 100);
        return `<span class="inline-flex flex-col gap-0.5 px-2.5 py-1.5 rounded glass-card" style="min-width:96px;">
            <span class="flex items-center justify-between gap-2">
                <span class="font-bold text-xs" style="color:var(--text-main);">${icon} ${esc(x.ticker)}</span>
                <span class="text-[9px] font-mono" style="color:var(--text-muted);">${x.mention_count || 0}×</span>
            </span>
            <span class="relative h-1 rounded overflow-hidden" style="background:var(--border);">
              <span style="position:absolute;left:0;top:0;bottom:0;width:${engPct}%;background:${polColor(pol, -0.2, 0.2)};"></span>
            </span>
        </span>`;
    }).join('');

    // market-wide buzz pills
    const buzz = (full?.market_wide_buzz?.length ? full.market_wide_buzz : tr?.market_wide_buzz) || [];
    const strip = $('mood-buzz-strip');
    if (buzz.length) {
        strip.style.display = '';
        strip.innerHTML = `<span class="text-[10px] uppercase tracking-wider mr-2" style="color:var(--text-muted);">${esc(t.buzz_label || '市場熱議')}</span>` +
            buzz.map(b => {
                const pol = b.polarity_score ?? 0;
                return `<span class="mood-chip" title="posts=${b.post_count} · engagement=${b.engagement_score}">
                    ${esc(b.topic)} <span style="color:${polColor(pol, -0.2, 0.2)};">${signed(pol)}</span></span>`;
            }).join('');
    } else strip.style.display = 'none';

    // post feed — full trending_tickers.json only (slim copy lacks source/engagement)
    const feedEl = $('mood-posts-feed');
    const posts = [];
    const seen = new Set();
    const collect = arr => (arr || []).forEach(item =>
        (item.sample_posts || []).forEach(p => {
            if (!p.url || seen.has(p.url)) return;
            if (String(p.source || '').startsWith('Truth Social')) return; // 4b handles these
            seen.add(p.url);
            posts.push({ ...p, ticker: item.ticker || null });
        }));
    collect(full?.tickers);
    collect(full?.market_wide_buzz);
    posts.sort((a, b) => (b.engagement || 0) - (a.engagement || 0));
    const top = posts.slice(0, 14);
    if (!top.length) { feedEl.innerHTML = ''; return; }
    feedEl.innerHTML = `<div class="text-[10px] uppercase tracking-wider mb-1" style="color:var(--text-muted);">${esc(t.posts_label || '熱門貼文')}</div>` +
        top.map(p => {
            const [name, color] = _sourceBadge(p.source);
            return `<div class="mood-row">
                <span class="flex items-center gap-2 min-w-0">
                    <span class="mood-srcbadge" style="background:${color}22;color:${color};">${esc(name)}</span>
                    <a href="${esc(p.url)}" target="_blank" rel="noopener" class="truncate hover:text-indigo-400 transition-all" style="color:var(--text-main);">${esc(p.headline)}</a>
                </span>
                <span class="flex items-center gap-2 shrink-0">
                    ${p.ticker ? `<span class="text-[10px] font-mono" style="color:var(--text-muted);">${esc(p.ticker)}</span>` : ''}
                    <span style="width:8px;height:8px;border-radius:50%;background:${polColor(p.polarity, -0.2, 0.2)};display:inline-block;"></span>
                </span>
            </div>`;
        }).join('');
}

// ═════════════════════════ 4b. TRUMP POLICY RADAR ═══════════════════════════

function _lexHits(text, terms) {
    const lo = String(text || '').toLowerCase();
    return terms.filter(term => lo.includes(term));
}

function renderTrump() {
    const t = _t();
    const sec = $('mood-trump');
    sec.classList.remove('hidden');
    $('mood-trump-title').querySelector('span').textContent = t.trump_section || '川普政策雷達';
    $('mood-trump-hint').textContent = t.trump_hint || '';

    const cutoff = Date.now() - 48 * 3600 * 1000;
    const raw = (S.rawStream?.items || [])
        .filter(x => String(x.source || '').startsWith('Truth Social'))
        .filter(x => {
            const d = new Date(x.published || 0);
            return !isNaN(d) && d.getTime() >= cutoff;
        });
    const body = $('mood-trump-body');
    if (!raw.length) {
        body.innerHTML = `<div class="mood-empty">${esc(t.trump_empty || '近 48 小時無川普帖文')}</div>`;
        return;
    }

    // attach existing debate verdicts by url (already-paid LLM output)
    const byUrl = {};
    (S.feed?.items || []).forEach(it => { if (it.url) byUrl[it.url] = it; });

    body.innerHTML = raw.slice(0, 8).map(p => {
        const text = p.headline || p.raw_summary || '';
        const policyHits = _lexHits(text, POLICY_TERMS);
        const flipHits = _lexHits(text, FLIP_TERMS);
        let html = esc(text.length > 220 ? text.slice(0, 220) + '…' : text);
        policyHits.forEach(term => {
            html = html.replace(new RegExp(`(${term.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')})`, 'ig'),
                `<mark style="background:transparent;color:#f59e0b;font-weight:700;">$1</mark>`);
        });
        const debate = byUrl[p.url];
        return `<div class="mood-row" style="align-items:flex-start;">
            <span class="flex flex-col gap-1 min-w-0">
                <span style="color:var(--text-main);line-height:1.5;">${html}</span>
                <span class="flex items-center gap-2 flex-wrap">
                    <span class="text-[10px] font-mono" style="color:var(--text-muted);">${fmtTime(p.published)}</span>
                    ${flipHits.length ? `<span class="mood-verdict-badge" style="background:#f59e0b22;color:#f59e0b;border:1px solid #f59e0b55;">⚠ ${esc(t.flip_flag || '可能轉彎')}: ${esc(flipHits.slice(0, 3).join(', '))}</span>` : ''}
                    ${debate ? `${verdictBadge(debate.consensus_verdict)}${debate.final_take ? `<span class="text-[10px]" style="color:var(--text-muted);">${esc(debate.final_take.slice(0, 140))}</span>` : ''}` : ''}
                    <a href="${esc(p.url)}" target="_blank" rel="noopener" class="text-[10px] hover:text-indigo-400" style="color:var(--text-muted);">↗</a>
                </span>
            </span>
        </div>`;
    }).join('');
}

// ═════════════════════════ 5. DEBATE SIGNALS ════════════════════════════════

function renderDebates() {
    const t = _t();
    const sec = $('mood-debates');
    const items = S.feed?.items || [];
    const clusters = S.clusters?.clusters || [];
    if (!items.length && !clusters.length) { sec.classList.add('hidden'); return; }
    sec.classList.remove('hidden');
    $('mood-debates-title').querySelector('span').textContent = t.debates_section || '突發辯論訊號';
    $('mood-debates-link').textContent = t.view_all || '看全部 →';

    // hot clusters strip (top 5 by heat)
    const strip = $('mood-clusters-strip');
    const hot = [...clusters].sort((a, b) => (b.heat || 0) - (a.heat || 0)).slice(0, 5);
    if (hot.length) {
        strip.style.display = '';
        strip.innerHTML = `<span class="text-[10px] uppercase tracking-wider mr-1" style="color:var(--text-muted);">${esc(t.clusters_hot || '熱事件')}</span>` +
            hot.map(c => {
                const h = c.rep_headline || '';
                return `<span class="mood-chip" title="${esc(h)}">
                    <span class="truncate" style="max-width:260px;color:var(--text-main);">${esc(h.length > 48 ? h.slice(0, 48) + '…' : h)}</span>
                    <strong style="color:#f59e0b;">×${c.echo_count}</strong></span>`;
            }).join('');
    } else strip.style.display = 'none';

    // closed debate rows; click toggles final_take
    const credColor = { HIGH: C_BULL, MEDIUM: '#f59e0b', LOW: C_BEAR };
    $('mood-debates-list').innerHTML = items.slice(0, 10).map((it, i) => {
        const headline = it.headline_zh || it.headline || '—';
        const take = it.final_take
            ? `<div id="mood-take-${i}" class="hidden text-[11px] pl-2 pb-2" style="color:var(--text-muted);line-height:1.6;border-left:2px solid var(--border);margin-left:4px;">${esc(it.final_take)}</div>`
            : '';
        return `<div>
            <div class="mood-row" style="cursor:${it.final_take ? 'pointer' : 'default'};" ${it.final_take ? `onclick="document.getElementById('mood-take-${i}').classList.toggle('hidden')"` : ''}>
                <span class="flex items-center gap-2 min-w-0">
                    ${verdictBadge(it.consensus_verdict)}
                    <span class="truncate" style="color:var(--text-main);">${esc(headline)}</span>
                </span>
                <span class="flex items-center gap-2 shrink-0">
                    ${(it.echo_count || 0) > 1 ? `<span class="text-[10px] font-mono" style="color:#f59e0b;">×${it.echo_count}</span>` : ''}
                    <span title="${esc(it.credibility || '')}" style="width:7px;height:7px;border-radius:50%;background:${credColor[it.credibility] || C_NEU};display:inline-block;"></span>
                    <span class="text-[10px] font-mono" style="color:var(--text-muted);">${fmtTime(it.fetched_at)}</span>
                </span>
            </div>
            ${take}
        </div>`;
    }).join('');
}

// ═════════════════════════ 6. SECTOR RANKING ════════════════════════════════

function renderSectorRanking() {
    const t = _t();
    const wrap = $('mood-sector-wrap');
    const rsp = S.data?.tactical?.retail_sector_pulse;
    if (!rsp || rsp.status !== 'success' || !Array.isArray(rsp.sectors)) {
        wrap.classList.add('hidden');
        return;
    }
    wrap.classList.remove('hidden');
    $('mood-sector-title').querySelector('span').textContent = t.sector_section || '產業情緒排行';

    // intraday % per GICS sector (heatmap names ≈ pulse names after normalize)
    const tape = computeTape(S.heatmap);
    const intraBySec = {};
    (tape?.sectors || []).forEach(s => { intraBySec[s.name.toLowerCase().replace(/[ _]/g, '')] = s.pct; });
    const intradayFor = name => intraBySec[String(name || '').toLowerCase().replace(/[ _]/g, '')];

    const sorted = [...rsp.sectors].sort((a, b) => (b.composite_score ?? -9) - (a.composite_score ?? -9));
    $('mood-sector-list').innerHTML = sorted.map(s => {
        const dir = s.composite_direction || 'neutral_mixed';
        const dirColor = RSP_TEXT_BY_DIR[dir] || C_NEU;
        const comp = s.composite_score;
        const pol = s.retail_polarity_score;
        const barPct = pol != null ? Math.min(Math.abs(pol), 1) * 50 : 0;
        const barSide = (pol ?? 0) >= 0 ? 'left:50%;' : 'right:50%;';
        const intra = intradayFor(s.sector);
        const news = s.news_count_72h
            ? `<span style="color:${polColor(s.news_sentiment_score, -0.5, 0.5)};">${(s.news_sentiment_score ?? 0) > 0.5 ? '▲' : (s.news_sentiment_score ?? 0) < -0.5 ? '▼' : '—'} ${s.news_count_72h}</span>`
            : `<span style="color:var(--text-muted);">—</span>`;
        return `<div class="mood-row">
            <a href="sector.html" class="font-bold hover:text-indigo-400 transition-all shrink-0" style="color:var(--text-main);width:170px;">
                ${esc(s.sector)} <span class="text-[10px] font-normal font-mono" style="color:var(--text-muted);">${esc(s.proxy_etf || '')}</span></a>
            <span class="mood-verdict-badge shrink-0" style="background:${dirColor}18;color:${dirColor};border:1px solid ${dirColor}44;width:84px;text-align:center;">
                ${_rspLabelText(dir)} ${comp != null ? signed(comp) : ''}</span>
            <span class="relative h-1.5 rounded overflow-hidden flex-1" style="background:var(--border);min-width:80px;" title="retail polarity ${pol != null ? signed(pol) : '—'}">
                <span style="position:absolute;top:0;bottom:0;${barSide}width:${barPct}%;background:${polColor(pol, -0.2, 0.2)};"></span>
                <span style="position:absolute;left:50%;top:0;bottom:0;width:1px;background:var(--text-muted);opacity:.4;"></span>
            </span>
            <span class="text-[11px] font-mono shrink-0" style="width:72px;text-align:right;color:${polColor(intra, -0.05, 0.05)};">
                ${intra != null ? `${signed(intra, 1)}%` : ''}</span>
            <span class="text-[11px] font-mono shrink-0" style="width:52px;text-align:right;">${news}</span>
        </div>`;
    }).join('');
}

// ═════════════════════════ 7. GAUGES STRIP (demoted) ════════════════════════

function renderTiles() {
    const t = _t();
    const mm = S.data?.market_mood;
    const sec = $('mood-tiles');
    if (!mm || mm.status !== 'success') { sec.classList.add('hidden'); return; }
    sec.classList.remove('hidden');
    $('mood-tiles-title').querySelector('span').textContent = t.tiles_section || '期權與情緒指標';

    const opt = mm.options || {};
    const optColor = opt.tilt === 'bull' ? C_BULL : opt.tilt === 'bear' ? C_BEAR : C_NEU;
    $('mood-tile-options').style.borderLeftColor = optColor;
    $('mood-options-value').textContent = opt.put_call_ratio != null ? opt.put_call_ratio.toFixed(2) : '—';
    $('mood-options-value').style.color = optColor;
    $('mood-options-interp').textContent = (_zh() ? opt.interpretation_zh : opt.interpretation) || opt.interpretation_zh || '';

    const vix = mm.vix || {}, skew = mm.skew || {};
    const vixColor = vix.regime === 'LOW' ? C_BULL
        : (vix.regime === 'ELEVATED' || vix.regime === 'CRISIS') ? C_BEAR : C_NEU;
    $('mood-tile-vix').style.borderLeftColor = vixColor;
    $('mood-vix-value').innerHTML = vix.current != null
        ? `${vix.current}<span class="text-xs" style="color:var(--text-muted);"> ${esc(vix.regime || '')}</span>` : '—';
    const skewLine = skew.current != null ? `SKEW ${skew.current} (${skew.label || '—'})` : '';
    $('mood-vix-interp').textContent = [vix.interpretation_zh, skewLine].filter(Boolean).join(' · ');

    const fg = mm.fear_greed || {};
    const fgColor = fg.index >= 60 ? C_BULL : fg.index <= 40 ? C_BEAR : C_NEU;
    $('mood-tile-fg').style.borderLeftColor = fgColor;
    $('mood-fg-value').innerHTML = fg.index != null
        ? `${fg.index}<span class="text-xs" style="color:var(--text-muted);"> ${esc(fg.label || '')}</span>` : '—';
    $('mood-fg-value').style.color = fgColor;
    const subLabels = {
        market_momentum_sp500: '動能', stock_price_strength: '強度', stock_price_breadth: '廣度',
        put_call_options: 'Put/Call', market_volatility_vix: 'VIX', safe_haven_demand: '避險',
        junk_bond_demand: '高收益債',
    };
    $('mood-fg-subs').innerHTML = Object.entries(fg.sub_indices || {}).map(([k, v]) => {
        const c = v >= 60 ? C_BULL : v <= 40 ? C_BEAR : C_NEU;
        return `<div class="flex items-center gap-1.5 text-[9px]">
            <span style="color:var(--text-muted);width:48px;" class="shrink-0">${subLabels[k] || k}</span>
            <span class="relative h-1 rounded flex-1 overflow-hidden" style="background:var(--border);">
              <span style="position:absolute;left:0;top:0;bottom:0;width:${Math.max(0, Math.min(100, v))}%;background:${c};"></span>
            </span>
            <span class="font-mono" style="color:var(--text-muted);width:18px;text-align:right;">${Math.round(v)}</span>
        </div>`;
    }).join('');
}

// ═════════════════════════ ORCHESTRATION ════════════════════════════════════

function renderAll() {
    const t = _t();
    const hasVerdict = renderVerdict();
    renderTrendExtras();
    renderIntraday();
    renderSocial();
    renderTrump();
    renderDebates();
    renderSectorRanking();
    renderTiles();
    const noData = $('mood-no-data');
    if (noData) noData.classList.toggle('hidden', hasVerdict || !!S.data?.market_mood);
    const disclaimer = $('mood-disclaimer');
    if (disclaimer) disclaimer.textContent = t.disclaimer || '';
    const asof = $('mood-as-of');
    if (asof) {
        const stamps = [];
        if (S.brief?.current?.generated_at) stamps.push(`brief ${fmtTime(S.brief.current.generated_at)}`);
        if (S.heatmap?.last_update) stamps.push(`tape ${fmtTime(S.heatmap.last_update)}`);
        asof.textContent = stamps.join(' · ');
    }
    if (window.lucide) lucide.createIcons();
}

async function loadBnBatch() {
    const [brief, trends, feed, clusters, raw, trending] = await Promise.allSettled([
        fetchJson('/api/break-news/brief?history=1'),
        fetchJson('/api/break-news/trends'),
        fetchJson('/api/break-news/feed?state=closed,partial_closed&limit=30'),
        fetchJson('/api/break-news/clusters'),
        fetchJson('/api/break-news/raw-stream?limit=200'),
        fetchJson('trending_tickers.json?t=' + Date.now()),
    ]);
    if (brief.status === 'fulfilled') S.brief = brief.value;
    if (trends.status === 'fulfilled') S.trends = trends.value;
    if (feed.status === 'fulfilled') S.feed = feed.value;
    if (clusters.status === 'fulfilled') S.clusters = clusters.value;
    if (raw.status === 'fulfilled') S.rawStream = raw.value;
    if (trending.status === 'fulfilled') S.trendingFull = trending.value;
}

async function loadHeatmap() {
    try { S.heatmap = await fetchJson('/api/heatmap/data'); }
    catch (e) { /* keep last good copy */ }
}

// heatmap timer runs only while the market is open and the tab is visible
function scheduleHeatmapPoll() {
    if (_heatmapTimer) { clearInterval(_heatmapTimer); _heatmapTimer = null; }
    if (!S.heatmap?.market_open) return;
    _heatmapTimer = setInterval(async () => {
        if (document.hidden) return;
        await loadHeatmap();
        renderVerdict();
        renderIntraday();
        renderSectorRanking();
        if (!S.heatmap?.market_open) scheduleHeatmapPoll();   // market just closed
    }, 180_000);
}

async function boot() {
    const dataP = window.DataStore ? DataStore.get() : fetchJson('data.json?t=' + Date.now());
    await Promise.allSettled([
        dataP.then(d => { S.data = d; }),
        loadBnBatch(),
        loadHeatmap(),
    ]);
    renderAll();
    scheduleHeatmapPoll();

    _trendInst = TrendChart.mount({ root: $('mood-trend-chart'), withSelector: true });

    // bn artifacts refresh on one shared 5-min timer
    setInterval(async () => {
        if (document.hidden) return;
        await loadBnBatch();
        renderAll();
    }, 300_000);
    // trend chart re-pull every 10 min
    setInterval(() => { if (!document.hidden && _trendInst) _trendInst.reload(); }, 600_000);

    document.addEventListener('visibilitychange', () => {
        if (!document.hidden) { loadHeatmap().then(() => { renderIntraday(); scheduleHeatmapPoll(); }); }
    });
}

function translate() {
    const t = _t();
    if (t.title) $('mood-title').textContent = t.title;
    if (t.subtitle) $('mood-subtitle').textContent = t.subtitle;
    if (t.experimental) $('mood-experimental-text').textContent = t.experimental;
    if (t.no_data) $('mood-no-data-text').textContent = t.no_data;
    renderAll();
    if (_trendInst) _trendInst.refresh();
}

function reload() {
    if (window.DataStore) DataStore.refresh?.();
    loadBnBatch().then(renderAll);
    loadHeatmap().then(() => { renderIntraday(); scheduleHeatmapPoll(); });
    if (_trendInst) _trendInst.reload();
}

document.addEventListener('DOMContentLoaded', () => {
    UI.boot('mood', { translate, reload, onThemeChange: renderAll });
    if (window.DataStore) {
        DataStore.subscribe(d => { S.data = d; renderAll(); });
    }
    boot().catch(err => console.error('Mood boot failed:', err));
});
