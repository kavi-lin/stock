#!/usr/bin/env python3
"""審計統計檢驗：Red Team verdict × outcome 相關性 + LLM confidence 校準。
數據源：event_index_latest.json（30d 實際報酬）join history.json（red_team/confidence）。
"""
import json
import random
import statistics as st
from collections import Counter, defaultdict

ROOT = '/Users/kavi/Developer/Claude/Projects/ai-investment-committee'

e = json.load(open(f'{ROOT}/reports/decision_review/event_index_latest.json'))
h = json.load(open(f'{ROOT}/investment/invest_logs/history.json'))

trades = {}
for rec in h:
    for t in rec.get('trades_this_session', []):
        trades[(rec.get('date'), t.get('ticker'))] = t

rows = []
for d in e['decisions']:
    if d.get('source') != 'deep-dive':
        continue
    r = d.get('reality_at_eval') or {}
    tr = (r.get('ticker_reality') or {})
    if r.get('pending') or tr.get('return_pct') is None:
        continue
    k = (d['decision_date'], d['tickers'][0])
    t = trades.get(k)
    if not t:
        continue
    rows.append({
        'date': d['decision_date'], 'ticker': d['tickers'][0],
        'action': t.get('final_action'), 'decision': t.get('final_decision'),
        'final_score': t.get('final_score'),
        'rt': t.get('red_team_verdict'),
        'conf': t.get('avg_confidence'),
        'ret': tr['return_pct'],
        'runup': tr.get('max_runup_pct'), 'dd': tr.get('max_drawdown_pct'),
        'label': (d.get('verdict') or {}).get('label'),
    })

print(f'joined completed-window rows: {len(rows)}')
print('action dist:', Counter(r['action'] for r in rows))
print('rt dist:', Counter(r['rt'] for r in rows))

def summ(xs):
    xs = [x for x in xs if x is not None]
    if not xs:
        return 'n=0'
    return (f'n={len(xs)} mean={st.mean(xs):+.2f} median={st.median(xs):+.2f} '
            f'stdev={st.pstdev(xs):.2f}')

def perm_test(a, b, n=20000, seed=42):
    """two-sided permutation test on mean difference"""
    if not a or not b:
        return None
    rng = random.Random(seed)
    obs = st.mean(a) - st.mean(b)
    pool = a + b
    na = len(a)
    cnt = 0
    for _ in range(n):
        rng.shuffle(pool)
        if abs(st.mean(pool[:na]) - st.mean(pool[na:])) >= abs(obs):
            cnt += 1
    return obs, cnt / n

print('\n===== TEST A: Red Team verdict × 30d outcome =====')
strong = [r for r in rows if r['rt'] == 'STRONG_COUNTER']
nonstrong = [r for r in rows if r['rt'] not in (None, 'STRONG_COUNTER')]
none_rt = [r for r in rows if r['rt'] is None]
print(f'STRONG_COUNTER: {summ([r["ret"] for r in strong])}')
print(f'MODERATE/other: {summ([r["ret"] for r in nonstrong])}')
print(f'None:           {summ([r["ret"] for r in none_rt])}')
res = perm_test([r['ret'] for r in strong], [r['ret'] for r in nonstrong])
if res:
    print(f'mean diff (STRONG - other) = {res[0]:+.2f}pp, permutation p = {res[1]:.3f}')

# Red Team 的職責是反對做多論點 → 若有訊號，STRONG_COUNTER 應預測更差的前瞻報酬/更深 drawdown
print('\n-- drawdown (deeper = red team right) --')
print(f'STRONG dd:   {summ([r["dd"] for r in strong])}')
print(f'other dd:    {summ([r["dd"] for r in nonstrong])}')
res = perm_test([r['dd'] for r in strong if r['dd'] is not None],
                [r['dd'] for r in nonstrong if r['dd'] is not None])
if res:
    print(f'mean diff = {res[0]:+.2f}pp, p = {res[1]:.3f}')

# 條件在執行的 BUY/STAGED 上（紅隊反對但仍執行 → 若紅隊有訊號這些應該表現差）
print('\n-- executed trades only (EXECUTE/STAGED) --')
ex_strong = [r for r in strong if r['action'] in ('EXECUTE', 'STAGED')]
ex_other = [r for r in nonstrong if r['action'] in ('EXECUTE', 'STAGED')]
print(f'executed & STRONG: {summ([r["ret"] for r in ex_strong])}')
print(f'executed & other:  {summ([r["ret"] for r in ex_other])}')
res = perm_test([r['ret'] for r in ex_strong], [r['ret'] for r in ex_other])
if res:
    print(f'mean diff = {res[0]:+.2f}pp, p = {res[1]:.3f}')

# CANCEL 的（紅隊反對且沒買 → 若紅隊對，這些之後應該跌）
print('\n-- cancelled only --')
ca_strong = [r for r in strong if r['action'] == 'CANCEL']
print(f'cancelled & STRONG 30d ret: {summ([r["ret"] for r in ca_strong])}')
pos = sum(1 for r in ca_strong if r['ret'] > 0)
print(f'  之後上漲比例: {pos}/{len(ca_strong)} = {pos/len(ca_strong)*100:.0f}%')

print('\n===== TEST B: confidence 校準 =====')
# 方向命中定義：sign(final_score) 與 sign(30d return) 一致（score≈0 或 |ret|<1% 視為 neutral 排除）
cal = [r for r in rows if r['conf'] is not None and r['final_score'] is not None
       and abs(r['ret']) >= 1.0 and abs(r['final_score']) >= 0.05]
for r in cal:
    r['dir_hit'] = (r['final_score'] > 0) == (r['ret'] > 0)
print(f'calibration sample: {len(cal)}')

buckets = defaultdict(list)
for r in cal:
    b = round(r['conf'] * 10) / 10  # 0.1 buckets
    buckets[b].append(r['dir_hit'])
print('conf bucket -> directional hit rate:')
for b in sorted(buckets):
    xs = buckets[b]
    print(f'  {b:.1f}: {sum(xs)}/{len(xs)} = {sum(xs)/len(xs)*100:.0f}%')

def spearman(x, y):
    def rank(v):
        s = sorted(range(len(v)), key=lambda i: v[i])
        rk = [0.0] * len(v)
        i = 0
        while i < len(s):
            j = i
            while j + 1 < len(s) and v[s[j+1]] == v[s[i]]:
                j += 1
            avg = (i + j) / 2 + 1
            for k2 in range(i, j + 1):
                rk[s[k2]] = avg
            i = j + 1
        return rk
    rx, ry = rank(x), rank(y)
    mx, my = st.mean(rx), st.mean(ry)
    num = sum((a - mx) * (b - my) for a, b in zip(rx, ry))
    den = (sum((a - mx)**2 for a in rx) * sum((b - my)**2 for b in ry)) ** 0.5
    return num / den if den else 0.0

rho = spearman([r['conf'] for r in cal], [1.0 if r['dir_hit'] else 0.0 for r in cal])
print(f'Spearman rho(conf, dir_hit) = {rho:+.3f}')

# permutation p for rho
vals = [1.0 if r['dir_hit'] else 0.0 for r in cal]
confs = [r['conf'] for r in cal]
rng = random.Random(7)
cnt = 0
N = 10000
for _ in range(N):
    rng.shuffle(vals)
    if abs(spearman(confs, vals)) >= abs(rho):
        cnt += 1
print(f'permutation p = {cnt/N:.3f}')

# hit label（覆盤 verdict）版本
cal2 = [r for r in rows if r['conf'] is not None and r['label'] in ('hit', 'miss')]
rho2 = spearman([r['conf'] for r in cal2],
                [1.0 if r['label'] == 'hit' else 0.0 for r in cal2])
print(f'\nverdict-label 版: n={len(cal2)}, rho(conf, hit) = {rho2:+.3f}')
hi = [r for r in cal2 if r['conf'] >= 0.625]
lo = [r for r in cal2 if r['conf'] < 0.625]
print(f'conf>=median(0.625): hit {sum(1 for r in hi if r["label"]=="hit")}/{len(hi)}')
print(f'conf< median      : hit {sum(1 for r in lo if r["label"]=="hit")}/{len(lo)}')

print('\n===== 附加: final_score 高低 vs 30d return（分數本身有沒有訊號）=====')
sc = [r for r in rows if r['final_score'] is not None and abs(r['final_score']) < 5]
rho3 = spearman([r['final_score'] for r in sc], [r['ret'] for r in sc])
print(f'n={len(sc)}, Spearman rho(final_score, 30d ret) = {rho3:+.3f}')
