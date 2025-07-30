#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import asyncio
import requests
from playwright.async_api import async_playwright

# —— 要監控的商品頁面列表 —— 
PRODUCT_URLS = [
    "https://www.ispo.com.tw/ho1162013bwht.html",
    "https://www.ispo.com.tw/ho1162013bblc.html",
]

# —— 只檢查這兩個尺寸 —— 
SIZES = ["US8.5", "US9"]

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
    """用 Playwright 檢查每個頁面指定尺寸是否有貨"""
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
            # 1. 開啟頁面並等所有網路請求完成
            await page.goto(url, timeout=60000)
            await page.wait_for_load_state("networkidle")
            # 2. 等任意一個尺寸按鈕載入完畢
            await page.wait_for_selector("div.swatch-option", timeout=30000)

            # 3. 依序檢查 US8.5 與 US9
            for size in SIZES:
                sel     = f'div.swatch-option[data-option-label="{size}"]'
                locator = page.locator(sel)

                # 如果根本沒有這個尺寸，就跳過
                if await locator.count() == 0:
                    print(f"[跳過] {size} 不在 {url}")
                    continue

                # 如果存在且可見 (display:block)，才通知
                if await locator.is_visible():
                    notify_via_telegram(size, url)
                else:
                    print(f"[沒貨] {size} 在 {url} 顯示 none")

        await browser.close()

if __name__ == "__main__":
    asyncio.run(check_stock())
