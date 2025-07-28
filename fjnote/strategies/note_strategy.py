"""
Standard Note Strategy - 标准笔记策略
"""
from typing import List, Dict, Any, Optional

from .base import INoteStrategy
from ..core.models import NoteType
from ..core.exceptions import BlinkoApiException
from astrbot.api import logger

class NoteStrategy(INoteStrategy):
    """标准笔记的具体策略实现"""
    
    async def create(self, content: str, tags: List[str], config: Optional[Dict] = None) -> bool:
        """创建标准笔记"""
        try:
            config = config or {}
            
            final_content, final_tags = self._prepare_content_and_tags(content, tags, config)

            # 检查内容长度限制
            max_length = config.get("advanced_settings", {}).get("max_content_length", 0)
            if max_length > 0 and len(final_content) > max_length:
                final_content = final_content[:max_length] + "..."
                logger.warning(f"Note content truncated to {max_length} characters")
            
            # Blinko会从内容中解析标签，所以tags参数可以传空列表
            await self.repository.create_note(final_content, NoteType.NOTE.value, [])
            
            if config.get("advanced_settings", {}).get("enable_debug_mode", False):
                logger.info(f"Note created with content: {final_content}")
            
            return True
        except BlinkoApiException as e:
            logger.error(f"Failed to create note: {e}")
            return False
    
    async def search(self, keyword: str) -> List[Dict[str, Any]]:
        """搜索标准笔记"""
        try:
            all_notes = await self.repository.search_notes(keyword)
            # 过滤出标准笔记类型并匹配关键词
            notes = [note for note in all_notes 
                    if note.get("type") == NoteType.NOTE.value and 
                    keyword.lower() in note.get("content", "").lower()]
            return notes
        except BlinkoApiException as e:
            logger.error(f"Failed to search notes: {e}")
            return []