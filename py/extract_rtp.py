import os
import re

# 配置路径
SOURCE_DIR = "zubo"      # 存放原始 m3u 文件的目录
RTP_TARGET_DIR = "py/rtp" # 生成的 RTP 文本保存目录
LOG_FILE = "py/rtp/mapping_log.txt" # 详细信息记录文件

def extract_and_classify():
    if not os.path.exists(RTP_TARGET_DIR):
        os.makedirs(RTP_TARGET_DIR, exist_ok=True)

    log_entries = []
    
    # 遍历源目录下的所有 m3u 文件
    for filename in os.listdir(SOURCE_DIR):
        if not filename.endswith(".m3u"):
            continue
            
        file_path = os.path.join(SOURCE_DIR, filename)
        print(f"正在处理: {filename}")
        
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # 匹配 EXTINF 及其下一行的 URL
        # 匹配频道名, 组播信息, RTP地址
        # 这里的正则根据你提供的内容进行了优化
        pattern = re.compile(r'#EXTINF:-1.*?group-title="(.*?)",(.*?)\n.*?/rtp/(.*)')
        matches = pattern.findall(content)

        for group_info, channel_name, rtp_addr in matches:
            # 1. 提取文件名（如 "浙江电信"）
            # 假设格式通常是 "具体城市 运营商"，我们取最后两个词
            info_parts = group_info.split()
            isp_name = info_parts[-1] if info_parts else "未知运营商"
            
            # 2. 准备保存的内容 (频道名,rtp://地址)
            rtp_content = f"{channel_name.strip()},rtp://{rtp_addr.strip()}\n"
            
            # 3. 写入对应的 RTP 文件 (例如 浙江电信.txt)
            target_file = os.path.join(RTP_TARGET_DIR, f"{isp_name}.txt")
            with open(target_file, 'a', encoding='utf-8') as tf:
                tf.write(rtp_content)

            # 4. 记录日志 (IP, 详细城市信息, 对应的文件)
            # 从文件名提取 IP
            ip_match = re.search(r'(\d+\.\d+\.\d+\.\d+)', filename)
            ip_addr = ip_match.group(1) if ip_match else "未知IP"
            
            log_entry = f"IP: {ip_addr} | 详细信息: {group_info} | 归类文件: {isp_name}.txt"
            if log_entry not in log_entries:
                log_entries.append(log_entry)

    # 写入日志文件
    with open(LOG_FILE, 'w', encoding='utf-8') as lf:
        lf.write("RTP 提取分类记录汇总\n")
        lf.write("="*50 + "\n")
        for entry in log_entries:
            lf.write(entry + "\n")

    print(f"✅ 处理完成！RTP文件已保存在 {RTP_TARGET_DIR}，日志已更新。")

if __name__ == "__main__":
    extract_and_classify()
