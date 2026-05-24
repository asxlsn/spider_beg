import time
import json
import hashlib
import random
import os
import hmac as hmac_mod
import requests
from urllib.parse import quote_plus
import base64


headers = {
    "accept": "application/json",
    "accept-language": "zh-CN,zh;q=0.9",
    "content-type": "application/x-www-form-urlencoded",
    "origin": "https://www.goofish.com",
    "priority": "u=1, i",
    "referer": "https://www.goofish.com/",
    "sec-ch-ua": "\"Chromium\";v=\"148\", \"Google Chrome\";v=\"148\", \"Not/A)Brand\";v=\"99\"",
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": "\"Windows\"",
    "sec-fetch-dest": "empty",
    "sec-fetch-mode": "cors",
    "sec-fetch-site": "same-site",
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36"
}

app_key = "34839810"

cookies = {
    "t": "240ef3743639ad6bc74b0a06b6be5401",
    "cna": "57lrIozHKE8BASQIglaSwrSS",
    "xlly_s": "1",
    "cookie2": "1167fa9989526a8057d3d671ec868a8d",
    "mtop_partitioned_detect": "1",
    "_m_h5_tk": "0242a4da38bbb6c18d6c038ba537022f_1779603267192",
    "_m_h5_tk_enc": "59141f25fccf170aad48b8a490d1e56e",
    "_samesite_flag_": "true",
    "_tb_token_": "eb67453f3ee83",
    "sdkSilent": "1779681748951",
    "tracknick": "xy342894735481",
    "unb": "2219105959387",
    "sgcookie": "E100JxBVbb2wMJ%2BceGIBUaEYOJnKSnjMghIrr3FJyYCq%2FS1N1LGO5x2tbxMd60uVYN7CA2cJHRm0eswAbBPBLvPWDtC1PgnZ7WkorC6rdg4CRfGFzOxDxkghxf5Fy4pbZX7e",
    "csg": "7aa65c53",
    "havana_lgc2_77": "eyJoaWQiOjIyMTkxMDU5NTkzODcsInNnIjoiMGNkNTk5M2IzMDc0MjAwMjMyNWRjMzhmYzMxZGNiNTkiLCJzaXRlIjo3NywidG9rZW4iOiIxX2xQVE43Q0pnLTB6R0hWYXd3NmExUSJ9",
    "_hvn_lgc_": "77",
    "havana_lgc_exp": "1782187392260",
    "tfstk": "gkwIKJ2l2eYCOssdyeSwcLAskYD50GW2F3i8mupe2vHpyUEx7yuELgXSyy0aL2rEpHVguopUL6DyFvDoeZ7V3trUxYDR6Dg4YHDtmmndUX3KBvmrq7Exutr3xhKByiPO3_GUxa9-yzhK6FnEWD3JeLIs6mo-ephJpCLtS0H-eb3-XCnr2LpppLI_XVm-eQpLyAIs4V3-eYU8Xjq15cfIJksl9G-ZALQ_YV9JeRiOrqEBxKn3BDTrukg1kp21IXgYvV9RRNSbV4ggHN5_jPPL8c45hNMTD5MKAzBvgVF_XJcqhsdQklz3hvefRpoZN2NTpftJelHi8bP7RwOnJWzsich9VtmauVE3p5skWkUqRvnt_tIbXbFaKj2FWpMYikkUwPB6drIrnKujx8AWfjvSfqS1fQAu6FlAWmR-WWlKjcyVfGTBZXnifqS1fQAo9cmZgGs6RQf.."
}


def get_sign(token, timestamp, app_key, data):
    """生成 mtop 签名：md5(token&timestamp&appKey&data)"""
    sign_str = f"{token}&{timestamp}&{app_key}&{data}"
    return hashlib.md5(sign_str.encode('utf-8')).hexdigest()


def fetch_feed(page_number=1, page_size=30):
    """获取闲鱼首页推荐 feed"""
    # 从 cookie 中提取 token
    m_h5_tk = cookies["_m_h5_tk"]
    token = m_h5_tk.split("_")[0]
    timestamp = str(int(time.time() * 1000))

    # 构造请求体
    data_obj = {
        "itemId": "",
        "pageSize": page_size,
        "pageNumber": page_number,
        "machId": ""
    }
    data_str = json.dumps(data_obj, separators=(',', ':'))

    # 生成签名
    sign = get_sign(token, timestamp, app_key, data_str)

    params = {
        "jsv": "2.7.2",
        "appKey": app_key,
        "t": timestamp,
        "sign": sign,
        "v": "1.0",
        "type": "originaljson",
        "accountSite": "xianyu",
        "dataType": "json",
        "timeout": "20000",
        "api": "mtop.taobao.idlehome.home.webpc.feed",
        "sessionOption": "AutoLoginOnly",
        "spm_cnt": "a21ybx.home.0.0"
    }

    post_data = {"data": data_str}

    resp = requests.post(
        url="https://h5api.m.goofish.com/h5/mtop.taobao.idlehome.home.webpc.feed/1.0/",
        headers=headers,
        cookies=cookies,
        params=params,
        data=post_data
    )
    return resp.json()


def extract_items(response_data):
    """从响应中提取关键商品信息"""
    items = []
    card_list = response_data.get("data", {}).get("cardList", [])

    for card in card_list:
        card_data = card.get("cardData", {})
        if not card_data:
            continue

        detail = card_data.get("detailParams", {})
        price_info = card_data.get("priceInfo", {})
        user_info = card_data.get("user", {})
        hot_point = card_data.get("hotPoint", {})

        item = {
            "itemId": card_data.get("itemId", ""),
            "title": detail.get("title", "") or card_data.get("titleSummary", {}).get("text", ""),
            "price": price_info.get("price", ""),
            "city": card_data.get("city", ""),
            "seller": user_info.get("userNick", ""),
            "wantCount": hot_point.get("text", ""),
        }
        items.append(item)

    return items


def load_seen_ids(filepath="xy_seen_ids.json"):
    if os.path.exists(filepath):
        with open(filepath, "r") as f:
            return set(json.load(f))
    return set()


def save_seen_ids(seen_ids, filepath="xy_seen_ids.json"):
    with open(filepath, "w") as f:
        json.dump(list(seen_ids), f)


def send_dingtalk(webhook_url, secret, title, content):
    """发送钉钉机器人通知（带加签）"""
    timestamp = str(round(time.time() * 1000))
    string_to_sign = f"{timestamp}\n{secret}"
    hmac_code = hmac_mod.new(secret.encode('utf-8'), string_to_sign.encode('utf-8'), digestmod=hashlib.sha256).digest()
    sign = quote_plus(base64.b64encode(hmac_code))
    url = f"{webhook_url}&timestamp={timestamp}&sign={sign}"

    data = {
        "msgtype": "markdown",
        "markdown": {"title": title, "text": content}
    }
    resp = requests.post(url, json=data)
    print(f"  钉钉响应: {resp.text}")


if __name__ == "__main__":
    dingtalk_webhook = os.environ.get("DINGTALK_WEBHOOK", "")
    dingtalk_secret = os.environ.get("DINGTALK_SECRET", "")

    all_items = []
    total_pages = 3

    for page in range(1, total_pages + 1):
        print(f"正在获取第 {page} 页...")
        resp_data = fetch_feed(page_number=page)

        ret = resp_data.get("ret", [])
        if not any("SUCCESS" in r for r in ret):
            print(f"  请求失败: {ret}")
            break

        items = extract_items(resp_data)
        print(f"  获取到 {len(items)} 条商品")
        all_items.extend(items)

        if not resp_data.get("data", {}).get("nextPage", False):
            print("  没有更多数据了")
            break

        # 随机延迟3-7秒
        delay = random.uniform(3, 7)
        print(f"  等待 {delay:.1f} 秒...")
        time.sleep(delay)

    print(f"共获取 {len(all_items)} 条商品")

    # 过滤新商品
    seen_ids = load_seen_ids()
    new_items = [item for item in all_items if item["itemId"] not in seen_ids]
    print(f"其中新商品 {len(new_items)} 条")

    if new_items and dingtalk_webhook and dingtalk_secret:
        # 钉钉单条消息有长度限制，每10条发一次
        for i in range(0, len(new_items), 10):
            batch = new_items[i:i+10]
            lines = [f"## 闲鱼新商品通知 ({len(batch)}条)\n"]
            for item in batch:
                lines.append(f"**{item['title'][:40]}**\n")
                lines.append(f"- 价格: {item['price']}元 | 城市: {item['city']}")
                lines.append(f"- 卖家: {item['seller']} | {item['wantCount']}\n")
            send_dingtalk(dingtalk_webhook, dingtalk_secret, "闲鱼新商品通知", "\n".join(lines))
            if i + 10 < len(new_items):
                time.sleep(1)
        print(f"已推送 {len(new_items)} 条新商品到钉钉")
    elif new_items:
        print("未配置钉钉，仅打印新商品：")
        for item in new_items:
            title = item['title'][:40].encode('gbk', errors='replace').decode('gbk', errors='replace')
            print(f"  {title} | {item['price']}元 | {item['city']}")
    else:
        print("没有新商品")

    # 更新已见ID
    for item in all_items:
        seen_ids.add(item["itemId"])
    save_seen_ids(seen_ids)
