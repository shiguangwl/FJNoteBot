"""
Template rendering utilities
模板渲染工具，采用模板方法模式
"""

from abc import ABC, abstractmethod
from typing import Dict, Any
from jinja2 import Environment, DictLoader


class ITemplateRenderer(ABC):
    """模板渲染器接口"""
    
    @abstractmethod
    async def render(self, template_name: str, data: Dict[str, Any]) -> str:
        """渲染模板"""
        pass


class Jinja2TemplateRenderer(ITemplateRenderer):
    """Jinja2 模板渲染器实现"""
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.templates = {
            'todo_list': self._get_todo_list_template(),
            'note_list': self._get_note_list_template(),
            'search_results': self._get_search_results_template(),
            'help': self._get_help_template(),
            'tags_list': self._get_tags_list_template()
        }
        self._load_custom_templates()
        self.env = Environment(loader=DictLoader(self.templates))
    
    def _load_custom_templates(self):
        """加载自定义模板"""
        custom_config = self.config.get("ui_preferences", {}).get("custom_templates", {})
        if custom_config.get("enable_custom", False):
            # 加载自定义模板
            if custom_config.get("todo_list_template"):
                self.templates['todo_list'] = custom_config["todo_list_template"]
            if custom_config.get("note_list_template"):
                self.templates['note_list'] = custom_config["note_list_template"]
            if custom_config.get("search_results_template"):
                self.templates['search_results'] = custom_config["search_results_template"]
    
    def _get_base_style(self) -> str:
        """获取基础样式 - 专为移动端优化"""
        font_size = self.config.get("ui_preferences", {}).get("font_size", 24)  # 增大默认字体
        compact_mode = self.config.get("ui_preferences", {}).get("compact_mode", True)  # 默认紧凑模式
        
        # 极致紧凑设计，移除所有不必要的空白
        padding = "6px" if compact_mode else "8px"
        line_height = "1.1" if compact_mode else "1.2"  # 更紧凑的行高
        
        return f"""
        font-family: 'Microsoft YaHei', 'PingFang SC', 'Helvetica Neue', Arial, sans-serif; 
        font-size: {font_size}px; 
        line-height: {line_height}; 
        padding: {padding}; 
        margin: 0;
        border-radius: 6px; 
        box-shadow: 0 2px 8px rgba(0,0,0,0.15);
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        width: 100%;
        box-sizing: border-box;
        min-height: auto;
        """
    
    def _get_todo_list_template(self) -> str:
        """获取极致紧凑的TODO列表模板 - 专为移动端优化"""
        font_size = self.config.get("ui_preferences", {}).get("font_size", 24)  # 增大默认字体
        compact_mode = self.config.get("ui_preferences", {}).get("compact_mode", True)  # 默认紧凑
        show_timestamps = self.config.get("ui_preferences", {}).get("show_timestamps", False)  # 默认隐藏时间戳
        
        # 极致紧凑的间距设计
        title_size = font_size + 2  # 标题稍大一点
        item_padding = "3px 6px"  # 固定紧凑内边距
        item_margin = "1px 0"     # 极小的外边距
        section_margin = "4px 0 2px 0"  # 分类间距
        
        return f'''
<div style="{self._get_base_style()}">
    <div style="text-align: center; margin: 0 0 6px 0; font-size: {title_size}px; font-weight: 700;">
        📝 ToDo{{{{ " - " + category if category else "" }}}}
    </div>
    {{% if todos %}}
        {{% for category_name, items in todos.items() %}}
            {{% if category_name and category_name != "默认" %}}
                <div style="margin: {section_margin}; color: #ffd700; font-size: {font_size - 2}px; font-weight: 600; border-bottom: 1px solid #ffd700; padding-bottom: 1px;">
                    📂 {{{{ category_name }}}}
                </div>
            {{% endif %}}
            {{% for todo in items %}}
                <div style="margin: {item_margin}; padding: {item_padding}; background: rgba(255,255,255,0.15); border-radius: 3px; border-left: 2px solid #ffd700;">
                    <div style="display: flex; align-items: center; justify-content: space-between;">
                        <div style="flex: 1; display: flex; align-items: center;">
                            <span style="color: #ffd700; margin-right: 4px; font-size: {font_size - 2}px; font-weight: 600;">[{{{{ todo.id }}}}]</span>
                            <span style="margin-right: 4px; font-size: {font_size + 2}px;">{{{{ "☑️" if todo.completed else "☐" }}}}</span>
                            <span style="{{{{ 'text-decoration: line-through; opacity: 0.7;' if todo.completed else '' }}}} font-size: {font_size}px; word-break: break-all;">{{{{ todo.content }}}}</span>
                        </div>
                        {{% if todo.deadline or (show_timestamps and todo.created_at) %}}
                            <div style="font-size: {font_size - 4}px; color: #ddd; text-align: right; margin-left: 6px; flex-shrink: 0;">
                                {{% if todo.deadline %}}
                                    <div style="color: #ffb3ba; font-weight: 600;">⏰{{{{ todo.deadline }}}}</div>
                                {{% endif %}}
                                {{% if show_timestamps and todo.created_at %}}
                                    <div>{{{{ todo.created_at }}}}</div>
                                {{% endif %}}
                            </div>
                        {{% endif %}}
                    </div>
                </div>
            {{% endfor %}}
        {{% endfor %}}
    {{% else %}}
        <div style="text-align: center; padding: 12px; color: #ddd; font-style: italic; font-size: {font_size}px;">
            ✨ 暂无待办，享受空闲时光！
        </div>
    {{% endif %}}
</div>'''
    
    def _get_note_list_template(self) -> str:
        """获取紧凑的笔记列表模板"""
        font_size = self.config.get("ui_preferences", {}).get("font_size", 20)
        compact_mode = self.config.get("ui_preferences", {}).get("compact_mode", False)
        show_timestamps = self.config.get("ui_preferences", {}).get("show_timestamps", True)
        
        title_size = font_size + 4
        item_padding = "4px 8px" if compact_mode else "6px 10px"
        item_margin = "2px 0" if compact_mode else "4px 0"
        section_margin = "8px 0 4px 0" if compact_mode else "12px 0 6px 0"
        
        return f'''
<div style="{self._get_base_style()} background: linear-gradient(135deg, #74b9ff 0%, #0984e3 100%);">
    <div style="text-align: center; margin: 0 0 {8 if compact_mode else 12}px 0; font-size: {title_size}px; font-weight: 700;">
        📝 笔记{{{{ " - " + category if category else "" }}}}
    </div>
    {{% if notes %}}
        {{% for category_name, items in notes.items() %}}
            {{% if category_name and category_name != "默认" %}}
                <div style="margin: {section_margin}; color: #ffd700; font-size: {font_size - 2}px; font-weight: 600; border-bottom: 1px solid #ffd700; padding-bottom: 2px;">
                    📂 {{{{ category_name }}}}
                </div>
            {{% endif %}}
            {{% for note in items %}}
                <div style="margin: {item_margin}; padding: {item_padding}; background: rgba(255,255,255,0.15); border-radius: 4px; border-left: 3px solid #00cec9;">
                    <div style="display: flex; align-items: flex-start; justify-content: space-between;">
                        <div style="flex: 1;">
                            <div style="display: flex; align-items: center; margin-bottom: 2px;">
                                <span style="color: #ffd700; margin-right: 6px; font-size: {font_size - 4}px; font-weight: 600;">[{{{{ note.id }}}}]</span>
                                <span style="font-size: {font_size}px;">{{{{ note.content[:120] }}}}{{{{ "..." if note.content|length > 120 else "" }}}}</span>
                            </div>
                            {{% if note.tags %}}
                                <div style="margin-top: 3px;">
                                    {{% for tag in note.tags %}}
                                        <span style="background: rgba(255,255,255,0.25); padding: 1px 4px; border-radius: 8px; margin-right: 3px; font-size: {font_size - 6}px;">
                                            #{{{{ tag }}}}
                                        </span>
                                    {{% endfor %}}
                                </div>
                            {{% endif %}}
                        </div>
                        {{% if show_timestamps and note.created_at %}}
                            <div style="font-size: {font_size - 6}px; color: #ddd; margin-left: 8px; white-space: nowrap;">
                                {{{{ note.created_at }}}}
                            </div>
                        {{% endif %}}
                    </div>
                </div>
            {{% endfor %}}
        {{% endfor %}}
    {{% else %}}
        <div style="text-align: center; padding: 20px; color: #ddd; font-style: italic; font-size: {font_size}px;">
            ✨ 暂无笔记，开始记录想法！
        </div>
    {{% endif %}}
</div>'''
    
    def _get_search_results_template(self) -> str:
        """获取紧凑的搜索结果模板"""
        font_size = self.config.get("ui_preferences", {}).get("font_size", 20)
        compact_mode = self.config.get("ui_preferences", {}).get("compact_mode", False)
        
        title_size = font_size + 4
        item_padding = "4px 8px" if compact_mode else "6px 10px"
        item_margin = "2px 0" if compact_mode else "3px 0"
        section_margin = "8px 0 4px 0" if compact_mode else "10px 0 5px 0"
        
        return f'''
<div style="{self._get_base_style()} background: linear-gradient(135deg, #00b894 0%, #00a085 100%);">
    <div style="text-align: center; margin: 0 0 {8 if compact_mode else 12}px 0; font-size: {title_size}px; font-weight: 700;">
        🔍 "{{{{ keyword }}}}"
    </div>
    
    {{% if flash_notes %}}
        <div style="margin: {section_margin}; color: #ffd700; font-size: {font_size - 2}px; font-weight: 600; border-bottom: 1px solid #ffd700; padding-bottom: 2px;">
            ⚡ 闪念 ({{{{ flash_notes|length }}}} 条)
        </div>
        {{% for note in flash_notes %}}
            <div style="margin: {item_margin}; padding: {item_padding}; background: rgba(255,255,255,0.15); border-radius: 4px; border-left: 3px solid #fdcb6e;">
                <div style="font-size: {font_size - 6}px; color: #ddd; margin-bottom: 2px;">{{{{ note.created_at }}}}</div>
                <div style="font-size: {font_size - 2}px;">{{{{ note.content[:100] }}}}{{{{ "..." if note.content|length > 100 else "" }}}}</div>
            </div>
        {{% endfor %}}
    {{% endif %}}
    
    {{% if note_notes %}}
        <div style="margin: {section_margin}; color: #ffd700; font-size: {font_size - 2}px; font-weight: 600; border-bottom: 1px solid #ffd700; padding-bottom: 2px;">
            📝 笔记 ({{{{ note_notes|length }}}} 条)
        </div>
        {{% for note in note_notes %}}
            <div style="margin: {item_margin}; padding: {item_padding}; background: rgba(255,255,255,0.15); border-radius: 4px; border-left: 3px solid #74b9ff;">
                <div style="font-size: {font_size - 6}px; color: #ddd; margin-bottom: 2px;">{{{{ note.created_at }}}}</div>
                <div style="font-size: {font_size - 2}px;">{{{{ note.content[:100] }}}}{{{{ "..." if note.content|length > 100 else "" }}}}</div>
            </div>
        {{% endfor %}}
    {{% endif %}}
    
    {{% if todo_notes %}}
        <div style="margin: {section_margin}; color: #ffd700; font-size: {font_size - 2}px; font-weight: 600; border-bottom: 1px solid #ffd700; padding-bottom: 2px;">
            ✅ 待办 ({{{{ todo_notes|length }}}} 条)
        </div>
        {{% for note in todo_notes %}}
            <div style="margin: {item_margin}; padding: {item_padding}; background: rgba(255,255,255,0.15); border-radius: 4px; border-left: 3px solid #e17055;">
                <div style="font-size: {font_size - 6}px; color: #ddd; margin-bottom: 2px;">{{{{ note.created_at }}}}</div>
                <div style="font-size: {font_size - 2}px;">{{{{ note.content[:100] }}}}{{{{ "..." if note.content|length > 100 else "" }}}}</div>
            </div>
        {{% endfor %}}
    {{% endif %}}
    
    {{% if not flash_notes and not note_notes and not todo_notes %}}
        <div style="text-align: center; padding: 20px; color: #ddd; font-style: italic; font-size: {font_size}px;">
            🔍 未找到相关内容
        </div>
    {{% endif %}}
</div>'''
    
    def _get_help_template(self) -> str:
        """获取紧凑的帮助模板"""
        font_size = self.config.get("ui_preferences", {}).get("font_size", 20)
        compact_mode = self.config.get("ui_preferences", {}).get("compact_mode", False)
        
        title_size = font_size + 6
        section_margin = "6px 0 3px 0" if compact_mode else "10px 0 5px 0"
        item_padding = "3px 6px" if compact_mode else "4px 8px"
        item_margin = "1px 0" if compact_mode else "2px 0"
        
        return f'''
<div style="{self._get_base_style()} background: linear-gradient(135deg, #a29bfe 0%, #6c5ce7 100%);">
    <div style="text-align: center; margin: 0 0 {6 if compact_mode else 10}px 0; font-size: {title_size}px; font-weight: 700;">
        📖 FJNote 使用指南
    </div>
    
    <div style="margin-bottom: {6 if compact_mode else 8}px;">
        <div style="color: #ffd700; margin: {section_margin}; font-size: {font_size - 1}px; font-weight: 600; border-bottom: 1px solid #ffd700; padding-bottom: 1px;">⚡ 闪念记录</div>
        <div style="margin: {item_margin}; padding: {item_padding}; background: rgba(255,255,255,0.12); border-radius: 3px; border-left: 2px solid #fdcb6e; font-size: {font_size - 3}px;">
            直接发送消息自动记录闪念
        </div>
        <div style="margin: {item_margin}; padding: {item_padding}; background: rgba(255,255,255,0.12); border-radius: 3px; border-left: 2px solid #fdcb6e; font-size: {font_size - 3}px;">
            连续消息自动合并，使用 #标签 分类
        </div>
    </div>
    
    <div style="margin-bottom: {6 if compact_mode else 8}px;">
        <div style="color: #ffd700; margin: {section_margin}; font-size: {font_size - 1}px; font-weight: 600; border-bottom: 1px solid #ffd700; padding-bottom: 1px;">📝 笔记管理</div>
        <div style="margin: {item_margin}; padding: {item_padding}; background: rgba(255,255,255,0.12); border-radius: 3px; border-left: 2px solid #74b9ff; font-size: {font_size - 3}px;">
            <b>#note</b> 内容 #分类 - 创建笔记
        </div>
        <div style="margin: {item_margin}; padding: {item_padding}; background: rgba(255,255,255,0.12); border-radius: 3px; border-left: 2px solid #74b9ff; font-size: {font_size - 3}px;">
            <b>#notes</b> [分类] - 查看笔记
        </div>
    </div>
    
    <div style="margin-bottom: {6 if compact_mode else 8}px;">
        <div style="color: #ffd700; margin: {section_margin}; font-size: {font_size - 1}px; font-weight: 600; border-bottom: 1px solid #ffd700; padding-bottom: 1px;">✅ ToDo 管理</div>
        <div style="margin: {item_margin}; padding: {item_padding}; background: rgba(255,255,255,0.12); border-radius: 3px; border-left: 2px solid #e17055; font-size: {font_size - 3}px;">
            <b>#todo</b> 任务 #分类 ~截止 - 添加待办
        </div>
        <div style="margin: {item_margin}; padding: {item_padding}; background: rgba(255,255,255,0.12); border-radius: 3px; border-left: 2px solid #e17055; font-size: {font_size - 3}px;">
            <b>#list</b> [分类] - 查看待办 | <b>#done</b> 编号 - 完成
        </div>
    </div>
    
    <div>
        <div style="color: #ffd700; margin: {section_margin}; font-size: {font_size - 1}px; font-weight: 600; border-bottom: 1px solid #ffd700; padding-bottom: 1px;">🔍 其他功能</div>
        <div style="margin: {item_margin}; padding: {item_padding}; background: rgba(255,255,255,0.12); border-radius: 3px; border-left: 2px solid #00b894; font-size: {font_size - 3}px;">
            <b>#find</b> 关键词 | <b>#tags</b> 标签 | <b>#help</b> 帮助
        </div>
    </div>
</div>'''
    
    def _get_tags_list_template(self) -> str:
        """获取紧凑的标签列表模板"""
        font_size = self.config.get("ui_preferences", {}).get("font_size", 20)
        compact_mode = self.config.get("ui_preferences", {}).get("compact_mode", False)
        
        title_size = font_size + 4
        item_padding = "4px 8px" if compact_mode else "6px 10px"
        item_margin = "2px 0" if compact_mode else "3px 0"
        
        return f'''
<div style="{self._get_base_style()} background: linear-gradient(135deg, #fd79a8 0%, #e84393 100%);">
    <div style="text-align: center; margin: 0 0 {8 if compact_mode else 12}px 0; font-size: {title_size}px; font-weight: 700;">
        🏷️ 标签统计
    </div>
    {{% if tags %}}
        {{% for tag in tags %}}
            <div style="margin: {item_margin}; padding: {item_padding}; background: rgba(255,255,255,0.15); border-radius: 4px; display: flex; justify-content: space-between; align-items: center; border-left: 3px solid #ffd700;">
                <span style="font-weight: 600; font-size: {font_size}px;">#{{{{ tag.name }}}}</span>
                <span style="color: #ffd700; font-weight: 700; background: rgba(255,215,0,0.25); padding: 2px 6px; border-radius: 8px; font-size: {font_size - 4}px;">
                    {{{{ tag.count }}}}
                </span>
            </div>
        {{% endfor %}}
    {{% else %}}
        <div style="text-align: center; padding: 20px; color: #ddd; font-style: italic; font-size: {font_size}px;">
            🏷️ 暂无标签
        </div>
    {{% endif %}}
</div>'''
    
    async def render(self, template_name: str, data: Dict[str, Any]) -> str:
        """渲染模板"""
        template = self.env.get_template(template_name)
        return template.render(**data)