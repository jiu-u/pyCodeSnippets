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



class IDataRiverClient(MailClientABC):
    # doc: https://www.idatariver.com/zh-cn/project/%E4%B8%B4%E6%97%B6%E9%82%AE%E7%AE%B1api-cbea

    def __init__(self,key:str):
        self.key = key
        self.api_url = "https://apiok.us"
        self.headers = {
            "Content-Type": "application/json",
            "Accept": "*/*",
        }
        self.email_address: Optional[str] = None
        self.email_id: Optional[str] = None
        self.email_list: list[MailData] = []
        self.mail_map: dict[str, MailData] = {}
        self.mail_set: set[MailData] = set()


    async def get_email_address(self) -> str:
        url = f"{self.api_url}/api/cbea/generate/v1"
        params = {
            "apikey": self.key,
            "type": "*",
        }
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(url, params=params)
                response.raise_for_status()
                data = response.json()
                self.email_address = data["result"]["email"]
                self.email_id = data["result"]["id"]
                return self.email_address
        except httpx.HTTPStatusError as e:
            raise MailClientError(
                f"获取邮箱收件列表失败，HTTP状态码: {e.response.status_code}, 详情: {e.response.text}") from e
        except httpx.RequestError as e:
            raise MailClientError(f"获取邮箱收件列表请求失败: {str(e)}") from e
        except Exception as e:
            raise MailClientError(f"获取邮箱收件列表发生未知错误: {str(e)}") from e

    async def get_email_list(self) -> list[MailData]:
        if not self.email_address:
            raise MailClientError("请先获取邮箱地址")
        url = f"{self.api_url}/api/cbea/messages/v1"
        try:
            async with httpx.AsyncClient() as client:
                params = {
                    "apikey": self.key,
                    "id": self.email_id,
                }
                response = await client.get(
                    url,
                    headers=self.headers,
                    timeout=30.0,
                    params=params,
                )
                response.raise_for_status()
                mail_list = response.json()["result"]["messages"]
                if len(mail_list)>0:
                    for mail_x in mail_list:
                        if mail_x["id"] not in self.mail_set:
                            mail_id = mail_x["id"]
                            self.mail_set.add(mail_id)
                            # 获取邮件细节
                            url = f"{self.api_url}/api/cbea/message/detail/v1"
                            params = {
                                "apikey": self.key,
                                "id": mail_id,
                            }
                            response = await client.get(
                                url,
                                headers=self.headers,
                                timeout=30.0,
                                params=params,
                            )
                            response.raise_for_status()
                            mail_data = response.json()
                            md5_hash = get_sha256_hash(json.dumps(mail_data))
                            item = self.convert_data(mail_data,md5_hash,mail_id)
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
        pass


    def convert_data(self,mail_data:dict,md5_hash:str,id:str)->MailData:
        timestamp = mail_data["result"]["time"]  # 1738078638
        t = datetime.fromtimestamp(timestamp)
        created_at = t.strftime("%Y-%m-%d %H:%M:%S")
        # 将邮件数据存入字典中
        item = MailData(
            md5=md5_hash,
            id=id,
            from_=mail_data["result"]["from"],
            to=self.email_address,
            subject=mail_data["result"]["subject"],
            date=timestamp,
            body=mail_data["result"]["content"],
            html=mail_data["result"]["content"],
            createdAt=created_at
        )
        return item

async def main():
    mail_client = IDataRiverClient(key="your_key")
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