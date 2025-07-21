"""
Note strategies using Strategy pattern
笔记策略，采用策略模式
"""

import re
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional

from ..core.models import NoteType
from ..core.exceptions import BlinkoApiException
from ..services.blinko_api import IBlinkoRepository
from astrbot.api import logger


class INoteStrategy(ABC):
    """笔记策略接口"""
    
    @abstractmethod
    async def create(self, content: str, tags: List[str], config: Optional[Dict] = None) -> bool:
        """创建笔记"""
        pass
    
    @abstractmethod
    async def search(self, keyword: str) -> List[Dict[str, Any]]:
        """搜索笔记"""
        pass


class FlashNoteStrategy(INoteStrategy):
    """闪念策略实现"""
    
    def __init__(self, repository: IBlinkoRepository):
        self.repository = repository
    
    def _extract_tags_from_content(self, content: str) -> List[str]:
        """从内容中提取#标签 - 支持中英文标签"""
        return re.findall(r'#([^\s#]+)', content)
    
    def _prepare_tags(self, content: str, user_tags: List[str], config: Dict) -> List[str]:
        """准备标签列表"""
        all_tags = user_tags.copy()
        
        # 自动提取标签
        if config.get("auto_features", {}).get("auto_extract_tags", True):
            extracted_tags = self._extract_tags_from_content(content)
            all_tags.extend(extracted_tags)
        
        # 添加默认分类
        default_category = config.get("default_categories", {}).get("flash_category", "")
        if default_category and default_category not in all_tags:
            all_tags.append(default_category)
        
        # 去重
        return list(set(all_tags))
    
    async def create(self, content: str, tags: List[str], config: Optional[Dict] = None) -> bool:
        """创建闪念"""
        try:
            config = config or {}
            
            # 检查内容长度限制
            max_length = config.get("advanced_settings", {}).get("max_content_length", 0)
            if max_length > 0 and len(content) > max_length:
                content = content[:max_length] + "..."
                logger.warning(f"Content truncated to {max_length} characters")
            
            # 直接使用传入的内容，不再进行标签处理（已在main.py中处理完毕）
            await self.repository.create_note(content, NoteType.FLASH.value, tags)
            
            if config.get("advanced_settings", {}).get("enable_debug_mode", False):
                logger.info(f"Flash note created with content: {content}")
                logger.info(f"Flash note created with tags: {tags}")
            
            return True
        except BlinkoApiException as e:
            logger.error(f"Failed to create flash note: {e}")
            
            # 自动重试
            if config.get("advanced_settings", {}).get("auto_retry_failed", True):
                try:
                    await self.repository.create_note(content, NoteType.FLASH.value, tags)
                    logger.info("Flash note created on retry")
                    return True
                except Exception as retry_e:
                    logger.error(f"Retry failed: {retry_e}")
            
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
        except BlinkoApiException as e:
            logger.error(f"Failed to search flash notes: {e}")
            return []


class TodoNoteStrategy(INoteStrategy):
    """Todo策略实现"""
    
    def __init__(self, repository: IBlinkoRepository):
        self.repository = repository
    
    def _extract_tags_from_content(self, content: str) -> List[str]:
        """从内容中提取#标签 - 支持中英文标签"""
        return re.findall(r'#([^\s#]+)', content)
    
    def _detect_smart_todo(self, content: str) -> bool:
        """智能检测TODO关键词"""
        todo_keywords = ['完成', '任务', '待办', '提醒', '计划', '安排', '处理', '解决']
        return any(keyword in content for keyword in todo_keywords)
    
    def _prepare_tags(self, content: str, user_tags: List[str], config: Dict) -> List[str]:
        """准备标签列表"""
        all_tags = user_tags.copy()
        
        # 自动提取标签
        if config.get("auto_features", {}).get("auto_extract_tags", True):
            extracted_tags = self._extract_tags_from_content(content)
            all_tags.extend(extracted_tags)
        
        # 添加默认分类
        default_category = config.get("default_categories", {}).get("todo_category", "")
        if default_category and default_category not in all_tags:
            all_tags.append(default_category)
        
        # 去重
        return list(set(all_tags))
    
    async def create(self, content: str, tags: List[str], config: Optional[Dict] = None) -> bool:
        """创建TODO"""
        try:
            config = config or {}
            final_tags = self._prepare_tags(content, tags, config)
            
            # 检查内容长度限制
            max_length = config.get("advanced_settings", {}).get("max_content_length", 0)
            if max_length > 0 and len(content) > max_length:
                content = content[:max_length] + "..."
                logger.warning(f"TODO content truncated to {max_length} characters")
            
            await self.repository.create_note(content, NoteType.TODO.value, final_tags)
            
            if config.get("advanced_settings", {}).get("enable_debug_mode", False):
                logger.info(f"TODO created with tags: {final_tags}")
            
            return True
        except BlinkoApiException as e:
            logger.error(f"Failed to create TODO: {e}")
            
            # 自动重试
            if config.get("advanced_settings", {}).get("auto_retry_failed", True):
                try:
                    await self.repository.create_note(content, NoteType.TODO.value, tags)
                    logger.info("TODO created on retry")
                    return True
                except Exception as retry_e:
                    logger.error(f"Retry failed: {retry_e}")
            
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


class NoteStrategy(INoteStrategy):
    """标准笔记策略实现"""
    
    def __init__(self, repository: IBlinkoRepository):
        self.repository = repository
    
    def _extract_tags_from_content(self, content: str) -> List[str]:
        """从内容中提取#标签 - 支持中英文标签"""
        return re.findall(r'#([^\s#]+)', content)
    
    def _prepare_tags(self, content: str, user_tags: List[str], config: Dict) -> List[str]:
        """准备标签列表"""
        all_tags = user_tags.copy()
        
        # 自动提取标签
        if config.get("auto_features", {}).get("auto_extract_tags", True):
            extracted_tags = self._extract_tags_from_content(content)
            all_tags.extend(extracted_tags)
        
        # 添加默认分类
        default_category = config.get("default_categories", {}).get("note_category", "")
        if default_category and default_category not in all_tags:
            all_tags.append(default_category)
        
        # 去重
        return list(set(all_tags))
    
    async def create(self, content: str, tags: List[str], config: Optional[Dict] = None) -> bool:
        """创建标准笔记"""
        try:
            config = config or {}
            final_tags = self._prepare_tags(content, tags, config)
            
            # 检查内容长度限制
            max_length = config.get("advanced_settings", {}).get("max_content_length", 0)
            if max_length > 0 and len(content) > max_length:
                content = content[:max_length] + "..."
                logger.warning(f"Note content truncated to {max_length} characters")
            
            await self.repository.create_note(content, NoteType.NOTE.value, final_tags)
            
            if config.get("advanced_settings", {}).get("enable_debug_mode", False):
                logger.info(f"Note created with tags: {final_tags}")
            
            return True
        except BlinkoApiException as e:
            logger.error(f"Failed to create note: {e}")
            
            # 自动重试
            if config.get("advanced_settings", {}).get("auto_retry_failed", True):
                try:
                    await self.repository.create_note(content, NoteType.NOTE.value, tags)
                    logger.info("Note created on retry")
                    return True
                except Exception as retry_e:
                    logger.error(f"Retry failed: {retry_e}")
            
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