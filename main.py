from astrbot.api.event import filter, AstrMessageEvent
from astrbot.core.platform.message_type import MessageType
from astrbot.core.platform.sources.aiocqhttp.aiocqhttp_message_event import (
    AiocqhttpMessageEvent,
)
from astrbot.api.star import Context, Star, register
from astrbot.api import logger


@register(
    "at_somebody",
    "JOJO",
    "[仅限aiocqhttp] 在指定群内艾特(@)给定名单的用户+要通知的内容",
    "0.0.1",
)
class AtSomebody(Star):
    def __init__(self, context: Context):
        super().__init__(context)

    @filter.command("@")
    @filter.permission_type(filter.PermissionType.ADMIN)
    async def send_at_message(self, event: AstrMessageEvent):
        """这是一个 hello world 指令"""  # 这是 handler 的描述，将会被解析方便用户了解插件内容。建议填写。
        if event.get_platform_name() == "aiocqhttp":
            content = event.message_str[2:].strip()  # 用户发的纯文本消息字符串
            logger.info("args: {}".format(content))
            parts = content.split(" ", 2)
            logger.info(
                "当前会话类型: {}, {}".format(event.message_obj.type, event.message_obj)
            )
            if len(parts) == 3:
                qunid, second, notify_content = parts
                if second == "all":
                    # 格式: qunid all 内容
                    if await self.get_all_remain_times(event, qunid) <= 0:
                        yield event.plain_result(
                            "当前bot在群聊: {} 中，可用@全体成员的次数为0，请稍后再试。".format(
                                qunid
                            )
                        )
                        return
                    await self.send_message(event, qunid, "all", notify_content)
                else:
                    # 格式: qunid qqnum列表 内容

                    # 解析qqnum列表
                    qqnums = second.split(",")
                    await self.send_message(event, qunid, qqnums, notify_content)
            elif len(parts) == 2:
                first, notify_content = parts
                if not self.is_group_message(event):
                    yield event.plain_result(
                        "当前指令只能在群聊中使用，请在群聊中使用此指令。"
                    )
                    return
                if first == "all":
                    # 格式: all 内容
                    if (
                        await self.get_all_remain_times(
                            event, event.message_obj.group_id
                        )
                        <= 0
                    ):
                        yield event.plain_result(
                            "当前bot在群聊: {} 中，可用@全体成员的次数为0，请稍后再试。".format(
                                event.message_obj.group_id
                            )
                        )
                        return
                    await self.send_message(
                        event, event.message_obj.group_id, "all", notify_content
                    )
                else:
                    # 格式: qqnum列表 内容
                    qqnums = first.split(",")
                    await self.send_message(
                        event, event.message_obj.group_id, qqnums, notify_content
                    )
            else:
                # 格式不符合，报错或忽略
                yield event.plain_result(
                    "输入格式不正确，请使用以下格式之一：\n"
                    "`/@ qunid qqnum1[,qqnum2,...] 内容`\n"
                    "`/@ qunid all 内容`\n"
                    "`/@ qqnum1[,qqnum2,...] 内容`\n"
                    "`/@ all 内容`"
                )

    # 判断是否为群消息
    def is_group_message(self, event: AstrMessageEvent) -> bool:
        return event.message_obj.type == MessageType.GROUP_MESSAGE

    def is_private_message(self, event: AstrMessageEvent) -> bool:
        return event.message_obj.type == MessageType.FRIEND_MESSAGE

    async def get_all_remain_times(self, event: AiocqhttpMessageEvent, group_id) -> int:
        """
        获取当前bot还有多少次@全体成员的机会
        :param event: AiocqhttpMessageEvent
        :param group_id: 群聊ID
        :return: 剩余次数
        """
        client = event.bot
        payloads = {
            "group_id": group_id,
        }
        ret = await client.api.call_action("get_group_at_all_remain", **payloads)
        remain_times = ret.get("remain_at_all_count_for_uin", 0)
        logger.info("获取{}群聊@全体成员剩余次数: {}".format(group_id, remain_times))
        return remain_times

    async def send_message(
        self, event: AiocqhttpMessageEvent, qunid: str, qqnums: list | str, message: str
    ):
        """
        发送消息到指定的群聊
        :param event: AiocqhttpMessageEvent
        :param qunid: 群聊ID
        :param qqnums: 要艾特的用户列表，可以是单个用户的QQ号或多个用户的列表
        :param message: 要发送的消息内容
        """
        # 创建消息链
        payloads = {"group_id": qunid, "message": []}
        chain = []
        if qqnums == "all":
            chain.append({"type": "at", "data": {"qq": "all"}})
        else:
            for qqnum in qqnums:
                chain.append({"type": "at", "data": {"qq": qqnum}})
        chain.append({"type": "text", "data": {"text": "\n"}})
        chain.append({"type": "text", "data": {"text": message}})
        payloads["message"] = chain
        # 发送消息
        client = event.bot
        await client.api.call_action("send_group_msg", **payloads)
        logger.info(
            "发送消息到群聊: {}，艾特用户: {}，消息内容: {}".format(
                qunid, qqnums, message
            )
        )
