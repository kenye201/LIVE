import requests
import re
import os
import time
import base64
import random
from datetime import datetime

# ======================
# 配置区 (保持你原来的)
# ======================
HOME_URL = "https://iptv.cqshushu.com/"
OUTPUT_DIR = "zubo"
HISTORY_FILE = os.path.join(OUTPUT_DIR, "history.txt")
MAX_IP_COUNT = 6  
TIMEOUT = 12

PRIMARY_MULTICAST_PORTS = [
    6636, 16888, 5002, 3333, 8188, 8055, 8288, 8880, 5555, 55555, 58888, 7000, 7700, 6003, 9988, 9999, 8012, 10000, 8888, 4022, 8188, 8022, 7777, 5146, 5140, 4056, 12320, 
    10000, 8080, 8000, 9901, 8090, 8181, 1234, 4000, 4001, 5148, 12345, 8805, 8187, 9926, 8222, 8808, 8883, 8686, 8188, 4023, 8848, 6666, 
    9000, 9001, 888, 9003, 8082, 20443, 85, 8081, 8001, 8003, 6001, 8899
]

UA_LIST = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"
]

def manage_history():
    if datetime.now().weekday() == 0:
        if os.path.exists(HISTORY_FILE):
            os.remove(HISTORY_FILE)
    history_ips = set()
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            for line in f:
                if ":" in line:
                    history_ips.add(line.split(':')[0].strip())
    return history_ips

def save_history(ip, port):
    with open(HISTORY_FILE, "a", encoding="utf-8") as f:
        f.write(f"{ip}:{port}\n")

def get_headers():
    return {"User-Agent": random.choice(UA_LIST), "Referer": "https://fofa.info/"}

def get_fofa_ports(ip):
    time.sleep(random.uniform(8, 15))
    try:
        query = base64.b64encode(ip.encode()).decode()
        res = requests.get(f"https://fofa.info/result?qbase64={query}", headers=get_headers(), timeout=15)
        ports = set(re.findall(rf'{ip}:(\d+)', res.text) + re.findall(r'port-item.*?(\d+)</a>', res.text, re.S))
        return sorted([int(p) for p in ports if int(p) not in {22, 23, 443, 80, 53, 3306, 3389}])
    except: return []

def scan_ip_port(ip, port):
    url = f"https://iptv.cqshushu.com/?s={ip}:{port}&t=multicast&channels=1&download=m3u"
    try:
        time.sleep(random.uniform(2, 4))
        res = requests.get(url, headers=get_headers(), timeout=TIMEOUT)
        if res.status_code == 200 and "#EXTINF" in res.text:
            return res.text
    except: pass
    return None

def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    history_ips = manage_history()
    
    try:
        r = requests.get(HOME_URL, headers=get_headers(), timeout=TIMEOUT)
        # 这里用你最原始的正则逻辑
        ips = list(dict.fromkeys(re.findall(r"\b(?:\d{1,3}\.){3}\d{1,3}\b", r.text)))
        target_ips = [ip for ip in ips if not ip.startswith("127")][-MAX_IP_COUNT:]
    except: return

    for ip in target_ips:
        if ip in history_ips: continue
        
        f_ports = get_fofa_ports(ip)
        test_ports = f_ports + [p for p in PRIMARY_MULTICAST_PORTS if p not in f_ports]
        
        for port in test_ports:
            content = scan_ip_port(ip, port)
            if content:
                # --- 重点：只在这里增加提取地区运营商的逻辑 ---
                provider = "未知"
                match = re.search(r'group-title="([^"]+)"', content)
                if match:
                    # 提取 group-title 的内容并简单清洗
                    title = match.group(1).replace("组播", "").strip()
                    provider = title.split()[-1] if " " in title else title
                
                # 按照你的要求命名
                filename = f"{provider}-{ip.replace('.', '_')}.m3u"
                
                with open(os.path.join(OUTPUT_DIR, filename), "w", encoding="utf-8") as f:
                    f.write(content)
                save_history(ip, port)
                print(f"✅ 成功! 保存为: {filename}")
                break
        time.sleep(random.uniform(5, 10))

if __name__ == "__main__":
    main()
