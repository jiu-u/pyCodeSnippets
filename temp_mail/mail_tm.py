import asyncio
import json
import random
import re
import time
from datetime import datetime
from typing import Optional

import httpx

from temp_mail.client import MailClientABC, MailData, MailClientError
from temp_mail.tools import generate_secure_random_string, get_sha256_hash, destroy_mail


class MailTM(MailClientABC):

    def __init__(self):
        self.domains:list[str] = []
        self.api_url = "https://api.mail.tm"
        self.headers = {
            "Content-Type": "application/json",
            "Accept": "*/*",
        }
        self.email_address: Optional[str] = None
        self.email_password: Optional[str] = None
        self.email_token: Optional[str] = None
        self.email_list: list[MailData] = []
        self.account_id: Optional[str] = None
        self.mail_map: dict[str, MailData] = {}
        self.mail_set: set[MailData] = set()

    # doc: https://docs.mail.tm/

    async def get_domains(self)->list[str]:
        url = f"{self.api_url}/domains"
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    url,
                    headers=self.headers,
                    timeout=30.0
                )
                response.raise_for_status()
                response_data = response.json()
                ll = response_data["hydra:member"]
                if len(ll) == 0:
                    raise MailClientError("获取域名列表失败，没有域名")
                domains = []
                for domain in ll:
                    domains.append(domain["domain"])
                self.domains = domains
                return self.domains
        except httpx.HTTPStatusError as e:
            raise MailClientError(
                f"获取域名列表，HTTP状态码: {e.response.status_code}, 详情: {e.response.text}") from e
        except httpx.RequestError as e:
            raise MailClientError(f"获取域名列表请求失败: {str(e)}") from e
        except Exception as e:
            raise MailClientError(f"获取域名列表发生未知错误: {str(e)}") from e

    async def generate(self)->None:
        if len(self.domains) == 0:
            raise MailClientError("未获取到域名列表，请先调用 get_domains 方法获取域名列表")
        domain = random.choice(self.domains)
        name = generate_secure_random_string(16).lower()
        mail_address = f"{name}@{domain}"
        self.email_address = mail_address
        self.email_password = generate_secure_random_string(16)
        url = f"{self.api_url}/accounts"
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    url,
                    headers=self.headers,
                    timeout=30.0,
                    json={
                        "address": self.email_address,
                        "password": self.email_password,
                    },
                )
                response.raise_for_status()
                data = response.json()
        except httpx.HTTPStatusError as e:
            raise MailClientError(
                f"创建邮箱地址失败，HTTP状态码: {e.response.status_code}, 详情: {e.response.text}") from e
        except httpx.RequestError as e:
            raise MailClientError(f"创建邮箱地址发生未知错误: {str(e)}") from e
        except Exception as e:
            raise MailClientError(f"创建邮箱地址发生未知错误: {str(e)}") from e

    async def auth(self)->None:
        if self.email_address is None or self.email_password is None:
            raise MailClientError("邮箱地址或密码为空，请先调用 create_email_address 方法设置邮箱地址和密码")
        url = f"{self.api_url}/token"
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    url,
                    headers=self.headers,
                    timeout=30.0,
                    json={
                        "address": self.email_address,
                        "password": self.email_password,
                    }
                )
                response.raise_for_status()
                token = response.json()
                self.account_id = token["id"]
                self.email_token = token["token"]
                self.headers["Authorization"] = f"Bearer {self.email_token}"
        except httpx.HTTPStatusError as e:
            raise MailClientError(
                f"获取邮箱token失败，HTTP状态码: {e.response.status_code}, 详情: {e.response.text}") from e
        except httpx.RequestError as e:
            raise MailClientError(f"获取邮箱token请求失败: {str(e)}") from e
        except Exception as e:
            raise MailClientError(f"获取邮箱token发生未知错误: {str(e)}") from e

    async def get_email_address(self) -> str:
        await self.get_domains()
        await self.generate()
        await self.auth()
        return self.email_address

    async def destroy(self) -> None:
        url = f"{self.api_url}/accounts/{self.account_id}"
        await destroy_mail(self.email_address,url,self.headers)
        # try:
        #     async with httpx.AsyncClient() as client:
        #         response = await client.delete(
        #             url,
        #             headers=self.headers,
        #             timeout=30.0
        #         )
        #         response.raise_for_status()
        # except httpx.HTTPStatusError as e:
        #     raise MailClientError(
        #         f"销毁邮箱地址失败，HTTP状态码: {e.response.status_code}, 详情: {e.response.text}") from e
        # except httpx.RequestError as e:
        #     raise MailClientError(f"销毁邮箱地址请求失败: {str(e)}") from e
        # except Exception as e:
        #     raise MailClientError(f"销毁邮箱地址发生未知错误: {str(e)}") from e

    async def get_email_list(self) -> list[MailData]:
        if self.email_address is None:
            raise MailClientError("请先获取邮箱地址")
        url = f"{self.api_url}/messages"
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    url,
                    headers=self.headers,
                    timeout=30.0
                )
                response.raise_for_status()
                mail_list = response.json()["hydra:member"]
                if len(mail_list)>0:
                    for mail_x in mail_list:
                        if mail_x["id"] not in self.mail_set:
                            mail_id = mail_x["id"]
                            self.mail_set.add(mail_id)
                            # 获取邮件细节
                            url = f"{self.api_url}/messages/{mail_id}"
                            response = await client.get(
                                url,
                                headers=self.headers,
                                timeout=30.0
                            )
                            response.raise_for_status()
                            mail_data = response.json()
                            md5_hash = get_sha256_hash(json.dumps(mail_data))
                            item = MailTM.convert_data(mail_data,md5_hash)
                            self.email_list.append(item)
                        else:
                            pass
        except httpx.HTTPStatusError as e:
            raise MailClientError(
                f"获取邮箱收件列表失败，HTTP状态码: {e.response.status_code}, 详情: {e.response.text}") from e
        except httpx.RequestError as e:
            raise MailClientError(f"获取邮箱收件列表请求失败: {str(e)}") from e
        except Exception as e:
            raise MailClientError(f"获取邮箱收件列表发生未知错误: {str(e)}") from e
        return self.email_list

    @staticmethod
    def convert_data(mail_data:dict,md5_hash:str)->MailData:
        t = mail_data["createdAt"]  # "2025-01-27T09:54:45+00:00"
        tt = datetime.fromisoformat(t)
        created_at = tt.strftime("%Y-%m-%d %H:%M:%S")
        date = int(tt.timestamp() * 1000)
        from_ = mail_data["from"]["address"]
        to = mail_data["to"][0]["address"]
        from_email_address = from_
        to_email_address = to
        # 将邮件数据存入字典中
        item = MailData(
            md5=md5_hash,
            id=mail_data["id"],
            from_=from_email_address,
            to=to_email_address,
            subject=mail_data["subject"],
            date=date,
            body=mail_data["text"],
            html=mail_data["html"][0],
            createdAt=created_at
        )
        return item

async def main():
    mail_client = MailTM()
    email_add = await mail_client.get_email_address()
    print(f"MailTM 获取邮箱列表成功，email_add: {email_add}")
    for i in range(30):
        print(f"尝试获取验证码，剩余次数: {30 - i}")
        time.sleep(3)
        try:
            data = await mail_client.get_email_list()
            print(f"MailTM 获取邮箱收件列表成功，email_list: {data}")
        except MailClientError as e:
            print(f"获取邮箱收件列表失败，原因: {str(e)}")
    await mail_client.destroy()
    print("销毁完成")

if __name__ == "__main__":
    asyncio.run(main())