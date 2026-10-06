# 學生專案工作規則

- 先讀 README、docs/source-map.md、strategies/momentum_eod/spec.json。區分原始來源、明確規則、未知與教學新增項。
- 正式回測只用雪鴞 api.bt。資料不足先記錄，不默默換資料源、引擎、股票或期間。
- 帳密只由 scripts/owl_login.py 讀本機 .env；不要讀取、回傳或提交帳密。不要上傳 .local、大量原始行情或供應商安裝檔。
- 改策略先建立 strategies/<新名稱>/；複製並記錄原規格，先寫假設再執行，保留失敗結果。現有 run_research.py 僅讀 momentum_eod；新增策略要明確調整入口，不能只改說明文字。
- 不把來源畫面當成隱藏公式證據；不把盤後近似當成原軟體盤中完整版。
- 同口徑比較：每組獨立資金、固定成本、相同時段。不得把單檔獨立結果相加當成投資組合。
- Telegram Token 由學生在收藏頁或本機編輯器填入 `.local/telegram.env`；AI 不讀取、不回顯。到價通知只提醒、不下單，查價至少間隔 300 秒、最多 20 檔。
- 出場訊號是學生作業：先問完 docs/exit-signals.md 的規格問題，學生回答後才實作，不先給門檻答案。
- 完成須有產物與驗收證據，更新 progress.json。暫停寫目前檔案、成功/失敗、阻礙、下一步到 resume.md；不把靜態進度當成正在背景執行。
