"""
Session management utilities
会话管理工具，采用观察者模式
"""

import asyncio
import re
from datetime import datetime
from typing import Dict, Optional, List
from abc import ABC, abstractmethod

from ..core.models import FlashSession
from ..core.exceptions import SessionException
from astrbot.api import logger


class ISessionObserver(ABC):
    """会话观察者接口"""
    
    @abstractmethod
    async def on_session_timeout(self, session: FlashSession):
        """会话超时回调"""
        pass


class SessionManager:
    """会话管理器"""
    
    def __init__(self, timeout_seconds: int = 30):
        self.sessions: Dict[str, FlashSession] = {}
        self.timeout_seconds = timeout_seconds
        self.observers: List[ISessionObserver] = []
    
    def add_observer(self, observer: ISessionObserver):
        """添加观察者"""
        self.observers.append(observer)
    
    def remove_observer(self, observer: ISessionObserver):
        """移除观察者"""
        if observer in self.observers:
            self.observers.remove(observer)
    
    async def _notify_timeout(self, session: FlashSession):
        """通知观察者会话超时"""
        for observer in self.observers:
            try:
                await observer.on_session_timeout(session)
            except Exception as e:
                logger.error(f"Session observer error: {e}")
    
    async def start_session(self, user_id: str, message_data: Dict) -> FlashSession:
        """开始新会话"""
        if user_id in self.sessions:
            await self.cancel_session(user_id)
        
        session = FlashSession(
            user_id=user_id,
            messages=[message_data],
            tags=[],
            created_at=datetime.now()
        )
        
        self.sessions[user_id] = session
        session.timer_task = asyncio.create_task(self._session_timeout(user_id))
        return session
    
    async def add_message(self, user_id: str, message_data: Dict) -> Optional[FlashSession]:
        """添加消息到现有会话"""
        if user_id not in self.sessions:
            return None
        
        session = self.sessions[user_id]
        session.messages.append(message_data)
        
        # 重置计时器
        if session.timer_task:
            session.timer_task.cancel()
        session.timer_task = asyncio.create_task(self._session_timeout(user_id))
        
        return session
    
    async def cancel_session(self, user_id: str) -> Optional[FlashSession]:
        """取消会话"""
        if user_id not in self.sessions:
            return None
        
        session = self.sessions.pop(user_id)
        if session.timer_task:
            session.timer_task.cancel()
        return session
    
    async def _session_timeout(self, user_id: str):
        """会话超时处理"""
        try:
            await asyncio.sleep(self.timeout_seconds)
            if user_id in self.sessions:
                session = self.sessions.pop(user_id)
                await self._notify_timeout(session)
        except asyncio.CancelledError:
            # 会话被取消，正常行为
            pass
        except Exception as e:
            logger.error(f"Session timeout error: {e}")
    
    def extract_tags(self, text: str) -> List[str]:
        """提取标签 - 支持中英文标签"""
        # 修改正则表达式以支持中文标签
        return re.findall(r'#([^\s#]+)', text)
    
    def remove_tags(self, text: str) -> str:
        """移除标签"""
        return re.sub(r'#[^\s#]+', '', text).strip()