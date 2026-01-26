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
LOCAL_SOURCE = "data/shushu_home.html"  # 月球宿主上传到仓库的文件路径
OUTPUT_DIR = "zubo"
HISTORY_FILE = os.path.join(OUTPUT_DIR, "history.txt")
MAX_IP_COUNT = 6  # 提取后 6 个 IP
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
    if datetime.now().weekday() == 0: # 周一清空历史
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
    time.sleep(random.uniform(5, 10))
    try:
        query = base64.b64encode(ip.encode()).decode()
        res = requests.get(f"https://fofa.info/result?qbase64={query}", headers=get_headers(), timeout=15)
        ports = set(re.findall(rf'{ip}:(\d+)', res.text) + re.findall(r'port-item.*?(\d+)</a>', res.text, re.S))
        return sorted([int(p) for p in ports if int(p) not in {22, 23, 443, 80, 53, 3306, 3389}])
    except: return []

def scan_ip_port(ip, port):
    # 使用你测试成功的 index.php 接口
    url = f"https://iptv.cqshushu.com/index.php?s={ip}:{port}&t=multicast&channels=1&download=m3u"
    try:
        # GitHub Actions 访问这个链接如果成功，就不需要像首页那样过验证
        res = requests.get(url, headers=get_headers(), timeout=TIMEOUT)
        if res.status_code == 200 and "#EXTINF" in res.text:
            return res.text
    except: pass
    return None

def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    history_ips = manage_history()
    
    if not os.path.exists(LOCAL_SOURCE):
        print(f"❌ 找不到本地文件: {LOCAL_SOURCE}, 请确认月球宿主是否已成功推送。")
        return

    try:
        with open(LOCAL_SOURCE, "r", encoding="utf-8") as f:
            content = f.read()
        
        # 匹配页面中的所有 IP
        all_ips = list(dict.fromkeys(re.findall(r"\b(?:\d{1,3}\.){3}\d{1,3}\b", content)))
        # 过滤掉非公网 IP
        public_ips = [ip for ip in all_ips if not ip.startswith(("127.", "192.", "10.", "172."))]
        
        # 按照你的需求：一共12个，取后面6个
        target_ips = public_ips[-MAX_IP_COUNT:]
        print(f"📊 页面共发现 {len(public_ips)} 个 IP，准备扫描最后的 {len(target_ips)} 个。")
        
    except Exception as e:
        print(f"❌ 解析本地文件失败: {e}")
        return

    for ip in target_ips:
        if ip in history_ips:
            print(f"⏭️ IP {ip} 已在历史记录中，跳过。")
            continue
        
        print(f"🔍 正在处理: {ip}")
        f_ports = get_fofa_ports(ip)
        test_ports = f_ports + [p for p in PRIMARY_MULTICAST_PORTS if p not in f_ports]
        
        for port in test_ports:
            m3u_content = scan_ip_port(ip, port)
            if m3u_content:
                provider = "未知"
                match = re.search(r'group-title="([^"]+)"', m3u_content)
                if match:
                    title = match.group(1).replace("组播", "").strip()
                    provider = title.split()[-1] if " " in title else title
                
                filename = f"{provider}-{ip.replace('.', '_')}-{port}.m3u"
                with open(os.path.join(OUTPUT_DIR, filename), "w", encoding="utf-8") as f:
                    f.write(m3u_content)
                
                save_history(ip, port)
                print(f"✅ 成功! 保存为: {filename}")
                break # 该 IP 扫描成功，换下一个
            
        time.sleep(random.uniform(3, 7))

if __name__ == "__main__":
    main()
