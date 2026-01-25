import requests
import re
import os

# 配置
# 注意：这里使用 raw.githubusercontent.com 才能获取纯文本内容
RAW_URL = "https://raw.githubusercontent.com/kenye201/LIVE/main/py/iptv_shushu.html"
SAVE_PATH = "/volume1/docker/iptv_backup/my_channels.txt" # 提取后的存放路径

def extract_ips_from_github():
    try:
        print(f"正在从 GitHub 获取源码: {RAW_URL}")
        response = requests.get(RAW_URL, timeout=30)
        response.encoding = 'utf-8'
        
        if response.status_code != 200:
            print(f"获取失败，HTTP 状态码: {response.status_code}")
            return

        html_content = response.text

        # 使用正则提取 IP 链接和频道名
        # 假设 HTML 中的格式通常是: 频道名,http://ip:port/xxx
        # 下面是一个通用的正则匹配模式，根据你上传的 HTML 内容可能需要微调
        # 匹配 pattern: 频道名 + 链接
        pattern = r'([^,\n]+),(http[s]?://[\d\.]+:\d+/[^\s\n]+)'
        matches = re.findall(pattern, html_content)

        if not matches:
            print("未能在 HTML 中匹配到有效的频道信息，请检查正则或 HTML 结构。")
            # 打印前100个字符调试
            print("HTML 预览:", html_content[:100])
            return

        # 格式化并保存
        results = []
        for name, url in matches:
            results.append(f"{name.strip()},{url.strip()}")

        with open(SAVE_PATH, "w", encoding="utf-8") as f:
            f.write("\n".join(results))
        
        print(f"成功！已提取 {len(results)} 个频道并保存至: {SAVE_PATH}")

    except Exception as e:
        print(f"发生错误: {e}")

if __name__ == "__main__":
    extract_ips_from_github()
