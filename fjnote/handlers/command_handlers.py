"""
Command Handlers - 命令处理器
本模块采用命令模式（Command Pattern）和工厂模式（Factory Pattern）。
- ICommandHandler: 定义了所有命令处理器的统一接口（命令接口）。
- 每个具体命令处理器（如 TodoCommandHandler, ListCommandHandler）封装了执行特定命令（如 #todo, #list）所需的所有逻辑（具体命令类）。
- CommandFactory（在 command_factory.py 中）负责根据命令名称创建相应的处理器实例，解耦了请求者（主插件）与具体命令的实现。
"""

import re
from abc import ABC, abstractmethod
from typing import List, Dict, Any
from dataclasses import asdict

from astrbot.api.event import AstrMessageEvent, MessageEventResult
from astrbot.api import logger

from ..core.models import NoteType, TodoItem
from ..core.exceptions import CommandException


class ICommandHandler(ABC):
    """
    命令处理器接口（Command Interface）
    定义了所有具体命令处理器必须实现的 `handle` 方法。
    """
    
    @abstractmethod
    async def handle(self, event: AstrMessageEvent, args: List[str]) -> MessageEventResult:
        """
        处理命令的抽象方法。
        
        :param event: 消息事件对象。
        :param args: 解析后的命令参数列表。
        :return: 一个消息事件结果，用于回复用户。
        """
        pass


class TodoCommandHandler(ICommandHandler):
    """'#todo' 命令的具体处理器"""
    
    def __init__(self, plugin):
        self.plugin = plugin
    
    async def handle(self, event: AstrMessageEvent, args: List[str]) -> MessageEventResult:
        """处理 todo 命令"""
        if not args:
            return event.plain_result("请提供待办事项内容。格式: #todo 任务内容 #标签")
        
        try:
            content = " ".join(args)
            tags = self.plugin.session_manager.extract_tags(content)
            clean_content = self.plugin.session_manager.remove_tags(content).strip()
            
            # 移除截止时间处理，简化为纯内容
            clean_content = re.sub(r'~[^\s]+', '', clean_content).strip()
            
            # 构造包含标签的内容（blinko 会自动解析 #标签）
            todo_content = clean_content
            if tags:
                todo_content += " " + " ".join(f"#{tag}" for tag in tags)
            
            # 不传递 tags 参数，让 blinko 从内容中解析
            success = await self.plugin.todo_strategy.create(todo_content, [], dict(self.plugin.config))
            
            if success:
                # 使用响应管理器
                category = tags[0] if tags else None
                response = self.plugin.response_manager.todo_created(clean_content, category)
                if response:
                    return event.plain_result(response)
                else:
                    return None  # 不响应
            else:
                error_response = self.plugin.response_manager.error_general("添加待办失败，请检查Blinko连接")
                if error_response:
                    return event.plain_result(error_response)
                else:
                    return None
                
        except Exception as e:
            logger.error(f"Todo command error: {e}")
            error_response = self.plugin.response_manager.error_general("添加待办失败")
            if error_response:
                return event.plain_result(error_response)
            else:
                return None


class ListCommandHandler(ICommandHandler):
    """'#list' 命令的具体处理器"""
    
    def __init__(self, plugin):
        self.plugin = plugin
    
    async def handle(self, event: AstrMessageEvent, args: List[str]) -> MessageEventResult:
        """处理 list 命令"""
        category = args[0] if args else None
        
        try:
            # 获取用户配置
            page_size = self.plugin.config.get("ui_preferences", {}).get("list_page_size", 10)
            show_timestamps = self.plugin.config.get("ui_preferences", {}).get("show_timestamps", True)
            compact_mode = self.plugin.config.get("ui_preferences", {}).get("compact_mode", False)
            
            # 默认只获取未归档的笔记
            notes = await self.plugin.api_client.list_notes(
                note_type=NoteType.TODO.value, 
                size=page_size * 2,
                archived_status=False
            )
            
            todos_by_category = {}
            for i, note in enumerate(notes, 1):
                content = note.get("content", "")
                note_tags = note.get("tags", [])
                note_category = note_tags[0].get("tag", {}).get("name", "默认") if note_tags else "默认"
                
                if category and category != note_category:
                    continue
                
                if note_category not in todos_by_category:
                    todos_by_category[note_category] = []
                
                todo_item = TodoItem(
                    id=i,
                    note_id=note["id"],  # 存储真实的 note_id
                    content=content,
                    category=note_category,
                    deadline=None,
                    completed=note.get("isArchived", False)
                )
                
                todos_by_category[note_category].append(asdict(todo_item))
            
            if self.plugin.config.get("enable_rich_display", True):
                html = await self.plugin.template_renderer.render('todo_list', {
                    'todos': todos_by_category,
                    'category': category,
                    'show_timestamps': show_timestamps,
                    'compact_mode': compact_mode
                })
                image_url = await self.plugin.html_render(html, {})
                return event.image_result(image_url)
            else:
                text_result = f"📝 ToDo 列表{f' - {category}' if category else ''}\n"
                for cat, items in todos_by_category.items():
                    if cat:
                        text_result += f"\n【{cat}】\n"
                    for todo in items[:page_size]:  # 限制显示数量
                        status = "☑" if todo['completed'] else "☐"
                        if compact_mode:
                            text_result += f"[{todo['id']}] {status} {todo['content'][:30]}{'...' if len(todo['content']) > 30 else ''}\n"
                        else:
                            text_result += f"[{todo['id']}] {status} {todo['content']}"
                            if show_timestamps and todo.get('created_at'):
                                text_result += f" ({todo['created_at']})"
                            if todo['deadline']:
                                text_result += f" ~{todo['deadline']}"
                            text_result += "\n"
                return event.plain_result(text_result or "暂无待办事项")
        
        except Exception as e:
            logger.error(f"List command error: {e}")
            return event.plain_result("❌ 获取待办列表失败")


class DoneCommandHandler(ICommandHandler):
    """'#done' 命令的具体处理器"""
    
    def __init__(self, plugin):
        self.plugin = plugin
    
    async def handle(self, event: AstrMessageEvent, args: List[str]) -> MessageEventResult:
        """处理 done 命令"""
        if not args:
            return event.plain_result("请提供要完成的待办编号。格式: #done 1 2 3")
        
        try:
            todo_indices = [int(arg) for arg in args if arg.isdigit()]
            if not todo_indices:
                return event.plain_result("请提供有效的待办编号")
            
            # 获取当前活动的待办列表，以确保索引正确
            active_notes = await self.plugin.api_client.list_notes(
                note_type=NoteType.TODO.value, 
                size=100, 
                archived_status=False
            )
            
            completed_todos = []
            for index in todo_indices:
                if 1 <= index <= len(active_notes):
                    note_to_complete = active_notes[index - 1]
                    note_id = note_to_complete["id"]
                    content = note_to_complete.get("content", "")
                    
                    # 通过 API 将笔记归档
                    await self.plugin.api_client.update_note(note_id=note_id, is_archived=True)
                    completed_todos.append({"id": str(index), "content": content})
            
            completed_count = len(completed_todos)
            # 使用响应管理器，支持单个和多个TODO的不同响应
            if completed_count == 1:
                todo = completed_todos[0]
                response = self.plugin.response_manager.todo_completed(todo["id"], todo["content"])
                if response:
                    return event.plain_result(response)
                else:
                    return None
            elif completed_count > 1:
                # 对于多个TODO，使用通用成功响应
                response = self.plugin.response_manager.get_response("todo_completed", 
                                                                   id=f"{completed_count}个", 
                                                                   content="待办事项")
                if response:
                    return event.plain_result(response)
                else:
                    return None
            else:
                error_response = self.plugin.response_manager.error_not_found("指定编号", "todo")
                if error_response:
                    return event.plain_result(error_response)
                else:
                    return None
        
        except Exception as e:
            logger.error(f"Done command error: {e}")
            error_response = self.plugin.response_manager.error_general("完成待办失败")
            if error_response:
                return event.plain_result(error_response)
            else:
                return None


class DeleteCommandHandler(ICommandHandler):
    """'#del' 或 '#rm' 命令的具体处理器"""
    
    def __init__(self, plugin):
        self.plugin = plugin
    
    async def handle(self, event: AstrMessageEvent, args: List[str]) -> MessageEventResult:
        """处理 delete 命令"""
        if not args:
            return event.plain_result("请提供要删除的待办编号。格式: #del 1 2 3")
        
        try:
            todo_indices = [int(arg) for arg in args if arg.isdigit()]
            if not todo_indices:
                return event.plain_result("请提供有效的待办编号")
            
            # 获取当前活动的待办列表，以确保索引正确
            active_notes = await self.plugin.api_client.list_notes(
                note_type=NoteType.TODO.value, 
                size=100, 
                archived_status=False
            )
            
            deleted_items = []
            # 按索引降序删除，防止删除时列表变化导致索引错乱
            for index in sorted(todo_indices, reverse=True):
                if 1 <= index <= len(active_notes):
                    note_to_delete = active_notes.pop(index - 1) # 从本地列表中也移除
                    note_id = note_to_delete["id"]
                    await self.plugin.api_client.delete_note(note_id)
                    deleted_items.append({"id": str(index), "content": note_to_delete.get("content", "")})
            
            deleted_count = len(deleted_items)
            # 使用响应管理器
            if deleted_count == 1:
                item = deleted_items[0]
                response = self.plugin.response_manager.item_deleted(item["id"], "todo")
                if response:
                    return event.plain_result(response)
                else:
                    return None
            elif deleted_count > 1:
                # 对于多个项目，使用通用响应
                response = self.plugin.response_manager.get_response("item_deleted", 
                                                                   id=f"{deleted_count}个", 
                                                                   type="待办")
                if response:
                    return event.plain_result(response)
                else:
                    return None
            else:
                error_response = self.plugin.response_manager.error_not_found("指定编号", "todo")
                if error_response:
                    return event.plain_result(error_response)
                else:
                    return None
        
        except Exception as e:
            logger.error(f"Delete command error: {e}")
            error_response = self.plugin.response_manager.error_general("删除待办失败")
            if error_response:
                return event.plain_result(error_response)
            else:
                return None


class EditCommandHandler(ICommandHandler):
    """'#edit' 命令的具体处理器"""
    
    def __init__(self, plugin):
        self.plugin = plugin
    
    async def handle(self, event: AstrMessageEvent, args: List[str]) -> MessageEventResult:
        """处理 edit 命令"""
        if len(args) < 2:
            return event.plain_result("格式错误。使用: #edit 编号 新内容")
        
        try:
            index = int(args[0])
            new_content = " ".join(args[1:])
            
            # 获取当前活动的待办列表
            active_notes = await self.plugin.api_client.list_notes(
                note_type=NoteType.TODO.value, 
                size=100, 
                archived_status=False
            )
            
            if 1 <= index <= len(active_notes):
                note_to_edit = active_notes[index - 1]
                note_id = note_to_edit["id"]
                
                # 提取新内容中的标签
                tags = self.plugin.session_manager.extract_tags(new_content)
                clean_content = self.plugin.session_manager.remove_tags(new_content).strip()
                
                # 构造包含标签的完整内容，让Blinko处理
                final_content = clean_content
                if tags:
                    final_content += " " + " ".join(f"#{tag}" for tag in tags)
                
                await self.plugin.api_client.update_note(
                    note_id=note_id, 
                    content=final_content
                )
                
                response = self.plugin.response_manager.todo_edited(str(index), clean_content)
                if response:
                    return event.plain_result(response)
                else:
                    return None
            else:
                error_response = self.plugin.response_manager.error_not_found(str(index), "todo")
                if error_response:
                    return event.plain_result(error_response)
                else:
                    return None
        
        except ValueError:
            return event.plain_result("❌ 编号必须是数字。")
        except Exception as e:
            logger.error(f"Edit command error: {e}")
            return event.plain_result("❌ 编辑待办失败")


class SearchCommandHandler(ICommandHandler):
    """'#search' 或 '#find' 命令的具体处理器"""
    
    def __init__(self, plugin):
        self.plugin = plugin
    
    async def handle(self, event: AstrMessageEvent, args: List[str]) -> MessageEventResult:
        """处理 search 命令"""
        if not args:
            return event.plain_result("请提供搜索关键词。格式: #find 关键词")
        
        keyword = " ".join(args)
        
        try:
            flash_notes = await self.plugin.flash_strategy.search(keyword)
            todo_notes = await self.plugin.todo_strategy.search(keyword)
            
            if self.plugin.config.get("enable_rich_display", True):
                html = await self.plugin.template_renderer.render('search_results', {
                    'keyword': keyword,
                    'flash_notes': flash_notes[:10],
                    'todo_notes': todo_notes[:10]
                })
                image_url = await self.plugin.html_render(html)
                return event.image_result(image_url)
            else:
                result = f"🔍 搜索结果 - \"{keyword}\"\n\n"
                if flash_notes:
                    result += "⚡ 闪念:\n"
                    for note in flash_notes[:5]:
                        content = note.get("content", "")[:50]
                        result += f"- {content}...\n"
                    result += "\n"
                
                if todo_notes:
                    result += "📝 ToDo:\n"
                    for note in todo_notes[:5]:
                        content = note.get("content", "")[:50]
                        result += f"- {content}...\n"
                
                return event.plain_result(result or "未找到相关内容")
        
        except Exception as e:
            logger.error(f"Search command error: {e}")
            return event.plain_result("❌ 搜索失败")


class TagsCommandHandler(ICommandHandler):
    """'#tags' 或 '#cats' 命令的具体处理器"""
    
    def __init__(self, plugin):
        self.plugin = plugin
    
    async def handle(self, event: AstrMessageEvent, args: List[str]) -> MessageEventResult:
        """处理 tags 命令"""
        try:
            tags = await self.plugin.api_client.list_tags()
            
            if self.plugin.config.get("enable_rich_display", True):
                html = await self.plugin.template_renderer.render('tags_list', {
                    'tags': tags
                })
                image_url = await self.plugin.html_render(html)
                return event.image_result(image_url)
            else:
                result_text = "🏷️ 标签统计\n\n"
                for tag in tags:
                    result_text += f"#{tag.get('name', '')} - {tag.get('count', 0)}次\n"
                return event.plain_result(result_text or "暂无标签")
        
        except Exception as e:
            logger.error(f"Tags command error: {e}")
            return event.plain_result("❌ 获取标签失败")


class HelpCommandHandler(ICommandHandler):
    """'#help' 命令的具体处理器"""
    
    def __init__(self, plugin):
        self.plugin = plugin
    
    async def handle(self, event: AstrMessageEvent, args: List[str]) -> MessageEventResult:
        """处理 help 命令"""
        try:
            if self.plugin.config.get("enable_rich_display", True):
                html = await self.plugin.template_renderer.render('help', {})
                image_url = await self.plugin.html_render(html, {})
                return event.image_result(image_url)
            else:
                help_text = """📖 FJNote 助手使用指南

⚡ 闪念记录:
- 直接发送消息即可开始记录闪念
- 30秒内的连续消息会合并为一条闪念
- 使用 #标签 为闪念添加标签

📝 ToDo 管理:
- #todo 任务内容 #分类 ~截止日期 - 添加待办
- #list [分类] - 查看待办列表
- #done 编号1 编号2... - 完成待办
- #del/#rm 编号1 编号2... - 删除待办
- #edit 编号 新内容 - 编辑待办

🔍 搜索与管理:
- #find/#search 关键词 - 全局搜索
- #tags/#cats - 查看所有标签

💡 使用技巧:
- 支持发送图片和文件，会自动上传到Blinko
- 日期格式: 2024-01-01, 明天, 下周一等"""
                return event.plain_result(help_text)
        
        except Exception as e:
            logger.error(f"Help command error: {e}")
            return event.plain_result("❌ 显示帮助失败")


class NoteCommandHandler(ICommandHandler):
    """'#note' 命令的具体处理器"""
    
    def __init__(self, plugin):
        self.plugin = plugin
    
    async def handle(self, event: AstrMessageEvent, args: List[str]) -> MessageEventResult:
        """处理 note 命令"""
        if not args:
            return event.plain_result("请提供笔记内容。格式: #note 内容 #分类")
        
        try:
            content = " ".join(args)
            tags = self.plugin.session_manager.extract_tags(content)
            clean_content = self.plugin.session_manager.remove_tags(content)
            
            if not clean_content.strip():
                return event.plain_result("笔记内容不能为空")
            
            # 创建标准笔记
            success = await self.plugin.note_strategy.create(clean_content, tags, dict(self.plugin.config))
            
            if success:
                # 使用响应管理器
                category = tags[0] if tags else None
                response = self.plugin.response_manager.note_created(clean_content, category)
                if response:
                    return event.plain_result(response)
                else:
                    return None  # 不响应
            else:
                error_response = self.plugin.response_manager.error_general("保存笔记失败，请检查Blinko连接")
                if error_response:
                    return event.plain_result(error_response)
                else:
                    return None
                
        except Exception as e:
            logger.error(f"Note command error: {e}")
            error_response = self.plugin.response_manager.error_general("保存笔记失败")
            if error_response:
                return event.plain_result(error_response)
            else:
                return None


class NotesCommandHandler(ICommandHandler):
    """'#notes' 命令的具体处理器"""
    
    def __init__(self, plugin):
        self.plugin = plugin
    
    async def handle(self, event: AstrMessageEvent, args: List[str]) -> MessageEventResult:
        """处理 notes 命令"""
        category = args[0] if args else None
        
        try:
            # 获取用户配置
            page_size = self.plugin.config.get("ui_preferences", {}).get("list_page_size", 10)
            show_timestamps = self.plugin.config.get("ui_preferences", {}).get("show_timestamps", True)
            compact_mode = self.plugin.config.get("ui_preferences", {}).get("compact_mode", False)
            
            notes = await self.plugin.api_client.list_notes(note_type=1, size=page_size * 2)  # NoteType.NOTE = 1
            
            notes_by_category = {}
            for i, note in enumerate(notes, 1):
                content = note.get("content", "")
                # 使用 blinko 的标签
                note_tags = note.get("tags", [])
                note_category = note_tags[0].get("tag", {}).get("name", "默认") if note_tags else "默认"
                
                if category and category != note_category:
                    continue
                
                if note_category not in notes_by_category:
                    notes_by_category[note_category] = []
                
                note_item = {
                    "id": i,
                    "content": content,
                    "category": note_category,
                    "tags": [tag.get("tag", {}).get("name", "") for tag in note_tags],
                    "created_at": note.get("createdAt", "")
                }
                
                notes_by_category[note_category].append(note_item)
            
            if self.plugin.config.get("enable_rich_display", True):
                html = await self.plugin.template_renderer.render('note_list', {
                    'notes': notes_by_category,
                    'category': category,
                    'show_timestamps': show_timestamps,
                    'compact_mode': compact_mode
                })
                image_url = await self.plugin.html_render(html, {})
                return event.image_result(image_url)
            else:
                text_result = f"📝 笔记列表{f' - {category}' if category else ''}\n"
                for cat, items in notes_by_category.items():
                    if cat:
                        text_result += f"\n【{cat}】\n"
                    for note in items[:page_size]:  # 限制显示数量
                        if compact_mode:
                            text_result += f"[{note['id']}] {note['content'][:50]}{'...' if len(note['content']) > 50 else ''}\n"
                        else:
                            text_result += f"[{note['id']}] {note['content']}"
                            if show_timestamps and note.get('created_at'):
                                text_result += f" ({note['created_at']})"
                            if note['tags']:
                                text_result += f" #{' #'.join(note['tags'])}"
                            text_result += "\n"
                return event.plain_result(text_result or "暂无笔记")
        
        except Exception as e:
            logger.error(f"Notes command error: {e}")
            return event.plain_result("❌ 获取笔记列表失败")