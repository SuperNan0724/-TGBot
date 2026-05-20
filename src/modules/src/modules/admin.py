"""
管理模块~ 主人和管理员们的专属小本本！(｡･ω･｡)ﾉ♡
"""
import logging
import random
import string
from datetime import datetime

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CommandHandler, CallbackQueryHandler, ContextTypes

from .base_module import BaseModule
from .data_manager import DataManager

logger = logging.getLogger(__name__)

# 存储验证码 {code: owner_id}
_confirm_codes = {}


def _generate_code(length=6):
    """生成验证码~"""
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))


class Admin(BaseModule):
    """管理模块~ 主人和管理员们的专属工具！"""
    
    name = "admin"
    description = "管理命令~ 主人专属喵！"
    
    def __init__(self, bot_app=None):
        super().__init__(bot_app)
        self.dm = DataManager()
    
    def register_handlers(self, application):
        """注册所有管理命令~"""
        # ===== 管理员可用命令（管理员和主人都可用） =====
        application.add_handler(CommandHandler("add_user", self.add_user))
        application.add_handler(CommandHandler("del_user", self.del_user))
        application.add_handler(CommandHandler("list_whitelist", self.list_whitelist))
        application.add_handler(CommandHandler("admin_help", self.admin_help))
        
        # ===== 主人专属命令（仅主人可用） =====
        application.add_handler(CommandHandler("add_group", self.add_group))
        application.add_handler(CommandHandler("del_group", self.del_group))
        application.add_handler(CommandHandler("add_admin", self.add_admin))
        application.add_handler(CommandHandler("del_admin", self.del_admin))
        application.add_handler(CommandHandler("list_admin", self.list_admin))
        application.add_handler(CommandHandler("error_detail", self.error_detail))
        application.add_handler(CommandHandler("error_clean", self.error_clean))
        application.add_handler(CommandHandler("error_export", self.error_export))
        application.add_handler(CommandHandler("error_config", self.error_config))
        application.add_handler(CommandHandler("backup_data", self.backup_data))
        application.add_handler(CommandHandler("data_stats", self.data_stats))
        application.add_handler(CommandHandler("delete_user_data", self.delete_user_data))
        application.add_handler(CommandHandler("delete_user_history", self.delete_user_history))
        application.add_handler(CommandHandler("reset_logs", self.reset_logs))
        application.add_handler(CommandHandler("reset_data", self.reset_data))
        application.add_handler(CommandHandler("reset_system", self.reset_system))
        application.add_handler(CommandHandler("clear_confirm_codes", self.clear_confirm_codes))
        
        # 确认回调
        application.add_handler(CallbackQueryHandler(self.confirm_callback, pattern="^confirm_"))
    
    # ==========================================
    #  管理员可用命令（管理员和主人都可用）
    # ==========================================
    
    async def add_user(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """添加小鱼干到白名单~"""
        if not self._check_admin(update, context):
            return
        if not context.args:
            await update.message.reply_text("用法：/add_user <ID>\n要把小鱼干给谁呢~ 给我他的ID吧！")
            return
        try:
            user_id = int(context.args[0])
            if self.dm.add_user(user_id):
                await update.message.reply_text("✅ 小鱼干已添加~ 现在可以使用我啦！(｡♥‿♥｡)")
            else:
                await update.message.reply_text("😅 这个小可爱已经在鱼干库里啦~")
        except ValueError:
            await update.message.reply_text("呜… ID 格式不对呢，要输入数字哦！")
    
    async def del_user(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """移除小鱼干~"""
        if not self._check_admin(update, context):
            return
        if not context.args:
            await update.message.reply_text("用法：/del_user <ID>\n要拿走谁的小鱼干呢~")
            return
        try:
            user_id = int(context.args[0])
            if self.dm.del_user(user_id):
                await update.message.reply_text("✅ 已拿走小鱼干~")
            else:
                await update.message.reply_text("😅 这个小可爱本来就没有小鱼干呢~")
        except ValueError:
            await update.message.reply_text("呜… ID 格式不对呢！")
    
    async def list_whitelist(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """显示鱼干库~"""
        if not self._check_admin(update, context):
            return
        wl = self.dm.get_whitelist()
        users = wl["users"]
        groups = wl["groups"]
        
        msg = "📋 小南的鱼干库~\n\n"
        msg += f"🐟 小鱼干：{len(users)} 条\n"
        msg += f"🐋 大鱼干：{len(groups)} 条\n"
        
        await update.message.reply_text(msg)
    
    async def admin_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """管理员小本本~"""
        if not self._check_admin(update, context):
            return
        
        user_id = update.effective_user.id
        is_owner = self.dm.is_owner(user_id)
        
        help_text = "📖 管理员小本本喵～\n\n"
        
        # 管理员可用命令
        help_text += (
            "👤 管理员可用命令：\n"
            "/add_user - 添加白名单小鱼干喵～（主人专属喵）\n"
            "/del_user - 移除小鱼干喵～（主人专属喵）\n"
            "/list_whitelist - 显示鱼干库喵～（主人专属喵）\n"
            "/admin_help - 管理员小本本喵～\n"
        )
        
        # 主人专属命令
        if is_owner:
            help_text += (
                "\n⭐ 主人专属命令：\n"
                "/add_group - 添加大鱼干喵～（主人专属喵）\n"
                "/del_group - 移除大鱼干喵～（主人专属喵）\n"
                "/add_admin - 添加管理员喵～（需要先添加user白名单，主人专属喵～）\n"
                "/del_admin - 删除管理员喵～（主人专属喵～）\n"
                "/list_admin - 管理员列表喵～（主人专属喵～）\n"
                "/error_detail - 错误详细报告喵～\n"
                "/error_clean - 清除错误报告喵～\n"
                "/error_export - 导出错误日志喵～\n"
                "/error_config - 监控错误设置喵～\n"
                "/backup_data - 备份数据喵～\n"
                "/data_stats - 数据统计喵～\n"
                "/delete_user_data - 删除特定小鱼干所有记忆喵～\n"
                "/delete_user_history - 删除特定小鱼干部分说过的话喵～\n"
                "/system_status - 当前小南身体状态喵～\n"
                "/reset_logs - 重置小南脑子喵～（confirm确认喵～）\n"
                "/reset_data - 完全重置小南脑子喵～（confirm确认喵～）\n"
                "/reset_system - 让小南彻底翻新喵～（需要验证码喵～）\n"
                "/clear_confirm_codes - 删除验证码喵～\n"
            )
        
        await update.message.reply_text(help_text)
    
    # ==========================================
    #  主人专属命令（仅主人可用）
    # ==========================================
    
    async def add_group(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """添加大鱼干到白名单~"""
        if not self._check_owner(update, context):
            return
        
        # 如果在群聊中使用，自动获取当前群聊ID
        if update.effective_chat.type in ("group", "supergroup"):
            group_id = update.effective_chat.id
            group_title = update.effective_chat.title or "未知群组"
            
            if self.dm.add_group(group_id):
                await update.message.reply_text(
                    f"✅ 大鱼干已添加~\n"
                    f"📌 群组：{group_title}\n"
                    f"🆔 ID：{group_id}\n"
                    f"这个群现在可以使用我啦！(｡♥‿♥｡)"
                )
            else:
                await update.message.reply_text("😅 这个群已经在鱼干库里啦~")
            return
        
        # 私聊中需要提供群组ID
        if not context.args:
            await update.message.reply_text(
                "用法：/add_group <ID>\n"
                "要把大鱼干给哪个群呢~ 给我群组ID吧！\n"
                "💡 小提示：在群聊中直接使用 /add_group 会自动添加当前群哦！"
            )
            return
        
        try:
            group_id = int(context.args[0])
            if self.dm.add_group(group_id):
                await update.message.reply_text("✅ 大鱼干已添加~ 这个群现在可以使用我啦！(｡♥‿♥｡)")
            else:
                await update.message.reply_text("😅 这个群已经在鱼干库里啦~")
        except ValueError:
            await update.message.reply_text("呜… ID 格式不对呢，要输入数字哦！")
    
    async def del_group(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """移除大鱼干~"""
        if not self._check_owner(update, context):
            return
        if not context.args:
            await update.message.reply_text("用法：/del_group <ID>\n要拿走哪个群的大鱼干呢~")
            return
        try:
            group_id = int(context.args[0])
            if self.dm.del_group(group_id):
                await update.message.reply_text("✅ 已拿走大鱼干~")
            else:
                await update.message.reply_text("😅 这个群本来就没有大鱼干呢~")
        except ValueError:
            await update.message.reply_text("呜… ID 格式不对呢！")
    
    async def add_admin(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """添加管理员~"""
        if not self._check_owner(update, context):
            return
        if not context.args:
            await update.message.reply_text("用法：/add_admin <ID>\n要先添加用户到白名单才能设为管理员哦~")
            return
        try:
            user_id = int(context.args[0])
            if not self.dm.is_user_whitelisted(user_id):
                await update.message.reply_text("😅 这个小可爱还没有小鱼干呢，先用 /add_user 添加吧~")
                return
            if self.dm.add_admin(user_id):
                await update.message.reply_text("✅ 已经成为管理员啦！🎉")
            else:
                await update.message.reply_text("😅 已经是管理员了哦~")
        except ValueError:
            await update.message.reply_text("呜… ID 格式不对呢！")
    
    async def del_admin(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """删除管理员~"""
        if not self._check_owner(update, context):
            return
        if not context.args:
            await update.message.reply_text("用法：/del_admin <ID>\n要拿走谁的管理员小帽子呢~")
            return
        try:
            user_id = int(context.args[0])
            if self.dm.del_admin(user_id):
                await update.message.reply_text("✅ 已拿走管理员小帽子~")
            else:
                await update.message.reply_text("😅 本来就不是管理员呢~")
        except ValueError:
            await update.message.reply_text("呜… ID 格式不对呢！")
    
    async def list_admin(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """管理员列表~"""
        if not self._check_owner(update, context):
            return
        admins = self.dm.get_admins()
        msg = "👑 管理员列表~\n\n"
        if admins:
            msg += f"共有 {len(admins)} 位管理员~\n"
        else:
            msg += "还没有管理员呢~ 用 /add_admin 添加吧！"
        
        await update.message.reply_text(msg)
    
    async def error_detail(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """错误详细报告~"""
        if not self._check_owner(update, context):
            return
        limit = int(context.args[0]) if context.args and context.args[0].isdigit() else 10
        errors = self.dm.get_errors(limit)
        
        if not errors:
            await update.message.reply_text("🎉 目前没有任何错误记录哦~ 小南很健康呢！")
            return
        
        msg = f"📋 最近 {len(errors)} 条错误记录~\n\n"
        for i, err in enumerate(errors, 1):
            msg += f"{i}. 🕐 {err.get('timestamp', '未知')}\n"
            msg += f"   ❌ {err.get('message', '未知错误')[:100]}\n\n"
        
        await update.message.reply_text(msg[:4000])
    
    async def error_clean(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """清除错误报告~"""
        if not self._check_owner(update, context):
            return
        self.dm.clean_errors()
        await update.message.reply_text("✅ 错误报告已清除干净啦~ ✨")
    
    async def error_export(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """导出错误日志~"""
        if not self._check_owner(update, context):
            return
        export_data = self.dm.export_errors()
        await update.message.reply_document(
            document=export_data.encode(),
            filename=f"error_log.txt",
            caption="📋 这是小南的错误日志哦~"
        )
    
    async def error_config(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """错误监控设置~"""
        if not self._check_owner(update, context):
            return
        await update.message.reply_text(
            "⚙️ 错误监控设置~\n\n"
            "当前配置：\n"
            "• 最大记录数：100 条\n"
            "• 自动清理：开启\n\n"
            "如需修改配置，请联系主人哦~"
        )
    
    async def backup_data(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """备份数据~"""
        if not self._check_owner(update, context):
            return
        msg = await update.message.reply_text("🔄 正在备份数据，请稍候~")
        backup_file = self.dm.backup_data()
        if backup_file:
            await msg.edit_text("✅ 数据备份成功！✨")
        else:
            await msg.edit_text("❌ 备份失败啦… 请检查日志喵~")
    
    async def data_stats(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """数据统计~"""
        if not self._check_owner(update, context):
            return
        stats = self.dm.get_stats()
        msg = (
            "📊 小南的数据统计~\n\n"
            f"🐟 白名单用户：{stats['whitelist_users']} 人\n"
            f"🐋 白名单群组：{stats['whitelist_groups']} 个\n"
            f"👑 管理员：{stats['admins']} 人\n"
            f"💬 总用户数：{stats['total_users']} 人\n"
            f"❌ 错误记录：{stats['total_errors']} 条\n"
            f"💾 备份数量：{stats['backup_count']} 个"
        )
        await update.message.reply_text(msg)
    
    async def delete_user_data(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """删除特定小鱼干所有记忆~"""
        if not self._check_owner(update, context):
            return
        if not context.args:
            await update.message.reply_text("用法：/delete_user_data <ID>\n要删除谁的记忆呢~")
            return
        try:
            user_id = int(context.args[0])
            if self.dm.delete_user_data(user_id):
                await update.message.reply_text("✅ 已删除该用户的记忆~ 🧹")
            else:
                await update.message.reply_text("😅 该用户本来就没有记忆呢~")
        except ValueError:
            await update.message.reply_text("呜… ID 格式不对呢！")
    
    async def delete_user_history(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """删除特定小鱼干部分说过的话~"""
        if not self._check_owner(update, context):
            return
        if not context.args:
            await update.message.reply_text("用法：/delete_user_history <ID>\n要删除谁的聊天记录呢~")
            return
        try:
            user_id = int(context.args[0])
            if self.dm.delete_user_history(user_id):
                await update.message.reply_text("✅ 已删除该用户的聊天记录~ 🧹")
            else:
                await update.message.reply_text("😅 该用户本来就没有聊天记录呢~")
        except ValueError:
            await update.message.reply_text("呜… ID 格式不对呢！")
    
    async def reset_logs(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """重置小南脑子~"""
        if not self._check_owner(update, context):
            return
        keyboard = [[
            InlineKeyboardButton("✅ 确认重置", callback_data="confirm_reset_logs"),
            InlineKeyboardButton("❌ 取消", callback_data="confirm_cancel")
        ]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            "⚠️ 确定要重置日志吗？\n这个操作会清除所有错误记录哦！",
            reply_markup=reply_markup
        )
    
    async def reset_data(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """完全重置小南脑子~"""
        if not self._check_owner(update, context):
            return
        keyboard = [[
            InlineKeyboardButton("✅ 确认重置", callback_data="confirm_reset_data"),
            InlineKeyboardButton("❌ 取消", callback_data="confirm_cancel")
        ]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            "⚠️⚠️ 确定要完全重置数据吗？\n这会清除所有白名单、管理员和用户数据！",
            reply_markup=reply_markup
        )
    
    async def reset_system(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """让小南彻底翻新~"""
        if not self._check_owner(update, context):
            return
        
        code = _generate_code()
        _confirm_codes[code] = update.effective_user.id
        
        await update.message.reply_text(
            f"⚠️⚠️⚠️ 彻底翻新警告！\n\n"
            f"此操作会删除所有数据，包括备份！\n"
            f"请输入验证码确认：{code}\n\n"
            f"使用 /clear_confirm_codes 可以取消此操作~"
        )
    
    async def clear_confirm_codes(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """删除验证码~"""
        if not self._check_owner(update, context):
            return
        _confirm_codes.clear()
        await update.message.reply_text("✅ 所有验证码已清除~")
    
    async def confirm_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """处理确认回调~"""
        query = update.callback_query
        await query.answer()
        
        action = query.data.replace("confirm_", "")
        
        if action == "cancel":
            await query.edit_message_text("✅ 操作已取消~")
            return
        
        if action == "reset_logs":
            self.dm.reset_logs()
            await query.edit_message_text("✅ 日志已重置完成~ ✨")
        elif action == "reset_data":
            self.dm.reset_data()
            await query.edit_message_text("✅ 数据已完全重置~ ✨")
    
    # ===== 权限检查 =====
    
    def _check_owner(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
        """检查是否是主人~"""
        user_id = update.effective_user.id
        if not self.dm.is_owner(user_id):
            context.application.create_task(
                update.message.reply_text("呜… 你不是我的主人，不能使用这个命令哦！(｡•́︿•̀｡)")
            )
            return False
        return True
    
    def _check_admin(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
        """检查是否是管理员或主人~"""
        user_id = update.effective_user.id
        if not (self.dm.is_owner(user_id) or self.dm.is_admin(user_id)):
            context.application.create_task(
                update.message.reply_text("呜… 你没有权限使用这个命令哦！需要管理员权限呢~ (｡•́︿•̀｡)")
            )
            return False
        return True
    
    def get_help_text(self) -> str:
        """返回帮助文本~"""
        return (
            "/add_user <ID> - 添加小鱼干~\n"
            "/del_user <ID> - 拿走小鱼干~\n"
            "/list_whitelist - 看看鱼干库~"
        )
