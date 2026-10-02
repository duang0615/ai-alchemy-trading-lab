---
name: momentum-research-lab
description: AI煉金術第二堂的交易解剖與模塊改造實作。使用已完成的雪鴞動能回測包，帶學生從來源、規則、驗證到Obsidian知識紀錄，保留進度与失敗經驗。
---

# 動能研究實作

先定位專案（有 README.md、reports/research.json、strategies/momentum_eod/spec.json）。找不到先問解壓位置；不猜全機資料夾、不需要帳密。讀專案 AGENTS.md 与 docs/classroom.md，再選下列模式。

## 交易解剖（首次先做）

先让學生看index.html，不要求安裝新軟體。讀docs/source-map.md，辨認來源、未知、教學新增。先提出學生可以回答的問題，再讀reports/research.json的6533成功与失敗，對照該run的trade_detail.csv、audit.json、accounting_audit.json。不要只報漂亮數字。説明期末強制出場、成本、實際成交与還原價的差別。完成三句心得Markdown，請學生核對後存自己的Obsidian；更新進度与證據。

## 模塊改造

學生先選一項：成交量／20MA／持有3或10日／額外成本；先寫預期。查看完成版comparison与account_comparison，比较同一時段、資金口徑，保留變差或無效结果。有學生自己的雪鴞Python与.env才重跑，帳密只由owl_login.py讀，不展示。執行README的兩個指令；不另換引擎。如果要新增規則，先複製規格到strategies/<新名稱>，明確接好新的入口与報告過濾，不只修改中文敘述。不得修改原始研究去挑最佳答案。

## 完成与暫停

驗收至少包含：次日開盤、費用、期末帳務、沒有用未來資料、比较的分母一致。產物与證據不足不得標completed。失敗写原因、嘗試、结果与下一步，不能寫成「已修好」。更新progress.json，暂時停工寫resume.md（進度／檔案／驗收／阻礙／下一步）。這是靜態紀錄，不代表背景代理在線，也沒有自動Telegram/Dify同步。若學生想接这些功能，另立任務与驗收。

所有結論區分「本次歷史觀察」「尚未證明」「下一步」。提醒人工四檔、存活者偏差、還原價与成交限制；不用泛泛的警語代替具體證據。課程用語用「這堂課的主軸」「課程結束之後你要學會」。
