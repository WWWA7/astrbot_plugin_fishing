from astrbot.api.event import filter, AstrMessageEvent
from ..utils import parse_target_user_id, to_percentage, safe_datetime_handler
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..main import FishingPlugin


def _get_field(obj, key, default=None):
    """统一读取字段，兼容 dataclass 模型实现了 __getitem__ 但没有 dict.get 的情况。"""
    try:
        # 优先尝试下标访问（GachaPool 实现了 __getitem__）
        return obj[key]
    except Exception:
        # 若是 dict 支持 get；否则回退 getattr
        if isinstance(obj, dict):
            return obj.get(key, default)
        return getattr(obj, key, default)


def _format_pool_details(pool, probabilities):
    message = "【🎰 卡池详情】\n\n"
    message += f"ID: {pool['gacha_pool_id']} - {pool['name']}\n"
    message += f"描述: {pool['description']}\n"
    # 限时开放信息展示（安全检查字段）
    is_limited_time = bool(_get_field(pool, "is_limited_time"))
    open_until = _get_field(pool, "open_until")
    if is_limited_time and open_until:
        display_time = str(open_until).replace("T", " ").replace("-", "/")
        if len(display_time) > 16:
            display_time = display_time[:16]
        message += f"限时开放 至: {display_time}\n"
    if _get_field(pool, "cost_premium_currency"):
        message += f"花费: {pool['cost_premium_currency']} 高级货币 / 次\n\n"
    else:
        message += f"花费: {pool['cost_coins']} 金币 / 次\n\n"
    message += "【📋 物品概率】\n"
    if probabilities:
        for item in probabilities:
            message += (
                f" - {'⭐' * item.get('item_rarity', 0)} {item['item_name']} "
                f"(概率: {to_percentage(item['probability'])})\n"
            )
    return message


async def gacha(self: "FishingPlugin", event: AstrMessageEvent):
    """抽卡"""
    user_id = self._get_effective_user_id(event)
    args = event.message_str.split(" ")
    if len(args) < 2:
        # 展示所有的抽奖池信息并显示帮助
        pools = self.gacha_service.get_all_pools()
        if not pools:
            yield event.plain_result("❌ 当前没有可用的抽奖池。")
            return
        message = "【🎰 抽奖池列表】\n\n"
        for pool in pools.get("pools", []):
            cost_text = f"💰 金币 {pool['cost_coins']} / 次"
            if pool["cost_premium_currency"]:
                cost_text = f"💎 高级货币 {pool['cost_premium_currency']} / 次"
            message += f"ID: {pool['gacha_pool_id']} - {pool['name']} - {pool['description']}\n {cost_text}\n\n"
        # 添加卡池详细信息
        message += "【📋 卡池详情】使用「查看卡池 ID」命令查看详细物品概率\n"
        message += "【🎲 抽卡命令】使用「抽卡 ID」命令选择抽卡池进行单次抽卡\n"
        message += "【🎯 十连命令】使用「十连 ID」命令进行十连抽卡"
        yield event.plain_result(message)
        return
    pool_id = args[1]
    if not pool_id.isdigit():
        yield event.plain_result("❌ 抽奖池 ID 必须是数字，请检查后重试。")
        return
    pool_id = int(pool_id)
    if result := self.gacha_service.perform_draw(user_id, pool_id, num_draws=1):
        if result["success"]:
            items = result.get("results", [])
            message = f"🎉 抽卡成功！您抽到了 {len(items)} 件物品：\n"
            for item in items:
                # 构造输出信息
                if item.get("type") == "coins":
                    # 金币类型的物品
                    message += f"⭐ {item['quantity']} 金币！\n"
                else:
                    message += f"{'⭐' * item.get('rarity', 1)} {item['name']}\n"
            yield event.plain_result(message)
        else:
            yield event.plain_result(f"❌ 抽卡失败：{result['message']}")
    else:
        yield event.plain_result("❌ 出错啦！请稍后再试。")


async def ten_gacha(self: "FishingPlugin", event: AstrMessageEvent):
    """十连抽卡"""
    user_id = self._get_effective_user_id(event)
    args = event.message_str.split(" ")
    if len(args) < 2:
        yield event.plain_result("❌ 请指定要进行十连抽卡的抽奖池 ID，例如：/十连 1")
        return
    pool_id = args[1]
    if not pool_id.isdigit():
        yield event.plain_result("❌ 抽奖池 ID 必须是数字，请检查后重试。")
        return
    pool_id = int(pool_id)
    if result := self.gacha_service.perform_draw(user_id, pool_id, num_draws=10):
        if result["success"]:
            items = result.get("results", [])
            message = f"🎉 十连抽卡成功！您抽到了 {len(items)} 件物品：\n"
            for item in items:
                # 构造输出信息
                if item.get("type") == "coins":
                    # 金币类型的物品
                    message += f"⭐ {item['quantity']} 金币！\n"
                else:
                    message += f"{'⭐' * item.get('rarity', 1)} {item['name']}\n"
            yield event.plain_result(message)
        else:
            yield event.plain_result(f"❌ 抽卡失败：{result['message']}")
    else:
        yield event.plain_result("❌ 出错啦！请稍后再试。")


async def view_gacha_pool(self: "FishingPlugin", event: AstrMessageEvent):
    """查看当前卡池"""
    args = event.message_str.split(" ")
    if len(args) < 2:
        yield event.plain_result("❌ 请指定要查看的卡池 ID，例如：/查看卡池 1")
        return
    pool_id = args[1]
    if not pool_id.isdigit():
        yield event.plain_result("❌ 卡池 ID 必须是数字，请检查后重试。")
        return
    pool_id = int(pool_id)
    if result := self.gacha_service.get_pool_details(pool_id):
        if result["success"]:
            pool = result.get("pool", {})
            probabilities = result.get("probabilities", [])
            yield event.plain_result(_format_pool_details(pool, probabilities))
        else:
            yield event.plain_result(f"❌ 查看卡池失败：{result['message']}")
    else:
        yield event.plain_result("❌ 出错啦！请稍后再试。")


async def gacha_history(self: "FishingPlugin", event: AstrMessageEvent):
    """查看抽卡记录"""
    user_id = self._get_effective_user_id(event)
    if result := self.gacha_service.get_user_gacha_history(user_id):
        if result["success"]:
            history = result.get("records", [])
            if not history:
                yield event.plain_result("📜 您还没有抽卡记录。")
                return
            total_count = len(history)
            message = f"【📜 抽卡记录】共 {total_count} 条\n\n"

            for record in history:
                message += f"物品名称: {record['item_name']} (稀有度: {'⭐' * record['rarity']})\n"
                message += f"时间: {safe_datetime_handler(record['timestamp'])}\n\n"

            yield event.plain_result(message)
        else:
            yield event.plain_result(f"❌ 查看抽卡记录失败：{result['message']}")
    else:
        yield event.plain_result("❌ 出错啦！请稍后再试。")


async def wipe_bomb(self: "FishingPlugin", event: AstrMessageEvent):
    """擦弹功能"""
    user_id = self._get_effective_user_id(event)
    args = event.message_str.split(" ")
    if len(args) < 2:
        yield event.plain_result("💸 请指定要擦弹的数量 ID，例如：/擦弹 123456789")
        return
    contribution_amount = args[1]
    if contribution_amount in ["allin", "halfin", "梭哈", "梭一半"]:
        # 查询用户当前金币数量
        if user := self.user_repo.get_by_id(user_id):
            coins = user.coins
        else:
            yield event.plain_result("❌ 您还没有注册，请先使用 /注册 命令注册。")
            return
        if contribution_amount in ("allin", "梭哈"):
            contribution_amount = coins
        elif contribution_amount in ("halfin", "梭一半"):
            contribution_amount = coins // 2
        contribution_amount = str(contribution_amount)
    # 判断是否为int或数字字符串
    if not contribution_amount.isdigit():
        yield event.plain_result("❌ 擦弹数量必须是数字，请检查后重试。")
        return
    if result := self.game_mechanics_service.perform_wipe_bomb(
        user_id, int(contribution_amount)
    ):
        if result["success"]:
            message = ""
            contribution = result["contribution"]
            multiplier = result["multiplier"]
            reward = result["reward"]
            profit = result["profit"]
            remaining_today = result["remaining_today"]

            # 格式化倍率，智能精度显示
            if multiplier < 0.01:
                # 当倍率小于0.01时，显示4位小数以避免混淆
                multiplier_formatted = f"{multiplier:.4f}"
            else:
                # 正常情况下保留两位小数
                multiplier_formatted = f"{multiplier:.2f}"

            if multiplier >= 3:
                message += f"🎰 大成功！你投入 {contribution} 金币，获得了 {multiplier_formatted} 倍奖励！\n 💰 奖励金额：{reward} 金币（盈利：+ {profit}）\n"
            elif multiplier >= 1:
                message += f"🎲 你投入 {contribution} 金币，获得了 {multiplier_formatted} 倍奖励！\n 💰 奖励金额：{reward} 金币（盈利：+ {profit}）\n"
            else:
                message += f"💥 你投入 {contribution} 金币，获得了 {multiplier_formatted} 倍奖励！\n 💰 奖励金额：{reward} 金币（亏损：- {abs(profit)})\n"
            message += f"剩余擦弹次数：{remaining_today} 次\n"

            # 如果触发了抑制模式，添加通知信息
            if "suppression_notice" in result:
                message += f"\n{result['suppression_notice']}"

            yield event.plain_result(message)
        else:
            yield event.plain_result(f"⚠️ 擦弹失败：{result['message']}")
    else:
        yield event.plain_result("❌ 出错啦！请稍后再试。")


async def wipe_bomb_history(self: "FishingPlugin", event: AstrMessageEvent):
    """查看擦弹记录"""
    user_id = self._get_effective_user_id(event)
    if result := self.game_mechanics_service.get_wipe_bomb_history(user_id):
        if result["success"]:
            history = result.get("logs", [])
            if not history:
                yield event.plain_result("📜 您还没有擦弹记录。")
                return
            message = "【📜 擦弹记录】\n\n"
            for record in history:
                # 添加一点emoji
                message += f"⏱️ 时间: {safe_datetime_handler(record['timestamp'])}\n"
                message += f"💸 投入: {record['contribution']} 金币, 🎁 奖励: {record['reward']} 金币\n"
                # 计算盈亏
                profit = record["reward"] - record["contribution"]
                profit_text = f"盈利: +{profit}" if profit >= 0 else f"亏损: {profit}"
                profit_emoji = "📈" if profit >= 0 else "📉"

                if record["multiplier"] >= 3:
                    message += f"🔥 倍率: {record['multiplier']} ({profit_emoji} {profit_text})\n\n"
                elif record["multiplier"] >= 1:
                    message += f"✨ 倍率: {record['multiplier']} ({profit_emoji} {profit_text})\n\n"
                else:
                    message += f"💔 倍率: {record['multiplier']} ({profit_emoji} {profit_text})\n\n"
            yield event.plain_result(message)
        else:
            yield event.plain_result(f"❌ 查看擦弹记录失败：{result['message']}")
    else:
        yield event.plain_result("❌ 出错啦！请稍后再试。")


async def start_wheel_of_fate(self: "FishingPlugin", event: AstrMessageEvent):
    """处理开始命运之轮游戏的指令，并提供玩法说明。"""
    user_id = self._get_effective_user_id(event)
    args = event.message_str.split(" ")

    if len(args) < 2:
        config = self.game_mechanics_service.WHEEL_OF_FATE_CONFIG
        min_fee = config.get("min_entry_fee", 500)
        max_fee = config.get("max_entry_fee", 50000)
        timeout = config.get("timeout_seconds", 60)
        help_message = "--- 🎲 命运之轮 玩法说明 ---\n\n"
        help_message += "这是一个挑战勇气与运气的游戏！你将面临连续的抉择，幸存得越久，奖励越丰厚，但失败将让你失去一切。\n\n"
        help_message += f"【玩法】\n使用 `/命运之轮 <金额>` 开始游戏。\n(金额需在 {min_fee} - {max_fee} 之间)\n\n"
        help_message += f"【规则】\n游戏共10层，每层机器人都会提示你当前的奖金和下一层的成功率。你需要在 {timeout} 秒内回复【继续】或【放弃】来决定你的命运！超时将自动放弃并结算当前奖金。\n\n"
        help_message += "【概率详情】\n"
        levels = config.get("levels", [])
        for i, level in enumerate(levels):
            rate = int(level.get("success_rate", 0) * 100)
            help_message += f" - 前往第 {i + 1} 层：{rate}% 成功率\n"
        help_message += "\n祝你好运，挑战者！"
        yield event.plain_result(help_message)
        return

    entry_fee_str = args[1]
    if not entry_fee_str.isdigit():
        yield event.plain_result("指令格式不正确哦！\n金额必须是纯数字。")
        return

    entry_fee = int(entry_fee_str)
    result = self.game_mechanics_service.start_wheel_of_fate(user_id, entry_fee)
    
    if result and result.get("message"):
        user = self.user_repo.get_by_id(user_id)
        user_nickname = user.nickname if user and user.nickname else user_id
        formatted_message = result["message"].replace(f"[CQ:at,qq={user_id}]", f"@{user_nickname}")
        yield event.plain_result(formatted_message)

async def continue_wheel_of_fate(self: "FishingPlugin", event: AstrMessageEvent):
    """处理命运之轮的“继续”指令"""
    user_id = self._get_effective_user_id(event)
    # 直接将请求交给 Service 层，它会处理所有逻辑
    result = self.game_mechanics_service.continue_wheel_of_fate(user_id)
    if result and result.get("message"):
        user = self.user_repo.get_by_id(user_id)
        user_nickname = user.nickname if user and user.nickname else user_id
        formatted_message = result["message"].replace(f"[CQ:at,qq={user_id}]", f"@{user_nickname}")
        yield event.plain_result(formatted_message)

async def stop_wheel_of_fate(self: "FishingPlugin", event: AstrMessageEvent):
    """处理命运之轮的“放弃”指令"""
    user_id = self._get_effective_user_id(event)
    # 直接将请求交给 Service 层，它会处理所有逻辑
    result = self.game_mechanics_service.cash_out_wheel_of_fate(user_id)
    if result and result.get("message"):
        user = self.user_repo.get_by_id(user_id)
        user_nickname = user.nickname if user and user.nickname else user_id
        formatted_message = result["message"].replace(f"[CQ:at,qq={user_id}]", f"@{user_nickname}")
        yield event.plain_result(formatted_message)

async def sicbo(self: "FishingPlugin", event: AstrMessageEvent):
    """处理骰宝游戏指令"""
    user_id = self._get_effective_user_id(event)
    args = event.message_str.split(" ")

    # 如果指令不完整，显示帮助信息
    if len(args) < 3:
        help_message = (
            "--- 🎲 骰子 (押大小) 玩法说明 ---\n\n"
            "【规则】\n"
            "系统将投掷三颗骰子，你可以选总点数是“大”还是“小”。\n"
            " - 🎯 小: 总点数 4 - 10\n"
            " - 🎯 大: 总点数 11 - 17\n"
            " - 🐅 豹子: 若三颗骰子点数相同 (例如 都在)，则庄家赢！\n"
            "奖金均为 1:1。\n\n"
            "【指令格式】\n"
            "`/骰子 <大或小> <金币>`\n"
            "例如: `/骰子 大 1000`"
        )
        yield event.plain_result(help_message)
        return

    bet_type = args[1]
    amount_str = args[2]

    if not amount_str.isdigit():
        yield event.plain_result("❌ 押注金额必须是纯数字！")
        return
    
    amount = int(amount_str)

    # 调用核心服务逻辑
    result = self.game_mechanics_service.play_sicbo(user_id, bet_type, amount)

    # 根据服务返回的结果，构建回复消息
    if not result["success"]:
        yield event.plain_result(result["message"])
        return

    dice_emojis = {1: '⚀', 2: '⚁', 3: '⚂', 4: '⚃', 5: '⚄', 6: '⚅'}
    dice_str = " ".join([dice_emojis.get(d, str(d)) for d in result["dice"]])
    
    message = f"🎲 开奖结果: {dice_str}  (总点数: {result['total']})\n"
    
    if result["is_triple"]:
        message += f"🐅 开出豹子！庄家通吃！\n"
    else:
        message += f"🎯 判定结果为: {result['result_type']}\n"

    if result["win"]:
        message += f"🎉 恭喜你，猜中了！\n"
        message += f"💰 你赢得了 {result['profit']:,} 金币！"
    else:
        message += f"😔 很遗憾，没猜中。\n"
        message += f"💸 你失去了 {abs(result['profit']):,} 金币。"

    message += f"\n余额: {result['new_balance']:,} 金币"
    
    yield event.plain_result(message)