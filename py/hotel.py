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
OUTPUT_DIR = "test"
MAX_IP_COUNT = 8  
TIMEOUT = 12 

# 常用酒店端口（穷举兜底方案）
PRIMARY_PORTS = [8082, 9901, 888, 9003, 8080, 8000, 9999, 8888, 8090, 8081, 8181, 8899, 8001, 85, 808, 20443]

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
    """
    改进版 FOFA 端口提取：
    支持正则匹配 ip:port 格式以及 FOFA 网页特有的 port-item 结构
    """
    sleep_time = random.uniform(8, 15)  # 稍微拉长等待，降低风控风险
    print(f"   ⏳ FOFA 冷却中 ({sleep_time:.1f}s)... ", end="", flush=True)
    time.sleep(sleep_time)

    try:
        query = base64.b64encode(ip.encode()).decode()
        search_url = f"https://fofa.info/result?qbase64={query}"
        
        res = requests.get(search_url, headers=get_headers(), timeout=15)
        html = res.text
        
        if "验证码" in html or "429 Too Many Requests" in html:
            print("❌ 触发防爬验证")
            return None 

        # 策略 1：直接匹配 IP:PORT 结构
        direct_matches = re.findall(rf'{ip}:(\d+)', html)
        
        # 策略 2：提取所有 class="port-item" 里的数字 (FOFA 列表页常用结构)
        item_matches = re.findall(r'port-item.*?(\d+)</a>', html, re.S)
        
        # 策略 3：备用正则，匹配所有类似端口的链接
        link_matches = re.findall(r':(\d+)/', html)

        # 合并结果
        all_found = set([int(p) for p in (direct_matches + item_matches + link_matches)])
        
        # 过滤掉非酒店常用端口 (如 22, 443, 80 等)
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
    """访问目标地址尝试抓取 m3u 内容"""
    url = f"https://iptv.cqshushu.com/?s={ip}:{port}&t=hotel&channels=1&download=m3u"
    try:
        # 给目标服务器留出喘息时间
        time.sleep(random.uniform(2, 4))
        res = requests.get(url, headers=get_headers(), timeout=TIMEOUT)
        if res.status_code == 200 and "#EXTINF" in res.text:
            return res.text
    except:
        pass
    return None

def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    print(f"🚀 启动慢速精准抓取任务 (目标: {MAX_IP_COUNT}个IP)")
    
    # 1. 获取首页 IP 列表
    try:
        r = requests.get(HOME_URL, headers=get_headers(), timeout=TIMEOUT)
        r.raise_for_status()
        ips = []
        for ip in re.findall(r"\b(?:\d{1,3}\.){3}\d{1,3}\b", r.text):
            if ip not in ips and not ip.startswith("127"):
                ips.append(ip)
        ips = ips[:MAX_IP_COUNT]
        print(f"📍 首页获取到 {len(ips)} 个待探测 IP")
    except Exception as e:
        print(f"❌ 首页访问失败: {e}")
        return

    # 2. 循环探测
    fofa_blocked = False
    for idx, ip in enumerate(ips, 1):
        print(f"\n[{idx}/{len(ips)}] 📡 正在探测: {ip}")
        
        test_ports = []
        
        if not fofa_blocked:
            f_ports = get_fofa_ports(ip)
            if f_ports is None:
                fofa_blocked = True
                print("   ⚠️ FOFA 已拦截，切换为全量穷举模式。")
                test_ports = PRIMARY_PORTS
            else:
                # 优先级：FOFA 发现的端口 > PRIMARY_PORTS
                test_ports = f_ports + [p for p in PRIMARY_PORTS if p not in f_ports]
        else:
            test_ports = PRIMARY_PORTS

        # 3. 执行测试
        found_success = False
        for port in test_ports:
            print(f"   ➜ 尝试端口 {port} ... ", end="", flush=True)
            content = scan_ip_port(ip, port)
            
            if content:
                filename = f"raw_{ip}_{port}.m3u"
                with open(os.path.join(OUTPUT_DIR, filename), "w", encoding="utf-8") as f:
                    f.write(content)
                print("✅ 成功！")
                found_success = True
                break # 该 IP 成功，直接跳到下一个 IP
            else:
                print("✕")
        
        if not found_success:
            print(f"   ⚠️ 该 IP 未发现有效源")
            
        # 降低整体频率，保护 GitHub Runner 的 IP
        time.sleep(random.uniform(5, 10))

if __name__ == "__main__":
    main()
