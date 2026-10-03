# AI 煉金術：帶 AI 完成自己的交易研究

上一堂學會用 AI，這一堂學會帶 AI 把事情做完。

這是第二堂課的學生答案包。由講師的「動能飆股盤中監控」拆出可確認的動能條件，延伸成**盤後研究案例**，用雪鴞 `api.bt` 完成 68 組回測與帳務核對。不是原軟體完整策略，也不是即時買賣建議。

**[開啟圖像化實作頁](https://duang0615.github.io/ai-alchemy-trading-lab/)** · **[下載整包 ZIP](https://github.com/duang0615/ai-alchemy-trading-lab/archive/refs/heads/main.zip)**

## 新增：雪鴞選股實作室

**[開啟18張策略卡與選股實作](https://duang0615.github.io/ai-alchemy-trading-lab/stock-picker/)** · **[抄答案與兩次休息練習](docs/stock-picker-workbook.md)** · **[來源與尚缺功能](docs/stock-picker-source-audit.md)**

公開頁是16檔真實教學小樣本，本機版用自己的雪鴞環境掃描目前股票資料。12張可計算，其中7張明示教學改造；6張缺資料或完整規則會停止。保留框架、公式、資料與畫面分工，讓同學抄完成版，再練習一次只改一個模塊。此篩選器尚不是原站100%等價版，也沒有包含完整買賣策略。

## 課程最後的禮物

**[學生答案包：帶 AI 完成自己的交易工具（Markdown）](docs/student-process-gift.md)**

把自己的需求填進去，依序讓 AI 設計框架、拆工作、核對產物，看到結果後找原因、改一項再驗證。附知識庫存檔與中斷續工指令。課程結論用三個大區塊：**想清楚 → 帶 AI 做 → 看結果再改**。每次實作的過程都能留給下次接續。

## 學生先做這兩件事

1. 開啟實作頁，選 `6533`：對照一筆成功、一筆失敗，查訊號、成交時間與成本。
2. 先寫「我的假設」，再看 3／5／10 日與增加成本的結果；把觀察下載成 Markdown，放進上一堂的 Obsidian。

無需安裝軟體就能看完成版。網頁內資料已嵌入，下載 ZIP 解壓後可直接開啟 `index.html`，離線看報告。瀏覽器本機筆記沒有多人同步。

## 交給 AI 的第一句話

> 請讀取這個專案的 AGENTS.md 和 skills/momentum-research-lab/SKILL.md。先帶我理解來源、規則、結果與缺少的證據。今天先做「交易解剖」，完成後再做「模塊改造」。每完成一個模塊就更新進度與驗收證據，失敗也要留下原因與下一步。

Skill 在 ZIP 內，可讓 AI 直接讀取；需要安裝時，把 `skills/momentum-research-lab` 整個資料夾放進自己的 Codex skills 目錄。Skill 引導 AI 尋找此專案，無需複製帳密或把資料上傳。

## 要重跑真實資料

同學已拿到雪鴞試用包：使用**已裝雪鴞的 Python**，帳密保留在自己的本機 `.env`，無需交給老師或 AI。

```powershell
# 把路徑換成你自己的雪鴞環境與 .env
& 'C:\AI\owl\.venv\Scripts\python.exe' -X utf8 .\scripts\run_research.py --env 'C:\AI\owl\.env'
& 'C:\AI\owl\.venv\Scripts\python.exe' -X utf8 .\scripts\build_report.py
```

本包不提供雪鴞安裝檔、帳號或大量原始行情。重跑需自己的合法資料權限與網路；取得的原始資料只放在被 Git 忽略的 `.local`。新資料截止日會跟著帳號資料範圍改變，所以重新執行不保證與本版數字相同。第一次會下載快取。

## 完成了什麼

| 內容 | 位置 |
|---|---|
| 固定規格、來源及假設 | `strategies/momentum_eod/spec.json`、`docs/source-map.md` |
| 4 檔 × 4 版本 × 3 時段，加天數與成本測試：68 組 | `reports/comparison.csv` |
| 同一千萬元帳戶分母的報酬、回撤、夏普與逐年報酬 | `reports/account_comparison.csv`、`reports/yearly_returns.csv` |
| 每組原生回測報表、逐筆交易、帳戶權益 | `reports/<run>/` |
| 次日成交核對、逐筆費用與損益核對 | `reports/audit.json`、`reports/accounting_audit.json` |
| 交易區間估計、交易順序壓力測試、配對區塊重抽樣 | `reports/research.json`、`reports/block_comparisons.json` |
| 學生操作與老師講法 | `docs/classroom.md` |
| 可續工的流程與工作單 | `skills/momentum-research-lab/SKILL.md`、`progress.json` |

## 研究結果怎麼看

時序保留段是 2025-03-20～2026-10-01。6533 核心動能帳戶報酬 **+4.89%**，最大回撤 **-16.91%**，19 筆交易。去掉最好的三筆，合計損益會變成負值；平均每筆損益的探索性 95% 區間也跨過零。這正好用來教「有獲利，不等於已證明策略可靠」。2357 的同一規則在這段是虧損。

原始資料 2022-08-17～2026-10-01；暖機後研究從 2022-11-11 開始。四檔固定教學樣本存在選樣與存活者偏差；時序保留段也不是從未接觸過的未來。這版研究使用還原 OHLC 代理，未逐筆還原實際除權息現金、流動性、漲跌停排隊與真實滑價。**適合教拆解、驗證、改造，尚不能據此認定可直接實盤。** 詳見 [研究說明](docs/research.md)。

程式採 MIT 授權；雪鴞套件與資料仍依供應商授權，本包不授予其使用或轉散布權。此庫沒有下單程式。
