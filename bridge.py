import json
import os
import glob
import requests
from datetime import datetime

FMP_API_KEY = os.getenv("FMP_API_KEY")

# Paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SECTOR_LOGS = os.path.join(BASE_DIR, 'sector', 'sector_logs')
INVEST_LOGS = os.path.join(BASE_DIR, 'investment', 'invest_logs')
NEWS_LOGS = os.path.join(BASE_DIR, 'news', 'news_logs')
OUTPUT_FILE = os.path.join(BASE_DIR, 'Dashboard', 'data.json')

def get_latest_file(pattern):
    files = glob.glob(pattern)
    if not files:
        return None
    return max(files, key=os.path.getmtime)

def run_bridge():
    data = {
        "status": "success",
        "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "market": {
            "regime": "UNKNOWN",
            "fear_greed": 50,
            "themes": [],
            "hot_sectors": [],
            "notes": ""
        },
        "recent_analysis": [],
        "news": []
    }

    # 2. Load Audit History (Consolidated & Smart)
    REPORTS_DIR = os.path.join(BASE_DIR, 'reports')
    history_file = os.path.join(INVEST_LOGS, 'history.json')
    audit_map = {} # To avoid duplicates
    
    # Process history.json first
    if os.path.exists(history_file):
        try:
            with open(history_file, 'r') as f:
                history_data = json.load(f)
                # Take last 10 audits
                for item in reversed(history_data[-10:]):
                    ticker = item.get("ticker", "UNKNOWN")
                    date_raw = item.get("date", "Unknown")
                    date_clean = date_raw.replace("-", "")
                    
                    # Smart Matching: Search for file in reports/
                    report_path = None
                    # Try exact date first, then any date for that ticker
                    possible_patterns = [
                        f"{date_clean}_{ticker}.md",
                        f"{date_clean}_{ticker}.html",
                        f"*{ticker}.md",
                        f"*{ticker}.html"
                    ]
                    
                    for pattern in possible_patterns:
                        matches = glob.glob(os.path.join(REPORTS_DIR, pattern))
                        if matches:
                            report_path = os.path.join('reports', os.path.basename(matches[0]))
                            break

                    meta = item.get("metadata", {})
                    decision = item.get("final_action", "HOLD")
                    score = meta.get("final_score") or item.get("final_score", 0.0)
                    ctx = meta.get("macro_context", "")

                    # Target Extraction (TP/SL)
                    tp = meta.get("take_profit") or item.get("take_profit")
                    sl = meta.get("stop_loss") or item.get("stop_loss")
                    
                    # Entry / Watch Extraction
                    watch = meta.get("watch_price") or meta.get("trigger_price")
                    entry = meta.get("entry_range") or meta.get("entry_price")
                    
                    # Regex Fallback for Watch/Entry from context
                    import re
                    if not entry and not watch:
                        print(f"[DEBUG] Ticker {ticker} missing structure targets. Scanning context...")
                        # Find patterns like "$143" or "$108-115"
                        matches = re.findall(r"\$(\d+[\-\d+]*)", ctx)
                        if matches:
                            entry = matches[-1]
                            print(f"[DEBUG] Found target in context: {entry}")
                        else:
                            # DEEP SCAN: Read the MD file if it exists
                            if report_path:
                                try:
                                    full_rep_path = os.path.join(BASE_DIR, report_path)
                                    with open(full_rep_path, 'r') as rf:
                                        content = rf.read() # Read all
                                        # Search for support/entry (TAKE THE LAST ONE in the file)
                                        support_matches = re.findall(r"(支撐|進場|觸及|回調).*?\$(\d+[\.\dot\d+]*)", content)
                                        target_matches = re.findall(r"(目標).*?\$(\d+[\.\dot\d+]*)", content)
                                        
                                        if support_matches:
                                            watch = support_matches[-1][1] # Get price from last match
                                            print(f"[DEBUG] Last Priority Support {ticker} found: {watch}")
                                        elif target_matches:
                                            watch = target_matches[-1][1]
                                            print(f"[DEBUG] Last Secondary Target {ticker} found: {watch}")
                                        else:
                                            # Fallback: any price
                                            deep_matches = re.findall(r"\$(\d+[\,\.\d+]*)", content)
                                            if len(deep_matches) > 3:
                                                watch = deep_matches[-1]
                                                print(f"[DEBUG] Last Price {ticker} fallback: {watch}")
                                except Exception as rf_err:
                                    print(f"[DEBUG] Deep Scan error for {ticker}: {rf_err}")

                    if isinstance(entry, list): entry = " - ".join(entry) 
                    
                    # Backtest: Fetch Current Price
                    perf = None
                    if FMP_API_KEY:
                        try:
                            price_res = requests.get(f"https://financialmodelingprep.com/api/v3/quote/{ticker}?apikey={FMP_API_KEY}").json()
                            if price_res:
                                curr_price = price_res[0].get("price")
                                entry_range = meta.get("entry_range") # ["$253", "$258"]
                                if entry_range and isinstance(entry_range, list):
                                    entry_price = float(entry_range[0].replace("$", ""))
                                    chg = ((curr_price - entry_price) / entry_price) * 100
                                    perf = {
                                        "current": curr_price,
                                        "entry": entry_price,
                                        "change": round(chg, 2)
                                    }
                        except Exception as pe:
                            print(f"Backtest error for {ticker}: {pe}")

                    data["recent_analysis"].append({
                        "ticker": ticker,
                        "decision": decision,
                        "score": round(float(score), 2) if score is not None else 0.0,
                        "time": date_raw,
                        "report_url": report_path,
                        "performance": perf,
                        "targets": { "tp": tp, "sl": sl, "watch": watch, "entry": entry }
                    })
                    audit_map[ticker] = True
        except Exception as e:
            print(f"Error reading history.json: {e}")

    # Fallback: Scan reports/ for files not in history
    try:
        report_files = glob.glob(os.path.join(REPORTS_DIR, "*_*.*"))
        for rep in sorted(report_files, reverse=True):
            fname = os.path.basename(rep)
            if "_" in fname:
                parts = fname.split("_")
                t_part = parts[1].split(".")[0]
                if t_part not in audit_map and len(t_part) <= 5 and t_part.isupper():
                    d_part = parts[0]
                    data["recent_analysis"].append({
                        "ticker": t_part,
                        "decision": "ARCHIVE",
                        "score": 0.0,
                        "time": f"{d_part[:4]}-{d_part[4:6]}-{d_part[6:8]}",
                        "report_url": os.path.join('reports', fname)
                    })
                    audit_map[t_part] = True
    except Exception as e:
        print(f"Error scanning reports folder: {e}")

    # 1. Load Sector Data (Market Pulse)
    latest_sector = get_latest_file(os.path.join(SECTOR_LOGS, "*_sector_intel.json"))
    if latest_sector:
        try:
            with open(latest_sector, 'r') as f:
                s_data = json.load(f)
                data["market"]["regime"] = s_data.get("market_regime", "UNKNOWN")
                data["market"]["fear_greed"] = s_data.get("political_risk_summary", {}).get("fear_greed_index", 50)
                data["market"]["themes"] = s_data.get("actionable_themes", [])
                data["market"]["hot_sectors"] = s_data.get("summary", {}).get("hot_sectors", [])
                data["market"]["notes"] = s_data.get("session_notes", "")
        except Exception as e:
            print(f"Error reading sector log: {e}")

    # 3. Load News Data
    latest_news_files = sorted(glob.glob(os.path.join(NEWS_LOGS, "*_digest.json")), reverse=True)
    for news_file in latest_news_files[:3]: # Look at last 3 days of digests
        try:
            with open(news_file, 'r') as f:
                n_data = json.load(f)
                file_date = n_data.get("timestamp", "Unknown")[:10]
                for v in n_data.get("verdicts", []):
                    # v.get("affected_sectors") is a list of objects, we need the names
                    sector_names = [s.get("sector", "Unknown") for s in v.get("affected_sectors", [])]
                    data["news"].append({
                        "headline": v.get("headline"),
                        "impact": v.get("verdict", "NEUTRAL").lower(),
                        "score": v.get("net_impact_score"),
                        "date": file_date,
                        "sectors": sector_names
                    })
        except Exception as e:
            print(f"Error reading news log {news_file}: {e}")

    # Write Output
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"Bridge completed. Data synced to {OUTPUT_FILE}")

if __name__ == "__main__":
    run_bridge()
