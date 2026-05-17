"""
系统模块~ 小南的身体状态和系统管理！(｡･ω･｡)ﾉ♡
"""
import logging
import time
import psutil

from telegram import Update
from telegram.ext import CommandHandler, ContextTypes

from config import BOT_NAME
from .base_module import BaseModule
from .data_manager import DataManager

logger = logging.getLogger(__name__)


class System(BaseModule):
    """系统模块~ 负责监控小南的身体状况！"""
    
    name = "system"
    description = "查看小南的身体状态~"
    
    def __init__(self, bot_app=None):
        super().__init__(bot_app)
        self.dm = DataManager()
        self.start_time = time.time()
    
    def register_handlers(self, application):
        """注册命令处理器~"""
        application.add_handler(CommandHandler("start", self.start_cmd))
        application.add_handler(CommandHandler("status", self.status))
        application.add_handler(CommandHandler("system_status", self.system_status))
        application.add_handler(CommandHandler("role", self.role))
        application.add_handler(CommandHandler("clear", self.clear_memory))
        application.add_handler(CommandHandler("reset", self.reset))
    
    async def start_cmd(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """/start - 我是混日子的喵～"""
        user = update.effective_user
        user_name = user.first_name or "小可爱"
        
        # 检查是否有验证码需要处理
        from .admin import _confirm_codes
        if context.args and context.args[0] in _confirm_codes:
            code = context.args[0]
            owner_id = _confirm_codes.get(code)
            if owner_id == user.id:
                self.dm.reset_system()
                del _confirm_codes[code]
                await update.message.reply_text(
                    "🔄 小南已彻底翻新完成！✨\n\n"
                    "所有数据都已清除，小南现在焕然一新啦~\n"
                    "重新开始吧！喵！(｡♥‿♥｡)"
                )
                return
            else:
                await update.message.reply_text("❌ 验证码错误哦~ 你不是发起这个操作的主人呢！")
                return
        
        welcome_text = (
            f"😺 嗨嗨~ {user_name}！\n\n"
            f"我是 小南，一只混日子的喵~ 🐱\n\n"
            f"✨ 我的功能：\n"
            f"💬 和 AI 聊天~\n"
            f"🎭 切换性格 (/role)\n"
            f"📊 查看状态 (/status)\n"
            f"📚 查看帮助 (/help)\n\n"
            f"有什么想和我聊的吗？喵~ (｡♥‿♥｡)"
        )
        
        await update.message.reply_text(welcome_text)
    
    async def status(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """/status - 查看状态喵"""
        uptime_seconds = int(time.time() - self.start_time)
        uptime_str = self._format_uptime(uptime_seconds)
        stats = self.dm.get_stats()
        
        status_text = (
            f"😺 小南的状态~\n\n"
            f"⏱ 已陪伴大家：{uptime_str}\n"
            f"💬 聊过的小可爱：{stats['total_users']} 人\n"
            f"👑 管理员：{stats['admins']} 人\n"
            f"❌ 小失误：{stats['total_errors']} 次\n\n"
            f"小南今天也很健康哦~ 喵！✨"
        )
        
        await update.message.reply_text(status_text)
    
    async def system_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """/system_status - 当前小南身体状态喵"""
        user_id = update.effective_user.id
        if not (self.dm.is_owner(user_id) or self.dm.is_admin(user_id)):
            await update.message.reply_text("呜… 你没有权限查看这个哦！需要管理员权限呢~ (｡•́︿•̀｡)")
            return
        
        uptime_seconds = int(time.time() - self.start_time)
        uptime_str = self._format_uptime(uptime_seconds)
        
        cpu_percent = psutil.cpu_percent(interval=0.3)
        memory = psutil.virtual_memory()
        process = psutil.Process()
        memory_mb = process.memory_info().rss / 1024 / 1024
        
        system_text = (
            f"🖥 小南的身体检查报告~\n\n"
            f"⏱ 已运行：{uptime_str}\n"
            f"🧠 脑子占用：{memory_mb:.1f} MB\n"
            f"⚡ CPU 活力：{cpu_percent}%\n"
            f"💾 内存用量：{memory.percent}%\n\n"
            f"小南的身体很健康哦~ 喵！(｡♥‿♥｡)"
        )
        
        await update.message.reply_text(system_text)
    
    async def role(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """/role - 切换性格喵～"""
        user_id = update.effective_user.id
        user_data = self.dm.get_user_data(user_id)
        
        personalities = {
            "default": "😺 默认模式 - 普通可爱的小南",
            "tsundere": "😤 傲娇模式 - 哼！才不是特意为你这样的呢！",
            "loli": "🎀 萝莉模式 - 欧尼酱~ 一起玩吧！",
            "senpai": "👓 前辈模式 - 让我来教你吧~",
            "yandere": "💕 病娇模式 - 你是我的… 永远都是我的…",
            "sleepy": "😴 慵懒模式 - 哈啊~ 好困… 不想动…",
            "gamer": "🎮 游戏模式 - 来开黑吗？我超强的！",
        }
        
        if context.args:
            new_role = context.args[0].lower()
            if new_role in personalities:
                user_data["personality"] = new_role
                self.dm.save_user_data(user_id, user_data)
                await update.message.reply_text(
                    f"🎭 性格已切换为：{personalities[new_role]}\n"
                    f"从现在开始，我会用这种性格和你聊天哦~ 喵！"
                )
            else:
                await update.message.reply_text(
                    f"😅 没有这种性格呢~ 可选性格有：\n\n" +
                    "\n".join([f"  • {k}" for k in personalities.keys()]) +
                    "\n\n用法：/role <性格名称>"
                )
        else:
            current = user_data.get("personality", "default")
            current_desc = personalities.get(current, "未知")
            
            await update.message.reply_text(
                f"🎭 性格切换~\n\n"
                f"当前性格：{current_desc}\n\n"
                f"可选性格：\n" +
                "\n".join([f"  • {k}" for k in personalities.keys()]) +
                f"\n\n用法：/role <性格名称>"
            )
    
    async def clear_memory(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """/clear - 清空我对你的印象喵～"""
        user_id = update.effective_user.id
        if self.dm.delete_user_history(user_id):
            await update.message.reply_text("🧹 已清空我对你的印象~ 我们重新认识一下吧！(｡♥‿♥｡)")
        else:
            await update.message.reply_text("😅 我本来就没有关于你的印象呢~")
    
    async def reset(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """/reset - 完全重置喵～"""
        user_id = update.effective_user.id
        if self.dm.delete_user_data(user_id):
            await update.message.reply_text(
                "🔄 已完全重置~\n\n"
                "关于你的一切记忆都消失啦…\n"
                "不过没关系，我们可以重新开始！喵~ (｡♥‿♥｡)"
            )
        else:
            await update.message.reply_text("😅 我本来就没有关于你的数据呢~")
    
    def _format_uptime(self, seconds: int) -> str:
        """格式化运行时间~"""
        days = seconds // 86400
        hours = (seconds % 86400) // 3600
        minutes = (seconds % 3600) // 60
        secs = seconds % 60
        
        parts = []
        if days > 0:
            parts.append(f"{days}天")
        if hours > 0:
            parts.append(f"{hours}小时")
        if minutes > 0:
            parts.append(f"{minutes}分")
        parts.append(f"{secs}秒")
        
        return "".join(parts)
    
    def get_help_text(self) -> str:
        """返回帮助文本~"""
        return (
            "/start - 我是混日子的喵～\n"
            "/role - 切换性格喵～\n"
            "/status - 查看状态喵\n"
            "/clear - 清空我对你的印象喵～\n"
            "/reset - 完全重置喵～\n"
            "/system_status - 当前小南身体状态喵"
        )
