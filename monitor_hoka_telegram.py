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
            # 1. 開啟頁面並等所有 JS 請求結束
            await page.goto(url, timeout=60000)
            await page.wait_for_load_state("networkidle")
            # 2. 等至少一個尺寸按鈕現身，確保整個尺碼區塊載入完成
            await page.wait_for_selector("div.swatch-option", timeout=30000)

            # 3. 只對 SIZES 裡的尺寸做檢查
            for size in SIZES:
                sel     = f'div.swatch-option[data-option-label="{size}"]'
                locator = page.locator(sel)

                # 3.1 欲檢查的尺寸不存在於頁面 → 跳過
                if await locator.count() == 0:
                    print(f"[跳過] {size} 不在此頁面 ({url})")
                    continue

                # 3.2 如果有 class 標記為 disabled / sold-out / out-of-stock → 代表已售罄，跳過
                class_attr = await locator.get_attribute("class") or ""
                sold_out_class = ["disabled", "sold-out", "out-of-stock"]
                if any(c in class_attr for c in sold_out_class):
                    print(f"[已售罄] {size} 在此頁面顯示售完 ({url})")
                    continue

                # 3.3 最後再檢查 display 狀態（保險起見）
                if await locator.is_visible():
                    notify_via_telegram(size, url)
                else:
                    print(f"[隱藏] {size} 在此頁面為 display:none ({url})")

        await browser.close()

if __name__ == "__main__":
    asyncio.run(check_stock())
