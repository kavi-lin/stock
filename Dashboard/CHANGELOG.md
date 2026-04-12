# INTEL COMMAND - Dashboard Change Log

## 專案核心目標：戰略智慧面板 (Strategic Intelligence Dashboard)
本文件記載從「AI 投資委員會」轉型為 **「INTEL COMMAND」** 專業戰情室風格的所有 UI/UX 與邏輯變更。

---

## 🚀 最新版本：V1.1.7.260412_19:20:00

### 1. 品牌重塑 (Branding & Identity)
- **品牌更名：** 從「AI 投資委員會」全面升級為 **INTEL COMMAND**。
- **視覺語言：** 採用全大寫、粗體、斜體字設計，強化軍事/專業戰情室的權威感。
- **文字細節：** 修正了斜體導致最後一個字母 `D` 被切掉的問題（增加 `pr-2` 補償）。

### 2. 日間模式深度集成 (Day Mode Integration)
- **色調定義：** 採用溫暖的 **Stone/Sand (#f5f2ed)** 為背景色，搭配高對比石墨黑文字，取代傳統刺眼的純白亮色。
- **全站自適應：** 所有組件（包含 Tooltip, Modals, Badges）皆透過 CSS 變數 `--bg-main`, `--text-main`, `--bg-card` 自動同步。

### 3. 系統日誌系統 (System Logs Console)
- **樣式統整：** 所有的 Log 視窗統一遵循 `sector.html` 的專業設計。
- **高度優化：** 最大高度提升一倍 (`max-h-80`)，支援歷史記錄上捲。
- **語系支持：** 標題與按鈕整合 `i18n.js`，支援自動語言切換。
- **主題同步：** 移除硬編碼黑色背景，日誌視窗現在會根據日/夜模式變換底色。

### 4. 信號顏色系統 (Signal Color Specification)
- **Bullish (看多)：** 沿用翡翠綠 (`#22c55e`)。
- **Bearish (看空)：** 沿用危險紅 (`#ef4444`)。
- **Binary (變數/風險)：** 從原本與紅色接近的琥珀色，重新定義為 **電信紫/靛色 (Violet/Indigo)**。
    - 夜間：`#8b5cf6` (高品質紫色)
    - 日間：`#6d28d9` (深紫色，高對比度且極其醒目)

### 5. UI/UX 細節修復與優化
- **側邊欄佈局：** 將頂部間距從 `p-6` 調至 `p-4`，收緊佈局，使品牌與切換按鈕更有平衡感。
- **標籤 (Labels) 自適應：** 產業標籤不再固定為黑色色塊，在日間模式下會自動切換為淺灰色。
- **彈窗背景 (Modals)：** 修正了審查報告彈窗硬編碼為黑色的問題。
- **按鈕視覺：** 「查看報告」按鈕 (View Report) 增加了日間模式下的反顯色與縮放動畫效果。

---

## ⚠️ 開發注意事項 (Important Notes)

1. **強制使用 CSS 變數：**
   - 不要直接使用 Tailwind 的 `text-zinc-50` 或 `bg-zinc-950` 等具体階度顏色。
   - **正確做法：** 使用 `style="color: var(--text-main)"` 或 `class="bg-[var(--bg-card)]"`，以確保日/夜切換時不會出現文字隱形或背景過深的問題。

2. **多國語系標籤：**
   - 所有的導航與重要標題請務必加上 `data-i18n="xxx"` 屬性。
   - 渲染動態 HTML 時，請記得在內容生成後呼叫 `lucide.createIcons()` 重新渲染圖標。

3. **版本控制：**
   - 修改完成後，需更新 HTML 底部的 Version Timestamp (格式：`V1.1.x.YYMMDD_hh:mm:ss`)，方便線上排錯。

4. **圖表 (Chart.js) 更新：**
   - 切換主題時需手動呼叫 `updateChart()` 或 `renderChart()` 重新獲取當前主題的網格顏色 (`gridColor`) 與標籤顏色 (`tickColor`)。

5. **Binary 顏色語意：**
   - 除非該新聞具備極端變數，否則優先使用 Bull/Bear 顏色。紫靛色專門保留給會造成市場巨大波動或雙向發展的情境。

---
*Last Updated: 2026-04-12 19:20*
