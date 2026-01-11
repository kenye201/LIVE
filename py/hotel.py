import requests
import re
import os
import time
import base64

# ======================
# 配置优化
# ======================
HOME_URL = "https://iptv.cqshushu.com/"
OUTPUT_DIR = "test"
MAX_IP_COUNT = 6
TIMEOUT = 15 

# 备用端口（如果 FOFA 没搜到，依然用这些兜底）
PRIMARY_PORTS = [8082, 9901, 888, 9003, 8080, 8000, 9999, 8888, 8090, 8081, 8181, 8899, 8001, 85, 808, 20443]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

def get_fofa_ports(ip):
    """通过 FOFA 搜索该 IP 开放的端口"""
    try:
        # 将 IP 转为 Base64 编码用于 FOFA 查询
        query = base64.b64encode(ip.encode()).decode()
        search_url = f"https://fofa.info/result?qbase64={query}"
        
        res = requests.get(search_url, headers=HEADERS, timeout=10)
        # 正则匹配页面中的端口号（通常在结果列表的 IP 后面）
        # FOFA 结果通常包含 <a href="http://1.1.1.1:8080"
        found_ports = re.findall(rf'{ip}:(\d+)', res.text)
        
        # 转换成整数并去重
        ports = list(set([int(p) for p in found_ports]))
        return ports
    except Exception as e:
        print(f"   ⚠️ FOFA 探测失败: {e}")
        return []

def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    print(f"🚀 开始精准探测抓取任务... (超时: {TIMEOUT}s)")
    
    try:
        r = requests.get(HOME_URL, headers=HEADERS, timeout=TIMEOUT)
        r.raise_for_status()
        ips = []
        for ip in re.findall(r"\b(?:\d{1,3}\.){3}\d{1,3}\b", r.text):
            if ip not in ips and not ip.startswith("127"):
                ips.append(ip)
        
        ips = ips[:MAX_IP_COUNT]
        print(f"🔎 首页共发现 {len(ips)} 个待探测 IP")
    except Exception as e:
        print(f"❌ 无法访问首页: {e}")
        return

    for idx, ip in enumerate(ips, 1):
        print(f"\n[{idx}/{len(ips)}] 📡 目标 IP: {ip}")
        
        # --- 第一步：FOFA 预探测 ---
        print(f"   🔍 正在 FOFA 检索开放端口...", end="", flush=True)
        fofa_ports = get_fofa_ports(ip)
        
        # 整合探测列表：优先 FOFA 发现的，然后才是 PRIMARY_PORTS
        test_ports = fofa_ports + [p for p in PRIMARY_PORTS if p not in fofa_ports]
        
        if fofa_ports:
            print(f" 找到: {fofa_ports}")
        else:
            print(" 未发现记录，使用穷举兜底。")

        # --- 第二步：精准尝试 ---
        found_any_port = False
        for port in test_ports:
            print(f"   ➜ 尝试端口 {port} ... ", end="", flush=True)
            url = f"https://iptv.cqshushu.com/?s={ip}:{port}&t=hotel&channels=1&download=m3u"
            
            try:
                # 给 FOFA 找到的端口稍微多一点重试机会
                res = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
                if res.status_code == 200 and "#EXTINF" in res.text:
                    filename = f"raw_{ip}_{port}.m3u"
                    with open(os.path.join(OUTPUT_DIR, filename), "w", encoding="utf-8") as f:
                        f.write(res.text)
                    print(f"✅ 成功！")
                    found_any_port = True
                    break
                else:
                    print("✕")
            except:
                print("✕")
        
        if not found_any_port:
            print(f"   ⚠️ IP {ip} 最终未发现有效端口。")
        
        time.sleep(2)

if __name__ == "__main__":
    main()
