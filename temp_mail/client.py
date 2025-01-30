from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Protocol


@dataclass
class MailData:
    """存储邮件数据的数据类

    Attributes:
        md5: 邮件的MD5哈希值
        id: 邮件唯一标识符
        from_: 发件人地址
        to: 收件人地址
        subject: 邮件主题
        date: 邮件时间戳
        body: 邮件文本内容
        html: 邮件HTML内容
        createdAt: 邮件创建时间
    """
    md5: str
    id: str
    from_: str
    to: str
    subject: str
    date: int
    body: str
    html: str
    createdAt: str

class MailClientError(Exception):
    """邮件客户端异常类"""
    pass

class MailClientABC(ABC):
    """邮件客户端抽象基类，定义邮件客户端的基本接口"""

    @abstractmethod
    async def get_email_address(self) -> str:
        """获取临时邮箱地址

        Returns:
            str: 临时邮箱地址
        """
        pass

    @abstractmethod
    async def get_email_list(self) -> list[MailData]:
        """获取邮箱收件列表

        Returns:
            list[MailData]: 邮件数据列表
        """
        pass

    @abstractmethod
    async def destroy(self) -> None:
        """销毁客户端资源

        Raises:
            ClientError: 销毁过程中发生错误
        """
        pass

class MailClientProtocol(Protocol):
    """
    定义邮件客户端协议
    """
    async def get_email_address(self) -> str:
        """
        获取临时邮箱地址
        """
        ...

    async def get_email_list(self) -> list[MailData]:
        """
        获取邮箱收件列表
        """
        ...

    async def destroy(self) -> None:
        """
        销毁客户端资源
        """
        ...