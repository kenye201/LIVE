import requests
import re
import os
import time

HOME_URL = "https://iptv.cqshushu.com/"
OUTPUT_DIR = "test"
MAX_IP_COUNT = 8  # 稍微增加几个，因为后面会有去重
TIMEOUT = 6

PRIMARY_PORTS = [8082, 9901, 8080, 8000, 9999, 8888, 8090, 8081, 8181, 8899, 8001, 85, 808]
SECONDARY_PORTS = [8088, 8001, 10000, 18080]
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

def fetch_ips():
    print("📥 抓取首页 IP...")
    r = requests.get(HOME_URL, headers=HEADERS, timeout=TIMEOUT)
    ips = re.findall(r"\b(?:\d{1,3}\.){3}\d{1,3}\b", r.text)
    unique_ips = []
    for ip in ips:
        if ip not in unique_ips and not ip.startswith("127"):
            unique_ips.append(ip)
        if len(unique_ips) >= MAX_IP_COUNT: break
    return unique_ips

def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    ips = fetch_ips()
    for ip in ips:
        print(f"\n🔍 扫描: {ip}")
        for port in PRIMARY_PORTS + SECONDARY_PORTS:
            url = f"https://iptv.cqshushu.com/?s={ip}:{port}&t=hotel&channels=1&download=m3u"
            try:
                r = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
                if r.status_code == 200 and "#EXTINF" in r.text:
                    filename = f"raw_{ip}_{port}.m3u"
                    with open(os.path.join(OUTPUT_DIR, filename), "w", encoding="utf-8") as f:
                        f.write(r.text)
                    print(f"  ✅ 成功保存: {filename}")
                    break 
            except: pass
            time.sleep(0.5)

if __name__ == "__main__":
    main()
