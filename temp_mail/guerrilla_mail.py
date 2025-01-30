import asyncio
import json
import time
from typing import Optional

import httpx

from temp_mail.client import MailClientABC, MailData
from temp_mail.tools import get_sha256_hash


class GuerrillaMail(MailClientABC):

    # doc: https://www.guerrillamail.com/GuerrillaMailAPI.html

    def __init__(self, ip="127.0.0.1", agent="Python-httpx-client"):
        self.base_url = "https://api.guerrillamail.com/ajax.php"
        self.ip = ip
        self.agent = agent
        self.sid_token = Optional[str]
        self.subscriber_cookie = Optional[str]
        self.email_address = Optional[str]
        self.email_list: list[MailData] = []
        self.mail_map: dict[str, MailData] = {}
        self.mail_set: set[MailData] = set()

    async def get_email_address(self) -> str:
        fn = f"get_email_address"
        params = {
            "f": "get_email_address",  # 函数名
            "ip": self.ip,  # 用户 IP 地址（可替换为实际 IP）
            "agent": self.agent,  # 用户代理
            "lang": "en"  # 语言代码
        }
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    self.base_url,
                    params=params,
                    timeout=30.0,
                )
                response.raise_for_status()
                data = response.json()
                self.sid_token = data["sid_token"]
                self.email_address = data["email_addr"]
                if "set-cookie" in response.headers:
                    for cookie_str in response.headers.get_list("set-cookie"):
                        if "PHPSESSID=" in cookie_str:
                            self.subscriber_cookie = cookie_str.split("PHPSESSID=")[1].split(";")[0]
                            print(f"GuerrillaMail {fn} 成功，subscriber_cookie: {self.subscriber_cookie}")
                return self.email_address
        except httpx.HTTPStatusError as e:
            raise Exception(f"获取邮箱地址失败，HTTP状态码: {e.response.status_code}, 详情: {e.response.text}") from e
        except httpx.RequestError as e:
            raise Exception(f"获取邮箱地址请求失败: {str(e)}") from e
        except Exception as e:
            raise Exception(f"获取邮箱地址发生未知错误: {str(e)}") from e

    async def get_email_list(self) -> list[MailData]:
        if not self.sid_token or not self.subscriber_cookie:
            raise Exception("请先获取邮箱地址")
        fn = f"check_email"
        params = {
            "f": fn,
            "seq": 0,
            "sid_token": self.sid_token,
        }
        headers = {
            "cookie": f"PHPSESSID={self.subscriber_cookie}"
        }
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    self.base_url,
                    params=params,
                    timeout=30.0,
                    headers=headers
                )
                response.raise_for_status()
                ll = response.json()["list"]
                if len(ll) > 0:
                    for email in ll:
                        mail_id = email["mail_id"]
                        if mail_id not in self.mail_set:
                            self.mail_set.add(mail_id)
                            params = {
                                "f": "fetch_email",
                                "email_id": mail_id,
                                "sid_token": self.sid_token,
                            }
                            response = await client.get(
                                self.base_url,
                                params=params,
                                timeout=30.0,
                                headers=headers
                            )
                            response.raise_for_status()
                            email_data = response.json()
                            md5_hash = get_sha256_hash(json.dumps(email_data))
                            item = MailData(
                                md5=md5_hash,
                                id=mail_id,
                                from_=email_data["mail_from"],
                                to=self.email_address,
                                subject=email_data["mail_subject"],
                                date=email_data["mail_timestamp"],
                                body=email_data["mail_excerpt"],
                                html=email_data["mail_body"],
                                createdAt=email_data["mail_date"]
                            )
                            self.email_list.append(item)
                            self.mail_map[item.id] = item
                        else:
                            pass

        except httpx.HTTPStatusError as e:
            raise Exception(f"获取邮箱收件列表失败，HTTP状态码: {e.response.status_code}, 详情: {e.response.text}") from e
        except httpx.RequestError as e:
            raise Exception(f"获取邮箱收件列表请求失败: {str(e)}") from e
        except Exception as e:
            raise Exception(f"获取邮箱收件列表发生未知错误: {str(e)}") from e
        return self.email_list


    async def destroy(self) -> None:
        fn = f"forget_me"
        params = {
            "f": fn,
            "email_addr": self.email_address,
            "sid_token": self.sid_token,
        }
        headers = {
            "cookie": f"PHPSESSID={self.subscriber_cookie}"
        }
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    self.base_url,
                    params=params,
                    timeout=30.0,
                    headers=headers
                )
                response.raise_for_status()
                print(f"GuerrillaMail {fn} 成功")
        except httpx.HTTPStatusError as e:
            raise Exception(f"销毁邮箱地址失败，HTTP状态码: {e.response.status_code}, 详情: {e.response.text}") from e
        except httpx.RequestError as e:
            raise Exception(f"销毁邮箱地址请求失败: {str(e)}") from e
        except Exception as e:
            raise Exception(f"销毁邮箱地址发生未知错误: {str(e)}") from e


async def main():
    mail_client = GuerrillaMail()
    email_address = await mail_client.get_email_address()
    print(f"GuerrillaMail 获取邮箱地址成功，email_address: {email_address}")
    for i in range(100):
        print(f"尝试获取验证码，剩余次数: {100 - i}")
        time.sleep(3)
        try:
            data = await mail_client.get_email_list()
            print(f"GuerrillaMail 获取邮箱收件列表成功，email_list: {data}")
        except Exception as e:
            print(f"获取邮箱收件列表失败，原因: {str(e)}")

if __name__ == "__main__":
    asyncio.run(main())