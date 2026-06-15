/**
 * page-graph.js — Project Nexus 知識圖譜 (V4.3.0 redesign)
 *
 * 結構重構：CO_THEME clique（N² hairball）→ theme hub-and-spoke。
 *  - ticker.metadata.themes 合成一級 theme 節點，ticker→theme MEMBER_OF 邊
 *  - CO_THEME 邊不再渲染（資訊已由 hub 表達）；結構邊（PEER_OF / SUPPLIES_TO …）保留直連
 *  - 點擊 = 聚焦模式：只留 1-2 hop ego 子圖；背景點擊 / ESC / 麵包屑退出
 *  - Zoom 修復：移除互搶的 auto-zoomToFit timer 與每幀 radial-gradient 特效；
 *    user 互動後永不自動 fit
 *
 * 相容：若載入 legacy 多型別 build（已含 theme/catalyst 節點）則跳過合成。
 */
(function () {
  'use strict';

  // ─── constants ───────────────────────────────────────────────────────────
  const EDGE_STYLE = {
    MEMBER_OF:        { color: 'rgba(251,191,36,0.30)', hover: 'rgba(251,191,36,0.85)', zh: '主題成員', en: 'Member' },
    PEER_OF:          { color: 'rgba(147,197,253,0.45)', hover: 'rgba(147,197,253,0.95)', zh: '同業',     en: 'Peer' },
    SUPPLIES_TO:      { color: 'rgba(34,197,94,0.55)',  hover: 'rgba(34,197,94,0.95)',  zh: '供應',     en: 'Supplies' },
    CUSTOMER_OF:      { color: 'rgba(34,197,94,0.40)',  hover: 'rgba(34,197,94,0.85)',  zh: '客戶',     en: 'Customer' },
    CONTRACT_MFG_FOR: { color: 'rgba(168,85,247,0.50)', hover: 'rgba(168,85,247,0.95)', zh: '代工',     en: 'Contract mfg' },
    COMPETES_WITH:    { color: 'rgba(239,68,68,0.50)',  hover: 'rgba(239,68,68,0.95)',  zh: '競爭',     en: 'Competes' },
    CO_DEVELOPS_WITH: { color: 'rgba(245,158,11,0.50)', hover: 'rgba(245,158,11,0.95)', zh: '合作',     en: 'Co-dev' },
    SUPPLY_CHAIN_HOP: { color: 'rgba(34,197,94,0.35)',  hover: 'rgba(34,197,94,0.80)',  zh: '供應鏈跳', en: 'SC hop' },
  };
  const NODE_COLOR = {
    ticker:    '#93c5fd',
    theme:     '#fbbf24',
    catalyst:  '#f87171',
    sector:    '#a78bfa',
    narrative: '#34d399',
    thesis:    '#f472b6',
  };
  const DIM_NODE = 'rgba(115,115,122,0.18)';
  const DIM_LINK = 'rgba(115,115,122,0.05)';

  // ─── state ───────────────────────────────────────────────────────────────
  let RAW = null;            // nexus_graph.json as loaded
  let FULL = null;           // transformed graph {nodes, links}
  let NODE_INDEX = new Map();
  let ADJ = new Map();       // id -> [{to, link}]
  let GraphInst = null;

  let focusRoot = null;      // node id when in focus mode
  let focusDepth = 1;
  let visibleEdgeTypes = new Set(Object.keys(EDGE_STYLE));
  let minWeight = 0;
  let hoverNode = null;
  let hoverNbrs = null;      // Set(id)
  let userInteracted = false;
  let didInitialFit = false;

  const isZh = () => !!(window.UI && window.UI.currentLang === 'zh');

  // ─── init ────────────────────────────────────────────────────────────────
  document.addEventListener('DOMContentLoaded', async () => {
    if (window.UI && UI.initTheme) UI.initTheme();
    if (window.UI && UI.renderSidebar) UI.renderSidebar('graph');
    if (window.lucide && lucide.createIcons) lucide.createIcons();
    try {
      RAW = await (await fetch('nexus_graph.json?t=' + Date.now(), { cache: 'no-store' })).json();
      FULL = transform(RAW);
      buildIndices(FULL);
      renderControls();
      mountGraph();
      updateMetaLine();
      hideStatus();
    } catch (err) { showStatusError(err); }
  });

  // ─── transform: CO_THEME clique → theme hubs ────────────────────────────
  function slugTheme(name) {
    return 'theme:' + String(name).toLowerCase().replace(/[^a-z0-9一-鿿]+/g, '_');
  }

  function transform(raw) {
    const srcNodes = raw.nodes || [];
    const srcEdges = raw.edges || [];
    const tickerOnly = srcNodes.every(n => n.type === 'ticker');

    const nodes = srcNodes.map(n => ({ ...n }));
    const links = [];

    // Structural ticker↔ticker edges pass through; CO_THEME dropped (replaced by hubs).
    srcEdges.forEach(e => {
      if (tickerOnly && e.type === 'CO_THEME') return;
      links.push({ source: e.source, target: e.target, type: e.type, weight: e.weight || 0, confidence: e.confidence, last_seen: e.last_seen });
    });

    if (tickerOnly) {
      // Synthesize theme hubs from per-ticker metadata (top 2 themes each;
      // hubs with <2 members are noise — dropped together with their spokes).
      const hubs = new Map();
      const spokes = [];
      nodes.forEach(n => {
        const themes = ((n.metadata || {}).themes || []).slice(0, 2);
        themes.forEach(tn => {
          const id = slugTheme(tn);
          if (!hubs.has(id)) hubs.set(id, { id, type: 'theme', label: tn, members: 0 });
          hubs.get(id).members++;
          spokes.push({ source: n.id, target: id, type: 'MEMBER_OF', weight: 0.6 });
        });
      });
      const kept = new Set([...hubs.values()].filter(h => h.members >= 2).map(h => h.id));
      hubs.forEach(h => { if (kept.has(h.id)) nodes.push(h); });
      spokes.forEach(s => { if (kept.has(s.target)) links.push(s); });
    }
    return { nodes, links };
  }

  function buildIndices(g) {
    NODE_INDEX = new Map();
    ADJ = new Map();
    g.nodes.forEach(n => { NODE_INDEX.set(n.id, n); ADJ.set(n.id, []); });
    g.links.forEach(l => {
      ADJ.get(endId(l.source))?.push({ to: endId(l.target), link: l });
      ADJ.get(endId(l.target))?.push({ to: endId(l.source), link: l });
    });
  }

  function endId(end) { return end == null ? null : (typeof end === 'string' ? end : end.id); }

  // ─── view assembly (filters + focus) ─────────────────────────────────────
  function currentView() {
    let nodeSet = null;
    if (focusRoot && NODE_INDEX.has(focusRoot)) {
      nodeSet = new Set([focusRoot]);
      let frontier = [focusRoot];
      for (let d = 1; d <= focusDepth; d++) {
        const next = [];
        for (const id of frontier) {
          for (const { to, link } of (ADJ.get(id) || [])) {
            if (!passesEdgeFilter(link)) continue;
            if (!nodeSet.has(to)) { nodeSet.add(to); next.push(to); }
          }
        }
        frontier = next;
      }
    }
    const nodes = FULL.nodes.filter(n => !nodeSet || nodeSet.has(n.id));
    const ids = new Set(nodes.map(n => n.id));
    const links = FULL.links.filter(l => {
      if (!passesEdgeFilter(l)) return false;
      return ids.has(endId(l.source)) && ids.has(endId(l.target));
    });
    // Drop nodes isolated by edge filters in overview (keeps canvas clean);
    // in focus mode keep all BFS-reached nodes.
    if (!focusRoot) {
      const connected = new Set();
      links.forEach(l => { connected.add(endId(l.source)); connected.add(endId(l.target)); });
      return { nodes: nodes.filter(n => connected.has(n.id)), links };
    }
    return { nodes, links };
  }

  function passesEdgeFilter(l) {
    if (!visibleEdgeTypes.has(l.type)) return false;
    if (l.type !== 'MEMBER_OF' && (l.weight || 0) < minWeight) return false;
    return true;
  }

  function refreshView({ fit = false } = {}) {
    if (!GraphInst) return;
    hoverNode = null; hoverNbrs = null;
    GraphInst.graphData(currentView());
    if (fit) setTimeout(() => GraphInst.zoomToFit(500, 70), 420);
  }

  // ─── focus mode ──────────────────────────────────────────────────────────
  function enterFocus(node) {
    focusRoot = node.id;
    refreshView({ fit: true });
    renderDetailPanel(node);
    renderBreadcrumb(node);
  }

  function exitFocus() {
    if (!focusRoot) return;
    focusRoot = null;
    document.getElementById('ng-detail').classList.add('hidden');
    document.getElementById('ng-breadcrumb').classList.add('hidden');
    refreshView({ fit: true });
  }

  function renderBreadcrumb(node) {
    const bc = document.getElementById('ng-breadcrumb');
    bc.classList.remove('hidden');
    bc.innerHTML = `
      <span class="text-zinc-500">${isZh() ? '聚焦' : 'Focus'}:</span>
      <span class="font-bold" style="color:${NODE_COLOR[node.type] || '#e4e4e7'}">${escapeHtml(node.label)}</span>
      <span class="text-zinc-600">· ${focusDepth} hop</span>
      <button id="ng-exit-focus" class="ml-2 px-1.5 rounded border border-zinc-600/50 hover:border-rose-400 hover:text-rose-400">✕ ${isZh() ? '返回全景' : 'Back'}</button>`;
    bc.querySelector('#ng-exit-focus').addEventListener('click', exitFocus);
  }

  // ─── controls ────────────────────────────────────────────────────────────
  function renderControls() {
    // Edge-type chips (clickable toggles)
    const present = new Set(FULL.links.map(l => l.type));
    const host = document.getElementById('ng-edge-chips');
    host.innerHTML = Object.entries(EDGE_STYLE)
      .filter(([k]) => present.has(k))
      .map(([k, st]) => `
        <button class="ng-edge-chip" data-edge-type="${k}" style="--chip:${st.hover}">
          ${isZh() ? st.zh : st.en}</button>`).join('');
    host.querySelectorAll('[data-edge-type]').forEach(btn => {
      btn.addEventListener('click', () => {
        const k = btn.dataset.edgeType;
        if (visibleEdgeTypes.has(k)) { visibleEdgeTypes.delete(k); btn.classList.add('off'); }
        else { visibleEdgeTypes.add(k); btn.classList.remove('off'); }
        refreshView();
      });
    });

    // Search with datalist autocomplete
    const dl = document.getElementById('ng-search-list');
    dl.innerHTML = FULL.nodes.map(n => `<option value="${escapeHtml(n.label)}"></option>`).join('');
    const search = document.getElementById('ng-search');
    const trySearch = () => {
      const q = (search.value || '').trim().toLowerCase();
      if (!q) return;
      const match = FULL.nodes.find(n => (n.label || '').toLowerCase() === q)
        || FULL.nodes.find(n => (n.label || '').toLowerCase().includes(q));
      if (match) { enterFocus(match); search.blur(); }
    };
    search.addEventListener('change', trySearch);
    search.addEventListener('keydown', e => { if (e.key === 'Enter') trySearch(); });

    // Edge weight threshold
    const wt = document.getElementById('ng-weight');
    const wtOut = document.getElementById('ng-weight-readout');
    wt.addEventListener('input', e => {
      minWeight = parseFloat(e.target.value);
      wtOut.textContent = '≥ ' + minWeight.toFixed(1);
      refreshView();
    });

    // Focus depth
    document.querySelectorAll('[data-focus-depth]').forEach(btn => {
      btn.addEventListener('click', () => {
        focusDepth = parseInt(btn.dataset.focusDepth, 10);
        document.querySelectorAll('[data-focus-depth]').forEach(b =>
          b.classList.toggle('active', b === btn));
        if (focusRoot) refreshView({ fit: true });
      });
    });

    document.getElementById('ng-zoom-fit').addEventListener('click', () => {
      if (GraphInst) GraphInst.zoomToFit(400, 70);
    });
    document.getElementById('ng-reset').addEventListener('click', () => {
      exitFocus();
      minWeight = 0; wt.value = 0; wtOut.textContent = '≥ 0.0';
      visibleEdgeTypes = new Set(Object.keys(EDGE_STYLE));
      host.querySelectorAll('.ng-edge-chip').forEach(b => b.classList.remove('off'));
      refreshView({ fit: true });
    });

    const toggleBtn = document.getElementById('ng-side-toggle');
    const panel = document.getElementById('ng-side-panel');
    toggleBtn.addEventListener('click', () => {
      const collapsed = panel.style.transform === 'translateX(-110%)';
      panel.style.transform = collapsed ? 'translateX(0)' : 'translateX(-110%)';
    });

    document.addEventListener('keydown', e => { if (e.key === 'Escape') exitFocus(); });
  }

  // ─── sizing / painting ───────────────────────────────────────────────────
  function nodeR(n) {
    if (n.type === 'theme') return 4 + Math.min((n.members || 2) * 0.55, 8);
    const sig = Math.max(n.weight || 0, (n.pagerank || 0) * 4);
    return 2.2 + Math.min(sig * 22, 7);
  }

  function nodeFill(n) {
    if (hoverNode) {
      if (n.id === hoverNode.id) return '#ffffff';
      if (hoverNbrs && hoverNbrs.has(n.id)) return NODE_COLOR[n.type] || '#a1a1aa';
      return DIM_NODE;
    }
    return NODE_COLOR[n.type] || '#a1a1aa';
  }

  function linkColor(l) {
    const st = EDGE_STYLE[l.type] || { color: 'rgba(120,120,120,0.2)', hover: 'rgba(200,200,200,0.8)' };
    if (hoverNode) {
      const s = endId(l.source), t = endId(l.target);
      if (s === hoverNode.id || t === hoverNode.id) return st.hover;
      return DIM_LINK;
    }
    return st.color;
  }

  function linkWidth(l) {
    if (hoverNode) {
      const s = endId(l.source), t = endId(l.target);
      if (s === hoverNode.id || t === hoverNode.id) return l.type === 'MEMBER_OF' ? 1.2 : 1.8;
    }
    return l.type === 'MEMBER_OF' ? 0.6 : 1.1;
  }

  // Single cheap painter: circle + conditional label. No gradients, no shadows,
  // no per-frame composite switches — zoom/pan stays a pure transform.
  function paintNode(n, ctx, scale) {
    const r = nodeR(n);
    ctx.beginPath();
    ctx.arc(n.x, n.y, r, 0, Math.PI * 2);
    ctx.fillStyle = nodeFill(n);
    ctx.fill();
    if (n.type === 'theme') {
      ctx.strokeStyle = 'rgba(251,191,36,0.55)';
      ctx.lineWidth = 1 / scale;
      ctx.stroke();
    }

    // Labels — theme hubs are landmarks: constant *screen-size* font (divide by
    // zoom scale) so they stay readable at any zoom. Ticker labels appear on
    // hover/focus (screen-size) or when zoomed in (canvas-size fade-in).
    const screenFont = px => Math.max(2.5, Math.min(px / scale, 26));
    let show = false, alpha = 1, fontPx = 3.5;
    if (n.type === 'theme') {
      show = true; fontPx = screenFont(10 + Math.min((n.members || 2) * 0.25, 3));
    } else if (hoverNode && (n.id === hoverNode.id || (hoverNbrs && hoverNbrs.has(n.id)))) {
      show = true; fontPx = screenFont(10);
    } else if (focusRoot) {
      show = true; fontPx = screenFont(9);
    } else if (scale >= 1.4) {
      show = true; alpha = Math.min((scale - 1.4) * 1.2, 0.9); fontPx = 3.2;
    } else if ((n.weight || 0) >= 0.05) {
      show = true; alpha = 0.85; fontPx = screenFont(8);
    }
    if (!show || (hoverNode && nodeFill(n) === DIM_NODE)) return;

    const label = n.label || '';
    if (!label) return;
    ctx.font = `600 ${fontPx}px Inter, sans-serif`;
    ctx.textAlign = 'center';
    ctx.textBaseline = 'top';
    const prev = ctx.globalAlpha;
    ctx.globalAlpha = alpha;
    ctx.fillStyle = 'rgba(5,6,9,0.8)';
    ctx.fillText(label, n.x + 0.4 / scale, n.y + r + 1 + 0.4 / scale);
    ctx.fillStyle = n.type === 'theme' ? '#fcd34d' : '#d4d4d8';
    ctx.fillText(label, n.x, n.y + r + 1);
    ctx.globalAlpha = prev;
  }

  // ─── tooltip (hover) — news rollup kept from V3.1 ───────────────────────
  function buildNodeTooltip(n) {
    if (!n) return '';
    const t = (zh, en) => isZh() ? zh : en;
    const wrap = inner =>
      `<div style="font-family:system-ui,sans-serif;padding:8px 10px;max-width:360px;background:rgba(15,15,17,0.96);border:1px solid rgba(161,161,170,0.35);border-radius:8px;box-shadow:0 6px 22px rgba(0,0,0,0.45);color:#e4e4e7;">${inner}</div>`;

    if (n.type === 'theme') {
      return wrap(`
        <div style="font-weight:700;font-size:12px;color:#fbbf24;">${escapeHtml(n.label)}</div>
        <div style="font-size:10px;color:#a1a1aa;margin-top:2px;">${t('主題 hub', 'Theme hub')} · ${n.members || 0} ${t('檔成員', 'members')} · ${t('點擊看成員星系', 'click to focus members')}</div>`);
    }
    if (n.type !== 'ticker') {
      return wrap(`<div style="font-weight:700;font-size:12px;">${escapeHtml(n.label)}</div>
        <div style="font-size:10px;color:#a1a1aa;margin-top:2px;">type=${n.type}</div>`);
    }

    const md = n.metadata || {};
    const themes = (md.themes || []).slice(0, 4);
    const news = (md.recent_news || []).slice(0, 5);
    const vc = v => {
      const k = String(v || '').toUpperCase();
      return k.includes('BULL') ? '#22c55e' : k.includes('BEAR') ? '#ef4444' : '#a1a1aa';
    };
    const themeChips = themes.length
      ? `<div style="margin-top:6px;display:flex;gap:4px;flex-wrap:wrap;">${themes.map(x =>
          `<span style="background:rgba(251,191,36,0.15);color:#fbbf24;border:1px solid rgba(251,191,36,0.35);border-radius:4px;padding:1px 6px;font-size:10px;font-weight:600;">${escapeHtml(x)}</span>`).join('')}</div>` : '';
    const newsRows = news.length ? news.map(e => {
      const col = vc(e.verdict);
      const imp = e.net_impact != null ? `<span style="color:${col};font-family:monospace;font-size:10px;">${e.net_impact >= 0 ? '+' : ''}${Number(e.net_impact).toFixed(1)}</span>` : '';
      const pub = e.published ? `<span style="color:#71717a;font-size:9px;">${escapeHtml(String(e.published).slice(0, 10))}</span>` : '';
      return `<div style="padding:5px 0;border-top:1px solid rgba(255,255,255,0.06);font-size:11px;line-height:1.35;">
        <div style="display:flex;justify-content:space-between;gap:8px;align-items:baseline;">
          <div style="flex:1;color:#e4e4e7;">${escapeHtml(e.headline || '')}</div>
          <div style="flex-shrink:0;display:flex;gap:6px;align-items:baseline;">${imp}</div>
        </div>${pub ? `<div style="margin-top:2px;">${pub}</div>` : ''}</div>`;
    }).join('') : `<div style="margin-top:4px;font-size:11px;color:#71717a;">${t('近期無相關新聞', 'No recent news')}</div>`;

    return wrap(`
      <div style="display:flex;align-items:baseline;gap:8px;justify-content:space-between;">
        <div style="font-weight:800;font-size:14px;">${escapeHtml(n.label)}</div>
        <div style="font-size:9px;color:#a1a1aa;font-family:monospace;">pr=${(n.pagerank || 0).toFixed(2)} · ${n.mentions || 0} ${t('則提及', 'mentions')}</div>
      </div>
      ${themeChips}
      <div style="margin-top:8px;font-size:9px;font-weight:700;letter-spacing:0.08em;color:#a1a1aa;text-transform:uppercase;">${t('近期新聞', 'Recent News')}</div>
      ${newsRows}`);
  }

  // ─── mount ───────────────────────────────────────────────────────────────
  function mountGraph() {
    const host = document.getElementById('graph-host');
    if (!host || typeof ForceGraph !== 'function') {
      throw new Error('graph host or ForceGraph CDN missing');
    }
    const rect = host.getBoundingClientRect();
    const W = Math.max(rect.width || 0, window.innerWidth - 256, 800);
    const H = Math.max(rect.height || 0, window.innerHeight - 64, 600);

    // User interaction kills all future auto-fit — fixes "zoom 被搶走".
    host.addEventListener('wheel', () => { userInteracted = true; }, { passive: true });
    host.addEventListener('pointerdown', () => { userInteracted = true; });

    GraphInst = ForceGraph()(host)
      .width(W).height(H)
      .graphData(currentView())
      .backgroundColor('rgba(0,0,0,0)')
      .minZoom(0.05).maxZoom(14)
      .nodeId('id')
      .nodeRelSize(1)
      .nodeVal(n => nodeR(n) * nodeR(n))
      .nodeLabel(n => buildNodeTooltip(n))
      .nodeCanvasObjectMode(() => 'replace')
      .nodeCanvasObject(paintNode)
      .linkColor(linkColor)
      .linkWidth(linkWidth)
      .enableNodeDrag(true)
      .onNodeHover(n => {
        if (hoverNode === n) return;
        hoverNode = n;
        hoverNbrs = n ? new Set((ADJ.get(n.id) || []).map(x => x.to)) : null;
        document.body.style.cursor = n ? 'pointer' : 'default';
      })
      .onNodeClick(n => enterFocus(n))
      .onBackgroundClick(() => exitFocus())
      .warmupTicks(120)
      .cooldownTicks(90)
      .d3VelocityDecay(0.38)
      .d3AlphaDecay(0.028)
      .onEngineStop(() => {
        // One initial fit only; never after the user has touched the canvas.
        if (!didInitialFit && !userInteracted) {
          didInitialFit = true;
          GraphInst.zoomToFit(600, 80);
        }
      });

    // Force tuning: MEMBER_OF spokes short (tight theme galaxies), structural
    // edges long (bridges between galaxies stay readable).
    try {
      const linkF = GraphInst.d3Force('link');
      if (linkF && linkF.distance) {
        linkF.distance(l => l.type === 'MEMBER_OF' ? 26 : 90).strength(l => l.type === 'MEMBER_OF' ? 0.5 : 0.25);
      }
      const chargeF = GraphInst.d3Force('charge');
      if (chargeF && chargeF.strength) chargeF.strength(n => n.type === 'theme' ? -240 : -60);
    } catch (e) { /* defaults are fine */ }

    const resize = () => {
      const r = host.getBoundingClientRect();
      GraphInst.width(Math.max(r.width || 0, window.innerWidth - 256))
               .height(Math.max(r.height || 0, window.innerHeight - 64));
    };
    window.addEventListener('resize', resize);
    setTimeout(resize, 60);
  }

  // ─── detail panel ────────────────────────────────────────────────────────
  function renderDetailPanel(n) {
    const panel = document.getElementById('ng-detail');
    panel.classList.remove('hidden');
    const t = (zh, en) => isZh() ? zh : en;

    const neighbors = (ADJ.get(n.id) || [])
      .filter(({ link }) => passesEdgeFilter(link))
      .map(({ to, link }) => ({ node: NODE_INDEX.get(to), link }))
      .filter(x => x.node)
      .sort((a, b) => (b.link.weight || 0) - (a.link.weight || 0))
      .slice(0, 14);

    const md = n.metadata || {};
    const themes = (md.themes || []).slice(0, 6);
    const news = (md.recent_news || []).slice(0, 5);
    const vc = v => {
      const k = String(v || '').toUpperCase();
      return k.includes('BULL') ? '#22c55e' : k.includes('BEAR') ? '#ef4444' : '#a1a1aa';
    };

    panel.innerHTML = `
      <div class="flex items-start justify-between">
        <div>
          <div class="ng-chip" data-type="${n.type}">${n.type === 'theme' ? t('主題', 'theme') : n.type}</div>
          <h3 class="font-bold text-base mt-1" style="color:var(--text-main)">${escapeHtml(n.label)}</h3>
        </div>
        <button id="ng-close" class="text-zinc-500 hover:text-rose-500 text-xs">✕</button>
      </div>

      ${n.type === 'ticker' ? `
      <div class="grid grid-cols-3 gap-2 text-center text-[10px]">
        <div><div class="ng-stat-num text-lg">${(n.pagerank || 0).toFixed(3)}</div><div class="text-zinc-500">pagerank</div></div>
        <div><div class="ng-stat-num text-lg">${n.mentions || 0}</div><div class="text-zinc-500">${t('提及', 'mentions')}</div></div>
        <div><div class="ng-stat-num text-lg">${neighbors.length}</div><div class="text-zinc-500">${t('連結', 'links')}</div></div>
      </div>
      <div class="text-[10px] text-zinc-500">${t('最後出現', 'last seen')}: ${n.last_seen || '—'}</div>` : `
      <div class="text-[10px] text-zinc-500">${n.members || 0} ${t('檔成員', 'member tickers')}</div>`}

      ${themes.length ? `
      <div>
        <h4 class="text-[10px] font-black uppercase tracking-widest text-zinc-500 mb-1">${t('主題', 'Themes')}</h4>
        <div class="flex flex-wrap gap-1">
          ${themes.map(x => `<span class="ng-theme-chip" data-jump-theme="${escapeHtml(slugTheme(x))}">${escapeHtml(x)}</span>`).join('')}
        </div>
      </div>` : ''}

      ${news.length ? `
      <div>
        <h4 class="text-[10px] font-black uppercase tracking-widest text-zinc-500 mb-1">${t('近期新聞', 'Recent News')}</h4>
        <div class="space-y-1">
          ${news.map(e => `<div class="text-[11px] leading-snug border-l-2 pl-2" style="border-color:${vc(e.verdict)};">
            <div>${escapeHtml(e.headline || '')}</div>
            <div class="flex gap-2 mt-0.5 items-baseline">
              ${e.net_impact != null ? `<span style="color:${vc(e.verdict)};font-family:monospace;font-size:10px;">${e.net_impact >= 0 ? '+' : ''}${Number(e.net_impact).toFixed(1)}</span>` : ''}
              ${e.published ? `<span class="text-zinc-500 text-[9px]">${escapeHtml(String(e.published).slice(0, 10))}</span>` : ''}
            </div></div>`).join('')}
        </div>
      </div>` : ''}

      <div>
        <h4 class="text-[10px] font-black uppercase tracking-widest text-zinc-500 mb-1">${t('關聯', 'Connections')}</h4>
        <div class="space-y-0.5">
          ${neighbors.map(x => {
            const st = EDGE_STYLE[x.link.type] || {};
            return `<div class="ng-neighbor-row" data-jump-id="${x.node.id}">
              <span><span class="ng-chip" data-type="${x.node.type}">${x.node.type[0]}</span>
                <span class="label ml-1">${escapeHtml(x.node.label)}</span></span>
              <span class="weight" style="color:${st.hover || '#71717a'}">${isZh() ? (st.zh || x.link.type) : (st.en || x.link.type)}</span>
            </div>`;
          }).join('') || `<div class="text-[10px] text-zinc-600">${t('目前篩選下無關聯', 'No connections under current filters')}</div>`}
        </div>
      </div>`;

    panel.querySelector('#ng-close').addEventListener('click', exitFocus);
    panel.querySelectorAll('[data-jump-id]').forEach(row =>
      row.addEventListener('click', () => {
        const tn = NODE_INDEX.get(row.getAttribute('data-jump-id'));
        if (tn) enterFocus(tn);
      }));
    panel.querySelectorAll('[data-jump-theme]').forEach(chip =>
      chip.addEventListener('click', () => {
        const tn = NODE_INDEX.get(chip.getAttribute('data-jump-theme'));
        if (tn) enterFocus(tn);
      }));
  }

  // ─── misc ────────────────────────────────────────────────────────────────
  function updateMetaLine() {
    const el = document.getElementById('ng-meta-line');
    const tickers = FULL.nodes.filter(n => n.type === 'ticker').length;
    const themes = FULL.nodes.filter(n => n.type === 'theme').length;
    el.textContent = `${tickers} tickers · ${themes} themes · ${FULL.links.length} edges · gen ${RAW.generated_at?.slice(0, 10) || '—'}`;
  }

  function escapeHtml(s) {
    if (s == null) return '';
    return String(s).replace(/[&<>"']/g, c => ({
      '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
    }[c]));
  }

  function hideStatus() {
    const s = document.getElementById('ng-status');
    if (s) s.style.display = 'none';
  }

  function showStatusError(err) {
    const s = document.getElementById('ng-status');
    if (s) s.innerHTML = `
      <div class="text-center text-rose-400">
        <i data-lucide="circle-alert" class="w-8 h-8 mx-auto opacity-70"></i>
        <div class="mt-2 font-bold">無法載入 Nexus 圖譜</div>
        <div class="text-[10px] mt-1 font-mono">${escapeHtml(err && err.message || String(err))}</div>
        <div class="text-[10px] mt-2 text-zinc-500">請先執行 <code>python3 scripts/nexus/build_graph.py --tier 1,2 --full</code></div>
      </div>`;
    if (window.lucide && lucide.createIcons) lucide.createIcons();
  }
})();
