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
TIMEOUT = 15 

# 你的常用端口字典
PRIMARY_PORTS = [
    4022, 8188, 6636, 16888, 5002, 3333, 8055, 8288, 8880, 5555, 7000, 8012, 10000, 
    8888, 8022, 7777, 9000, 8080, 8000, 1234, 4000, 4001, 8899
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
        # 慢速探测：每个端口请求前强制随机停顿 1.2-2.5 秒
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
        
        # 1. 宽松匹配：先抓出所有 IP
        all_ips = list(dict.fromkeys(re.findall(r"(?:\d{1,3}\.){3}\d{1,3}", html)))
        # 过滤掉内网 IP
        public_ips = [ip for ip in all_ips if not ip.startswith(("127.", "192.", "10.", "172."))]
        
        if not public_ips:
            log("⚠️ 源码中未发现任何公网 IP。")
            return

        # 2. 尝试寻找 IP 紧跟着的端口
        found_data = {}
        for ip in public_ips:
            # 搜索 IP 后面跟着的端口 (兼容 :4022 或 s=IP:PORT 等各种格式)
            port_match = re.search(rf"{re.escape(ip)}[:&s=]*(\d+)", html)
            if port_match:
                found_data[ip] = int(port_match.group(1))
            else:
                found_data[ip] = 4022 # 默认保底

        target_ips = list(found_data.keys())[-MAX_IP_COUNT:]
        log(f"📊 提取到 {len(target_ips)} 个目标 IP")

        for ip in target_ips:
            log(f"🌟 开始处理 IP: {ip}")
            
            # 构建测试字典：[网页原始端口] + [常用端口字典]
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
                    break 
            
            if not success:
                log(f"❌ IP {ip} 所有端口均未响应。")
            
            # 每个 IP 处理完后休息
            time.sleep(5)

    except Exception as e:
        log(f"❌ 程序崩溃: {e}")

if __name__ == "__main__":
    main()
