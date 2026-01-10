import os
import re

INPUT_DIR = "test"
OUTPUT_FILE = "test/hotel_all.m3u"
LOGO_BASE_URL = "https://gcore.jsdelivr.net/gh/taksssss/tv/icon"

def clean_group_title(line):
    """
    将 '广西钦州市灵山县酒店 广西联通' 简化为 '广西联通'
    """
    match = re.search(r'group-title="(.*?)"', line)
    if match:
        full_title = match.group(1)
        # 提取运营商 (电信|联通|移动|广电)
        isp_match = re.search(r'(电信|联通|移动|广电)', full_title)
        if isp_match:
            isp = isp_match.group(1)
            # 提取前两个字作为省份/城市
            region = full_title[:2]
            # 组合成：广西联通 / 河北电信
            return re.sub(r'group-title=".*?"', f'group-title="{region}{isp}"', line)
    return line

def fix_line_content(line):
    """清洗频道名并修复台标"""
    if not line.startswith("#EXTINF"): return line
    
    # 提取频道名
    name_match = re.search(r",([^,\n\r]+)$", line)
    if not name_match: return line
    raw_name = name_match.group(1).strip()
    
    # 归一化频道名用于匹配台标
    clean_name = raw_name.replace("HD", "").replace("高清", "").replace("-综合", "").replace("综合", "")
    clean_name = clean_name.replace("-", "").replace(" ", "").replace("中央", "CCTV")
    cctv_match = re.search(r"(CCTV\d+)", clean_name, re.I)
    if cctv_match: clean_name = cctv_match.group(1).upper()

    # 替换或插入属性
    new_logo = f'tvg-logo="{LOGO_BASE_URL}/{clean_name}.png"'
    new_id = f'tvg-id="{raw_name}"'
    
    line = re.sub(r'tvg-logo=".*?"', new_logo, line) if 'tvg-logo="' in line else line.replace("#EXTINF:-1", f"#EXTINF:-1 {new_logo}")
    line = re.sub(r'tvg-id=".*?"', new_id, line) if 'tvg-id="' in line else line.replace("#EXTINF:-1", f"#EXTINF:-1 {new_id}")
    return line

def main():
    all_channels = {} # { url: inf_line }
    files = [f for f in os.listdir(INPUT_DIR) if f.startswith("raw_") and f.endswith(".m3u")]
    
    for filename in files:
        with open(os.path.join(INPUT_DIR, filename), "r", encoding="utf-8") as f:
            current_inf = ""
            for line in f:
                line = line.strip()
                if line.startswith("#EXTINF"):
                    line = clean_group_title(line)
                    current_inf = fix_line_content(line)
                elif line.startswith("http"):
                    if line not in all_channels: # URL去重
                        all_channels[line] = current_inf

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write('#EXTM3U x-tvg-url="https://fy.188766.xyz/e.xml"\n')
        for url, inf in all_channels.items():
            f.write(f"{inf}\n{url}\n")
    print(f"✅ 合并完成，共 {len(all_channels)} 个频道")

if __name__ == "__main__":
    main()
