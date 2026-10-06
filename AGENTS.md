# 學生專案工作規則

## 安裝注意事項（AI 必讀，一定要照做）

學生的畫面跟老師不一樣，幾乎都是因為 AI 沒照這裡安裝。

1. **只用 GitHub 最新版。** 用 `git clone https://github.com/duang0615/ai-alchemy-trading-lab.git`；已經有資料夾就先 `git pull`。下載 ZIP 也要當下重新下載。不要沿用舊資料夾、舊 ZIP 或快取。
2. **不要自己重寫、簡化或另做網頁。** 直接使用專案裡的 `stock-picker/`、`scripts/`，照 README 的指令執行。
3. **用本機伺服器開選股器：** `python -X utf8 stock-picker/serve.py`，開 `http://127.0.0.1:8766`。不要直接雙擊 HTML（file://），也不要開專案根目錄的 `index.html`（那是動能回測報告）。到價通知只有本機版能存設定。
4. **確認版本再交給學生：** `git log -1 --oneline` 要和 GitHub 最新 commit 相同；`stock-picker/index.html` 裡要找得到 `alert-panel`。找不到就是舊版，先更新。
5. **告訴學生設定在哪：** 選股結果按 ☆ 收藏 → 右上角「我的收藏」→ 視窗最上方「到價進場通知」，裡面有「1 我的 Telegram」。不是另一個頁面。
6. **看不到收藏或 Telegram 設定時：** 先 `git pull` 並重啟 serve.py，瀏覽器按 Ctrl+F5，確認網址是 `127.0.0.1` 或 `localhost`。不要自己補做一個設定頁。

安裝完成回報四件事：commit 編號、開啟的網址、`alert-panel` 有找到、學生已看到「我的收藏」裡的 Telegram 設定。

## 工作規則

- 先讀 README、docs/source-map.md、strategies/momentum_eod/spec.json。區分原始來源、明確規則、未知與教學新增項。
- 正式回測只用雪鴞 api.bt。資料不足先記錄，不默默換資料源、引擎、股票或期間。
- 帳密只由 scripts/owl_login.py 讀本機 .env；不要讀取、回傳或提交帳密。不要上傳 .local、大量原始行情或供應商安裝檔。
- 改策略先建立 strategies/<新名稱>/；複製並記錄原規格，先寫假設再執行，保留失敗結果。現有 run_research.py 僅讀 momentum_eod；新增策略要明確調整入口，不能只改說明文字。
- 不把來源畫面當成隱藏公式證據；不把盤後近似當成原軟體盤中完整版。
- 同口徑比較：每組獨立資金、固定成本、相同時段。不得把單檔獨立結果相加當成投資組合。
- Telegram Token 由學生在收藏頁或本機編輯器填入 `.local/telegram.env`；AI 不讀取、不回顯。到價通知只提醒、不下單，查價至少間隔 300 秒、最多 20 檔。
- 出場訊號是學生作業：先問完 docs/exit-signals.md 的規格問題，學生回答後才實作，不先給門檻答案。
- 完成須有產物與驗收證據，更新 progress.json。暫停寫目前檔案、成功/失敗、阻礙、下一步到 resume.md；不把靜態進度當成正在背景執行。
