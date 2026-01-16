import requests
import re
import os
import time
import random
import base64

# ======================
# 深度配置区
# ======================
HOME_URL = "https://iptv.cqshushu.com/"
OUTPUT_DIR = "test_multicast"          # 所有抓取的组播源文件统一放这里
MAX_IP_COUNT = 6                       # 只抓后6个组播IP
TIMEOUT = 12                           # 单次请求超时

# 组播常用端口（根据常见酒店/组播源整理，优先高频）
PRIMARY_MULTICAST_PORTS = [
    8888, 4022, 8188，5146, 5140, 4056, 12320, 10000, 8080, 8000,
    9901, 8090, 8181, 1234, 4000, 4001, 5148, 12345,
    9000, 9001, 888, 9003, 8082, 20443, 85, 8081, 9999, 8001, 8899
]

# 随机 User-Agent 库
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
        "Accept-Language": "zh-CN,zh;q=0.8,zh-TW;q=0.7,zh-HK;q=0.5,en-US;q=0.3,en;q=0.2",
        "Referer": "https://fofa.info/",
        "Connection": "keep-alive"
    }

def get_fofa_ports(ip):
    """FOFA 端口提取（原函数复用）"""
    sleep_time = random.uniform(8, 15)
    print(f" ⏳ FOFA 冷却中 ({sleep_time:.1f}s)... ", end="", flush=True)
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
    """使用正确的链接格式生成页面，然后提取并下载真正的 M3U 文件"""
    generate_url = f"https://iptv.cqshushu.com/?s={ip}:{port}&t=multicast&channels=1&download=m3u"
    
    try:
        time.sleep(random.uniform(2, 4))
        print(f"  生成页面: {generate_url}")
        
        res = requests.get(generate_url, headers=get_headers(), timeout=TIMEOUT)
        if res.status_code != 200:
            print(f"  生成页面失败: 状态码 {res.status_code}")
            return None
        
        # 提取真正的 M3U 下载链接（常见模式：href="/download/xxx.m3u" 或类似）
        m3u_match = re.search(r'href="([^"]*\.m3u[^"]*)"', res.text, re.IGNORECASE)
        if not m3u_match:
            print("  未在页面找到 M3U 下载链接")
            return None
        
        m3u_path = m3u_match.group(1)
        if m3u_path.startswith('/'):
            m3u_url = "https://iptv.cqshushu.com" + m3u_path
        else:
            m3u_url = m3u_path
        
        print(f"  找到 M3U 下载链接: {m3u_url}")
        
        # 请求真正的 M3U 文件
        time.sleep(random.uniform(1, 3))
        m3u_res = requests.get(m3u_url, headers=get_headers(), timeout=TIMEOUT, allow_redirects=True)
        
        if m3u_res.status_code == 200 and "#EXTINF" in m3u_res.text:
            print(f"  M3U 下载成功，长度 {len(m3u_res.text)} 字符")
            return m3u_res.text
        else:
            print(f"  下载 M3U 失败: 状态码 {m3u_res.status_code}")
            return None
    
    except Exception as e:
        print(f"  请求异常: {e}")
        return None

def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    print(f"🚀 启动组播源抓取任务 (目标: 后 {MAX_IP_COUNT} 个组播IP)")
    print(f"输出目录: {OUTPUT_DIR}")
    
    # 1. 获取首页所有 IP
    try:
        r = requests.get(HOME_URL, headers=get_headers(), timeout=TIMEOUT)
        r.raise_for_status()
        
        all_ips = []
        for ip in re.findall(r"\b(?:\d{1,3}\.){3}\d{1,3}\b", r.text):
            if ip not in all_ips and not ip.startswith("127") and not ip.startswith("192.168") and not ip.startswith("10."):
                all_ips.append(ip)
        
        print(f"📍 首页共提取到 {len(all_ips)} 个 IP")
        if len(all_ips) > 0:
            print("前几个IP示例:", all_ips[:6])
        
        # 取后 6 个（组播部分）
        multicast_ips = all_ips[-MAX_IP_COUNT:] if len(all_ips) >= MAX_IP_COUNT else all_ips
        print(f"🎯 锁定后 {len(multicast_ips)} 个组播 IP: {multicast_ips}")
    
    except Exception as e:
        print(f"❌ 首页访问失败: {e}")
        return

    # 2. 循环探测后6个 IP
    fofa_blocked = False
    for idx, ip in enumerate(multicast_ips, 1):
        print(f"\n[{idx}/{len(multicast_ips)}] 📡 正在探测组播 IP: {ip}")
        
        test_ports = []
        
        if not fofa_blocked:
            f_ports = get_fofa_ports(ip)
            if f_ports is None:
                fofa_blocked = True
                print(" ⚠️ FOFA 已拦截，切换为全量穷举模式。")
                test_ports = PRIMARY_MULTICAST_PORTS
            else:
                test_ports = f_ports + [p for p in PRIMARY_MULTICAST_PORTS if p not in f_ports]
        else:
            test_ports = PRIMARY_MULTICAST_PORTS

        found_success = False
        for port in test_ports:
            print(f" ➜ 尝试端口 {port} ... ", end="", flush=True)
            content = scan_ip_port(ip, port)
            
            if content:
                filename = f"multicast_raw_{ip}_{port}.m3u"
                with open(os.path.join(OUTPUT_DIR, filename), "w", encoding="utf-8") as f:
                    f.write(content)
                print("✅ 成功！文件已保存:", filename)
                found_success = True
                break  # 该 IP 成功，直接跳到下一个 IP
            else:
                print("✕")
        
        if not found_success:
            print(f" ⚠️ 该组播 IP 未发现有效源")
        
        # 延时防风控
        time.sleep(random.uniform(5, 12))

    print("\n任务完成！所有抓取文件已保存在:", OUTPUT_DIR)

if __name__ == "__main__":
    main()
