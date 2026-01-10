import requests
import re
import os
import time

# ======================
# 基础配置
# ======================
HOME_URL = "https://iptv.cqshushu.com/"
OUTPUT_DIR = "test"
MAX_IP_COUNT = 6
TIMEOUT = 6

# 高命中端口池（优先级从高到低）
PRIMARY_PORTS = [
    8082, 9901, 8080, 8000,
    9999, 8888, 8090, 8081,
    8181, 8899, 8001,85,808
]

SECONDARY_PORTS = [
    8088, 8001, 8899, 10000,
    18080, 28080
]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
}

# ======================
# 工具函数
# ======================
def fetch_homepage_ips():
    """
    抓取首页中按页面顺序出现的 IP
    """
    print("📥 获取首页 IP（按页面顺序）...")
    r = requests.get(HOME_URL, headers=HEADERS, timeout=TIMEOUT)
    r.raise_for_status()

    ips = []
    for ip in re.findall(r"\b(?:\d{1,3}\.){3}\d{1,3}\b", r.text):
        if ip not in ips:
            ips.append(ip)
        if len(ips) >= MAX_IP_COUNT:
            break

    print(f"共加载 {len(ips)} 个 IP")
    return ips


def try_download(ip, port):
    """
    尝试下载 m3u 文件
    """
    url = (
        "https://iptv.cqshushu.com/"
        f"?s={ip}:{port}&t=hotel&channels=1&download=m3u"
    )

    try:
        r = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
        if r.status_code == 200 and "#EXTM3U" in r.text:
            size_kb = len(r.content) // 1024
            channels = r.text.count("#EXTINF")
            return r.text, channels, size_kb
    except requests.RequestException:
        pass

    return None, 0, 0


# ======================
# 主流程
# ======================
def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    ips = fetch_homepage_ips()
    if not ips:
        print("❌ 未获取到任何 IP")
        return

    for ip in ips:
        print(f"\n🔍 扫描 IP: {ip}")
        found = False

        for port in PRIMARY_PORTS + SECONDARY_PORTS:
            print(f"  ➜ 尝试端口 {port} ...", end=" ")
            content, channels, size_kb = try_download(ip, port)

            if content:
                print(f"✅ 命中 | 频道:{channels} | 大小:{size_kb}KB")
                filename = f"channels_{ip}_{port}.m3u"
                path = os.path.join(OUTPUT_DIR, filename)

                with open(path, "w", encoding="utf-8") as f:
                    f.write(content)

                print(f"     保存: {path}")
                found = True
                break
            else:
                print("❌")

            time.sleep(1.2)  # 降速，模拟正常用户

        if not found:
            print("  ⛔ 本 IP 未发现有效端口")


if __name__ == "__main__":
    main()
