import requests
import re
import os
import base64

# 尝试访问不同的入口，避开 index.php 首页的盾
TARGET_URLS = [
    "https://iptv.cqshushu.com/index.php?m=vod-type-id-1.html", # 尝试分类页
    "https://iptv.cqshushu.com/index.php?m=vod-search"         # 尝试搜索页
]
OUTPUT_DIR = "zubo"

def decode_base64(data):
    try:
        padding = len(data) % 4
        if padding: data += '=' * (4 - padding)
        decoded = base64.b64decode(data).decode('utf-8')
        if re.match(r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$", decoded):
            return decoded
    except: return None

def main():
    if not os.path.exists(OUTPUT_DIR): os.makedirs(OUTPUT_DIR)

    # 构造极度逼真的浏览器请求头
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.9",
        "Referer": "https://www.baidu.com/link?url=...", # 伪装成从百度跳转
        "Cookie": "PHPSESSID=random_session_id_" + str(os.urandom(4).hex()) # 注入虚假 Session
    }

    found_ips = set()

    for url in TARGET_URLS:
        print(f"📡 尝试访问入口: {url}")
        try:
            res = requests.get(url, headers=headers, timeout=15)
            res.encoding = 'utf-8'
            html = res.text
            
            print(f"📄 响应长度: {len(html)} | 标题: {re.search(r'<title>(.*?)</title>', html).group(1) if re.search(r'<title>(.*?)</title>', html) else 'No Title'}")

            # 如果响应中依然包含“验证中”，说明该入口也被封锁
            if "验证中" in html:
                continue

            # 抓取所有 Base64 字符串
            matches = re.findall(r"['\"]([A-Za-z0-9+/=]{8,})['\"]", html)
            for m in matches:
                ip = decode_base64(m)
                if ip: found_ips.add(ip)
            
            if found_ips: break
        except Exception as e:
            print(f"⚠️ 请求失败: {e}")

    print(f"📍 最终提取到 IP: {list(found_ips)}")

    # 后续下载逻辑
    count = 0
    if found_ips:
        for ip in found_ips:
            for port in ['8001', '8000', '4022']:
                dl_url = f"https://iptv.cqshushu.com/download.php?s={ip}:{port}&t=mcast"
                try:
                    m3u = requests.get(dl_url, headers=headers, timeout=5).text
                    if "#EXTINF" in m3u:
                        with open(f"{OUTPUT_DIR}/{ip.replace('.','_')}.m3u", "w") as f:
                            f.write(m3u)
                        count += 1
                        break
                except: continue
    print(f"✅ 任务结束，保存 {count} 个文件。")

if __name__ == "__main__":
    main()
