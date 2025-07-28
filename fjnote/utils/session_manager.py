"""
Session Management Utilities - 会话管理工具
本模块采用观察者模式（Observer Pattern）来管理闪念会话。
- SessionManager: 作为被观察者（Subject），负责管理所有用户的闪念会话，并在会话超时时通知观察者。
- ISessionObserver: 定义了观察者（Observer）必须实现的接口。
"""

import asyncio
import re
from datetime import datetime
from typing import Dict, Optional, List
from abc import ABC, abstractmethod

from ..core.models import FlashSession
from astrbot.api import logger


class ISessionObserver(ABC):
    """
    会话观察者接口
    任何希望在会话超时时收到通知的类都应实现此接口。
    """
    
    @abstractmethod
    async def on_session_timeout(self, session: FlashSession):
        """
        当会话超时时由 SessionManager 调用的回调方法。
        
        :param session: 已超时的会话对象。
        """
        pass


class SessionManager:
    """
    闪念会话管理器（被观察者）
    负责创建、更新、取消和监控所有用户的闪念会话。
    """
    
    def __init__(self, timeout_seconds: int = 30):
        """
        初始化会话管理器。
        
        :param timeout_seconds: 闪念会话的超时时间（秒）。
        """
        self.sessions: Dict[str, FlashSession] = {}
        self.timeout_seconds = timeout_seconds
        self.observers: List[ISessionObserver] = []
    
    def add_observer(self, observer: ISessionObserver):
        """添加一个观察者。"""
        if observer not in self.observers:
            self.observers.append(observer)
    
    def remove_observer(self, observer: ISessionObserver):
        """移除一个观察者。"""
        if observer in self.observers:
            self.observers.remove(observer)
    
    async def _notify_timeout(self, session: FlashSession):
        """通知所有观察者会话已超时。"""
        for observer in self.observers:
            try:
                await observer.on_session_timeout(session)
            except Exception as e:
                logger.error(f"会话观察者在处理超时事件时出错: {e}")
    
    async def start_session(self, user_id: str, message_data: Dict) -> FlashSession:
        """
        为指定用户开始一个新的闪念会话。
        如果用户已有会话，将先取消旧会话。
        
        :param user_id: 用户的唯一标识符。
        :param message_data: 会话的第一条消息数据。
        :return: 新创建的会话对象。
        """
        if user_id in self.sessions:
            await self.cancel_session(user_id)
        
        session = FlashSession(
            user_id=user_id,
            messages=[message_data],
            tags=[],
            created_at=datetime.now()
        )
        
        self.sessions[user_id] = session
        session.timer_task = asyncio.create_task(self._session_timeout_task(user_id))
        return session
    
    async def add_message(self, user_id: str, message_data: Dict) -> Optional[FlashSession]:
        """
        向现有会话中添加一条消息，并重置超时计时器。
        
        :param user_id: 用户的唯一标识符。
        :param message_data: 要添加的消息数据。
        :return: 更新后的会话对象，如果会话不存在则返回 None。
        """
        session = self.sessions.get(user_id)
        if not session:
            return None
        
        session.messages.append(message_data)
        
        # 重置计时器
        if session.timer_task:
            session.timer_task.cancel()
        session.timer_task = asyncio.create_task(self._session_timeout_task(user_id))
        
        return session
    
    async def cancel_session(self, user_id: str) -> Optional[FlashSession]:
        """
        手动取消一个用户的会话。
        
        :param user_id: 用户的唯一标识符。
        :return: 被取消的会话对象，如果会话不存在则返回 None。
        """
        session = self.sessions.pop(user_id, None)
        if session and session.timer_task:
            session.timer_task.cancel()
        return session
    
    async def _session_timeout_task(self, user_id: str):
        """
        用于监控单个会话超时的异步任务。
        任务完成后，会通知观察者。
        """
        try:
            await asyncio.sleep(self.timeout_seconds)
            session = self.sessions.pop(user_id, None)
            if session:
                await self._notify_timeout(session)
        except asyncio.CancelledError:
            # 会话被重置或取消，这是正常行为，无需处理。
            pass
        except Exception as e:
            logger.error(f"会话超时任务出错 (用户: {user_id}): {e}")

    async def cleanup_finished_timers(self):
        """清理已结束的会话计时器任务，释放资源。"""
        for user_id in list(self.sessions.keys()):
            session = self.sessions.get(user_id)
            if session and session.timer_task and session.timer_task.done():
                # 通常，超时的任务会自己移除会话，但为防止意外情况，这里也进行清理
                self.sessions.pop(user_id, None)
    
    def extract_tags(self, text: str) -> List[str]:
        """提取标签 - 支持中英文标签"""
        # 修改正则表达式以支持中文标签
        return re.findall(r'#([^\s#]+)', text)
    
    def remove_tags(self, text: str) -> str:
        """移除标签"""
        return re.sub(r'#[^\s#]+', '', text).strip()