"""
FJNote Main Plugin - 插件主入口
本文件作为插件的入口点，核心职责是：
1. 注册插件信息。
2. 初始化并装配所有核心组件（如API客户端、策略、处理器等）。
3. 监听并分发消息到相应的命令处理器或闪念会话管理器。
4. 管理插件的生命周期，如启动后台任务和执行清理操作。
"""

import asyncio
from datetime import datetime
from typing import Dict, Any

from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.star import Context, Star, register
from astrbot.api import logger, AstrBotConfig
import astrbot.api.message_components as Comp

# 核心服务与组件
from .fjnote.services.blinko_api import BlinkoApiClient
from .fjnote.strategies.flash_strategy import FlashNoteStrategy
from .fjnote.strategies.todo_strategy import TodoNoteStrategy
from .fjnote.strategies.note_strategy import NoteStrategy
from .fjnote.utils.session_manager import SessionManager
from .fjnote.utils.template_renderer import Jinja2TemplateRenderer
from .fjnote.utils.response_manager import ResponseManager
from .fjnote.utils.file_uploader import FileUploader

# 处理器
from .fjnote.handlers.command_factory import CommandFactory
from .fjnote.handlers.flash_session_handler import FlashSessionHandler


@register("FJNote", "FjNote", "为 Blinko 笔记服务开发的插件，提供闪念记录和 ToDo 管理功能", "1.4.0", "https://github.com/FjNote/FjNoteBot")
class FJNotePlugin(Star):
    """
    FJNote 主插件类
    作为插件的协调中心，采用依赖注入的方式将各个模块组合在一起。
    - 使用工厂模式（CommandFactory）创建命令处理器。
    - 使用策略模式（NoteStrategy）处理不同类型的笔记。
    - 使用观察者模式（SessionManager/FlashSessionHandler）处理闪念会话超时。
    """
    
    def __init__(self, context: Context, config: AstrBotConfig):
        super().__init__(context)
        self.config = config
        
        # 初始化所有核心组件
        self._init_components()
        
        # 启动后台任务，用于清理超时的会话计时器
        asyncio.create_task(self._start_session_monitor())
    
    def _init_components(self):
        """
        初始化并装配所有核心组件。
        这种方式使得各个组件的职责单一，易于测试和替换。
        """
        # API 客户端（仓储模式）
        self.api_client = BlinkoApiClient(
            base_url=self.config.get("blinko_base_url", "http://localhost:1111"),
            token=self.config.get("blinko_token", "")
        )
        
        # 文件上传工具
        self.file_uploader = FileUploader(self.api_client)
        
        # 笔记策略（策略模式）
        self.flash_strategy = FlashNoteStrategy(self.api_client)
        self.todo_strategy = TodoNoteStrategy(self.api_client)
        self.note_strategy = NoteStrategy(self.api_client)
        
        # 模板渲染器
        self.template_renderer = Jinja2TemplateRenderer(dict(self.config))
        
        # 响应管理器
        self.response_manager = ResponseManager(dict(self.config))
        
        # 闪念会话处理器（观察者）
        self.flash_session_handler = FlashSessionHandler(
            self.flash_strategy,
            self.file_uploader,
            self.response_manager,
            dict(self.config)
        )
        
        # 会话管理器（被观察者）
        self.session_manager = SessionManager(
            timeout_seconds=self.config.get("flash_session_timeout", 30)
        )
        self.session_manager.add_observer(self.flash_session_handler)  # 注册闪念处理器为观察者
        
        # 命令工厂（工厂模式）
        self.command_factory = CommandFactory(self)
    
    async def _start_session_monitor(self):
        """启动会话监控任务，定期清理已完成的计时器任务以释放资源。"""
        while True:
            try:
                await asyncio.sleep(1)
                await self.session_manager.cleanup_finished_timers()
            except Exception as e:
                logger.error(f"会话监控任务出错: {e}")
    
    async def _handle_multimedia_message(self, event: AstrMessageEvent) -> Dict[str, Any]:
        """
        解析消息事件，提取文本和多媒体信息。
        :return: 一个包含消息类型、内容、URL等信息的字典。
        """
        # 基础消息数据包含文本内容
        message_data = {
            "type": "text",
            "content": event.message_str,
            "timestamp": datetime.now().isoformat()
        }
        
        # 检查并附加多媒体信息
        for component in event.message_obj.message:
            if isinstance(component, Comp.Image):
                message_data.update({
                    "type": "image",
                    "url": component.url if hasattr(component, 'url') else component.file,
                    "filename": f"image_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg",
                })
            elif hasattr(component, 'file') and hasattr(component, 'name'):
                message_data.update({
                    "type": "file",
                    "url": component.file, # 假设文件组件也有一个可访问的路径或URL
                    "filename": component.name,
                })
        
        return message_data
    
    def _should_record_flash(self, content: str) -> bool:
        """
        检查是否应该记录闪念
        根据配置过滤短内容和指定前缀
        """
        # 获取过滤配置
        filters_config = self.config.get("flash_filters", {})
        min_length = filters_config.get("min_content_length", 5)
        ignore_prefixes_str = filters_config.get("ignore_prefixes", "/t")
        
        # 解析忽略前缀列表
        ignore_prefixes = []
        if ignore_prefixes_str:
            ignore_prefixes = [prefix.strip() for prefix in ignore_prefixes_str.split(",") if prefix.strip()]
        
        # 检查内容长度
        if len(content.strip()) < min_length:
            return False
        
        # 检查是否以忽略前缀开头
        content_lower = content.strip().lower()
        for prefix in ignore_prefixes:
            prefix_lower = prefix.lower()
            # 精确匹配前缀：要么是完整匹配，要么后面跟着空格
            if content_lower.startswith(prefix_lower):
                # 如果前缀后面是空格或者就是完整的前缀，则匹配
                if len(content_lower) == len(prefix_lower) or content_lower[len(prefix_lower)] == ' ':
                    return False
        
        return True
    
    @filter.event_message_type(filter.EventMessageType.PRIVATE_MESSAGE)
    async def on_private_message(self, event: AstrMessageEvent):
        """
        处理私聊消息
        支持命令处理和闪念记录
        """
        async for result in self._handle_message(event):
            yield result
    
    @filter.event_message_type(filter.EventMessageType.GROUP_MESSAGE)
    async def on_group_message(self, event: AstrMessageEvent):
        """
        处理群聊消息
        支持命令处理和闪念记录
        """
        async for result in self._handle_message(event):
            yield result
    
    async def _handle_message(self, event: AstrMessageEvent):
        """
        统一的消息处理方法
        """
        user_id = event.get_sender_id()
        message_text = event.message_str.strip()
        
        # 处理命令
        if message_text.startswith('#'):
            command_parts = message_text[1:].split()
            if command_parts:
                command = command_parts[0].lower()
                args = command_parts[1:]
                
                handler = self.command_factory.get_handler(command)
                if handler:
                    try:
                        result = await handler.handle(event, args)
                        if result:  # 只有当有响应内容时才返回
                            yield result
                        return
                    except Exception as e:
                        logger.error(f"Command handler error: {e}")
                        error_response = self.response_manager.error_general(str(e))
                        if error_response:
                            yield event.plain_result(error_response)
                        return
                else:
                    unknown_response = self.response_manager.command_unknown(command)
                    if unknown_response:
                        yield event.plain_result(unknown_response)
                    return
        
        # 处理闪念记录
        try:
            # 闪念过滤检查
            if not self._should_record_flash(message_text):
                return  # 不记录闪念，直接返回
            
            message_data = await self._handle_multimedia_message(event)
            
            existing_session = self.session_manager.sessions.get(user_id)
            if existing_session:
                # 添加到现有会话
                await self.session_manager.add_message(user_id, message_data)
                add_response = self.response_manager.flash_add()
                if add_response:
                    yield event.plain_result(add_response)
            else:
                # 开始新会话
                await self.session_manager.start_session(user_id, message_data)
                timeout_seconds = self.config.get('flash_session_timeout', 30)
                start_response = self.response_manager.flash_start(timeout_seconds)
                if start_response:
                    yield event.plain_result(start_response)
            
        except Exception as e:
            logger.error(f"Flash note processing error: {e}")
            error_response = self.response_manager.error_general("闪念记录失败")
            if error_response:
                yield event.plain_result(error_response)
    
    async def terminate(self):
        """
        插件终止时的清理工作
        保存所有未完成的闪念会话
        """
        try:
            # 保存所有活跃会话
            for user_id in list(self.session_manager.sessions.keys()):
                session = await self.session_manager.cancel_session(user_id)
                if session:
                    await self._save_flash_session(session)
            
            # 关闭 API 客户端
            await self.api_client.close()
            
            logger.info("FJNote plugin terminated successfully")
            
        except Exception as e:
            logger.error(f"Error during plugin termination: {e}")