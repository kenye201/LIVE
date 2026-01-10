import os
import re

# ======================
# 配置
# ======================
INPUT_DIR = "test"
OUTPUT_FILE = "test/hotel_all.m3u"
LOGO_BASE_URL = "https://gcore.jsdelivr.net/gh/taksssss/tv/icon"

# ======================
# 工具函数
# ======================

def clean_group_title(line):
    """
    精简分组名称：提取 [地名] + [运营商]
    输入示例: group-title="广西钦州市灵山县酒店 广西联通"
    输出示例: group-title="广西联通"
    """
    match = re.search(r'group-title="(.*?)"', line)
    if match:
        full_title = match.group(1)
        
        # 1. 提取运营商 (电信/联通/移动/广电)
        isp_match = re.search(r'(电信|联通|移动|广电)', full_title)
        isp = isp_match.group(1) if isp_match else ""
        
        # 2. 提取地名 (通常是标题最开始的两个字，如 "河北"、"广西")
        # 逻辑：取空格后的地名，或者取最开头的地名
        if " " in full_title:
            # 针对 "酒店 广西联通" 这种结构，取空格后的部分
            parts = full_title.split()
            # 寻找包含运营商的那一部分
            for part in parts:
                if isp in part:
                    # 去掉其中的“酒店”二字
                    clean_name = part.replace("酒店", "")
                    return line.replace(f'group-title="{full_title}"', f'group-title="{clean_name}"')
        
        # 兜底逻辑：如果没空格，尝试提取前两个字+运营商
        location = full_title[:2]
        return line.replace(f'group-title="{full_title}"', f'group-title="{location}{isp}"')
        
    return line

def clean_channel_name(name):
    """清洗频道名用于匹配台标"""
    n = name.replace("HD", "").replace("高清", "").replace("-综合", "").replace("综合", "")
    n = n.replace("-", "").replace(" ", "").replace("超清", "").replace("中央", "CCTV")
    # 特殊处理 CCTV
    match = re.search(r"(CCTV\d+)", n, re.I)
    if match:
        return match.group(1).upper()
    return n.strip()

def fix_logo_and_id(line):
    """修复台标和 ID"""
    name_match = re.search(r",([^,\n\r]+)$", line)
    if not name_match:
        return line
    
    raw_name = name_match.group(1).strip()
    clean_name = clean_channel_name(raw_name)

    # 修复 Logo 链接
    new_logo = f'tvg-logo="{LOGO_BASE_URL}/{clean_name}.png"'
    if 'tvg-logo="' in line:
        line = re.sub(r'tvg-logo=".*?"', new_logo, line)
    else:
        line = line.replace("#EXTINF:-1", f"#EXTINF:-1 {new_logo}")
    
    # 修复 ID
    new_tvg_id = f'tvg-id="{raw_name}"'
    if 'tvg-id="' in line:
        line = re.sub(r'tvg-id=".*?"', new_tvg_id, line)
    else:
        line = line.replace("#EXTINF:-1", f"#EXTINF:-1 {new_tvg_id}")
    
    return line

# ======================
# 主逻辑
# ======================
def main():
    if not os.path.exists(INPUT_DIR):
        print(f"❌ 文件夹 {INPUT_DIR} 不存在")
        return

    all_entries = {} # { url: inf_line }
    
    # 遍历文件夹下所有 m3u 文件 (排除合并后的总文件)
    files = [f for f in os.listdir(INPUT_DIR) if f.endswith(".m3u") and f != "hotel_all.m3u"]
    print(f"📂 正在合并本地文件: {files}")

    for filename in files:
        filepath = os.path.join(INPUT_DIR, filename)
        with open(filepath, "r", encoding="utf-8") as f:
            lines = f.readlines()
            
            current_inf = ""
            for line in lines:
                line = line.strip()
                if not line or line.startswith("#EXTM3U"):
                    continue
                
                if line.startswith("#EXTINF"):
                    # 1. 修复分组名 (地名+运营商)
                    line = clean_group_title(line)
                    # 2. 修复台标和 ID
                    line = fix_logo_and_id(line)
                    current_inf = line
                elif line.startswith("http"):
                    # 3. 按 URL 去重
                    if line not in all_entries:
                        all_entries[line] = current_inf

    # 写入合成文件
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write('#EXTM3U x-tvg-url="https://fy.188766.xyz/e.xml"\n')
        for url, inf in all_entries.items():
            f.write(f"{inf}\n{url}\n")

    print(f"✨ 处理完成！已生成清爽分组的列表。")
    print(f"💾 输出文件: {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
