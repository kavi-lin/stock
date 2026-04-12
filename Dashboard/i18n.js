const i18n = {
  zh: {
    // ── News page ──────────────────────────────────────────────────
    title: "新聞戰情室",
    sync: "同步資料",
    total: "新聞總數",
    bullish: "利多信號",
    bearish: "利空信號",
    binary: "二元風險",
    last_sync: "最後同步",
    no_data: "尚無符合條件的新聞快取資料",
    failed: "資料載入失敗",
    impact: "影響力評分",
    unknown: "未知",

    // ── Nav ────────────────────────────────────────────────────────
    nav: {
      dash:      "總體儀表板",
      watchlist: "進場雷達",
      breadth:   "市場廣度",
      sector:    "產業掃描",
      news:      "即時新聞",
      history:   "決策歷史",
      logs:      "系統日誌",
    },

    // ── Status / Decision ──────────────────────────────────────────
    status: {
      bullish: "利多", bearish: "利空", binary: "變數", neutral: "中性",
      EXECUTE: "執行建倉", CANCEL: "不予執行", ARCHIVE: "存檔觀察",
      HOLD: "持續觀望", BUY: "執行買入",
    },

    // ── Overview (index.html) ──────────────────────────────────────
    overview: {
      market_regime:  "市場體制",
      hot_themes:     "熱門主題",
      sentiment:      "情緒指標",
      recent_audit:   "最近審查個股",
      catalyst:       "市場催化劑",
      quick_launch:   "快速啟動引擎",
      launch_desc:    "輸入代碼進行自動分析",
      start_btn:      "開始分析",
      tbl_decision:   "決策",
      tbl_score:      "分數",
      tbl_time:       "時間",
      // Regime card extra
      breadth_score:  "廣度分數",
      uptrend_ratio:  "上升趨勢比例",
      cycle_phase:    "週期位置",
    },

    // ── Watchlist page ─────────────────────────────────────────────
    watchlist: {
      title:           "進場雷達",
      subtitle:        "Watch Radar",
      active_label:    "監控中",
      waiting_label:   "等待進場",
      avg_conf:        "平均信心",
      avg_rr:          "平均風報比",
      filter_all:      "全部",
      filter_active:   "進行中",
      filter_waiting:  "等待中",
      entry_triggers:  "進場觸發條件",
      key_risks:       "主要風險",
      view_report:     "查看報告",
      no_items:        "無符合條件的項目",
      model_score:     "模型分數",
      da_filed:        "反向論點已提交",
      horizon_label:   "持有週期",
      size_label:      "建議倉位",
      rr_label:        "風報比",
      conf_label:      "信心指數",
    },

    // ── Warning / Breadth (index.html) ────────────────────────────
    warnings: {
      banner_title:   "風險旗幟啟動",
      uptrend_label:  "上升趨勢比例",
      breadth_label:  "廣度分數",
      // Flag name translations
      flags: {
        Late_Cycle:             "晚期週期",
        High_Selectivity:       "高選股要求",
        Narrowing_Breadth:      "廣度收窄",
        Death_Cross_SP500:      "死亡交叉(S&P500)",
        Extreme_Fear_Sentiment: "極端恐慌情緒",
        Overbought:             "超買",
        Oversold:               "超賣",
        Mean_Reversion_Risk:    "均值回歸風險",
      },
    },

    // ── Binary Risks / Calendar ────────────────────────────────────
    calendar: {
      binary_risks_title: "近期二元風險",
      no_events:          "暫無即將到來的事件",
      today:              "今天",
      past:               "已過",
    },

    // ── Trump Signals ──────────────────────────────────────────────
    trump_signals: {
      title:     "政策交易信號",
      direction: { bullish: "利多", bearish: "利空", binary: "變數" },
    },

    // ── Sector page ────────────────────────────────────────────────
    sectors: {
      TECHNOLOGY: "科技", SEMICONDUCTORS: "半導體", SOFTWARE: "軟體服務",
      AIRLINES: "航空運輸", HEALTHCARE: "醫療保健", FINANCIALS: "金融服務",
      RETAIL: "零售消費", ENERGY: "能源", UTILITIES: "公用事業",
      INFRASTRUCTURE: "基礎設施", CYBERSECURITY: "網絡安全",
      OIL_GAS: "石油與天然氣", CONSUMER_DISCRETIONARY: "非必要消費",
      INDUSTRIALS: "工業製造", CONSUMER_STAPLES: "必需消費品",
      COMMUNICATION: "通訊服務", MATERIALS: "原物料",
      REAL_ESTATE: "房地產", COMMUNICATION_SERVICES: "通訊服務",
    },

    // ── Rotation signals ──────────────────────────────────────────
    rotation: {
      INFLOW:  "資金流入",
      OUTFLOW: "資金流出",
      NEUTRAL: "中性",
    },

    // ── Sentiment labels (shared) ──────────────────────────────────
    sentiment_labels: {
      bullish: "看多", bearish: "看空", neutral: "中性",
      heatmap_title:     "產業動量分布圖",
      strength_contrast: "相對強度對比",
      strategy_summary:  "產業策略摘要",
      tp: "止盈位", sl: "止損位", watch: "監測價", entry: "進場區間",
    },

    // ── Time horizon ──────────────────────────────────────────────
    horizon: { short: "短線", mid: "中線", long: "長線" },

    // ── Breadth page ───────────────────────────────────────────────
    breadth: {
      title:              "市場廣度雷達",
      subtitle:           "Market Breadth",
      breadth_score:      "廣度綜合分數",
      uptrend_ratio:      "上升趨勢比例",
      cycle_phase:        "週期位置",
      regime_conf:        "體制信心",
      exposure_ceiling:   "建議最高倉位",
      components_title:   "廣度分量分析",
      overall_breadth:    "整體廣度",
      sector_participation: "產業參與度",
      momentum:           "動量強度",
      mean_reversion_risk: "均值回歸風險",
      flags_title:        "風險旗幟",
      sector_uptrend:     "各產業上升趨勢比例",
      notes_title:        "分析師筆記",
      slope_rising:       "上升",
      slope_falling:      "下降",
      slope_flat:         "持平",
      score_label:        "分數",
      no_data:            "尚無廣度資料",
    },
  },

  // ═══════════════════════════════════════════════════════════════
  en: {
    // ── News page ──────────────────────────────────────────────────
    title: "News War Room",
    sync: "Sync Data",
    total: "Total News",
    bullish: "Bullish Signals",
    bearish: "Bearish Signals",
    binary: "Binary Risk",
    last_sync: "Last Sync",
    no_data: "No news cache data found",
    failed: "Failed to load data",
    impact: "Impact Score",
    unknown: "Unknown",

    // ── Nav ────────────────────────────────────────────────────────
    nav: {
      dash:      "Dashboard",
      watchlist: "Watch Radar",
      breadth:   "Market Breadth",
      sector:    "Sectors",
      news:      "News Feed",
      history:   "Audit History",
      logs:      "System Logs",
    },

    // ── Status / Decision ──────────────────────────────────────────
    status: {
      bullish: "Bullish", bearish: "Bearish", binary: "Binary", neutral: "Neutral",
      EXECUTE: "EXECUTE", CANCEL: "CANCEL", ARCHIVE: "ARCHIVE",
      HOLD: "HOLD", BUY: "BUY",
    },

    // ── Overview (index.html) ──────────────────────────────────────
    overview: {
      market_regime:  "Market Regime",
      hot_themes:     "Hot Themes",
      sentiment:      "Sentiment Index",
      recent_audit:   "Recent Audits",
      catalyst:       "Market Catalysts",
      quick_launch:   "Quick Launch",
      launch_desc:    "Enter ticker for analysis",
      start_btn:      "Launch Analysis",
      tbl_decision:   "Decision",
      tbl_score:      "Score",
      tbl_time:       "Time",
      breadth_score:  "Breadth Score",
      uptrend_ratio:  "Uptrend Ratio",
      cycle_phase:    "Cycle Phase",
    },

    // ── Watchlist page ─────────────────────────────────────────────
    watchlist: {
      title:           "Watch Radar",
      subtitle:        "進場雷達",
      active_label:    "Active / Monitoring",
      waiting_label:   "Waiting Entry",
      avg_conf:        "Avg Confidence",
      avg_rr:          "Avg R/R Ratio",
      filter_all:      "ALL",
      filter_active:   "ACTIVE",
      filter_waiting:  "WAITING",
      entry_triggers:  "Entry Triggers",
      key_risks:       "Key Risks",
      view_report:     "View Report",
      no_items:        "No items match this filter.",
      model_score:     "Model Score",
      da_filed:        "DA Filed",
      horizon_label:   "Horizon",
      size_label:      "Size",
      rr_label:        "R/R",
      conf_label:      "Confidence",
    },

    // ── Warning / Breadth (index.html) ────────────────────────────
    warnings: {
      banner_title:   "Risk Flags Active",
      uptrend_label:  "Uptrend Ratio",
      breadth_label:  "Breadth Score",
      flags: {
        Late_Cycle:             "Late Cycle",
        High_Selectivity:       "High Selectivity",
        Narrowing_Breadth:      "Narrowing Breadth",
        Death_Cross_SP500:      "Death Cross (S&P500)",
        Extreme_Fear_Sentiment: "Extreme Fear",
        Overbought:             "Overbought",
        Oversold:               "Oversold",
        Mean_Reversion_Risk:    "Mean Reversion Risk",
      },
    },

    // ── Binary Risks / Calendar ────────────────────────────────────
    calendar: {
      binary_risks_title: "Upcoming Binary Risks",
      no_events:          "No upcoming events.",
      today:              "TODAY",
      past:               "PAST",
    },

    // ── Trump Signals ──────────────────────────────────────────────
    trump_signals: {
      title:     "Policy Trade Signals",
      direction: { bullish: "Bullish", bearish: "Bearish", binary: "Binary" },
    },

    // ── Sector page ────────────────────────────────────────────────
    sectors: {
      TECHNOLOGY: "Technology", SEMICONDUCTORS: "Semiconductors", SOFTWARE: "Software",
      AIRLINES: "Airlines", HEALTHCARE: "Healthcare", FINANCIALS: "Financials",
      RETAIL: "Retail", ENERGY: "Energy", UTILITIES: "Utilities",
      INFRASTRUCTURE: "Infrastructure", CYBERSECURITY: "Cybersecurity",
      OIL_GAS: "Oil & Gas", CONSUMER_DISCRETIONARY: "Consumer Discretionary",
      INDUSTRIALS: "Industrials", CONSUMER_STAPLES: "Consumer Staples",
      COMMUNICATION: "Communication", MATERIALS: "Materials",
      REAL_ESTATE: "Real Estate", COMMUNICATION_SERVICES: "Communication Svcs",
    },

    // ── Rotation signals ──────────────────────────────────────────
    rotation: {
      INFLOW:  "Inflow",
      OUTFLOW: "Outflow",
      NEUTRAL: "Neutral",
    },

    // ── Sentiment labels (shared) ──────────────────────────────────
    sentiment_labels: {
      bullish: "Bullish", bearish: "Bearish", neutral: "Neutral",
      heatmap_title:     "Sector Momentum Heatmap",
      strength_contrast: "Relative Strength Contrast",
      strategy_summary:  "Sector Strategy Summary",
      tp: "Take Profit", sl: "Stop Loss", watch: "Watch Price", entry: "Entry Zone",
    },

    // ── Time horizon ──────────────────────────────────────────────
    horizon: { short: "Short", mid: "Mid-term", long: "Long-term" },

    // ── Breadth page ───────────────────────────────────────────────
    breadth: {
      title:              "Market Breadth Radar",
      subtitle:           "市場廣度雷達",
      breadth_score:      "Breadth Score",
      uptrend_ratio:      "Uptrend Ratio",
      cycle_phase:        "Cycle Phase",
      regime_conf:        "Regime Confidence",
      exposure_ceiling:   "Exposure Ceiling",
      components_title:   "Breadth Components",
      overall_breadth:    "Overall Breadth",
      sector_participation: "Sector Participation",
      momentum:           "Momentum",
      mean_reversion_risk: "Mean Reversion Risk",
      flags_title:        "Risk Flags",
      sector_uptrend:     "Per-Sector Uptrend Ratio",
      notes_title:        "Analyst Notes",
      slope_rising:       "Rising",
      slope_falling:      "Falling",
      slope_flat:         "Flat",
      score_label:        "Score",
      no_data:            "No breadth data available",
    },
  },
};

window.i18n = i18n;
