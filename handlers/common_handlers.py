import os
from astrbot.api.event import filter, AstrMessageEvent
from ..draw.help import draw_help_image
from ..draw.state import draw_state_image, get_user_state_data
from ..core.utils import get_now
from ..utils import safe_datetime_handler
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..main import FishingPlugin


async def register_user(plugin: "FishingPlugin", event: AstrMessageEvent):
    """注册用户命令"""
    user_id = plugin._get_effective_user_id(event)
    nickname = event.get_sender_name() if event.get_sender_name() is not None else user_id
    if result := plugin.user_service.register(user_id, nickname):
        yield event.plain_result(result["message"])
    else:
        yield event.plain_result("❌ 出错啦！请稍后再试。")

async def sign_in(plugin: "FishingPlugin", event: AstrMessageEvent):
    """签到"""
    user_id = plugin._get_effective_user_id(event)
    result = plugin.user_service.daily_sign_in(user_id)
    if result["success"]:
        yield event.plain_result(result["message"])
    else:
        yield event.plain_result(f"❌ 签到失败：{result['message']}")

async def state(plugin: "FishingPlugin", event: AstrMessageEvent):
    """查看用户状态"""
    user_id = plugin._get_effective_user_id(event)

    # 调用新的数据获取函数
    user_data = get_user_state_data(
        plugin.user_repo,
        plugin.inventory_repo,
        plugin.item_template_repo,
        plugin.log_repo,
        plugin.buff_repo,
        plugin.game_config,
        user_id,
    )
    
    if not user_data:
        yield event.plain_result('❌ 用户不存在，请先发送"注册"来开始游戏')
        return
    # 生成状态图像
    image = await draw_state_image(user_data, plugin.data_dir)
    # 保存图像到临时文件
    image_path = os.path.join(plugin.tmp_dir, "user_status.png")
    image.save(image_path)
    yield event.image_result(image_path)

async def fishing_log(plugin: "FishingPlugin", event: AstrMessageEvent):
    """查看钓鱼记录"""
    user_id = plugin._get_effective_user_id(event)
    if result := plugin.fishing_service.get_user_fish_log(user_id):
        if result["success"]:
            records = result["records"]
            if not records:
                yield event.plain_result("❌ 您还没有钓鱼记录。")
                return
            message = "【📜 钓鱼记录】：\n"
            for record in records:
                message += (f" - {record['fish_name']} ({'★' * record['fish_rarity']})\n"
                            f" - ⚖️重量: {record['fish_weight']} 克 - 💰价值: {record['fish_value']} 金币\n"
                            f" - 🔧装备： {record['accessory']} & {record['rod']} | 🎣鱼饵: {record['bait']}\n"
                            f" - 钓鱼时间: {safe_datetime_handler(record['timestamp'])}\n")
            yield event.plain_result(message)
        else:
            yield event.plain_result(f"❌ 获取钓鱼记录失败：{result['message']}")
    else:
        yield event.plain_result("❌ 出错啦！请稍后再试。")

async def fishing_help(plugin: "FishingPlugin", event: AstrMessageEvent):
    """显示钓鱼插件帮助信息"""
    image = draw_help_image()
    output_path = os.path.join(plugin.tmp_dir, "fishing_help.png")
    image.save(output_path)
    yield event.image_result(output_path)
