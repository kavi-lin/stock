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

    // ── Breadth page tooltips ──────────────────────────────────────
    tooltips: {
      // ── Breadth analyzer components ────
      breadth_level_trend:    "廣度水平趨勢：追蹤 S&P 500 中有多少比例的股票高於其 8 週移動平均線，並監測此比例的趨勢方向。數值高（>60%）代表廣泛多頭參與；數值下滑代表廣度收縮，不宜激進做多。",
      ma_crossover:           "均線交叉：比較廣度的短期均線（8MA）與長期均線（200MA）。8MA 高於 200MA = 健康多頭環境；反之為結構性弱勢，代表多數股票中長期趨勢向下。",
      cycle_position:         "週期位置：利用廣度指標評估市場目前處於週期的哪個階段。從極端低點（底部）反彈是最佳進場時機；接近峰值時需開始保護利潤；中間段則維持標準操作。",
      bearish_signal:         "空頭信號：當廣度指標觸發明確的空頭條件（廣度大幅惡化並突破關鍵閾值）時啟動。信號啟動建議降低倉位上限、緊縮止損位置。",
      historical_percentile:  "歷史百分位：將當前廣度分數與歷史數據比較。低於 30th percentile = 接近歷史最差水準，需大幅保守操作；高於 70th percentile = 廣度健康，市場參與度廣泛。",
      divergence:             "背離偵測：偵測指數價格與市場廣度的背離。指數創高但廣度下降（少數大型股撐盤）是市場可能即將見頂的早期預警訊號。",
      overall_breadth:        "整體廣度：整體市場廣度的綜合評估，反映多數股票的健康程度。數值高代表廣泛多頭參與，低代表市場下行壓力普遍。",
      sector_participation:   "產業參與度：各產業板塊參與當前漲勢的廣度。參與度低（漲勢集中少數板塊）代表市場基礎脆弱，風險較高。",
      momentum:               "動量強度：當前市場趨勢的速度與力道。動量強代表趨勢可靠；動量弱代表趨勢可能即將轉折，需提高警覺。",
      mean_reversion_risk:    "均值回歸風險：市場短期過度偏離均值的程度。風險高代表可能即將出現修正；數值本身為雙向風險，過高過低均代表回歸壓力。",
      // ── Breadth stat cards ────
      stat_breadth_score:     "廣度綜合分數（0-100）：由 market-breadth-analyzer 計算，整合 6 個子指標。0-30 危險、30-55 弱化、55-80 健康、80+ 強勢。來源：TraderMonty CSV，不依賴付費 API。",
      stat_8ma_200ma:         "廣度移動平均：8MA 為近期有多少比例股票處於上升趨勢（短期）；200MA 為長期基準值。8MA > 200MA = 多頭環境。數值如 0.519 代表約 51.9% 的股票滿足條件。",
      stat_cycle_phase:       "市場週期階段：Early（早期/底部）= 最佳進場時機；Mid（中段）= 標準操作；Late（晚期）= 開始減倉保護利潤。週期判斷基於廣度的歷史百分位與趨勢方向。",
      stat_exposure_ceiling:  "建議最高倉位上限：根據當前廣度分數計算的最高股票倉位建議。廣度越差上限越低（最低 20-40%），保護資本免受系統性下跌影響。此為上限參考，非目標倉位。",
      stat_regime_conf:       "數據品質：量化分析器能取得並計算的完整程度。Complete（6 組件全齊）= 高可靠性；Partial（4-5 組件）= 中等；Limited（<4 組件）= 低可靠性，解讀需謹慎。",
      // ── Warning flags ────
      Bearish_Signal_Active:      "空頭信號啟動：廣度指標已觸發明確空頭條件。建議：降低整體倉位上限、緊縮現有部位止損、暫停新的激進進場。",
      Below_200MA:                "廣度跌破 200MA：大多數股票已跌破其長期均線，市場進入結構性弱勢。技術反彈難以持續，不宜追漲；以防禦為主。",
      Low_Historical_Percentile:  "歷史低百分位：廣度低於歷史 30th percentile，接近歷史最差水準。代表此次弱勢程度高於歷史七成以上的時期，需高度謹慎。",
      Early_Warning_Divergence:   "早期背離預警：指數與廣度出現背離，市場可能正形成頂部。建議開始保護核心部位利潤，不宜追加曝險。",
      Critical_Zone:              "危險區（廣度 < 30）：廣度分數處於最低區間，多數股票均在下跌。歷史上常見於熊市中段；若同時出現底部訊號，也可能是反彈機會。",
      Weakening_Zone:             "弱化區（廣度 30-55）：廣度不足以支撐積極進攻。僅考慮最強領頭股的保守進場，不宜做多弱勢板塊。",
      Death_Cross_SP500:          "死亡交叉（S&P 500）：50MA 向下穿越 200MA，是中長期空頭確認訊號。歷史上死亡交叉後市場通常仍有進一步下行空間，直至出現 FTD 確認底部。",
      Extreme_Fear_Sentiment:     "極端恐慌情緒：VIX 或 Fear & Greed 指標達到極端恐慌水準。極端恐慌常見於市場底部附近，但也可能持續延伸。通常為逆向看多訊號，需配合 FTD 確認。",
      // ── FTD section ────
      ftd_state:         "市場狀態（O'Neil FTD 方法論）：CORRECTION = 修正中；RALLY_ATTEMPT = 反彈第 1 天已觸發；FTD_WINDOW = 第 4-7 天視窗（FTD 待確認）；FTD_CONFIRMED = 放量突破確認，可積極加碼；FTD_INVALIDATED = FTD 失效，需重新等待。",
      ftd_quality_score: "FTD 品質分數（0-100）：綜合評估 FTD 信號強度，包含放量幅度、均線排列、機構動向、成交量分佈。70+ 高品質可積極進場；40-70 謹慎進場；40 以下可靠性低。",
      ftd_exposure:      "FTD 曝險建議：根據 FTD 品質分數建議的初始進場倉位範圍。FTD 是進場起點而非滿倉信號，需隨後觀察出貨日與後續走勢再逐步加倉。",
      ftd_event:         "Follow-Through Day（FTD）：O'Neil 市場底部確認信號。條件：從反彈 Day 1 起算的第 4-7 天內，指數放量上漲 1.5%+ 且成交量高於前日。FTD 確認後可開始系統性積累。",
      ftd_swing_low:     "反彈基準低點：本次市場修正的最低收盤點，也是 Rally Day 1 的計算起點。若指數收盤跌破此低點，整個反彈嘗試重置歸零，需重新等待新的 Day 1。",
      ftd_post_health:   "Post-FTD 健康追蹤：FTD 確認後持續監測市場健康。出貨日達 5+ 天或 FTD 失效，代表底部反彈可能失敗，需再次轉為保守。",
      ftd_dist_days:     "出貨日（Post-FTD）：FTD 確認後機構大量賣出的天數。0-2 天正常；3-4 天需警覺；5+ 天代表機構開始退場，此次底部可能失敗。",
      ftd_power_trend:   "強力趨勢（Power Trend）：同時滿足三條件：①股價 > 21EMA、②21EMA > 50MA、③50MA 斜率向上。強力趨勢啟動代表最健康的多頭狀態，持倉信心最強。",
      ftd_invalidated:   "FTD 失效：已確認的 FTD 被後續走勢否定（跌破修正低點或出貨日過多）。FTD 失效後需重新等待新的底部確認訊號才可積極進場。",
      // ── Market Top section ────
      mt_score:          "市場頂部概率（O'Neil + Minervini + Monty 三框架）：0-20 正常；21-40 早期預警；41-60 風險升高；61-80 高概率頂部；81-100 頂部形成中。高分代表需收緊止損、保護利潤、暫停激進新進場，不代表立即崩跌。",
      mt_risk_budget:    "風險預算：根據頂部概率建議的最高股票倉位。分數越高，建議持現比例越高。此為動態上限——強勢個股可維持；弱勢持股應率先調整。",
      mt_data_quality:   "數據完整性：6 個評估組件中有多少組件具有有效數據。缺少 put/call 比率或 50DMA 廣度時，相關組件權重會自動重新分配給其他可用組件。",
      mt_ftd_monitor:    "頂部偵測器內建 FTD 監測（補充）：當頂部分數超過 40（橙色/紅色區），同時監測市場底部確認訊號（FTD）。主要 FTD 分析與品質評分請見上方 FTD Detector 區塊。",
      // ── Market Top components ────
      distribution_days:  "出貨日計數（權重 25% · O'Neil）：機構大量賣出的特徵日，指數下跌同時成交量高於前日。過去 25 個交易日出現 5 天以上為高可信度頂部警訊。分數越高代表出貨日越密集。",
      leading_stocks:     "領頭股健康度（權重 20% · Minervini）：追蹤最強勢主題 ETF 的技術狀況（相對強弱、均線位置、高低點結構）。市場頂部通常先從領頭股開始轉弱，早於大盤指數。",
      defensive_rotation: "防禦性輪動（權重 15% · Monty）：衡量資金從進攻性板塊（科技、消費、通訊）流向防禦性板塊（公用事業、必需消費品）的速度與幅度。資金大舉轉進防禦是頂部的典型跡象。",
      breadth_divergence: "廣度背離（權重 15%）：指數走高但高於 200MA 股票比例下降（少數大型股撐盤、多數個股走弱）。此「領頭羊效應」歷史上常出現在重要頂部之前。",
      index_technical:    "指數技術面（權重 15%）：評估 S&P 500 與 NASDAQ 的技術指標：距離歷史高點幅度、均線排列（200/50/21MA）、趨勢結構。技術面惡化是市場轉弱的直接反映。",
      sentiment:          "情緒與投機（權重 10%）：綜合 VIX（隱含波動率）、Put/Call 比率（恐懼貪婪）、VIX 期限結構（backwardation = 短期恐慌）。過度樂觀是反向警訊；極端恐慌則可能是底部訊號。",
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

    // ── Breadth page tooltips ──────────────────────────────────────
    tooltips: {
      // ── Breadth analyzer components ────
      breadth_level_trend:    "Breadth Level & Trend: Tracks the % of S&P 500 stocks above their 8-week moving average and monitors the trend direction. Readings above 60% indicate broad bullish participation. Declining readings signal contracting breadth — avoid aggressive positioning.",
      ma_crossover:           "MA Crossover: Compares the short-term breadth average (8MA) against the long-term baseline (200MA). 8MA above 200MA = healthy bull environment. When 8MA drops below 200MA, the majority of stocks are in structural downtrends.",
      cycle_position:         "Cycle Position: Uses breadth metrics to estimate the market's position in the cycle. Extreme lows (trough) offer the best entry opportunities. Near peaks, begin protecting profits. Mid-cycle favors standard position management.",
      bearish_signal:         "Bearish Signal: Activates when breadth breaches clearly bearish thresholds — significant deterioration or sustained readings in danger zones. When triggered, tighten stops and reduce maximum portfolio exposure.",
      historical_percentile:  "Historical Percentile: Ranks the current breadth score against historical readings. Below the 30th percentile means breadth is worse than 70% of all historical periods. Above the 70th percentile indicates healthy, broadly participating market conditions.",
      divergence:             "Divergence Detection: Flags when the index makes new highs while breadth (% of stocks above key averages) declines. This 'narrow market' condition — a few large caps carrying the index — has historically preceded major market tops.",
      overall_breadth:        "Overall Breadth: A composite measure of how broadly the market is participating in the current trend. High readings mean widespread bullish participation; low readings mean broad downside pressure.",
      sector_participation:   "Sector Participation: Measures how many sectors are actively participating in the rally. Narrow participation (1-2 leading sectors) indicates a fragile, concentrated advance with elevated risk.",
      momentum:               "Momentum Strength: Measures the speed and force of the current trend. Strong momentum validates trend reliability; weakening momentum warns of potential exhaustion ahead.",
      mean_reversion_risk:    "Mean Reversion Risk: Measures how far current conditions have deviated from the long-term mean in either direction. High risk suggests elevated snap-back probability — can apply to both overextended rallies and oversold conditions.",
      // ── Breadth stat cards ────
      stat_breadth_score:     "Composite Breadth Score (0-100): Calculated by market-breadth-analyzer integrating 6 sub-components. 0-30 = Danger; 30-55 = Weakening; 55-80 = Healthy; 80+ = Strong. Source: TraderMonty CSV — no paid API required.",
      stat_8ma_200ma:         "Breadth Moving Averages: 8MA tracks the recent % of stocks in uptrends (short-term); 200MA is the long-term baseline. 8MA > 200MA = bull environment. A value like 0.519 means ~51.9% of stocks satisfy the uptrend condition.",
      stat_cycle_phase:       "Market Cycle Phase: Early = best entry opportunity near a trough; Mid = standard position management; Late = begin profit protection. Phase is estimated from breadth's historical percentile rank and trend direction.",
      stat_exposure_ceiling:  "Exposure Ceiling: Maximum recommended equity exposure based on current breadth. Poor breadth → lower ceiling (min 20-40%) to protect capital from systemic downside. This is an upper limit, not a target allocation.",
      stat_regime_conf:       "Data Quality: How completely the quantitative analyzer computed all 6 breadth components. Complete (all 6) = high reliability; Partial (4-5) = moderate; Limited (<4) = interpret with caution.",
      // ── Warning flags ────
      Bearish_Signal_Active:      "Bearish Signal Active: Breadth has triggered clearly bearish conditions. Action: Reduce max portfolio exposure, tighten stops on existing positions, pause new aggressive entries.",
      Below_200MA:                "Below 200MA: The majority of stocks have broken below their long-term moving average — structural weakness. Technical rallies are unlikely to sustain; a defensive posture is warranted.",
      Low_Historical_Percentile:  "Low Historical Percentile: Current breadth is below the 30th percentile of all historical readings — worse than 70% of periods on record. Elevated caution and conservative allocation are appropriate.",
      Early_Warning_Divergence:   "Early Warning Divergence: The index and breadth are diverging — a potential early top formation signal. Begin protecting core position profits; avoid adding new exposure.",
      Critical_Zone:              "Critical Zone (breadth < 30): Breadth is in its lowest tier, indicating most stocks are declining. Historically appears mid-bear-market. Combined with other bottom signals it can also mark reversal opportunities.",
      Weakening_Zone:             "Weakening Zone (breadth 30-55): Breadth is insufficient for aggressive positioning. Only consider entries in the strongest leaders; avoid the weakest sectors entirely.",
      Death_Cross_SP500:          "Death Cross (S&P 500): The 50MA has crossed below the 200MA — a medium-to-long-term bearish confirmation. Markets typically see further downside after a Death Cross until a Follow-Through Day confirms a bottom.",
      Extreme_Fear_Sentiment:     "Extreme Fear: VIX or Fear & Greed has reached extreme fear levels. Extreme fear often appears near market bottoms but can persist. Generally a contrarian bullish signal — confirm with FTD before acting.",
      // ── FTD section ────
      ftd_state:         "Market State (O'Neil FTD Methodology): CORRECTION = declining; RALLY_ATTEMPT = Day 1 triggered; FTD_WINDOW = Days 4-7 (confirmation pending); FTD_CONFIRMED = high-volume breakout confirmed, systematic accumulation can begin; FTD_INVALIDATED = bottom failed, wait for a new signal.",
      ftd_quality_score: "FTD Quality Score (0-100): Evaluates the strength of the FTD signal: volume magnitude, MA positioning, institutional behavior, volume distribution. 70+ = high quality (aggressive entry); 40-70 = moderate (cautious); <40 = low reliability.",
      ftd_exposure:      "FTD Exposure Guidance: Recommended initial position size range based on FTD quality. FTD is a starting gun, not a signal to go fully invested — build gradually as the market proves itself with follow-through.",
      ftd_event:         "Follow-Through Day (FTD): O'Neil's market bottom confirmation. On Day 4-7 counting from Rally Day 1, the index gains ≥1.5% on higher volume than the prior day. FTD signals institutional buyers are returning — systematic accumulation can begin.",
      ftd_swing_low:     "Swing Low (Rally Base): The closing low that triggered the current rally attempt — the reference price for counting rally days. If the index closes below this level, the entire rally attempt resets to zero.",
      ftd_post_health:   "Post-FTD Health Tracking: Ongoing monitoring after FTD confirmation. Accumulating ≥5 distribution days or triggering invalidation means the bottom may have failed — return to a defensive posture.",
      ftd_dist_days:     "Post-FTD Distribution Days: Count of institutional heavy-selling days after FTD confirmation. 0-2 = normal; 3-4 = caution; 5+ = institutions are exiting and the bottom may be failing.",
      ftd_power_trend:   "Power Trend: All 3 conditions met: ① price > 21EMA, ② 21EMA > 50MA, ③ 50MA slope is rising. Power Trend represents the healthiest bull market condition — highest conviction for holding and adding to positions.",
      ftd_invalidated:   "FTD Invalidated: The confirmed FTD has been negated by subsequent market action (closing below the correction low or accumulating too many distribution days). Wait for a fresh bottom confirmation before re-engaging aggressively.",
      // ── Market Top section ────
      mt_score:          "Market Top Probability (O'Neil + Minervini + Monty): 0-20 Normal; 21-40 Early Warning; 41-60 Elevated Risk; 61-80 High Probability Top; 81-100 Top Formation. High score means tighten stops, protect profits, pause new aggressive entries — not an immediate crash call.",
      mt_risk_budget:    "Risk Budget: Maximum recommended equity exposure based on the composite top probability. Higher score = more cash recommended. Dynamic ceiling: strong leaders can be held; weak positions should be trimmed first.",
      mt_data_quality:   "Data Completeness: How many of 6 scored components have valid data. Missing put/call ratio or 50DMA breadth causes those components' weights to be redistributed to available ones — the composite score adjusts automatically.",
      mt_ftd_monitor:    "Built-in FTD Monitor (supplementary): When the top score exceeds 40 (Orange/Red zone), this tracker also watches for a market bottom confirmation signal (FTD). For primary FTD analysis with quality scoring, see the FTD Detector section above.",
      // ── Market Top components ────
      distribution_days:  "Distribution Day Count (25% weight · O'Neil): Days when the index falls while volume exceeds the prior day, signaling institutional selling. 5+ distribution days in 25 sessions is a high-confidence market top warning. Higher score = more distribution activity.",
      leading_stocks:     "Leading Stock Health (20% weight · Minervini): Tracks the technical condition of the strongest growth ETFs and leaders: relative strength, MA position, high/low structure. Markets typically top when leading stocks begin deteriorating before the index does.",
      defensive_rotation: "Defensive Sector Rotation (15% weight · Monty): Measures the speed and magnitude of capital flowing from offensive sectors (tech, discretionary, communications) into defensive sectors (utilities, staples, healthcare). Heavy defensive rotation is a classic topping signature.",
      breadth_divergence: "Breadth Divergence (15% weight): The index makes new highs while the % of stocks above the 200DMA declines — 'narrow leadership.' A few large-caps propping up the index while most stocks weaken has historically preceded major tops.",
      index_technical:    "Index Technical Condition (15% weight): Evaluates S&P 500 and NASDAQ health: distance from all-time high, moving average alignment (200/50/21MA), trend structure. Technical deterioration is the most direct reflection of weakening market internals.",
      sentiment:          "Sentiment & Speculation (10% weight): Combines VIX (implied volatility), Put/Call ratio (fear vs greed), and VIX term structure (backwardation = near-term panic). Extreme complacency is a contrarian warning; extreme fear can mark bottoms.",
    },
  },
};

window.i18n = i18n;
