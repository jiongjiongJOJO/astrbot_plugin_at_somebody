from astrbot.api import logger
import astrbot.api.message_components as Comp
from astrbot.api.event import filter, AstrMessageEvent, MessageChain
from astrbot.api.star import Context, Star, register
from .utils import parse_command, is_group_message, get_all_remain_times, get_group_unified_msg_origin


@register(
    "at_somebody",
    "JOJO",
    "[仅限aiocqhttp] 在指定群内艾特(@)给定名单的用户+要通知的内容",
    "1.0.0",
)
class AtSomebody(Star):
    def __init__(self, context: Context):
        super().__init__(context)
        self.context = context

    @filter.command("@")
    @filter.permission_type(filter.PermissionType.ADMIN)
    async def send_at_message(self, event: AstrMessageEvent):
        """
        在指定群内艾特(@)给定名单的用户+要通知的内容
        :param event: AstrMessageEvent
        :return:
        """
        if event.get_platform_name() == "aiocqhttp":
            message_chain = event.get_messages()
            command_str = message_chain[0].text
            command_params = parse_command(command_str)

            if not command_params:
                yield event.plain_result(
                    "指令格式错误，请使用 `/@ [群ID] 目标用户 [内容]` 的格式。"
                )
                return

            # 获取群号
            if not command_params.get('group_id'):
                if is_group_message(event):
                    command_params['group_id'] = event.message_obj.group_id
                else:
                    yield event.plain_result("当前指令只能在群聊中使用，请在群聊中使用此指令。")
                    return 

            # 当前群内bot可使用 @全体成员 的次数
            remain_times = await get_all_remain_times(
                event, command_params['group_id']
            )

            if remain_times <= 0 and command_params["target"] == "all":
                yield event.plain_result(
                    "当前bot在群聊: {} 中，可用@全体成员的次数为0，请稍后再试。".format(
                        event.message_obj.group_id
                    )
                )
                return

            # 获取消息链完整信息
            msg_chain = [Comp.Plain(command_params['content'])]
            for chain in event.get_messages()[1:]:
                msg_chain.append(chain)

            command_params['content'] = msg_chain

            # 发送消息
            await self.send_message(command_params)

    async def send_message(self, command_params: dict):
        """
        发送消息到指定的群聊
        :param command_params: 命令参数字典，包含群号、目标用户和内容
        """
        at_chain = []
        if command_params["target"] != "all":
            for user_id in command_params["target"]:
                at_chain.append(Comp.At(qq=user_id))
        else:
            at_chain.append(Comp.At(qq="all"))

        # 转换消息类型
        msg_chain = command_params["content"]

        # 获取群组统一消息来源
        unified_msg_origin = get_group_unified_msg_origin(command_params["group_id"])

        # 合并艾特和消息链
        chains = MessageChain(at_chain + [Comp.Plain('\n\n')] + msg_chain)
        await self.context.send_message(unified_msg_origin, chains)

        logger.info(
            "已发送消息到群聊: {}, 消息内容: {}".format(
                command_params["group_id"],
                chains
            )
        )
