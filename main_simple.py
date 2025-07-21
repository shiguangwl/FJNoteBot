"""
简化版FJNote测试插件
"""

from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.star import Context, Star, register
from astrbot.api import logger

@register("FJNote", "FjNote", "测试插件", "1.2.8", "https://github.com/FjNote/FjNoteBot")
class FJNotePlugin(Star):
    def __init__(self, context: Context):
        super().__init__(context)
        logger.info("[FJNote] 简化版插件初始化完成")

    @filter.command("test")
    async def test(self, event: AstrMessageEvent):
        """测试命令"""
        logger.info("[FJNote] 收到test命令")
        yield event.plain_result("FJNote插件正常运行！")

    @filter.event_message_type(filter.EventMessageType.ALL)
    async def on_all_message(self, event: AstrMessageEvent):
        """接收所有消息"""
        message_text = event.message_str.strip()
        user_id = event.get_sender_id()
        logger.info(f"[FJNote] 收到消息: {message_text} from user: {user_id}")
        
        if not message_text.startswith('#') and len(message_text) > 3:
            yield event.plain_result(f"收到闪念: {message_text}")