import requests
import re
import os
import time

# 配置
HOME_URL = "https://iptv.cqshushu.com/"
OUTPUT_DIR = "test"
MAX_IP_COUNT = 6  # 增加抓取数量
TIMEOUT = 6
PRIMARY_PORTS = [8082, 9901, 8080, 8000, 9999, 8888, 8090, 8081, 8181, 8899, 8001, 85, 808]
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    print(f"🚀 开始运行 IPTV 抓取任务...")
    
    try:
        r = requests.get(HOME_URL, headers=HEADERS, timeout=TIMEOUT)
        r.raise_for_status()
        # 提取并去重 IP
        ips = []
        for ip in re.findall(r"\b(?:\d{1,3}\.){3}\d{1,3}\b", r.text):
            if ip not in ips and not ip.startswith("127"):
                ips.append(ip)
        
        ips = ips[:MAX_IP_COUNT]
        print(f"🔎 首页共发现 {len(ips)} 个有效候选 IP")
    except Exception as e:
        print(f"❌ 无法访问首页: {e}")
        return

    for idx, ip in enumerate(ips, 1):
        print(f"[{idx}/{len(ips)}] 📡 正在扫描 IP: {ip}")
        found_any_port = False
        
        for port in PRIMARY_PORTS:
            # 实时显示尝试的端口
            print(f"   ➜ 尝试端口 {port} ... ", end="", flush=True)
            url = f"https://iptv.cqshushu.com/?s={ip}:{port}&t=hotel&channels=1&download=m3u"
            
            try:
                res = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
                if "#EXTINF" in res.text:
                    filename = f"raw_{ip}_{port}.m3u"
                    with open(os.path.join(OUTPUT_DIR, filename), "w", encoding="utf-8") as f:
                        f.write(res.text)
                    print(f"✅ 成功！已保存至 {filename}")
                    found_any_port = True
                    break # 找到该 IP 的一个可用端口后跳向下一个 IP
                else:
                    print("✕ (无效数据)")
            except Exception:
                print("✕ (连接超时/失败)")
            
            time.sleep(0.2) # 稍微停顿，防止被封
            
        if not found_any_port:
            print(f"   ⚠️  IP {ip} 所有端口尝试完毕，未发现有效服务。")

if __name__ == "__main__":
    main()
