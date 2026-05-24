import requests
import base64
import json
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


# 使用示例
if __name__ == "__main__":
    token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6Ijg4QUI3NTlGQzI3NDQ1NTdCQkMyQjkwQkMzQjdEMUY0IiwidXNlcm5hbWUiOiLluJjlpJbmtbfmo6AiLCJpYXQiOjE3Nzk1NDM3NjAsImV4cCI6MTc4MjEzNTc2MH0.HnXcpbewj2Q2YZAk7lmojZGAbIW_VmnN8T8MVG-MfZk"

    # 创建API实例
    api = XiaohongziAPI(token)

    # 获取第2页数据
    result = api.get_orders(page=1)
    result_list = result.get("record")
    for order in result_list:
        print(order.get("id"))
        print(order.get("title"))
        print(order.get("desc"))
        print(order.get("createTime"))
        print("*"*60)

    # print(json.dumps(result, indent=2, ensure_ascii=False))