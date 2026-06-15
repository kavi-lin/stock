import json
from collections import Counter, defaultdict

def main():
    with open("reports/decision_review/event_index_latest.json", "r") as f:
        data = json.load(f)
        
    decisions = data.get("decisions", [])
    print(f"Total decisions: {len(decisions)}")
    
    # 1. Verdict Statistics by Source
    source_stats = defaultdict(lambda: Counter())
    for d in decisions:
        src = d.get("source")
        lbl = d.get("verdict", {}).get("label", "n/a")
        source_stats[src][lbl] += 1
        
    print("\nSource Stats:")
    for src, counts in source_stats.items():
        print(f"Source: {src}")
        for lbl in ["hit", "miss", "neutral", "pending", "n/a"]:
            print(f"  {lbl}: {counts.get(lbl, 0)}")
            
    # 2. Industry Rollup
    print("\nIndustry Rollup:")
    rollup = data.get("industry_rollup", [])
    print(f"Total industry rollup buckets: {len(rollup)}")
    for item in rollup[:15]:
        print(f"  {item.get('industry')} ({item.get('sector')}): n={item.get('n')}, miss_rate={item.get('miss_rate')*100:.1f}%, avg_miss_return={item.get('avg_miss_return_pct') or 0.0:.2f}%, top_30%={item.get('industry_top_30pct')}, tickers={item.get('tickers')}")

    # 3. Active Ledger Metrics Evaluation
    deep_dives = [d for d in decisions if d.get("source") == "deep-dive"]
    print(f"\nDeep Dives count: {len(deep_dives)}")
    
    staged_entries = []
    executes = []
    
    null_actions = 0
    null_scores = 0
    for d in deep_dives:
        dc = d.get("decision_content", {})
        action = dc.get("final_action")
        score = dc.get("final_score")
        if action is None:
            null_actions += 1
        if score is None:
            null_scores += 1
            
        lbl = d.get("verdict", {}).get("label", "n/a")
        if action == "STAGED_ENTRY":
            staged_entries.append(lbl)
        elif action == "EXECUTE":
            executes.append(lbl)
            
    print(f"Deep dive null actions: {null_actions} ({null_actions/len(deep_dives)*100:.1f}%)")
    print(f"Deep dive null scores: {null_scores} ({null_scores/len(deep_dives)*100:.1f}%)")
    
    def get_miss_rate(labels):
        if not labels:
            return 0.0
        c = Counter(labels)
        miss = c.get("miss", 0)
        total = len(labels)
        return miss / total * 100
        
    def get_hit_rate(labels):
        if not labels:
            return 0.0
        c = Counter(labels)
        hit = c.get("hit", 0)
        total = len(labels)
        return hit / total * 100
        
    dd_labels = [d.get("verdict", {}).get("label", "n/a") for d in deep_dives]
    print(f"STAGED_ENTRY miss_rate: {get_miss_rate(staged_entries):.1f}% (N={len(staged_entries)})")
    print(f"EXECUTE miss_rate: {get_miss_rate(executes):.1f}% (N={len(executes)})")
    print(f"Overall deep-dive hit_rate: {get_hit_rate(dd_labels):.1f}% (N={len(dd_labels)})")
    
    # Rec 4 - news-digest macro_delta
    news_digests = [d for d in decisions if d.get("source") == "news-digest"]
    null_deltas = 0
    for d in news_digests:
        dc = d.get("decision_content", {})
        if dc.get("macro_delta") is None:
            null_deltas += 1
    print(f"News digests count: {len(news_digests)}")
    print(f"News digest null deltas: {null_deltas} ({null_deltas/len(news_digests)*100:.1f}%)")
    
    # Rec 7 - sub_industry_heat
    null_heat = 0
    top_30_miss = []
    not_top_30_miss = []
    for d in deep_dives:
        th = d.get("tuning_hooks", {})
        heat = th.get("sub_industry_heat")
        if heat is None or heat.get("industry_avg_change_1d") is None:
            null_heat += 1
        else:
            top_30 = heat.get("industry_top_30pct")
            lbl = d.get("verdict", {}).get("label", "n/a")
            if top_30 is True:
                top_30_miss.append(lbl)
            elif top_30 is False:
                not_top_30_miss.append(lbl)
                
    print(f"Deep dive null heat: {null_heat} ({null_heat/len(deep_dives)*100:.1f}%)")
    print(f"Top 30% miss_rate: {get_miss_rate(top_30_miss):.1f}% (N={len(top_30_miss)})")
    print(f"Not Top 30% miss_rate: {get_miss_rate(not_top_30_miss):.1f}% (N={len(not_top_30_miss)})")
    print(f"Heat miss difference: {get_miss_rate(top_30_miss) - get_miss_rate(not_top_30_miss):.1f}pp")
    
    # Rec 8 - Industry rollup
    print(f"Industry rollup buckets: {len(rollup)}")
    
    # TODO-001 evaluation
    # CANCEL decisions (含 final_action_modifier=CANCEL)
    cancel_decisions = []
    for d in deep_dives:
        dc = d.get("decision_content", {})
        action = dc.get("final_action")
        modifier = dc.get("final_action_modifier")
        if action == "CANCEL" or modifier == "CANCEL":
            cancel_decisions.append(d)
    print(f"CANCEL decisions count: {len(cancel_decisions)}")
    cancel_labels = [d.get("verdict", {}).get("label", "n/a") for d in cancel_decisions]
    print(f"CANCEL miss rate: {get_miss_rate(cancel_labels):.1f}% (N={len(cancel_labels)})")
    
    # TODO-002 evaluation
    # V5 era deep-dive count: decisive_agent in tuning_hooks
    v5_dd = []
    for d in deep_dives:
        th = d.get("tuning_hooks", {})
        if th.get("decisive_agent") is not None:
            v5_dd.append(d)
    print(f"V5 deep-dives count (with decisive_agent): {len(v5_dd)}")
    score_x_conf = [d for d in v5_dd if d.get("tuning_hooks", {}).get("decisive_agent_method") == "score_x_confidence"]
    print(f"decisive_agent_method=score_x_confidence count: {len(score_x_conf)} ({len(score_x_conf)/len(v5_dd)*100 if v5_dd else 0:.1f}%)")
    
    # TODO-003 evaluation: momentum-screen aggregate records
    momentum_screens = [d for d in decisions if d.get("source") == "momentum-screen"]
    print(f"Momentum screens count: {len(momentum_screens)}")
    momentum_labels = [d.get("verdict", {}).get("label", "n/a") for d in momentum_screens]
    print(f"Momentum hit rate: {get_hit_rate(momentum_labels):.1f}%, miss rate: {get_miss_rate(momentum_labels):.1f}% (N={len(momentum_labels)})")

if __name__ == "__main__":
    main()
