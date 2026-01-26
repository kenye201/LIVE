import requests
import re
import os
import time
import base64
import random
import sys
from datetime import datetime

# ======================
# 配置区
# ======================
LOCAL_SOURCE = "data/shushu_home.html"
DEBUG_OUTPUT = "data/extracted_hotel_ips.txt"
OUTPUT_DIR = "hotel"
HISTORY_FILE = os.path.join(OUTPUT_DIR, "hotel_history.txt")
MAX_IP_COUNT = 6
TIMEOUT = 15

PRIMARY_PORTS = [8000, 8080, 9901, 8082, 8888, 9001, 8001, 8090, 9999, 888, 9003, 8081, 50001]

def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")
    sys.stdout.flush()

def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    if not os.path.exists(LOCAL_SOURCE):
        log(f"❌ 找不到源码: {LOCAL_SOURCE}"); return

    try:
        with open(LOCAL_SOURCE, "r", encoding="utf-8") as f:
            content = f.read()
        
        # 1. 定位酒店区域
        hotel_content = content.split("Hotel IPTV")[1] if "Hotel IPTV" in content else content
        
        # 2. 【剥洋葱提取】
        # 提取 gotoIP('XXX', 'hotel') 里的加密字符串
        found_ips = []
        b64_matches = re.findall(r"gotoIP\('([^']+)',\s*'hotel'\)", hotel_content)
        
        log(f"🔎 找到 {len(b64_matches)} 个加密串，正在解码...")
        
        for b in b64_matches:
            try:
                # 解码 Base64
                decoded = base64.b64decode(b).decode('utf-8')
                # 只要解码出来长得像 IP 就要
                if re.match(r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$", decoded):
                    found_ips.append(decoded)
            except: continue

        # 3. 兜底提取：抓取那些带空格的明文 IP
        # 比如 1.197.252.109 可能中间混了空格
        text_ips = re.findall(r"(?:\d{1,3}\s*\.\s*){3}\d{1,3}", hotel_content)
        for tip in text_ips:
            clean_ip = tip.replace(" ", "").strip()
            if clean_ip not in found_ips:
                found_ips.append(clean_ip)

        # 4. 存证
        with open(DEBUG_OUTPUT, "w", encoding="utf-8") as df:
            df.write("\n".join(found_ips) if found_ips else "EMPTY: No IPs extracted")

        if not found_ips:
            log("❌ 依然没抓到，可能网页结构变了"); return

        log(f"✅ 成功抓取到 {len(found_ips)} 个 IP")

        # 5. 探测逻辑 (只取前 6)
        target_ips = found_ips[:MAX_IP_COUNT]
        for ip in target_ips:
            log(f"📡 探测: {ip}")
            for port in PRIMARY_PORTS:
                url = f"https://iptv.cqshushu.com/index.php?s={ip}:{port}&t=hotel&channels=1&download=m3u"
                try:
                    res = requests.get(url, timeout=TIMEOUT)
                    if "#EXTINF" in res.text:
                        log(f"  ➜ {port} 【✅】")
                        with open(os.path.join(OUTPUT_DIR, f"{ip.replace('.','_')}_{port}.m3u"), "w") as m3u:
                            m3u.write(res.text)
                        break
                except: continue
                
    except Exception as e:
        log(f"❌ 崩溃: {e}")

if __name__ == "__main__":
    main()
