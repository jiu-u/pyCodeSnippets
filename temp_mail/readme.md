# Mail Client

一个用于处理临时邮箱的Python异步邮件客户端库。

## 功能特性

- 异步支持
- 获取临时邮箱地址
- 获取邮件列表
- 自动资源管理

## 快速开始

```python
async def main():
    # 初始化邮件客户端
    client = MailClient()  # 替换为具体实现
    
    try:
        # 获取临时邮箱地址
        email = await client.get_email_address()
        print(f"临时邮箱地址: {email}")
        
        # 获取邮件列表
        emails = await client.get_email_list()
        for email in emails:
            print(f"主题: {email.subject}")
            print(f"发件人: {email.from_}")
            print(f"内容: {email.body}")
    
    finally:
        # 清理资源
        await client.destroy()

asyncio.run(main())
```

## API 文档
*MailData*
邮件数据类，包含以下字段：
- md5: 邮件的MD5哈希值
- id: 邮件唯一标识符
- from_: 发件人地址
- to: 收件人地址
- subject: 邮件主题
- date: 邮件时间戳
- body: 邮件文本内容
- html: 邮件HTML内容
- createdAt: 邮件创建时间

*MailClient*
邮件客户端基类，定义了以下方法：

- async get_email_address() -> str: 获取临时邮箱地址
- async get_email_list() -> list[MailData]: 获取邮箱收件列表
- async destroy() -> None: 销毁客户端资源

## 错误处理
库使用 MailClientError 异常类处理所有相关错误。

## 协议
该项目实现了 MailClientProtocol 协议，可用于类型检查和接口定义。