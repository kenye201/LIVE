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
MAX_IP_COUNT = 6 # 适当增加扫描范围
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

def extract_provider_from_m3u(m3u_text):
    """从 M3U 的 group-title 中提取地区运营商"""
    try:
        # 正则匹配 group-title="上海市上海市组播 上海电信"
        match = re.search(r'group-title="([^"]+)"', m3u_text)
        if match:
            full_title = match.group(1)
            # 过滤掉“组播”、“上海市”等重复字样，只取空格后的核心内容
            # 或者直接取最后 4 个字（如：上海电信）
            parts = full_title.split()
            provider = parts[-1] if len(parts) > 1 else full_title
            return provider.replace("组播", "").strip()
    except:
        pass
    return "未知运营商"

def manage_history():
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)
    # 周一清理历史
    if datetime.now().weekday() == 0:
        if os.path.exists(HISTORY_FILE):
            os.remove(HISTORY_FILE)
    
    history_ips = set()
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            for line in f:
                ip_part = line.split(':')[0].strip()
                if ip_part: history_ips.add(ip_part)
    return history_ips

def save_history(ip, port):
    with open(HISTORY_FILE, "a", encoding="utf-8") as f:
        f.write(f"{ip}:{port}\n")

def get_headers():
    return {"User-Agent": random.choice(UA_LIST), "Referer": "https://fofa.info/"}

def get_fofa_ports(ip):
    time.sleep(random.uniform(3, 6))
    try:
        query = base64.b64encode(ip.encode()).decode()
        res = requests.get(f"https://fofa.info/result?qbase64={query}", headers=get_headers(), timeout=15)
        ports = set(re.findall(rf'{ip}:(\d+)', res.text))
        return sorted([int(p) for p in ports if int(p) > 100])
    except: return []

def scan_ip_port(ip, port):
    url = f"https://iptv.cqshushu.com/?s={ip}:{port}&t=multicast&channels=1&download=m3u"
    try:
        res = requests.get(url, headers=get_headers(), timeout=TIMEOUT)
        if res.status_code == 200 and "#EXTINF" in res.text:
            return res.text
    except: pass
    return None

def main():
    history_ips = manage_history()
    print(f"🚀 启动组播源提取任务...")
    
    try:
        r = requests.get(HOME_URL, headers=get_headers(), timeout=TIMEOUT)
        # 提取所有 IP
        all_found_ips = re.findall(r"\b(?:\d{1,3}\.){3}\d{1,3}\b", r.text)
        # 去重并过滤掉本地 IP
        ips = []
        for ip in all_found_ips:
            if not ip.startswith(("127.", "0.", "192.168.")) and ip not in ips:
                ips.append(ip)
        
        # 取最新的前 N 个
        target_ips = ips[:MAX_IP_COUNT]
        print(f"📍 首页获取到 {len(target_ips)} 个有效 IP 目标")
    except Exception as e:
        print(f"❌ 首页访问失败: {e}")
        return

    for idx, ip in enumerate(target_ips, 1):
        if ip in history_ips:
            print(f"[{idx}] 跳过已处理 IP: {ip}")
            continue

        print(f"\n[{idx}] 📡 正在探测: {ip}")
        f_ports = get_fofa_ports(ip)
        test_ports = f_ports + [p for p in PRIMARY_MULTICAST_PORTS if p not in f_ports]
        
        found_ok = False
        for port in test_ports:
            print(f"  ➜ 尝试 {port}...", end="", flush=True)
            content = scan_ip_port(ip, port)
            
            if content:
                # --- 核心改动：改命名规则 ---
                provider = extract_provider_from_m3u(content)
                safe_ip = ip.replace('.', '_')
                filename = f"{provider}-{safe_ip}.m3u"
                
                with open(os.path.join(OUTPUT_DIR, filename), "w", encoding="utf-8") as f:
                    f.write(content)
                save_history(ip, port)
                print(f" ✅ 成功! 命名为: {filename}")
                found_ok = True
                break
            else:
                print(" ✕", end="")
        
        if not found_ok:
            print(f"\n ⚠️ IP {ip} 遍历端口后未发现有效输出")
        
        time.sleep(random.uniform(2, 4))

if __name__ == "__main__":
    main()
