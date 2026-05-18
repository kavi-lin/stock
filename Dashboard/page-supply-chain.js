/**
 * page-supply-chain.js — US supply-chain explorer.
 * Layered upstream→downstream diagram of LLM-drafted, data-grounded value chains.
 * Depends on: utils.js (UI.renderSidebar), i18n.js.
 */
document.addEventListener('DOMContentLoaded', () => {
  const NODE_W = 198, NODE_H = 100, V_GAP = 16, COL_GAP = 66;
  const HEADER_H = 44, PAD = 26;
  // module sub-panel geometry
  const MOD_HEAD = 26, MOD_GAP = 16, MOD_SIDE = 11, MOD_TOP_PLAIN = 9, MOD_BOT = 11;
  const MOD_W = NODE_W + MOD_SIDE * 2;
  const COL_W = MOD_W + COL_GAP;

  const LISTING_COLOR = {
    us_listed: '#22c55e', foreign_listed: '#3b82f6',
    pre_ipo: '#a855f7', private: '#71717a',
  };
  const GROUNDING = {
    verified: { icon: '✓', color: '#22c55e', bg: 'rgba(34,197,94,0.13)', bd: 'rgba(34,197,94,0.32)',
                zh: '追蹤中', en: 'Verified' },
    seen:     { icon: '◦', color: '#60a5fa', bg: 'rgba(59,130,246,0.13)', bd: 'rgba(59,130,246,0.32)',
                zh: '有資料', en: 'Seen' },
    llm_only: { icon: '⚠', color: '#f59e0b', bg: 'rgba(245,158,11,0.13)', bd: 'rgba(245,158,11,0.32)',
                zh: '僅 LLM', en: 'LLM-only' },
  };
  const HEAT_COLOR = { hot: '#ef4444', warm: '#f97316', cold: '#3b82f6', none: null };
  const HEAT_LABEL = {
    hot:  { zh: '熱', en: 'Hot' }, warm: { zh: '溫', en: 'Warm' },
    cold: { zh: '冷', en: 'Cold' },
  };
  const LISTING_LABEL = {
    us_listed:      { zh: '美股上市', en: 'US-listed' },
    foreign_listed: { zh: '外股',     en: 'Foreign-listed' },
    pre_ipo:        { zh: '擬上市',   en: 'Pre-IPO' },
    private:        { zh: '私有',     en: 'Private' },
  };
  const groundingLabel = (k) => { const m = GROUNDING[k]; return m ? (isZh() ? m.zh : m.en) : k; };
  const heatLabel = (k) => { const m = HEAT_LABEL[k]; return m ? (isZh() ? m.zh : m.en) : k; };
  const listingLabel = (k) => { const m = LISTING_LABEL[k]; return m ? (isZh() ? m.zh : m.en) : k; };
  // Commercialization stage ramp — design partner → revenue recognized.
  // `unknown` is intentionally absent so it renders no badge.
  const STAGE = {
    design_partner: { zh: '設計夥伴', en: 'Design',  color: '#94a3b8' },
    sampling:       { zh: '送樣',     en: 'Sampling', color: '#3b82f6' },
    qualification:  { zh: '驗證',     en: 'Qual',    color: '#eab308' },
    production:     { zh: '量產',     en: 'Production', color: '#f97316' },
    revenue:        { zh: '營收認列', en: 'Revenue', color: '#22c55e' },
  };
  const stageLabel = (s) => { const m = STAGE[s]; return m ? (isZh() ? m.zh : m.en) : ''; };

  // Legend pill hover tooltips — same pattern as sector.html.
  const SC_PILL_TIPS = {
    us: {
      zh: { title: 'US 上市', desc: '在美國交易所掛牌的公司，美股帳戶可直接買賣。' },
      en: { title: 'US-listed', desc: 'Listed on a US exchange — directly tradeable in a US brokerage account.' },
    },
    fl: {
      zh: { title: '外股', desc: '在非美國交易所掛牌（台 / 韓 / 日 / 歐 等）。美股帳戶通常買不到，需 ADR 或複委託。' },
      en: { title: 'Foreign-listed', desc: 'Listed on a non-US exchange (TW/KR/JP/EU…). Usually needs an ADR or an international broker.' },
    },
    pi: {
      zh: { title: '擬上市 Pre-IPO', desc: '已遞件或預期近期 IPO，尚未掛牌。目前無法買進，只能留意。' },
      en: { title: 'Pre-IPO', desc: 'Filed or expected to IPO soon — not yet listed. Watch only, not tradeable.' },
    },
    pv: {
      zh: { title: '私有公司', desc: '未上市的私有公司。屬研究線索，無法投資。' },
      en: { title: 'Private', desc: 'A private, unlisted company. A research lead, not investable.' },
    },
    verified: {
      zh: { title: '追蹤中 Verified', desc: '此 ticker 在系統追蹤的美股 universe 內 — 真實、可投資、有完整本地資料佐證。' },
      en: { title: 'Verified', desc: 'Ticker is in the tracked US universe — real, investable, fully backed by local data.' },
    },
    seen: {
      zh: { title: '有資料 Seen', desc: '公司在知識圖譜或新聞出現過，但不在核心追蹤 universe（外股或小型股）。真實，但資料較少。' },
      en: { title: 'Seen', desc: 'Appears in the knowledge graph / news but not in the core universe (foreign or small-cap). Real but thinly covered.' },
    },
    llm: {
      zh: { title: '僅 LLM Unverified', desc: '本地資料完全查無此公司 — 純 LLM 生成內容，未經佐證，需自行查證。' },
      en: { title: 'LLM-only', desc: 'No trace in any local data — purely LLM-asserted and unverified. Check it yourself.' },
    },
    heat: {
      zh: { title: '近期熱度', desc: '節點卡的外光暈強度 = 該公司近期在知識圖譜的被提及熱度。',
            scale: '🔴 hot　提及 ≥ 40\n🟠 warm　15 – 39\n🔵 cold　1 – 14\n⚪ none　無近期提及' },
      en: { title: 'Recent Heat', desc: 'Card glow intensity = how often the company is mentioned recently in the knowledge graph.',
            scale: '🔴 hot　≥ 40 mentions\n🟠 warm　15 – 39\n🔵 cold　1 – 14\n⚪ none　no recent mentions' },
    },
    stage: {
      zh: { title: '商用階段', desc: '公司在此供應鏈主題上的商業化成熟度（相對主線標的）。僅在有公開證據時標記。',
            scale: '⚫ 設計夥伴 → 🔵 送樣 → 🟡 驗證 → 🟠 量產 → 🟢 營收認列' },
      en: { title: 'Commercialization Stage', desc: "The company's commercialization maturity for this chain's theme. Tagged only when public evidence exists.",
            scale: '⚫ Design → 🔵 Sampling → 🟡 Qual → 🟠 Production → 🟢 Revenue' },
    },
  };

  let currentChain = null;
  let selectedNodeId = null;

  const $ = (id) => document.getElementById(id);
  const isZh = () => UI && UI.currentLang === 'zh';
  const t = (zh, en) => (isZh() ? zh : en);

  function applyTranslations() {
    $('sc-title').textContent = t('供應鏈探索', 'Supply Chain Explorer');
    $('sc-subtitle').textContent = t('Supply Chain Explorer', '供應鏈探索');
    $('sc-theme-input').placeholder = t('輸入主題 (CPO / HBM…)', 'Theme (CPO / HBM…)');
    $('sc-gen-btn').textContent = t('生成', 'Generate');
    $('sc-lg-us').textContent = t('US 上市', 'US-listed');
    $('sc-lg-fl').textContent = t('外股', 'Foreign');
    $('sc-lg-pi').textContent = t('擬上市', 'Pre-IPO');
    $('sc-lg-pv').textContent = t('私有', 'Private');
    $('sc-lg-verified').textContent = t('追蹤中', 'verified');
    $('sc-lg-seen').textContent = t('有資料', 'seen');
    $('sc-lg-llm').textContent = t('僅 LLM', 'llm-only');
    $('sc-lg-heat').textContent = t('熱度', 'heat');
    $('sc-lg-stage').textContent = t('商用階段', 'stage');
    if (currentChain) renderDiagram(currentChain);
  }

  async function fetchJson(url, opts) {
    const r = await fetch(url, opts || {});
    const j = await r.json().catch(() => ({}));
    if (!r.ok) throw new Error(j.error || `${r.status} ${r.statusText}`);
    return j;
  }

  function prettyLayer(s) {
    return String(s || '').replace(/_/g, ' ').toUpperCase();
  }
  function esc(s) {
    return String(s == null ? '' : s).replace(/[&<>"]/g,
      c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
  }

  // ── data loading ───────────────────────────────────────────────
  async function loadChainList(selectSlug) {
    try {
      const r = await fetchJson('/api/supply-chain/list');
      const sel = $('sc-chain-select');
      sel.innerHTML = (r.chains || []).map(c =>
        `<option value="${esc(c.id)}">${esc(c.title)} · ${c.node_count}</option>`).join('')
        || `<option value="">${t('尚無供應鏈', 'no chains yet')}</option>`;
      if (selectSlug) sel.value = selectSlug;
      return sel.value;
    } catch (e) { return null; }
  }

  async function loadThemes() {
    try {
      const r = await fetchJson('/api/supply-chain/themes');
      $('sc-theme-list').innerHTML =
        (r.themes || []).map(th => `<option value="${esc(th)}">`).join('');
    } catch (e) { /* non-fatal */ }
  }

  async function loadChain(slug) {
    if (!slug) return;
    showStatus(t('載入中…', 'Loading…'));
    try {
      currentChain = await fetchJson('/api/supply-chain/' + encodeURIComponent(slug));
      selectedNodeId = null;
      hideDetail();
      renderDiagram(currentChain);
    } catch (e) {
      showStatus(t('載入失敗: ', 'Load failed: ') + e.message);
    }
  }

  async function generate() {
    const theme = $('sc-theme-input').value.trim();
    if (!theme) return;
    const btn = $('sc-gen-btn');
    btn.disabled = true;
    btn.innerHTML = `<span class="sc-spinner"></span>${t('生成中', 'Generating')}`;
    showStatus(t('LLM 生成供應鏈中，約 30-60 秒…', 'LLM drafting the chain — 30-60s…'));
    try {
      currentChain = await fetchJson('/api/supply-chain/generate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ theme }),
      });
      selectedNodeId = null;
      hideDetail();
      await loadChainList(currentChain.id);
      renderDiagram(currentChain);
    } catch (e) {
      showStatus(t('生成失敗: ', 'Generate failed: ') + e.message);
    } finally {
      btn.disabled = false;
      btn.textContent = t('生成', 'Generate');
    }
  }

  function showStatus(msg) {
    $('sc-status').textContent = msg;
    $('sc-status').style.display = 'block';
    $('sc-canvas').style.display = 'none';
  }

  // ── layout (2-level: stage column → module sub-panels → nodes) ──
  function moduleIdOf(chain, n) {
    if (n.module) return n.module;
    const ms = (chain.modules && chain.modules[n.layer]) || [];
    return ms.length ? ms[0].id : '_default';
  }

  function layout(chain) {
    const layers = chain.layers || [];
    const modulesMap = chain.modules || {};
    const spine = new Set(chain.spine || []);
    const pos = {}, panels = [], stageBands = [];
    let maxBottom = HEADER_H;

    layers.forEach((layer, li) => {
      const colX = PAD + li * COL_W;
      const mods = (modulesMap[layer] && modulesMap[layer].length)
        ? modulesMap[layer] : [{ id: '_default', label: '' }];
      let y = HEADER_H;
      mods.forEach(m => {
        const arr = (chain.nodes || []).filter(n =>
          n.layer === layer && moduleIdOf(chain, n) === m.id);
        if (!arr.length) return;                       // skip empty module
        arr.sort((a, b) => (spine.has(b.id) ? 1 : 0) - (spine.has(a.id) ? 1 : 0));
        const hasHead = !!(m.label && m.id !== '_default');
        const topInset = hasHead ? MOD_HEAD : MOD_TOP_PLAIN;
        const nodesH = arr.length * (NODE_H + V_GAP) - V_GAP;
        const panelH = topInset + nodesH + MOD_BOT;
        if (hasHead) {
          panels.push({ x: colX, y, w: MOD_W, h: panelH, label: m.label });
        }
        const y0 = y + topInset;
        arr.forEach((n, ni) => {
          pos[n.id] = { x: colX + MOD_SIDE, y: y0 + ni * (NODE_H + V_GAP) };
        });
        y += panelH + MOD_GAP;
      });
      const colBottom = y - MOD_GAP;
      stageBands.push({ layer, index: li + 1,
        x: colX - 5, y: HEADER_H - 8, w: MOD_W + 10, h: colBottom - HEADER_H + 14 });
      if (colBottom > maxBottom) maxBottom = colBottom;
    });

    return {
      pos, panels, stageBands,
      width: PAD * 2 + layers.length * COL_W - COL_GAP,
      height: maxBottom + PAD,
    };
  }

  // cross-stage edge: bezier left→right
  function edgePath(s, d) {
    const x1 = s.x + NODE_W, y1 = s.y + NODE_H / 2;
    const x2 = d.x, y2 = d.y + NODE_H / 2;
    const dx = Math.max(30, Math.abs(x2 - x1) * 0.45);
    return { d: `M${x1},${y1} C${x1 + dx},${y1} ${x2 - dx},${y2} ${x2},${y2}`,
             x1, y1, x2, y2 };
  }

  // same-column (intra-stage) edge: C-curve out the right side — no bulge
  // through the block.
  function sidePath(s, d) {
    const x1 = s.x + NODE_W, y1 = s.y + NODE_H / 2;
    const x2 = d.x + NODE_W, y2 = d.y + NODE_H / 2;
    const bulge = 54;
    return { d: `M${x1},${y1} C${x1 + bulge},${y1} ${x2 + bulge},${y2} ${x2},${y2}`,
             x1, y1, x2, y2 };
  }

  // ── render ─────────────────────────────────────────────────────
  function renderDiagram(chain) {
    const canvas = $('sc-canvas');
    const svg = $('sc-edges');
    $('sc-status').style.display = 'none';
    canvas.style.display = 'block';
    const L = layout(chain);
    const spine = new Set(chain.spine || []);

    canvas.style.width = L.width + 'px';
    canvas.style.height = L.height + 'px';
    svg.setAttribute('width', L.width);
    svg.setAttribute('height', L.height);

    // ── edges — per-edge userSpaceOnUse gradient (objectBoundingBox
    // degenerates to invisible on perfectly horizontal edges) ──
    let grads = '', edgeSvg = '', particleSvg = '';
    (chain.edges || []).forEach((e, i) => {
      const s = L.pos[e.from], d = L.pos[e.to];
      if (!s || !d) return;
      const isSpine = spine.has(e.from) && spine.has(e.to);
      const sameCol = Math.abs(s.x - d.x) < 1;
      const P = sameCol ? sidePath(s, d) : edgePath(s, d);
      let stroke, width, opacity, dash = '', marker;
      if (isSpine) {
        grads += `<linearGradient id="sc-ge${i}" gradientUnits="userSpaceOnUse"`
          + ` x1="${P.x1}" y1="${P.y1}" x2="${P.x2}" y2="${P.y2}">`
          + `<stop offset="0" stop-color="#10b981"/>`
          + `<stop offset="1" stop-color="#fbbf24"/></linearGradient>`;
        stroke = `url(#sc-ge${i})`; width = 2.6; opacity = 0.95;
        marker = 'sc-arrow-spine';
      } else if (sameCol) {
        stroke = '#71717a'; width = 1.2; opacity = 0.4;
        dash = ' stroke-dasharray="4 3"'; marker = 'sc-arrow';
      } else {
        stroke = '#71717a'; width = 1.3; opacity = 0.42; marker = 'sc-arrow';
      }
      edgeSvg += `<path d="${P.d}" fill="none" stroke="${stroke}" `
        + `stroke-width="${width}" opacity="${opacity}"${dash} `
        + `marker-end="url(#${marker})"/>`;
      if (isSpine) {
        for (let p = 0; p < 2; p++) {
          particleSvg += `<circle r="2.6" fill="#fde68a">
            <animateMotion dur="2.8s" begin="${p * 1.4}s" repeatCount="indefinite"
              path="${P.d}"/>
            <animate attributeName="opacity" dur="2.8s" begin="${p * 1.4}s"
              values="0;1;1;0" keyTimes="0;0.15;0.85;1" repeatCount="indefinite"/>
          </circle>`;
        }
      }
    });
    svg.innerHTML = `<defs>
      <marker id="sc-arrow" viewBox="0 0 8 8" refX="6.5" refY="4" markerWidth="6"
        markerHeight="6" orient="auto-start-reverse">
        <path d="M0,0 L8,4 L0,8 z" fill="#71717a"/></marker>
      <marker id="sc-arrow-spine" viewBox="0 0 8 8" refX="6.5" refY="4" markerWidth="6.5"
        markerHeight="6.5" orient="auto-start-reverse">
        <path d="M0,0 L8,4 L0,8 z" fill="#fbbf24"/></marker>
      ${grads}</defs>` + edgeSvg + particleSvg;

    // ── stage bands + headers + module panels + nodes ──
    let html = '';
    L.stageBands.forEach(b => {
      html += `<div class="sc-band" style="left:${b.x}px;top:${b.y}px;`
        + `width:${b.w}px;height:${b.h}px;"></div>`;
      html += `<div class="sc-colhead" style="left:${b.x + 5}px;top:14px;`
        + `width:${MOD_W}px;">
        <span class="sc-colhead-idx">${b.index}</span>
        <span class="sc-colhead-name">${esc(prettyLayer(b.layer))}</span>
      </div>`;
    });
    L.panels.forEach(p => {
      html += `<div class="sc-module" style="left:${p.x}px;top:${p.y}px;`
        + `width:${p.w}px;height:${p.h}px;">`
        + `<div class="sc-module-head">${esc(p.label)}</div></div>`;
    });
    let order = 0;
    (chain.nodes || []).forEach(n => {
      const p = L.pos[n.id];
      if (!p) return;
      const stripe = LISTING_COLOR[n.listing] || '#71717a';
      const g = GROUNDING[n.grounding] || GROUNDING.llm_only;
      const heat = HEAT_COLOR[n.heat];
      const isSpine = spine.has(n.id);
      const tkr = n.ticker
        ? `<span class="sc-tkr sc-tkr-real">${esc(n.ticker)}</span>`
        : `<span class="sc-tkr sc-tkr-none">${t('未上市', 'PRIVATE')}</span>`;
      const heatTag = heat
        ? `<span class="sc-heat-tag"><span class="sc-heat-dot"
            style="background:${heat};"></span>${esc(heatLabel(n.heat))}</span>`
        : '';
      const sg = STAGE[n.stage];
      const stageTag = sg
        ? `<span class="sc-stage" style="color:${sg.color};
            border-color:color-mix(in srgb,${sg.color} 45%,transparent);
            background:color-mix(in srgb,${sg.color} 13%,transparent);"
            >${esc(stageLabel(n.stage))}</span>`
        : '';
      const cls = 'sc-node'
        + (heat ? ` sc-heat-${n.heat}` : '')
        + (isSpine ? ' sc-spine' : '')
        + (n.id === selectedNodeId ? ' sc-sel' : '');
      html += `<div class="${cls}" data-node="${esc(n.id)}"
        style="left:${p.x}px;top:${p.y}px;width:${NODE_W}px;height:${NODE_H}px;
        animation-delay:${order * 28}ms;">
        <i class="sc-node-stripe" style="background:linear-gradient(180deg,
          ${stripe} 0%,color-mix(in srgb,${stripe} 35%,transparent) 100%);"></i>
        <div class="sc-node-top">
          <span class="sc-node-label">${esc(n.label)}</span>${tkr}
        </div>
        <div class="sc-role">${esc(n.role)}</div>
        <div class="sc-badges">
          <span class="sc-badge" style="color:${g.color};background:${g.bg};
            border:1px solid ${g.bd};">${g.icon} ${esc(groundingLabel(n.grounding))}</span>
          ${heatTag}
          ${stageTag}
        </div>
      </div>`;
      order++;
    });
    [...canvas.querySelectorAll('.sc-node,.sc-colhead,.sc-band,.sc-module')]
      .forEach(el => el.remove());
    canvas.insertAdjacentHTML('beforeend', html);
    canvas.querySelectorAll('.sc-node').forEach(el => {
      el.addEventListener('click', () => selectNode(el.dataset.node));
    });

    const modCount = Object.values(chain.modules || {})
      .reduce((a, m) => a + (m ? m.length : 0), 0);
    $('sc-meta').textContent =
      `${(chain.nodes || []).length} ${t('家公司', 'COS')} · `
      + `${(chain.layers || []).length} ${t('層', 'LAYERS')} · `
      + `${modCount} ${t('模塊', 'MODULES')} · `
      + `${(chain.edges || []).length} ${t('關係', 'LINKS')}`;
  }

  // ── node detail ────────────────────────────────────────────────
  function selectNode(id) {
    selectedNodeId = id;
    renderDiagram(currentChain);
    const n = (currentChain.nodes || []).find(x => x.id === id);
    if (!n) return;
    const edges = currentChain.edges || [];
    const labelOf = (nid) => {
      const m = (currentChain.nodes || []).find(x => x.id === nid);
      return m ? m.label : nid;
    };
    const g = GROUNDING[n.grounding] || GROUNDING.llm_only;
    const stripe = LISTING_COLOR[n.listing] || '#71717a';
    const edgeRow = (txt, e) => {
      const c = e.corroboration;
      const badge = (c && c.count)
        ? ` <span class="sc-edge-corr" title="${esc(t('知識圖譜佐證 (break-news + digest 關係)：', 'Nexus-corroborated (break-news + digest relations): ')
            + (c.sources || []).join(', '))}">✓${c.count}</span>`
        : '';
      return `<div class="sc-edge-row">${txt}
      <span class="sc-edge-rel">${esc(e.rel)}</span>${badge}</div>`;
    };
    const downstream = edges.filter(e => e.from === id)
      .map(e => edgeRow('→ ' + esc(labelOf(e.to)), e));
    const upstream = edges.filter(e => e.to === id)
      .map(e => edgeRow('← ' + esc(labelOf(e.from)), e));
    const d = $('sc-detail');
    d.style.setProperty('--sc-detail-accent', stripe);
    d.innerHTML = `
      <div class="sc-detail-head">
        <div style="min-width:0;">
          <div style="font-size:14px;font-weight:800;color:var(--text-card-title);">${esc(n.label)}</div>
          <div style="font-size:9.5px;font-weight:700;letter-spacing:0.08em;
            text-transform:uppercase;color:var(--text-muted);margin-top:2px;">
            ${esc(prettyLayer(n.layer))}</div>
        </div>
        <span class="sc-detail-x" id="sc-detail-x">✕</span>
      </div>
      <div class="sc-detail-body">
        <div class="sc-detail-row">${t('代號', 'Ticker')}:
          <strong>${esc(n.ticker || t('未上市 / 私有', 'private'))}</strong></div>
        <div class="sc-detail-row">${t('上市別', 'Listing')}: <strong>${esc(listingLabel(n.listing))}</strong></div>
        <div class="sc-detail-row">${t('資料支持', 'Grounding')}:
          <strong style="color:${g.color};">${g.icon} ${esc(groundingLabel(n.grounding))}</strong></div>
        <div class="sc-detail-row">${t('近期熱度', 'Heat')}:
          <strong>${n.heat && n.heat !== 'none' ? esc(heatLabel(n.heat)) : t('無', 'none')}</strong></div>
        <div class="sc-detail-row">${t('商用階段', 'Stage')}:
          <strong${STAGE[n.stage] ? ` style="color:${STAGE[n.stage].color};"` : ''}
          >${STAGE[n.stage] ? esc(stageLabel(n.stage)) : esc(n.stage || 'unknown')}</strong></div>
        <div class="sc-detail-sec">${t('角色', 'Role')}</div>
        <div style="font-size:11px;color:var(--text-main);line-height:1.5;">${esc(n.role)}</div>
        ${n.note ? `<div class="sc-detail-sec">${t('備註', 'Note')}</div>
          <div style="font-size:10.5px;color:var(--text-muted);line-height:1.5;">${esc(n.note)}</div>` : ''}
        ${downstream.length ? `<div class="sc-detail-sec">${t('供應給', 'Supplies to')}</div>${downstream.join('')}` : ''}
        ${upstream.length ? `<div class="sc-detail-sec">${t('上游來源', 'Upstream')}</div>${upstream.join('')}` : ''}
      </div>`;
    d.classList.add('show');
    $('sc-detail-x').addEventListener('click', hideDetail);
  }
  function hideDetail() {
    selectedNodeId = null;
    $('sc-detail').classList.remove('show');
  }

  // ── legend pill tooltip ────────────────────────────────────────
  function initPillTooltip() {
    const tip = $('pill-tooltip');
    if (!tip) return;
    let hideT = null;
    const show = (el) => {
      const data = SC_PILL_TIPS[el.dataset.tipKey];
      if (!data) return;
      const d = (isZh() ? data.zh : data.en) || data.en;
      tip.innerHTML = `<div class="tip-title">${esc(d.title)}</div>`
        + `<div class="tip-desc">${esc(d.desc)}</div>`
        + (d.scale ? `<div class="tip-scale">${esc(d.scale).replace(/\n/g, '<br>')}</div>` : '');
      tip.style.opacity = '0';
      tip.style.top = '-9999px';
      tip.classList.add('tip-visible');
      requestAnimationFrame(() => {
        const r = el.getBoundingClientRect();
        const tr = tip.getBoundingClientRect();
        let top = r.top - tr.height - 8;
        if (top < 8) top = r.bottom + 8;          // flip below if near top
        let left = r.left + (r.width - tr.width) / 2;
        left = Math.max(8, Math.min(left, window.innerWidth - tr.width - 8));
        tip.style.top = top + 'px';
        tip.style.left = left + 'px';
        tip.style.opacity = '';                   // CSS transition takes over
      });
    };
    const hide = () => tip.classList.remove('tip-visible');
    document.addEventListener('mouseover', (e) => {
      const pill = e.target.closest('[data-tip-key]');
      if (!pill) return;
      if (hideT) { clearTimeout(hideT); hideT = null; }
      show(pill);
    });
    document.addEventListener('mouseout', (e) => {
      const pill = e.target.closest('[data-tip-key]');
      if (!pill) return;
      hideT = setTimeout(hide, 80);
    });
  }

  // ── boot ───────────────────────────────────────────────────────
  if (typeof UI !== 'undefined' && UI.renderSidebar) {
    try { UI.renderSidebar(); } catch (e) { console.warn('sidebar', e); }
  }
  applyTranslations();
  $('sc-chain-select').addEventListener('change', (e) => loadChain(e.target.value));
  $('sc-gen-btn').addEventListener('click', generate);
  $('sc-theme-input').addEventListener('keydown', (e) => {
    if (e.key === 'Enter') generate();
  });

  initPillTooltip();
  loadThemes();
  loadChainList().then(slug => loadChain(slug));
  if (window.lucide && lucide.createIcons) lucide.createIcons();
});
