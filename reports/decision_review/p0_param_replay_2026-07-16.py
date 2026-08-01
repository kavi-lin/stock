#!/usr/bin/env python3
"""P0 參數選擇 replay：
A) P0-1 — 正分模糊區 [0, staged) 的 CANCEL/HOLD 30d 結果，按分數帶 / regime / industry gate 分組
   → 決定 Rec 11 gate 是否放寬、probe 分數下限
B) P0-4 — 用 event_index 的 per-agent score×conf 重算 raw_total（連續 C vs 分檔 C_eff），
   看 decision flips 與其 30d 結果
"""
import json
import statistics as st
from collections import Counter, defaultdict

ROOT = '/Users/kavi/Developer/Claude/Projects/ai-investment-committee'
e = json.load(open(f'{ROOT}/reports/decision_review/event_index_latest.json'))
h = json.load(open(f'{ROOT}/investment/invest_logs/history.json'))

trades = {}
for rec in h:
    for t in rec.get('trades_this_session', []):
        trades[(rec.get('date'), t.get('ticker'))] = (t, rec)

rows = []
for d in e['decisions']:
    if d.get('source') != 'deep-dive':
        continue
    r = d.get('reality_at_eval') or {}
    tr = (r.get('ticker_reality') or {})
    if r.get('pending') or tr.get('return_pct') is None:
        continue
    k = (d['decision_date'], d['tickers'][0])
    if k not in trades:
        continue
    t, rec = trades[k]
    hooks = d.get('tuning_hooks') or {}
    heat = hooks.get('sub_industry_heat') or {}
    rows.append({
        'date': d['decision_date'], 'ticker': d['tickers'][0],
        'action': t.get('final_action'),
        'fs': t.get('final_score'),
        'regime': (rec.get('phase0_macro_snapshot') or {}).get('market_regime'),
        'top30': heat.get('industry_top_30pct'),
        'agents': d.get('agent_breakdown') or [],
        'ret': tr['return_pct'], 'runup': tr.get('max_runup_pct'), 'dd': tr.get('max_drawdown_pct'),
    })
print(f'rows: {len(rows)}')

def summ(g):
    if not g:
        return 'n=0'
    rets = [r['ret'] for r in g]
    up = sum(1 for x in rets if x > 0)
    dd = [r['dd'] for r in g if r['dd'] is not None]
    return (f'n={len(g)} mean_ret={st.mean(rets):+.1f}% up_rate={up}/{len(g)}'
            f' mean_dd={st.mean(dd):+.1f}%' if dd else f'n={len(g)}')

print('\n===== A) 正分模糊區 [0, 0.8) 的 CANCEL/HOLD =====')
fuzzy = [r for r in rows if r['action'] in ('CANCEL', 'HOLD')
         and r['fs'] is not None and 0 <= r['fs'] < 0.8]
print('全部模糊區觀望:', summ(fuzzy))
for lo, hi in [(0.0, 0.2), (0.2, 0.4), (0.4, 0.6), (0.6, 0.8)]:
    g = [r for r in fuzzy if lo <= r['fs'] < hi]
    print(f'  score [{lo},{hi}): {summ(g)}')
print('\n-- regime 分組 --')
for reg in ('RISK_ON', 'BULL', 'SIDEWAYS', 'VOLATILE', 'RISK_OFF'):
    g = [r for r in fuzzy if r['regime'] == reg]
    print(f'  {reg}: {summ(g)}')
bull = [r for r in fuzzy if r['regime'] in ('RISK_ON', 'BULL')]
print('\n-- RISK_ON/BULL 內，industry_top_30pct 分組（注意 heat 是現時非決策時，僅參考）--')
for v in (True, False, None):
    g = [r for r in bull if r['top30'] is v]
    print(f'  top30={v}: {summ(g)}')
print('\n-- RISK_ON/BULL 內按分數帶 --')
for lo, hi in [(0.0, 0.2), (0.2, 0.4), (0.4, 0.8)]:
    g = [r for r in bull if lo <= r['fs'] < hi]
    print(f'  score [{lo},{hi}): {summ(g)}')
# 對照：模糊區但被執行的（staged）
fuzzy_ex = [r for r in rows if r['action'] in ('STAGED', 'EXECUTE')
            and r['fs'] is not None and 0 <= r['fs'] < 0.8]
print('\n對照—模糊區但仍執行者:', summ(fuzzy_ex))

print('\n===== B) P0-4 confidence 分檔 what-if =====')
W = {'Fundamentals': 0.25, 'Sentiment': 0.15, 'News': 0.20, 'Technical': 0.25,
     'Valuation': 0.15, 'Valuation Specialist': 0.15}

def raw(agents, mode):
    tot = 0.0
    n = 0
    for a in agents:
        w = W.get(a.get('agent'))
        s, c = a.get('score'), a.get('confidence')
        if w is None or s is None:
            continue
        if c is None:
            c = 0.6
        if mode == 'cont':
            ce = c
        else:  # step: <0.45 → 0.3, else 0.6
            ce = 0.3 if c < 0.45 else 0.6
        tot += w * s * ce
        n += 1
    return tot if n >= 4 else None

flips = []
both = []
for r in rows:
    rc = raw(r['agents'], 'cont')
    rs = raw(r['agents'], 'step')
    if rc is None:
        continue
    both.append((rc, rs, r))
print(f'可重算 raw_total 樣本: {len(both)}')
# 相關性：兩版 raw 與 30d ret 的 Spearman
def spearman(x, y):
    def rank(v):
        s = sorted(range(len(v)), key=lambda i: v[i])
        rk = [0.0]*len(v); i = 0
        while i < len(s):
            j = i
            while j+1 < len(s) and v[s[j+1]] == v[s[i]]:
                j += 1
            for k2 in range(i, j+1):
                rk[s[k2]] = (i+j)/2+1
            i = j+1
        return rk
    rx, ry = rank(x), rank(y)
    mx, my = st.mean(rx), st.mean(ry)
    num = sum((a-mx)*(b-my) for a, b in zip(rx, ry))
    den = (sum((a-mx)**2 for a in rx)*sum((b-my)**2 for b in ry))**0.5
    return num/den if den else 0.0

rets = [r['ret'] for _, _, r in both]
print(f'rho(raw_cont, ret) = {spearman([a for a,_,_ in both], rets):+.3f}')
print(f'rho(raw_step, ret) = {spearman([b for _,b,_ in both], rets):+.3f}')
# 分檔後跨帶移動（用 0.8/1.2 default 帶）
def band(x):
    if x >= 1.2: return 'BUY'
    if x >= 0.8: return 'STAGED'
    if x > -0.8: return 'HOLD'
    return 'SELL-side'
moves = Counter((band(a), band(b)) for a, b, _ in both if band(a) != band(b))
print('band flips (cont→step):', dict(moves))
for (fa, fb), _ in moves.items():
    g = [r for a, b, r in both if band(a) == fa and band(b) == fb]
    print(f'  {fa}→{fb}: {summ(g)}')
