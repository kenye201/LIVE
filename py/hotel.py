import requests
import re
import os
import time
import random
import sys
from datetime import datetime

# ======================
# 深度配置区
# ======================
LOCAL_SOURCE = "data/shushu_home.html"  # 本地源码
OUTPUT_DIR = "hotel"
HISTORY_FILE = os.path.join(OUTPUT_DIR, "hotel_history.txt")
MAX_IP_COUNT = 6  
TIMEOUT = 10 # 酒店源请求通常较快，10秒足够

# 酒店源常用端口字典（已保留你提供的全部端口）
PRIMARY_PORTS = [8082, 9901, 888, 9001, 9003, 9888, 8080, 8000, 9999, 8888, 8090, 8081, 8181, 8899, 8001, 85, 808, 50001, 20443]

UA_LIST = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1"
]

def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")
    sys.stdout.flush()

def manage_hotel_history():
    """管理黑名单，周一清理"""
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
    with open(HISTORY_FILE, "a", encoding="utf-8") as f:
        f.write(f"{ip}:{port}\n")

def clean_name(name):
    if not name: return "酒店源"
    parts = name.split()
    # 提取 group-title 的最后一段，例如 "广东移动"
    last_part = parts[-1] if parts else name
    return re.sub(r'[\\/:*?"<>|]', '', last_part)

def get_headers():
    return {"User-Agent": random.choice(UA_LIST), "Referer": "https://iptv.cqshushu.com/"}

def scan_ip_port(ip, port):
    # 构造酒店源专用链接 t=hotel
    url = f"https://iptv.cqshushu.com/index.php?s={ip}:{port}&t=hotel&channels=1&download=m3u"
    try:
        # 每个端口测试间隔，防止请求过密
        time.sleep(random.uniform(1.2, 2.0))
        res = requests.get(url, headers=get_headers(), timeout=TIMEOUT)
        if res.status_code == 200 and "#EXTINF" in res.text:
            return res.text
    except: pass
    return None

def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    history_ips = manage_hotel_history()
    log(f"📜 已加载酒店历史黑名单，包含 {len(history_ips)} 个 IP")
    
    if not os.path.exists(LOCAL_SOURCE):
        log(f"❌ 找不到本地源码文件: {LOCAL_SOURCE}")
        return

    try:
        with open(LOCAL_SOURCE, "r", encoding="utf-8") as f:
            html_content = f.read()
        
        # --- 核心改进：精准定位 Hotel IPTV 区域 ---
        # 寻找包含 "Hotel IPTV" 的起始位置
        hotel_start_key = "Hotel IPTV"
        if hotel_start_key in html_content:
            # 截取从 "Hotel IPTV" 开始到页面结束的内容
            hotel_raw_area = html_content.split(hotel_start_key)[1]
            
            # 进一步精细化：如果后面还有其他 section（如组播源），则在那之前截断
            # 假设下一个区域也带 group-section 类名
            hotel_clean_area = hotel_raw_area.split('class="group-section"')[0]
            log("🎯 已成功锁定 Hotel IPTV 专属区域")
        else:
            log("⚠️ 未在源码中定位到 'Hotel IPTV' 标记，切换到全局兜底模式")
            hotel_clean_area = html_content

        # 从锁定区域中提取 IP
        # 匹配标准 IP 格式
        found_ips = re.findall(r"\b(?:\d{1,3}\.){3}\d{1,3}\b", hotel_clean_area)
        
        # 去重并过滤内网 IP
        public_ips = []
        seen = set()
        for ip in found_ips:
            if ip not in seen and not ip.startswith(("127.", "192.", "10.", "172.")):
                public_ips.append(ip)
                seen.add(ip)
        
        if not public_ips:
            log("❌ 在酒店源区域内未发现任何有效 IP。")
            return

        log(f"🔎 酒店区域识别到 {len(public_ips)} 个独立 IP")
    except Exception as e:
        log(f"❌ 解析源码失败: {e}"); return

    # --- 选取前 6 个不在黑名单中的 IP ---
    new_ips_to_scan = []
    for ip in public_ips: 
        if ip in history_ips:
            continue
        new_ips_to_scan.append(ip)
        if len(new_ips_to_scan) >= MAX_IP_COUNT:
            break

    if not new_ips_to_scan:
        log("✅ 酒店区域内的 IP 均已在黑名单中，无需重复探测。")
        return

    log(f"🚀 开始顺序探测前 {len(new_ips_to_scan)} 个酒店 IP: {new_ips_to_scan}")

    # ... 下接 scan_ip_port 探测循环 ...
    for idx, ip in enumerate(new_ips_to_scan, 1):
        log(f"\n[{idx}/{len(new_ips_to_scan)}] 📡 探测 IP: {ip}")
        # (后续探测逻辑保持不变)

    log(f"🚀 开始字典探测 {len(new_ips_to_scan)} 个酒店源 IP")

    for idx, ip in enumerate(new_ips_to_scan, 1):
        log(f"\n[{idx}/{len(new_ips_to_scan)}] 📡 探测 IP: {ip}")
        
        found_success = False
        for port in PRIMARY_PORTS:
            sys.stdout.write(f"    ➜ {port} ")
            sys.stdout.flush()
            
            content = scan_ip_port(ip, port)
            
            if content:
                sys.stdout.write("【✅】\n")
                # 提取 group-title
                group_match = re.search(r'group-title="(.*?)"', content)
                group_name = clean_name(group_match.group(1))
                
                # 命名格式: 运营商_IP_端口.m3u
                filename = f"{group_name}_{ip.replace('.', '_')}_{port}.m3u"
                
                with open(os.path.join(OUTPUT_DIR, filename), "w", encoding="utf-8") as f:
                    f.write(content)
                
                save_history(ip, port)
                log(f"🎉 成功保存: {filename}")
                found_success = True
                break # 该 IP 成功，停止其余端口测试
            else:
                sys.stdout.write("✕ ")
                sys.stdout.flush()
        
        if not found_success:
            sys.stdout.write("\n")
            log(f"⚠️ IP {ip} 所有字典端口均无效")
            
        time.sleep(random.uniform(3, 5))

    log("\n✨ 酒店源任务全部完成！")

if __name__ == "__main__":
    main()
