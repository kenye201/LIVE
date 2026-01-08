import asyncio
import base64
import os
import sys
from playwright.async_api import async_playwright

BASE_URL = "https://iptv.cqshushu.com/?t=hotel"
OUT_FILE = "test/hotel_m3u_links.txt"
PROXY = os.environ.get("PROXY")  # 从环境变量读取代理

async def main():
    os.makedirs(os.path.dirname(OUT_FILE), exist_ok=True)

    async with async_playwright() as p:
        launch_opts = {"headless": True}
        if PROXY:
            launch_opts["proxy"] = {"server": PROXY}

        browser = await p.chromium.launch(**launch_opts)
        context = await browser.new_context()
        page = await context.new_page()

        print("访问首页...", flush=True)
        await page.goto(BASE_URL, timeout=60000)

        ip_elements = await page.query_selector_all("a.ip-link")
        ips = []
        for el in ip_elements:
            b64 = await el.get_attribute("onclick")
            if b64:
                import re
                m = re.search(r"gotoIP\('([^']+)'", b64)
                if m:
                    try:
                        ip = base64.b64decode(m.group(1)).decode()
                        ips.append(ip)
                    except:
                        pass

        print(f"发现 {len(ips)} 个 IP: {ips}", flush=True)
        all_links = []

        for ip in ips:
            print(f"\n处理 IP: {ip}", flush=True)
            try:
                await page.evaluate(f"""
                    () => {{
                        const ipEl = Array.from(document.querySelectorAll('a.ip-link'))
                                      .find(el => el.textContent.includes('{ip}'));
                        if(ipEl) ipEl.click();
                    }}
                """)
                await page.wait_for_selector("div.download-section a.download-btn.m3u", timeout=15000)
                m3u_link_el = await page.query_selector("div.download-section a.download-btn.m3u")
                if m3u_link_el:
                    href = await m3u_link_el.get_attribute("href")
                    full_link = f"http://iptv.cqshushu.com/{href.lstrip('?')}"
                    all_links.append(full_link)
                    print(f"  └─ M3U 链接: {full_link}", flush=True)
            except Exception as e:
                print(f"  └─ [异常] {e}", flush=True)

        await browser.close()

    with open(OUT_FILE, "w", encoding="utf-8") as f:
        for link in sorted(set(all_links)):
            f.write(link + "\n")

    print(f"\n完成，共获取 {len(all_links)} 条 M3U", flush=True)
    print(f"保存至 {OUT_FILE}", flush=True)


if __name__ == "__main__":
    asyncio.run(main())
