import sys
import os
import requests
import json
import yfinance as yf
from datetime import datetime

FMP_API_KEY = os.environ.get("FMP_API_KEY")

def get_sector_info(ticker):
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        return {
            "sector": info.get("sector"),
            "industry": info.get("industry"),
            "longName": info.get("longName"),
            "summary": info.get("longBusinessSummary")
        }
    except Exception as e:
        return {"error": str(e)}

def get_fmp_supply_chain(ticker):
    if not FMP_API_KEY:
        return None
    
    # Try fetching supply chain from FMP (V4 endpoints)
    results = {"suppliers": [], "customers": []}
    
    # Note: These endpoints might require premium FMP plans. 
    # If not accessible, it will return 403 or empty.
    try:
        # Suppliers
        resp_s = requests.get(f"https://financialmodelingprep.com/api/v4/supplier-list?symbol={ticker}&apikey={FMP_API_KEY}")
        if resp_s.status_code == 200:
            results["suppliers"] = resp_s.json()
            
        # Customers
        resp_c = requests.get(f"https://financialmodelingprep.com/api/v4/customer-list?symbol={ticker}&apikey={FMP_API_KEY}")
        if resp_c.status_code == 200:
            results["customers"] = resp_c.json()
            
    except Exception as e:
        results["error"] = f"FMP Error: {str(e)}"
        
    return results

def main():
    if len(sys.argv) < 2:
        print("Usage: python3 chain_mapper.py <TICKER>")
        sys.exit(1)
        
    ticker = sys.argv[1].upper()
    print(f"--- Analyzing Supply Chain for {ticker} ---")
    
    info = get_sector_info(ticker)
    print(f"Company: {info.get('longName')} | Sector: {info.get('sector')}")
    
    chain = get_fmp_supply_chain(ticker)
    
    # Format and Output
    output = {
        "ticker": ticker,
        "profile": info,
        "supply_chain": chain,
        "analyzed_at": datetime.now().isoformat()
    }
    
    # If FMP has no data, suggest web search pattern for the AI agent
    if not chain or (not chain.get("suppliers") and not chain.get("customers")):
        print("\n[!] No structured supply chain data found in FMP. Fallback to Web Search required.")
        print(f"Search Prompt: 'Who are the major suppliers and customers of {ticker} in {datetime.now().year}?'")
    else:
        print(f"\nFound {len(chain.get('suppliers', []))} suppliers and {len(chain.get('customers', []))} customers via FMP.")
    
    # Write to cache
    cache_path = f"skills/supply-chain-event-analyst/cache/{ticker}_chain.json"
    with open(cache_path, "w") as f:
        json.dump(output, f, indent=2)
    print(f"\n[wrote] {cache_path}")

if __name__ == "__main__":
    main()
