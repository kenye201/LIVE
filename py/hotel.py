import requests
import re
import os
import time

# 配置
HOME_URL = "https://iptv.cqshushu.com/"
OUTPUT_DIR = "test"
MAX_IP_COUNT = 6  
TIMEOUT = 6
PRIMARY_PORTS = [8082, 9901, 8080, 8000, 9999, 8888, 8090, 8081, 8181, 8899, 8001, 85, 808]
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    try:
        r = requests.get(HOME_URL, headers=HEADERS, timeout=TIMEOUT)
        ips = list(set(re.findall(r"\b(?:\d{1,3}\.){3}\d{1,3}\b", r.text)))[:MAX_IP_COUNT]
    except: return

    for ip in ips:
        if ip.startswith("127"): continue
        for port in PRIMARY_PORTS:
            url = f"https://iptv.cqshushu.com/?s={ip}:{port}&t=hotel&channels=1&download=m3u"
            try:
                res = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
                if "#EXTINF" in res.text:
                    with open(os.path.join(OUTPUT_DIR, f"raw_{ip}_{port}.m3u"), "w", encoding="utf-8") as f:
                        f.write(res.text)
                    print(f"📥 抓取成功: {ip}:{port}")
                    break
            except: pass
            time.sleep(0.3)

if __name__ == "__main__":
    main()
