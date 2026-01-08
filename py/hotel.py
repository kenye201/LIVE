import requests
import re
import os
import base64
from urllib.parse import quote, urljoin

BASE_URL = "https://iptv.cqshushu.com/"
LIST_URL = "https://iptv.cqshushu.com/?t=hotel"

SESSION_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
    "Referer": LIST_URL,
    "Accept": "application/json, text/javascript, */*; q=0.01",
    "X-Requested-With": "XMLHttpRequest",
}

OUTPUT_DIR = "test"
OUTPUT_FILE = os.path.join(OUTPUT_DIR, "hotel_m3u_links.txt")


def get_ips():
    r = requests.get(LIST_URL, headers={"User-Agent": SESSION_HEADERS["User-Agent"]}, timeout=20)
    r.raise_for_status()

    encoded = re.findall(
        r"gotoIP\('([^']+)',\s*'hotel'\)",
        r.text
    )

    ips = []
    for e in encoded:
        try:
            ips.append(base64.b64decode(e).decode())
        except Exception:
            pass

    print(f"发现 {len(ips)} 个 IP")
    return ips


def get_ip_ports(ip):
    """
    关键：模拟浏览器 XHR 请求
    """
    url = f"{BASE_URL}?p={ip}&t=hotel&_js=1"
    r = requests.get(url, headers=SESSION_HEADERS, timeout=20)

    if r.status_code != 200:
        print(f"[403] 跳过 {ip}")
        return []

    # JSON / JS 中包含 IP:端口
    ports = re.findall(
        rf"{re.escape(ip)}:\d+",
        r.text
    )

    return list(set(ports))


def get_m3u_link(ip_port):
    s = quote(ip_port)
    url = f"{BASE_URL}?s={s}&t=hotel"

    r = requests.get(url, headers={"User-Agent": SESSION_HEADERS["User-Agent"]}, timeout=20)
    if r.status_code != 200:
        return None

    m = re.search(r"href=['\"]([^'\"]+download=m3u)['\"]", r.text)
    if not m:
        return None

    return urljoin(BASE_URL, m.group(1))


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    results = []
    ips = get_ips()

    for ip in ips:
        print(f"处理 IP {ip}")
        for ip_port in get_ip_ports(ip):
            print(f"  → {ip_port}")
            m3u = get_m3u_link(ip_port)
            if m3u:
                results.append(m3u)

    results = sorted(set(results))

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        for u in results:
            f.write(u + "\n")

    print(f"\n完成，共获取 {len(results)} 条 M3U")
    print(f"保存至 {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
