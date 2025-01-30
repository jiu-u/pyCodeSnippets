import asyncio
import json
import time
from typing import Optional

import httpx

from temp_mail.client import MailClientABC, MailData, MailClientError
from temp_mail.tools import get_sha256_hash


class TempMailLOL(MailClientABC):
    """TempMail.lol 临时邮箱客户端实现

    实现基于 https://tempmail.lol/zh/api 的临时邮箱服务
    """

    def __init__(self):
        """初始化临时邮箱客户端"""
        self.api_url: str = "https://api.tempmail.lol"
        self.headers: dict = {
            "Content-Type": "application/json",
            "Accept": "*/*",
        }
        # 使用 Optional 类型提示可能为空的属性
        self.email_address: Optional[str] = None
        self.email_token: Optional[str] = None
        self.email_list: list[MailData] = []
        self.mail_map: dict[str, MailData] = {}
        self.mail_set: set[str] = set()

    async def get_email_address(self) -> str:
        """获取临时邮箱地址

        Returns:
            str: 临时邮箱地址

        Raises:
            MailClientError: 当获取邮箱地址失败时抛出
        """
        url = f"{self.api_url}/v2/inbox/create"

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    url,
                    headers=self.headers,
                    timeout=30.0,
                    json={"email": "sky@sky.com"}
                )
                response.raise_for_status()
                data = response.json()

                self.email_address = data["address"]
                self.email_token = data["token"]
                # print(f"TempMailLOL 获取邮箱地址成功，email_address: {self.email_address}")
                return self.email_address
        except httpx.HTTPStatusError as e:
            raise MailClientError(
                f"获取邮箱地址失败，HTTP状态码: {e.response.status_code}, 详情: {e.response.text}") from e
        except httpx.RequestError as e:
            raise MailClientError(f"获取邮箱地址请求失败: {str(e)}") from e
        except Exception as e:
            raise MailClientError(f"获取邮箱地址发生未知错误: {str(e)}") from e

    async def get_email_list(self) -> list[MailData]:
        """获取邮箱收件列表

        Returns:
            list[MailData]: 邮件数据列表
        """
        if not self.email_address:
            raise MailClientError("请先获取邮箱地址")
        if not self.email_token:
            raise MailClientError("请先获取邮箱令牌")
        url = f"{self.api_url}/v2/inbox"
        token = self.email_token
        params = {
            "token": token
        }
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    url,
                    params=params,
                    headers=self.headers,
                    timeout=30.0
                )
                response.raise_for_status()
                data = response.json()
                if data["expired"]:
                    raise MailClientError("邮箱已过期")
                if len(data["emails"]):
                    for email in data["emails"]:
                        md5_hash = get_sha256_hash(json.dumps(email))
                        item = MailData(
                            md5=md5_hash,
                            id=email["_id"],
                            from_=email["from"],
                            to=email["to"],
                            subject=email["subject"],
                            date=email["date"],
                            body=email["body"],
                            html=email["html"],
                            createdAt=email["createdAt"]
                        )
                        if item.id not in self.mail_set:
                            self.mail_set.add(item.id)
                            self.email_list.append(item)
                            self.mail_map[item.id] = item
                            # print(f"TempMailLOL 获取邮箱收件列表成功，email_id: {item.id}")
        except httpx.HTTPStatusError as e:
            raise MailClientError(
                f"获取邮箱收件列表失败，HTTP状态码: {e.response.status_code}, 详情: {e.response.text}") from e
        except httpx.RequestError as e:
            raise MailClientError(f"获取邮箱收件列表请求失败: {str(e)}") from e
        except Exception as e:
            raise MailClientError(f"获取邮箱收件列表发生未知错误: {str(e)}") from e

        return self.email_list


    async def destroy(self) -> None:
        pass

async def main():
    mail_client = TempMailLOL()
    email_address = await mail_client.get_email_address()
    print(f"TempMailLOL 获取邮箱地址成功，email_address: {email_address}")
    max_count = 100
    for i in range(max_count):
        print(f"尝试获取验证码，剩余次数: {max_count - i}")
        time.sleep(3)
        try:
            data = await mail_client.get_email_list()
            print(f"TempMailLOL 获取邮箱收件列表成功，email_list: {data}")
        except MailClientError as e:
            print(f"获取邮箱收件列表失败，原因: {str(e)}")

if __name__ == "__main__":
    asyncio.run(main())