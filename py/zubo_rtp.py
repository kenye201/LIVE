import os
import re

# 配置路径
SOURCE_DIR = "zubo"      # 存放原始 m3u 文件的目录
RTP_TARGET_DIR = "py/rtp" # 生成的 RTP 文本保存目录
LOG_FILE = "py/rtp/mapping_log.txt" 

def get_sort_key(line):
    """
    自定义排序规则：
    返回一个元组 (核心名, 原始全名)
    """
    channel_name = line.split(',')[0]
    # 提取核心名：去掉常见的画质后缀
    core_name = re.sub(r'(HD|SD|4K|8K|高清|标清|超清|超高|频道)$', '', channel_name, flags=re.IGNORECASE)
    # 处理特殊情况，如 CCTV1HD -> CCTV1
    core_name = core_name.strip().upper()
    return (core_name, channel_name.upper())

def extract_and_classify():
    if not os.path.exists(RTP_TARGET_DIR):
        os.makedirs(RTP_TARGET_DIR, exist_ok=True)

    rtp_data_storage = {}
    log_entries = []
    
    if not os.path.exists(SOURCE_DIR):
        print(f"❌ 找不到源目录: {SOURCE_DIR}")
        return

    for filename in os.listdir(SOURCE_DIR):
        if not filename.endswith(".m3u"):
            continue
            
        file_path = os.path.join(SOURCE_DIR, filename)
        print(f"正在读取: {filename}")
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except Exception as e:
            print(f"读取失败 {filename}: {e}")
            continue

        # 匹配频道名, 组播信息, RTP地址
        pattern = re.compile(r'#EXTINF:-1.*?group-title="(.*?)",(.*?)\n.*?/rtp/(.*)')
        matches = pattern.findall(content)

        for group_info, channel_name, rtp_addr in matches:
            # 1. 提取运营商名
            info_parts = group_info.split()
            isp_name = info_parts[-1] if info_parts else "未知运营商"
            
            # 2. 规范化内容
            clean_name = channel_name.strip()
            # 顺便把常见的横杠或空格清理掉，方便去重
            clean_name = clean_name.replace("-", "")
            
            clean_rtp = rtp_addr.strip()
            entry_line = f"{clean_name},rtp://{clean_rtp}"
            
            # 3. 内存去重
            if isp_name not in rtp_data_storage:
                rtp_data_storage[isp_name] = set()
            rtp_data_storage[isp_name].add(entry_line)

            # 4. 日志记录
            ip_match = re.search(r'(\d+\.\d+\.\d+\.\d+)', filename)
            ip_addr = ip_match.group(1) if ip_match else "未知IP"
            log_entry = f"IP: {ip_addr} | 详细信息: {group_info} | 归类文件: {isp_name}.txt"
            if log_entry not in log_entries:
                log_entries.append(log_entry)

    # --- 写入阶段 ---
    print("💾 正在写入并智能排序 RTP 文件...")
    for isp_name, entries in rtp_data_storage.items():
        target_file = os.path.join(RTP_TARGET_DIR, f"{isp_name}.txt")
        
        # --- 核心改进：使用自定义 Key 排序 ---
        # 结果会是：CETV1, CETV1HD, CETV1SD, CETV2...
        sorted_entries = sorted(list(entries), key=get_sort_key)
        
        with open(target_file, 'w', encoding='utf-8') as tf:
            for line in sorted_entries:
                tf.write(line + "\n")

    with open(LOG_FILE, 'w', encoding='utf-8') as lf:
        lf.write("RTP 提取分类记录汇总 (已去重且聚类排序)\n")
        lf.write("="*50 + "\n")
        for entry in sorted(log_entries):
            lf.write(entry + "\n")

    print(f"✅ 处理完成！同类频道已排列在一起。")

if __name__ == "__main__":
    extract_and_classify()
