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

DOMAINS = ["yzm.de","qabq.com","nqmo.com","end.tw","uuf.me","yzm.de"]

class MailCX(MailClientABC):

    def __init__(self):
        self.domains:list[str] = DOMAINS
        self.api_url = "https://api.mail.cx"
        self.headers = {
            "Content-Type": "application/json",
            "Accept": "*/*",
        }
        self.email_address: Optional[str] = None
        self.email_token: Optional[str] = None
        self.email_list: list[MailData] = []
        self.mail_map: dict[str, MailData] = {}
        self.mail_set: set[MailData] = set()

    # doc:https://api.mail.cx/

    async def auth(self)->None:
        url = f"{self.api_url}/api/v1/auth/authorize_token"
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    url,
                    headers=self.headers,
                    timeout=30.0,
                    json={"domains": self.domains}
                )
                response.raise_for_status()
                token = response.text
                token = token.replace('"','')
                token = token.replace('\n','')
                self.email_token = str(token)
                self.headers["Authorization"] = f"Bearer {self.email_token}"
        except httpx.HTTPStatusError as e:
            raise MailClientError(
                f"获取邮箱地址失败，HTTP状态码: {e.response.status_code}, 详情: {e.response.text}") from e
        except httpx.RequestError as e:
            raise MailClientError(f"获取邮箱地址请求失败: {str(e)}") from e
        except Exception as e:
            raise MailClientError(f"获取邮箱地址发生未知错误: {str(e)}") from e

    async def get_email_address(self) -> str:
        await self.auth()
        domain = random.choice(self.domains)
        name = generate_secure_random_string(8)
        mail_address = f"{name}@{domain}"
        self.email_address = mail_address
        return self.email_address

    async def get_email_list(self) -> list[MailData]:
        if not self.email_address:
            raise MailClientError("请先获取邮箱地址")
        url = f"{self.api_url}/api/v1/mailbox/{self.email_address}"
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    url,
                    headers=self.headers,
                    timeout=30.0
                )
                response.raise_for_status()
                mail_list = response.json()
                if len(mail_list)>0:
                    for mail_x in mail_list:
                        if mail_x["id"] not in self.mail_set:
                            mail_id = mail_x["id"]
                            self.mail_set.add(mail_id)
                            # 获取邮件细节
                            url = f"{self.api_url}/api/v1/mailbox/{self.email_address}/{mail_id}"
                            response = await client.get(
                                url,
                                headers=self.headers,
                                timeout=30.0
                            )
                            response.raise_for_status()
                            mail_data = response.json()
                            md5_hash = get_sha256_hash(json.dumps(mail_data))
                            item = MailCX.convert_data(mail_data,md5_hash)
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

    async def destroy(self) -> None:
        url = f"{self.api_url}/api/v1/mailbox/{self.email_address}"
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

    @staticmethod
    def convert_data(mail_data:dict,md5_hash:str)->MailData:
        t = mail_data["date"]  # "2025-01-27T07:27:25.711873584Z"
        tt = datetime.strptime(t[:26], "%Y-%m-%dT%H:%M:%S.%f")
        created_at = tt.strftime("%Y-%m-%d %H:%M:%S")
        date = int(tt.timestamp() * 1000)
        from_ = mail_data["from"]
        to = mail_data["to"][0]
        # 正则表达式用于匹配电子邮件地址
        email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
        from_email = re.search(email_pattern, from_)
        to_email = re.search(email_pattern, to)
        from_email_address = from_email.group() if from_email else None
        to_email_address = to_email.group() if to_email else None
        # 将邮件数据存入字典中
        item = MailData(
            md5=md5_hash,
            id=mail_data["id"],
            from_=from_email_address,
            to=to_email_address,
            subject=mail_data["subject"],
            date=date,
            body=mail_data["body"]["text"],
            html=mail_data["body"]["html"],
            createdAt=created_at
        )
        return item

async def main():
    mail_client = MailCX()
    email_address = await mail_client.get_email_address()
    print(f"MailCX 获取邮箱地址成功，email_address: {email_address}")
    for i in range(100):
        print(f"尝试获取验证码，剩余次数: {100 - i}")
        time.sleep(3)
        try:
            data = await mail_client.get_email_list()
            print(f"MailCX 获取邮箱收件列表成功，email_list: {data}")
        except MailClientError as e:
            print(f"获取邮箱收件列表失败，原因: {str(e)}")

if __name__ == "__main__":
    asyncio.run(main())