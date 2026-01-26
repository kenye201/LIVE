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
LOCAL_SOURCE = "data/shushu_home.html"
OUTPUT_DIR = "hotel"
HISTORY_FILE = os.path.join(OUTPUT_DIR, "hotel_history.txt")
MAX_IP_COUNT = 6
TIMEOUT = 15

# 酒店源常用端口
PRIMARY_PORTS = [8000, 8080, 9901, 8082, 8888, 9001, 8001, 8090, 9999, 888, 9003, 8081, 50001]

def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")
    sys.stdout.flush()

def scan_ip_port(ip, port):
    url = f"https://iptv.cqshushu.com/index.php?s={ip}:{port}&t=hotel&channels=1&download=m3u"
    sys.stdout.write(f"  --> 尝试 [{port}] ... ")
    sys.stdout.flush()
    try:
        time.sleep(random.uniform(1.0, 1.5))
        res = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=TIMEOUT)
        if res.status_code == 200 and "#EXTINF" in res.text:
            sys.stdout.write("【✅ 成功】\n")
            return res.text
    except:
        pass
    sys.stdout.write("✕ ")
    return None

def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    # 1. 加载历史记录
    history_ips = set()
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            for line in f:
                if ":" in line: history_ips.add(line.split(':')[0].strip())

    if not os.path.exists(LOCAL_SOURCE):
        log("❌ 找不到源码"); return

    try:
        with open(LOCAL_SOURCE, "r", encoding="utf-8") as f:
            content = f.read()
        
        # 2. 【粉碎提取】思路：
        # 第一步：只保留 Hotel IPTV 之后的内容
        if "Hotel IPTV" in content:
            content = content.split("Hotel IPTV")[1]

        # 第二步：暴力匹配所有看起来像 IP 的字符串
        # 无论它是在 onclick 里、td 里、还是躲在空格里
        raw_ips = re.findall(r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}", content)
        
        # 第三步：去重并过滤掉局域网 IP
        public_ips = []
        seen = set()
        for ip in raw_ips:
            if ip not in seen and not ip.startswith(("127.", "192.", "10.", "172.")):
                public_ips.append(ip)
                seen.add(ip)

        if not public_ips:
            log("❌ 依然没有抓到 IP，请检查本地文件内容。")
            return

        # 3. 选取前 6 个
        target_ips = [ip for ip in public_ips if ip not in history_ips][:MAX_IP_COUNT]
        log(f"📊 粉碎提取完成，发现 {len(public_ips)} 个 IP，准备探测前 {len(target_ips)} 个新目标")

        for ip in target_ips:
            log(f"🌟 探测 IP: {ip}")
            success = False
            for port in PRIMARY_PORTS:
                content_m3u = scan_ip_port(ip, port)
                if content_m3u:
                    # 命名
                    m = re.search(r'group-title="([^"]+)"', content_m3u)
                    provider = m.group(1).split()[-1] if m else "酒店源"
                    provider = re.sub(r'[\\/:*?"<>|]', '', provider)
                    
                    filename = f"{provider}-{ip.replace('.', '_')}-{port}.m3u"
                    with open(os.path.join(OUTPUT_DIR, filename), "w", encoding="utf-8") as f:
                        f.write(content_m3u)
                    
                    with open(HISTORY_FILE, "a", encoding="utf-8") as hf:
                        hf.write(f"{ip}:{port}\n")
                    
                    log(f"🎉 成功保存: {filename}")
                    success = True
                    break
            
            if not success:
                print("\n")
                log(f"❌ IP {ip} 失败")
            time.sleep(2)

    except Exception as e:
        log(f"❌ 运行崩溃: {e}")

if __name__ == "__main__":
    main()
