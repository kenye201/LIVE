import requests
import re
import os
import time

# ======================
# 配置优化
# ======================
HOME_URL = "https://iptv.cqshushu.com/"
OUTPUT_DIR = "test"
MAX_IP_COUNT = 6
TIMEOUT = 15 

# 重新整理了固定顺序：把最常见的 8082, 9901, 8081 等放在最前面
PRIMARY_PORTS = [8082, 9901,888,9003,8080, 8000, 9999, 8888, 8090, 8081, 8181, 8899, 8001, 85, 808,20443]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Connection": "keep-alive"
}

def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    print(f"🚀 开始固定顺序抓取任务... (超时: {TIMEOUT}s)")
    
    try:
        r = requests.get(HOME_URL, headers=HEADERS, timeout=TIMEOUT)
        r.raise_for_status()
        # 提取 IP
        ips = []
        for ip in re.findall(r"\b(?:\d{1,3}\.){3}\d{1,3}\b", r.text):
            if ip not in ips and not ip.startswith("127"):
                ips.append(ip)
        
        ips = ips[:MAX_IP_COUNT]
        print(f"🔎 首页共发现 {len(ips)} 个唯一 IP")
    except Exception as e:
        print(f"❌ 无法访问首页: {e}")
        return

    for idx, ip in enumerate(ips, 1):
        print(f"\n[{idx}/{len(ips)}] 📡 正在扫描 IP: {ip}")
        found_any_port = False
        
        # ❌ 已删除 random.shuffle，现在将严格按照 PRIMARY_PORTS 的顺序执行
        for port in PRIMARY_PORTS:
            print(f"   ➜ 尝试端口 {port} ... ", end="", flush=True)
            url = f"https://iptv.cqshushu.com/?s={ip}:{port}&t=hotel&channels=1&download=m3u"
            
            # 保持重试机制，增加稳定性
            success = False
            for retry in range(2):
                try:
                    # 降低延迟，提升固定顺序下的扫描手感
                    time.sleep(1) 
                    res = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
                    
                    if res.status_code == 200 and "#EXTINF" in res.text:
                        filename = f"raw_{ip}_{port}.m3u"
                        with open(os.path.join(OUTPUT_DIR, filename), "w", encoding="utf-8") as f:
                            f.write(res.text)
                        print(f"✅ 成功！")
                        found_any_port = True
                        success = True
                        break
                except Exception:
                    continue # 第一次失败自动重试
            
            if success:
                break # 该 IP 成功抓到一个端口，直接换下一个 IP
            else:
                print("✕")
        
        if not found_any_port:
            print(f"   ⚠️  IP {ip} 未发现有效端口。")
        
        # 减小 IP 间的等待时间，加快速度
        time.sleep(2)

if __name__ == "__main__":
    main()
