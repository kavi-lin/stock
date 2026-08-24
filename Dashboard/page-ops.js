/* ════════════════════════════════════════════════════════════════════
   page-ops.js — Script 工具箱 (V3.47.0 → V4.6)
   GET /api/ops/scripts → registry (config/ops_scripts.json) + artifact-mtime
   推斷的 last run + cadence 到期判定。
   V4.6: entry 帶 protocol_id/endpoint → ▶ 一鍵執行（走 protocol queue /
   journal endpoint）；auto:true → 🤖 chip（server ops_auto_loop 到期自動跑）。
   ════════════════════════════════════════════════════════════════════ */
const $ = id => document.getElementById(id);

const STATUS_META = {
    due:       { zh: '到期，該跑了', en: 'DUE',       cls: 'text-red-500 border-red-500/40 bg-red-500/10',       icon: 'alarm-clock' },
    never_run: { zh: '從未執行',     en: 'NEVER RUN',  cls: 'text-amber-500 border-amber-500/40 bg-amber-500/10', icon: 'circle-dashed' },
    fresh:     { zh: '新鮮',         en: 'FRESH',      cls: 'text-emerald-500 border-emerald-500/40 bg-emerald-500/10', icon: 'check-circle-2' },
    on_demand: { zh: '隨需',         en: 'ON DEMAND',  cls: 'text-zinc-400 border-zinc-500/30 bg-zinc-500/10',    icon: 'hand' },
};
const CADENCE_ZH = { daily: '每日', weekly: '每週', monthly: '每月', on_demand: '隨需' };

function fmtAge(h) {
    if (h == null) return '—';
    if (h < 1) return `${Math.round(h * 60)} 分鐘前`;
    if (h < 48) return `${Math.round(h)} 小時前`;
    return `${Math.round(h / 24)} 天前`;
}

function copyCmd(cmd, btn) {
    navigator.clipboard?.writeText(cmd).then(() => {
        btn.textContent = '✓ 已複製';
        setTimeout(() => { btn.textContent = '📋 複製指令'; }, 1500);
    });
}

// ── V4.6 — one-click run (protocol queue / journal endpoint) ────────────
async function runEntry(s, btn) {
    btn.disabled = true;
    btn.textContent = '⏳ 排隊中…';
    try {
        let r;
        if (s.endpoint) {
            r = await fetch(s.endpoint, { method: 'POST' });
        } else {
            r = await fetch('/api/protocol-queue', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ name: s.protocol_id }),
            });
        }
        const d = await r.json().catch(() => ({}));
        if (!r.ok || d.error) {
            btn.textContent = '⚠ ' + (d.error || `HTTP ${r.status}`).slice(0, 30);
            btn.disabled = false;
            return;
        }
        btn.textContent = '⏳ 執行中…';
        pollUntilIdle(btn, d.id || null);
    } catch (e) {
        btn.textContent = '⚠ ' + String(e).slice(0, 30);
        btn.disabled = false;
    }
}

function pollUntilIdle(btn, queueId) {
    const timer = setInterval(async () => {
        try {
            const suffix = queueId ? `?queue_id=${encodeURIComponent(queueId)}` : '';
            const r = await fetch('/api/run-protocol/status' + suffix);
            const d = await r.json();
            if (!d || d.status !== 'running') {
                clearInterval(timer);
                btn.textContent = '✓ 完成';
                setTimeout(load, 1200);   // refresh badges
            }
        } catch (e) { /* keep polling */ }
    }, 3000);
}

function render(data) {
    const list = $('ops-list'), summary = $('ops-summary'), errBox = $('ops-error');
    if (data.error) {
        errBox.textContent = data.error;
        errBox.classList.remove('hidden');
        return;
    }
    errBox.classList.add('hidden');
    const scripts = data.scripts || [];

    const counts = {};
    scripts.forEach(s => { counts[s.status] = (counts[s.status] || 0) + 1; });
    summary.innerHTML = Object.entries(STATUS_META)
        .filter(([k]) => counts[k])
        .map(([k, m]) => `
          <span class="text-[11px] font-bold px-3 py-1.5 rounded-full border ${m.cls}">
            ${m.zh} ${counts[k]}
          </span>`).join('');

    list.innerHTML = scripts.map(s => {
        const m = STATUS_META[s.status] || STATUS_META.on_demand;
        return `
        <div class="glass-card p-4 flex items-center gap-4">
            <span class="shrink-0 text-[10px] font-bold px-2.5 py-1 rounded-full border ${m.cls} flex items-center gap-1">
                <i data-lucide="${m.icon}" class="w-3 h-3"></i>${m.zh}
            </span>
            <div class="min-w-0 flex-1">
                <div class="flex items-baseline gap-2 flex-wrap">
                    <span class="font-bold text-sm">${s.name}</span>
                    ${s.auto ? '<span class="text-[9px] font-bold px-1.5 py-0.5 rounded border border-sky-500/40 text-sky-400 bg-sky-500/10" title="server 到期自動跑（ops_auto_loop）">🤖 自動</span>' : ''}
                    <span class="text-[10px] text-zinc-500">${CADENCE_ZH[s.cadence] || s.cadence}</span>
                    <span class="text-[10px] font-mono ${s.status === 'due' ? 'text-red-400' : 'text-zinc-500'}">
                        上次：${fmtAge(s.last_run_age_hours)}
                    </span>
                </div>
                <p class="text-[11px] text-zinc-500 truncate mt-0.5">${s.desc || ''}</p>
                <code class="text-[10px] font-mono text-zinc-400 block truncate mt-0.5">${s.cmd}</code>
            </div>
            ${(s.protocol_id || s.endpoint) ? `
            <button class="ops-run shrink-0 text-[10px] font-bold px-2.5 py-1.5 rounded-lg border border-emerald-500/40 text-emerald-500 hover:bg-emerald-500/10"
                    data-id="${s.id}">▶ 執行</button>` : ''}
            <button class="ops-copy shrink-0 text-[10px] px-2.5 py-1.5 rounded-lg border border-zinc-300 dark:border-zinc-700 hover:bg-zinc-100 dark:hover:bg-zinc-800"
                    data-cmd="${s.cmd.replace(/"/g, '&quot;')}">📋 複製指令</button>
        </div>`;
    }).join('');

    list.querySelectorAll('.ops-copy').forEach(btn =>
        btn.addEventListener('click', () => copyCmd(btn.dataset.cmd, btn)));
    list.querySelectorAll('.ops-run').forEach(btn => {
        const s = scripts.find(x => x.id === btn.dataset.id);
        if (s) btn.addEventListener('click', () => runEntry(s, btn));
    });

    $('ops-as-of').textContent = new Date((data.generated_at || 0) * 1000).toLocaleTimeString();
    if (window.lucide) lucide.createIcons();
}

function load() {
    fetch('/api/ops/scripts?t=' + Date.now())
        .then(r => r.json())
        .then(render)
        .catch(err => {
            $('ops-error').textContent = 'API 不可用：' + err;
            $('ops-error').classList.remove('hidden');
        });
}

document.addEventListener('DOMContentLoaded', () => {
    UI.boot('ops', { reload: load });
    $('ops-refresh').addEventListener('click', load);
    load();
});
