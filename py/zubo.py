import requests
import re
import os
import time
import base64
import random
from datetime import datetime, timedelta

# ======================
# 配置区
# ======================
HOME_URL = "https://iptv.cqshushu.com/"
OUTPUT_DIR = "zubo"
HISTORY_FILE = os.path.join(OUTPUT_DIR, "history.txt")
MAX_IP_COUNT = 6
TIMEOUT = 12
DAYS_TO_KEEP = 7  # 历史记录保留天数

PRIMARY_MULTICAST_PORTS = [
    6636, 16888, 5002, 8055, 8288, 8880, 5555, 55555, 7000, 6003, 9999, 8012, 10000, 8888, 4022, 8188, 8022, 7777, 5146, 5140, 4056, 12320, 
    10000, 8080, 8000,9901, 8090, 8181, 1234, 4000, 4001, 5148, 12345, 8805, 8187, 9926, 8222, 8808, 8883, 8686, 8188, 4023, 8848, 6666, 
    9000, 9001, 888, 9003, 8082, 20443, 85, 8081, 8001, 8899
]

UA_LIST = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0"
]

# ======================
# 历史记录管理函数
# ======================

def clean_history():
    """如果记录文件超过指定天数，则清理"""
    if os.path.exists(HISTORY_FILE):
        file_age = datetime.now() - datetime.fromtimestamp(os.path.getmtime(HISTORY_FILE))
        if file_age.days >= DAYS_TO_KEEP:
            print(f"🧹 历史记录已超过 {DAYS_TO_KEEP} 天，正在自动清理...")
            os.remove(HISTORY_FILE)

def load_history():
    """读取已抓取的 IP 和端口"""
    history = set()
    ip_counts = {}
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    history.add(line)
                    ip = line.split(':')[0]
                    ip_counts[ip] = ip_counts.get(ip, 0) + 1
    return history, ip_counts

def save_history(ip, port):
    """保存新抓取的记录"""
    with open(HISTORY_FILE, "a", encoding="utf-8") as f:
        f.write(f"{ip}:{port}\n")

# ======================
# 原有功能函数
# ======================

def get_headers():
    return {"User-Agent": random.choice(UA_LIST), "Referer": "https://fofa.info/"}

def get_fofa_ports(ip):
    sleep_time = random.uniform(8, 15)
    print(f" ⏳ FOFA 冷却 ({sleep_time:.1f}s)... ", end="", flush=True)
    time.sleep(sleep_time)
    try:
        query = base64.b64encode(ip.encode()).decode()
        search_url = f"https://fofa.info/result?qbase64={query}"
        res = requests.get(search_url, headers=get_headers(), timeout=15)
        html = res.text
        if "验证码" in html or "429" in html:
            print("❌ 触发防爬")
            return None
        all_found = set([int(p) for p in re.findall(rf'{ip}:(\d+)', html) + re.findall(r'port-item.*?(\d+)</a>', html, re.S)])
        final_ports = sorted([p for p in all_found if p not in {22, 23, 443, 80, 53, 3306, 3389}])
        print(f"✅ 发现: {final_ports}" if final_ports else "❓ 无特殊端口")
        return final_ports
    except Exception as e:
        print(f"❌ 异常: {e}")
        return []

def scan_ip_port(ip, port):
    url = f"https://iptv.cqshushu.com/?s={ip}:{port}&t=multicast&channels=1&download=m3u"
    try:
        time.sleep(random.uniform(2, 4))
        res = requests.get(url, headers=get_headers(), timeout=TIMEOUT)
        if res.status_code == 200 and "#EXTINF" in res.text:
            return res.text
    except:
        pass
    return None

def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    clean_history() # 运行前检查是否需要清理
    history_set, ip_counts = load_history()
    
    print(f"🚀 启动任务。已记录历史条目: {len(history_set)}")
    
    try:
        r = requests.get(HOME_URL, headers=get_headers(), timeout=TIMEOUT)
        all_ips = []
        for ip in re.findall(r"\b(?:\d{1,3}\.){3}\d{1,3}\b", r.text):
            if ip not in all_ips and not ip.startswith("127"):
                all_ips.append(ip)
        
        multicast_ips = all_ips[-MAX_IP_COUNT:] if len(all_ips) >= MAX_IP_COUNT else all_ips
    except Exception as e:
        print(f"❌ 首页访问失败: {e}")
        return

    fofa_blocked = False
    for idx, ip in enumerate(multicast_ips, 1):
        # 判断是否需要跳过整个 IP
        # 逻辑：如果该 IP 已经出现 2 次以上，则不跳过；否则如果该 IP 已存在则考虑跳过
        current_ip_count = ip_counts.get(ip, 0)
        
        print(f"\n[{idx}/{len(multicast_ips)}] 📡 探测: {ip} (历史出现次数: {current_ip_count})")
        
        test_ports = []
        if not fofa_blocked:
            f_ports = get_fofa_ports(ip)
            if f_ports is None:
                fofa_blocked = True
                test_ports = PRIMARY_MULTICAST_PORTS
            else:
                test_ports = f_ports + [p for p in PRIMARY_MULTICAST_PORTS if p not in f_ports]
        else:
            test_ports = PRIMARY_MULTICAST_PORTS

        found_success = False
        for port in test_ports:
            record = f"{ip}:{port}"
            
            # 过滤逻辑：
            # 1. 如果记录完全匹配且该 IP 出现次数不足 2 次，跳过
            if record in history_set and current_ip_count < 2:
                print(f" ⏩ 跳过已存在: {port}")
                continue

            print(f" ➜ 尝试端口 {port} ... ", end="", flush=True)
            content = scan_ip_port(ip, port)
            
            if content:
                filename = f"multicast_raw_{ip}_{port}.m3u"
                with open(os.path.join(OUTPUT_DIR, filename), "w", encoding="utf-8") as f:
                    f.write(content)
                save_history(ip, port) # 记录到文件
                print("✅ 成功并记录！")
                found_success = True
                break 
            else:
                print("✕")
        
        time.sleep(random.uniform(5, 10))

    print("\n任务完成！")

if __name__ == "__main__":
    main()
