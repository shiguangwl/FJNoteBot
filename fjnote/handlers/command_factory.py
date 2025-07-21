"""
Command factory using Factory pattern
命令工厂，采用工厂模式
"""

from typing import Optional
from .command_handlers import (
    ICommandHandler, TodoCommandHandler, ListCommandHandler, 
    DoneCommandHandler, DeleteCommandHandler, EditCommandHandler,
    SearchCommandHandler, TagsCommandHandler, HelpCommandHandler,
    NoteCommandHandler, NotesCommandHandler
)


class CommandFactory:
    """命令处理器工厂"""
    
    def __init__(self, plugin_instance):
        self.plugin = plugin_instance
        self._handlers = {}
        self._register_handlers()
    
    def _register_handlers(self):
        """注册所有命令处理器"""
        self._handlers.update({
            'todo': TodoCommandHandler(self.plugin),
            'list': ListCommandHandler(self.plugin),
            'done': DoneCommandHandler(self.plugin),
            'del': DeleteCommandHandler(self.plugin),
            'rm': DeleteCommandHandler(self.plugin),
            'edit': EditCommandHandler(self.plugin),
            'note': NoteCommandHandler(self.plugin),
            'notes': NotesCommandHandler(self.plugin),
            'find': SearchCommandHandler(self.plugin),
            'search': SearchCommandHandler(self.plugin),
            'tags': TagsCommandHandler(self.plugin),
            'cats': TagsCommandHandler(self.plugin),
            'help': HelpCommandHandler(self.plugin)
        })
    
    def get_handler(self, command: str) -> Optional[ICommandHandler]:
        """获取命令处理器"""
        return self._handlers.get(command.lower())
    
    def register_handler(self, command: str, handler: ICommandHandler):
        """注册新的命令处理器"""
        self._handlers[command.lower()] = handler
    
    def unregister_handler(self, command: str):
        """注销命令处理器"""
        if command.lower() in self._handlers:
            del self._handlers[command.lower()]
    
    def list_commands(self) -> list:
        """获取所有已注册的命令"""
        return list(self._handlers.keys())