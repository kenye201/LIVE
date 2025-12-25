import requests
import random
import time
import os
import sys

# ============ 配置从环境变量读取（GitHub Secrets） ============
SUBDOMAIN_PREFIX = os.getenv("SUBDOMAIN_PREFIX", "hao")
TTL = int(os.getenv("TTL", "120"))
PROXIED = os.getenv("PROXIED", "false").lower() == "true"
RECORDS_PER_DOMAIN = int(os.getenv("RECORDS_PER_DOMAIN", "4"))
IP_URL = os.getenv("https://565a.bou.qzz.io/ip.txt")  # 必须设置，例如 https://565a.bou.qzz.io/ip.txt

# Cloudflare 账号配置（JSON 格式，从 Secrets 读取）
CF_ACCOUNTS_JSON = os.getenv("CF_ACCOUNTS")
if not CF_ACCOUNTS_JSON:
    print("❌ 错误：未设置 CF_ACCOUNTS 环境变量")
    sys.exit(1)

try:
    import json
    CF_ACCOUNTS = json.loads(CF_ACCOUNTS_JSON)
except json.JSONDecodeError as e:
    print(f"❌ CF_ACCOUNTS JSON 格式错误: {e}")
    sys.exit(1)

if not IP_URL:
    print("❌ 错误：未设置 IP_URL 环境变量")
    sys.exit(1)

# ============ 函数定义（保持原有逻辑） ============
def get_random_ips_from_url(ip_url, count):
    try:
        r = requests.get(ip_url, timeout=10)
        r.raise_for_status()
        ips = [line.strip() for line in r.text.splitlines() if line.strip()]
        if len(ips) < count:
            raise Exception(f"IP数量不足，需要 {count} 条，只有 {len(ips)} 条")
        return random.sample(ips, count)
    except Exception as e:
        raise Exception(f"获取 IP 列表失败: {e}")

def get_zone_id(domain, token):
    url = f"https://api.cloudflare.com/client/v4/zones?name={domain}"
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    r = requests.get(url, headers=headers, timeout=10)
    r.raise_for_status()
    data = r.json()
    if data["success"] and data["result"]:
        return data["result"][0]["id"]
    raise Exception(f"获取 {domain} 的 Zone ID 失败: {data.get('errors')}")

def get_existing_a_records(zone_id, subdomain, token):
    url = f"https://api.cloudflare.com/client/v4/zones/{zone_id}/dns_records?type=A&name={subdomain}"
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    r = requests.get(url, headers=headers, timeout=10)
    r.raise_for_status()
    return r.json().get("result", [])

def delete_record(zone_id, record_id, token):
    url = f"https://api.cloudflare.com/client/v4/zones/{zone_id}/dns_records/{record_id}"
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    r = requests.delete(url, headers=headers, timeout=10)
    r.raise_for_status()
    data = r.json()
    if data["success"]:
        print(f"✅ 删除记录成功: {record_id}")
    else:
        print(f"❌ 删除失败: {record_id}")

def add_a_record(zone_id, subdomain, ip, token):
    url = f"https://api.cloudflare.com/client/v4/zones/{zone_id}/dns_records"
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    payload = {
        "type": "A",
        "name": subdomain,
        "content": ip,
        "ttl": TTL,
        "proxied": PROXIED
    }
    r = requests.post(url, headers=headers, json=payload, timeout=10)
    r.raise_for_status()
    data = r.json()
    if data["success"]:
        print(f"✅ 添加成功: {subdomain} -> {ip}")
    else:
        print(f"❌ 添加失败: {subdomain} -> {ip}, 错误: {data.get('errors')}")

# ============ 主函数 ============
def main():
    print(f"开始执行 DNS 更新任务 - {time.strftime('%Y-%m-%d %H:%M:%S')}")

    try:
        ips_to_add_all = get_random_ips_from_url(IP_URL, RECORDS_PER_DOMAIN * len([d for a in CF_ACCOUNTS for d in a["domains"]]))
        ip_index = 0
    except Exception as e:
        print(f"❌ 获取 IP 列表失败: {e}")
        sys.exit(1)

    for account in CF_ACCOUNTS:
        token = account["token"]
        for domain in account["domains"]:
            subdomain = f"{SUBDOMAIN_PREFIX}.{domain}"
            print(f"\n处理域名: {subdomain}")

            try:
                zone_id = get_zone_id(domain, token)
            except Exception as e:
                print(f"❌ {e}")
                continue

            # 删除旧记录
            existing = get_existing_a_records(zone_id, subdomain, token)
            for rec in existing:
                delete_record(zone_id, rec["id"], token)
                time.sleep(0.2)

            # 添加新记录（从全局随机 IP 池取，避免重复）
            for _ in range(RECORDS_PER_DOMAIN):
                if ip_index >= len(ips_to_add_all):
                    print("警告：IP 不足，跳过剩余记录")
                    break
                ip = ips_to_add_all[ip_index]
                ip_index += 1
                try:
                    add_a_record(zone_id, subdomain, ip, token)
                    time.sleep(0.2)
                except Exception as e:
                    print(f"❌ 添加失败 {subdomain} -> {ip}: {e}")

    print(f"\n所有任务完成 - {time.strftime('%Y-%m-%d %H:%M:%S')}")

if __name__ == "__main__":
    main()
