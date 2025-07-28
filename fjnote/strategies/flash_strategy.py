"""
Flash Note Strategy - 闪念笔记策略
"""
from typing import List, Dict, Any, Optional

from .base import INoteStrategy
from ..core.models import NoteType
from astrbot.api import logger

class FlashNoteStrategy(INoteStrategy):
    """闪念笔记的具体策略实现"""
    
    async def create(self, content: str, tags: List[str], config: Optional[Dict] = None) -> bool:
        """创建闪念笔记"""
        try:
            config = config or {}
            
            final_content, final_tags = self._prepare_content_and_tags(content, tags, config)
            
            # 检查内容长度限制
            max_length = config.get("advanced_settings", {}).get("max_content_length", 0)
            if max_length > 0 and len(final_content) > max_length:
                # 截断时要小心，不要破坏标签
                # 简单处理：直接截断
                final_content = final_content[:max_length] + "..."
                logger.warning(f"Content truncated to {max_length} characters")

            # Blinko会从内容中解析标签，所以tags参数可以传空列表
            await self.repository.create_note(final_content, NoteType.FLASH.value, [])
            
            if config.get("advanced_settings", {}).get("enable_debug_mode", False):
                logger.info(f"Flash note created with content: {final_content}")
            
            return True
        except Exception as e:
            logger.error(f"Failed to create flash note: {e}")
            return False
    
    async def search(self, keyword: str) -> List[Dict[str, Any]]:
        """搜索闪念"""
        try:
            all_notes = await self.repository.search_notes(keyword)
            # 过滤出闪念类型并匹配关键词
            flash_notes = [note for note in all_notes 
                          if note.get("type") == NoteType.FLASH.value and 
                          keyword.lower() in note.get("content", "").lower()]
            return flash_notes
        except Exception as e:
            logger.error(f"Failed to search flash notes: {e}")
            return []