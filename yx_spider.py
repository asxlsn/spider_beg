import requests
import base64
import json
import time
import random
import os
import hmac
import hashlib
from urllib.parse import quote_plus
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad


class XiaohongziAPI:
    """小红滋API客户端"""

    # 固定的密钥和IV（类属性）
    KEY = b'8s@kQ2$9pR7!zDc5'
    IV = b'$3aF6&dS2^zX1!jH'

    def __init__(self, token: str):
        self.token = token
        self.base_url = "https://dgserver.xiaohongzi.top"
        self.headers = {
            "accept": "*/*",
            "accept-language": "zh-CN,zh;q=0.9",
            "authorization": f"Bearer {token}",
            "content-type": "text/plain",
            "priority": "u=1, i",
            "referer": "https://servicewechat.com/wx8a79caadf0490571/45/page-frame.html",
            "sec-fetch-dest": "empty",
            "sec-fetch-mode": "cors",
            "sec-fetch-site": "cross-site",
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36 MicroMessenger/7.0.20.1781(0x6700143B) NetType/WIFI MiniProgramEnv/Windows WindowsWechat/WMPF WindowsWechat(0x63090a13) UnifiedPCWindowsWechat(0xf2541212) XWEB/16815",
            "xweb_xhr": "1"
        }

    def encrypt_request(self, data_dict: dict) -> str:
        """加密请求数据"""
        plain_text = json.dumps(data_dict, ensure_ascii=False)
        cipher = AES.new(self.KEY, AES.MODE_CBC, self.IV)
        encrypted_bytes = cipher.encrypt(pad(plain_text.encode('utf-8'), AES.block_size))
        return base64.b64encode(encrypted_bytes).decode('utf-8')

    def decrypt_response(self, encrypted_text: str) -> dict:
        """解密响应数据"""
        ciphertext = base64.b64decode(encrypted_text)
        cipher = AES.new(self.KEY, AES.MODE_CBC, self.IV)
        decrypted = unpad(cipher.decrypt(ciphertext), AES.block_size)
        return json.loads(decrypted.decode('utf-8'))

    def get_orders(self, order_type: str = "1", status: int = 0,
                   keyword: str = "", page: int = 1, page_size: int = 20) -> dict:
        """获取订单列表"""
        # 构造请求参数
        request_params = {
            "orderType": order_type,
            "status": status,
            "keyword": keyword,
            "page": page,
            "pageSize": page_size
        }

        # 加密请求
        encrypted_data = self.encrypt_request(request_params)

        # 发送请求
        url = f"{self.base_url}/api/receivingorders/get/status"
        response = requests.post(url, headers=self.headers, data=encrypted_data)

        # 解密响应
        result = self.decrypt_response(response.json().get("data"))
        return result


def send_dingtalk(webhook_url, secret, title, content):
    """发送钉钉机器人通知（带加签）"""
    timestamp = str(round(time.time() * 1000))
    string_to_sign = f"{timestamp}\n{secret}"
    hmac_code = hmac.new(secret.encode('utf-8'), string_to_sign.encode('utf-8'), digestmod=hashlib.sha256).digest()
    sign = quote_plus(base64.b64encode(hmac_code))
    url = f"{webhook_url}&timestamp={timestamp}&sign={sign}"

    data = {
        "msgtype": "markdown",
        "markdown": {
            "title": title,
            "text": content
        }
    }
    requests.post(url, json=data)


def load_seen_ids(filepath="seen_ids.json"):
    """加载上次推送过的订单ID"""
    if os.path.exists(filepath):
        with open(filepath, "r") as f:
            return set(json.load(f))
    return set()


def save_seen_ids(seen_ids, filepath="seen_ids.json"):
    """保存本次订单ID"""
    with open(filepath, "w") as f:
        json.dump(list(seen_ids), f)


if __name__ == "__main__":
    # 定时触发时随机延迟，手动触发时跳过
    if os.environ.get("SCHEDULED") == "true":
        delay = random.randint(0, 3600)
        print(f"随机延迟 {delay} 秒后执行...")
        time.sleep(delay)

    token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6Ijg4QUI3NTlGQzI3NDQ1NTdCQkMyQjkwQkMzQjdEMUY0IiwidXNlcm5hbWUiOiLluJjlpJbmtbfmo6AiLCJpYXQiOjE3Nzk1NDM3NjAsImV4cCI6MTc4MjEzNTc2MH0.HnXcpbewj2Q2YZAk7lmojZGAbIW_VmnN8T8MVG-MfZk"
    dingtalk_webhook = os.environ.get("DINGTALK_WEBHOOK", "")
    dingtalk_secret = os.environ.get("DINGTALK_SECRET", "")

    api = XiaohongziAPI(token)
    result = api.get_orders(page=1)
    result_list = result.get("record", [])

    if not result_list:
        print("没有获取到订单数据")
    elif dingtalk_webhook and dingtalk_secret:
        # 加载上次的订单ID，用于标注新增
        prev_ids = load_seen_ids()

        # 构造钉钉消息，全部订单都推送，新增的标注【新】
        lines = [f"## 订单通知 (共{len(result_list)}条)\n"]
        for order in result_list:
            is_new = order.get("id") not in prev_ids
            tag = "【新】" if is_new else ""
            lines.append(f"**{tag}{order.get('title', '')}**\n")
            lines.append(f"- 描述：{order.get('desc', '')}")
            lines.append(f"- 时间：{order.get('createTime', '')}\n")

        send_dingtalk(dingtalk_webhook, dingtalk_secret, "订单通知", "\n".join(lines))
        print(f"已推送 {len(result_list)} 条订单到钉钉")

        # 保存本次所有订单ID
        current_ids = {o.get("id") for o in result_list}
        save_seen_ids(current_ids)
    else:
        print("未配置钉钉 webhook 或 secret，仅打印：")
        for order in result_list:
            print(f"  - {order.get('title')} | {order.get('desc')} | {order.get('createTime')}")