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
TIMEOUT = 20

# 组播源核心端口
PRIMARY_PORTS = [6636, 16888, 5002, 3333, 8188, 8055, 8288, 8880, 5555, 55555, 58888, 7000, 7700, 6003, 9988, 9999, 8012, 10000, 8888, 4022, 8188, 8022, 7777, 5146, 5140, 4056, 12320, 
    10000, 8080, 8000, 9901, 8090, 8181, 1234, 4000, 4001, 5148, 12345, 8805, 8187, 9926, 8222, 8808, 8883, 8686, 8188, 4023, 8848, 6666, 
    9000, 9001, 888, 9003, 8082, 20443, 85, 8081, 8001, 8003, 6001, 8899
]


def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")
    sys.stdout.flush()

def scan_zubo(ip, port):
    # 强制使用 https 提高成功率
    url = f"https://iptv.cqshushu.com/index.php?s={ip}:{port}&t=multicast&channels=1&download=m3u"
    sys.stdout.write(f"  --> {port} ")
    sys.stdout.flush()
    try:
        # 模拟真实浏览器延迟
        time.sleep(random.uniform(3, 5))
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Referer": "https://iptv.cqshushu.com/"
        }
        res = requests.get(url, headers=headers, timeout=TIMEOUT)
        
        # 深度指纹校验：必须是 M3U 格式且包含 RTP 频道链接
        content = res.text
        if res.status_code == 200 and "#EXTM3U" in content and "rtp://" in content:
            # 统计频道数，太少（比如 < 5）通常是垃圾信息
            count = content.count("rtp://")
            if count > 5:
                sys.stdout.write(f"【✅ 抓取成功: {count}个频道】\n")
                return content
            else:
                sys.stdout.write("【✕ 频道太少/假文件】")
        else:
            sys.stdout.write("✕ ")
    except Exception as e:
        sys.stdout.write("⏰ ")
    return None

def main():
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)
    
    # 1. 加载黑名单 (精准匹配 IP)
    history_ips = set()
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            for line in f:
                if ":" in line:
                    history_ips.add(line.split(':')[0].strip())
    
    if not os.path.exists(LOCAL_SOURCE):
        log("❌ 找不到源码"); return

    with open(LOCAL_SOURCE, "r", encoding="utf-8") as f:
        html_content = f.read()

    # 2. 精准提取：只看 gotoIP 中的 multicast 记录
    # 提取格式: gotoIP('Base64字符串', 'multicast')
    matches = re.findall(r"gotoIP\('([^']+)',\s*'multicast'\)", html_content)
    
    all_ips = []
    for b64_str in matches:
        try:
            # 补齐 Base64 填充位
            missing_padding = len(b64_str) % 4
            if missing_padding:
                b64_str += '=' * (4 - missing_padding)
            
            decoded_ip = base64.b64decode(b64_str).decode('utf-8')
            # 严格正则校验 IP 格式
            if re.match(r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$", decoded_ip):
                if decoded_ip not in all_ips:
                    all_ips.append(decoded_ip)
        except:
            continue

    # 取最后（最新）出的 10 个 IP
    target_ips = all_ips[-10:]
    log(f"📊 源码共含 {len(all_ips)} 个组播 IP，取最新 {len(target_ips)} 个进入测试")

    for idx, ip in enumerate(target_ips, 1):
        # 检查是否真的在黑名单里
        if ip in history_ips:
            log(f"⏭️  [{idx}/{len(target_ips)}] {ip} 已在历史成功记录中，跳过"); continue
        
        log(f"📡 [{idx}/{len(target_ips)}] 正在扫描新 IP: {ip}")
        ip_success = False
        
        for port in PRIMARY_PORTS:
            m3u_content = scan_zubo(ip, port)
            if m3u_content:
                # 提取提供商标签
                tag_match = re.search(r'group-title="([^"]+)"', m3u_content)
                tag = tag_match.group(1).split()[-1] if tag_match else "Zubo"
                tag = re.sub(r'[\\/:*?"<>|]', '', tag)
                
                # 保存文件
                filename = f"{tag}_{ip.replace('.', '_')}_{port}.m3u"
                with open(os.path.join(OUTPUT_DIR, filename), "w", encoding="utf-8") as f:
                    f.write(m3u_content)
                
                # 【关键】只有此时才写入黑名单
                with open(HISTORY_FILE, "a", encoding="utf-8") as hf:
                    hf.write(f"{ip}:{port}\n")
                
                ip_success = True
                break # 该 IP 已成功，停止测试其他端口
        
        if not ip_success:
            print(f"\n❌ IP {ip} 这一轮没抓到任何有效频道列表。")
        
        time.sleep(2) # IP 间停顿

if __name__ == "__main__":
    main()
