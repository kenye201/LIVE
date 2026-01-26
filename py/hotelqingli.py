import os
import re
import requests
import concurrent.futures

# ===============================
# 配置区
# ===============================
M3U_DIR = "hotel"
HISTORY_FILE = os.path.join(M3U_DIR, "hotel_history.txt")
SAMPLE_COUNT = 3               # 抽测 3 个链接即可，提高效率
CHECK_TIMEOUT = 10
HEADERS = {"User-Agent": "Mozilla/5.0"}

def check_link(url):
    """检测单个直播源链接"""
    try:
        # 优先使用 GET 请求读取极小字节，比 HEAD 更准确（很多直播源屏蔽 HEAD）
        response = requests.get(url, headers=HEADERS, timeout=CHECK_TIMEOUT, stream=True)
        return response.status_code == 200
    except:
        return False

def is_m3u_alive(file_path):
    """判断 m3u 文件是否还有效"""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
        links = re.findall(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', content)
        if not links: return False
        
        test_links = links[:SAMPLE_COUNT]
        with concurrent.futures.ThreadPoolExecutor(max_workers=SAMPLE_COUNT) as executor:
            results = list(executor.map(check_link, test_links))
        return any(results)
    except:
        return False

def main():
    if not os.path.exists(M3U_DIR): return

    print(f"🔍 开始清理失效文件...")
    files = [f for f in os.listdir(M3U_DIR) if f.endswith(".m3u")]
    
    removed_ips = []
    removed_count = 0

    for filename in files:
        file_path = os.path.join(M3U_DIR, filename)
        if not is_m3u_alive(file_path):
            # 提取 IP 用于后续清理黑名单 (假设文件名格式为: 运营商_1_2_3_4_端口.m3u)
            parts = filename.split('_')
            if len(parts) >= 5:
                ip = ".".join(parts[-5:-1]) # 提取 1_2_3_4 还原为 1.2.3.4
                removed_ips.append(ip)
            
            os.remove(file_path)
            print(f"  ❌ 已删除: {filename}")
            removed_count += 1
        else:
            print(f"  ✅ 有效: {filename}")

    # --- 同步清理黑名单 ---
    if removed_ips and os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            lines = f.readlines()
        with open(HISTORY_FILE, "w", encoding="utf-8") as f:
            for line in lines:
                if not any(ip in line for ip in removed_ips):
                    f.write(line)
        print(f"♻️  同步清理黑名单记录: {len(removed_ips)} 条")

    print(f"✨ 清理完成！共删除 {removed_count} 个失效文件。")

if __name__ == "__main__":
    main()
