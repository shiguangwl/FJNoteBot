"""
FJNote Main Plugin
高质量的 Blinko 笔记助手插件主文件
采用多种设计模式确保代码的可扩展性和可维护性
"""

import asyncio
import re
from datetime import datetime
from typing import Dict, List, Any

from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.star import Context, Star, register
from astrbot.api import logger, AstrBotConfig
import astrbot.api.message_components as Comp

from .fjnote.core.models import FlashSession
from .fjnote.core.exceptions import FJNoteException
from .fjnote.services.blinko_api import BlinkoApiClient
from .fjnote.strategies.note_strategies import FlashNoteStrategy, TodoNoteStrategy, NoteStrategy
from .fjnote.utils.session_manager import SessionManager, ISessionObserver
from .fjnote.utils.template_renderer import Jinja2TemplateRenderer
from .fjnote.utils.response_manager import ResponseManager
from .fjnote.handlers.command_factory import CommandFactory


@register("FJNote", "FjNote", "为 Blinko 笔记服务开发的插件，提供闪念记录和 ToDo 管理功能", "1.3.2", "https://github.com/FjNote/FjNoteBot")
class FJNotePlugin(Star):
    """
    FJNote 主插件类
    采用观察者模式监听会话超时，策略模式处理不同类型笔记，工厂模式创建命令处理器
    """
    
    def __init__(self, context: Context, config: AstrBotConfig):
        super().__init__(context)
        self.config = config
        
        # 初始化核心组件
        self._init_components()
        
        # 启动会话监控任务
        asyncio.create_task(self._start_session_monitor())
    
    def _init_components(self):
        """初始化核心组件"""
        # API 客户端（仓储模式）
        self.api_client = BlinkoApiClient(
            base_url=self.config.get("blinko_base_url", "http://localhost:1111"),
            token=self.config.get("blinko_token", "")
        )
        
        # 笔记策略（策略模式）
        self.flash_strategy = FlashNoteStrategy(self.api_client)
        self.todo_strategy = TodoNoteStrategy(self.api_client)
        self.note_strategy = NoteStrategy(self.api_client)
        
        # 模板渲染器（模板方法模式）- 传入配置支持渲染质量设置
        self.template_renderer = Jinja2TemplateRenderer(dict(self.config))
        
        # 响应管理器（支持自定义响应内容）
        self.response_manager = ResponseManager(dict(self.config))
        
        # 会话管理器（观察者模式）
        self.session_manager = SessionManager(
            timeout_seconds=self.config.get("flash_session_timeout", 30)
        )
        self.session_manager.add_observer(self)  # 注册为观察者
        
        # 命令工厂（工厂模式）
        self.command_factory = CommandFactory(self)
    
    async def _start_session_monitor(self):
        """启动会话监控任务"""
        while True:
            try:
                await asyncio.sleep(1)
                # 清理已完成的计时器任务
                for user_id in list(self.session_manager.sessions.keys()):
                    session = self.session_manager.sessions.get(user_id)
                    if session and session.timer_task and session.timer_task.done():
                        # 会话超时已由观察者模式处理，这里只需清理
                        await self.session_manager.cancel_session(user_id)
            except Exception as e:
                logger.error(f"Session monitor error: {e}")
    
    async def on_session_timeout(self, session: FlashSession):
        """
        会话超时回调（观察者模式）
        当会话超时时自动保存闪念
        """
        try:
            await self._save_flash_session(session)
        except Exception as e:
            logger.error(f"Failed to save flash session: {e}")
    
    async def _save_flash_session(self, session: FlashSession):
        """保存闪念会话"""
        try:
            # 合并消息内容
            content_parts = []
            all_tags = set()
            
            for msg in session.messages:
                if msg.get("type") == "text":
                    content = msg["content"]
                    content_parts.append(content)
                    all_tags.update(self.session_manager.extract_tags(content))
                elif msg.get("type") == "image":
                    content_parts.append(f"[图片: {msg.get('filename', 'image')}]")
                elif msg.get("type") == "file":
                    content_parts.append(f"[文件: {msg.get('filename', 'file')}]")
            
            # 生成最终内容 - 保持原始内容，不移除标签
            final_content = "\n".join(content_parts)
            
            # 如果有提取到的标签但内容中缺少，则添加（前面加空行以确保Blinko能识别）
            if all_tags:
                existing_tags_in_content = self.session_manager.extract_tags(final_content)
                missing_tags = [tag for tag in all_tags if tag not in existing_tags_in_content]
                if missing_tags:
                    final_content += "\n\n" + " ".join(f"#{tag}" for tag in missing_tags)
            
            # 如果内容中已有标签，确保标签前有空行以便Blinko识别
            if all_tags:
                # 检查最后一个标签前是否有空行，如果没有则添加
                lines = final_content.split('\n')
                
                # 找到包含标签的行
                for i, line in enumerate(lines):
                    if '#' in line:
                        # 找到第一个标签的位置
                        tag_match = re.search(r'#[^\s#]+', line)
                        if tag_match:
                            tag_start = tag_match.start()
                            # 如果标签前有非空白字符，需要重新格式化
                            if tag_start > 0 and line[:tag_start].strip():
                                content_before_tags = line[:tag_start].rstrip()
                                tags_part = line[tag_start:]
                                
                                # 重新构造内容：内容 + 空行 + 标签
                                new_lines = lines[:i] + [content_before_tags, "", tags_part] + lines[i+1:]
                                final_content = '\n'.join(new_lines)
                                break
            
            # 保存闪念（直接传递包含标签的完整内容）
            success = await self.flash_strategy.create(final_content, list(all_tags), dict(self.config))
            
            if success:
                # 使用自定义响应消息
                response = self.response_manager.flash_saved(list(all_tags))
                if response:
                    logger.info(f"Flash note saved for user {session.user_id}, response: {response}")
                else:
                    logger.info(f"Flash note saved for user {session.user_id} (no response configured)")
            else:
                logger.error(f"Failed to save flash note for user {session.user_id}")
                
        except Exception as e:
            logger.error(f"Error saving flash session: {e}")
    
    async def _handle_multimedia_message(self, event: AstrMessageEvent) -> Dict[str, Any]:
        """处理多媒体消息"""
        message_data = {
            "type": "text",
            "content": event.message_str,
            "timestamp": datetime.now().isoformat()
        }
        
        # 检查消息组件中的多媒体内容
        for component in event.message_obj.message:
            if isinstance(component, Comp.Image):
                message_data = {
                    "type": "image",
                    "content": "[图片]",
                    "url": component.url if hasattr(component, 'url') else component.file,
                    "filename": f"image_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg",
                    "timestamp": datetime.now().isoformat()
                }
                break
            elif hasattr(component, 'file') and hasattr(component, 'name'):
                # 文件消息
                message_data = {
                    "type": "file",
                    "content": f"[文件: {component.name}]",
                    "filename": component.name,
                    "timestamp": datetime.now().isoformat()
                }
                break
        
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