import os
import re
import requests
import concurrent.futures
import random   # ← 这里添加了！必须导入

# ===============================
# 配置区（针对你的组播目录）
# ===============================
M3U_DIR = "zubo"         # 你的组播输出目录
SAMPLE_COUNT = 3                   # 每个文件只抽测 3 个链接（节约资源）
CHECK_TIMEOUT = 15                  # 超时时间（组播延迟高，8秒足够）

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

def check_link(url):
    try:
        # 先 HEAD（最快）
        response = requests.head(url, headers=HEADERS, timeout=CHECK_TIMEOUT, allow_redirects=True)
        if response.status_code == 200:
            return True
        
        # HEAD 不行再 GET（只读一点点）
        response = requests.get(url, headers=HEADERS, timeout=CHECK_TIMEOUT, stream=True)
        response.raw.read(1024)  # 读 1KB 就停
        return response.status_code == 200
    except:
        return False

def is_m3u_alive(file_path):
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
        
        if not content.strip() or "#EXTM3U" not in content:
            print(f"  文件为空或非标准 m3u，判失效")
            return False
        
        # 提取所有 http(s) 链接
        links = re.findall(r'https?://[^\s\'"]+', content)
        if not links:
            print("  无任何链接，判失效")
            return False
        
        # 随机打乱 + 抽样（防止总是测前几个失效的）
        random.shuffle(links)
        test_links = links[:SAMPLE_COUNT]
        
        print(f"  测试 {len(test_links)} 个链接... ", end="", flush=True)
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=SAMPLE_COUNT) as executor:
            results = list(executor.map(check_link, test_links))
        
        alive = any(results)
        print("通过" if alive else "全部失效")
        return alive
    
    except Exception as e:
        print(f"  处理出错: {e} → 判失效")
        return False

def main():
    if not os.path.exists(M3U_DIR):
        print(f"❌ 目录 {M3U_DIR} 不存在")
        return
    
    print(f"🔍 开始清理失效的 M3U 文件 (目录: {M3U_DIR})...")
    print("-" * 60)
    
    files = [f for f in os.listdir(M3U_DIR) if f.lower().endswith(".m3u")]
    files.sort()  # 按文件名排序，便于查看
    
    removed_count = 0
    kept_count = 0
    
    for filename in files:
        file_path = os.path.join(M3U_DIR, filename)
        print(f"📄 {filename} ... ", end="", flush=True)
        
        if is_m3u_alive(file_path):
            print("✅ 保留")
            kept_count += 1
        else:
            print("❌ 删除")
            os.remove(file_path)
            removed_count += 1
    
    print("-" * 60)
    print(f"\n✨ 清理完成！")
    print(f"  总文件数: {len(files)}")
    print(f"  保留有效: {kept_count}")
    print(f"  删除失效: {removed_count}")
    print(f"  当前剩余文件: {len(os.listdir(M3U_DIR)) if os.path.exists(M3U_DIR) else 0}")

if __name__ == "__main__":
    main()
