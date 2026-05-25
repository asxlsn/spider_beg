import time
import json
import hashlib
import random
import os
import hmac as hmac_mod
import requests
from curl_cffi import requests as curl_requests
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


def parse_cookie_str(cookie_str):
    """将 cookie 字符串解析为 dict"""
    cookies = {}
    for pair in cookie_str.split(";"):
        if "=" in pair:
            k, v = pair.strip().split("=", 1)
            cookies[k] = v
    return cookies


def get_sign(token, timestamp, app_key, data):
    """生成 mtop 签名：md5(token&timestamp&appKey&data)"""
    sign_str = f"{token}&{timestamp}&{app_key}&{data}"
    return hashlib.md5(sign_str.encode('utf-8')).hexdigest()


def build_feed_request(cookies, page_number=1, page_size=30):
    """构造 feed 请求参数，返回 (params, post_data)"""
    token = ""
    if "_m_h5_tk" in cookies:
        token = cookies["_m_h5_tk"].split("_")[0]

    timestamp = str(int(time.time() * 1000))

    data_obj = {
        "itemId": "",
        "pageSize": page_size,
        "pageNumber": page_number,
        "machId": ""
    }
    data_str = json.dumps(data_obj, separators=(',', ':'))

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
    return params, post_data


def update_cookies_from_response(cookies, resp):
    """从响应的 Set-Cookie 中提取新的 _m_h5_tk 和 _m_h5_tk_enc"""
    for key in ("_m_h5_tk", "_m_h5_tk_enc"):
        if key in resp.cookies:
            cookies[key] = resp.cookies[key]


def fetch_feed(cookies, page_number=1, page_size=30):
    """获取闲鱼首页推荐 feed，自动处理 token 过期（两次请求机制）"""
    url = "https://h5api.m.goofish.com/h5/mtop.taobao.idlehome.home.webpc.feed/1.0/"

    params, post_data = build_feed_request(cookies, page_number, page_size)
    resp = curl_requests.post(url, headers=headers, cookies=cookies, params=params, data=post_data, impersonate="chrome")

    result = resp.json()
    ret = result.get("ret", [])

    # token 过期或缺失时，服务器返回错误但会在 Set-Cookie 中下发新 token
    token_expired = any("TOKEN_EXOIRED" in r or "TOKEN_EMPTY" in r for r in ret)
    if token_expired:
        print("  token 过期/缺失，使用服务器下发的新 token 重试...")
        update_cookies_from_response(cookies, resp)

        # 用新 token 重新构造请求
        params, post_data = build_feed_request(cookies, page_number, page_size)
        resp = curl_requests.post(url, headers=headers, cookies=cookies, params=params, data=post_data, impersonate="chrome")
        result = resp.json()

    # 无论是否重试，都更新 cookie 中的 token（保持最新）
    update_cookies_from_response(cookies, resp)
    return result


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
            "picUrl": detail.get("picUrl", ""),
        }
        items.append(item)

    return items


def load_seen_ids(filepath="xy_seen_ids.json"):
    """加载已推送记录，格式: {itemId: timestamp}"""
    if os.path.exists(filepath):
        with open(filepath, "r") as f:
            data = json.load(f)
            # 兼容旧格式（纯列表）
            if isinstance(data, list):
                return {item_id: time.time() for item_id in data}
            return data
    return {}


def save_seen_ids(seen_dict, filepath="xy_seen_ids.json"):
    """保存已推送记录，自动清理超过3天的"""
    now = time.time()
    three_days = 3 * 24 * 3600
    cleaned = {k: v for k, v in seen_dict.items() if now - v < three_days}
    with open(filepath, "w") as f:
        json.dump(cleaned, f)


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


# 关键词白名单，命中任一即保留给 AI 判断
KEYWORDS = [
    "预约", "代抢", "代拍", "代购", "代跑", "代办", "代订", "代排",
    "抢购", "秒杀", "脚本", "自动化", "外挂", "辅助", "定制", "开发",
    "接单", "门票", "车票", "挂号", "取号", "排队", "黄牛",
    "签证", "代签", "代约", "代订票", "代注册", "代做", "代写",
    "爬虫", "逆向", "破解", "接口", "数据采集", "批量",
]


def keyword_filter(items):
    """关键词预过滤，只保留标题命中关键词的商品"""
    matched = []
    for item in items:
        title = item.get("title", "")
        if any(kw in title for kw in KEYWORDS):
            matched.append(item)
    return matched


def ai_filter(items, api_key):
    """调用 DeepSeek 批量判断商品是否值得推送"""
    if not items:
        return []

    # 构造精简的商品列表给 AI
    items_for_ai = []
    for item in items:
        items_for_ai.append({
            "id": item["itemId"],
            "title": item["title"],
            "price": item["price"],
            "wantCount": item["wantCount"],
        })

    prompt = f"""你是一个闲鱼商品筛选助手。请判断以下商品中，哪些属于"能赚钱的服务类商品"。

筛选标准：
- 预约服务（门票预约、挂号预约、车辆预约、景区预约等）
- 代跑/代办服务（代抢、代拍、代排队、代注册等）
- 抢购服务（限量商品抢购、秒杀服务等）
- 脚本/自动化定制（爬虫、自动化工具、脚本开发、数据采集等）
- 技术服务（接口对接、逆向、破解等技术外包）

不要选择：普通二手商品、实物转让、课程资料、虚拟账号、游戏账号

请只返回符合条件的商品ID列表，JSON格式：{{"ids": ["id1", "id2", ...]}}
如果没有符合条件的商品，返回：{{"ids": []}}

商品列表：
{json.dumps(items_for_ai, ensure_ascii=False)}"""

    try:
        resp = requests.post(
            "https://api.deepseek.com/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            },
            json={
                "model": "deepseek-chat",
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.1,
                "response_format": {"type": "json_object"}
            },
            timeout=30
        )
        result = resp.json()
        content = result["choices"][0]["message"]["content"]
        selected_ids = json.loads(content).get("ids", [])
        print(f"  DeepSeek 筛选出 {len(selected_ids)} 条值得推送的商品")
        return [item for item in items if item["itemId"] in selected_ids]
    except Exception as e:
        print(f"  DeepSeek 调用失败: {e}，跳过 AI 筛选，直接推送关键词匹配结果")
        return items


if __name__ == "__main__":
    # 定时触发时随机延迟5-10分钟，手动触发跳过
    if os.environ.get("SCHEDULED") == "true":
        delay = random.randint(300, 600)
        print(f"随机延迟 {delay} 秒后执行...")
        time.sleep(delay)

    # 从环境变量读取 cookie 字符串
    cookie_str = os.environ.get("XY_COOKIE", "")
    if not cookie_str:
        print("错误: 未设置 XY_COOKIE 环境变量")
        exit(1)
    cookies = parse_cookie_str(cookie_str)


    dingtalk_webhook = os.environ.get("DINGTALK_WEBHOOK", "")
    dingtalk_secret = os.environ.get("DINGTALK_SECRET", "")
    deepseek_key = os.environ.get("DEEPSEEK_API_KEY", "")

    all_items = []
    total_pages = 3

    for page in range(1, total_pages + 1):
        print(f"正在获取第 {page} 页...")
        resp_data = fetch_feed(cookies, page_number=page)

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
    seen_dict = load_seen_ids()
    new_items = [item for item in all_items if item["itemId"] not in seen_dict]
    print(f"其中新商品 {len(new_items)} 条")

    # 两层筛选：关键词匹配的直接推送，剩余的交给 AI 判断
    if new_items:
        kw_matched = keyword_filter(new_items)
        kw_matched_ids = {item["itemId"] for item in kw_matched}
        print(f"关键词匹配 {len(kw_matched)} 条")

        # 关键词未命中的商品交给 AI 判断
        remaining = [item for item in new_items if item["itemId"] not in kw_matched_ids]
        if remaining and deepseek_key:
            ai_matched = ai_filter(remaining, deepseek_key)
        else:
            ai_matched = []

        # 合并：关键词命中 + AI 筛选通过
        push_items = kw_matched + ai_matched
        print(f"最终推送 {len(push_items)} 条")
    else:
        push_items = []

    if push_items and dingtalk_webhook and dingtalk_secret:
        # 钉钉单条消息有长度限制，每10条发一次
        for i in range(0, len(push_items), 10):
            batch = push_items[i:i+10]
            lines = [f"## 闲鱼服务商品通知 ({len(batch)}条)\n"]
            for item in batch:
                lines.append(f"**{item['title'][:40]}**\n")
                lines.append(f"- 价格: {item['price']}元 | 城市: {item['city']}")
                lines.append(f"- 卖家: {item['seller']} | {item['wantCount']}")
                lines.append(f"- [查看商品](https://www.goofish.com/item?id={item['itemId']})")
                if item.get("picUrl"):
                    lines.append(f"- ![商品图]({item['picUrl']})\n")
                else:
                    lines.append("")
            send_dingtalk(dingtalk_webhook, dingtalk_secret, "闲鱼服务商品通知", "\n".join(lines))
            if i + 10 < len(push_items):
                time.sleep(1)
        print(f"已推送 {len(push_items)} 条服务商品到钉钉")
    elif push_items:
        print("未配置钉钉，仅打印筛选结果：")
        for item in push_items:
            title = item['title'][:40].encode('gbk', errors='replace').decode('gbk', errors='replace')
            print(f"  {title} | {item['price']}元 | {item['city']}")
    else:
        print("没有符合条件的服务类商品")

    # 更新已见ID（带时间戳）
    now = time.time()
    for item in all_items:
        seen_dict[item["itemId"]] = now
    save_seen_ids(seen_dict)
