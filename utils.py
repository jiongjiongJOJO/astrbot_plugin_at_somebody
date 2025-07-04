import re
import astrbot.api.message_components as Comp
from astrbot.api import logger
from astrbot.api.event import AstrMessageEvent
from astrbot.core.platform.message_type import MessageType
from astrbot.core.platform.sources.aiocqhttp.aiocqhttp_message_event import AiocqhttpMessageEvent


def parse_command(input_str):
    """
    解析输入字符串，提取群ID、目标用户和内容
    :param input_str: str 输入字符串，格式为 /@ [群ID] 目标用户[ 内容]
    :return: dict 包含群ID、目标用户和内容的字典
    """
    pattern = r"^/@\s*(?:(\d+)\s+)?(all|\d[\d,]*\d|\d)\s*(.*)$"
    match = re.match(pattern, input_str, re.DOTALL)
    if not match:
        return None

    # 提取匹配的组
    group_id = match.group(1)  # 群ID（可能为None）
    target = match.group(2).lower()  # 目标部分（转为小写）
    content = match.group(3).strip()  # 内容部分（去除首尾空格）

    # 处理目标部分：如果是数字列表则拆分
    if target != "all":
        # 分解id列表（允许数字间有空格）
        id_list = [tid.strip() for tid in target.split(",") if tid.strip()]
        # 验证每个ID均为纯数字
        if not all(tid.isdigit() for tid in id_list):
            return None
    else:
        id_list = []

    return {
        "group_id": group_id,
        "target": "all" if target == "all" else id_list,
        "content": content,
    }


def is_group_message(event: AstrMessageEvent) -> bool:
    """
    判断是否为群聊消息
    :param event: AstrMessageEvent
    :return: 是群聊消息返回True，否则返回False
    """
    return event.message_obj.type == MessageType.GROUP_MESSAGE


def is_private_message(event: AstrMessageEvent) -> bool:
    """
    判断是否为私聊消息
    :param event: AstrMessageEvent
    :return: 是私聊消息返回True，否则返回False
    """
    return event.message_obj.type == MessageType.FRIEND_MESSAGE


async def get_all_remain_times(event: AiocqhttpMessageEvent, group_id) -> int:
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


async def send_message_bak(
    event: AiocqhttpMessageEvent, command_params: dict
):
    """
    发送消息到指定的群聊
    :param event: AiocqhttpMessageEvent
    :param command_params: 命令参数字典，包含群号、目标用户和内容
    """
    payloads = {"group_id": command_params['group_id'], "message": []}
    at_chain = []
    if command_params["target"] != "all":
        for user_id in command_params["target"]:
            at_chain.append({"type": "at", "data": {"qq": user_id}})
    else:
        at_chain.append({"type": "at", "data": {"qq": "all"}})

    # 转换消息类型
    msg_chain = [{"type": "text", "data": {"text": "\n\n"}}]
    for chain in command_params["content"]:
        if isinstance(chain, Comp.Plain):
            msg_chain.append(
                {"type": "text", "data": {"text": chain.text}}
            )
        elif isinstance(chain, Comp.Face):
            msg_chain.append(
                {"type": "face", "data": {"id": chain.id}}
            )
        elif isinstance(chain, Comp.Video):
            msg_chain.append(
                {"type": "video", "data": {"file": chain.url}}
            )
        elif isinstance(chain, Comp.At):
            msg_chain.append(
                {"type": "at", "data": {"qq": chain.qq}}
            )
        elif isinstance(chain, Comp.Image):
            msg_chain.append(
                {"type": "image", "data": {"file": chain.url}}
            )
        elif isinstance(chain, Comp.Record):
            msg_chain.append(
                {"type": "record", "data": {"file": chain.url}}
            )
        elif isinstance(chain, Comp.File):
            msg_chain.append({"type": "file", "data": {"file": chain.url}})

    # 合并艾特和消息链
    payloads["message"] = at_chain + msg_chain

    client = event.bot
    await client.api.call_action("send_group_msg", **payloads)
    logger.info(
        "在群聊 {} 中发送消息: {}".format(
            command_params["group_id"], payloads["message"]
        )
    )


def get_group_unified_msg_origin(
    group_id: str, platform: str = "aiocqhttp"
) -> str:
    """获取群组统一消息来源

    Args:
        group_id: 群组ID
        platform: 平台名称

    Returns:
        str: 统一消息来源
    """
    return f"{platform}:GroupMessage:{group_id}"
