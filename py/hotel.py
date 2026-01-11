import requests
import re
import os
import time
import random

# ======================
# 配置优化
# ======================
HOME_URL = "https://iptv.cqshushu.com/"
OUTPUT_DIR = "test"
MAX_IP_COUNT = 6
TIMEOUT = 15  # 延长超时时间，给弱网环境更多时间
PRIMARY_PORTS = [8082, 9901, 8080, 8000, 9999, 8888, 8090, 8081, 8181, 8899, 8001, 85, 808,20443,888,9003]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Connection": "keep-alive"
}

def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    print(f"🚀 开始慢速深度抓取任务... (当前超时设定: {TIMEOUT}s)")
    
    try:
        r = requests.get(HOME_URL, headers=HEADERS, timeout=TIMEOUT)
        r.raise_for_status()
        # 寻找网页中明确提到的 IP:端口 组合（如 171.127.54.187:888）
        # 优先抓取网页上显示的活跃组合
        active_sources = re.findall(r"\b(?:\d{1,3}\.){3}\d{1,3}:\d+\b", r.text)
        ips = list(set(re.findall(r"\b(?:\d{1,3}\.){3}\d{1,3}\b", r.text)))[:MAX_IP_COUNT]
        
        print(f"🔎 首页共发现 {len(ips)} 个候选 IP，优先尝试活跃源...")
    except Exception as e:
        print(f"❌ 无法访问首页: {e}")
        return

    for idx, ip in enumerate(ips, 1):
        print(f"\n[{idx}/{len(ips)}] 📡 正在扫描 IP: {ip}")
        found_any_port = False
        
        # 为了提高成功率，我们将端口列表随机打乱，避免固定顺序被防火墙拦截
        random.shuffle(PRIMARY_PORTS)
        
        for port in PRIMARY_PORTS:
            print(f"   ➜ 尝试端口 {port} ... ", end="", flush=True)
            url = f"https://iptv.cqshushu.com/?s={ip}:{port}&t=hotel&channels=1&download=m3u"
            
            # 尝试最多 2 次重试
            for retry in range(2):
                try:
                    # 每次尝试前增加随机延迟 (1.0 到 2.5 秒)
                    time.sleep(random.uniform(1.0, 2.5))
                    
                    res = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
                    
                    if res.status_code == 200 and "#EXTINF" in res.text:
                        filename = f"raw_{ip}_{port}.m3u"
                        with open(os.path.join(OUTPUT_DIR, filename), "w", encoding="utf-8") as f:
                            f.write(res.text)
                        print(f"✅ 成功！(重试次数: {retry})")
                        found_any_port = True
                        break
                    else:
                        if retry == 0: continue # 第一次失败则立即重试
                        print("✕ (数据为空或格式不对)")
                except Exception:
                    if retry == 0: continue
                    print("✕ (连接超时)")
            
            if found_any_port:
                break # 该 IP 已成功，跳到下一个 IP
        
        if not found_any_port:
            print(f"   ⚠️  IP {ip} 扫描完毕，未捕获有效数据。")
        
        # 每个 IP 扫描完后大休息，模拟真人浏览
        time.sleep(5)

if __name__ == "__main__":
    main()
