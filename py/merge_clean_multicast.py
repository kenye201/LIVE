import os
import re

INPUT_DIR = "test_multicast"                  # 你的组播小文件目录
OUTPUT_FILE = "test_multicast/all_multicast.m3u"  # 输出大文件路径
LOGO_BASE_URL = "https://gcore.jsdelivr.net/gh/taksssss/tv/icon"

def clean_group_title(line):
    """提取 [地名][运营商]，例如: 北京联通"""
    match = re.search(r'group-title="(.*?)"', line)
    if match:
        full = match.group(1)
        isp_match = re.search(r'(电信|联通|移动|广电)', full)
        if isp_match:
            isp = isp_match.group(1)
            # 取运营商前面的部分（假设前两个字是地名或关键地区）
            prefix = full[:full.find(isp)].strip()
            # 只保留最后一个词作为地名（去掉多余的省市区）
            parts = prefix.split()
            simple_prefix = parts[-1] if parts else ""
            return re.sub(r'group-title=".*?"', f'group-title="{simple_prefix}{isp}"', line)
    return line

def fix_content(line):
    """修复台标、ID，并清洗频道显示名称"""
    if not line.startswith("#EXTINF"): return line
    name_match = re.search(r",([^,\n\r]+)$", line)
    if not name_match: return line
    
    raw_name = name_match.group(1).strip()
    
    # 清洗显示名称（去掉末尾的 HD、高清、超清、SD 等）
    display_name = re.sub(r'([-_\s]?(HD|高清|超清|SD))$', '', raw_name, flags=re.I).strip()
    # 将清洗后的名字应用回 line 的末尾
    line = line.replace(f",{raw_name}", f",{display_name}")
    
    # 归一化频道名用于匹配台标
    clean = display_name.replace("-综合","").replace("综合","").replace(" ","").replace("中央","CCTV")
    cctv = re.search(r"(CCTV\d+)", clean, re.I)
    if cctv: clean = cctv.group(1).upper()
    
    logo = f'tvg-logo="{LOGO_BASE_URL}/{clean}.png"'
    tid = f'tvg-id="{display_name}"'
    
    line = re.sub(r'tvg-logo=".*?"', logo, line) if 'tvg-logo="' in line else line.replace("#EXTINF:-1", f"#EXTINF:-1 {logo}")
    line = re.sub(r'tvg-id=".*?"', tid, line) if 'tvg-id="' in line else line.replace("#EXTINF:-1", f"#EXTINF:-1 {tid}")
    
    return line

def main():
    all_channels = {}  # 使用字典按 URL 去重
    
    if not os.path.exists(INPUT_DIR):
        print(f"❌ 目录 {INPUT_DIR} 不存在")
        return
    
    files = [f for f in os.listdir(INPUT_DIR) if f.startswith("multicast_raw_") and f.endswith(".m3u")]
    print(f"🔄 正在融合 {len(files)} 个文件...")
    
    for filename in files:
        with open(os.path.join(INPUT_DIR, filename), "r", encoding="utf-8") as f:
            current_inf = ""
            for line in f:
                line = line.strip()
                if line.startswith("#EXTINF"):
                    line = clean_group_title(line)
                    current_inf = fix_content(line)
                elif line.startswith("http"):
                    # 按 URL 去重，保留先发现的
                    if line not in all_channels:
                        all_channels[line] = current_inf
    
    # 写入最终合集（保留原始头部风格）
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write('#EXTM3U x-tvg-url="https://fy.188766.xyz/e.xml" tvg-shift="0"\n')
        for url, inf in all_channels.items():
            f.write(f"{inf}\n{url}\n")
    
    print(f"✨ 融合完成！总计唯一频道数: {len(all_channels)}")
    print(f"输出文件: {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
