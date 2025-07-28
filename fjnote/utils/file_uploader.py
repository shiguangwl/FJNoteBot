"""
File Uploader Utility
文件上传工具类，负责处理文件下载和上传到Blinko的逻辑
"""

import aiohttp
from typing import Dict, Any

from ..services.blinko_api import BlinkoApiClient
from astrbot.api import logger

class FileUploader:
    """文件上传器"""

    def __init__(self, api_client: BlinkoApiClient):
        """
        初始化文件上传器
        
        :param api_client: Blinko API 客户端实例
        """
        self.api_client = api_client

    async def upload_and_get_markdown_link(self, msg: Dict[str, Any]) -> str:
        """
        从消息中包含的URL下载文件，上传到Blinko，并返回Markdown格式的链接。
        
        :param msg: 包含文件/图片信息的消息字典
        :return: Markdown 格式的链接字符串，或在失败时返回错误提示
        """
        file_url = msg.get("url")
        if not file_url:
            return ""

        try:
            # 1. 从 URL 下载文件内容
            async with aiohttp.ClientSession() as session:
                async with session.get(file_url) as response:
                    if response.status != 200:
                        logger.error(f"下载文件失败 {file_url}: 状态码 {response.status}")
                        return f"[{msg.get('type', 'file')} 下载失败]"
                    file_data = await response.read()

            # 2. 上传到 Blinko
            filename = msg.get("filename", "file")
            upload_response = await self.api_client.upload_file(file_data, filename)
            
            # 3. 解析响应并获取 URL
            # 假设响应格式为 {'url': '...'} 或 {'data': {'url': '...'}}
            uploaded_url = upload_response.get("url") or upload_response.get("data", {}).get("url")

            if not uploaded_url:
                logger.error(f"Blinko 上传响应中不包含 URL: {upload_response}")
                return f"[{msg.get('type', 'file')} 上传失败]"

            # 4. 返回 Markdown 格式的链接
            if msg.get("type") == "image":
                return f"![{filename}]({uploaded_url})"
            else:
                return f"[{filename}]({uploaded_url})"

        except Exception as e:
            logger.error(f"文件上传过程中出错 {file_url}: {e}")
            return f"[{msg.get('type', 'file')} 处理失败]"