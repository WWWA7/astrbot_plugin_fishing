import asyncio
from hypercorn.config import Config
from hypercorn.asyncio import serve

from astrbot.api import logger
from astrbot.api.event import filter, AstrMessageEvent
from astrbot.core.star.filter.permission import PermissionType
from astrbot.api.message_components import At, Node, Plain

from ..utils import parse_target_user_id, _is_port_available
from ..manager.server import create_app

def register_admin_handlers(plugin):
    @filter.permission_type(PermissionType.ADMIN)
    @filter.command("修改金币")
    async def modify_coins(event: AstrMessageEvent):
        """修改用户金币"""
        args = event.message_str.split(" ")
        
        # 解析目标用户ID（支持@和用户ID两种方式）
        target_user_id, error_msg = parse_target_user_id(event, args, 1)
        if error_msg:
            yield event.plain_result(error_msg)
            return
        
        # 检查金币数量参数
        if len(args) < 3:
            yield event.plain_result("❌ 请指定金币数量，例如：/修改金币 @用户 1000 或 /修改金币 123456789 1000")
            return
        
        coins = args[2]
        if not coins.isdigit():
            yield event.plain_result("❌ 金币数量必须是数字，请检查后重试。")
            return
        
        result = plugin.user_service.modify_user_coins(target_user_id, int(coins))
        if result:
            yield event.plain_result(f"✅ 成功修改用户 {target_user_id} 的金币数量为 {coins} 金币")
        else:
            yield event.plain_result("❌ 出错啦！请稍后再试。")

    @filter.permission_type(PermissionType.ADMIN)
    @filter.command("修改高级货币")
    async def modify_premium(event: AstrMessageEvent):
        """修改用户高级货币"""
        args = event.message_str.split(" ")
        
        # 解析目标用户ID（支持@和用户ID两种方式）
        target_user_id, error_msg = parse_target_user_id(event, args, 1)
        if error_msg:
            yield event.plain_result(error_msg)
            return
        
        # 检查高级货币数量参数
        if len(args) < 3:
            yield event.plain_result("❌ 请指定高级货币数量，例如：/修改高级货币 @用户 100 或 /修改高级货币 123456789 100")
            return
        
        premium = args[2]
        if not premium.isdigit():
            yield event.plain_result("❌ 高级货币数量必须是数字，请检查后重试。")
            return
        
        user = plugin.user_repo.get_by_id(target_user_id)
        if not user:
            yield event.plain_result("❌ 用户不存在或未注册，请检查后重试。")
            return
        user.premium_currency = int(premium)
        plugin.user_repo.update(user)
        yield event.plain_result(f"✅ 成功修改用户 {target_user_id} 的高级货币为 {premium}")

    @filter.permission_type(PermissionType.ADMIN)
    @filter.command("奖励高级货币")
    async def reward_premium(event: AstrMessageEvent):
        """奖励用户高级货币"""
        args = event.message_str.split(" ")
        
        # 解析目标用户ID（支持@和用户ID两种方式）
        target_user_id, error_msg = parse_target_user_id(event, args, 1)
        if error_msg:
            yield event.plain_result(error_msg)
            return
        
        # 检查高级货币数量参数
        if len(args) < 3:
            yield event.plain_result("❌ 请指定高级货币数量，例如：/奖励高级货币 @用户 100 或 /奖励高级货币 123456789 100")
            return
        
        premium = args[2]
        if not premium.isdigit():
            yield event.plain_result("❌ 高级货币数量必须是数字，请检查后重试。")
            return
        
        user = plugin.user_repo.get_by_id(target_user_id)
        if not user:
            yield event.plain_result("❌ 用户不存在或未注册，请检查后重试。")
            return
        user.premium_currency += int(premium)
        plugin.user_repo.update(user)
        yield event.plain_result(f"✅ 成功给用户 {target_user_id} 奖励 {premium} 高级货币")

    @filter.permission_type(PermissionType.ADMIN)
    @filter.command("扣除高级货币")
    async def deduct_premium(event: AstrMessageEvent):
        """扣除用户高级货币"""
        args = event.message_str.split(" ")
        
        # 解析目标用户ID（支持@和用户ID两种方式）
        target_user_id, error_msg = parse_target_user_id(event, args, 1)
        if error_msg:
            yield event.plain_result(error_msg)
            return
        
        # 检查高级货币数量参数
        if len(args) < 3:
            yield event.plain_result("❌ 请指定高级货币数量，例如：/扣除高级货币 @用户 100 或 /扣除高级货币 123456789 100")
            return
        
        premium = args[2]
        if not premium.isdigit():
            yield event.plain_result("❌ 高级货币数量必须是数字，请检查后重试。")
            return
        
        user = plugin.user_repo.get_by_id(target_user_id)
        if not user:
            yield event.plain_result("❌ 用户不存在或未注册，请检查后重试。")
            return
        if int(premium) > user.premium_currency:
            yield event.plain_result("❌ 扣除的高级货币不能超过用户当前拥有数量")
            return
        user.premium_currency -= int(premium)
        plugin.user_repo.update(user)
        yield event.plain_result(f"✅ 成功扣除用户 {target_user_id} 的 {premium} 高级货币")

    @filter.permission_type(PermissionType.ADMIN)
    @filter.command("全体奖励金币")
    async def reward_all_coins(event: AstrMessageEvent):
        """给所有注册用户发放金币"""
        args = event.message_str.split(" ")
        if len(args) < 2:
            yield event.plain_result("❌ 请指定奖励的金币数量，例如：/全体奖励金币 1000")
            return
        amount = args[1]
        if not amount.isdigit() or int(amount) <= 0:
            yield event.plain_result("❌ 奖励数量必须是正整数，请检查后重试。")
            return
        amount_int = int(amount)
        user_ids = plugin.user_repo.get_all_user_ids()
        if not user_ids:
            yield event.plain_result("❌ 当前没有注册用户。")
            return
        updated = 0
        for uid in user_ids:
            user = plugin.user_repo.get_by_id(uid)
            if not user:
                continue
            user.coins += amount_int
            plugin.user_repo.update(user)
            updated += 1
        yield event.plain_result(f"✅ 已向 {updated} 位用户每人发放 {amount_int} 金币")

    @filter.permission_type(PermissionType.ADMIN)
    @filter.command("全体奖励高级货币")
    async def reward_all_premium(event: AstrMessageEvent):
        """给所有注册用户发放高级货币"""
        args = event.message_str.split(" ")
        if len(args) < 2:
            yield event.plain_result("❌ 请指定奖励的高级货币数量，例如：/全体奖励高级货币 100")
            return
        amount = args[1]
        if not amount.isdigit() or int(amount) <= 0:
            yield event.plain_result("❌ 奖励数量必须是正整数，请检查后重试。")
            return
        amount_int = int(amount)
        user_ids = plugin.user_repo.get_all_user_ids()
        if not user_ids:
            yield event.plain_result("❌ 当前没有注册用户。")
            return
        updated = 0
        for uid in user_ids:
            user = plugin.user_repo.get_by_id(uid)
            if not user:
                continue
            user.premium_currency += amount_int
            plugin.user_repo.update(user)
            updated += 1
        yield event.plain_result(f"✅ 已向 {updated} 位用户每人发放 {amount_int} 高级货币")

    @filter.permission_type(PermissionType.ADMIN)
    @filter.command("全体扣除金币")
    async def deduct_all_coins(event: AstrMessageEvent):
        """从所有注册用户扣除金币（不低于0）"""
        args = event.message_str.split(" ")
        if len(args) < 2:
            yield event.plain_result("❌ 请指定扣除的金币数量，例如：/全体扣除金币 1000")
            return
        amount = args[1]
        if not amount.isdigit() or int(amount) <= 0:
            yield event.plain_result("❌ 扣除数量必须是正整数，请检查后重试。")
            return
        amount_int = int(amount)
        user_ids = plugin.user_repo.get_all_user_ids()
        if not user_ids:
            yield event.plain_result("❌ 当前没有注册用户。")
            return
        affected = 0
        total_deducted = 0
        for uid in user_ids:
            user = plugin.user_repo.get_by_id(uid)
            if not user:
                continue
            if user.coins <= 0:
                continue
            deduct = amount_int if user.coins >= amount_int else user.coins
            if deduct <= 0:
                continue
            user.coins -= deduct
            plugin.user_repo.update(user)
            affected += 1
            total_deducted += deduct
        yield event.plain_result(f"✅ 已从 {affected} 位用户总计扣除 {total_deducted} 金币（每人至多 {amount_int}）")

    @filter.permission_type(PermissionType.ADMIN)
    @filter.command("全体扣除高级货币")
    async def deduct_all_premium(event: AstrMessageEvent):
        """从所有注册用户扣除高级货币（不低于0）"""
        args = event.message_str.split(" ")
        if len(args) < 2:
            yield event.plain_result("❌ 请指定扣除的高级货币数量，例如：/全体扣除高级货币 100")
            return
        amount = args[1]
        if not amount.isdigit() or int(amount) <= 0:
            yield event.plain_result("❌ 扣除数量必须是正整数，请检查后重试。")
            return
        amount_int = int(amount)
        user_ids = plugin.user_repo.get_all_user_ids()
        if not user_ids:
            yield event.plain_result("❌ 当前没有注册用户。")
            return
        affected = 0
        total_deducted = 0
        for uid in user_ids:
            user = plugin.user_repo.get_by_id(uid)
            if not user:
                continue
            if user.premium_currency <= 0:
                continue
            deduct = amount_int if user.premium_currency >= amount_int else user.premium_currency
            if deduct <= 0:
                continue
            user.premium_currency -= deduct
            plugin.user_repo.update(user)
            affected += 1
            total_deducted += deduct
        yield event.plain_result(f"✅ 已从 {affected} 位用户总计扣除 {total_deducted} 高级货币（每人至多 {amount_int}）")
    @filter.permission_type(PermissionType.ADMIN)
    @filter.command("奖励金币")
    async def reward_coins(event: AstrMessageEvent):
        """奖励用户金币"""
        args = event.message_str.split(" ")
        
        # 解析目标用户ID（支持@和用户ID两种方式）
        target_user_id, error_msg = parse_target_user_id(event, args, 1)
        if error_msg:
            yield event.plain_result(error_msg)
            return
        
        # 检查金币数量参数
        if len(args) < 3:
            yield event.plain_result("❌ 请指定金币数量，例如：/奖励金币 @用户 1000 或 /奖励金币 123456789 1000")
            return
        
        coins = args[2]
        if not coins.isdigit():
            yield event.plain_result("❌ 金币数量必须是数字，请检查后重试。")
            return
        
        current_coins = plugin.user_service.get_user_currency(target_user_id)
        if current_coins is None:
            yield event.plain_result("❌ 用户不存在或未注册，请检查后重试。")
            return
        result = plugin.user_service.modify_user_coins(target_user_id, int(current_coins.get('coins') + int(coins)))
        if result:
            yield event.plain_result(f"✅ 成功给用户 {target_user_id} 奖励 {coins} 金币")
        else:
            yield event.plain_result("❌ 出错啦！请稍后再试。")

    @filter.permission_type(PermissionType.ADMIN)
    @filter.command("扣除金币")
    async def deduct_coins(event: AstrMessageEvent):
        """扣除用户金币"""
        args = event.message_str.split(" ")
        
        # 解析目标用户ID（支持@和用户ID两种方式）
        target_user_id, error_msg = parse_target_user_id(event, args, 1)
        if error_msg:
            yield event.plain_result(error_msg)
            return
        
        # 检查金币数量参数
        if len(args) < 3:
            yield event.plain_result("❌ 请指定金币数量，例如：/扣除金币 @用户 1000 或 /扣除金币 123456789 1000")
            return
        
        coins = args[2]
        if not coins.isdigit():
            yield event.plain_result("❌ 金币数量必须是数字，请检查后重试。")
            return
        
        current_coins = plugin.user_service.get_user_currency(target_user_id)
        if current_coins is None:
            yield event.plain_result("❌ 用户不存在或未注册，请检查后重试。")
            return
        if int(coins) > current_coins.get('coins'):
            yield event.plain_result("❌ 扣除的金币数量不能超过用户当前拥有的金币数量")
            return
        result = plugin.user_service.modify_user_coins(target_user_id, int(current_coins.get('coins') - int(coins)))
        if result:
            yield event.plain_result(f"✅ 成功扣除用户 {target_user_id} 的 {coins} 金币")
        else:
            yield event.plain_result("❌ 出错啦！请稍后再试。")

    @filter.permission_type(PermissionType.ADMIN)
    @filter.command("开启钓鱼后台管理")
    async def start_admin(event: AstrMessageEvent):
        if plugin.web_admin_task and not plugin.web_admin_task.done():
            yield event.plain_result("❌ 钓鱼后台管理已经在运行中")
            return
        yield event.plain_result("🔄 正在启动钓鱼插件Web管理后台...")

        if not await _is_port_available(plugin.port):
            yield event.plain_result(f"❌ 端口 {plugin.port} 已被占用，请更换端口后重试")
            return

        try:
            services_to_inject = {
                "item_template_service": plugin.item_template_service,
                "user_service": plugin.user_service,
                "market_service": plugin.market_service,
                "fishing_zone_service": plugin.fishing_zone_service,
            }
            app = create_app(
                secret_key=plugin.secret_key,
                services=services_to_inject
            )
            config = Config()
            config.bind = [f"0.0.0.0:{plugin.port}"]
            plugin.web_admin_task = asyncio.create_task(serve(app, config))

            # 等待服务启动
            for i in range(10):
                if await plugin._check_port_active():
                    break
                await asyncio.sleep(1)
            else:
                raise Exception("⌛ 启动超时，请检查防火墙设置")

            await asyncio.sleep(1)  # 等待服务启动

            yield event.plain_result(f"✅ 钓鱼后台已启动！\n🔗请访问 http://localhost:{plugin.port}/admin\n🔑 密钥请到配置文件中查看\n\n⚠️ 重要提示：\n• 如需公网访问，请自行配置端口转发和防火墙规则\n• 确保端口 {plugin.port} 已开放并映射到公网IP\n• 建议使用反向代理（如Nginx）增强安全性")
        except Exception as e:
            logger.error(f"启动后台失败: {e}", exc_info=True)
            yield event.plain_result(f"❌ 启动后台失败: {e}")

    @filter.permission_type(PermissionType.ADMIN)
    @filter.command("关闭钓鱼后台管理")
    async def stop_admin(event: AstrMessageEvent):
        """关闭钓鱼后台管理"""
        if not hasattr(plugin, "web_admin_task") or not plugin.web_admin_task or plugin.web_admin_task.done():
            yield event.plain_result("❌ 钓鱼后台管理没有在运行中")
            return

        try:
            # 1. 请求取消任务
            plugin.web_admin_task.cancel()
            # 2. 等待任务实际被取消
            await plugin.web_admin_task
        except asyncio.CancelledError:
            # 3. 捕获CancelledError，这是成功关闭的标志
            logger.info("钓鱼插件Web管理后台已成功关闭")
            yield event.plain_result("✅ 钓鱼后台已关闭")
        except Exception as e:
            # 4. 捕获其他可能的意外错误
            logger.error(f"关闭钓鱼后台管理时发生意外错误: {e}", exc_info=True)
            yield event.plain_result(f"❌ 关闭钓鱼后台管理失败: {e}")

    @filter.permission_type(PermissionType.ADMIN)
    @filter.command("同步道具", alias={"管理员 同步道具"})
    async def sync_items_from_initial_data(event: AstrMessageEvent):
        """从 initial_data.py 同步道具数据到数据库。"""
        try:
            plugin.data_setup_service.create_initial_items()
            yield event.plain_result(
                '✅ 成功执行初始道具同步操作。\n请检查后台或使用 /道具 命令确认数据。'
            )
        except Exception as e:
            logger.error(f"执行 sync_items_from_initial_data 命令时出错: {e}", exc_info=True)
            yield event.plain_result(f"❌ 操作失败，请查看后台日志。错误: {e}")

    @filter.permission_type(PermissionType.ADMIN)
    @filter.command("代理上线")
    async def impersonate_start(event: AstrMessageEvent):
        """管理员开始扮演一名用户。"""
        admin_id = event.get_sender_id()
        args = event.message_str.split(" ")
        
        # 如果已经在线，则显示当前状态
        if admin_id in plugin.impersonation_map:
            target_user_id = plugin.impersonation_map[admin_id]
            target_user = plugin.user_repo.get_by_id(target_user_id)
            nickname = target_user.nickname if target_user else '未知用户'
            yield event.plain_result(f"您当前正在代理用户: {nickname} ({target_user_id})")
            return
        
        # 解析目标用户ID（支持@和用户ID两种方式）
        target_user_id, error_msg = parse_target_user_id(event, args, 1)
        if error_msg:
            yield event.plain_result(f"用法: /代理上线 <目标用户ID> 或 /代理上线 @用户\n{error_msg}")
            return

        target_user = plugin.user_repo.get_by_id(target_user_id)
        if not target_user:
            yield event.plain_result("❌ 目标用户不存在。")
            return

        plugin.impersonation_map[admin_id] = target_user_id
        nickname = target_user.nickname
        yield event.plain_result(f"✅ 您已成功代理用户: {nickname} ({target_user_id})。\n现在您发送的所有游戏指令都将以该用户的身份执行。\n使用 /代理下线 结束代理。")

    @filter.permission_type(PermissionType.ADMIN)
    @filter.command("代理下线")
    async def impersonate_stop(event: AstrMessageEvent):
        """管理员结束扮演用户。"""
        admin_id = event.get_sender_id()
        if admin_id in plugin.impersonation_map:
            del plugin.impersonation_map[admin_id]
            yield event.plain_result("✅ 您已成功结束代理。")
        else:
            yield event.plain_result("❌ 您当前没有在代理任何用户。")

    plugin.context.add_handler(modify_coins)
    plugin.context.add_handler(modify_premium)
    plugin.context.add_handler(reward_premium)
    plugin.context.add_handler(deduct_premium)
    plugin.context.add_handler(reward_all_coins)
    plugin.context.add_handler(reward_all_premium)
    plugin.context.add_handler(deduct_all_coins)
    plugin.context.add_handler(deduct_all_premium)
    plugin.context.add_handler(reward_coins)
    plugin.context.add_handler(deduct_coins)
    plugin.context.add_handler(start_admin)
    plugin.context.add_handler(stop_admin)
    plugin.context.add_handler(sync_items_from_initial_data)
    plugin.context.add_handler(impersonate_start)
    plugin.context.add_handler(impersonate_stop)
