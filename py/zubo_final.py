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
HISTORY_FILE = os.path.join(OUTPUT_DIR, "history.txt") # 记录【真正成功】的记录
MAX_IP_COUNT = 10   # 组播源变动快，建议增加扫描数量
TIMEOUT = 20        # 组播源握手慢，增加超时时间

# 常用端口字典：优先放高频端口
PRIMARY_PORTS = [    6636, 16888, 5002, 3333, 8188, 8055, 8288, 8880, 5555, 55555, 58888, 7000, 7700, 6003, 9988, 9999, 8012, 10000, 8888, 4022, 8188, 8022, 7777, 5146, 5140, 4056, 12320, 
    10000, 8080, 8000, 9901, 8090, 8181, 1234, 4000, 4001, 5148, 12345, 8805, 8187, 9926, 8222, 8808, 8883, 8686, 8188, 4023, 8848, 6666, 
    9000, 9001, 888, 9003, 8082, 20443, 85, 8081, 8001, 8003, 6001, 8899
]

def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")
    sys.stdout.flush()

def get_headers():
    return {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Referer": "https://iptv.cqshushu.com/",
        "Accept": "*/*"
    }

def scan_ip_port(ip, port):
    # 构造请求 URL (t=multicast)
    url = f"https://iptv.cqshushu.com/index.php?s={ip}:{port}&t=multicast&channels=1&download=m3u"
    
    sys.stdout.write(f"  --> {port} ")
    sys.stdout.flush()

    try:
        # 组播探测需要更慢的频率，防止被封
        time.sleep(random.uniform(2.5, 4.5))
        
        res = requests.get(url, headers=get_headers(), timeout=TIMEOUT)
        
        # 关键判断：必须包含 #EXTM3U 且 code 为 200
        if res.status_code == 200 and "#EXTM3U" in res.text:
            # 进一步检查是否有有效频道链接 (rtp://)
            if "rtp://" in res.text or "http" in res.text:
                sys.stdout.write("【✅ 成功】\n")
                return res.text
            else:
                sys.stdout.write("【Empty】") # 拿到文件但里面没频道
        elif "请稍候" in res.text:
            sys.stdout.write("【🛡️ 遇盾】")
        else:
            sys.stdout.write("✕ ")
    except:
        sys.stdout.write("⏰ ")
    
    sys.stdout.flush()
    return None

def main():
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)
    
    # 1. 加载黑名单 (只有以前成功抓到文件的 IP 才在里面)
    history_ips = set()
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            for line in f:
                if ":" in line:
                    history_ips.add(line.split(':')[0].strip())
    log(f"📜 已加载历史记录，跳过 {len(history_ips)} 个已采集 IP")

    if not os.path.exists(LOCAL_SOURCE):
        log("❌ 找不到源码文件"); return

    try:
        with open(LOCAL_SOURCE, "r", encoding="utf-8") as f:
            content = f.read()

        # 2. 提取跳转 IP (对应 gotoIP 逻辑)
        # 组播源在 HTML 中通常也是 base64 或直接显示的 IP
        b64_matches = re.findall(r"gotoIP\('([^']+)',\s*'multicast'\)", content)
        
        extracted_ips = []
        for b in b64_matches:
            try:
                ip = base64.b64decode(b).decode('utf-8')
                if re.match(r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$", ip):
                    if ip not in extracted_ips:
                        extracted_ips.append(ip)
            except: continue

        # 如果 gotoIP 没抓到，尝试正则抓取正文中的 IP
        if not extracted_ips:
            extracted_ips = list(dict.fromkeys(re.findall(r"(?:\d{1,3}\.){3}\d{1,3}", content)))
            # 过滤内网 IP
            extracted_ips = [ip for ip in extracted_ips if not ip.startswith(("127.", "192.", "10.", "172."))]

        # 取最新的几个 IP 进行探测
        target_ips = [ip for ip in extracted_ips if ip not in history_ips][:MAX_IP_COUNT]
        
        if not target_ips:
            log("🔎 没有发现新的待测 IP"); return

        log(f"🎯 准备探测 {len(target_ips)} 个新目标")

        # 3. 开始扫描
        for idx, ip in enumerate(target_ips, 1):
            log(f"📡 [{idx}/{len(target_ips)}] 目标: {ip}")
            
            success_this_ip = False
            # 端口策略：4022, 8888 永远是组播的首选
            test_ports = PRIMARY_PORTS
            
            for port in test_ports:
                file_content = scan_ip_port(ip, port)
                
                if file_content:
                    # 命名逻辑
                    m = re.search(r'group-title="([^"]+)"', file_content)
                    tag = m.group(1).split()[-1] if m else "组播源"
                    tag = re.sub(r'[\\/:*?"<>|]', '', tag)
                    
                    fn = f"{tag}_{ip.replace('.', '_')}_{port}.m3u"
                    with open(os.path.join(OUTPUT_DIR, fn), "w", encoding="utf-8") as f:
                        f.write(file_content)
                    
                    # 【重要】只有真正抓到文件了，才记入 history.txt
                    with open(HISTORY_FILE, "a", encoding="utf-8") as hf:
                        hf.write(f"{ip}:{port}\n")
                    
                    success_this_ip = True
                    break # 这个 IP 成功了，跳到下一个 IP
            
            if not success_this_ip:
                print(f"\n❌ IP {ip} 所有端口探测失败，不计入黑名单，下次继续尝试。")
            
            time.sleep(5) # IP 间休息

    except Exception as e:
        log(f"❌ 运行崩溃: {e}")

if __name__ == "__main__":
    main()
