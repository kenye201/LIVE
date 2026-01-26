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
MAX_IP_COUNT = 8  # 增加扫描深度
TIMEOUT = 20

# 组播源核心端口字典 (按成功率排序)
PRIMARY_PORTS = [4022, 8888, 8188, 9901, 8000, 8080, 85, 9999, 6636, 16888, 8090, 8012]

def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")
    sys.stdout.flush()

def scan_ip_port(ip, port):
    url = f"https://iptv.cqshushu.com/index.php?s={ip}:{port}&t=multicast&channels=1&download=m3u"
    
    sys.stdout.write(f"  --> {port} ")
    sys.stdout.flush()

    try:
        # 组播探测需要慢，太快必被封
        time.sleep(random.uniform(2.5, 5.0))
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Referer": "https://iptv.cqshushu.com/"
        }
        res = requests.get(url, headers=headers, timeout=TIMEOUT)
        
        # 核心判断：必须包含直播源特征码
        if res.status_code == 200 and "#EXTM3U" in res.text and ("rtp://" in res.text or "http" in res.text):
            sys.stdout.write("【✅ 成功】\n")
            return res.text
        elif "请稍候" in res.text:
            sys.stdout.write("【🛡️ 盾】")
        else:
            sys.stdout.write("✕ ")
    except:
        sys.stdout.write("⏰ ")
    
    sys.stdout.flush()
    return None

def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    # 1. 重新加载黑名单 IP
    history_ips = set()
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            for line in f:
                if ":" in line:
                    # 只提取冒号前的 IP 部分
                    history_ips.add(line.split(':')[0].strip())
    log(f"📜 已加载黑名单，包含 {len(history_ips)} 个已验证 IP")

    if not os.path.exists(LOCAL_SOURCE):
        log("❌ 找不到源码文件"); return

    try:
        with open(LOCAL_SOURCE, "r", encoding="utf-8") as f:
            content = f.read()

        # 2. 【精准提取】只找网页逻辑里的组播 IP
        # 匹配 gotoIP('Base64字符', 'multicast')
        b64_matches = re.findall(r"gotoIP\('([^']+)',\s*'multicast'\)", content)
        
        extracted_ips = []
        for b in b64_matches:
            try:
                # 处理 Base64 填充
                missing_padding = len(b) % 4
                if missing_padding:
                    b += '=' * (4 - missing_padding)
                
                decoded_ip = base64.b64decode(b).decode('utf-8')
                # 验证是否是合法 IP 格式
                if re.match(r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$", decoded_ip):
                    if decoded_ip not in extracted_ips:
                        extracted_ips.append(decoded_ip)
            except: continue

        # 3. 过滤掉黑名单，取最新的 8 个
        target_ips = [ip for ip in extracted_ips if ip not in history_ips][:MAX_IP_COUNT]
        
        if not target_ips:
            log("🔎 网页上这几个 IP 都在黑名单里了，没有新目标。")
            return

        log(f"🎯 准备探测 {len(target_ips)} 个真正的新组播目标...")

        # 4. 探测循环
        for idx, ip in enumerate(target_ips, 1):
            log(f"📡 [{idx}/{len(target_ips)}] 目标: {ip}")
            
            success_this_ip = False
            for port in PRIMARY_PORTS:
                file_content = scan_ip_port(ip, port)
                
                if file_content:
                    # 命名
                    m = re.search(r'group-title="([^"]+)"', file_content)
                    tag = m.group(1).split()[-1] if m else "组播源"
                    tag = re.sub(r'[\\/:*?"<>|]', '', tag)
                    
                    fn = f"{tag}_{ip.replace('.', '_')}_{port}.m3u"
                    with open(os.path.join(OUTPUT_DIR, fn), "w", encoding="utf-8") as f:
                        f.write(file_content)
                    
                    # 【核心修正】只有此时才写入 history.txt
                    with open(HISTORY_FILE, "a", encoding="utf-8") as hf:
                        hf.write(f"{ip}:{port}\n")
                    
                    success_this_ip = True
                    break 
            
            if not success_this_ip:
                print(f"\n❌ {ip} 这一轮没扫出开放端口，不进黑名单，下次刷新再试。")
            
            time.sleep(5)

    except Exception as e:
        log(f"❌ 运行崩溃: {e}")

if __name__ == "__main__":
    main()
