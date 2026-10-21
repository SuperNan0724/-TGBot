"""
系统模块~ 小南的身体状态和系统管理！(｡･ω･｡)ﾉ♡
"""
import asyncio
import logging
import time
import psutil

from telegram import Update
from telegram.ext import CommandHandler, ContextTypes

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
        # /role 由 deepseek_chat 提供（翻页性格菜单），这里再注册会被前面的模块抢走、永远不执行
        application.add_handler(CommandHandler("clear", self.clear_memory))
        application.add_handler(CommandHandler("reset", self.reset))
    
    def _skip_channel(self, update: Update) -> bool:
        """频道里的 Update 没有 effective_user，取 .id 就会 AttributeError，直接跳过~"""
        if update.effective_user is None:
            logger.warning("在频道里收到了命令，但频道消息没有用户信息，已忽略~")
            return True
        return False
    
    async def start_cmd(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """/start - 我是混日子的喵～"""
        # 频道里发命令时 effective_user 是 None，直接取属性会 AttributeError
        if self._skip_channel(update):
            return
        user = update.effective_user
        user_name = user.first_name or "小可爱"
        
        # 验证码走 admin.py 里唯一的那个校验入口（consume_confirm_code）：
        # 命中的码当场被消费掉，没命中就当普通 /start 处理。
        # 以前这里自己 import 了 admin 的 _confirm_codes 再 get/del 一遍，
        # 和 admin 的 /reset_system <code> 各写一套判断——两边的规则（比如
        # 新加的过期时间、次数上限）只能靠人肉同步，迟早漂移成"一个通道能
        # 兑现过期的码、另一个不能"。现在两条通道共用同一份代码。
        from .admin import consume_confirm_code
        if context.args:
            result = consume_confirm_code(context.args[0], user.id)
            if result == "ok":
                self.dm.reset_system()
                await update.message.reply_text(
                    "🔄 小南已彻底翻新完成！✨\n\n"
                    "所有数据都已清除，小南现在焕然一新啦~\n"
                    "重新开始吧！喵！(｡♥‿♥｡)"
                )
                return
            if result == "not_owner":
                await update.message.reply_text("❌ 验证码错误哦~ 你不是发起这个操作的主人呢！")
                return
            # "missing"：不是验证码，当成普通 /start 继续往下走
        
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
        # 频道里发命令时 update.message 是 None（消息在 channel_post 里），
        # 直接 reply_text 会 AttributeError；这个命令谁的权限都要不，所以
        # 以前是真会炸的，这里和其它命令一样先挡掉频道
        if self._skip_channel(update):
            return
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
        if self._skip_channel(update):
            return
        user_id = update.effective_user.id
        if not (self.dm.is_owner(user_id) or self.dm.is_admin(user_id)):
            await update.message.reply_text("呜… 你没有权限查看这个哦！需要管理员权限呢~ (｡•́︿•̀｡)")
            return
        
        uptime_seconds = int(time.time() - self.start_time)
        uptime_str = self._format_uptime(uptime_seconds)
        
        # 带 interval 的采样会 sleep 0.3 秒，直接在事件循环里调用会把整个机器人
        # 卡住 0.3 秒（这期间所有用户的消息都排队），所以丢到线程里采样~
        cpu_percent = await asyncio.to_thread(psutil.cpu_percent, 0.3)
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
    
    async def clear_memory(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """/clear - 清空我对你的印象喵～"""
        if self._skip_channel(update):
            return
        user_id = update.effective_user.id
        if self.dm.delete_user_history(user_id):
            await update.message.reply_text("🧹 已清空我对你的印象~ 我们重新认识一下吧！(｡♥‿♥｡)")
        else:
            await update.message.reply_text("😅 我本来就没有关于你的印象呢~")
    
    async def reset(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """/reset - 完全重置喵～"""
        if self._skip_channel(update):
            return
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
        # 系统时钟被往回拨时，start_time 会"在未来"，差值是负数，
        # 会显示成 "-1天23小时…"；这里统一夹到 0
        seconds = max(0, int(seconds))
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
