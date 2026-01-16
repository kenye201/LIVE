import requests
import re
import os
import time
import random

# ======================
# 配置区
# ======================
HOME_URL = "https://iptv.cqshushu.com/"
# 分页链接模板（从第2页开始使用，避开第1页的参数化访问）
PAGE_URL_TEMPLATE = "https://iptv.cqshushu.com/?t=all&province=all&limit=6&hotel_page=1&multicast_page={}"

OUTPUT_DIR = "zubo"
MAX_PAGES = 5              # 设置要抓取的页数
TIMEOUT = 12

# 组播常用端口（按命中率排序，前几个最常用）
PRIMARY_MULTICAST_PORTS = [
    8888, 4022, 8188, 8022, 7777, 5146, 5140, 4056, 12320, 10000, 8080, 8000,
    9901, 8090, 8181, 1234, 4000, 4001, 5148, 12345, 9000, 8082, 20443
]

UA_LIST = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Edge/120.0.0.0"
]

def get_headers():
    return {
        "User-Agent": random.choice(UA_LIST),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Referer": "https://iptv.cqshushu.com/",
        "Connection": "keep-alive"
    }

def scan_ip_port(ip, port):
    """访问目标地址尝试抓取 m3u 内容"""
    url = f"https://iptv.cqshushu.com/?s={ip}:{port}&t=multicast&channels=1&download=m3u"
    try:
        # 探测间隔，防止被该站封禁 IP
        time.sleep(random.uniform(1.5, 3))
        res = requests.get(url, headers=get_headers(), timeout=TIMEOUT)
        if res.status_code == 200 and "#EXTINF" in res.text:
            return res.text
    except:
        pass
    return None

def extract_page_data(html):
    """
    正则提取：1.IP 2.节目数 3.状态
    """
    # 匹配逻辑：找含有“组播”字样的行，提取前后的 IP、频道数、以及最后的 状态文字
    pattern = re.compile(
        r'<tr>.*?<td>(\d{1,3}(?:\.\d{1,3}){3})</td>.*?<td>(\d+)</td>.*?<td>.*?组播.*?</td>.*?<td>.*?</td>.*?<td>.*?</td>.*?<td>(.*?)</td>.*?</tr>',
        re.S
    )
    return pattern.findall(html)

def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    print(f"🚀 启动抓取任务 | 目标页数: {MAX_PAGES}")
    
    valid_targets = []

    # 1. 翻页爬取 IP 列表
    for page in range(1, MAX_PAGES + 1):
        if page == 1:
            target_url = HOME_URL
        else:
            target_url = PAGE_URL_TEMPLATE.format(page)
        
        print(f"\n📖 正在扫描第 {page} 页: {target_url}")
        try:
            r = requests.get(target_url, headers=get_headers(), timeout=TIMEOUT)
            r.encoding = 'utf-8'
            
            items = extract_page_data(r.text)
            
            for ip, count_str, status in items:
                count = int(count_str)
                # 过滤逻辑：频道数为0 或者 状态包含“暂时失效”
                if count == 0 or "暂时失效" in status:
                    print(f"  🚫 过滤: {ip} (频道:{count}, 状态:{status})")
                    continue
                
                # 去重检查
                if ip not in [t['ip'] for t in valid_targets]:
                    valid_targets.append({'ip': ip, 'count': count})
                    print(f"  ✅ 命中: {ip} (频道:{count}, 状态:{status})")

            # 翻页冷却，避免触发机器人验证
            time.sleep(random.uniform(3, 5))
            
        except Exception as e:
            print(f"  ❌ 访问失败: {e}")

    print(f"\n📊 扫描完成！共获得 {len(valid_targets)} 个高质量组播 IP 待探测")

    # 2. 端口穷举探测
    for idx, target in enumerate(valid_targets, 1):
        ip = target['ip']
        print(f"\n[{idx}/{len(valid_targets)}] 📡 开始探测 IP: {ip}")
        
        success = False
        for port in PRIMARY_MULTICAST_PORTS:
            print(f"  ➜ {port}", end="", flush=True)
            content = scan_ip_port(ip, port)
            
            if content:
                filename = f"multicast_{ip}_{port}.m3u"
                save_path = os.path.join(OUTPUT_DIR, filename)
                with open(save_path, "w", encoding="utf-8") as f:
                    f.write(content)
                print(" -> [✅ 抓取成功]")
                success = True
                break  # 一个 IP 只要有一个端口通了就换下一个 IP
            else:
                print(".", end="", flush=True)
        
        if not success:
            print("\n  ⚠️ 遍历常用端口无果")

    print(f"\n✨ 全部任务已完成。请在 {OUTPUT_DIR} 文件夹中查看结果。")

if __name__ == "__main__":
    main()
