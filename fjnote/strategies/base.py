"""
Base Note Strategy - 笔记策略基类
本模块定义了所有笔记策略的抽象基类 INoteStrategy。
"""

import re
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional

from ..services.blinko_api import IBlinkoRepository

class INoteStrategy(ABC):
    """
    笔记策略接口
    定义了所有笔记处理策略的公共行为。
    """
    
    def __init__(self, repository: IBlinkoRepository):
        """
        初始化策略。
        
        :param repository: 一个实现了 IBlinkoRepository 接口的数据仓储实例。
        """
        self.repository = repository

    def _prepare_content_and_tags(self, content: str, tags: List[str], config: Dict) -> (str, List[str]):
        """
        准备最终要发送给 Blinko 的内容和标签。
        核心逻辑：Blinko 服务端会从笔记内容中自动解析 #标签。此方法确保所有标签（无论是来自用户输入还是配置的默认标签）都包含在最终的内容字符串中。
        
        :param content: 原始笔记内容。
        :param tags: 从外部传入的标签列表。
        :param config: 插件配置字典。
        :return: 一个元组，包含处理后的内容字符串和所有标签的集合列表。
        """
        # 1. 从内容中提取已有的标签
        content_tags = set(re.findall(r'#([^\s#]+)', content))
        
        # 2. 合并所有标签源
        all_tags = set(tags) | content_tags
        
        # 3. 根据策略类型添加默认分类标签
        note_type_name = self.__class__.__name__.replace("NoteStrategy", "").lower()
        default_category = config.get("default_categories", {}).get(f"{note_type_name}_category", "")
        if default_category:
            all_tags.add(default_category)
            
        # 4. 确保所有标签都存在于内容中，以便Blinko解析
        final_content = content
        missing_tags = all_tags - content_tags
        if missing_tags:
            # 在末尾添加缺失的标签，并确保前面有空行以符合Blinko的解析规则
            final_content += "\n\n" + " ".join(f"#{tag}" for tag in sorted(list(missing_tags)))
            
        return final_content.strip(), list(all_tags)

    @abstractmethod
    async def create(self, content: str, tags: List[str], config: Optional[Dict] = None) -> bool:
        """
        创建笔记的抽象方法。
        
        :param content: 笔记内容。
        :param tags: 标签列表。
        :param config: 插件配置。
        :return: 如果创建成功则返回 True，否则返回 False。
        """
        pass
    
    @abstractmethod
    async def search(self, keyword: str) -> List[Dict[str, Any]]:
        """
        搜索笔记的抽象方法。
        
        :param keyword: 搜索关键词。
        :return: 匹配的笔记列表。
        """
        pass