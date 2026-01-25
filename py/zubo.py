import requests
import re
import os
import base64
import time
import random

HOME_URL = "https://iptv.cqshushu.com/"
OUTPUT_DIR = "zubo"
TIMEOUT = 12

def get_headers():
    return {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Referer": HOME_URL
    }

def decode_ip(b64_str):
    """解码网页中的 Base64 IP"""
    try:
        return base64.b64decode(b64_str).decode('utf-8')
    except:
        return None

def main():
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)

    print(f"🚀 开始解析加密 IP...")
    try:
        r = requests.get(HOME_URL, headers=get_headers(), timeout=TIMEOUT)
        html_content = r.text
        
        # 1. 使用正则精准匹配 gotoIP 函数里的 Base64 字符串
        # 匹配格式如: gotoIP('MTIzLjEwLjc2LjQx', '...
        encoded_ips = re.findall(r"gotoIP\('([^']+)'", html_content)
        
        # 2. 解码并去重
        all_ips = []
        for b64 in encoded_ips:
            ip = decode_ip(b64)
            if ip and ip not in all_ips:
                all_ips.append(ip)
        
        # 3. 按照你的需求，取最新的（通常是前 12 个，或者后 12 个）
        # 网页结构通常是 6个酒店 + 6个组播，一共 12 个
        target_ips = all_ips[:12] 
        
        print(f"📍 成功提取到 {len(target_ips)} 个有效 IP: {target_ips}")
        
    except Exception as e:
        print(f"❌ 访问或解析失败: {e}")
        return

    # 4. 尝试常用端口并保存
    test_ports = [8001, 8000, 4022, 16888]
    for ip in target_ips:
        success = False
        for port in test_ports:
            # 这里的下载链接逻辑保持你之前的版本
            test_url = f"https://iptv.cqshushu.com/?s={ip}:{port}&t=multicast&channels=1&download=m3u"
            try:
                time.sleep(random.uniform(1, 3)) # 礼貌抓取
                res = requests.get(test_url, headers=get_headers(), timeout=TIMEOUT)
                if "#EXTINF" in res.text:
                    # 提取省份/运营商作为文件名
                    # 匹配示例: 河南省漯河市... 河南联通
                    name_match = re.search(r'data-label="类型:">([^<]+)</td>', html_content)
                    provider = "源"
                    if name_match:
                        info = name_match.group(1)
                        provider = info.split()[-1] if " " in info else "IPTV"

                    filename = f"{provider}-{ip.replace('.', '_')}.m3u"
                    with open(os.path.join(OUTPUT_DIR, filename), "w", encoding="utf-8") as f:
                        f.write(res.text)
                    print(f" ✅ 成功: {filename}")
                    success = True
                    break
            except:
                continue

if __name__ == "__main__":
    main()
