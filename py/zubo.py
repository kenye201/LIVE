import os
import re
import base64
import time
import cloudscraper  # 替换 requests

HOME_URL = "https://iptv.cqshushu.com/"
OUTPUT_DIR = "zubo"

def decode_base64(data):
    try:
        missing_padding = len(data) % 4
        if missing_padding:
            data += '=' * (4 - missing_padding)
        decoded = base64.b64decode(data).decode('utf-8')
        if re.match(r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$", decoded):
            return decoded
    except:
        pass
    return None

def main():
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)

    # 创建一个可以绕过验证的 scraper 实例
    scraper = cloudscraper.create_scraper(
        browser={
            'browser': 'chrome',
            'platform': 'windows',
            'desktop': True
        }
    )

    print("🚀 正在通过 Cloudscraper 绕过验证页面...")
    try:
        response = scraper.get(HOME_URL, timeout=20)
        html = response.text
        
        # 打印前 150 字确认是否成功进入主页
        print(f"📄 页面快照: {html[:150].strip()}...")

        if "验证中" in html or "document.body" in html and len(html) < 1000:
            print("❌ 绕过失败，依然停留在验证页。")
            return

        # 提取所有看起来像 Base64 的字符串
        found_ips = set()
        # 匹配 gotoIP('...') 或 data-ip='...' 中的内容
        potential_strings = re.findall(r"['\"]([A-Za-z0-9+/=]{8,})['\"]", html)
        
        for s in potential_strings:
            ip = decode_base64(s)
            if ip:
                found_ips.add(ip)

        print(f"📍 发现有效 IP: {list(found_ips)}")

        count = 0
        ports = ['8001', '8000', '4022', '16888']
        for ip in found_ips:
            for port in ports:
                # 使用相同的 scraper 实例（携带 Cookie）下载文件
                down_url = f"{HOME_URL}download.php?s={ip}:{port}&t=mcast"
                try:
                    m3u_res = scraper.get(down_url, timeout=10)
                    if "#EXTINF" in m3u_res.text:
                        filename = f"{ip.replace('.', '_')}_{port}.m3u"
                        with open(os.path.join(OUTPUT_DIR, filename), "w", encoding="utf-8") as f:
                            f.write(m3u_res.text)
                        print(f"✅ 成功抓取: {ip}:{port}")
                        count += 1
                        break
                except:
                    continue
        
        print(f"🏁 任务结束，共抓取 {count} 个源。")

    except Exception as e:
        print(f"❌ 运行异常: {e}")

if __name__ == "__main__":
    main()
