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
MAX_IP_COUNT = 6
TIMEOUT = 15 # 增加超时容忍度

# 你的常用端口字典
PRIMARY_PORTS = [
    6636, 16888, 5002, 3333, 8188, 8055, 8288, 8880, 5555, 55555, 58888, 7000, 7700, 6003, 9988, 9999, 8012, 10000, 8888, 4022, 8188, 8022, 7777, 5146, 5140, 4056, 12320, 
    10000, 8080, 8000, 9901, 8090, 8181, 1234, 4000, 4001, 5148, 12345, 8805, 8187, 9926, 8222, 8808, 8883, 8686, 8188, 4023, 8848, 6666, 
    9000, 9001, 888, 9003, 8082, 20443, 85, 8081, 8001, 8003, 6001, 8899
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
    url = f"https://iptv.cqshushu.com/index.php?s={ip}:{port}&t=multicast&channels=1&download=m3u"
    
    # 实时显示正在尝试的端口
    sys.stdout.write(f"  --> 尝试 [{port}] ... ")
    sys.stdout.flush()

    try:
        # 慢速探测：每个端口请求前强制随机停顿 1-2 秒
        time.sleep(random.uniform(1.2, 2.5))
        
        res = requests.get(url, headers=get_headers(), timeout=TIMEOUT)
        
        if res.status_code == 200 and "#EXTINF" in res.text:
            sys.stdout.write("【✅ 成功】\n")
            sys.stdout.flush()
            return res.text
        elif "请稍候" in res.text:
            sys.stdout.write("【⚠️ 遇盾】\n")
        else:
            sys.stdout.write(f"【❌ 无效 (Code:{res.status_code})】\n")
    except Exception as e:
        sys.stdout.write(f"【⏰ 超时/异常】\n")
    
    sys.stdout.flush()
    return None

def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    if not os.path.exists(LOCAL_SOURCE):
        log(f"❌ 找不到本地源码: {LOCAL_SOURCE}")
        return

    try:
        with open(LOCAL_SOURCE, "r", encoding="utf-8") as f:
            html = f.read()
        
        # --- 核心改进：同时提取 IP 和 对应的端口 ---
        # 匹配格式如：s=36.22.241.67:8188
        matches = re.findall(r's=((\d{1,3}\.){3}\d{1,3}):(\d+)', html)
        
        # 整理数据：{ IP: 原始端口 }
        found_data = {}
        for ip, _, port in matches:
            if not ip.startswith(("127.", "192.", "10.")):
                found_data[ip] = int(port)
        
        target_ips = list(found_data.keys())[-MAX_IP_COUNT:]
        log(f"📊 提取到 {len(target_ips)} 个目标 IP")

        for ip in target_ips:
            log(f"🌟 开始处理 IP: {ip}")
            
            # 构建测试字典：[原始端口] + [常用端口字典]
            original_port = found_data[ip]
            test_ports = [original_port] + [p for p in PRIMARY_PORTS if p != original_port]
            
            log(f"📋 优先测试原始端口 {original_port}，备选端口共 {len(test_ports)-1} 个")

            success = False
            for port in test_ports:
                content = scan_ip_port(ip, port)
                if content:
                    # 提取地区命名
                    match = re.search(r'group-title="([^"]+)"', content)
                    title = match.group(1).replace("组播", "").strip() if match else "未知"
                    provider = title.split()[-1] if " " in title else title
                    
                    filename = f"{provider}-{ip.replace('.', '_')}-{port}.m3u"
                    with open(os.path.join(OUTPUT_DIR, filename), "w", encoding="utf-8") as f:
                        f.write(content)
                    
                    log(f"🎉 任务完成: {filename}")
                    success = True
                    break # 该 IP 成功，跳过剩余端口
            
            if not success:
                log(f"❌ IP {ip} 所有端口均未响应。")
            
            # 每个 IP 处理完后大休整，保护 GitHub IP 不被封
            time.sleep(5)

    except Exception as e:
        log(f"❌ 程序崩溃: {e}")

if __name__ == "__main__":
    main()
