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

# 组播高频端口
PRIMARY_PORTS = [6636, 16888, 5002, 3333, 8188, 8055, 8288, 8880, 5555, 55555, 58888, 7000, 7700, 6003, 9988, 9999, 8012, 10000, 8888, 4022, 8188, 8022, 7777, 5146, 5140, 4056, 12320, 
    10000, 8080, 8000, 9901, 8090, 8181, 1234, 4000, 4001, 5148, 12345, 8805, 8187, 9926, 8222, 8808, 8883, 8686, 8188, 4023, 8848, 6666, 
    9000, 9001, 888, 9003, 8082, 20443, 85, 8081, 8001, 8003, 6001, 8899
]


def log_process(msg, end='\n'):
    """实时刷新日志函数"""
    timestamp = datetime.now().strftime('%H:%M:%S')
    sys.stdout.write(f"[{timestamp}] {msg}{end}")
    sys.stdout.flush()

def scan_zubo(ip, port):
    url = f"https://iptv.cqshushu.com/index.php?s={ip}:{port}&t=multicast&channels=1&download=m3u"
    
    # 在同一行显示当前尝试的端口
    sys.stdout.write(f"    🔎 尝试端口 {port: <5} ... ")
    sys.stdout.flush()
    
    try:
        # 适度随机延迟，防止被反爬
        time.sleep(random.uniform(2, 4))
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Referer": "https://iptv.cqshushu.com/"
        }
        
        # 使用 stream=True 快速判断
        res = requests.get(url, headers=headers, timeout=TIMEOUT, stream=True)
        
        if res.status_code == 200:
            content = res.text
            # 严格指纹检测：必须有 EXTM3U 且包含真实的 rtp 链接
            if "#EXTM3U" in content and "rtp://" in content:
                count = content.count("rtp://")
                if count > 5:
                    sys.stdout.write(f"【✅ 成功: 抓获 {count} 条频道】\n")
                    sys.stdout.flush()
                    return content
                else:
                    sys.stdout.write("【✕ 假文件/空壳】\n")
            else:
                sys.stdout.write("【✕ 无效内容】\n")
        else:
            sys.stdout.write(f"【✕ 错误码: {res.status_code}】\n")
            
    except requests.exceptions.Timeout:
        sys.stdout.write("【⏰ 超时】\n")
    except Exception as e:
        sys.stdout.write(f"【⚠️ 异常: {str(e)[:20]}】\n")
    
    sys.stdout.flush()
    return None

def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    # 1. 打印初始化信息
    log_process("🚀 组播源采集任务启动")
    
    history_ips = set()
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            for line in f:
                if ":" in line:
                    history_ips.add(line.split(':')[0].strip())
    log_process(f"📜 载入历史记录: {len(history_ips)} 条")

    if not os.path.exists(LOCAL_SOURCE):
        log_process("❌ 致命错误: 找不到本地源码 data/shushu_home.html")
        return

    # 2. 提取 IP
    with open(LOCAL_SOURCE, "r", encoding="utf-8") as f:
        html = f.read()

    matches = re.findall(r"gotoIP\('([^']+)',\s*'multicast'\)", html)
    
    extracted_ips = []
    for b64_str in matches:
        try:
            b64_str += '=' * (-len(b64_str) % 4)
            ip = base64.b64decode(b64_str).decode('utf-8')
            if re.match(r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$", ip):
                if ip not in extracted_ips:
                    extracted_ips.append(ip)
        except: continue

    # 组播源通常网页最后的比较新，我们倒序取 10 个
    target_ips = extracted_ips[::-1][:10]
    log_process(f"📊 源码解析完成: 发现 {len(extracted_ips)} 个 IP，准备探测其中 {len(target_ips)} 个新目标")

    # 3. 遍历探测
    for idx, ip in enumerate(target_ips, 1):
        if ip in history_ips:
            log_process(f"⏭️  [{idx}/{len(target_ips)}] 跳过已采集 IP: {ip}")
            continue
        
        log_process(f"📡 [{idx}/{len(target_ips)}] 正在扫描目标: {ip}")
        found_valid = False
        
        for port in PRIMARY_PORTS:
            content = scan_zubo(ip, port)
            if content:
                # 提取提供商标签命名
                m = re.search(r'group-title="([^"]+)"', content)
                tag = re.sub(r'[\\/:*?"<>|]', '', m.group(1).split()[-1] if m else "Zubo")
                
                filename = f"{tag}_{ip.replace('.', '_')}_{port}.m3u"
                with open(os.path.join(OUTPUT_DIR, filename), "w", encoding="utf-8") as f:
                    f.write(content)
                
                # 记录成功历史
                with open(HISTORY_FILE, "a", encoding="utf-8") as hf:
                    hf.write(f"{ip}:{port}\n")
                
                found_valid = True
                break # 该 IP 探测成功，跳出端口循环
        
        if not found_valid:
            log_process(f"❌ 目标 {ip} 所有常用端口探测均未发现有效推流")
        
        # IP 间隔，防止被封
        time.sleep(2)

    log_process("✨ 任务全部完成")

if __name__ == "__main__":
    main()
