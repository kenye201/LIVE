import asyncio
from playwright.async_api import async_playwright
import re
import os

async def get_real_content():
    async with async_playwright() as p:
        # 1. 启动浏览器
        browser = await p.chromium.launch(headless=True)
        
        # 2. 设置更加真实的 Context
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
            viewport={'width': 1920, 'height': 1080}
        )

        # 3. 关键：注入脚本隐藏自动化特征
        await context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
            window.chrome = { runtime: {} };
        """)

        page = await context.new_page()
        
        try:
            print("🚀 正在访问首页...")
            # 增加超时到 60 秒防止网络卡顿
            await page.goto("https://iptv.cqshushu.com/", wait_until="networkidle", timeout=60000)
            
            # 4. 强制等待 JS 验证跳转（这里多等一会儿）
            print("⏳ 等待 JS 验证跳转 (15秒)...")
            await page.wait_for_timeout(15000) 

            # 5. 调试：截个图看看，确认到底显示的是什么
            os.makedirs("debug", exist_ok=True)
            await page.screenshot(path="debug/screenshot.png")
            print("📸 截图已保存到 debug/screenshot.png")

            # 6. 获取源码并打印长度
            content = await page.content()
            print(f"📄 网页源码长度: {len(content)}")

            # 7. 提取 IP (兼容更多格式的正则)
            ips = list(dict.fromkeys(re.findall(r"(?:\d{1,3}\.){3}\d{1,3}", content)))
            # 过滤掉常见的 CDN 或内网 IP
            ips = [ip for ip in ips if not ip.startswith(('127.', '10.', '172.', '0.'))]
            
            print(f"✅ 找到 IP 列表: {ips}")
            
            # 如果抓到了内容，保存一份源码供分析
            with open("debug/source.html", "w", encoding="utf-8") as f:
                f.write(content)

            return ips

        except Exception as e:
            print(f"❌ 访问出错: {e}")
            return []
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(get_real_content())
