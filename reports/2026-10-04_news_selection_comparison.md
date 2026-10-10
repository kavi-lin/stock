# News 選稿修正與 Luna 實跑比較 — 2026-10-04

**結論：原本 5 則不是全部低影響。3 則低增量、2 則值得深度分析；主要缺陷是 Stage 1 選稿和把多數低分視為缺漏分析的規則。**

本報告由主代理整理 Luna 實跑輸出、原 10/3 lane 結果與補充來源核對。Luna 完成當期四 lane 分析；未宣稱它重新獨立評完原五則。

## 原五則逐項比較

| 原 ID／新聞 | 原 Bull / Bear | 固定原始資料：Stage 1 修正前 → 後 | 判斷與證據 |
|---|---:|---:|---|
| n0237 Fleur Capital 收購核准 | +1 / -1 | 5.5 → 2.0 | 低增量。Fed 公告是 Fleur Capital 收購 Simmesport State Bank 的核准，不是利率決策；例行公告 regex 漏掉省略 the 的寫法。[Fed 原文](https://www.federalreserve.gov/newsevents/pressreleases/orders20261002a.htm) 本輪重新開啟核對。 |
| n0315 Regulation O 徵詢延期 | +1 / -1 | 5.5 → 2.0 | 低增量。僅將徵詢期延至 11/4，沒有最終規則生效；過去因 Federal Reserve 關鍵字被判成貨幣政策。[Fed 原文](https://www.federalreserve.gov/newsevents/pressreleases/bcreg20261002a.htm) 本輪重新開啟核對。 |
| n0344 就業報告／利率預期 | +3 / -2 | 4.9 → 4.9 | 原本就不是低影響，存在利率預期與需求放緩兩條傳導。Luna 第一次取材讀取 WSJ；第二次重抓時已超出 24 小時窗口，退出原因是時間，不是降級。[原文](https://www.wsj.com/finance/stocks/u-s-stocks-rise-as-jobs-report-tempers-rate-outlook-fde051d1)；此處沿用原 lane 評估，未另編新分数。 |
| n0062 航艦水兵生活報導 | +1 / -1 | 4.5 → 2.5 | 低新增市場影響。10/3 發表，主體是 Reuters 九月艦上採訪與生活經驗，不能當成當天新部署或新供應中斷。本輪主代理重新找到 [Reuters 轉載全文](https://www.internazionale.it/ultime-notizie-reuters/2026/10/03/aboard-the-uss-george-washington-young-sailors-adjust-to-war-with-iran) 核對。 |
| n0324 沙烏地／胡塞／紅海 | +2 / -3 | 4.5 → 4.5 | 有條件式實質影響，應保留 deep。Luna 本次新證據與四 lane 得 Bull +2、Bear -4、Sector +2、Macro -2，deterministic net=-1.4、BEARISH；計畫尚非已發生的航運中斷。[Reuters 轉載](https://www.defensenews.com/global/mideast-africa/2026/10/02/saudis-plan-assault-on-houthis-to-break-red-sea-chokehold/) |

以上「低增量／值得 deep」是市場影響判讀，不能只由來源名氣或新聞標題推定。三筆 Stage 1 降分反映文章形式分類修正，沒有改動原 lane impact_score。

## 本次正式結果

- 時間窗：2026-10-04 00:33 之後執行，往前 24 小時；來源為 RSS、Finnhub、FMP、SEC EDGAR，全部成功，去重後 345 則。
- Stage 2：葡萄牙對美軍使用 Lajes 基地的法律調查、沙烏地／胡塞紅海計畫、川普不實施柴油出口禁令，共 3 則。
- Luna / medium 四 lane 完成。葡萄牙新聞為 +1/-1/0/0，降為摘要；紅海為 -1.4 BEARISH；柴油出口為 +0.6 NEUTRAL，保留 deep 反映政策資訊但方向幅度有限。
- Finalizer 最終產生 2 deep + 10 shallow；validator rc=0；event store append 12 筆，僅 2 deep 更新 cache。完整輸出：[正式報告](2026-10-04_news_digest.md)。
- 首次取材另發現「How to Protect Your Portfolio…」理財教學文漏網；原網址失效，fallback 是 2022 舊文。已新增文章形式辨識，固定當時 350 則重算由 5 候選變 4；後續 345 則／3 候選的差異另包含時間窗變化。

## 執行與限制

| 協調流程 | 結果 |
|---|---|
| Luna 第 1 次，00:11 任務／00:12 取得名額 | 取材完成，host 拒絕子代理 effort 字面值 default，lane 未開始；保留失敗紀錄。 |
| Luna 第 2 次，00:33，明確 medium | 四 lane 完成，初次 finalizer 因缺少 shallow 標題翻譯停止。主代理僅補 n0127/n0063/n0192 三個翻譯後重跑 finalizer，通過。 |

共 2 次協調推論，成功的 4 個 lane 使用指定 Luna/medium；沒有第三次模型重跑。啟動前的模組載入錯誤、broker busy／連線逾時均發生在 model_called=false，未算推論。

Luna 第二次執行前後，394 個受監測 Python 檔（含 news/scripts）一致。補翻譯前後 lanes JSON 的 SHA256 均為 `c302113add992e3ae6fffa36ff718cb407d30cfc85e2edc2c2fc814c712cf4b2`。原 10/3 raw/triage/debate、首次 Luna 快照與第二次原始 debate 均保存在 `news/news_logs/audits/2026-10-03_news_repair/`。

驗证：129 項 News 測試；routing／scheduler／broker contract；5 支 Dashboard JS syntax；省略-the 記憶體 mutation 確認會重現錯誤。正式 validator 另以當日 digest 路徑驗收 rc=0。
