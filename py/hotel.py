import requests
import re
import os
import base64
from urllib.parse import quote, urljoin

BASE_URL = "https://iptv.cqshushu.com/"
LIST_URL = "https://iptv.cqshushu.com/?t=hotel"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
    "Referer": "https://iptv.cqshushu.com/",
}

OUTPUT_DIR = "test"
OUTPUT_FILE = os.path.join(OUTPUT_DIR, "hotel_m3u_links.txt")


def get_ip_and_ports():
    """
    从 Hotel IPTV 列表页中直接解析 IP + 端口
    """
    r = requests.get(LIST_URL, headers=HEADERS, timeout=20)
    r.raise_for_status()
    html = r.text

    # 1. 找出所有 base64 IP
    encoded_ips = re.findall(
        r"gotoIP\('([^']+)',\s*'hotel'\)",
        html
    )

    results = set()

    for e in encoded_ips:
        try:
            ip = base64.b64decode(e).decode()
        except Exception:
            continue

        # 2. 在整页 HTML / JS 中找该 IP 对应的端口
        ports = re.findall(
            rf"{re.escape(ip)}:(\d+)",
            html
        )

        for p in ports:
            results.add(f"{ip}:{p}")

    print(f"发现 {len(results)} 个 IP:端口")
    return sorted(results)


def get_m3u_link(ip_port):
    """
    第三层：获取 m3u 下载链接
    """
    s_value = quote(ip_port)
    url = f"{BASE_URL}?s={s_value}&t=hotel"

    r = requests.get(url, headers=HEADERS, timeout=20)
    r.raise_for_status()

    m = re.search(
        r"href=['\"]([^'\"]+download=m3u)['\"]",
        r.text
    )

    if not m:
        return None

    return urljoin(BASE_URL, m.group(1))


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    results = []
    ip_ports = get_ip_and_ports()

    for ip_port in ip_ports:
        print(f"处理 {ip_port}")
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
