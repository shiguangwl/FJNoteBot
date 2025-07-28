"""
Core Domain Models and Enums - 核心领域模型与枚举
本模块定义了插件业务逻辑中使用的核心数据结构。
使用 dataclasses 来创建简洁、类型安全的数据类。
"""

from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional, Any, Dict
import asyncio


class NoteType(Enum):
    """
    笔记类型枚举
    与 Blinko API 中的笔记类型定义保持一致。
    """
    FLASH = 0   # 闪念/普通笔记
    NOTE = 1    # 标准笔记
    TODO = 2    # 待办事项


@dataclass
class FlashSession:
    """
    闪念会话数据模型
    用于在内存中临时存储一个用户的连续闪念消息。
    """
    user_id: str
    messages: List[Dict[str, Any]]
    tags: List[str]
    created_at: datetime
    timer_task: Optional[asyncio.Task] = None


@dataclass 
class TodoItem:
    """
    待办事项数据模型
    用于在业务逻辑和模板渲染中表示一个待办事项。
    """
    id: Optional[int]           # 在列表中的临时显示ID (从1开始)
    note_id: int                # Blinko中笔记的真实、唯一ID
    content: str                # 待办内容
    category: str               # 所属分类
    deadline: Optional[str] = None
    completed: bool = False
    created_at: Optional[str] = None


@dataclass
class NoteItem:
    """
    标准笔记数据模型
    用于表示一个标准的、非待办的笔记。
    """
    id: Optional[int]
    content: str
    category: str
    tags: List[str] = field(default_factory=list)
    created_at: Optional[str] = None
    attachments: List[str] = field(default_factory=list)


@dataclass
class NoteSearchResult:
    """
    笔记搜索结果模型
    用于统一表示不同类型笔记的搜索结果。
    """
    id: int
    content: str
    note_type: int
    tags: List[str]
    created_at: str
