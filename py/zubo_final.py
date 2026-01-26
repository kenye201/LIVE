import requests
import re
import os
import time
import random
import sys
from datetime import datetime

# ======================
# 配置区
# ======================
LOCAL_SOURCE = "data/shushu_home.html"  # 源码位置
OUTPUT_DIR = "hotel"
HISTORY_FILE = os.path.join(OUTPUT_DIR, "hotel_history.txt")
MAX_IP_COUNT = 6  # 酒店源我们要前 6 个（最新的）
TIMEOUT = 15      # 超时时间

# 酒店源常用端口字典（优先排在前面）
PRIMARY_PORTS = [
    8000, 8080, 9901, 8082, 8888, 9001, 8001, 8090, 9999, 888, 9003, 
    8081, 8181, 8899, 85, 808, 50001, 20443, 4022, 5002, 1234
]

UA_LIST = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1"
]

def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")
    sys.stdout.flush()

def get_headers():
    return {
        "User-Agent": random.choice(UA_LIST),
        "Referer": "https://iptv.cqshushu.com/index.php",
        "Accept": "*/*"
    }

def scan_ip_port(ip, port):
    # 注意这里 t=hotel
    url = f"https://iptv.cqshushu.com/index.php?s={ip}:{port}&t=hotel&channels=1&download=m3u"
    
    sys.stdout.write(f"  --> 尝试 [{port}] ... ")
    sys.stdout.flush()

    try:
        time.sleep(random.uniform(1.2, 2.5))
        res = requests.get(url, headers=get_headers(), timeout=TIMEOUT)
        
        if res.status_code == 200 and "#EXTINF" in res.text:
            sys.stdout.write("【✅ 成功】\n")
            return res.text
        else:
            sys.stdout.write(f"【❌ 无效】 ") # 简化输出
    except:
        sys.stdout.write(f"【⏰ 超时】 ")
    
    sys.stdout.flush()
    return None

def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    # 1. 加载黑名单
    history_ips = set()
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            for line in f:
                if ":" in line:
                    history_ips.add(line.split(':')[0].strip())
    log(f"📜 已加载黑名单，包含 {len(history_ips)} 个 IP")

    if not os.path.exists(LOCAL_SOURCE):
        log(f"❌ 找不到源码: {LOCAL_SOURCE}")
        return

    try:
        with open(LOCAL_SOURCE, "r", encoding="utf-8") as f:
            html = f.read()
        
        # 2. 提取所有公网 IP (套用组播脚本逻辑)
        # 先找到 "Hotel IPTV" 字样，只取它后面的内容以防抓到前面的组播 IP
        if "Hotel IPTV" in html:
            html = html.split("Hotel IPTV")[1]

        all_ips = list(dict.fromkeys(re.findall(r"(?:\d{1,3}\.){3}\d{1,3}", html)))
        public_ips = [ip for ip in all_ips if not ip.startswith(("127.", "192.", "10.", "172."))]
        
        if not public_ips:
            log("⚠️ 源码中未发现任何公网 IP。")
            return

        # 3. 选取前 MAX_IP_COUNT 个目标 (酒店源通常越靠前越新)
        target_ips = public_ips[:MAX_IP_COUNT]
        log(f"📊 提取到 {len(target_ips)} 个潜在目标: {target_ips}")

        for ip in target_ips:
            if ip in history_ips:
                log(f"⏭️ 跳过已存在的 IP: {ip}")
                continue

            log(f"🌟 开始探测酒店 IP: {ip}")
            
            success = False
            for port in PRIMARY_PORTS:
                content = scan_ip_port(ip, port)
                if content:
                    # 提取提供商/地区命名
                    match = re.search(r'group-title="([^"]+)"', content)
                    title = match.group(1).strip() if match else "酒店源"
                    # 提取最后一段，如 "湖北电信"
                    provider = title.split()[-1] if " " in title else title
                    provider = re.sub(r'[\\/:*?"<>|]', '', provider)
                    
                    filename = f"{provider}-{ip.replace('.', '_')}-{port}.m3u"
                    with open(os.path.join(OUTPUT_DIR, filename), "w", encoding="utf-8") as f:
                        f.write(content)
                    
                    # 写入黑名单记录
                    with open(HISTORY_FILE, "a", encoding="utf-8") as hf:
                        hf.write(f"{ip}:{port}\n")
                    
                    log(f"🎉 成功保存: {filename}")
                    success = True
                    break 
            
            if not success:
                log(f"❌ IP {ip} 所有字典端口均失败。")
            
            time.sleep(3)

    except Exception as e:
        log(f"❌ 运行崩溃: {e}")

if __name__ == "__main__":
    main()
