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
OUTPUT_DIR = "hotel"
HISTORY_FILE = os.path.join(OUTPUT_DIR, "hotel_history.txt")
MAX_IP_COUNT = 5    # 提取 IP 成功了，我们可以稍微多看几个
TIMEOUT = 15        # 增加超时等待

# 酒店高频端口字典
PRIMARY_PORTS = [8082, 9901, 888, 9001, 9003, 9888, 8080, 8000, 9999, 8888, 8090, 8081, 8181, 8899, 8001, 85, 808, 50001, 20443]

def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")
    sys.stdout.flush()

def scan_ip_port(ip, port):
    """单次端口扫描"""
    url = f"https://iptv.cqshushu.com/index.php?s={ip}:{port}&t=hotel&channels=1&download=m3u"
    
    # 显示当前正在尝试的端口
    sys.stdout.write(f"  --> 测试端口 [{port}] ... ")
    sys.stdout.flush()

    try:
        # 加长随机等待，让对方服务器喘口气 (1.5s - 3.5s)
        time.sleep(random.uniform(1.5, 3.5))
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Referer": "https://iptv.cqshushu.com/"
        }
        
        res = requests.get(url, headers=headers, timeout=TIMEOUT)
        
        if res.status_code == 200 and "#EXTINF" in res.text:
            sys.stdout.write("【✅ 发现数据！】\n")
            return res.text
        else:
            sys.stdout.write("✕\n")
    except Exception:
        sys.stdout.write("⏰ 超时\n")
    
    sys.stdout.flush()
    return None

def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    if not os.path.exists(LOCAL_SOURCE):
        log("❌ 找不到源码文件"); return

    try:
        with open(LOCAL_SOURCE, "r", encoding="utf-8") as f:
            content = f.read()

        # 1. 提取加密 IP
        b64_list = re.findall(r"gotoIP\('([^']+)',\s*'hotel'\)", content)
        found_ips = []
        for b in b64_list:
            try:
                decoded = base64.b64decode(b).decode('utf-8')
                if re.match(r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$", decoded):
                    if decoded not in found_ips:
                        found_ips.append(decoded)
            except: continue

        if not found_ips:
            log("❌ 未在页面发现有效 IP 串"); return

        log(f"✅ 成功提取 {len(found_ips)} 个 IP，准备开始探测...")

        # 2. 顺序探测
        target_ips = found_ips[:MAX_IP_COUNT]
        for idx, ip in enumerate(target_ips, 1):
            log(f"📡 [{idx}/{len(target_ips)}] 正在深度扫描 IP: {ip}")
            success = False
            
            # 尝试每一个端口
            for port in PRIMARY_PORTS:
                m3u_content = scan_ip_port(ip, port)
                
                if m3u_content:
                    # 提取省份/运营商信息作为文件名
                    m = re.search(r'group-title="([^"]+)"', m3u_content)
                    title = m.group(1).split()[-1] if m else "Hotel"
                    title = re.sub(r'[\\/:*?"<>|]', '', title) # 清洗文件名
                    
                    filename = f"{title}_{ip.replace('.', '_')}_{port}.m3u"
                    with open(os.path.join(OUTPUT_DIR, filename), "w", encoding="utf-8") as f:
                        f.write(m3u_content)
                    
                    log(f"🎉 抓取成功，已保存至: {filename}")
                    success = True
                    break # 找到一个有效端口就跳到下一个 IP
            
            if not success:
                log(f"⚠️ IP {ip} 尝试了所有常用端口，均未响应。")
            
            # IP 之间的大冷却，防止被封 IP
            time.sleep(5)

    except Exception as e:
        log(f"❌ 程序发生崩溃: {e}")

if __name__ == "__main__":
    main()
