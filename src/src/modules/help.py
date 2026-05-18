"""
帮助模块~ 小南的小本本！(｡･ω･｡)ﾉ♡
"""
import logging
import os
import sys

from telegram import Update
from telegram.ext import CommandHandler, ContextTypes

from .base_module import BaseModule

logger = logging.getLogger(__name__)

# 指令列表文件路径（在 src/deploy 文件夹中）
COMMANDS_FILE = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", "deploy", "指令集.txt"
)


def _load_commands() -> dict:
    """从指令集.txt 加载指令列表~"""
    commands = {}
    current_category = "未分类"
    
    if not os.path.exists(COMMANDS_FILE):
        logger.warning(f"找不到指令文件 {COMMANDS_FILE}")
        return commands
    
    try:
        with open(COMMANDS_FILE, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                
                # 跳过空行和注释
                if not line or line.startswith("#"):
                    continue
                
                # 检测分类标签
                if line.startswith("[") and line.endswith("]"):
                    current_category = line[1:-1]
                    if current_category not in commands:
                        commands[current_category] = []
                    continue
                
                # 解析指令行：指令名 - 说明
                if " - " in line:
                    parts = line.split(" - ", 1)
                    cmd_name = parts[0].strip()
                    cmd_desc = parts[1].strip()
                    
                    if current_category not in commands:
                        commands[current_category] = []
                    
                    commands[current_category].append({
                        "name": cmd_name,
                        "desc": cmd_desc
                    })
    except Exception as e:
        logger.error(f"读取指令文件失败: {e}")
    
    return commands


class Help(BaseModule):
    """帮助模块~ 负责展示所有命令的说明！"""
    
    name = "help"
    description = "查看帮助喵～"
    
    def __init__(self, bot_app=None):
        super().__init__(bot_app)
        self.bot_app = bot_app
    
    def register_handlers(self, application):
        """注册帮助命令~"""
        application.add_handler(CommandHandler("help", self.help_command))
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """/help - 查看帮助喵～"""
        user_id = update.effective_user.id
        
        from .data_manager import DataManager
        dm = DataManager()
        is_owner = dm.is_owner(user_id)
        is_admin = dm.is_admin(user_id)
        
        # 从 commands.txt 加载指令
        all_commands = _load_commands()
        
        help_text = "📚 小南的帮助小本本~\n\n"
        
        # 遍历所有分类
        for category, cmds in all_commands.items():
            # 判断分类是否对当前用户可见
            if category == "管理命令" and not (is_owner or is_admin):
                continue
            
            help_text += f"【{category}】\n"
            for cmd in cmds:
                help_text += f"/{cmd['name']} - {cmd['desc']}\n"
            help_text += "\n"
        
        help_text += "💡 有什么问题都可以问我哦~ 喵！(｡♥‿♥｡)"
        
        await update.message.reply_text(help_text)
    
    def get_help_text(self) -> str:
        """返回帮助文本~"""
        return "/help - 查看帮助喵～"
