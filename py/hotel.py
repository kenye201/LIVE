import requests
import re
import os
import time
import base64
import random
from datetime import datetime

# ======================
# 深度配置区
# ======================
HOME_URL = "https://iptv.cqshushu.com/"
OUTPUT_DIR = "hotel"
HISTORY_FILE = os.path.join(OUTPUT_DIR, "hotel_history.txt")
MAX_IP_COUNT = 6  # 酒店源通常取首页前 6 个
TIMEOUT = 12 

# 常用高频端口
PRIMARY_PORTS = [8082, 9901, 888, 9001, 9003, 9888, 8080, 8000, 9999, 8888, 8090, 8081, 8181, 8899, 8001, 85, 808, 20443]

UA_LIST = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"
]

def manage_hotel_history():
    """周一简单粗暴删表，其他时间读取 IP"""
    if datetime.now().weekday() == 0: # 0代表周一
        if os.path.exists(HISTORY_FILE):
            print("📅 今天是周一，执行每周例行清理：删除酒店历史 IP 表。")
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

def clean_name(name):
    if not name: return "未知分类"
    parts = name.split()
    last_part = parts[-1] if parts else name
    return re.sub(r'[\\/:*?"<>|]', '', last_part)

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
    url = f"https://iptv.cqshushu.com/?s={ip}:{port}&t=hotel&channels=1&download=m3u"
    try:
        time.sleep(random.uniform(2, 4))
        res = requests.get(url, headers=get_headers(), timeout=TIMEOUT)
        if res.status_code == 200 and "#EXTINF" in res.text:
            return res.text
    except: pass
    return None

def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    history_ips = manage_hotel_history()
    
    print(f"🚀 启动酒店源抓取任务 (目标数量: {MAX_IP_COUNT})")
    
    try:
        r = requests.get(HOME_URL, headers=get_headers(), timeout=TIMEOUT)
        ips = list(dict.fromkeys(re.findall(r"\b(?:\d{1,3}\.){3}\d{1,3}\b", r.text)))
        target_ips = [ip for ip in ips if not ip.startswith("127")][:MAX_IP_COUNT]
        print(f"📍 首页获取到目标 IP 列表: {target_ips}")
    except Exception as e:
        print(f"❌ 首页访问失败: {e}"); return

    # 第一遍遍历：打印所有 IP 的当前状态
    print("\n--- IP 状态检查 ---")
    new_ips_to_scan = []
    for ip in target_ips:
        if ip in history_ips:
            print(f" ⏩ IP {ip} -> [已存在于历史表，跳过]")
        else:
            print(f" 🎯 IP {ip} -> [新发现，准备探测]")
            new_ips_to_scan.append(ip)

    if not new_ips_to_scan:
        print("\n✅ 所有目标 IP 均已处理过，本次无须探测新 IP。")
        return

    # 第二遍遍历：开始真正抓取新 IP
    print(f"\n--- 开始探测 {len(new_ips_to_scan)} 个新 IP ---")
    fofa_blocked = False
    for idx, ip in enumerate(new_ips_to_scan, 1):
        print(f"\n[{idx}/{len(new_ips_to_scan)}] 📡 正在探测: {ip}")
        f_ports = get_fofa_ports(ip)
        test_ports = f_ports + [p for p in PRIMARY_PORTS if p not in f_ports] if f_ports is not None else PRIMARY_PORTS
        
        success_count = 0
        for port in test_ports:
            print(f"    ➜ 尝试端口 {port} ... ", end="", flush=True)
            content = scan_ip_port(ip, port)
            if content:
                # ... 前面的保存逻辑保持不变 ...
                save_history(ip, port)
                print(f"✅ 成功! 保存为: {filename}")
                
                found_success = True # 标记该 IP 已成功
                break  # <--- 关键：抓到一个就立刻跳出当前端口循环，去弄下一个 IP
            else:
                print("✕")
        time.sleep(random.uniform(5, 10))

    print("\n任务完成！所有新文件已保存在 hotel 目录。")

if __name__ == "__main__":
    main()
