#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import asyncio
import requests
from playwright.async_api import async_playwright

# —— 要監控的商品頁面列表 —— 
PRODUCT_URLS = [
    "https://www.momentum.com.tw/products/HO1162013BBLC",
    "https://www.momentum.com.tw/products/HO1162013BWHT",
]

# —— 標準化後要檢查的尺碼 —— 
TARGET_SIZES = ["US8.5", "US9"]

def notify_via_telegram(size: str, url: str):
    """使用 Telegram Bot API 發送補貨通知"""
    token   = os.getenv("TELEGRAM_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    text    = f"[補貨通知] {size} 有貨啦！\n{url}"
    api_url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "disable_web_page_preview": True
    }
    r = requests.post(api_url, data=payload)
    if r.status_code == 200:
        print(f"[Telegram] 已通知 {chat_id}: {text}")
    else:
        print(f"[Telegram] 推播失敗 {r.status_code}: {r.text}")

async def check_stock():
    """用 Playwright 檢查每個頁面指定尺寸是否有貨（支援 'US8.5' / 'US 8.5' 兩種格式）"""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/115.0.0.0 Safari/537.36"
            )
        )

        for url in PRODUCT_URLS:
            # 1. 開啟頁面並等所有 JS 請求結束
            await page.goto(url, timeout=60000)
            await page.wait_for_load_state("networkidle")
            # 2. 等至少一個尺寸按鈕現身，確保整個尺碼區塊載入完成
            await page.wait_for_selector("div.swatch-option", timeout=30000)

            # 3. 依序檢查每個按鈕
            buttons = await page.query_selector_all("div.swatch-option")
            for btn in buttons:
                raw_label = await btn.get_attribute("data-option-label") or ""
                # 將空格去掉，以支援 "US8.5" / "US 8.5" 兩種格式
                norm_label = raw_label.replace(" ", "")
                # 只處理我們關心的兩種尺寸
                if norm_label not in TARGET_SIZES:
                    continue

                # 4. 檢查是否有售罄的 class 或 disabled 屬性
                cls = await btn.get_attribute("class") or ""
                if any(x in cls for x in ["sold-out", "disabled", "out-of-stock"]):
                    print(f"[已售罄] {norm_label} 在此頁面顯示售完 ({url})")
                    continue

                # 5. 最後再檢查按鈕是否可見（display:block）
                if await btn.is_visible():
                    notify_via_telegram(norm_label, url)
                else:
                    print(f"[隱藏] {norm_label} 在此頁面為 display:none ({url})")

        await browser.close()

if __name__ == "__main__":
    asyncio.run(check_stock())
