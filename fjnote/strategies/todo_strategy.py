"""
ToDo Note Strategy - ToDo 笔记策略
"""
from typing import List, Dict, Any, Optional

from .base import INoteStrategy
from ..core.models import NoteType
from ..core.exceptions import BlinkoApiException
from astrbot.api import logger

class TodoNoteStrategy(INoteStrategy):
    """ToDo 笔记的具体策略实现"""
    
    async def create(self, content: str, tags: List[str], config: Optional[Dict] = None) -> bool:
        """创建 ToDo 笔记"""
        try:
            config = config or {}
            
            final_content, final_tags = self._prepare_content_and_tags(content, tags, config)

            # 检查内容长度限制
            max_length = config.get("advanced_settings", {}).get("max_content_length", 0)
            if max_length > 0 and len(final_content) > max_length:
                final_content = final_content[:max_length] + "..."
                logger.warning(f"TODO content truncated to {max_length} characters")
            
            # Blinko会从内容中解析标签，所以tags参数可以传空列表
            await self.repository.create_note(final_content, NoteType.TODO.value, [])
            
            if config.get("advanced_settings", {}).get("enable_debug_mode", False):
                logger.info(f"TODO created with content: {final_content}")
            
            return True
        except BlinkoApiException as e:
            logger.error(f"Failed to create TODO: {e}")
            return False
    
    async def search(self, keyword: str) -> List[Dict[str, Any]]:
        """搜索TODO"""
        try:
            all_notes = await self.repository.search_notes(keyword)
            # 过滤出TODO类型并匹配关键词
            todo_notes = [note for note in all_notes 
                         if note.get("type") == NoteType.TODO.value and 
                         keyword.lower() in note.get("content", "").lower()]
            return todo_notes
        except BlinkoApiException as e:
            logger.error(f"Failed to search TODOs: {e}")
            return []