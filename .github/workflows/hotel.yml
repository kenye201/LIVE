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
DEBUG_OUTPUT = "data/extracted_hotel_ips.txt"  # 强制生成的结果预览文件
OUTPUT_DIR = "hotel"
HISTORY_FILE = os.path.join(OUTPUT_DIR, "hotel_history.txt")
MAX_IP_COUNT = 6
TIMEOUT = 15

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
    except: pass
    sys.stdout.write("✕ ")
    return None

def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    os.makedirs(os.path.dirname(DEBUG_OUTPUT), exist_ok=True)
    
    history_ips = set()
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            for line in f:
                if ":" in line: history_ips.add(line.split(':')[0].strip())

    if not os.path.exists(LOCAL_SOURCE):
        log(f"❌ 找不到源码: {LOCAL_SOURCE}")
        return

    try:
        with open(LOCAL_SOURCE, "r", encoding="utf-8") as f:
            content = f.read()
        
        # 1. 强制切分区域
        hotel_content = content
        if "Hotel IPTV" in content:
            hotel_content = content.split("Hotel IPTV")[1]
            log("🎯 已定位到酒店源区域")
        else:
            log("⚠️ 未定位到 Hotel IPTV 关键词，将扫描全文")

        # 2. 暴力提取所有符合 IP 格式的字符串
        # 无论它是在 HTML 标签里、JS 函数里、还是带空格的文本里
        raw_ips = re.findall(r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}", hotel_content)
        
        # 去重并过滤局域网
        public_ips = []
        seen = set()
        for ip in raw_ips:
            if ip not in seen and not ip.startswith(("127.", "192.", "10.", "172.")):
                public_ips.append(ip)
                seen.add(ip)

        # 3. 【新功能】无论结果如何，强制生成一个预览文件供你检查
        with open(DEBUG_OUTPUT, "w", encoding="utf-8") as df:
            if public_ips:
                df.write("\n".join(public_ips))
                log(f"📝 已将提取到的 {len(public_ips)} 个 IP 写入 {DEBUG_OUTPUT}")
            else:
                df.write("FAILED: No IP strings found in the targeted section.")
                log(f"📝 未找到 IP，已在 {DEBUG_OUTPUT} 中记录失败状态")

        if not public_ips:
            return

        # 4. 提取前 6 个新 IP 进行探测
        target_ips = [ip for ip in public_ips if ip not in history_ips][:MAX_IP_COUNT]
        log(f"📊 准备探测 {len(target_ips)} 个新目标")

        for ip in target_ips:
            log(f"🌟 正在探测: {ip}")
            success = False
            for port in PRIMARY_PORTS:
                content_m3u = scan_ip_port(ip, port)
                if content_m3u:
                    m = re.search(r'group-title="([^"]+)"', content_m3u)
                    provider = m.group(1).split()[-1] if m else "酒店源"
                    provider = re.sub(r'[\\/:*?"<>|]', '', provider)
                    
                    filename = f"{provider}-{ip.replace('.', '_')}-{port}.m3u"
                    with open(os.path.join(OUTPUT_DIR, filename), "w", encoding="utf-8") as f:
                        f.write(content_m3u)
                    
                    with open(HISTORY_FILE, "a", encoding="utf-8") as hf:
                        hf.write(f"{ip}:{port}\n")
                    
                    log(f"🎉 保存成功: {filename}")
                    success = True
                    break
            
            if not success:
                print("\n")
                log(f"❌ {ip} 探测结束（无有效端口）")
            time.sleep(2)

    except Exception as e:
        log(f"❌ 崩溃: {e}")

if __name__ == "__main__":
    main()
