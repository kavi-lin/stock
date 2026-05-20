/**
 * page-graph.js — Project Nexus V3.0 Knowledge Graph
 *
 * - Loads Dashboard/nexus_graph.json (or /api/graph/data)
 * - Renders Obsidian-style force-directed graph via force-graph@1.43
 * - Monochrome by default, size by degree centrality, glow on hover
 * - Click ticker → BFS 3-hop path tracing (1st/2nd/3rd order beneficiaries)
 */
(function () {
  'use strict';

  // V3.1.0 — graph is ticker-only by default (build_graph.py `ticker_centric: true`).
  // Other node types remain enumerated here so a legacy non-ticker-centric build
  // (e.g. dry-run dump for Tier 3 debugging) still renders if loaded manually.
  const NODE_TYPES = ['ticker', 'theme', 'catalyst', 'sector', 'narrative', 'thesis'];
  const TYPE_COLOR = {
    ticker:    'rgba(147,197,253,0.85)',   // sky blue   — 個股
    theme:     'rgba(251,191,36,0.85)',    // amber
    catalyst:  'rgba(248,113,113,0.85)',   // rose
    sector:    'rgba(167,139,250,0.85)',   // violet
    narrative: 'rgba(52,211,153,0.85)',    // emerald
    thesis:    'rgba(244,114,182,0.85)',   // pink
  };
  // Edge palette for ticker-centric mode — distinguishes direct supply-chain
  // / peer relations from synthesized co-theme relations.
  const EDGE_COLOR = {
    PEER_OF:          'rgba(147,197,253,0.55)',
    SUPPLIES_TO:      'rgba(34,197,94,0.65)',
    CUSTOMER_OF:      'rgba(34,197,94,0.45)',
    CONTRACT_MFG_FOR: 'rgba(168,85,247,0.55)',
    COMPETES_WITH:    'rgba(239,68,68,0.55)',
    CO_DEVELOPS_WITH: 'rgba(245,158,11,0.55)',
    SUPPLY_CHAIN_HOP: 'rgba(34,197,94,0.45)',
    CO_THEME:         'rgba(251,191,36,0.22)',   // dim — synthetic via shared theme
  };
  const TYPE_COLOR_PROVISIONAL = 'rgba(245,158,11,0.6)';   // amber-orange — pending promotion
  const COLOR_DIM = 'rgba(115,115,115,0.06)';

  // ─── Thermographic palette ──────────────────────────────────────────────
  // Click = incandescent ignition. Heat radiates outward: white → gold → crimson.
  // Each hop has core/rim/glow colors used for canvas fill, stroke, radial-gradient bloom.
  const HEAT_PALETTE = {
    0: { core: '#ffffff', rim: '#fff7cc', glow: 'rgba(255,247,204,0.65)', edgeOut: 'rgba(254,243,199,0.92)' },
    1: { core: '#fbbf24', rim: '#f97316', glow: 'rgba(251,146,60,0.55)',  edgeOut: 'rgba(249,115,22,0.72)' },
    2: { core: '#ef4444', rim: '#991b1b', glow: 'rgba(220,38,38,0.40)',   edgeOut: 'rgba(220,38,38,0.55)'  },
    3: { core: '#7f1d1d', rim: '#450a0a', glow: 'rgba(127,29,29,0.30)',   edgeOut: 'rgba(127,29,29,0.40)'  },
  };
  function heat(hop) {
    return HEAT_PALETTE[Math.min(hop, 3)] || HEAT_PALETTE[3];
  }

  let GRAPH_DATA = null;          // raw nexus_graph.json
  let RENDERED = null;            // force-graph instance
  let NODE_INDEX = new Map();     // id -> node ref
  let ADJ = new Map();            // id -> [{to, edge}]
  let visibleTypes = new Set(NODE_TYPES);
  let showProvisional = false;
  let decayMult = 1.0;
  let hoveredNode = null;
  let hoverNeighbors = null;      // Set(id) of nodes linked to hoveredNode
  let activeNode = null;
  let pathHops = null;            // Map(id -> hop_distance) when active path-trace
  let pathSpine = null;            // Set("src|tgt") of edges along BFS spine — only these glow
  let pathEdgeHop = null;          // Map("src|tgt" -> hop_depth_of_target_node)
  let clickIgnitionT = 0;          // performance.now() timestamp of last click; drives ignition wave
  let ignitionRafId = 0;

  const PATH_MAX_HOPS = 2;        // BFS depth on click (was 3 — too noisy)
  const IGNITION_MS = 1100;       // shockwave + bloom animation duration

  // ─── init ────────────────────────────────────────────────────────────────
  document.addEventListener('DOMContentLoaded', async () => {
    if (window.UI && UI.initTheme) UI.initTheme();
    if (window.UI && UI.renderSidebar) UI.renderSidebar('graph');
    if (window.lucide && lucide.createIcons) lucide.createIcons();

    renderFilters();
    bindControls();

    try {
      await loadGraph();
      buildIndices();
      // Re-render filter row now that GRAPH_DATA is loaded — switches to edge
      // legend if the build is ticker-centric.
      renderFilters();
      bindControls();
      mountGraph();
      updateMetaLine();
      hideStatus();
    } catch (err) {
      showStatusError(err);
    }
  });

  // V3.1.0 — ticker tooltip. News rolled up at build time into ticker.metadata
  // (recent_news[], themes[], narratives[], sector). Reads only that; no extra
  // network calls. Wider than the legacy 1-line title so the news block fits.
  function buildNodeTooltip(n) {
    if (!n) return '';
    const md = n.metadata || {};
    const isZh = !!(window.UI && window.UI.currentLang === 'zh');
    const t = (zh, en) => isZh ? zh : en;
    const verdictColor = (v) => {
      const k = String(v || '').toUpperCase();
      if (k.includes('BULL')) return '#22c55e';
      if (k.includes('BEAR')) return '#ef4444';
      return '#a1a1aa';
    };
    const escapeAttr = s => escapeHtml(String(s == null ? '' : s));
    const wrap = (inner) =>
      `<div style="font-family:system-ui,sans-serif;padding:8px 10px;max-width:360px;background:rgba(15,15,17,0.96);border:1px solid rgba(161,161,170,0.35);border-radius:8px;box-shadow:0 6px 22px rgba(0,0,0,0.45);color:#e4e4e7;">${inner}</div>`;

    // Non-ticker fallback (only present if a legacy non-ticker-centric build
    // is loaded). Compact single-line.
    if (n.type !== 'ticker') {
      return wrap(`
        <div style="font-weight:700;font-size:12px;">${escapeAttr(n.label)}</div>
        <div style="font-size:10px;color:#a1a1aa;margin-top:2px;">
          type=${n.type} · deg=${(n.weight||0).toFixed(2)} · pr=${(n.pagerank||0).toFixed(2)}
        </div>
      `);
    }

    const themes = (md.themes || []).slice(0, 5);
    const narratives = (md.narratives || []).slice(0, 5);
    const news = (md.recent_news || []).slice(0, 6);
    const sector = md.sector;

    const themesChips = themes.length
      ? `<div style="margin-top:6px;display:flex;gap:4px;flex-wrap:wrap;">
          ${themes.map(x => `<span style="background:rgba(251,191,36,0.15);color:#fbbf24;border:1px solid rgba(251,191,36,0.35);border-radius:4px;padding:1px 6px;font-size:10px;font-weight:600;">${escapeAttr(x)}</span>`).join('')}
        </div>` : '';
    const narrativesChips = narratives.length
      ? `<div style="margin-top:4px;display:flex;gap:4px;flex-wrap:wrap;">
          ${narratives.map(x => `<span style="background:rgba(52,211,153,0.12);color:#34d399;border:1px solid rgba(52,211,153,0.30);border-radius:4px;padding:1px 6px;font-size:10px;">${escapeAttr(x)}</span>`).join('')}
        </div>` : '';

    const newsRows = news.length
      ? news.map(e => {
          const col = verdictColor(e.verdict);
          const v   = e.verdict ? `<span style="color:${col};font-weight:700;font-size:9px;letter-spacing:0.04em;">${escapeAttr(String(e.verdict).toUpperCase().slice(0,8))}</span>` : '';
          const imp = (e.net_impact != null)
            ? `<span style="color:${col};font-family:monospace;font-size:10px;">${e.net_impact >= 0 ? '+' : ''}${Number(e.net_impact).toFixed(1)}</span>` : '';
          const pub = e.published ? `<span style="color:#71717a;font-size:9px;">${escapeAttr(String(e.published).slice(0,10))}</span>` : '';
          return `<div style="padding:5px 0;border-top:1px solid rgba(255,255,255,0.06);font-size:11px;line-height:1.35;">
            <div style="display:flex;justify-content:space-between;gap:8px;align-items:baseline;">
              <div style="flex:1;color:#e4e4e7;">${escapeAttr(e.headline || '')}</div>
              <div style="flex-shrink:0;display:flex;gap:6px;align-items:baseline;">${v}${imp}</div>
            </div>
            ${pub ? `<div style="margin-top:2px;">${pub}</div>` : ''}
          </div>`;
        }).join('')
      : `<div style="margin-top:4px;font-size:11px;color:#71717a;">${t('近期無相關新聞', 'No recent news')}</div>`;

    return wrap(`
      <div style="display:flex;align-items:baseline;gap:8px;justify-content:space-between;">
        <div style="font-weight:800;font-size:14px;letter-spacing:0.02em;">${escapeAttr(n.label)}</div>
        <div style="font-size:9px;color:#a1a1aa;font-family:monospace;">
          deg=${(n.weight||0).toFixed(2)} · pr=${(n.pagerank||0).toFixed(2)}
        </div>
      </div>
      ${sector ? `<div style="margin-top:3px;font-size:10px;color:#a78bfa;">${escapeAttr(sector)}</div>` : ''}
      ${themesChips}
      ${narrativesChips}
      <div style="margin-top:8px;font-size:9px;font-weight:700;letter-spacing:0.08em;color:#a1a1aa;text-transform:uppercase;">
        ${t('近期新聞', 'Recent News')} ${news.length ? `(${news.length})` : ''}
      </div>
      ${newsRows}
    `);
  }

  async function loadGraph() {
    const url = 'nexus_graph.json?t=' + Date.now();
    const r = await fetch(url, { cache: 'no-store' });
    if (!r.ok) throw new Error('HTTP ' + r.status);
    GRAPH_DATA = await r.json();
  }

  function buildIndices() {
    NODE_INDEX = new Map();
    ADJ = new Map();
    (GRAPH_DATA.nodes || []).forEach(n => NODE_INDEX.set(n.id, n));
    (GRAPH_DATA.edges || []).forEach(e => {
      if (!ADJ.has(e.source)) ADJ.set(e.source, []);
      if (!ADJ.has(e.target)) ADJ.set(e.target, []);
      ADJ.get(e.source).push({ to: e.target, edge: e });
      ADJ.get(e.target).push({ to: e.source, edge: e });
    });
  }

  // ─── controls ────────────────────────────────────────────────────────────
  function renderFilters() {
    const host = document.getElementById('ng-filter-types');
    // V3.1.0 — ticker-centric. Only render type filters for kinds that actually
    // exist in the current graph; legacy multi-type filters are hidden when the
    // graph is collapsed to ticker-only. Edge-type legend replaces the chip row
    // so users can tell PEER_OF from CO_THEME at a glance.
    const presentTypes = GRAPH_DATA && GRAPH_DATA.nodes
      ? Array.from(new Set(GRAPH_DATA.nodes.map(n => n.type)))
      : NODE_TYPES.slice();
    if (presentTypes.length <= 1 && presentTypes[0] === 'ticker') {
      // Pure ticker graph — show edge-type legend instead of pointless type checkboxes.
      const edgeLegend = [
        ['PEER_OF',          isLangZh() ? '同業' : 'Peer'],
        ['SUPPLIES_TO',      isLangZh() ? '供應' : 'Supplies'],
        ['CUSTOMER_OF',      isLangZh() ? '客戶' : 'Customer'],
        ['COMPETES_WITH',    isLangZh() ? '競爭' : 'Competes'],
        ['CO_DEVELOPS_WITH', isLangZh() ? '合作' : 'Co-dev'],
        ['CO_THEME',         isLangZh() ? '同主題' : 'Co-theme'],
      ];
      host.innerHTML = edgeLegend.map(([k, label]) => {
        const col = EDGE_COLOR[k] || 'rgba(160,160,160,0.6)';
        return `<span class="ng-chip" style="border-color:${col};color:${col}" title="${k}">${label}</span>`;
      }).join(' ');
      // No checkbox to bind; visibleTypes already contains 'ticker' from init.
      return;
    }
    host.innerHTML = presentTypes.map(t =>
      `<label><span class="ng-chip" data-type="${t}">${t}</span>
        <input type="checkbox" data-filter-type="${t}" /></label>`
    ).join('');
    host.querySelectorAll('input[type=checkbox]').forEach(el => { el.checked = true; });
  }

  function isLangZh() {
    return !!(window.UI && window.UI.currentLang === 'zh');
  }

  function bindControls() {
    document.querySelectorAll('input[data-filter-type]').forEach(el => {
      el.addEventListener('change', () => {
        const t = el.getAttribute('data-filter-type');
        if (el.checked) visibleTypes.add(t);
        else visibleTypes.delete(t);
        applyFiltersAndRedraw();
      });
    });

    document.getElementById('ng-show-provisional').addEventListener('change', e => {
      showProvisional = e.target.checked;
      applyFiltersAndRedraw();
    });

    const decay = document.getElementById('ng-decay');
    const decayReadout = document.getElementById('ng-decay-readout');
    decay.addEventListener('input', e => {
      decayMult = parseFloat(e.target.value);
      decayReadout.textContent = '×' + decayMult.toFixed(1);
      applyFiltersAndRedraw();
    });

    const search = document.getElementById('ng-search');
    search.addEventListener('input', e => {
      const q = (e.target.value || '').trim().toLowerCase();
      if (!q || !RENDERED) return;
      const match = (GRAPH_DATA.nodes || []).find(n =>
        (n.label || '').toLowerCase().includes(q) || (n.id || '').toLowerCase().includes(q)
      );
      if (match) {
        RENDERED.centerAt(match.x, match.y, 600);
        RENDERED.zoom(2.6, 600);
        hoveredNode = match;
        hoverNeighbors = new Set();
        for (const { to } of (ADJ.get(match.id) || [])) hoverNeighbors.add(to);
        scheduleRefresh();
        setTimeout(() => { hoveredNode = null; hoverNeighbors = null; scheduleRefresh(); }, 1200);
      }
    });

    const toggleBtn = document.getElementById('ng-side-toggle');
    const panel = document.getElementById('ng-side-panel');
    toggleBtn.addEventListener('click', () => {
      const collapsed = panel.style.transform === 'translateX(-110%)';
      panel.style.transform = collapsed ? 'translateX(0)' : 'translateX(-110%)';
    });

    document.getElementById('ng-zoom-fit').addEventListener('click', () => {
      if (RENDERED) RENDERED.zoomToFit(400, 60);
    });
    document.getElementById('ng-reset').addEventListener('click', () => {
      pathHops = null;
      pathSpine = null;
      pathEdgeHop = null;
      hoveredNode = null;
      hoverNeighbors = null;
      activeNode = null;
      stopIgnitionLoop();
      document.body.classList.remove('ng-thermal');
      document.getElementById('ng-detail').classList.add('hidden');
      if (RENDERED) {
        RENDERED.zoomToFit(400, 60);
        RENDERED.refresh();
      }
    });
  }

  // ─── render ──────────────────────────────────────────────────────────────
  function baseColor(n) {
    if (n.status === 'provisional') return TYPE_COLOR_PROVISIONAL;
    return TYPE_COLOR[n.type] || 'rgba(161,161,170,0.55)';
  }

  function nodeColor(n) {
    // Built-in fallback renderer color. The thermographic decoration in
    // nodeCanvasObject overrides this for active path nodes, so this only
    // affects (a) idle nodes, (b) non-path nodes during path-trace.
    if (pathHops) {
      if (!pathHops.has(n.id)) return COLOR_DIM;
      return heat(pathHops.get(n.id)).core;
    }
    if (hoveredNode) {
      if (n.id === hoveredNode.id) return '#ffffff';
      if (hoverNeighbors && hoverNeighbors.has(n.id)) return baseColor(n);
      return COLOR_DIM;
    }
    return baseColor(n);
  }

  function spineHop(sId, tId) {
    if (!pathEdgeHop) return 0;
    return pathEdgeHop.get(sId + '|' + tId) || pathEdgeHop.get(tId + '|' + sId) || 0;
  }

  function linkColor(l) {
    const sId = edgeEnd(l.source);
    const tId = edgeEnd(l.target);
    if (pathSpine) {
      const hop = spineHop(sId, tId);
      if (hop > 0) return heat(hop).edgeOut;
      return 'rgba(0,0,0,0)';
    }
    if (hoveredNode) {
      if (sId === hoveredNode.id || tId === hoveredNode.id) {
        // Hover edges colored by edge type so the relation kind is visible at
        // first glance (peer / supply / co-theme).
        return EDGE_COLOR[l.type] || 'rgba(254,243,199,0.55)';
      }
      return 'rgba(0,0,0,0)';
    }
    // Idle state: keep edges subtly visible at low alpha so the topology shows
    // even without hover. CO_THEME is dimmest (synthetic).
    const base = EDGE_COLOR[l.type] || 'rgba(120,120,120,0.18)';
    return base.replace(/[\d.]+\)$/, m => (parseFloat(m) * 0.35).toFixed(2) + ')');
  }

  function linkWidth(l) {
    const sId = edgeEnd(l.source);
    const tId = edgeEnd(l.target);
    if (pathSpine) {
      const hop = spineHop(sId, tId);
      if (hop === 1) return 1.8;
      if (hop === 2) return 1.1;
      if (hop > 0) return 0.7;
      return 0;
    }
    if (hoveredNode && (sId === hoveredNode.id || tId === hoveredNode.id)) {
      return 1.1;
    }
    return 0;
  }

  function nodeSize(n) {
    // Dampened power scale — smaller overall, hub still visible but not dominating.
    const sig = Math.max(n.weight || 0, (n.pagerank || 0) * 5, 0.001);
    return Math.pow(sig * 80, 1.2) + 0.4;
  }

  function nodeRadius(n) {
    // Mirror force-graph's internal radius derivation: area = val * relSize,
    // r = sqrt(area / π). We use nodeRelSize(3) below.
    return Math.sqrt(nodeSize(n) * 3 / Math.PI);
  }

  // ─── Thermographic node painter ─────────────────────────────────────────
  // For each path-trace node, paint a hop-tinted radial-bloom + filled core.
  // Root additionally renders concentric spotlight rings AND the ignition
  // shockwave that animates outward for ~1.1s after click.
  function paintThermographicNode(n, ctx, scale) {
    if (!pathHops || !pathHops.has(n.id)) return;
    const hop = pathHops.get(n.id);
    const palette = heat(hop);
    const baseR = Math.max(nodeRadius(n), 1.2);
    const haloR = baseR * (hop === 0 ? 7.5 : hop === 1 ? 4.2 : 3.0);

    // Radial bloom (warm haze behind node)
    const grad = ctx.createRadialGradient(n.x, n.y, baseR * 0.6, n.x, n.y, haloR);
    grad.addColorStop(0, palette.glow);
    grad.addColorStop(0.55, palette.glow.replace(/[\d.]+\)$/, '0.12)'));
    grad.addColorStop(1, 'rgba(0,0,0,0)');
    ctx.fillStyle = grad;
    ctx.beginPath();
    ctx.arc(n.x, n.y, haloR, 0, Math.PI * 2);
    ctx.fill();

    if (hop === 0) {
      // Root: concentric spotlight rings + ignition shockwave
      drawRing(ctx, n.x, n.y, baseR * 2.2, 1.6 / scale, '#ffffff', 0.92);
      drawRing(ctx, n.x, n.y, baseR * 3.4, 0.9 / scale, '#fbbf24', 0.55);
      drawRing(ctx, n.x, n.y, baseR * 5.0, 0.6 / scale, '#ef4444', 0.32);

      // Ignition shockwave (1 primary + 1 delayed secondary)
      const elapsed = performance.now() - clickIgnitionT;
      if (clickIgnitionT > 0 && elapsed >= 0 && elapsed < IGNITION_MS) {
        const t = elapsed / IGNITION_MS;
        const eased = 1 - Math.pow(1 - t, 3);   // easeOutCubic
        const r1 = baseR + eased * 95;
        const a1 = (1 - eased) * 0.85;
        ctx.beginPath();
        ctx.arc(n.x, n.y, r1, 0, Math.PI * 2);
        ctx.strokeStyle = `rgba(255,255,255,${a1.toFixed(3)})`;
        ctx.lineWidth = (3.2 - 2.6 * eased) / scale;
        ctx.stroke();

        const t2 = (elapsed - 280) / IGNITION_MS;
        if (t2 > 0 && t2 < 1) {
          const e2 = 1 - Math.pow(1 - t2, 3);
          const r2 = baseR + e2 * 140;
          ctx.beginPath();
          ctx.arc(n.x, n.y, r2, 0, Math.PI * 2);
          ctx.strokeStyle = `rgba(251,191,36,${((1 - e2) * 0.55).toFixed(3)})`;
          ctx.lineWidth = (1.6) / scale;
          ctx.stroke();
        }
      }
    }

    // Core fill
    const prevShadow = ctx.shadowBlur;
    ctx.shadowColor = palette.glow;
    ctx.shadowBlur = hop === 0 ? 18 : hop === 1 ? 12 : 6;
    ctx.beginPath();
    ctx.arc(n.x, n.y, baseR, 0, Math.PI * 2);
    ctx.fillStyle = palette.core;
    ctx.fill();
    ctx.shadowBlur = prevShadow || 0;

    // Crisp rim
    ctx.beginPath();
    ctx.arc(n.x, n.y, baseR, 0, Math.PI * 2);
    ctx.strokeStyle = palette.rim;
    ctx.lineWidth = 0.9 / scale;
    ctx.stroke();
  }

  function drawRing(ctx, x, y, r, lw, color, alpha) {
    ctx.beginPath();
    ctx.arc(x, y, r, 0, Math.PI * 2);
    const prev = ctx.globalAlpha;
    ctx.globalAlpha = alpha;
    ctx.strokeStyle = color;
    ctx.lineWidth = lw;
    ctx.stroke();
    ctx.globalAlpha = prev;
  }

  function startIgnitionLoop() {
    if (ignitionRafId) return;
    const tick = () => {
      const elapsed = performance.now() - clickIgnitionT;
      if (elapsed > IGNITION_MS + 400) {
        ignitionRafId = 0;
        return;
      }
      if (RENDERED) RENDERED.refresh();
      ignitionRafId = requestAnimationFrame(tick);
    };
    ignitionRafId = requestAnimationFrame(tick);
  }

  function stopIgnitionLoop() {
    if (ignitionRafId) {
      cancelAnimationFrame(ignitionRafId);
      ignitionRafId = 0;
    }
    clickIgnitionT = 0;
  }

  // ─── Idle-state hub glow ────────────────────────────────────────────────
  // Subtle radial glow behind high-centrality nodes — gives the "stars in
  // space" feel without overwhelming the rest of the constellation.
  // Glow uses globalCompositeOperation='lighter' so overlapping hubs reinforce.
  const HUB_GLOW_THRESHOLD = 0.018;   // degree centrality cutoff
  function paintIdleHubGlow(n, ctx, scale) {
    const deg = n.weight || 0;
    if (deg < HUB_GLOW_THRESHOLD) return;
    if (pathHops || hoveredNode) return;   // only idle state
    const baseR = Math.max(nodeRadius(n), 1);
    const haloR = baseR * (3 + Math.min(deg * 50, 4));
    const prevComp = ctx.globalCompositeOperation;
    ctx.globalCompositeOperation = 'lighter';
    const grad = ctx.createRadialGradient(n.x, n.y, baseR * 0.4, n.x, n.y, haloR);
    const typeRgb = parseRgb(baseColor(n)) || [200, 200, 200];
    grad.addColorStop(0, `rgba(${typeRgb[0]},${typeRgb[1]},${typeRgb[2]},${Math.min(0.22 + deg * 4, 0.45)})`);
    grad.addColorStop(1, `rgba(${typeRgb[0]},${typeRgb[1]},${typeRgb[2]},0)`);
    ctx.fillStyle = grad;
    ctx.beginPath();
    ctx.arc(n.x, n.y, haloR, 0, Math.PI * 2);
    ctx.fill();
    ctx.globalCompositeOperation = prevComp;
  }

  // ─── Smart label rendering ──────────────────────────────────────────────
  // Rules:
  //   - Path-trace node: always show (force=true)
  //   - Hover target: always show
  //   - Idle: show if zoom-scale ≥ 1.6 OR degree ≥ 0.03
  // Labels fade in based on (scale - threshold) so they don't pop abruptly.
  function paintNodeLabel(n, ctx, scale, force) {
    // News/catalyst nodes never get a label — far too many, visually noisy.
    if (n.type === 'catalyst') return;
    const deg = n.weight || 0;
    let alpha = 0;
    if (force) {
      alpha = 1;
    } else if (hoveredNode && (n.id === hoveredNode.id ||
                               (hoverNeighbors && hoverNeighbors.has(n.id)))) {
      alpha = 1;
    } else if (scale >= 1.6) {
      alpha = Math.min((scale - 1.6) * 1.4, 0.9);
    } else if (deg >= 0.03) {
      alpha = Math.min((deg - 0.03) * 25 + 0.4, 0.9);
    }
    if (alpha <= 0.05) return;

    const label = n.label || n.id || '';
    if (!label) return;
    // Font size in *canvas-space* — force-graph applies the zoom transform
    // before calling nodeCanvasObject, so we don't need to compensate manually.
    const fontPx = force ? 11 : Math.min(8 + deg * 60, 12);
    ctx.font = `600 ${fontPx}px Inter, sans-serif`;
    const offset = nodeRadius(n) + 3 / scale;
    ctx.textAlign = 'center';
    ctx.textBaseline = 'top';
    const prev = ctx.globalAlpha;
    ctx.globalAlpha = alpha;
    // Stroke first for legibility on busy bloom
    ctx.lineWidth = 3 / scale;
    ctx.strokeStyle = 'rgba(5,6,9,0.85)';
    ctx.strokeText(label, n.x, n.y + offset);
    ctx.fillStyle = pathHops ? (pathHops.get(n.id) === 0 ? '#ffffff' : '#fef3c7') : '#d4d4d8';
    ctx.fillText(label, n.x, n.y + offset);
    ctx.globalAlpha = prev;
  }

  function parseRgb(str) {
    const m = /rgba?\(([^)]+)\)/.exec(str || '');
    if (!m) return null;
    const parts = m[1].split(',').map(s => parseFloat(s.trim()));
    return [parts[0] | 0, parts[1] | 0, parts[2] | 0];
  }

  // ─── Custom d3 forces (radial + light collide) ──────────────────────────
  // force-graph bundles d3 internally but doesn't expose it. Implement
  // dependency-free factories that match d3-force's force-function contract.
  function forceRadialDeg(strengthFn, radiusFn) {
    let nodes;
    function force(alpha) {
      if (alpha < 0.005 || !nodes) return;
      for (const n of nodes) {
        const r = radiusFn(n);
        const dx = n.x || 0, dy = n.y || 0;
        const dist = Math.sqrt(dx * dx + dy * dy) || 0.001;
        const k = (dist - r) / dist * strengthFn(n) * alpha;
        n.vx = (n.vx || 0) - dx * k;
        n.vy = (n.vy || 0) - dy * k;
      }
    }
    force.initialize = (n) => { nodes = n; };
    return force;
  }

  function forceLightCollide(radiusFn) {
    let nodes;
    function force(alpha) {
      if (alpha < 0.03 || !nodes) return;   // skip late-cool ticks for perf
      const n = nodes.length;
      for (let i = 0; i < n; i++) {
        const a = nodes[i];
        const ra = radiusFn(a);
        // sample-based: each node checks 12 random others per tick
        for (let s = 0; s < 12; s++) {
          const j = (i + 1 + ((Math.random() * (n - 1)) | 0)) % n;
          const b = nodes[j];
          const dx = (b.x || 0) - (a.x || 0);
          const dy = (b.y || 0) - (a.y || 0);
          const dist = Math.sqrt(dx * dx + dy * dy) || 0.001;
          const min = ra + radiusFn(b);
          if (dist < min) {
            const push = (min - dist) * 0.5 * alpha;
            const ux = dx / dist, uy = dy / dist;
            a.vx = (a.vx || 0) - ux * push;
            a.vy = (a.vy || 0) - uy * push;
            b.vx = (b.vx || 0) + ux * push;
            b.vy = (b.vy || 0) + uy * push;
          }
        }
      }
    }
    force.initialize = (n) => { nodes = n; };
    return force;
  }

  function mountGraph() {
    const host = document.getElementById('graph-host');
    if (!host) { console.error('[nexus] #graph-host not found'); return; }
    if (typeof ForceGraph !== 'function') {
      console.error('[nexus] ForceGraph CDN not loaded'); return;
    }
    const data = filteredData();
    const rect = host.getBoundingClientRect();
    const W = Math.max(rect.width  || 0, window.innerWidth  - 256, 800);
    const H = Math.max(rect.height || 0, window.innerHeight - 64,  600);
    console.log('[nexus] mounting graph', { nodes: data.nodes.length, links: data.links.length, W, H });
    RENDERED = ForceGraph()(host)
      .width(W)
      .height(H)
      .graphData(data)
      .backgroundColor('rgba(0,0,0,0)')
      .enableZoomInteraction(true)
      .enablePanInteraction(true)
      .enableNodeDrag(false)
      .minZoom(0.1)
      .maxZoom(8)
      .nodeId('id')
      .nodeRelSize(3)
      .nodeVal(n => nodeSize(n))
      .nodeColor(n => nodeColor(n))
      .nodeLabel(n => buildNodeTooltip(n))
      .linkColor(linkColor)
      .linkWidth(linkWidth)
      .linkDirectionalParticles(l => {
        if (!pathSpine) return 0;
        const hop = spineHop(edgeEnd(l.source), edgeEnd(l.target));
        if (hop === 1) return 4;
        if (hop === 2) return 2;
        return 0;
      })
      .linkDirectionalParticleSpeed(0.008)
      .linkDirectionalParticleWidth(l => {
        const hop = spineHop(edgeEnd(l.source), edgeEnd(l.target));
        return hop === 1 ? 2.4 : 1.4;
      })
      .linkDirectionalParticleColor(l => {
        const hop = spineHop(edgeEnd(l.source), edgeEnd(l.target));
        return hop ? heat(hop).core : '#ffffff';
      })
      .onNodeHover(n => {
        if (hoveredNode === n) return;     // skip duplicate events
        hoveredNode = n;
        if (n) {
          hoverNeighbors = new Set();
          for (const { to } of (ADJ.get(n.id) || [])) hoverNeighbors.add(to);
        } else {
          hoverNeighbors = null;
        }
        document.body.style.cursor = n ? 'pointer' : 'default';
        scheduleRefresh();
      })
      .onNodeClick(n => {
        activeNode = n;
        runPathTrace(n);
        renderDetailPanel(n);
        clickIgnitionT = performance.now();
        document.body.classList.add('ng-thermal');
        // Force-graph stops ticking once the simulation cools; nudge it so the
        // thermographic paint actually flushes to canvas. Belt + braces:
        // sync refresh + rAF-scheduled refresh + ignition loop.
        if (RENDERED && RENDERED.d3ReheatSimulation) RENDERED.d3ReheatSimulation();
        if (RENDERED) RENDERED.refresh();
        scheduleRefresh();
        startIgnitionLoop();
      })
      .onBackgroundClick(() => {
        pathHops = null;
        pathSpine = null;
        pathEdgeHop = null;
        activeNode = null;
        hoveredNode = null;
        hoverNeighbors = null;
        stopIgnitionLoop();
        document.body.classList.remove('ng-thermal');
        document.getElementById('ng-detail').classList.add('hidden');
        scheduleRefresh();
      })
      .nodeCanvasObjectMode(n => {
        if (pathHops && pathHops.has(n.id)) return 'replace';
        return 'after';   // overlay: hub glow + smart label
      })
      .nodeCanvasObject((n, ctx, scale) => {
        if (pathHops && pathHops.has(n.id)) {
          paintThermographicNode(n, ctx, scale);
          paintNodeLabel(n, ctx, scale, true);
          return;
        }
        paintIdleHubGlow(n, ctx, scale);
        paintNodeLabel(n, ctx, scale, false);
      })
      .cooldownTicks(150)
      .d3VelocityDecay(0.40)
      .d3AlphaDecay(0.03)
      .onEngineStop(() => {
        // Center & fit once layout settles
        if (RENDERED && !pathHops) RENDERED.zoomToFit(400, 80);
      });

    // Hub-aware physics — restored to the stable pre-galaxy config.
    // Radial + collide forces were causing initial-tick velocity blow-ups
    // because force-graph spawns nodes near origin; division by tiny dist
    // produced NaN velocities. Keep just link + charge tuning here.
    try {
      const linkF = RENDERED.d3Force('link');
      if (linkF && linkF.distance) {
        linkF.distance(l => {
          const sDeg = (l.source && l.source.weight) || 0;
          const tDeg = (l.target && l.target.weight) || 0;
          return 80 + Math.max(sDeg, tDeg) * 700;
        }).strength(0.32);
      }
      const chargeF = RENDERED.d3Force('charge');
      if (chargeF && chargeF.strength) {
        chargeF.strength(n => -260 - (n.weight || 0) * 5200);
      }
    } catch (e) { /* silent fallback */ }

    // Resize handler so graph follows window changes — guarantees viewport fill.
    const resize = () => {
      const r = host.getBoundingClientRect();
      const w = Math.max(r.width || 0, window.innerWidth - 256);
      const h = Math.max(r.height || 0, window.innerHeight - 64);
      RENDERED.width(w).height(h);
    };
    window.addEventListener('resize', resize);
    // Trigger resize after first paint settles to catch late layout reflows.
    setTimeout(resize, 50);
    setTimeout(resize, 400);

    // Three-pass framing — first fit fires immediately on the seeded
    // circle (so the user sees something even before physics settles),
    // then again after early layout, then again once cooldown finishes.
    setTimeout(() => { if (RENDERED) RENDERED.zoomToFit(0,   120); }, 50);
    setTimeout(() => { if (RENDERED) RENDERED.zoomToFit(600, 140); }, 800);
    setTimeout(() => { if (RENDERED && !pathHops) RENDERED.zoomToFit(800, 160); }, 2500);
  }

  function edgeEnd(end) {
    // After force-graph's first .graphData() pass, edge.source / .target become
    // node-object refs. Normalize to string id either way.
    if (end == null) return null;
    return typeof end === 'string' ? end : (end.id || null);
  }

  function filteredData() {
    const nodes = (GRAPH_DATA.nodes || []).filter(n => {
      if (!visibleTypes.has(n.type)) return false;
      if (!showProvisional && n.status === 'provisional') return false;
      return true;
    });
    // Seed initial positions on a wide circle so simulation doesn't start
    // from a single (0,0) bundle (causes blank canvas for several frames).
    const N = nodes.length || 1;
    nodes.forEach((n, i) => {
      if (n.x == null || n.y == null) {
        const angle = (i / N) * Math.PI * 2;
        const radius = 250 + Math.random() * 350;
        n.x = Math.cos(angle) * radius;
        n.y = Math.sin(angle) * radius;
      }
    });
    const ids = new Set(nodes.map(n => n.id));
    const edges = (GRAPH_DATA.edges || []).filter(e => {
      const sId = edgeEnd(e.source);
      const tId = edgeEnd(e.target);
      if (!ids.has(sId) || !ids.has(tId)) return false;
      const decayed = (e.weight || 0) * (1.0 / decayMult);
      return decayed >= 0.05;
    });
    return { nodes, links: edges };
  }

  function applyFiltersAndRedraw() {
    if (!RENDERED) return;
    // Clear ephemeral highlight state so a stale hover/path doesn't keep the
    // graph dimmed after the user toggles a filter.
    hoveredNode = null;
    hoverNeighbors = null;
    pathHops = null;
    pathSpine = null;
    pathEdgeHop = null;
    stopIgnitionLoop();
    document.body.classList.remove('ng-thermal');
    document.getElementById('ng-detail').classList.add('hidden');
    RENDERED.graphData(filteredData());
  }

  // ─── path tracing (BFS up to PATH_MAX_HOPS) ────────────────────────────
  // Spine-only: each non-root node has ONE incoming edge from its BFS parent.
  // For huge hubs, cap 1st-hop fanout to top-N neighbors by edge weight.
  const HUB_FANOUT_CAP = 40;
  function runPathTrace(start) {
    pathHops = new Map();
    pathSpine = new Set();
    pathEdgeHop = new Map();
    pathHops.set(start.id, 0);
    let frontier = [start.id];

    for (let depth = 1; depth <= PATH_MAX_HOPS; depth++) {
      const next = [];
      for (const id of frontier) {
        let adj = (ADJ.get(id) || []).slice();
        if (depth === 1 && adj.length > HUB_FANOUT_CAP) {
          adj.sort((a, b) => (b.edge.weight || 0) - (a.edge.weight || 0));
          adj = adj.slice(0, HUB_FANOUT_CAP);
        }
        for (const { to } of adj) {
          if (!pathHops.has(to)) {
            pathHops.set(to, depth);
            const key = id + '|' + to;
            pathSpine.add(key);
            pathEdgeHop.set(key, depth);
            next.push(to);
          }
        }
      }
      frontier = next;
      if (!frontier.length) break;
    }
  }

  function renderDetailPanel(n) {
    const panel = document.getElementById('ng-detail');
    panel.classList.remove('hidden');
    const neighbors = (ADJ.get(n.id) || [])
      .map(({ to, edge }) => ({ id: to, edge, node: NODE_INDEX.get(to) }))
      .filter(x => x.node)
      .sort((a, b) => (b.edge.weight || 0) - (a.edge.weight || 0))
      .slice(0, 15);

    const second = collectHopNodes(2).slice(0, 10);
    const third = collectHopNodes(3).slice(0, 10);

    panel.innerHTML = `
      <div class="flex items-start justify-between">
        <div>
          <div class="ng-chip" data-type="${n.type}">${n.type}</div>
          <h3 class="font-bold text-base mt-1" style="color:var(--text-main)">${escapeHtml(n.label)}</h3>
          <p class="text-[10px] font-mono text-zinc-500 break-all">${n.id}</p>
        </div>
        <button id="ng-close" class="text-zinc-500 hover:text-rose-500 text-xs">✕</button>
      </div>
      <div class="grid grid-cols-3 gap-2 text-center text-[10px]">
        <div><div class="ng-stat-num text-lg">${(n.weight || 0).toFixed(3)}</div><div class="text-zinc-500">degree</div></div>
        <div><div class="ng-stat-num text-lg">${(n.pagerank || 0).toFixed(3)}</div><div class="text-zinc-500">pagerank</div></div>
        <div><div class="ng-stat-num text-lg">${n.mentions || 0}</div><div class="text-zinc-500">mentions</div></div>
      </div>
      <div class="text-[10px] text-zinc-500">last seen: ${n.last_seen || '—'}</div>

      ${n.status === 'provisional' ? `
        <div class="text-[10px] px-2 py-1 rounded bg-amber-500/10 text-amber-400 border border-amber-500/30">
          provisional — needs ≥3 distinct docs to promote
        </div>` : ''}

      ${(() => {
        // V3.1.0 — for ticker nodes show rolled-up news + themes from metadata.
        // Surfacing news here (in addition to hover tooltip) is the click-state
        // equivalent and matches the goal: news inside the ticker, not in the graph.
        const md = n.metadata || {};
        if (n.type !== 'ticker') return '';
        const themes = (md.themes || []).slice(0, 8);
        const narratives = (md.narratives || []).slice(0, 8);
        const news = (md.recent_news || []).slice(0, 6);
        const sector = md.sector;
        const verdictColor = v => {
          const k = String(v || '').toUpperCase();
          if (k.includes('BULL')) return '#22c55e';
          if (k.includes('BEAR')) return '#ef4444';
          return '#a1a1aa';
        };
        const themesBlock = themes.length ? `
          <div class="mt-2">
            <h4 class="text-[10px] font-black uppercase tracking-widest text-zinc-500 mb-1">主題 / Themes</h4>
            <div class="flex flex-wrap gap-1">
              ${themes.map(x => `<span style="background:rgba(251,191,36,0.12);color:#fbbf24;border:1px solid rgba(251,191,36,0.30);border-radius:4px;padding:1px 6px;font-size:10px;font-weight:600;">${escapeHtml(x)}</span>`).join('')}
            </div>
          </div>` : '';
        const narrativesBlock = narratives.length ? `
          <div class="mt-2">
            <h4 class="text-[10px] font-black uppercase tracking-widest text-zinc-500 mb-1">敘事 / Narratives</h4>
            <div class="flex flex-wrap gap-1">
              ${narratives.map(x => `<span style="background:rgba(52,211,153,0.10);color:#34d399;border:1px solid rgba(52,211,153,0.28);border-radius:4px;padding:1px 6px;font-size:10px;">${escapeHtml(x)}</span>`).join('')}
            </div>
          </div>` : '';
        const sectorBlock = sector ? `
          <div class="text-[10px] text-violet-400">${escapeHtml(sector)}</div>` : '';
        const newsBlock = news.length ? `
          <div class="mt-2">
            <h4 class="text-[10px] font-black uppercase tracking-widest text-zinc-500 mb-1">近期新聞 / Recent News</h4>
            <div class="space-y-1">
              ${news.map(e => {
                const col = verdictColor(e.verdict);
                const v = e.verdict ? `<span style="color:${col};font-weight:700;font-size:9px;">${escapeHtml(String(e.verdict).toUpperCase().slice(0, 8))}</span>` : '';
                const imp = (e.net_impact != null)
                  ? `<span style="color:${col};font-family:monospace;font-size:10px;">${e.net_impact >= 0 ? '+' : ''}${Number(e.net_impact).toFixed(1)}</span>` : '';
                const pub = e.published ? `<span class="text-zinc-500 text-[9px]">${escapeHtml(String(e.published).slice(0,10))}</span>` : '';
                return `<div class="text-[11px] leading-snug border-l-2 pl-2" style="border-color:${col};">
                  <div>${escapeHtml(e.headline || '')}</div>
                  <div class="flex gap-2 mt-0.5 items-baseline">${v}${imp}${pub}</div>
                </div>`;
              }).join('')}
            </div>
          </div>` : '';
        return sectorBlock + themesBlock + narrativesBlock + newsBlock;
      })()}

      <div>
        <h4 class="text-[10px] font-black uppercase tracking-widest text-zinc-500 mb-1">直接鄰居 (1st)</h4>
        <div class="space-y-0.5">
          ${neighbors.map(x => `
            <div class="ng-neighbor-row" data-jump-id="${x.id}">
              <span><span class="ng-chip" data-type="${x.node.type}">${x.node.type[0]}</span>
                <span class="label ml-1">${escapeHtml(x.node.label)}</span></span>
              <span class="weight">${x.edge.type}<br/>w=${(x.edge.weight || 0).toFixed(2)}</span>
            </div>`).join('')}
        </div>
      </div>

      ${second.length ? `
      <div>
        <h4 class="text-[10px] font-black uppercase tracking-widest text-zinc-500 mb-1">2nd-order 受惠者</h4>
        <div class="space-y-0.5">
          ${second.map(x => `<div class="ng-neighbor-row" data-jump-id="${x.id}">
            <span><span class="ng-chip" data-type="${x.type}">${x.type[0]}</span>
              <span class="label ml-1">${escapeHtml(x.label)}</span></span>
            <span class="weight">${(x.pagerank || 0).toFixed(3)}</span>
          </div>`).join('')}
        </div>
      </div>` : ''}

      ${third.length ? `
      <div>
        <h4 class="text-[10px] font-black uppercase tracking-widest text-zinc-500 mb-1">3rd-order 橋接</h4>
        <div class="space-y-0.5">
          ${third.map(x => `<div class="ng-neighbor-row" data-jump-id="${x.id}">
            <span><span class="ng-chip" data-type="${x.type}">${x.type[0]}</span>
              <span class="label ml-1">${escapeHtml(x.label)}</span></span>
            <span class="weight">${(x.pagerank || 0).toFixed(3)}</span>
          </div>`).join('')}
        </div>
      </div>` : ''}

      <div>
        <h4 class="text-[10px] font-black uppercase tracking-widest text-zinc-500 mb-1">來源</h4>
        <div class="text-[10px] font-mono text-zinc-500 break-words leading-snug">
          ${(n.sources || []).slice(0, 8).map(escapeHtml).join('<br/>') || '—'}
        </div>
      </div>
    `;

    panel.querySelector('#ng-close').addEventListener('click', () => {
      panel.classList.add('hidden');
      pathHops = null;
      pathSpine = null;
      pathEdgeHop = null;
      activeNode = null;
      stopIgnitionLoop();
      document.body.classList.remove('ng-thermal');
      if (RENDERED) RENDERED.refresh();
    });

    panel.querySelectorAll('[data-jump-id]').forEach(row => {
      row.addEventListener('click', () => {
        const tid = row.getAttribute('data-jump-id');
        const tn = NODE_INDEX.get(tid);
        if (tn && RENDERED) {
          activeNode = tn;
          runPathTrace(tn);
          renderDetailPanel(tn);
          clickIgnitionT = performance.now();
          startIgnitionLoop();
          RENDERED.centerAt(tn.x, tn.y, 600);
          RENDERED.zoom(2.6, 600);
          RENDERED.refresh();
        }
      });
    });
  }

  function collectHopNodes(targetHop) {
    if (!pathHops) return [];
    const out = [];
    for (const [id, h] of pathHops.entries()) {
      if (h === targetHop) {
        const n = NODE_INDEX.get(id);
        if (n) out.push(n);
      }
    }
    out.sort((a, b) => (b.pagerank || 0) - (a.pagerank || 0));
    return out;
  }

  // ─── utility ─────────────────────────────────────────────────────────────
  function updateMetaLine() {
    const meta = GRAPH_DATA.meta || {};
    const el = document.getElementById('ng-meta-line');
    const counts = Object.entries(meta.nodes_by_type || {})
      .map(([k, v]) => `${k}=${v}`).join(' · ');
    el.textContent = `${meta.node_count || 0} nodes · ${meta.edge_count || 0} edges · ${counts} · gen ${GRAPH_DATA.generated_at?.slice(0, 10) || '—'}`;
  }

  let _refreshScheduled = false;
  function scheduleRefresh() {
    if (_refreshScheduled || !RENDERED) return;
    _refreshScheduled = true;
    requestAnimationFrame(() => {
      _refreshScheduled = false;
      if (RENDERED) RENDERED.refresh();
    });
  }

  function getCssVar(name) {
    try { return getComputedStyle(document.documentElement).getPropertyValue(name).trim(); } catch (e) { return ''; }
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
