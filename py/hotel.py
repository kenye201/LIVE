import requests
import re
import os
import base64
from urllib.parse import urljoin, quote

BASE_URL = "https://iptv.cqshushu.com/"
LIST_URL = "https://iptv.cqshushu.com/?t=hotel"

HEADERS = {
    "User-Agent": "Mozilla/5.0"
}

OUTPUT_DIR = "test"
OUTPUT_FILE = os.path.join(OUTPUT_DIR, "hotel_m3u_links.txt")


def get_ip_list():
    """
    第 1 层：从列表页提取 base64 IP
    """
    r = requests.get(LIST_URL, headers=HEADERS, timeout=20)
    r.raise_for_status()

    encoded_ips = re.findall(
        r"gotoIP\('([^']+)',\s*'hotel'\)",
        r.text
    )

    ips = []
    for e in encoded_ips:
        try:
            ip = base64.b64decode(e).decode()
            ips.append(ip)
        except Exception:
            pass

    print(f"发现 {len(ips)} 个 IP")
    return ips


def get_ip_ports(ip):
    """
    第 2 层：通过 ?p=ip 获取 IP:端口
    """
    url = f"{BASE_URL}?p={ip}&t=hotel&_js=1"
    r = requests.get(url, headers=HEADERS, timeout=20)
    r.raise_for_status()

    # 匹配 IP:端口
    ports = re.findall(
        rf"{re.escape(ip)}:\d+",
        r.text
    )

    return list(set(ports))


def get_m3u_link(ip_port):
    """
    第 3 层：获取 m3u 下载链接
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

    ips = get_ip_list()
    for ip in ips:
        print(f"处理 IP {ip}")
        ip_ports = get_ip_ports(ip)

        for ip_port in ip_ports:
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
