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
MAX_IP_COUNT = 6  # 组播源取首页后 6 个
TIMEOUT = 12

# 组播常用端口池
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
    """周一清理逻辑"""
    if datetime.now().weekday() == 0:
        if os.path.exists(HISTORY_FILE):
            print("📅 今天是周一，执行每周例行清理：删除组播历史 IP 表。")
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
    
    print(f"🚀 启动组播源抓取任务 (目标数量: {MAX_IP_COUNT})")
    
    try:
        r = requests.get(HOME_URL, headers=get_headers(), timeout=TIMEOUT)
        ips = list(dict.fromkeys(re.findall(r"\b(?:\d{1,3}\.){3}\d{1,3}\b", r.text)))
        target_ips = [ip for ip in ips if not ip.startswith("127")][-MAX_IP_COUNT:]
        print(f"📍 首页获取到目标 IP 列表: {target_ips}")
    except Exception as e:
        print(f"❌ 首页访问失败: {e}"); return

    print("\n--- IP 状态检查 ---")
    new_ips_to_scan = []
    for ip in target_ips:
        if ip in history_ips:
            print(f" ⏩ IP {ip} -> [已存在于历史表，跳过探测]")
        else:
            print(f" 🎯 IP {ip} -> [新发现，准备探测]")
            new_ips_to_scan.append(ip)

    if not new_ips_to_scan:
        print("\n✅ 所有组播 IP 均已处理过，本次无须探测。")
        return

    print(f"\n--- 开始探测 {len(new_ips_to_scan)} 个新组播 IP ---")
    for idx, ip in enumerate(new_ips_to_scan, 1):
        print(f"\n[{idx}/{len(new_ips_to_scan)}] 📡 正在处理: {ip}")
        f_ports = get_fofa_ports(ip)
        test_ports = f_ports + [p for p in PRIMARY_MULTICAST_PORTS if p not in f_ports] if f_ports is not None else PRIMARY_MULTICAST_PORTS
        
        found_success = False
        for port in test_ports:
            print(f"    ➜ 尝试端口 {port} ... ", end="", flush=True)
            content = scan_ip_port(ip, port)
            
            if content:
                filename = f"zubo_{ip}_{port}.m3u"
                with open(os.path.join(OUTPUT_DIR, filename), "w", encoding="utf-8") as f:
                    f.write(content)
                save_history(ip, port)
                print(f"✅ 成功! 保存为: {filename}")
                found_success = True
                break  # <--- 抓到一个通的就停，不再测试后续端口
            else:
                print("✕")
        
        if not found_success:
            print(f"    ⚠️ IP {ip} 未能探测到有效端口")
        
        time.sleep(random.uniform(5, 10))

    print("\n组播任务完成！")

if __name__ == "__main__":
    main()
