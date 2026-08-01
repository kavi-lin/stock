# Session Notes 歸檔 v4.28.0 → v4.43.2（新在上，共 10 個）

> 由 scripts/rotate_session_notes.py 產出。查特定版本：Grep 版號於 archive/session_notes_*.md。

## 🟢 Session Note (v4.43.2) — Forward Expectations calibration 誠實化：修 gate 假性 fail
- **起因**：問「前瞻下一步」→ success_criteria gate = **fail (WAPE 0.77 / bias −0.46 / n=100)**。挖根因 → 三個方法學 artifact，非引擎差。
- **缺陷 A 基準錯配**：拿多年 forward CAGR 比單年 trailing YoY（CAGR 內含減速 < 火熱單年 → 81/100 偏低）。改 `_realized_window_cagr`：由 `annual_growth` 各 FY YoY 幾何平均出**同窗 realized CAGR**。
- **缺陷 B 未到期計分**：窗 2027–2031 但 actual 取 2026 trailing。改 `window_to > 最新實現 FY` → `actual_not_comparable_yet`；缺窗內 FY → `actual_basis_unavailable`（不退回 YoY）。
- **缺陷 C 重複灌水**：同股 re-run 8 份算 8 row。`_latest_snapshot_per_ticker` 只留每股最新。
- **結果**：gate fail → **insufficient_evidence (comparable=0)**。56 檔→13 ticker→48 row 全 not_comparable_yet（最早窗 2027 > 實現 FY 2026）。仍擋 live 但理由正確。calibration golden 9→25 asserts，全 forward 套件（24 檔）綠。
- **注意版本**：本 session 與平行 session（供應鏈 4.43.0/4.43.1）同日；我的 forward 工作 = 4.42.0（貨幣正規化）+ 4.43.2（calibration）。三處版本同步至 4.43.2。
- **檔案**：forward_expectations_calibration.py（v2 helpers + dedup + evaluate）/ test_..._calibration.py（重寫）/ VERSION + utils.js + CHANGELOG。

## 🟢 Session Note (v4.43.1) — 供應鏈外股常見公司 backfill
- **起因**：V4.43.0 新欄位上線後，既有 YAML 因沒有 `market/local_ticker`，仍顯示 `FOREIGN`。這是正確 fallback，但對常見台/韓/日供應鏈公司可 deterministic 補齊。
- **做法**：`supply_chain.py` 加 `_FOREIGN_LISTING_BACKFILL` 與 `_apply_foreign_listing_backfill()`，只在 `listing: foreign_listed` 且欄位為空時套用，不覆蓋人工修正。
- **覆蓋**：TSMC、Samsung Electronics、SK hynix、Tokyo Electron、Advantest、Disco、Lasertec、Hon Hai/Foxconn、Quanta、Wistron、Wiwynn、MediaTek、ASE、ASML 等。
- **驗證**：`python3 -m pytest tests/test_supply_chain_enrichment.py` 11 passed；`python3 -m py_compile scripts/nexus/supply_chain.py` rc=0。

## 🟢 Session Note (v4.43.0) — 供應鏈頁外股標示 + 上下游投資摘要
- **起因**：供應鏈頁把大量台股/韓股/日股與 private/pre-IPO 混成「外股/未上市」，使用者難以分辨可交易性；同時圖譜只回答「誰連誰」，缺少可掃讀的上下游投資報告。
- **資料層**：`supply_chain.py` schema/enrich 新增 `market/exchange/local_ticker/adr_ticker/country/investability/proxy_tickers`，derive `display_symbol/market_label`；`chain_report` deterministic 輸出可投資節點、瓶頸、私有 proxy、關係信心與高信心 edge。
- **UI**：`supply-chain.html/page-supply-chain.js` 新增「上下游投資摘要」四欄，卡片顯示 `US:NVDA` / `TW:2330` / `KR:005930` / `PRIVATE`，detail panel 顯示市場與可投資性。
- **生成提示/文件**：prompt 改成 global supply-chain for US-focused investor，要求非美上市填本地 market/ticker；SCHEMA.md 同步。
- **驗證**：`python3 -m pytest tests/test_supply_chain_enrichment.py` 9 passed；`node --check Dashboard/page-supply-chain.js` rc=0；`python3 -m py_compile scripts/nexus/supply_chain.py` rc=0。

## 🟢 Session Note (v4.42.0) — Forward Expectations 貨幣正規化：修 ADR (TWD/EUR) 前瞻股價 ~30× 爆衝
- **起因**：review 抓到 TSM「未來前瞻」base = **$11,491 (+2598%)** garbage。根因：FMP 對外國 ADR 三表/估計用記帳幣別（TSM→TWD，eps 131.6 TWD），但股價/市值/PE 是 USD → TWD EPS × USD P/E 膨脹整個 FX 倍率。cache **無 reportedCurrency 欄位**。
- **治本（FX）**：`forward_expectations_price_range.py` 加 `reporting_to_trading_fx`，EPS/rev-ps/fcf-ps 乘 multiple 前先 ÷ fx。純函式 `resolve_reporting_fx()`（reportedCurrency==USD→1.0 / FMP forex {CUR}USD→1/rate / 由 statement-vs-ADR EPS ratio >5× 反推 / parity）。`forward_expectations.py` `_currency_normalization()` fetch **income-statement reportedCurrency**（權威；**非 profile.currency** — 對 ADR 是 USD 交易幣別會誤判 parity）+ forex。
- **防護網（gate）**：base/現價 >6× 或 <1/6 → 退自洽 advisory band + `currency_unit_suspect`，永不寫爆炸值。anchor 可用無 derived 退路時動態合成 current-price band。
- **驗證**：TSM live fx=31.6 (TWD via forex) → base **$363** / bear $184 / bull $487（對齊 blended FV，review 預期 ~$359）。NVDA fx=1.0 range 不變。price_range golden 56 passed（+TSM TWD fixture 兩路）；margin_norm 18 / bridge 38 / compression 47 / core 48 全綠。
- **連帶查證**：live blend `peer_pe_implied`（compute_price_framework）`eps_ttm = 現價(USD)/pe_self(USD)` → **USD 自洽無污染**，$773 偏高純 peer 失配已折讓。Shadow-only，不入 live 決策。
- **檔案**：price_range.py（fx+gate+resolve）/ forward_expectations.py（_currency_normalization）/ margin_normalization.py（currency tag）/ test_..._price_range.py（fixtures）/ schema + VERSION + utils.js + CHANGELOG。

## 🟢 Session Note (v4.41.0) — 決策卡 v5.1 估值區 price-axis number-line 視覺化
- **起因**：user 要重新設計決策中心 v5.1 卡片估值區那批數據（FV / range / 5D-60D / implied CAGR / archetype / forward / glide）的視覺呈現。
- **選的方向**：user 選 price-axis number-line（同尺規把各價位放一條軸上），inline 在卡內。
- **做法**：`page-decisions.js` `buildFvExtras` 全重寫成兩條 CSS-positioned track — Track A 現值估值（p25–p75 著色帶 + FV tick + 現價 marker，現價>FV 紅/<FV 綠）、Track B 未來前瞻 shadow（現價→bear/base/bull caret + %，glide chips 移此）；momentum / implied CAGR / archetype 收成下方 compact chips。新增 helper `buildValAxis()`（純 CSS %-positioning，themeable）。
- **不變**：全 advisory / shadow-only 標籤、tooltip、版本閘、缺 block 隱藏行為照舊；不碰決策數學。`node --check` rc=0。
- **檔案**：page-decisions.js（重寫 + helper）/ VERSION / utils.js / CHANGELOG。

## 🟢 Session Note (v4.40.0) — PEG terminal P/E + 近年年化 glide + 修 limit=3 截斷（EXP-3.5）
- **起因**：user 問 NVDA forward base $252 是幾年（→4.6yr），覺得「不該取這麼遠當 horizon」，要近年年化目標價。
- **挖到的根因**：`fetch.py` annual estimates `limit=3` + FMP 降冪 → 只拿最遠 3 年、丟掉近年；遠期營收被截成假平 → EXP-3.4 把 NVDA 誤判 mature → 22x → **$252 是壞資料假象**。修 `limit=6` 後 NVDA 變 hypergrowth → 55x → $1024（定價完美，不可作 base）。
- **解法（user 選 PEG）**：`terminal_pe = clamp(2.2 × terminal_growth_pct, 20, 60)`，綁定**終期減速成長**（非年份），含薄覆蓋雜訊守門。NVDA 57→30x（13.7%）、ARM 151→60x。+ 近年年化 glide trajectory（錨定 terminal、幾何內插、年化恆定，不重估）。
- **NVDA 結果**：terminal base **$562**（ann +24%/yr）；glide FY2027 $237(+14%)→FY2028 $294(+42%)→FY2031 $562(+171%)。AMD/MU 亦合理。
- **校準 lever**：PEG 常數 2.2 / 20 / 60 在 `forward_expectations_multiple_compression.py` 頂部。Shadow-only，不入 live 決策。
- **檔案**：fetch.py(limit) / multiple_compression.py(PEG) / price_range.py(glide) / financial_bridge.py(coverage) / forward_expectations.py(compress 移後) / forward_price_range.py + bridge.py(顯示) / 3 golden + schema + CHANGELOG。全套 golden rc=0。

## 🟢 Session Note (v4.30.0→v4.35.0) — Forward Valuation Robustness Sweep（review → P0 gate 全清 + cohort）
- **起因**：user 請 code review 整套未來估值系統（V4.13–4.30，~4363 行原 uncommit）。Review 抓 6 問題，最致命：`future_price_range` 預設 `base_multiple = current_price/forward_eps` → base ≡ 現價（ARM/NVDA 實測 +0.0%），看似 forecast 實為波動帶。
- **EXP-R0**（V4.30.0）落地 commit 全系統（runtime ledger 不入 git）。
- **EXP-R4**（V4.30.1）全線 `json.dumps(allow_nan=False)` + 除零 guard + safety test。
- **EXP-R1**（V4.31.0）**破套套邏輯**：`forward_expectations_multiple_anchor.py` 自身歷史 multiple regime（price-independent，dispersion ≤3.0 gate）；優先序 explicit→historical→derived，只剩 derived 時 status `advisory_band_only` + ⚠️。
- **EXP-R2**（V4.32.0）bridge held-constant 揭露 + terminal sensitivity。
- **EXP-R3**（V4.33.0）scenario 分歧度改用 consensus low/high envelope，缺證據降級，移除固定 ±step。
- **EXP-0.4**（V4.34.0）`forward_expectations_success_criteria.py` 8 criteria + shadow→live gate（現況 insufficient_evidence）。**EXP-1.2** consensus 獨立性 guard。
- **EXP-3.2**（V4.35.0）`forward_expectations_cohort.py` 可稽核 base-rate cohort（防 cherry-pick）。ARM→9 名 Tech cohort median 0.135。
- **驗證**：20 forward test suite 全綠。8 commits（`fad6359`→`efa2438`）。健康度 6 問題全修。
- **待 user 實測**：`forward_price_range.py <T> --fetch`（真前瞻）vs 無 `--fetch`（advisory band）；`forward_expectations_success_criteria.py`（升 live 門檻）。
- **下一步 P1**：EXP-3.1 新 adapter（目前只 royalty_ip→只 ARM 走 independent lane）；EXP-2.1/2.2 ARM driver 深度。ARM `--fetch` base $870 偏樂觀（歷史 151× P/E 持續）→ 倍數壓縮留 EXP-3.4。

## 🟢 Session Note (v4.30.0) — Ticker Future Price Range CLI
- **新增**：`forward_price_range.py`，使用者輸入 ticker 即可直接看到 forward future price range。
- **命令**：`python3 investment/scripts/forward_price_range.py ARM`。
- **輸出**：Current、Horizon、Method、Bear/Base/Bull target price、upside/downside、warnings、shadow-only policy。
- **驗收結果**：ARM cache-first smoke 成功，輸出 2030-03-31 EPS×P/E range：Bear $197.52 / Base $237.30 / Bull $280.14。
- **治理**：wrapper 只萃取 `future_price_range`，不改 live `fair_value_summary`、decision lock、threshold 或 sizing。
- **驗證**：wrapper 13/13、py_compile rc=0、ARM end-to-end command rc=0。

## 🟢 Session Note (v4.29.0) — Forward Future Price Range
- **新增**：`forward_expectations_price_range.py`，把 forward financial bridge rows 映射成 shadow `future_price_range`。
- **輸出**：bear/base/bull `target_price`、`upside_pct`、使用的 metric / multiple、`horizon_date`、method 與 warnings。
- **Mapping order**：EPS×P/E 優先；EPS 不可用時 Revenue/share×P/S；再不行 FCF/share×P/FCF。
- **Multiple source**：優先 explicit `valuation_multiples`；沒有時用 current-market implied multiple band（±15%）並標 `derived_current_market_multiple_used`。
- **接線**：`forward_expectations.py --ticker <T> --self-assemble` 現在 top-level 會輸出 `future_price_range`；report renderer 新增 Future Price Range section。
- **治理**：仍是 shadow-only，不修改 live `fair_value_summary`、decision lock、threshold 或 sizing。
- **驗證**：price range 19/19、report renderer 22/22、core forward expectations 45/45、py_compile rc=0。
- **下一步**：做 CLI/UX 驗收包裝，讓使用者輸入 ticker 時能直接只看價格區間，而不用讀完整 JSON。

## 🟢 Session Note (v4.28.0) — Royalty/IP Driver-Level Scenarios
- **新增**：`royalty_ip` adapter 輸出 `driver_model`，整理 promoted primary-source driver values / evidence refs。
- **Driver-level cases**：scenario builder 優先用 `driver_model` 產生 bear/base/bull，調整 royalty-bearing units、royalty rate/value per unit、license pipeline conversion、data-center exposure、revenue CAGR。
- **新增 gate**：`data_center_segment_exposure` 成為 Royalty/IP numeric lane 必要 driver；缺值或缺 evidence 時仍 blocked。
- **Fallback**：若 policy 允許 numeric 但 adapter 沒有完整 driver model，才退回 V4.27.0 aggregate revenue CAGR sensitivity。
- **防誤用**：仍是 shadow-only；不產生 fair value、target price、verdict、threshold 或 sizing。
- **驗證**：royalty_ip adapter 32/32、scenario builder 26/26、report renderer 20/20、core forward expectations 42/42、scenario policy 16/16、primary sources 24/24、evidence inventory 30/30、py_compile rc=0。
- **下一步**：補 driver-level revenue bridge / formula attribution，讓 units × rate 與 license conversion 能解釋 aggregate revenue CAGR，而不是只並列 driver sensitivities。
