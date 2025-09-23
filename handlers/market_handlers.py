from astrbot.api.event import filter, AstrMessageEvent
from ..utils import format_rarity_display, parse_target_user_id

async def sell_all(self, event: AstrMessageEvent):
    """卖出用户所有鱼"""
    user_id = self._get_effective_user_id(event)
    if result := self.inventory_service.sell_all_fish(user_id):
        yield event.plain_result(result["message"])
    else:
        yield event.plain_result("❌ 出错啦！请稍后再试。")

async def sell_keep(self, event: AstrMessageEvent):
    """卖出用户鱼，但保留每种鱼一条"""
    user_id = self._get_effective_user_id(event)
    if result := self.inventory_service.sell_all_fish(user_id, keep_one=True):
        yield event.plain_result(result["message"])
    else:
        yield event.plain_result("❌ 出错啦！请稍后再试。")

async def sell_everything(self, event: AstrMessageEvent):
    """砸锅卖铁：出售所有未锁定且未装备的鱼竿、饰品和全部鱼类"""
    user_id = self._get_effective_user_id(event)
    if result := self.inventory_service.sell_everything_except_locked(user_id):
        if result["success"]:
            yield event.plain_result(result["message"])
        else:
            yield event.plain_result(f"❌ 砸锅卖铁失败：{result['message']}")
    else:
        yield event.plain_result("❌ 出错啦！请稍后再试。")

async def sell_by_rarity(self, event: AstrMessageEvent):
    """按稀有度出售鱼"""
    user_id = self._get_effective_user_id(event)
    args = event.message_str.split(" ")
    if len(args) < 2:
        yield event.plain_result("❌ 请指定要出售的稀有度，例如：/出售稀有度 3")
        return
    rarity = args[1]
    if not rarity.isdigit() or int(rarity) < 1 or int(rarity) > 5:
        yield event.plain_result("❌ 稀有度必须是1到5之间的数字，请检查后重试。")
        return
    if result := self.inventory_service.sell_fish_by_rarity(user_id, int(rarity)):
        yield event.plain_result(result["message"])
    else:
        yield event.plain_result("❌ 出错啦！请稍后再试。")

async def sell_rod(self, event: AstrMessageEvent):
    """出售鱼竿"""
    user_id = self._get_effective_user_id(event)
    args = event.message_str.split(" ")
    if len(args) < 2:
        yield event.plain_result("❌ 请指定要出售的鱼竿 ID，例如：/出售鱼竿 12")
        return
    rod_instance_id = args[1]
    if not rod_instance_id.isdigit():
        yield event.plain_result("❌ 鱼竿 ID 必须是数字，请检查后重试。")
        return
    if result := self.inventory_service.sell_rod(user_id, int(rod_instance_id)):
        if result["success"]:
            yield event.plain_result(result["message"])
        else:
            yield event.plain_result(f"❌ 出售鱼竿失败：{result['message']}")
    else:
        yield event.plain_result("❌ 出错啦！请稍后再试。")

async def sell_all_rods(self, event: AstrMessageEvent):
    """出售用户所有鱼竿"""
    user_id = self._get_effective_user_id(event)
    result = self.inventory_service.sell_all_rods(user_id)
    if result:
        yield event.plain_result(result["message"])
    else:
        yield event.plain_result("❌ 出错啦！请稍后再试。")

async def sell_accessories(self, event: AstrMessageEvent):
    """出售饰品"""
    user_id = self._get_effective_user_id(event)
    args = event.message_str.split(" ")
    if len(args) < 2:
        yield event.plain_result("❌ 请指定要出售的饰品 ID，例如：/出售饰品 15")
        return
    accessory_instance_id = args[1]
    if not accessory_instance_id.isdigit():
        yield event.plain_result("❌ 饰品 ID 必须是数字，请检查后重试。")
        return
    result = self.inventory_service.sell_accessory(user_id, int(accessory_instance_id))
    if result:
        if result["success"]:
            yield event.plain_result(result["message"])
        else:
            yield event.plain_result(f"❌ 出售饰品失败：{result['message']}")
    else:
        yield event.plain_result("❌ 出错啦！请稍后再试。")

async def sell_all_accessories(self, event: AstrMessageEvent):
    """出售用户所有饰品"""
    user_id = self._get_effective_user_id(event)
    result = self.inventory_service.sell_all_accessories(user_id)
    if result:
        yield event.plain_result(result["message"])
    else:
        yield event.plain_result("❌ 出错啦！请稍后再试。")

async def shop(self, event: AstrMessageEvent):
    """查看商店：/商店 [商店ID]"""
    args = event.message_str.split(" ")
    # /商店 → 列表
    if len(args) == 1:
        result = self.shop_service.get_shops()
        if not result or not result.get("success"):
            yield event.plain_result("❌ 出错啦！请稍后再试。")
            return
        shops = result.get("shops", [])
        if not shops:
            yield event.plain_result("🛒 当前没有开放的商店。")
            return
        msg = "【🛒 商店列表】\n"
        for s in shops:
            stype = s.get("shop_type", "normal")
            type_name = "普通" if stype == "normal" else ("高级" if stype == "premium" else "限时")
            status = "🟢 营业中" if s.get("is_active") else "🔴 已关闭"
            msg += f" - {s.get('name')} (ID: {s.get('shop_id')}) [{type_name}] {status}\n"
            if s.get("description"):
                msg += f"   - {s.get('description')}\n"
        msg += "\n💡 使用「商店 商店ID」查看详情；使用「商店购买 商店ID 商品ID [数量]」购买\n"
        yield event.plain_result(msg)
        return

    # /商店 <ID> → 详情
    shop_id = args[1]
    if not shop_id.isdigit():
        yield event.plain_result("❌ 商店ID必须是数字")
        return
    detail = self.shop_service.get_shop_details(int(shop_id))
    if not detail.get("success"):
        yield event.plain_result(f"❌ {detail.get('message','查询失败')}")
        return
    shop = detail["shop"]
    items = detail.get("items", [])
    msg = f"【🛒 {shop.get('name')}】(ID: {shop.get('shop_id')})\n"
    if shop.get("description"):
        msg += f"📖 {shop.get('description')}\n"
    if not items:
        msg += "\n📭 当前没有在售商品。"
        yield event.plain_result(msg)
        return
    msg += "\n🛍️ 【在售商品】\n"
    msg += "═" * 50 + "\n"
    for i, e in enumerate(items):
        item = e["item"]
        costs = e["costs"]
        rewards = e.get("rewards", [])
        
        # 获取商品稀有度和emoji
        rarity = 1
        item_emoji = "📦"
        rarity_stars = "⭐"
        
        if rewards:
            # 如果奖励物品超过2个，使用礼包emoji
            if len(rewards) > 2:
                item_emoji = "🎁"
                # 计算平均稀有度
                total_rarity = 0
                for reward in rewards:
                    if reward["reward_type"] == "rod":
                        rod_template = self.item_template_repo.get_rod_by_id(reward.get("reward_item_id"))
                        if rod_template:
                            total_rarity += rod_template.rarity
                    elif reward["reward_type"] == "bait":
                        bait_template = self.item_template_repo.get_bait_by_id(reward.get("reward_item_id"))
                        if bait_template:
                            total_rarity += bait_template.rarity
                    elif reward["reward_type"] == "accessory":
                        accessory_template = self.item_template_repo.get_accessory_by_id(reward.get("reward_item_id"))
                        if accessory_template:
                            total_rarity += accessory_template.rarity
                    elif reward["reward_type"] == "item":
                        item_template = self.item_template_repo.get_by_id(reward.get("reward_item_id"))
                        if item_template:
                            total_rarity += item_template.rarity
                rarity = max(1, total_rarity // len(rewards))  # 取平均稀有度，最少1星
            else:
                 # 单个或两个物品，使用第一个物品的类型和稀有度
                 reward = rewards[0]
                 if reward["reward_type"] == "rod":
                     rod_template = self.item_template_repo.get_rod_by_id(reward.get("reward_item_id"))
                     if rod_template:
                         rarity = rod_template.rarity
                         item_emoji = "🎣"
                 elif reward["reward_type"] == "bait":
                     bait_template = self.item_template_repo.get_bait_by_id(reward.get("reward_item_id"))
                     if bait_template:
                         rarity = bait_template.rarity
                         item_emoji = "🪱"
                 elif reward["reward_type"] == "accessory":
                     accessory_template = self.item_template_repo.get_accessory_by_id(reward.get("reward_item_id"))
                     if accessory_template:
                         rarity = accessory_template.rarity
                         item_emoji = "💍"
                 elif reward["reward_type"] == "item":
                     item_template = self.item_template_repo.get_by_id(reward.get("reward_item_id"))
                     if item_template:
                         rarity = item_template.rarity
                         # 根据道具名称选择合适的emoji
                         item_name = item_template.name.lower()
                         if "沙漏" in item_name or "时运" in item_name:
                             item_emoji = "⏳"
                         elif "令牌" in item_name or "通行证" in item_name:
                             item_emoji = "🎫"
                         elif "护符" in item_name or "神佑" in item_name:
                             item_emoji = "🛡️"
                         elif "钱袋" in item_name:
                             item_emoji = "💰"
                         elif "海图" in item_name or "地图" in item_name:
                             item_emoji = "🗺️"
                         elif "香" in item_name or "驱灵" in item_name:
                             item_emoji = "🕯️"
                         elif "许可证" in item_name or "擦弹" in item_name:
                             item_emoji = "📋"
                         elif "符" in item_name or "符文" in item_name:
                             item_emoji = "🔮"
                         elif "海灵" in item_name or "守护" in item_name:
                             item_emoji = "🌊"
                         elif "斗篷" in item_name or "暗影" in item_name:
                             item_emoji = "🪶"
                         elif "药水" in item_name or "幸运" in item_name:
                             item_emoji = "🧪"
                         elif "声呐" in item_name or "便携" in item_name:
                             item_emoji = "📡"
                         else:
                             item_emoji = "📦"  # 默认道具emoji 
        
        # 根据稀有度设置星星
        if rarity == 1:
            rarity_stars = "⭐"
        elif rarity == 2:
            rarity_stars = "⭐⭐"
        elif rarity == 3:
            rarity_stars = "⭐⭐⭐"
        elif rarity == 4:
            rarity_stars = "⭐⭐⭐⭐"
        elif rarity == 5:
            rarity_stars = "⭐⭐⭐⭐⭐"
        else:
            rarity_stars = "⭐" * min(rarity, 10)
            if rarity > 10:
                rarity_stars += "+"
        
        # 按组ID分组成本
        cost_groups = {}
        for c in costs:
            group_id = c.get("group_id", 1)  # 默认组ID为1
            if group_id not in cost_groups:
                cost_groups[group_id] = []
            cost_groups[group_id].append(c)
        
        # 构建成本字符串
        group_parts = []
        for group_id in sorted(cost_groups.keys()):
            group_costs = cost_groups[group_id]
            group_parts_inner = []
            
            for c in group_costs:
                cost_text = ""
                if c["cost_type"] == "coins":
                    cost_text = f"💰 {c['cost_amount']} 金币"
                elif c["cost_type"] == "premium":
                    cost_text = f"💎 {c['cost_amount']} 高级货币"
                elif c["cost_type"] == "item":
                    # 获取道具名称
                    item_template = self.item_template_repo.get_by_id(c.get("cost_item_id"))
                    item_name = item_template.name if item_template else f"道具#{c.get('cost_item_id')}"
                    cost_text = f"🎁 {item_name} x{c['cost_amount']}"
                elif c["cost_type"] == "fish":
                    # 获取鱼类名称
                    fish_template = self.item_template_repo.get_fish_by_id(c.get("cost_item_id"))
                    fish_name = fish_template.name if fish_template else f"鱼类#{c.get('cost_item_id')}"
                    cost_text = f"🐟 {fish_name} x{c['cost_amount']}"
                elif c["cost_type"] == "rod":
                    # 获取鱼竿名称
                    rod_template = self.item_template_repo.get_rod_by_id(c.get("cost_item_id"))
                    rod_name = rod_template.name if rod_template else f"鱼竿#{c.get('cost_item_id')}"
                    cost_text = f"🎣 {rod_name} x{c['cost_amount']}"
                elif c["cost_type"] == "accessory":
                    # 获取饰品名称
                    accessory_template = self.item_template_repo.get_accessory_by_id(c.get("cost_item_id"))
                    accessory_name = accessory_template.name if accessory_template else f"饰品#{c.get('cost_item_id')}"
                    cost_text = f"💍 {accessory_name} x{c['cost_amount']}"
                
                group_parts_inner.append(cost_text)
            
            # 根据组内关系连接
            if len(group_parts_inner) == 1:
                group_parts.append(group_parts_inner[0])
            else:
                # 检查组内关系
                relation = group_costs[0].get("cost_relation", "and")
                if relation == "or":
                    group_parts.append(f"({' OR '.join(group_parts_inner)})")
                else:  # and
                    group_parts.append(" + ".join(group_parts_inner))
        
        # 连接不同组（组间是AND关系）
        cost_str = " + ".join(group_parts) if group_parts else "免费"
        stock_str = "无限" if item.get("stock_total") is None else f"{item.get('stock_sold',0)}/{item.get('stock_total')}"
        
        # 获取限购信息
        per_user_limit = item.get("per_user_limit")
        per_user_daily_limit = item.get("per_user_daily_limit")
        
        # 获取限时信息
        start_time = item.get("start_time")
        end_time = item.get("end_time")
        
        # 美化输出格式
        msg += f"┌─ {item_emoji} {item['name']} {rarity_stars}\n"
        msg += f"├─ 价格: {cost_str}\n"
        msg += f"├─ 库存: {stock_str}\n"
        msg += f"├─ ID: {item['item_id']}\n"
        
        # 添加限购信息
        limit_info = []
        if per_user_limit is not None:
            limit_info.append(f"每人限购: {per_user_limit}")
        if per_user_daily_limit is not None:
            limit_info.append(f"每日限购: {per_user_daily_limit}")
        
        if limit_info:
            msg += f"├─ 限购: {' | '.join(limit_info)}\n"
        
        # 添加限时信息
        time_info = []
        current_time = None
        from datetime import datetime
        try:
            current_time = datetime.now()
        except:
            pass
        
        if start_time:
            if isinstance(start_time, str):
                try:
                    start_time = datetime.fromisoformat(start_time.replace("Z", "+00:00"))
                except:
                    pass
            if isinstance(start_time, datetime):
                if current_time and current_time < start_time:
                    time_info.append(f"未开始: {start_time.strftime('%m-%d %H:%M')}")
                else:
                    time_info.append(f"开始: {start_time.strftime('%m-%d %H:%M')}")
        
        if end_time:
            if isinstance(end_time, str):
                try:
                    end_time = datetime.fromisoformat(end_time.replace("Z", "+00:00"))
                except:
                    pass
            if isinstance(end_time, datetime):
                if current_time and current_time > end_time:
                    time_info.append(f"已结束: {end_time.strftime('%m-%d %H:%M')}")
                else:
                    time_info.append(f"结束: {end_time.strftime('%m-%d %H:%M')}")
        
        if time_info:
            msg += f"├─ 限时: {' | '.join(time_info)}\n"
        
        # 如果包含多个物品（≥2），显示礼包包含的物品
        if len(rewards) >= 2:
            msg += "├─ 包含物品:\n"
            for reward in rewards:
                item_name = "未知物品"
                item_emoji = "📦"
                
                if reward["reward_type"] == "rod":
                    rod_template = self.item_template_repo.get_rod_by_id(reward.get("reward_item_id"))
                    if rod_template:
                        item_name = rod_template.name
                        item_emoji = "🎣"
                elif reward["reward_type"] == "bait":
                    bait_template = self.item_template_repo.get_bait_by_id(reward.get("reward_item_id"))
                    if bait_template:
                        item_name = bait_template.name
                        item_emoji = "🪱"
                elif reward["reward_type"] == "accessory":
                    accessory_template = self.item_template_repo.get_accessory_by_id(reward.get("reward_item_id"))
                    if accessory_template:
                        item_name = accessory_template.name
                        item_emoji = "💍"
                elif reward["reward_type"] == "item":
                    item_template = self.item_template_repo.get_by_id(reward.get("reward_item_id"))
                    if item_template:
                        item_name = item_template.name
                        item_emoji = "🎁"
                elif reward["reward_type"] == "fish":
                    fish_template = self.item_template_repo.get_fish_by_id(reward.get("reward_item_id"))
                    if fish_template:
                        item_name = fish_template.name
                        item_emoji = "🐟"
                elif reward["reward_type"] == "coins":
                    item_name = "金币"
                    item_emoji = "💰"
                
                msg += f"│   • {item_emoji} {item_name}"
                if reward.get("reward_quantity", 1) > 1:
                    msg += f" x{reward['reward_quantity']}"
                msg += "\n"
        
        if item.get("description"):
            msg += f"└─ {item['description']}\n"
        else:
            msg += "└─\n"
        
        # 添加商品之间的分隔符（除了最后一个商品）
        if i < len(items) - 1:
            msg += "─" * 30 + "\n"
    msg += "═" * 50 + "\n"
    msg += "💡 购买：商店购买 商店ID 商品ID [数量]\n"
    msg += "示例：商店购买 1 2 5"
    yield event.plain_result(msg)

async def buy_in_shop(self, event: AstrMessageEvent):
    """按商店池购买：/商店购买 <商店ID> <商品ID> [数量]"""
    user_id = self._get_effective_user_id(event)
    args = event.message_str.split(" ")
    if len(args) < 3:
        yield event.plain_result("❌ 用法：商店购买 商店ID 商品ID [数量]")
        return
    shop_id, item_id = args[1], args[2]
    if not shop_id.isdigit() or not item_id.isdigit():
        yield event.plain_result("❌ 商店ID与商品ID必须是数字")
        return
    qty = 1
    if len(args) >= 4:
        if not args[3].isdigit() or int(args[3]) <= 0:
            yield event.plain_result("❌ 数量必须是正整数")
            return
        qty = int(args[3])
    result = self.shop_service.purchase_item(user_id, int(item_id), qty)
    if result.get("success"):
        yield event.plain_result(result["message"])
    else:
        error_message = result.get('message', '购买失败')
        # 检查错误消息是否已经包含❌符号，避免重复添加
        if error_message.startswith("❌"):
            yield event.plain_result(error_message)
        else:
            yield event.plain_result(f"❌ {error_message}")


async def market(self, event: AstrMessageEvent):
    """查看市场"""
    result = self.market_service.get_market_listings()
    if result["success"]:
        message = "【🛒 市场】\n\n"
        if result["rods"]:
            message += "【🎣 鱼竿】:\n"
            for rod in result["rods"]:
                message += f" - {rod['item_name']} 精{rod['refine_level']} (ID: {rod['market_id']}) - 价格: {rod['price']} 金币\n"
                message += f" - 售卖人： {rod['seller_nickname']}\n\n"
        else:
            message += "🎣 市场中没有鱼竿可供购买。\n\n"
        if result["accessories"]:
            message += "【💍 饰品】:\n"
            for accessory in result["accessories"]:
                message += f" - {accessory['item_name']} 精{accessory['refine_level']} (ID: {accessory['market_id']}) - 价格: {accessory['price']} 金币\n"
                message += f" - 售卖人： {accessory['seller_nickname']}\n\n"
        else:
            message += "💍 市场中没有饰品可供购买。\n\n"
        if result["items"]:
            message += "【🎁 道具】:\n"
            for item in result["items"]:
                message += f" - {item['item_name']} (ID: {item['market_id']}) - 价格: {item['price']} 金币\n"
                message += f" - 售卖人： {item['seller_nickname']}\n\n"
        else:
            message += "🎁 市场中没有道具可供购买。\n"
        yield event.plain_result(message)
    else:
        yield event.plain_result(f"❌ 出错啦！{result['message']}")

async def list_rod(self, event: AstrMessageEvent):
    """上架鱼竿到市场"""
    user_id = self._get_effective_user_id(event)
    args = event.message_str.split(" ")
    if len(args) < 3:
        yield event.plain_result("❌ 请指定要上架的鱼竿 ID和价格，例如：/上架鱼竿 12 1000")
        return
    rod_instance_id = args[1]
    if not rod_instance_id.isdigit():
        yield event.plain_result("❌ 鱼竿 ID 必须是数字，请检查后重试。")
        return
    price = args[2]
    if not price.isdigit() or int(price) <= 0:
        yield event.plain_result("❌ 上架价格必须是正整数，请检查后重试。")
        return
    result = self.market_service.put_item_on_sale(user_id, "rod", int(rod_instance_id), int(price))
    if result:
        if result["success"]:
            yield event.plain_result(result["message"])
        else:
            yield event.plain_result(f"❌ 上架鱼竿失败：{result['message']}")
    else:
        yield event.plain_result("❌ 出错啦！请稍后再试。")

async def list_accessories(self, event: AstrMessageEvent):
    """上架饰品到市场"""
    user_id = self._get_effective_user_id(event)
    args = event.message_str.split(" ")
    if len(args) < 3:
        yield event.plain_result("❌ 请指定要上架的饰品 ID和价格，例如：/上架饰品 15 1000")
        return
    accessory_instance_id = args[1]
    if not accessory_instance_id.isdigit():
        yield event.plain_result("❌ 饰品 ID 必须是数字，请检查后重试。")
        return
    price = args[2]
    if not price.isdigit() or int(price) <= 0:
        yield event.plain_result("❌ 上架价格必须是正整数，请检查后重试。")
        return
    result = self.market_service.put_item_on_sale(user_id, "accessory", int(accessory_instance_id), int(price))
    if result:
        if result["success"]:
            yield event.plain_result(result["message"])
        else:
            yield event.plain_result(f"❌ 上架饰品失败：{result['message']}")
    else:
        yield event.plain_result("❌ 出错啦！请稍后再试。")

async def list_item(self, event: AstrMessageEvent):
    """上架道具到市场"""
    user_id = self._get_effective_user_id(event)
    args = event.message_str.split(" ")
    if len(args) < 3:
        yield event.plain_result("❌ 请指定要上架的道具 ID和价格，例如：/上架道具 1 1000")
        return
    item_id = args[1]
    if not item_id.isdigit():
        yield event.plain_result("❌ 道具 ID 必须是数字，请检查后重试。")
        return
    price = args[2]
    if not price.isdigit() or int(price) <= 0:
        yield event.plain_result("❌ 上架价格必须是正整数，请检查后重试。")
        return
    result = self.market_service.put_item_on_sale(user_id, "item", int(item_id), int(price))
    if result:
        if result["success"]:
            yield event.plain_result(result["message"])
        else:
            yield event.plain_result(f"❌ 上架道具失败：{result['message']}")
    else:
        yield event.plain_result("❌ 出错啦！请稍后再试。")

async def buy_item(self, event: AstrMessageEvent):
    """购买市场上的物品"""
    user_id = self._get_effective_user_id(event)
    args = event.message_str.split(" ")
    if len(args) < 2:
        yield event.plain_result("❌ 请指定要购买的物品 ID，例如：/购买 12")
        return
    item_instance_id = args[1]
    if not item_instance_id.isdigit():
        yield event.plain_result("❌ 物品 ID 必须是数字，请检查后重试。")
        return
    result = self.market_service.buy_market_item(user_id, int(item_instance_id))
    if result:
        if result["success"]:
            yield event.plain_result(result["message"])
        else:
            yield event.plain_result(f"❌ 购买失败：{result['message']}")
    else:
        yield event.plain_result("❌ 出错啦！请稍后再试。")

async def my_listings(self, event: AstrMessageEvent):
    """查看我在市场上架的商品"""
    user_id = self._get_effective_user_id(event)
    result = self.market_service.get_user_listings(user_id)
    if result["success"]:
        listings = result["listings"]
        if not listings:
            yield event.plain_result("📦 您还没有在市场上架任何商品。")
            return
        
        message = f"【🛒 我的上架商品】共 {result['count']} 件\n\n"
        for listing in listings:
            message += f"🆔 ID: {listing.market_id}\n"
            message += f"📦 {listing.item_name}"
            if listing.refine_level > 1:
                message += f" 精{listing.refine_level}"
            message += f"\n💰 价格: {listing.price} 金币\n"
            message += f"📅 上架时间: {listing.listed_at.strftime('%Y-%m-%d %H:%M')}\n\n"
        message += "💡 使用「下架 ID」命令下架指定商品"
        yield event.plain_result(message)
    else:
        yield event.plain_result(f"❌ 查询失败：{result['message']}")

async def delist_item(self, event: AstrMessageEvent):
    """下架市场上的商品"""
    user_id = self._get_effective_user_id(event)
    args = event.message_str.split(" ")
    if len(args) < 2:
        yield event.plain_result("❌ 请指定要下架的商品 ID，例如：/下架 12\n💡 使用「我的上架」命令查看您的商品列表")
        return
    market_id = args[1]
    if not market_id.isdigit():
        yield event.plain_result("❌ 商品 ID 必须是数字，请检查后重试。")
        return
    market_id = int(market_id)
    result = self.market_service.delist_item(user_id, market_id)
    if result:
        if result["success"]:
            yield event.plain_result(result["message"])
        else:
            yield event.plain_result(f"❌ 下架失败：{result['message']}")
    else:
        yield event.plain_result("❌ 出错啦！请稍后再试。")
