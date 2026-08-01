# Session Notes 歸檔 v4.18.0 → v4.27.0（新在上，共 10 個）

> 由 scripts/rotate_session_notes.py 產出。查特定版本：Grep 版號於 archive/session_notes_*.md。

## 🟢 Session Note (v4.27.0) — Operating-Driver Scenario Builder
- **新增**：`forward_expectations_scenario_builder.py`，接在 `scenario_policy` 後面產生 shadow-only scenario output。
- **Numeric gate**：只有 `numeric_scenario_allowed` + Independent revenue CAGR driver 存在時，才產生 bear/base/bull operating-driver cases。
- **降級呈現**：`range_or_overlay_only` 顯示 management guidance overlay；`qualitative_only` 顯示缺失 driver / conversion watchlist；`insufficient_inputs` 不產生 scenario。
- **防誤用**：輸出固定 `valuation_output=false` / `changes_live_decision=false`；不產生 fair value、target price、verdict、threshold 或 sizing。
- **接線**：`forward_expectations.py` snapshot 新增 `operating_driver_scenarios`；`forward_expectations_report.py` 新增 Operating-Driver Scenarios 區塊。
- **驗證**：scenario builder 20/20、report renderer 17/17、core forward expectations 42/42、py_compile rc=0。
- **下一步**：若要讓 scenario 更接近真正營運模型，需擴充 adapter 讓 royalty units、rate/value per unit、license conversion、mix/margin 等 driver 各自可形成 case，而不是只用 aggregate revenue CAGR sensitivity。

## 🟢 Session Note (v4.26.0) — Scenario Policy Gates
- **新增**：`forward_expectations_scenario_policy.py`，先判定 scenario mode 權限，不直接產生 bear/base/bull 數字。
- **Gates**：base metric、driver evidence、conversion method、forward bridge、range discipline。
- **輸出**：`numeric_scenario_allowed` / `range_or_overlay_only` / `qualitative_only` / `insufficient_inputs`，並列 forbidden methods。
- **防幻覺**：固定 EPS/P-E 百分比加減、LLM invented TAM、跨口徑 gap 當 driver、guidance range 壓單點全部列為 forbidden。
- **下一步**：在 policy 允許的情況下，建立真正 operating-driver scenario builder；否則報告只呈現 qualitative watchlist / range overlay。

## 🟢 Session Note (v4.25.0) — Forward Expectations Shadow Report Renderer
- **新增**：`forward_expectations_report.py`，把 snapshot render 成 Markdown advisory section。
- **呈現**：Expectations Matrix、Expectations Gap、Financial Bridge Risk、Policy footer。
- **防誤用**：renderer 只讀 snapshot，不做 valuation math；輸出明確標 shadow-only，不改 fair value、verdict、decision lock、threshold 或 sizing。
- **驗證**：`test_forward_expectations_report.py` 12 asserts，涵蓋 bridge-risk-only、same-metric gap table、bridge unavailable。
- **下一步**：將 renderer 串入個股分析 Phase 5 報告流程或先以 sidecar section 手動附加。

## 🟢 Session Note (v4.24.0) — Expectations Gap Engine
- **新增**：`forward_expectations_gap.py`，整理 market-implied、consensus、Independent、base-rate 的同口徑 expectations gap。
- **同口徑紀律**：營收 CAGR 只和營收 CAGR 比；FCF CAGR / EPS CAGR 若沒有同口徑 comparator，只輸出 unavailable 或 cross-metric observation。
- **Bridge risk**：`forward_financial_bridge` 的 wide gap、negative FCF、conversion warning 進 `financial_bridge_risks`，只作財務敘事風險，不作 valuation verdict。
- **治理**：top-level `expectations_gap` 只進 shadow snapshot，不改 fair value、decision lock、threshold 或 sizing。
- **下一步**：新增 shadow report 區塊，將 expectations matrix / gap / bridge risk 用人可讀格式呈現。

## 🟢 Session Note (v4.23.0) — Forward Financial Bridge
- **新增**：`forward_expectations_financial_bridge.py`，用 annual estimates + 歷史 margin / FCF conversion / share count 建立 ticker-neutral forward financial bridge。
- **輸出**：forward revenue、gross profit、operating income、tax/other bridge、net income from margin、EPS-implied net income、FCF、capex 與 consistency checks。
- **防幻覺**：缺 annual estimates、margin、FCF margin 或 share count 時 `insufficient_inputs`；guidance 只作 overlay，range 不被壓成單點。
- **治理**：top-level `forward_financial_bridge` 只進 shadow snapshot，不產生 fair value、不改 decision lock、不做 full forward DCF。
- **下一步**：用 bridge 計算 Expectations Gap，並把 market-implied / consensus / Independent / base-rate 並列成 report block。

## 🟢 Session Note (v4.22.0) — Forecast Calibration Scaffold
- **新增**：`forward_expectations_calibration.py`，唯讀掃 forecast ledger snapshots 與後續 earnings-analyst cache actual，建立 forecast-vs-actual rows。
- **初始可比項**：consensus revenue/EPS CAGR vs latest actual revenue_yoy / earnings_yoy；future-level revision snapshot 暫標 `actual_not_comparable_yet`。
- **指標**：absolute pct error、direction_hit、per-lane n、WAPE proxy、directional accuracy、`insufficient_sample`。
- **治理**：scaffold 不調權重、不改 live fair value、不宣稱 lane 優劣；n < min_required_n 固定 insufficient sample。
- **下一步**：開始 forward financial bridge 或把 calibration report 接入 shadow report；仍須保持 shadow-only。

## 🟢 Session Note (v4.21.0) — Analyst Estimate Revision Snapshot
- **新增**：`forward_expectations_revisions.py`，保存 point-in-time annual revenue／EPS consensus curve、low/high dispersion、analyst count 與 rating momentum。
- **誠實邊界**：目前 earnings cache 只有最新 forward curve，沒有同一 estimate 的歷史版本；因此 `estimate_revision_delta_available=false`，真正上修/下修要等未來 ledger snapshots 累積後比較。
- **Evidence 整合**：Evidence Inventory 新增 `consensus_revision:revenue`、`consensus_revision:eps`、`consensus_revision:rating_momentum` accepted evidence；不和 management guidance 混用。
- **治理**：revision snapshot 是市場預期紀錄，不是 analyst price target，也不進 live fair value / decision lock。
- **下一步**：建立 forecast-to-actual calibration scaffold 或 forward financial bridge，開始把保存下來的 expectations 對 actual 做可驗證閉環。

## 🟢 Session Note (v4.20.0) — Management Guidance Extraction
- **新增**：`forward_expectations_guidance.py`，通用抽取 company filing／IR／transcript 裡的 revenue、EPS、gross margin、operating margin、FCF、capex guidance/outlook。
- **Range discipline**：guidance range 保持 `{low, high, midpoint}`；midpoint 只是 derived helper，不當成 management 原始單點預測。
- **Evidence 整合**：primary-source acquisition 現在分開輸出 driver candidates 與 guidance candidates；Evidence Inventory 以 `guidance:<metric>` + `value_type=guided` accepted，不會混入 adapter driver。
- **防幻覺**：歷史數字無 guidance words 不抽；investment report / unsupported narrative 不 promoted；缺 period/date/source 保持 provisional。
- **下一步**：建立 estimate revision snapshot 或 forward financial bridge；guidance 目前只存 evidence，不直接改 fair value / decision lock。

## 🟢 Session Note (v4.19.0) — Bounded SEC Document Acquisition / Normalization
- **新增**：`forward_expectations_document_acquisition.py`，在 `--acquire-documents` opt-in 下，從 discovery manifest 的 allowlisted SEC filing document URL 下載並正規化 HTML/TXT。
- **安全邊界**：只允許 `sec.gov` / `www.sec.gov` / `data.sec.gov`，且 filing document 必須在 `/Archives/edgar/data/`；SEC submissions manifest、company website／IR root 與任意網站不抓。
- **防幻覺**：normalized text 只是 primary-source bundle input，`numeric_eligible=false`；仍必須通過 `forward_expectations_primary_sources.py` 的 value/unit/period/date/source gate 才能 promoted。
- **Quota / cache**：文件 30-day cache；cache hit 不打網路；普通 `forward_expectations.py` run 預設不抓文件。
- **驗證**：Document Acquisition 19/19、Source Discovery 18/18、Primary Source 19/19、Evidence Inventory 23/23、Royalty/IP adapter 30/30、Forward Expectations core 34/34、Price Framework 26/26、py_compile / diff-check rc=0。ARM/ORCL/LLY `--acquire-documents --no-fetch` 均無網路抓取、無誤升級。
- **下一步**：擴充通用 guidance/range extractor 與 filing 內 driver pattern，但仍不可用 LLM 或任意敘事補值。

## 🟢 Session Note (v4.18.0) — Ticker-Neutral Primary Source Discovery
- **新增**：`forward_expectations_source_discovery.py`，對所有 ticker 共用 source manifest；從 profile cache 的 website／CIK、24h filing metadata cache、FMP filing metadata 與 transcript location 發現候選來源。
- **無 ARM 特例**：表格家族只依實際 metadata 分類；`10-K/20-F/40-F` annual、`10-Q` interim、`6-K` 保持中性 foreign-issuer report，避免只看 metadata 就猜內容。
- **防幻覺**：discovered URL／filing metadata 進 Evidence Inventory 時一律 provisional、`numeric_eligible=false`；不下載全文、不抽 driver、不解鎖 Independent lane。
- **Quota**：profile 重用 shared cache；filing metadata 新增 24h cache，cache hit 不查 FMP。
- **跨 ticker 修正**：adapter registry 只有完整 `matched` 才可 selected；ORCL 的 License partial match
  現在只留候選，不再套用 Royalty/IP 缺失 driver。
- **下一步**：建立受限 document acquisition／normalization，下載已發現的 filing／IR 文件內容，再交給既有 primary-source promotion gate；仍不得由來源 metadata 自動補值。
