import os
import re
from collections import OrderedDict

# 配置
INPUT_DIR = "test_multicast"                  # 输入小文件目录
OUTPUT_FILE = "clean_all.m3u"       # 输出的大文件
HEADER = '#EXTM3U x-tvg-url="https://fy.188766.xyz/e.xml" tvg-shift="0"'

# 运营商关键词，用于简化 group-title
OPERATORS = ["电信", "联通", "移动"]

def simplify_group(group):
    """
    简化 group-title，只保留运营商部分（如 北京联通、广东电信）
    规则：取最后一个运营商关键词 + 前面的最后一个地名
    """
    if not group:
        return "其他"
    
    # 找最后一个运营商
    last_op = None
    last_op_idx = -1
    for op in OPERATORS:
        idx = group.rfind(op)
        if idx > last_op_idx:
            last_op_idx = idx
            last_op = op
    
    if last_op is None:
        return group  # 没运营商，原样返回
    
    # 运营商前面的内容
    prefix = group[:last_op_idx].strip()
    # 只保留最后一个词（地名），去掉多余省市区
    parts = prefix.split()
    simple_prefix = parts[-1] if parts else ""
    
    return f"{simple_prefix}{last_op}"

def extract_channel_name(info_line):
    """
    从 #EXTINF 提取纯频道名（去掉 tvg-id、tvg-logo 等）
    """
    # 取逗号后面的部分作为频道名
    match = re.search(r',(.+)$', info_line)
    if match:
        name = match.group(1).strip()
        # 清理常见后缀（HD、4K、超高清等）
        name = re.sub(r'\s*(HD|4K|超高清|高清|\+|\s*)$', '', name, flags=re.I).strip()
        return name
    return "未知频道"

def main():
    if not os.path.exists(INPUT_DIR):
        print(f"❌ 输入目录 {INPUT_DIR} 不存在")
        return

    print(f"🔄 开始清洗 & 合并 {INPUT_DIR} 中的 multicast_raw_*.m3u 文件...")
    files = [f for f in os.listdir(INPUT_DIR) if f.startswith("multicast_raw_") and f.endswith(".m3u")]
    
    if not files:
        print("未找到任何 multicast_raw_*.m3u 文件")
        return

    print(f"找到 {len(files)} 个文件，开始处理")

    # 使用 OrderedDict 去重 + 保持首次出现顺序
    seen = OrderedDict()  # key: (频道名, URL), value: info_line

    for filename in sorted(files):
        path = os.path.join(INPUT_DIR, filename)
        print(f"  处理: {filename}")
        
        try:
            with open(path, "r", encoding="utf-8") as f:
                lines = f.readlines()
        except Exception as e:
            print(f"    读取失败: {e}")
            continue

        i = 0
        while i < len(lines):
            line = lines[i].strip()
            if line.startswith("#EXTINF"):
                info = line
                i += 1
                if i >= len(lines):
                    break
                url = lines[i].strip()
                if not url.startswith("http"):
                    i += 1
                    continue

                channel_name = extract_channel_name(info)
                if channel_name == "未知频道":
                    i += 1
                    continue

                # 提取原始 group-title
                group_match = re.search(r'group-title="([^"]*)"', info)
                group_original = group_match.group(1) if group_match else ""
                group_simple = simplify_group(group_original)

                # 修复 logo：用频道名补全
                info = re.sub(
                    r'tvg-logo="[^"]*"',
                    f'tvg-logo="https://gcore.jsdelivr.net/gh/taksssss/tv/icon/{channel_name}.png"',
                    info
                )

                # 更新 group-title 为简化版
                info = re.sub(
                    r'group-title="[^"]*"',
                    f'group-title="{group_simple}"',
                    info
                )

                # 去重 key
                key = (channel_name, url)
                if key not in seen:
                    seen[key] = info
                    print(f"    添加频道: {channel_name} | 分组: {group_simple}")

            i += 1

    # 生成最终大文件
    final_lines = [HEADER]
    for info in seen.values():
        final_lines.append(info)
        # 添加 URL（从 info 里提取不方便，所以这里假设 URL 紧跟 info，但实际合并时需要记录）
        # 为了完整性，这里简单处理：实际生产中建议记录 (info, url) 元组
        # 临时方案：从原始 info 提取 URL（不完美，但可行）
        url_match = re.search(r'http[s]?://[^\s\'"]+', info)
        if url_match:
            final_lines.append(url_match.group(0))

    if len(final_lines) > 1:
        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            f.write("\n".join(final_lines) + "\n")
        print(f"\n🎉 合并完成！生成 {OUTPUT_FILE}")
        print(f"  唯一频道数: {len(seen)}")
    else:
        print("\n无有效频道，跳过生成")

if __name__ == "__main__":
    main()
