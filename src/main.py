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
        error_info = {
            "message": str(context.error),
            "update_id": update.update_id if update else None,
            "user_id": update.effective_user.id if update and update.effective_user else None,
        }
        self.dm.add_error(error_info)
        
        logger.error(f"💔 更新 {update} 导致错误 {context.error}")
        
        if update and update.effective_message:
            await update.effective_message.reply_text(
                "呜… 好像出了点小问题呢(｡•́︿•̀｡)\n"
                "请稍后再试试看吧~ 喵！"
            )
    
    def run(self):
        """运行机器人~ 开始和小可爱们聊天啦！"""
        print()
        logger.info(f"✨ {BOT_NAME} 启动成功！开始轮询消息...")
        print(f"{Colors.PINK}{'♥' * 50}{Colors.RESET}")
        print(f"{Colors.HOT_PINK}{Colors.BOLD}    🐱 小南正在等待小可爱们的消息~ 喵呜！(｡♥‿♥｡){Colors.RESET}")
        print(f"{Colors.PINK}{'♥' * 50}{Colors.RESET}")
        print()
        self.application.run_polling(allowed_updates=Update.ALL_TYPES)


def main():
    """主函数~ 一切从这里开始！"""
    bot = BotApp()
    bot.setup()
    bot.run()


if __name__ == "__main__":
    main()
