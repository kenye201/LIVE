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
LOCAL_SOURCE = "data/shushu_home.html"  # 源码路径
OUTPUT_DIR = "hotel"
HISTORY_FILE = os.path.join(OUTPUT_DIR, "hotel_history.txt")
MAX_IP_COUNT = 6    # 每次处理前 6 个新 IP
TIMEOUT = 12        # 单次请求超时

# 酒店源高频端口字典
PRIMARY_PORTS = [8000, 8080, 9901, 8082, 8888, 9001, 8001, 8090, 9999, 888, 9003, 8081, 8181, 8899, 50001]

UA_LIST = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1"
]

def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")
    sys.stdout.flush()

def manage_hotel_history():
    """管理黑名单：加载历史记录，周一自动清理"""
    if datetime.now().weekday() == 0: 
        if os.path.exists(HISTORY_FILE):
            log("📅 周一例行清理：删除酒店历史 IP 表。")
            os.remove(HISTORY_FILE)
    
    history_ips = set()
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            for line in f:
                if ":" in line:
                    history_ips.add(line.split(':')[0].strip())
    return history_ips

def save_history(ip, port):
    """保存成功的记录到黑名单"""
    with open(HISTORY_FILE, "a", encoding="utf-8") as f:
        f.write(f"{ip}:{port}\n")

def clean_name(name):
    """清洗运营商/地区名称，用于文件名"""
    if not name: return "酒店源"
    # 取最后一段，例如 "湖北电信"
    parts = name.split()
    last_part = parts[-1] if parts else name
    return re.sub(r'[\\/:*?"<>|]', '', last_part)

def scan_ip_port(ip, port):
    """尝试扫描特定 IP 和端口"""
    url = f"https://iptv.cqshushu.com/index.php?s={ip}:{port}&t=hotel&channels=1&download=m3u"
    try:
        # 模拟人工测试间隔
        time.sleep(random.uniform(1.0, 1.8))
        headers = {"User-Agent": random.choice(UA_LIST), "Referer": "https://iptv.cqshushu.com/"}
        res = requests.get(url, headers=headers, timeout=TIMEOUT)
        if res.status_code == 200 and "#EXTINF" in res.text:
            return res.text
    except:
        pass
    return None

def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    history_ips = manage_hotel_history()
    log(f"📜 已加载黑名单，包含 {len(history_ips)} 个 IP")
    
    if not os.path.exists(LOCAL_SOURCE):
        log(f"❌ 找不到本地源码文件: {LOCAL_SOURCE}")
        return

    try:
        with open(LOCAL_SOURCE, "r", encoding="utf-8") as f:
            html = f.read()
        
        # 1. 区域锁定：只看 Hotel IPTV 板块
        if "Hotel IPTV" in html:
            # 截取 Hotel IPTV 标题之后，到下一个分类标题之前的内容
            hotel_area = html.split("Hotel IPTV")[1].split('class="group-section"')[0]
            log("🎯 已成功锁定 Hotel IPTV 数据块")
        else:
            hotel_area = html
            log("⚠️ 未在源码中定位到 Hotel IPTV 标记，将全局扫描")

        # 2. 提取 IP (双路并行)
        found_ips = []

        # 路 A: 解码 gotoIP('Base64字符串', 'hotel') 中的 IP
        b64_matches = re.findall(r"gotoIP\('([^']+)',\s*'hotel'\)", hotel_area)
        for b in b64_matches:
            try:
                decoded = base64.b64decode(b).decode('utf-8')
                if re.match(r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$", decoded):
                    found_ips.append(decoded)
            except:
                continue

        # 路 B: 抓取标签中间带空格换行的明文 IP
        text_ips = re.findall(r">\s*(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})\s*<", hotel_area)
        found_ips.extend(text_ips)

        # 3. 整理 IP：去重、去内网、保持顺序
        public_ips = []
        seen = set()
        for ip in found_ips:
            if ip not in seen and not ip.startswith(("127.", "192.", "10.", "172.")):
                public_ips.append(ip)
                seen.add(ip)
        
        if not public_ips:
            # 最后的保底尝试：全局全量提取
            public_ips = list(dict.fromkeys(re.findall(r"(?:\d{1,3}\.){3}\d{1,3}", hotel_area)))

        if not public_ips:
            log("❌ 区域内未识别到任何有效 IP 字符串。")
            return
        
        log(f"🔎 成功识别到 {len(public_ips)} 个潜在酒店 IP")

        # 4. 获取前 6 个新 IP 执行探测
        target_ips = [ip for ip in public_ips if ip not in history_ips][:MAX_IP_COUNT]
        
        if not target_ips:
            log("✅ 所有候选 IP 均已在黑名单中，本次无需探测。")
            return

        log(f"🚀 开始顺序探测前 {len(target_ips)} 个目标 IP")

        for idx, ip in enumerate(target_ips, 1):
            log(f"\n[{idx}/{len(target_ips)}] 📡 探测 IP: {ip}")
            found_success = False
            
            for port in PRIMARY_PORTS:
                sys.stdout.write(f"    ➜ {port} ")
                sys.stdout.flush()
                
                content = scan_ip_port(ip, port)
                if content:
                    sys.stdout.write("【✅ 成功】\n")
                    # 提取 group-title 命名
                    group_match = re.search(r'group-title="(.*?)"', content)
                    group_name = clean_name(group_match.group(1)) if group_match else "酒店源"
                    
                    filename = f"{group_name}_{ip.replace('.', '_')}_{port}.m3u"
                    with open(os.path.join(OUTPUT_DIR, filename), "w", encoding="utf-8") as f:
                        f.write(content)
                    
                    # 记录成功历史
                    save_history(ip, port)
                    log(f"🎉 任务完成: {filename}")
                    found_success = True
                    break 
                else:
                    sys.stdout.write("✕ ")
                    sys.stdout.flush()
            
            if not found_success:
                sys.stdout.write("\n")
                log(f"⚠️ IP {ip} 尝试了所有字典端口均未通过")
            
            time.sleep(3) # IP 间的长冷却

    except Exception as e:
        log(f"❌ 运行崩溃: {e}")

if __name__ == "__main__":
    main()
