---
name: snowyowl-pattern-lab
description: 在學生專案中使用雪鴞OHLC建立K線型態、走勢輪廓和自訂繪圖選股，協助學生一次改一個門檻，保存規格、反例與修改紀錄。
---

# 型態選股實作

找到包含`stock-picker/pattern-engine.js`的專案，讀AGENTS.md和[課堂答案](../../docs/pattern-lab.md)。沿用使用者已選的交易週期。

- K線以OHLC的明確比例判定，29種定義見`pattern-catalog.json`。前期方向、長短實體與影線倍數是本版規格，不歸給來源網站。多根分類中的上升／下降三法用5根。
- 走勢19種示意模板用收盤輪廓的正規化RMSE；自訂繪圖採同一計算模塊。相似度不是勝率，沒有自動驗證頸線、突破或主力意圖。一字形底有獨立振幅規則。
- 型態公開18檔（含兩檔事後挑選範例）和本機資料範圍分開記錄，原條件選股仍是16檔。日線、已完成週線、已完成月線不能混比；缺值不補零，訊號搜尋多日與單日分開。
- 修改前寫假設，保留原版本、候選數和一筆核對。先只改小實體／十字比例、K棒數、相似門檻或一段輪廓中的一項。
- 資料入口`build_patterns.py --env <本機.env>`，只由登入助手讀帳密，原始歷史留`.local`。不要讀、輸出或提交帳密。
- 唯一計算入口為`pattern-engine.js`。規則更動同步`make_pattern_catalog.py`並重新產生JSON；執行`node --test stock-picker/test_patterns.cjs`，再實際核對符合、不符合與資料不足案例。
- 修改UI要操作日／週／月、篩選、繪圖、存檔重開、JSON匯入匯出與Markdown下載。報告實際測過的項目，未測不寫完成。
- 保存自訂型態用JSON備份，實作過程存Markdown到自己的Obsidian。失敗也記錄理由、版本和下一步。這個Skill沒有Dify自動寫入或Telegram續工能力。

候選有了仍要定義進出場、部位、成本和資料可得時間，再另建策略目錄使用雪鴞api.bt。中斷時更新resume.md，不把保存的進度說成AI正在背景執行。
