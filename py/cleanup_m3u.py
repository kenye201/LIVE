import os
import re
import requests
import concurrent.futures

# ===============================
# 配置区
# ===============================
M3U_DIR = "hotel"              # m3u 文件存放目录
SAMPLE_COUNT = 5              # 每个文件抽测多少个频道
CHECK_TIMEOUT = 10            # 每个链接的探测超时时间
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}

def check_link(url):
    """检测单个直播源链接是否有效"""
    try:
        # 使用 HEAD 请求只检查响应头，速度比 GET 快
        response = requests.head(url, headers=HEADERS, timeout=CHECK_TIMEOUT, allow_redirects=True)
        if response.status_code == 200:
            return True
        # 如果 HEAD 不被允许，尝试 GET 请求（只读少量字节）
        response = requests.get(url, headers=HEADERS, timeout=CHECK_TIMEOUT, stream=True)
        return response.status_code == 200
    except:
        return False

def is_m3u_alive(file_path):
    """判断一个 m3u 文件是否还有效"""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
        
        # 提取所有 http 链接
        links = re.findall(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', content)
        
        if not links:
            return False
        
        # 抽取前 SAMPLE_COUNT 个链接进行测试（或者从中间抽）
        test_links = links[:SAMPLE_COUNT]
        
        # 使用并发探测
        with concurrent.futures.ThreadPoolExecutor(max_workers=SAMPLE_COUNT) as executor:
            results = list(executor.map(check_link, test_links))
        
        # 只要有一个链接通了，就认为这个 IP 文件还有效
        return any(results)
    except Exception as e:
        print(f"⚠️ 处理文件 {file_path} 出错: {e}")
        return False

def main():
    if not os.path.exists(M3U_DIR):
        print(f"❌ 目录 {M3U_DIR} 不存在")
        return

    print(f"🔍 开始清理失效的 M3U 文件 (目录: {M3U_DIR})...")
    files = [f for f in os.listdir(M3U_DIR) if f.endswith(".m3u")]
    
    removed_count = 0
    for filename in files:
        file_path = os.path.join(M3U_DIR, filename)
        print(f"📡 正在检测: {filename} ... ", end="", flush=True)
        
        if not is_m3u_alive(file_path):
            print("❌ 失效 (已删除)")
            os.remove(file_path)
            removed_count += 1
        else:
            print("✅ 有效")

    print(f"\n✨ 清理完成！共删除 {removed_count} 个失效文件。")

if __name__ == "__main__":
    main()
