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
TIMEOUT = 12

# 酒店高频端口
PRIMARY_PORTS = [8000, 8080, 9901, 8082, 8888, 9001, 8001, 8090, 9999, 888, 9003, 8081, 50001]

def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")
    sys.stdout.flush()

def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    if not os.path.exists(LOCAL_SOURCE):
        log("❌ 找不到源码文件"); return

    try:
        with open(LOCAL_SOURCE, "r", encoding="utf-8") as f:
            content = f.read()

        # 1. 精准提取：寻找 gotoIP 函数里的 Base64 字符串
        # 对应源码：onclick="gotoIP('MTc1LjExLjczLjIzMA==', 'hotel')"
        b64_list = re.findall(r"gotoIP\('([^']+)',\s*'hotel'\)", content)
        
        found_ips = []
        for b in b64_list:
            try:
                decoded = base64.b64decode(b).decode('utf-8')
                # 验证是否为合法 IP 格式
                if re.match(r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$", decoded):
                    if decoded not in found_ips:
                        found_ips.append(decoded)
            except: continue

        # 2. 存证（不管成没成功都写文件）
        with open(DEBUG_OUTPUT, "w", encoding="utf-8") as df:
            if found_ips:
                df.write("\n".join(found_ips))
                log(f"✅ 提取成功！共发现 {len(found_ips)} 个酒店 IP")
            else:
                df.write("FAILED: No IPs found in gotoIP functions.")
                log("❌ 提取失败：未发现 gotoIP 函数特征")

        if not found_ips: return

        # 3. 选取前 6 个进行扫描
        target_ips = found_ips[:MAX_IP_COUNT]
        log(f"🚀 开始扫描前 {len(target_ips)} 个目标...")

        for ip in target_ips:
            log(f"\n📡 正在探测 IP: {ip}")
            success = False
            for port in PRIMARY_PORTS:
                sys.stdout.write(f"  ➜ {port} ")
                sys.stdout.flush()
                
                url = f"https://iptv.cqshushu.com/index.php?s={ip}:{port}&t=hotel&channels=1&download=m3u"
                try:
                    time.sleep(random.uniform(0.5, 1.0))
                    res = requests.get(url, timeout=TIMEOUT)
                    if res.status_code == 200 and "#EXTINF" in res.text:
                        sys.stdout.write("【✅】\n")
                        # 命名并保存
                        with open(os.path.join(OUTPUT_DIR, f"Hotel_{ip.replace('.','_')}_{port}.m3u"), "w", encoding="utf-8") as m3u:
                            m3u.write(res.text)
                        success = True; break
                except: pass
                sys.stdout.write("✕ ")
                sys.stdout.flush()
            
            if not success: print(f"\n⚠️ {ip} 无响应")

    except Exception as e:
        log(f"❌ 程序崩溃: {e}")

if __name__ == "__main__":
    main()
