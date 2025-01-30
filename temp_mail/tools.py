import hashlib
import secrets
import string

import httpx

from temp_mail.client import MailClientError


def generate_secure_random_string(length=10):
    # 定义字符集：字母（大小写） + 数字
    characters = string.ascii_letters + string.digits
    # 从字符集中随机选择指定长度的字符
    random_string = ''.join(secrets.choice(characters) for _ in range(length))
    return random_string


def get_sha256_hash(data_string: str) -> str:
    encoded_data = data_string.encode()
    sha256_hash = hashlib.sha256(encoded_data).hexdigest()
    return sha256_hash

async def destroy_mail(mail_address: str,url:str,header:dict) -> None:
    try:
        async with httpx.AsyncClient() as client:
            response = await client.delete(
                url,
                headers=header,
                timeout=30.0
            )
            response.raise_for_status()
            print(f"销毁邮箱地址成功，mail_address: {mail_address}")
    except httpx.HTTPStatusError as e:
        raise MailClientError(
            f"销毁邮箱地址失败，HTTP状态码: {e.response.status_code}, 详情: {e.response.text}") from e
    except httpx.RequestError as e:
        raise MailClientError(f"销毁邮箱地址请求失败: {str(e)}") from e
    except Exception as e:
        raise MailClientError(f"销毁邮箱地址发生未知错误: {str(e)}") from e