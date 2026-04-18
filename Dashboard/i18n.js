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
      decisions: "決策中心",
      sector:    "產業掃描",
      news:      "即時新聞",
      logs:      "系統日誌",
    },

    // ── Status / Decision ──────────────────────────────────────────
    status: {
      bullish: "利多", bearish: "利空", binary: "變數", neutral: "中性",
      EXECUTE: "執行建倉", CANCEL: "不予執行", ARCHIVE: "存檔觀察",
      HOLD: "持續觀望", BUY: "執行買入", SELL: "執行賣出",
      STAGED: "分批建倉", STAGED_ENTRY: "分批進場", STAGED_EXIT: "分批出場",
    },

    // ── Positions form + table (zh) ────────────────────────────
    positions: {
      add_btn: "+ 新增持倉",
      modal_title: "新增持倉記錄",
      ticker_placeholder: "例：MU",
      price_placeholder: "例：382.50",
      shares_placeholder: "例：50",
      notes_placeholder: "備註，例如 V4.6 STAGED 激進建倉",
      ticker: "代號", entry_date: "進場日期", entry_price: "進場價格",
      shares: "股數", track: "軌道", status: "狀態", notes: "備註",
      track_aggressive: "積極", track_conservative: "保守", track_manual: "手動",
      status_open: "持有中", status_trimmed: "部分出場", status_closed: "已平倉",
      submit: "儲存", cancel: "取消",
      live_pos: "已持倉", avg_cost: "均價", shares_lbl: "股",
      upl: "浮盈", lots: "筆次", delete: "刪除",
      // Close modal
      close_btn: "平倉", close_modal_title: "平倉持倉",
      exit_date: "出場日期", exit_price: "出場價格",
      closed_shares: "出場股數", close_partial_hint: "可少於總股數做部分出場",
      realized_pl: "已實現損益", confirm_btn: "確認",
      partial_exit: "部分出場", full_close: "全部平倉",
      // Positions tab table
      portfolio_title: "投資組合",
      total_cost: "總成本",
      total_upl: "未實現損益",
      total_realized: "已實現損益",
      status_col: "狀態",
      cost_col: "成本",
      current: "現價",
      pct_col: "%",
      show_closed: "顯示已平倉",
      no_positions: "尚未記錄任何持倉。點擊「新增持倉」開始追蹤。",
    },

    // ── Overview (index.html) ──────────────────────────────────────
    overview: {
      market_regime:  "市場體制",
      hot_themes:     "熱門主題",
      sentiment:      "情緒指標",
      recent_audit:   "最近審查個股",
      catalyst:       "市場催化劑",
      quick_launch:   "快速啟動引擎",
      preflight_btn:  "盤前檢查",
      preflight_title: "盤前狀態檢查",
      launch_desc:    "輸入代碼進行自動分析",
      start_btn:      "開始分析",
      tbl_decision:   "決策",
      tbl_score:      "分數",
      tbl_time:       "時間",
      // Regime card extra
      breadth_score:  "廣度分數",
      uptrend_ratio:  "上升趨勢比例",
      cycle_phase:    "週期位置",
      // Header
      market_status:       "市場狀態",
      operator:            "操作員",
      // Conviction hero
      conviction_title:    "市場信心指標",
      // Action Posture card
      action_posture:      "操作方向儀",
      action_posture_desc: "根據體制 + 廣度 + 旗幟，決定倉位與激進程度",
      regime_label:        "市場體制",
      exposure_label:      "最高倉位上限",
      exposure_hint:       "各訊號建議最保守值",
      // Misc
      view_all:            "查看全部",
      no_flags:            "無活躍風險旗幟",
      flags_active:        "個風險旗幟啟動",
      backtest_pl:         "歷史回測",
    },

    // ── Signals / Conviction (index.html dynamic) ─────────────────
    signals: {
      conviction: {
        STRONG_BULL: "強力多頭", BULLISH: "偏多", MIXED: "中性偏多",
        CAUTIOUS: "謹慎觀望", BEARISH: "偏空", STRONG_BEAR: "強力空頭",
      },
      components: {
        ftd: "FTD 信號", sentiment: "情緒逆向",
        top_risk: "頂部風險", uptrend: "上升趨勢",
      },
      drivers: {
        ftd: "FTD", sentiment: "情緒逆向",
        top_risk: "頂部風險", uptrend: "上升趨勢",
      },
      cards: {
        ftd: "FTD 信號", top_risk: "頂部風險",
        sentiment: "市場情緒", uptrend: "上升趨勢%",
      },
      ftd_states: {
        FTD_CONFIRMED: "FTD 已確認", FTD_WINDOW: "FTD 視窗期",
        FTD_INVALIDATED: "FTD 已失效", RALLY_ATTEMPT: "反彈嘗試中",
        CORRECTION: "修正中", RALLY_FAILED: "反彈失敗", default: "無信號",
      },
      top_zones: { Green: "安全", Yellow: "早期預警", Orange: "注意", Red: "高風險" },
      fg_labels: {
        "Extreme Fear": "極端恐慌", Fear: "恐慌", Neutral: "中性",
        Greed: "貪婪", "Extreme Greed": "極度貪婪",
        contrarian_suffix: "（逆向）",
      },
      uptrend_labels: { healthy: "趨勢健康", neutral: "趨勢中性", weak: "趨勢偏弱" },
      regime: {
        RISK_ON: "偏多｜積極操作", RISK_OFF: "防禦｜降低曝險",
        VOLATILE: "震盪｜縮小規模", NEUTRAL: "中性｜均衡配置",
      },
    },

    // ── Sector page (zh) ───────────────────────────────────────────
    sector_page: {
      title: "產業情報",
      refresh: "更新分析",
      // Pills
      pill_regime: "市場體制",
      pill_breadth: "廣度分數",
      pill_ftd: "FTD 狀態",
      pill_exposure: "曝險上限",
      pill_fg: "恐慌貪婪",
      pill_cycle: "市場週期",
      pill_vix: "VIX",
      // FTD state labels
      ftd_confirmed: "✓ 確認",
      // Binary risk alert
      binary_alert: "⚡ 48h 內二元風險",
      // PS handoff
      handoff_title: "投資策略長 · 最終裁決",
      // Verdict groups
      hot_label: "積極",
      warm_label: "中性",
      cold_label: "保守",
      avoid_label: "迴避",
      sectors_unit: "板塊",
      // Three-signal synthesis panel
      three_signal_title: "三訊號合成",
      synthesized_ceiling: "合成曝險上限",
      synth_subtitle: "min(Breadth, FTD, Top) — 取最保守",
      signal_conflict: "訊號衝突 — 以保守上限為準",
      signal_breadth: "廣度",
      signal_ftd: "FTD",
      signal_top: "頂部風險",
      quality_label: "品質",
      exposure_label: "曝險",
      budget_label: "預算",
      cap_label: "上限",
      // Catalyst / political signals
      catalyst_title: "新聞與政策訊號",
      named_targets_today: "今日點名目標",
      no_catalyst: "無政策訊號偵測",
      // Divergence
      divergence_title: "背離監控",
      no_divergence: "無活躍背離",
      action_reduce: "↓ 降低曝險",
      action_monitor: "👁 持續監控",
      // Themes
      themes_title: "主題線索",
      no_themes: "無活躍主題",
      // Overbought
      overbought_label: "⚠ 超買",
      da_challenge: "反方論點",
      uptrend_label_card: "上升率",
      // Score-component abbreviations
      comp_bm: "廣度",
      comp_th: "主題",
      comp_nc: "新聞",
      comp_rs: "輪動",
    },

    // ── Watchlist page ─────────────────────────────────────────────
    watchlist: {
      title:              "決策中心",
      subtitle:           "Decisions",
      active_label:       "監控中",
      waiting_label:      "等待進場",
      avg_conf:           "平均信心",
      avg_rr:             "平均風報比",
      filter_all:         "全部",
      filter_active:      "進行中",
      filter_waiting:     "等待中",
      filter_historical:  "歷史",
      filter_positions:   "持倉",
      entry_triggers:  "進場觸發條件",
      reeval_triggers: "觀察觸發條件",
      key_risks:       "主要風險",
      view_report:     "查看報告",
      flash_btn:       "FLASH",
      flash_toast:     "<span class=\"text-emerald-400 font-bold\">「新聞分析 FLASH {TICKER} 近期動態」</span><br>已複製到剪貼簿，貼回 Claude Code 執行針對 {TICKER} 的單股 FLASH 新聞分析",
      no_items:        "無符合條件的項目",
      model_score:     "模型分數",
      da_filed:        "反向論點已提交",
      horizon_label:   "持有週期",
      size_label:      "建議倉位",
      rr_label:        "風報比",
      conf_label:      "信心指數",
      refresh_btn:     "重新分析",
      history_title:   "歷次分析",
      history_empty:   "沒有歷史分析記錄",
    },

    // ── Warning / Breadth (index.html) ────────────────────────────
    warnings: {
      banner_title:   "風險旗幟啟動",
      uptrend_label:  "上升趨勢比例",
      breadth_label:  "廣度分數",
      // Flag name translations
      flags: {
        Late_Cycle:                 "晚期週期",
        High_Selectivity:           "高選股要求",
        Narrowing_Breadth:          "廣度收窄",
        Death_Cross_SP500:          "死亡交叉(S&P500)",
        Extreme_Fear_Sentiment:     "極端恐慌情緒",
        Overbought:                 "超買",
        Oversold:                   "超賣",
        Mean_Reversion_Risk:        "均值回歸風險",
        Bearish_Signal_Active:      "空頭信號啟動",
        Below_200MA:                "廣度跌破200均線",
        Low_Historical_Percentile:  "歷史低百分位",
        Weakening_Zone:             "弱化區間（廣度30-55）",
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

    // ── News page extra strings ────────────────────────────────────
    news_page: {
      bull_label:       "利多論點",
      bear_label:       "利空論點",
      arbiter_prefix:   "仲裁判定 → ",
      binary_badge:     "⚡ 二元風險",
      pending_label:    "待審核",
      reviewed_label:   "已審核",
      review_btn:       "送審",
      review_toast:     "<span class=\"text-emerald-400 font-bold\">審核 prompt</span> 已複製到剪貼簿，<br>貼回 Claude Code 執行正式委員會審核",
      filter_all:       "全部",
      filter_reviewed:  "已審核 ✅",
      filter_pending:   "待審核 ⏳",
      copy_prompt:      "複製 Prompt",
      retry_btn:        "重試",
      loading:          "資料載入中...",
      last_sync_none:   "最後同步：尚未",
      digest_toast:     "資料已重新載入。<br><span class=\"text-emerald-400 font-bold\">「新聞分析 DIGEST」</span> 已複製到剪貼簿，<br>貼回 Claude Code 執行完整 DIGEST 更新（需 1–2 分鐘）",
      news_type: {
        fomc:            "FOMC",
        earnings:        "財報",
        geopolitical:    "地緣政治",
        macro_data:      "總經數據",
        political:       "政治事件",
        sector_specific: "產業事件",
      },
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

    // ── Sector page (sector.html / page-sector.js) ────────────────
    sector_page: {
      // Header block titles
      binary_alert:        "⚡ 48 小時內二元風險",
      handoff_title:       "Portfolio Strategist · 最終判決",
      three_signal_title:  "三訊號合成",
      catalyst_title:      "新聞 / 政治訊號",
      divergence_title:    "背離觀察",
      themes_title:        "可行主題",
      named_targets_today: "今日點名標的",
      // Status pill labels
      pill_regime:         "市場體制",
      pill_breadth:        "廣度分數",
      pill_ftd:             "FTD 狀態",
      pill_exposure:       "曝險上限",
      pill_fg:             "恐懼貪婪",
      pill_cycle:          "週期位置",
      pill_vix:            "波動指數",
      // FTD + sector card
      ftd_confirmed:       "✓ 已確認",
      sectors_unit:        "個產業",
      uptrend_label_card:  "上升比例",
      overbought_label:    "⚠ 超買",
      da_challenge:        "反方挑戰",
      // Score component codes (kept short to fit the card)
      comp_bm:             "廣度",
      comp_th:             "主題",
      comp_nc:             "新聞",
      comp_rs:             "輪動",
      // Three-signal synthesis
      signal_breadth:      "市場廣度",
      signal_ftd:          "FTD 訊號",
      signal_top:          "頂部風險",
      cap_label:           "上限",
      quality_label:       "品質",
      exposure_label:      "曝險",
      budget_label:        "預算",
      synthesized_ceiling: "綜合曝險上限",
      synth_subtitle:      "取 min(廣度, FTD, 頂部) — 最保守",
      signal_conflict:     "訊號衝突 — 採用最保守上限",
      // Empty / action placeholders
      no_catalyst:         "目前無政治訊號",
      no_divergence:       "目前無活躍背離",
      no_themes:           "目前無熱門主題",
      action_reduce:       "↓ 降低曝險",
      action_monitor:      "👁 持續監控",
      // Scan modal
      scan_modal_title:    "產業掃描執行中",
      scan_confirm:        "即將觸發 Claude 執行完整產業掃描 protocol。\n\n預計 3–5 分鐘，會消耗 API tokens。\n\n確認執行？",
      scan_running:        "執行中",
      scan_done:           "完成",
      scan_error:          "錯誤",
      scan_cancelled:      "已取消",
      scan_log_title:      "即時日誌",
      scan_cancel_btn:     "取消",
      scan_close_btn:      "關閉",
      scan_start_failed:   "啟動失敗",
      scan_in_progress:    "已有掃描在執行",
      scan_expand:         "展開",
      scan_minimize:       "收合",
      scan_latest:         "最新事件",
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
      decisions: "Decisions",
      sector:    "Sectors",
      news:      "News Feed",
      logs:      "System Logs",
    },

    // ── Status / Decision ──────────────────────────────────────────
    status: {
      bullish: "Bullish", bearish: "Bearish", binary: "Binary", neutral: "Neutral",
      EXECUTE: "EXECUTE", CANCEL: "CANCEL", ARCHIVE: "ARCHIVE",
      HOLD: "HOLD", BUY: "BUY", SELL: "SELL",
      STAGED: "STAGED", STAGED_ENTRY: "STAGED ENTRY", STAGED_EXIT: "STAGED EXIT",
    },

    // ── Positions form + table (en) ────────────────────────────
    positions: {
      add_btn: "+ Add Position",
      modal_title: "Add Position",
      ticker_placeholder: "e.g. MU",
      price_placeholder: "e.g. 382.50",
      shares_placeholder: "e.g. 50",
      notes_placeholder: "Notes, e.g. V4.6 STAGED aggressive fill",
      ticker: "Ticker", entry_date: "Entry Date", entry_price: "Entry Price",
      shares: "Shares", track: "Track", status: "Status", notes: "Notes",
      track_aggressive: "Aggressive", track_conservative: "Conservative", track_manual: "Manual",
      status_open: "Open", status_trimmed: "Trimmed", status_closed: "Closed",
      submit: "Save", cancel: "Cancel",
      live_pos: "Held", avg_cost: "Avg", shares_lbl: "sh",
      upl: "U/L", lots: "lots", delete: "Delete",
      // Close modal
      close_btn: "Close", close_modal_title: "Close Position",
      exit_date: "Exit Date", exit_price: "Exit Price",
      closed_shares: "Shares to Close", close_partial_hint: "Less than total = partial exit",
      realized_pl: "Realized P/L", confirm_btn: "Confirm",
      partial_exit: "PARTIAL EXIT", full_close: "FULL CLOSE",
      // Positions tab table
      portfolio_title: "Portfolio",
      total_cost: "Total Cost",
      total_upl: "Unrealized P/L",
      total_realized: "Realized P/L",
      status_col: "Status",
      cost_col: "Cost",
      current: "Current",
      pct_col: "%",
      show_closed: "Show Closed",
      no_positions: "No positions recorded. Click Add Position to start tracking.",
    },

    // ── Overview (index.html) ──────────────────────────────────────
    overview: {
      market_regime:  "Market Regime",
      hot_themes:     "Hot Themes",
      sentiment:      "Sentiment Index",
      recent_audit:   "Recent Audits",
      catalyst:       "Market Catalysts",
      quick_launch:   "Quick Launch",
      preflight_btn:  "Pre-Market Check",
      preflight_title: "Pre-Market Status Check",
      launch_desc:    "Enter ticker for analysis",
      start_btn:      "Launch Analysis",
      tbl_decision:   "Decision",
      tbl_score:      "Score",
      tbl_time:       "Time",
      breadth_score:  "Breadth Score",
      uptrend_ratio:  "Uptrend Ratio",
      cycle_phase:    "Cycle Phase",
      // Header
      market_status:       "Market Status",
      operator:            "Session User",
      // Conviction hero
      conviction_title:    "Market Conviction Score",
      // Action Posture card
      action_posture:      "Action Posture",
      action_posture_desc: "Regime + Breadth + Flags → position sizing guidance",
      regime_label:        "Regime",
      exposure_label:      "Exposure Ceiling",
      exposure_hint:       "Conservative floor across all signals",
      // Misc
      view_all:            "View All",
      no_flags:            "No Active Flags",
      flags_active:        "Flag(s) Active",
      backtest_pl:         "Backtest P/L",
    },

    // ── Signals / Conviction (index.html dynamic) ─────────────────
    signals: {
      conviction: {
        STRONG_BULL: "Strong Bull", BULLISH: "Bullish", MIXED: "Mixed",
        CAUTIOUS: "Cautious", BEARISH: "Bearish", STRONG_BEAR: "Strong Bear",
      },
      components: {
        ftd: "FTD Signal", sentiment: "Sentiment (Ctr)",
        top_risk: "Top Risk (Inv)", uptrend: "Uptrend Ratio",
      },
      drivers: {
        ftd: "FTD", sentiment: "Sentiment",
        top_risk: "Top Risk", uptrend: "Uptrend",
      },
      cards: {
        ftd: "FTD Signal", top_risk: "Top Risk",
        sentiment: "Sentiment", uptrend: "Uptrend %",
      },
      ftd_states: {
        FTD_CONFIRMED: "FTD Confirmed", FTD_WINDOW: "FTD Window",
        FTD_INVALIDATED: "FTD Invalidated", RALLY_ATTEMPT: "Rally Attempt",
        CORRECTION: "Correction", RALLY_FAILED: "Rally Failed", default: "No Signal",
      },
      top_zones: { Green: "Safe", Yellow: "Early Warning", Orange: "Caution", Red: "High Risk" },
      fg_labels: {
        "Extreme Fear": "Extreme Fear", Fear: "Fear", Neutral: "Neutral",
        Greed: "Greed", "Extreme Greed": "Extreme Greed",
        contrarian_suffix: " (Ctr)",
      },
      uptrend_labels: { healthy: "Healthy", neutral: "Neutral", weak: "Weak" },
      regime: {
        RISK_ON: "Risk On | Aggressive", RISK_OFF: "Risk Off | Defensive",
        VOLATILE: "Volatile | Reduce Size", NEUTRAL: "Neutral | Balanced",
      },
    },

    // ── Sector page (en) ───────────────────────────────────────────
    sector_page: {
      title: "Sector Intelligence",
      refresh: "Refresh",
      pill_regime: "Regime",
      pill_breadth: "Breadth",
      pill_ftd: "FTD State",
      pill_exposure: "Exposure Cap",
      pill_fg: "Fear & Greed",
      pill_cycle: "Cycle",
      pill_vix: "VIX",
      ftd_confirmed: "✓ Confirmed",
      binary_alert: "⚡ Binary Risk Within 48h",
      handoff_title: "Portfolio Strategist · Final Verdict",
      hot_label: "HOT",
      warm_label: "WARM",
      cold_label: "COLD",
      avoid_label: "AVOID",
      sectors_unit: "sectors",
      three_signal_title: "Three-Signal Synthesis",
      synthesized_ceiling: "Synthesized Ceiling",
      synth_subtitle: "min(Breadth, FTD, Top) — most conservative",
      signal_conflict: "Signal conflict — use conservative ceiling",
      signal_breadth: "Breadth",
      signal_ftd: "FTD",
      signal_top: "Market Top",
      quality_label: "Quality",
      exposure_label: "Exp",
      budget_label: "Budget",
      cap_label: "Cap",
      catalyst_title: "News & Political Signals",
      named_targets_today: "Named Targets Today",
      no_catalyst: "No political signals detected.",
      divergence_title: "Divergence Watch",
      no_divergence: "No active divergences.",
      action_reduce: "↓ Reduce Exposure",
      action_monitor: "👁 Monitor",
      themes_title: "Actionable Themes",
      no_themes: "No active themes.",
      overbought_label: "⚠ Overbought",
      da_challenge: "DA Challenge",
      uptrend_label_card: "Uptrend",
      comp_bm: "BM",
      comp_th: "TH",
      comp_nc: "NC",
      comp_rs: "RS",
    },

    // ── Watchlist page ─────────────────────────────────────────────
    watchlist: {
      title:              "Decisions",
      subtitle:            "決策中心",
      active_label:        "Active / Monitoring",
      waiting_label:       "Waiting Entry",
      avg_conf:            "Avg Confidence",
      avg_rr:              "Avg R/R Ratio",
      filter_all:          "ALL",
      filter_active:       "ACTIVE",
      filter_waiting:      "WAITING",
      filter_historical:   "HISTORICAL",
      filter_positions:    "POSITIONS",
      entry_triggers:  "Entry Triggers",
      reeval_triggers: "Watch Triggers",
      key_risks:       "Key Risks",
      view_report:     "View Report",
      flash_btn:       "FLASH",
      flash_toast:     "<span class=\"text-emerald-400 font-bold\">\"新聞分析 FLASH {TICKER} 近期動態\"</span><br>Copied to clipboard — paste into Claude Code to run FLASH news debate on {TICKER}",
      no_items:        "No items match this filter.",
      model_score:     "Model Score",
      da_filed:        "DA Filed",
      horizon_label:   "Horizon",
      size_label:      "Size",
      rr_label:        "R/R",
      conf_label:      "Confidence",
      refresh_btn:     "Re-analyze",
      history_title:   "Analysis History",
      history_empty:   "No prior analyses.",
    },

    // ── Warning / Breadth (index.html) ────────────────────────────
    warnings: {
      banner_title:   "Risk Flags Active",
      uptrend_label:  "Uptrend Ratio",
      breadth_label:  "Breadth Score",
      flags: {
        Late_Cycle:                 "Late Cycle",
        High_Selectivity:           "High Selectivity",
        Narrowing_Breadth:          "Narrowing Breadth",
        Death_Cross_SP500:          "Death Cross (S&P500)",
        Extreme_Fear_Sentiment:     "Extreme Fear",
        Overbought:                 "Overbought",
        Oversold:                   "Oversold",
        Mean_Reversion_Risk:        "Mean Reversion Risk",
        Bearish_Signal_Active:      "Bearish Signal Active",
        Below_200MA:                "Below 200MA",
        Low_Historical_Percentile:  "Low Historical Percentile",
        Weakening_Zone:             "Weakening Zone",
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

    // ── News page extra strings ────────────────────────────────────
    news_page: {
      bull_label:       "Bull",
      bear_label:       "Bear",
      arbiter_prefix:   "Arbiter → ",
      binary_badge:     "⚡ BINARY RISK",
      pending_label:    "PENDING",
      reviewed_label:   "REVIEWED",
      review_btn:       "Submit Review",
      review_toast:     "<span class=\"text-emerald-400 font-bold\">Review prompt</span> copied to clipboard.<br>Paste into Claude Code for formal committee review.",
      filter_all:       "All",
      filter_reviewed:  "Reviewed ✅",
      filter_pending:   "Pending ⏳",
      copy_prompt:      "Copy Prompt",
      retry_btn:        "RETRY",
      loading:          "Loading data...",
      last_sync_none:   "LAST SYNC: NONE",
      digest_toast:     "Dashboard reloaded.<br><span class=\"text-emerald-400 font-bold\">\"新聞分析 DIGEST\"</span> copied to clipboard.<br>Paste into Claude Code to run full DIGEST (1–2 min).",
      news_type: {
        fomc:            "FOMC",
        earnings:        "EARNINGS",
        geopolitical:    "GEOPOLITICAL",
        macro_data:      "MACRO DATA",
        political:       "POLITICAL",
        sector_specific: "SECTOR",
      },
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

    // ── Sector page (sector.html / page-sector.js) ────────────────
    sector_page: {
      binary_alert:        "⚡ Binary Risk Within 48h",
      handoff_title:       "Portfolio Strategist · Final Verdict",
      three_signal_title:  "Three-Signal Synthesis",
      catalyst_title:      "News & Political Signals",
      divergence_title:    "Divergence Watch",
      themes_title:        "Actionable Themes",
      named_targets_today: "Named Targets Today",
      pill_regime:         "Regime",
      pill_breadth:        "Breadth",
      pill_ftd:            "FTD State",
      pill_exposure:       "Exposure Cap",
      pill_fg:             "Fear & Greed",
      pill_cycle:          "Cycle",
      pill_vix:            "VIX",
      ftd_confirmed:       "✓ Confirmed",
      sectors_unit:        "sectors",
      uptrend_label_card:  "Uptrend",
      overbought_label:    "⚠ Overbought",
      da_challenge:        "DA Challenge",
      comp_bm:             "BM",
      comp_th:             "TH",
      comp_nc:             "NC",
      comp_rs:             "RS",
      signal_breadth:      "Breadth",
      signal_ftd:          "FTD",
      signal_top:          "Market Top",
      cap_label:           "Cap",
      quality_label:       "Quality",
      exposure_label:      "Exp",
      budget_label:        "Budget",
      synthesized_ceiling: "Synthesized Ceiling",
      synth_subtitle:      "min(Breadth, FTD, Top) — most conservative",
      signal_conflict:     "Signal conflict — use conservative ceiling",
      no_catalyst:         "No political signals detected.",
      no_divergence:       "No active divergences.",
      no_themes:           "No active themes.",
      action_reduce:       "↓ Reduce Exposure",
      action_monitor:      "👁 Monitor",
      // Scan modal
      scan_modal_title:    "Sector Scan Running",
      scan_confirm:        "This will ask Claude to run the full sector scan protocol.\n\nExpected: 3–5 minutes, will consume API tokens.\n\nProceed?",
      scan_running:        "RUNNING",
      scan_done:           "DONE",
      scan_error:          "ERROR",
      scan_cancelled:      "CANCELLED",
      scan_log_title:      "Live Log",
      scan_cancel_btn:     "Cancel",
      scan_close_btn:      "Close",
      scan_start_failed:   "failed to start",
      scan_in_progress:    "another scan already running",
      scan_expand:         "Expand",
      scan_minimize:       "Minimize",
      scan_latest:         "Latest event",
    },
  },
};

window.i18n = i18n;
