"""
配置文件~ 请在这里填写你的小秘密哦(｡♥‿♥｡)
"""
import os

# Telegram Bot 配置
TELEGRAM_BOT_TOKEN = "YOUR_TELEGRAM_BOT_TOKEN"  # 从 @BotFather 那里拿到的小钥匙🔑

# DeepSeek API 配置
DEEPSEEK_API_KEY = "YOUR_DEEPSEEK_API_KEY"      # 从 DeepSeek 平台获取的魔法钥匙✨
DEEPSEEK_API_URL = "https://api.deepseek.com/v1/chat/completions"
DEEPSEEK_MODEL = "deepseek-chat"

# 机器人配置
BOT_NAME = "小南专属TGbot"
BOT_OWNER_NAME = "主人"  # 主人的名字（会显示在欢迎消息等地方哦~）
BOT_OWNER_ID = None  # 主人的 Telegram ID（填上才能用主人专属命令哦~）
MAX_HISTORY_LENGTH = 10  # 每个小可爱最多保留的对话历史条数~

# 数据文件路径
DATA_DIR = "data"
WHITELIST_FILE = "data/whitelist.json"
ADMIN_FILE = "data/admins.json"
USER_DATA_FILE = "data/user_data.json"
ERROR_LOG_FILE = "data/errors.json"
BACKUP_DIR = "data/backups"

# 模块配置
ENABLED_MODULES = [
    "deepseek_chat",  # DeepSeek AI 对话模块
    "help",           # 帮助模块
    "admin",          # 管理模块
    "system",         # 系统模块
    "fun",            # 娱乐模块
    # 在这里添加更多模块吧(๑•̀ㅂ•́)و✧
]
