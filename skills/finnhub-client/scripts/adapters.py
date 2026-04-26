"""
Finnhub → FMP-shape adapters.

Translate Finnhub raw responses into FMP-compatible payloads so downstream
skills can swap providers without changing call sites.

Adapters are best-effort. Lossy or shape-mismatched fields are flagged in
docstrings. Every adapted payload includes "_source": "finnhub" for trace.
"""
import datetime


def quote_to_fmp(finnhub_quote, ticker):
    """
    Finnhub /quote → FMP /quote (single-symbol list).

    Finnhub: {c, h, l, o, pc, t, v?}
    FMP    : [{symbol, price, change, changesPercentage, dayLow, dayHigh,
              open, previousClose, timestamp, volume, ...}]
    """
    if not finnhub_quote or finnhub_quote.get("c") in (None, 0):
        return None
    c = finnhub_quote["c"]
    pc = finnhub_quote.get("pc") or c
    change = c - pc
    pct = (change / pc * 100) if pc else 0.0
    return [{
        "symbol": ticker.upper(),
        "price": c,
        "change": change,
        "changesPercentage": pct,
        "dayLow": finnhub_quote.get("l"),
        "dayHigh": finnhub_quote.get("h"),
        "open": finnhub_quote.get("o"),
        "previousClose": pc,
        "timestamp": finnhub_quote.get("t"),
        "volume": finnhub_quote.get("v"),
        "_source": "finnhub",
    }]


def candle_to_fmp_historical(candle, ticker):
    """
    Finnhub /stock/candle → FMP /historical-price-full.

    Finnhub: {c:[...], h:[...], l:[...], o:[...], t:[...], v:[...], s:"ok"}
    FMP    : {symbol, historical: [{date, open, high, low, close, volume}]}
            (most-recent first)
    """
    if not candle or candle.get("s") != "ok":
        return None
    closes = candle.get("c") or []
    highs = candle.get("h") or []
    lows = candle.get("l") or []
    opens = candle.get("o") or []
    times = candle.get("t") or []
    vols = candle.get("v") or []
    n = len(closes)
    historical = []
    for i in range(n):
        date = datetime.datetime.utcfromtimestamp(times[i]).strftime("%Y-%m-%d")
        historical.append({
            "date": date,
            "open": opens[i] if i < len(opens) else None,
            "high": highs[i] if i < len(highs) else None,
            "low": lows[i] if i < len(lows) else None,
            "close": closes[i],
            "volume": vols[i] if i < len(vols) else None,
        })
    historical.reverse()
    return {
        "symbol": ticker.upper(),
        "historical": historical,
        "_source": "finnhub",
    }


def profile_to_fmp(profile):
    """
    Finnhub /stock/profile2 → FMP /profile.

    Caveat: Finnhub returns marketCapitalization and shareOutstanding in
    millions; FMP uses absolute values. Adapter scales by 1e6.
    Caveat: Finnhub has finnhubIndustry but no separate sector — adapter
    duplicates the value into both fields.
    """
    if not profile:
        return None
    mcap_m = profile.get("marketCapitalization")
    shares_m = profile.get("shareOutstanding")
    return {
        "symbol": profile.get("ticker"),
        "companyName": profile.get("name"),
        "industry": profile.get("finnhubIndustry"),
        "sector": profile.get("finnhubIndustry"),
        "country": profile.get("country"),
        "currency": profile.get("currency"),
        "exchange": profile.get("exchange"),
        "ipoDate": profile.get("ipo"),
        "mktCap": (mcap_m * 1_000_000) if mcap_m else None,
        "sharesOutstanding": (shares_m * 1_000_000) if shares_m else None,
        "website": profile.get("weburl"),
        "image": profile.get("logo"),
        "_source": "finnhub",
    }


def metric_to_fmp_key_metrics(metric):
    """
    Finnhub /stock/metric → FMP /key-metrics (single-period list).

    Finnhub returns {metric: {...100+ keys...}, series: {...}}.
    FMP returns array of period snapshots; adapter returns list of 1
    representing the latest TTM/annual snapshot.
    """
    if not metric or not metric.get("metric"):
        return None
    m = metric["metric"]
    return [{
        "symbol": metric.get("symbol"),
        "peRatio": m.get("peTTM") or m.get("peNormalizedAnnual"),
        "pegRatio": m.get("pegRatioTTM") or m.get("pegRatio5Y"),
        "priceToBookRatio": m.get("pbAnnual") or m.get("pbQuarterly"),
        "priceToSalesRatio": m.get("psTTM"),
        "dividendYield": m.get("dividendYieldIndicatedAnnual"),
        "roe": m.get("roeTTM") or m.get("roeRfy"),
        "roa": m.get("roaTTM") or m.get("roaRfy"),
        "debtToEquity": m.get("totalDebt/totalEquityAnnual"),
        "currentRatio": m.get("currentRatioAnnual"),
        "epsTTM": m.get("epsTTM"),
        "freeCashFlowPerShare": m.get("freeCashFlowPerShareTTM"),
        "marketCap": m.get("marketCapitalization"),
        "_source": "finnhub",
    }]


def financials_to_fmp_income(financials):
    """
    Finnhub /stock/financials-reported → FMP /income-statement (lossy).

    Maps top-line items only: revenue, EPS, operating income, net income.
    For deeper analysis (margins, segment data, working capital), use FMP
    /income-statement directly.
    """
    if not financials or not financials.get("data"):
        return []
    out = []
    for entry in financials["data"]:
        report = entry.get("report") or {}
        ic = report.get("ic") or [] if isinstance(report, dict) else []

        def get_concept(suffix):
            for item in ic:
                concept = (item.get("concept") or "")
                if concept.endswith(suffix):
                    return item.get("value")
            return None

        out.append({
            "symbol": entry.get("symbol"),
            "date": entry.get("endDate"),
            "period": entry.get("quarter") or entry.get("year"),
            "revenue": get_concept("Revenues") or get_concept("SalesRevenueNet"),
            "operatingIncome": get_concept("OperatingIncomeLoss"),
            "netIncome": get_concept("NetIncomeLoss"),
            "eps": get_concept("EarningsPerShareBasic"),
            "epsdiluted": get_concept("EarningsPerShareDiluted"),
            "_source": "finnhub",
            "_lossy": True,
        })
    return out
