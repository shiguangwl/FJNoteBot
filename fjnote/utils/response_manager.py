"""
Response Manager for FJNote Plugin
响应管理器，支持自定义响应内容和占位符替换
"""

from typing import Dict, Any, Optional


class ResponseManager:
    """响应管理器 - 处理自定义响应内容"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self._response_config = self.config.get("ui_preferences", {}).get("custom_responses", {})
    
    def get_response(self, response_type: str, **kwargs) -> Optional[str]:
        """
        获取自定义响应内容
        
        Args:
            response_type: 响应类型
            **kwargs: 用于占位符替换的参数
        
        Returns:
            格式化后的响应内容，如果配置为空则返回 None
        """
        template = self._response_config.get(response_type)
        
        # 如果模板为空或者未配置，返回 None（不响应）
        if not template or not template.strip():
            return None
        
        try:
            # 替换占位符
            return template.format(**kwargs)
        except (KeyError, ValueError) as e:
            # 如果占位符替换失败，返回原始模板
            return template
    
    def flash_start(self, timeout: int) -> Optional[str]:
        """闪念开始响应"""
        return self.get_response("flash_start", timeout=timeout)
    
    def flash_add(self) -> Optional[str]:
        """闪念添加响应"""
        return self.get_response("flash_add")
    
    def flash_saved(self, tags: list = None) -> Optional[str]:
        """闪念保存成功响应"""
        if tags:
            tags_text = f"，并添加了标签：【{', '.join(tags)}】"
        else:
            tags_text = ""
        return self.get_response("flash_saved", tags=tags_text)
    
    def todo_created(self, content: str, category: str = None, deadline: str = None) -> Optional[str]:
        """TODO创建成功响应"""
        return self.get_response("todo_created", 
                                content=content, 
                                category=category or "", 
                                deadline=deadline or "")
    
    def todo_completed(self, todo_id: str, content: str) -> Optional[str]:
        """TODO完成响应"""
        return self.get_response("todo_completed", id=todo_id, content=content)
    
    def note_created(self, content: str, category: str = None) -> Optional[str]:
        """笔记创建成功响应"""
        return self.get_response("note_created", 
                                content=content[:50] + "..." if len(content) > 50 else content, 
                                category=category or "")
    
    def item_deleted(self, item_id: str, item_type: str) -> Optional[str]:
        """项目删除成功响应"""
        type_map = {
            "todo": "待办",
            "note": "笔记", 
            "flash": "闪念"
        }
        return self.get_response("item_deleted", 
                                id=item_id, 
                                type=type_map.get(item_type, item_type))
    
    def error_general(self, error: str) -> Optional[str]:
        """一般错误响应"""
        return self.get_response("error_general", error=error)
    
    def error_not_found(self, item_id: str, item_type: str) -> Optional[str]:
        """未找到项目错误响应"""
        type_map = {
            "todo": "待办",
            "note": "笔记",
            "flash": "闪念"
        }
        return self.get_response("error_not_found", 
                                id=item_id, 
                                type=type_map.get(item_type, item_type))
    
    def command_unknown(self, command: str) -> Optional[str]:
        """未知命令响应"""
        return self.get_response("command_unknown", command=command)
    
    def should_respond(self, response_type: str) -> bool:
        """检查是否应该响应（配置不为空）"""
        template = self._response_config.get(response_type)
        return bool(template and template.strip())