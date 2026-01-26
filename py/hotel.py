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
TIMEOUT = 12

# 酒店源高频端口
PRIMARY_PORTS = [8000, 8080, 9901, 8082, 8888, 9001, 8001, 8090, 9999, 888, 9003, 8081, 50001]

UA_LIST = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1"
]

def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")
    sys.stdout.flush()

def manage_hotel_history():
    # 周一清理历史
    if datetime.now().weekday() == 0 and os.path.exists(HISTORY_FILE):
        os.remove(HISTORY_FILE)
    history_ips = set()
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            for line in f:
                if ":" in line: 
                    history_ips.add(line.split(':')[0].strip())
    return history_ips

def scan_ip_port(ip, port):
    url = f"https://iptv.cqshushu.com/index.php?s={ip}:{port}&t=hotel&channels=1&download=m3u"
    try:
        time.sleep(random.uniform(1.0, 1.5))
        res = requests.get(url, headers={"User-Agent": random.choice(UA_LIST)}, timeout=TIMEOUT)
        return res.text if (res.status_code == 200 and "#EXTINF" in res.text) else None
    except: return None

def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    history_ips = manage_hotel_history()
    log(f"📜 已加载黑名单，包含 {len(history_ips)} 个 IP")
    
    if not os.path.exists(LOCAL_SOURCE):
        log(f"❌ 找不到文件: {LOCAL_SOURCE}"); return

    try:
        with open(LOCAL_SOURCE, "r", encoding="utf-8") as f:
            html = f.read()
        
        # 1. 精准切割酒店区域 (排除前面的组播源)
        if "Hotel IPTV" in html:
            # 找到 Hotel IPTV 后，截取到下一个 group-section 之前
            hotel_area = html.split("Hotel IPTV")[1].split('class="group-section"')[0]
            log("🎯 已成功锁定 Hotel IPTV 数据块")
        else:
            hotel_area = html
            log("⚠️ 未定位到酒店标记，使用全局扫描")

        # 2. 极其宽松的 IP 匹配 (套用组播脚本的逻辑)
        # 匹配任何符合 IP 格式的纯文本，不管它是在 <td> 里还是哪里
        raw_ips = re.findall(r"(?:\d{1,3}\.){3}\d{1,3}", hotel_area)
        
        # 3. 过滤并保持顺序
        public_ips = []
        seen = set()
        for ip in raw_ips:
            if ip not in seen and not ip.startswith(("127.", "192.", "10.", "172.")):
                public_ips.append(ip)
                seen.add(ip)
        
        if not public_ips:
            log("❌ 区域内未发现任何 IP 字符串。")
            return
        
        log(f"🔎 成功提取 {len(public_ips)} 个酒店 IP")

        # 4. 获取前 6 个未处理过的 IP
        target_ips = [ip for ip in public_ips if ip not in history_ips][:MAX_IP_COUNT]
        
        if not target_ips:
            log("✅ 所有候选 IP 均已在黑名单中。")
            return

        log(f"🚀 开始扫描前 {len(target_ips)} 个新目标: {target_ips}")

        for idx, ip in enumerate(target_ips, 1):
            log(f"\n[{idx}/{len(target_ips)}] 📡 探测 IP: {ip}")
            found = False
            for port in PRIMARY_PORTS:
                sys.stdout.write(f"    ➜ {port} ")
                sys.stdout.flush()
                
                content = scan_ip_port(ip, port)
                if content:
                    sys.stdout.write("【✅】\n")
                    # 命名处理
                    m = re.search(r'group-title="(.*?)"', content)
                    name = m.group(1).split()[-1] if m else "酒店源"
                    name = re.sub(r'[\\/:*?"<>|]', '', name)
                    
                    fname = f"{name}_{ip.replace('.','_')}_{port}.m3u"
                    with open(os.path.join(OUTPUT_DIR, fname), "w", encoding="utf-8") as f:
                        f.write(content)
                    
                    # 记录历史
                    with open(HISTORY_FILE, "a", encoding="utf-8") as h:
                        h.write(f"{ip}:{port}\n")
                    
                    log(f"🎉 成功保存: {fname}")
                    found = True
                    break
                else:
                    sys.stdout.write("✕ ")
                    sys.stdout.flush()
            
            if not found:
                sys.stdout.write("\n")
                log(f"⚠️ IP {ip} 所有端口均失败")
            
            time.sleep(3)

    except Exception as e:
        log(f"❌ 程序运行崩溃: {e}")

if __name__ == "__main__":
    main()
