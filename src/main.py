"""
小南专属TGbot - 主程序入口
一只可可爱爱的 Telegram 机器人，支持 DeepSeek AI 对话~ ✨
"""
import logging
import sys
import os

from telegram import Update
from telegram.ext import Application, ContextTypes

# 确保项目根目录在 Python 路径中
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import TELEGRAM_BOT_TOKEN, BOT_NAME
from modules.module_loader import ModuleLoader
from modules.data_manager import DataManager

# 二次元风格日志
from modules.anime_logger import setup_anime_logging, print_banner, print_module_load, print_separator, Colors

# 设置二次元风格日志
setup_anime_logging()
logger = logging.getLogger(__name__)


class BotApp:
    """机器人主应用类~ 负责启动和管理所有小模块喵！"""
    
    def __init__(self):
        self.module_loader = ModuleLoader()
        self.application = None
        self.dm = DataManager()
    
    def setup(self):
        """初始化机器人~ 准备启动啦！"""
        # 打印启动横幅
        print_banner()
        print_separator("═", 50)
        
        logger.info(f"🚀 {BOT_NAME} 正在启动...")
        print()
        
        # 检查 Token 是否已配置
        if not TELEGRAM_BOT_TOKEN or TELEGRAM_BOT_TOKEN == "YOUR_TELEGRAM_BOT_TOKEN":
            logger.error("呜哇！请在 config.py 中设置 TELEGRAM_BOT_TOKEN 啦！")
            sys.exit(1)
        
        # 检查主人 ID 是否已配置
        from config import BOT_OWNER_ID
        if BOT_OWNER_ID is None:
            logger.warning("⚠️ BOT_OWNER_ID 未设置，主人专属命令将不可用~")
        
        # 创建 Application
        self.application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
        
        # 加载模块
        print()
        logger.info("📦 正在加载模块...")
        loaded_modules = self.module_loader.load_modules(self.application)
        
        print()
        print_separator("─", 40)
        logger.info(f"🎉 成功加载了 {len(loaded_modules)} 个模块:")
        for module_name in loaded_modules:
            print_module_load(module_name)
        print_separator("─", 40)
        print()
        
        # 注册错误处理器
        self.application.add_error_handler(self.error_handler)
    
    def get_help_text(self) -> str:
        """获取帮助文本（供模块调用）"""
        return self.module_loader.get_help_text()
    
    async def error_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """全局错误处理器~ 出错了也不怕！"""
        error_msg = str(context.error)
        
        # ========== 错误分析与中文提示 ==========
        
        # 1. Conflict 错误：旧会话冲突
        if "Conflict" in error_msg:
            logger.warning(
                "⚠️ 检测到旧会话冲突\n"
                "   ├─ 原因：上一个机器人实例未正常关闭，Telegram 服务器还保留着旧连接\n"
                "   ├─ 影响：新实例无法获取消息，但不会导致崩溃\n"
                "   ├─ 解决：自动杀掉旧进程，释放连接\n"
                "   └─ 状态：正在等待自动恢复..."
            )
            # 自动杀掉最先启动的旧进程
            try:
                import subprocess
                import platform
                if platform.system() == "Windows":
                    # 获取所有 python 进程，按启动时间排序，杀掉最早的那个
                    result = subprocess.run(
                        ["wmic", "process", "where", 'name="python.exe"', "get", "processid,creationdate"],
                        capture_output=True, text=True, timeout=5
                    )
                    lines = [line.strip() for line in result.stdout.split("\n") if line.strip()]
                    # 跳过标题行，按创建时间排序
                    processes = []
                    for line in lines[1:]:
                        parts = line.split()
                        if len(parts) >= 2 and parts[0].isdigit():
                            processes.append((parts[0], parts[1]))
                    if processes:
                        # 按创建时间排序，取最早的（创建时间最小的）
                        processes.sort(key=lambda x: x[0])
                        oldest_pid = processes[0][1]
                        subprocess.run(
                            ["taskkill", "/F", "/PID", oldest_pid],
                            capture_output=True, text=True, timeout=3
                        )
                        logger.info(f"🔫 已杀掉最早启动的旧进程 (PID: {oldest_pid})")
                else:
                    # Linux/macOS：杀掉最早启动的 python main.py 进程
                    subprocess.run(
                        ["pkill", "-9", "-f", "main.py"],
                        capture_output=True, text=True, timeout=5
                    )
                    logger.info("🔫 已杀掉所有旧 main.py 进程")
            except Exception as e:
                logger.warning(f"⚠️ 自动清理旧进程失败：{e}")
            
            # 检查当前状态
            status = await self._check_bot_status()
            logger.info(f"📊 当前状态检测：{status}")
            return
        
        # 2. Timed out 错误：连接超时
        if "Timed out" in error_msg or "timeout" in error_msg.lower():
            logger.warning(
                "⚠️ 连接 Telegram API 超时\n"
                "   ├─ 原因：网络环境无法访问 Telegram 服务器\n"
                "   ├─ 影响：消息发送/接收延迟或失败\n"
                "   ├─ 解决：请确保已开启代理软件（Clash/v2ray/SSR 等）\n"
                "   └─ 状态：机器人会继续尝试重连..."
            )
            # 检查当前状态
            status = await self._check_bot_status()
            logger.info(f"📊 当前状态检测：{status}")
            return
        
        # 3. NetworkError 错误：网络异常
        if "NetworkError" in error_msg or "Connection" in error_msg:
            logger.warning(
                "⚠️ 网络连接异常\n"
                "   ├─ 原因：与 Telegram 服务器的网络连接中断\n"
                "   ├─ 影响：机器人暂时离线\n"
                "   ├─ 解决：检查网络连接和代理状态\n"
                "   └─ 状态：机器人会自动重连..."
            )
            # 检查当前状态
            status = await self._check_bot_status()
            logger.info(f"📊 当前状态检测：{status}")
            return
        
        # 4. RetryAfter 错误：请求频率限制
        if "RetryAfter" in error_msg:
            logger.warning(
                "⚠️ 请求过于频繁，被 Telegram 限流\n"
                "   ├─ 原因：短时间内发送了太多请求\n"
                "   ├─ 影响：部分消息可能延迟处理\n"
                "   ├─ 解决：无需操作，Telegram 会自动恢复\n"
                "   └─ 状态：等待限流解除..."
            )
            # 检查当前状态
            status = await self._check_bot_status()
            logger.info(f"📊 当前状态检测：{status}")
            return
        
        # 5. 其他未知错误
        error_info = {
            "message": error_msg,
            "update_id": update.update_id if update else None,
            "user_id": update.effective_user.id if update and update.effective_user else None,
        }
        self.dm.add_error(error_info)
        
        logger.error(
            f"💔 遇到未知错误\n"
            f"   ├─ 错误信息：{error_msg}\n"
            f"   ├─ 更新 ID：{update.update_id if update else '无'}\n"
            f"   ├─ 用户 ID：{update.effective_user.id if update and update.effective_user else '无'}\n"
            f"   └─ 已记录到错误日志，可联系开发者查看~"
        )
        
        # 检查当前状态
        status = await self._check_bot_status()
        logger.info(f"📊 当前状态检测：{status}")
        
        if update and update.effective_message:
            await update.effective_message.reply_text(
                "呜… 好像出了点小问题呢(｡•́︿•̀｡)\n"
                "请稍后再试试看吧~ 喵！"
            )
    
    async def _check_bot_status(self) -> str:
        """检查机器人当前状态，返回中文状态描述"""
        try:
            # 尝试获取 bot 信息来检测连接状态
            bot_user = await self.application.bot.get_me()
            if bot_user:
                return "✅ 机器人运行正常，已成功连接到 Telegram 服务器~"
        except Exception as e:
            error_str = str(e)
            if "Conflict" in error_str:
                return "⏳ 旧会话冲突中，等待 Telegram 释放连接..."
            elif "Timed out" in error_str or "timeout" in error_str.lower():
                return "❌ 无法连接到 Telegram 服务器，请检查代理是否开启~"
            elif "NetworkError" in error_str or "Connection" in error_str:
                return "❌ 网络连接中断，请检查网络状态~"
            else:
                return f"⚠️ 状态检测异常：{error_str}"
        return "❓ 无法获取机器人状态~"
    
    def run(self):
        """运行机器人~ 开始和小可爱们聊天啦！"""
        print()
        logger.info(f"✨ {BOT_NAME} 启动成功！开始轮询消息...")
        print(f"{Colors.PINK}{'♥' * 50}{Colors.RESET}")
        print(f"{Colors.HOT_PINK}{Colors.BOLD}    🐱 小南正在等待小可爱们的消息~ 喵呜！(｡♥‿♥｡){Colors.RESET}")
        print(f"{Colors.PINK}{'♥' * 50}{Colors.RESET}")
        print()
        # drop_pending_updates=True 清除旧会话冲突
        self.application.run_polling(
            allowed_updates=Update.ALL_TYPES,
            drop_pending_updates=True
        )


def main():
    """主函数~ 一切从这里开始！"""
    bot = BotApp()
    bot.setup()
    bot.run()


if __name__ == "__main__":
    main()
