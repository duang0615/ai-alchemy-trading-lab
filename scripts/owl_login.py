# -*- coding: utf-8 -*-
"""
owl_login.py — 登入雪鴞，回傳 api 物件。帳密由這支程式自己讀 .env，不印、不回傳。

用法（在「裝雪鴞的那個 python」裡）：
    from owl_login import login
    api = login(r"C:\\...\\.env")      # 不給路徑 → 找目前工作目錄的 .env

    api.MSMP.日_K.Close["2330"]        # 之後就照 SKILL.md 的表用
"""
from __future__ import annotations

import contextlib
import io
import os
import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass


def _read_env(env_path: str | None) -> tuple[str, str, str]:
    p = Path(env_path) if env_path else Path.cwd() / ".env"
    if p.is_dir():
        p = p / ".env"
    if not p.exists():
        raise FileNotFoundError(
            f"找不到 .env：{p}\n→ 問使用者「你裝雪鴞的那個資料夾在哪？裡面有一個 .env」，"
            f"問到之後寫回 snowyowl skill 的 SKILL.md「設定」那段。"
        )
    kv = {}
    for line in p.read_text(encoding="utf-8-sig").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            kv[k.strip()] = v.strip().strip('"').strip("'")
    uid = kv.get("SNOWYOWL_PERSON_ID") or kv.get("SNOWYOWL_ID") or \
        next((v for k, v in kv.items() if "OWL" in k.upper() and "ID" in k.upper()), "")
    pwd = kv.get("SNOWYOWL_PERSON_PWD") or kv.get("SNOWYOWL_PW") or \
        next((v for k, v in kv.items() if "OWL" in k.upper()
              and any(t in k.upper() for t in ("PW", "PASS", "PWD"))), "")
    typ = kv.get("SNOWYOWL_LOGIN_TYPE", "account") or "account"
    if not uid or not pwd or "填這裡" in (uid, pwd):
        raise ValueError(
            "雪鴞的 .env 還沒填帳號密碼。\n"
            "→ 跟使用者說：「請用記事本打開 .env，把兩個『填這裡』換成你的星系帳號密碼，存檔後再跑一次。」\n"
            "⛔ 不要叫他在對話框打帳密。"
        )
    return uid, pwd, typ


def login(env_path: str | None = None):
    """登入雪鴞。第一次約 30 秒起（要下載快取）。登入失敗直接拋錯。"""
    try:
        import snowyowl as so
    except ImportError:
        raise ImportError(
            "這個 python 裡沒有 snowyowl。\n"
            "→ 要用「裝雪鴞的那個環境」的 python（snowyowl skill 的 SKILL.md「設定」有寫路徑）。"
        )
    uid, pwd, typ = _read_env(env_path)
    with contextlib.redirect_stdout(io.StringIO()):          # 登入會噴一堆系統訊息，吞掉
        api = so.login(uid, pwd, type=typ)
    del uid, pwd
    if not all(hasattr(api, n) for n in ("Block", "MSMP")):
        raise RuntimeError(
            "雪鴞登入沒過（帳號或密碼不對）。\n"
            "→ 跟使用者說：「請確認 .env 裡是你星系 i-zone 的帳號密碼，改好存檔再跑一次。」"
        )
    return api


if __name__ == "__main__":
    api = login(sys.argv[1] if len(sys.argv) > 1 else None)
    c = api.MSMP.日_K.Close
    print("登入 OK")
    print(f"台股日線：{c.shape[1]:,} 檔、{c.shape[0]:,} 個交易日，資料到 {str(c.index.max())[:10]}")
