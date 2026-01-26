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
OUTPUT_DIR = "hotel"
# 确保黑名单路径正确
HISTORY_FILE = os.path.join(OUTPUT_DIR, "hotel_history.txt")
MAX_IP_COUNT = 15   # 增加扫描深度
TIMEOUT = 25        # 增加超时容忍度

# 重新编排端口：根据实测，9999, 9901, 8888, 85 是目前酒店源最高频端口
PRIMARY_PORTS = [9999, 8000, 8080, 9901, 8082, 8888, 85, 9888, 8090, 8081, 8181, 8899, 8001, 808, 50001, 20443]

def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")
    sys.stdout.flush()

def main():
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)
    
    # 1. 加载黑名单 (hotel_history.txt)
    history_ips = set()
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            for line in f:
                if ":" in line:
                    history_ips.add(line.split(':')[0].strip())
    log(f"📜 已加载黑名单，包含 {len(history_ips)} 个已成功 IP，将自动跳过。")

    if not os.path.exists(LOCAL_SOURCE):
        log("❌ 源码文件缺失"); return

    try:
        with open(LOCAL_SOURCE, "r", encoding="utf-8") as f:
            content = f.read()

        # 2. 提取 IP
        b64_list = re.findall(r"gotoIP\('([^']+)',\s*'hotel'\)", content)
        found_ips = []
        for b in b64_list:
            try:
                decoded = base64.b64decode(b).decode('utf-8')
                if re.match(r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$", decoded):
                    # 【核心改进】在这里进行黑名单过滤
                    if decoded not in found_ips and decoded not in history_ips:
                        found_ips.append(decoded)
            except: continue

        if not found_ips:
            log("🔎 本次扫描未发现新 IP（或全部已被黑名单过滤）"); return

        log(f"✅ 发现 {len(found_ips)} 个待探测新目标。")

        # 3. 探测逻辑
        for idx, ip in enumerate(found_ips[:MAX_IP_COUNT], 1):
            log(f"📡 [{idx}] 正在探测新 IP: {ip}")
            success = False
            
            for port in PRIMARY_PORTS:
                # 严格按照你测试成功的 URL 格式
                url = f"http://iptv.cqshushu.com/index.php?s={ip}:{port}&t=hotel&channels=1&download=m3u"
                
                sys.stdout.write(f"  --> {port} ")
                sys.stdout.flush()

                try:
                    # 慢速探测，防止丢包
                    time.sleep(random.uniform(2.5, 4.5))
                    headers = {"User-Agent": "Mozilla/5.0", "Referer": "http://iptv.cqshushu.com/"}
                    res = requests.get(url, headers=headers, timeout=TIMEOUT)
                    
                    if res.status_code == 200 and "#EXTINF" in res.text:
                        sys.stdout.write("【✅】\n")
                        # 提取信息并命名
                        m = re.search(r'group-title="([^"]+)"', res.text)
                        tag = m.group(1).split()[-1] if m else "Hotel"
                        tag = re.sub(r'[\\/:*?"<>|]', '', tag)
                        
                        fn = f"{tag}_{ip.replace('.', '_')}_{port}.m3u"
                        with open(os.path.join(OUTPUT_DIR, fn), "w", encoding="utf-8") as f:
                            f.write(res.text)
                        
                        # 【核心改进】成功后写入黑名单文件
                        with open(HISTORY_FILE, "a", encoding="utf-8") as hf:
                            hf.write(f"{ip}:{port}\n")
                        
                        log(f"🎉 记录黑名单并保存: {fn}")
                        success = True
                        break
                    else:
                        sys.stdout.write("✕ ")
                except:
                    sys.stdout.write("⏰ ")
                sys.stdout.flush()
            
            if not success: print(f"\n❌ IP {ip} 扫描完所有字典端口无果")
            time.sleep(6) # IP 间休息

    except Exception as e:
        log(f"❌ 运行异常: {e}")

if __name__ == "__main__":
    main()
