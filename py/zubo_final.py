import requests
import re
import os
import time
import base64
import random
import sys
from datetime import datetime

# ======================
# 配置区
# ======================
LOCAL_SOURCE = "data/shushu_home.html"
OUTPUT_DIR = "zubo"
HISTORY_FILE = os.path.join(OUTPUT_DIR, "history.txt")
TIMEOUT = 25

# 组播源常见高频端口
PRIMARY_PORTS = [6636, 16888, 5002, 3333, 8188, 8055, 8288, 8880, 5555, 55555, 58888, 7000, 7700, 6003, 9988, 9999, 8012, 10000, 8888, 4022, 8188, 8022, 7777, 5146, 5140, 4056, 12320, 
    10000, 8080, 8000, 9901, 8090, 8181, 1234, 4000, 4001, 5148, 12345, 8805, 8187, 9926, 8222, 8808, 8883, 8686, 8188, 4023, 8848, 6666, 
    9000, 9001, 888, 9003, 8082, 20443, 85, 8081, 8001, 8003, 6001, 8899
]


def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")
    sys.stdout.flush()

def scan_zubo(ip, port):
    url = f"https://iptv.cqshushu.com/index.php?s={ip}:{port}&t=multicast&channels=1&download=m3u"
    sys.stdout.write(f"  --> {port} ")
    sys.stdout.flush()
    try:
        time.sleep(random.uniform(3.0, 5.0))
        headers = {"User-Agent": "Mozilla/5.0", "Referer": "https://iptv.cqshushu.com/"}
        res = requests.get(url, headers=headers, timeout=TIMEOUT)
        
        # 深度校验：必须包含多于 5 个 rtp 链接才算真成功
        if res.status_code == 200 and "#EXTM3U" in res.text:
            rtp_count = res.text.count("rtp://")
            if rtp_count > 5:
                sys.stdout.write(f"【✅ 真成功: {rtp_count}条】\n")
                return res.text
            else:
                sys.stdout.write("【✕ 假文件/空壳】")
        else:
            sys.stdout.write("✕ ")
    except:
        sys.stdout.write("⏰ ")
    return None

def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    history_ips = set()
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            for line in f:
                if ":" in line: history_ips.add(line.split(':')[0].strip())

    with open(LOCAL_SOURCE, "r", encoding="utf-8") as f:
        content = f.read()

    # 精准提取后半段 multicast 的 IP
    b64_list = re.findall(r"gotoIP\('([^']+)',\s*'multicast'\)", content)
    all_ips = []
    for b in b64_list:
        try:
            decoded = base64.b64decode(b).decode('utf-8')
            if decoded not in all_ips: all_ips.append(decoded)
        except: continue

    # 取最后 8 个 IP（即网页最下方的最新组播源）
    target_ips = all_ips[-8:]
    log(f"🎯 识别到组播潜在目标 {len(target_ips)} 个")

    for idx, ip in enumerate(target_ips, 1):
        if ip in history_ips:
            log(f"📡 [{idx}/8] 跳过已验证 IP: {ip}"); continue
        
        log(f"📡 [{idx}/8] 正在测试组播 IP: {ip}")
        success = False
        for port in PRIMARY_PORTS:
            res_text = scan_zubo(ip, port)
            if res_text:
                m = re.search(r'group-title="([^"]+)"', res_text)
                tag = re.sub(r'[\\/:*?"<>|]', '', m.group(1).split()[-1] if m else "Zubo")
                fn = f"{tag}_{ip.replace('.', '_')}_{port}.m3u"
                with open(os.path.join(OUTPUT_DIR, fn), "w", encoding="utf-8") as f:
                    f.write(res_text)
                with open(HISTORY_FILE, "a", encoding="utf-8") as hf:
                    hf.write(f"{ip}:{port}\n")
                success = True
                break
        if not success: print(f"\n❌ {ip} 扫描完毕，无有效推流")
        time.sleep(3)

if __name__ == "__main__":
    main()
