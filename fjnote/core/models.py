"""
Core domain models and enums
核心领域模型和枚举
"""

from datetime import datetime
from dataclasses import dataclass
from enum import Enum
from typing import List, Optional, Any, Dict
import asyncio


class NoteType(Enum):
    """笔记类型枚举 - 对应Blinko的完整类型"""
    FLASH = 0   # 闪念/普通笔记
    NOTE = 1    # 标准笔记
    TODO = 2    # 待办事项


@dataclass
class FlashSession:
    """闪念会话数据模型"""
    user_id: str
    messages: List[Dict[str, Any]]
    tags: List[str]
    created_at: datetime
    timer_task: Optional[asyncio.Task] = None


@dataclass 
class TodoItem:
    """待办事项数据模型"""
    id: Optional[int]
    content: str
    category: str
    deadline: Optional[str]
    completed: bool = False
    created_at: Optional[str] = None


@dataclass
class NoteItem:
    """标准笔记数据模型"""
    id: Optional[int]
    content: str
    category: str
    tags: List[str]
    created_at: Optional[str] = None
    attachments: List[str] = None


@dataclass
class NoteSearchResult:
    """笔记搜索结果模型"""
    id: int
    content: str
    note_type: int
    tags: List[str]
    created_at: str