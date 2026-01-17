import requests
import re
import os
import time
import base64
import random

# ======================
# 深度配置区
# ======================
HOME_URL = "https://iptv.cqshushu.com/"
OUTPUT_DIR = "hotel"
MAX_IP_COUNT = 6  
TIMEOUT = 12 

PRIMARY_PORTS = [8082, 9901, 888, 9001, 9003, 8080, 8000, 9999, 8888, 8090, 8081, 8181, 8899, 8001, 85, 808, 20443]

UA_LIST = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0"
]

def get_headers():
    return {
        "User-Agent": random.choice(UA_LIST),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Referer": "https://fofa.info/",
        "Connection": "keep-alive"
    }

def clean_name(name):
    """提取 group-title 的最后一部分并过滤非法文件名字符"""
    if not name:
        return "未知分类"
    # 针对 "山西省太原市 酒店 山西电信" 这种格式，取最后一段
    parts = name.split()
    last_part = parts[-1] if parts else name
    # 去除非法字符
    return re.sub(r'[\\/:*?"<>|]', '', last_part)

def get_fofa_ports(ip):
    sleep_time = random.uniform(8, 15)
    print(f"    ⏳ FOFA 冷却中 ({sleep_time:.1f}s)... ", end="", flush=True)
    time.sleep(sleep_time)
    try:
        query = base64.b64encode(ip.encode()).decode()
        search_url = f"https://fofa.info/result?qbase64={query}"
        res = requests.get(search_url, headers=get_headers(), timeout=15)
        html = res.text
        if "验证码" in html or "429 Too Many Requests" in html:
            print("❌ 触发防爬验证")
            return None 
        direct_matches = re.findall(rf'{ip}:(\d+)', html)
        item_matches = re.findall(r'port-item.*?(\d+)</a>', html, re.S)
        link_matches = re.findall(r':(\d+)/', html)
        all_found = set([int(p) for p in (direct_matches + item_matches + link_matches)])
        ignore_ports = {22, 23, 443, 80, 53, 3306, 3389}
        final_ports = sorted([p for p in all_found if p not in ignore_ports])
        if final_ports:
            print(f"✅ 提取到: {final_ports}")
        else:
            print("❓ 未发现特殊端口")
        return final_ports
    except Exception as e:
        print(f"❌ 请求异常: {e}")
        return []

def scan_ip_port(ip, port):
    url = f"https://iptv.cqshushu.com/?s={ip}:{port}&t=hotel&channels=1&download=m3u"
    try:
        time.sleep(random.uniform(2, 4))
        res = requests.get(url, headers=get_headers(), timeout=TIMEOUT)
        if res.status_code == 200 and "#EXTINF" in res.text:
            return res.text
    except:
        pass
    return None

def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    print(f"🚀 启动命名改进版抓取任务 (目标: {MAX_IP_COUNT}个IP)")
    
    try:
        r = requests.get(HOME_URL, headers=get_headers(), timeout=TIMEOUT)
        ips = []
        for ip in re.findall(r"\b(?:\d{1,3}\.){3}\d{1,3}\b", r.text):
            if ip not in ips and not ip.startswith("127"):
                ips.append(ip)
        ips = ips[:MAX_IP_COUNT]
        print(f"📍 首页获取到 {len(ips)} 个待探测 IP")
    except Exception as e:
        print(f"❌ 首页访问失败: {e}")
        return

    fofa_blocked = False
    for idx, ip in enumerate(ips, 1):
        print(f"\n[{idx}/{len(ips)}] 📡 正在探测: {ip}")
        test_ports = []
        if not fofa_blocked:
            f_ports = get_fofa_ports(ip)
            if f_ports is None:
                fofa_blocked = True
                test_ports = PRIMARY_PORTS
            else:
                test_ports = f_ports + [p for p in PRIMARY_PORTS if p not in f_ports]
        else:
            test_ports = PRIMARY_PORTS

        found_success = False
        for port in test_ports:
            print(f"    ➜ 尝试端口 {port} ... ", end="", flush=True)
            content = scan_ip_port(ip, port)
            
            if content:
                # --- 改进：提取 group-title 分类 ---
                group_match = re.search(r'group-title="(.*?)"', content)
                group_name = clean_name(group_match.group(1)) if group_match else "未知分类"
                
                # 构造新文件名：山西电信_110.178.210.130.m3u
                filename = f"{group_name}_{ip}.m3u"
                
                # 如果文件名重复（同分类不同端口），加上端口以防覆盖
                save_path = os.path.join(OUTPUT_DIR, filename)
                if os.path.exists(save_path):
                    filename = f"{group_name}_{ip}_{port}.m3u"
                    save_path = os.path.join(OUTPUT_DIR, filename)

                with open(save_path, "w", encoding="utf-8") as f:
                    f.write(content)
                
                print(f"✅ 成功! 保存为: {filename}")
                found_success = True
                break 
            else:
                print("✕")
        
        if not found_success:
            print(f"    ⚠️ 该 IP 未发现有效源")
        
        time.sleep(random.uniform(5, 10))

if __name__ == "__main__":
    main()
