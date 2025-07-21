"""
Core exceptions
核心异常定义
"""


class FJNoteException(Exception):
    """FJNote 插件基础异常"""
    pass


class BlinkoApiException(FJNoteException):
    """Blinko API 异常"""
    pass


class SessionException(FJNoteException):
    """会话管理异常"""  
    pass


class CommandException(FJNoteException):
    """命令处理异常"""
    pass