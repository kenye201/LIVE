import os
import re
import requests
import concurrent.futures

# ===============================
# 配置区
# ===============================
ZUBO_DIR = "zubo"              # 目标文件夹
SAMPLE_COUNT = 2               # 每个文件抽测 2 个频道，只要有 1 个通就行
CHECK_TIMEOUT = 8              # 探测连接超时（秒）
STREAM_READ_TIMEOUT = 5        # 读取流数据的等待时间（秒）
HEADERS = {"User-Agent": "Mozilla/5.0"}

def check_zubo_stream(url):
    """
    双重检测：
    1. 连通性检测 (Connection)
    2. 推流检测 (Stream Data)
    """
    try:
        # 使用 stream=True 尝试打开流
        response = requests.get(url, headers=HEADERS, timeout=CHECK_TIMEOUT, stream=True)
        
        if response.status_code == 200:
            # 尝试读取前 1024 字节的数据，如果 5 秒内读不到，说明无推流
            # iter_content 会触发实际的数据传输
            for chunk in response.iter_content(chunk_size=1024):
                if chunk:
                    return True # 成功读到数据，判定有效
                break 
        return False
    except:
        return False
    finally:
        try: response.close()
        except: pass

def is_zubo_file_alive(file_path):
    """判断组播 m3u 文件是否有效"""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
        
        # 提取 http 链接
        links = re.findall(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', content)
        if not links: return False
        
        # 抽取前几个链接进行测试
        test_links = links[:SAMPLE_COUNT]
        
        # 使用并发提升速度
        with concurrent.futures.ThreadPoolExecutor(max_workers=SAMPLE_COUNT) as executor:
            results = list(executor.map(check_zubo_stream, test_links))
        
        return any(results)
    except Exception as e:
        print(f"  ⚠️ 读取失败 {file_path}: {e}")
        return False

def main():
    if not os.path.exists(ZUBO_DIR):
        print(f"❌ 目录 {ZUBO_DIR} 不存在")
        return

    print(f"🔍 开始清理失效组播源 (目录: {ZUBO_DIR})...")
    files = [f for f in os.listdir(ZUBO_DIR) if f.endswith(".m3u")]
    
    removed_count = 0
    for filename in files:
        file_path = os.path.join(ZUBO_DIR, filename)
        print(f"📡 正在检测流状态: {filename} ... ", end="", flush=True)
        
        if not is_zubo_file_alive(file_path):
            print("❌ 无推流/服务器失效 (已删除)")
            os.remove(file_path)
            removed_count += 1
        else:
            print("✅ 正常")

    print(f"\n✨ zubo 文件夹清理完成！共删除 {removed_count} 个失效文件。")

if __name__ == "__main__":
    main()
