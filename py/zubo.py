import requests
import re
import os
import time
import base64
import random
from datetime import datetime

# ======================
# 配置区
# ======================
HOME_URL = "https://iptv.cqshushu.com/"
OUTPUT_DIR = "zubo"
HISTORY_FILE = os.path.join(OUTPUT_DIR, "history.txt")
MAX_IP_COUNT = 6  # 组播源通常取首页后 6 个
TIMEOUT = 12

# 常用组播端口
PRIMARY_MULTICAST_PORTS = [
    6636, 16888, 5002, 8055, 8288, 8880, 5555, 55555, 7000, 6003, 9999, 8012, 10000, 8888, 4022, 8188, 8022, 7777, 5146, 5140, 4056, 12320, 
    10000, 8080, 8000, 9901, 8090, 8181, 1234, 4000, 4001, 5148, 12345, 8805, 8187, 9926, 8222, 8808, 8883, 8686, 8188, 4023, 8848, 6666, 
    9000, 9001, 888, 9003, 8082, 20443, 85, 8081, 8001, 8899
]

UA_LIST = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"
]

def manage_history():
    """周一准时清理 history.txt"""
    if datetime.now().weekday() == 0:
        if os.path.exists(HISTORY_FILE):
            print("📅 周一检测：正在清理旧的组播 IP 记录表...")
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
    
    print(f"🚀 启动组播源抓取任务 (目标数量: 后 {MAX_IP_COUNT} 个 IP)")
    
    try:
        r = requests.get(HOME_URL, headers=get_headers(), timeout=TIMEOUT)
        ips = list(dict.fromkeys(re.findall(r"\b(?:\d{1,3}\.){3}\d{1,3}\b", r.text)))
        # 组播源通常取首页最后 MAX_IP_COUNT 个
        target_ips = [ip for ip in ips if not ip.startswith("127")][-MAX_IP_COUNT:]
        print(f"📍 首页获取到目标 IP 列表: {target_ips}")
    except Exception as e:
        print(f"❌ 首页访问失败: {e}"); return

    # 第一遍：显示所有 IP 状态
    print("\n--- IP 状态检查 ---")
    new_ips = []
    for ip in target_ips:
        if ip in history_ips:
            print(f" ⏩ IP {ip} -> [历史记录已存在，跳过]")
        else:
            print(f" 🎯 IP {ip} -> [发现新 IP，准备扫描]")
            new_ips.append(ip)

    if not new_ips:
        print("\n✅ 所有 IP 均已记录，无需执行新抓取。")
        return

    # 第二遍：抓取新 IP
    print(f"\n--- 开始探测 {len(new_ips)} 个新 IP ---")
    fofa_blocked = False
    for idx, ip in enumerate(new_ips, 1):
        print(f"\n[{idx}/{len(new_ips)}] 📡 探测中: {ip}")
        f_ports = get_fofa_ports(ip)
        test_ports = f_ports + [p for p in PRIMARY_MULTICAST_PORTS if p not in f_ports] if f_ports is not None else PRIMARY_MULTICAST_PORTS
        
        success_count = 0
        for port in test_ports:
            print(f"    ➜ 尝试端口 {port} ... ", end="", flush=True)
            content = scan_ip_port(ip, port)
            if content:
                filename = f"multicast_{ip}_{port}.m3u"
                with open(os.path.join(OUTPUT_DIR, filename), "w", encoding="utf-8") as f:
                    f.write(content)
                save_history(ip, port)
                print(f"✅ 成功! 保存为: {filename}")
                success_count += 1
                if success_count >= 2: # 单个 IP 抓双端口
                    print(f"    💡 已获取 2 个端口源，切换下个 IP。")
                    break
            else:
                print("✕")
        time.sleep(random.uniform(5, 10))

if __name__ == "__main__":
    main()
