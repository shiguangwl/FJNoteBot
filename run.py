#!/usr/bin/env python3
"""
FJNote 最终测试工具
输入消息直接模拟机器人接收，调用真实 Blinko API
"""

import asyncio
import sys
import os
import types

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def setup_minimal_env():
    """最小化环境设置"""
    class MockLogger:
        def info(self, msg): print(f"[INFO] {msg}")
        def error(self, msg): print(f"[ERROR] {msg}")
        def warning(self, msg): print(f"[WARNING] {msg}")
        def debug(self, msg): print(f"[DEBUG] {msg}")

    class MockConfig(dict):
        def __init__(self):
            super().__init__()
            self.update({
                "blinko_base_url": "http://log.xxhoz.com",
                "blinko_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOjEsIm5hbWUiOiJUaW1lSG8iLCJyb2xlIjoic3VwZXJhZG1pbiIsInR3b0ZhY3RvclZlcmlmaWVkIjpmYWxzZSwiZXhwIjoxNzUzMzk5NDY4LCJpYXQiOjE3NTA4MDc0Njh9.i0g1x0Dm1Kr8hZMScmw50BzkcINMVMlmwPUlfrk6zFY",
                "flash_session_timeout": 3,
                "enable_rich_display": False,
                "default_tags": {"auto_add_date": False, "auto_add_platform": False}
            })

    class MockContext:
        def __init__(self):
            self.config = MockConfig()

    class MockPlain:
        def __init__(self, text: str): self.text = text

    class MockImage:
        def __init__(self, file: str): self.file = file

    class MockMessageResult:
        def __init__(self, components):
            self.chain = components if isinstance(components, list) else [components]

    class MockEvent:
        def __init__(self, message: str, sender_id: str = "test_user"):
            self.message_str = message
            self.sender_id = sender_id
            self.unified_msg_origin = f"test:{sender_id}"
            
            class MockMsgObj:
                def __init__(self, msg):
                    self.message = [MockPlain(msg)]
                    self.sender = type('Sender', (), {'id': sender_id, 'name': 'TestUser'})()
            
            self.message_obj = MockMsgObj(message)
        
        def get_sender_id(self): return self.sender_id
        def get_sender_name(self): return "TestUser"
        def get_group_id(self): return ""
        def plain_result(self, text): return MockMessageResult(MockPlain(text))
        def image_result(self, path): return MockMessageResult(MockPlain(f"[图片: {path}]"))

    # 创建 astrbot 模块结构
    astrbot = types.ModuleType('astrbot')
    astrbot_api = types.ModuleType('astrbot.api')
    astrbot_api.logger = MockLogger()
    astrbot_api.AstrBotConfig = MockConfig

    # Event 模块
    event_mod = types.ModuleType('astrbot.api.event')
    filter_mod = types.ModuleType('filter')
    EventMessageType = types.ModuleType('EventMessageType')
    EventMessageType.PRIVATE_MESSAGE = 'private'
    filter_mod.EventMessageType = EventMessageType
    filter_mod.event_message_type = lambda event_type: lambda func: func
    event_mod.filter = filter_mod
    event_mod.AstrMessageEvent = MockEvent
    event_mod.MessageEventResult = MockMessageResult

    # Star 模块
    star_mod = types.ModuleType('astrbot.api.star')
    star_mod.Context = MockContext
    
    class MockStar:
        def __init__(self, context): self.context = context
        async def html_render(self, html): return f"[模拟图片] {html[:30]}..."
    
    star_mod.Star = MockStar
    star_mod.register = lambda *args: lambda cls: cls

    # Components 模块
    comp_mod = types.ModuleType('astrbot.api.message_components')
    comp_mod.Plain = MockPlain
    comp_mod.Image = MockImage

    # 注册模块
    modules = {
        'astrbot': astrbot,
        'astrbot.api': astrbot_api,
        'astrbot.api.event': event_mod,
        'astrbot.api.star': star_mod,
        'astrbot.api.message_components': comp_mod
    }
    
    for name, mod in modules.items():
        sys.modules[name] = mod
    
    return MockEvent, MockContext


async def main():
    """主测试函数"""
    print("🎮 FJNote 最终测试")
    print("=" * 30)
    
    # 设置环境
    MockEvent, MockContext = setup_minimal_env()
    
    # 初始化插件
    try:
        from main import FJNotePlugin
        context = MockContext()
        plugin = FJNotePlugin(context, context.config)
        print("✅ 插件初始化成功\n")
    except Exception as e:
        print(f"❌ 初始化失败: {e}")
        return
    
    print("📝 支持的命令:")
    print("- 消息内容 → 闪念记录")
    print("- #todo 任务 #标签 → 添加待办")
    print("- #list → 查看待办")
    print("- #find 关键词 → 搜索")
    print("- #tags → 查看标签")
    print("- quit → 退出\n")
    
    # 交互循环
    try:
        while True:
            user_input = input("💬 ").strip()
            
            if not user_input:
                continue
            if user_input.lower() == 'quit':
                break
            
            try:
                event = MockEvent(user_input)
                async for result in plugin.on_private_message(event):
                    if result and result.chain:
                        for comp in result.chain:
                            if hasattr(comp, 'text'):
                                print(f"🤖 {comp.text}")
            except Exception as e:
                print(f"❌ 处理错误: {e}")
                
    except (KeyboardInterrupt, EOFError):
        pass
    
    print("\n👋 退出中...")
    await plugin.terminate()
    print("✅ 测试结束")


if __name__ == "__main__":
    asyncio.run(main())