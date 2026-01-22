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
HISTORY_FILE = os.path.join(OUTPUT_DIR, "hotel_history.txt") # 独立的酒店历史表
MAX_IP_COUNT = 6  
TIMEOUT = 12 

PRIMARY_PORTS = [8082, 9901, 888, 9001, 9003, 9888, 8080, 8000, 9999, 8888, 8090, 8081, 8181, 8899, 8001, 85, 808, 20443]

UA_LIST = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"
]

# ======================
# 核心逻辑：周一清理 & 记录管理
# ======================

def manage_hotel_history():
    """周一删除 hotel_history.txt"""
    if datetime.now().weekday() == 0: # 0是周一
        if os.path.exists(HISTORY_FILE):
            print("📅 周一例行清理：删除旧的酒店 IP 记录表。")
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

# ======================
# 辅助函数
# ======================

def clean_name(name):
    """提取 group-title 最后一节并去除非法字符"""
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

# ======================
# 主程序
# ======================

def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    history_ips = manage_hotel_history()
    
    print(f"🚀 启动酒店源改进版抓取任务")
    
    try:
        r = requests.get(HOME_URL, headers=get_headers(), timeout=TIMEOUT)
        ips = list(dict.fromkeys(re.findall(r"\b(?:\d{1,3}\.){3}\d{1,3}\b", r.text)))
        # 酒店源通常在首页前 MAX_IP_COUNT 个
        target_ips = [ip for ip in ips if not ip.startswith("127")][:MAX_IP_COUNT]
    except Exception as e:
        print(f"❌ 首页失败: {e}"); return

    # 核心改进：对比历史 IP，直接跳过已抓过的
    new_ips = [ip for ip in target_ips if ip not in history_ips]
    
    if not new_ips:
        print("✅ 选定的 6 个酒店 IP 均已记录在案，跳过本次抓取。")
        return

    print(f"🎯 待探测新酒店 IP: {new_ips}")

    fofa_blocked = False
    for idx, ip in enumerate(new_ips, 1):
        print(f"\n[{idx}/{len(new_ips)}] 📡 探测新 IP: {ip}")
        
        test_ports = []
        if not fofa_blocked:
            f_ports = get_fofa_ports(ip)
            if f_ports is None:
                fofa_blocked = True
                test_ports = PRIMARY_PORTS
            else:
                test_ports = f_ports + [p for p in PRIMARY_PORTS if p not in f_ports]
        else:
            test_ports = PRIMARY_PORTS

        success_count = 0
        for port in test_ports:
            print(f"    ➜ 尝试端口 {port} ... ", end="", flush=True)
            content = scan_ip_port(ip, port)
            
            if content:
                # 提取分类命名
                group_match = re.search(r'group-title="(.*?)"', content)
                group_name = clean_name(group_match.group(1)) if group_match else "未知分类"
                
                filename = f"{group_name}_{ip}_{port}.m3u"
                with open(os.path.join(OUTPUT_DIR, filename), "w", encoding="utf-8") as f:
                    f.write(content)
                
                save_history(ip, port)
                print(f"✅ 成功! 保存为: {filename}")
                
                success_count += 1
                # 设定：单个 IP 最多抓取 2 个端口源，防止冗余
                if success_count >= 2:
                    print(f"    💡 已获取该 IP 的 2 个端口，停止后续尝试。")
                    break 
            else:
                print("✕")
        
        time.sleep(random.uniform(5, 10))

    print("\n任务完成！")

if __name__ == "__main__":
    main()
