"""
Flash Session Handler
闪念会话处理器，负责处理会话超时和保存逻辑
"""
import re
from typing import Dict, Any

from ..core.models import FlashSession
from ..strategies.flash_strategy import FlashNoteStrategy
from ..utils.session_manager import ISessionObserver
from ..utils.file_uploader import FileUploader
from ..utils.response_manager import ResponseManager
from astrbot.api import logger

class FlashSessionHandler(ISessionObserver):
    """
    闪念会话处理器
    实现了 ISessionObserver 接口，用于监听和处理会话超时事件。
    """

    def __init__(self, 
                 flash_strategy: FlashNoteStrategy, 
                 file_uploader: FileUploader,
                 response_manager: ResponseManager,
                 config: Dict[str, Any]):
        """
        初始化闪念会话处理器
        
        :param flash_strategy: 闪念笔记策略
        :param file_uploader: 文件上传器
        :param response_manager: 响应管理器
        :param config: 插件配置
        """
        self.flash_strategy = flash_strategy
        self.file_uploader = file_uploader
        self.response_manager = response_manager
        self.config = config

    async def on_session_timeout(self, session: FlashSession):
        """
        会话超时回调方法（观察者模式）
        当会话超时时，此方法被调用以自动保存闪念。
        """
        try:
            await self._save_flash_session(session)
        except Exception as e:
            logger.error(f"保存闪念会话失败: {e}")

    async def _save_flash_session(self, session: FlashSession):
        """
        保存闪念会话，包括处理多媒体上传。
        
        :param session: 要保存的闪念会话对象
        """
        try:
            content_parts = []
            all_tags = set()

            for msg in session.messages:
                if msg.get("type") == "text":
                    content = msg.get("content", "")
                    content_parts.append(content)
                    # 从文本内容中提取标签
                    all_tags.update(re.findall(r'#([^\s#]+)', content))
                elif msg.get("type") in ["image", "file"]:
                    # 上传文件并获取 Markdown 链接
                    markdown_link = await self.file_uploader.upload_and_get_markdown_link(msg)
                    content_parts.append(markdown_link)

            final_content = "\n".join(content_parts)

            # 调用策略创建笔记，标签处理已在策略内部完成
            success = await self.flash_strategy.create(final_content, list(all_tags), self.config)

            if success:
                # 使用响应管理器生成成功消息
                response = self.response_manager.flash_saved(list(all_tags))
                if response:
                    logger.info(f"用户 {session.user_id} 的闪念已保存，响应: {response}")
                else:
                    logger.info(f"用户 {session.user_id} 的闪念已保存 (无响应配置)")
            else:
                logger.error(f"未能为用户 {session.user_id} 保存闪念")

        except Exception as e:
            logger.error(f"保存闪念会话时出错: {e}")