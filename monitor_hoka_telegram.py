#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os, asyncio, requests
from playwright.async_api import async_playwright

PRODUCT_URLS = [
    "https://www.ispo.com.tw/ho1162013bwht.html",
    "https://www.ispo.com.tw/ho1162013bblc.html",
]
SIZES = ["US8.5", "US9", "US10"]

def notify_via_telegram(size, url):
    token = os.getenv("TELEGRAM_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    text = f"[補貨通知] {size} 有貨啦！\n{url}"
    api_url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {"chat_id": chat_id, "text": text, "disable_web_page_preview": True}
    r = requests.post(api_url, data=payload)
    print(f"[Telegram] Status {r.status_code}: {r.text}")

async def check_stock():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        for url in PRODUCT_URLS:
            await page.goto(url, timeout=60000)
            await page.wait_for_selector(f'div.swatch-option[data-option-label="{SIZES[0]}"]')
            for size in SIZES:
                sel = f'div.swatch-option[data-option-label="{size}"]'
                if await page.locator(sel).is_visible():
                    notify_via_telegram(size, url)
        await browser.close()

if __name__ == "__main__":
    asyncio.run(check_stock())
