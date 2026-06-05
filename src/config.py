"""
配置文件~ 请在这里填写你的小秘密哦(｡♥‿♥｡)
"""
import os

# Telegram Bot 配置
TELEGRAM_BOT_TOKEN = "7435553023:AAFAVnI8TfkBxnFASZNYyniKj4OE0DwAx1s"  # 从 @BotFather 那里拿到的小钥匙🔑

# DeepSeek API 配置
DEEPSEEK_API_KEY = "sk-0a539536cb6a4a44a4f14e88fdef6ef0"      # 从 DeepSeek 平台获取的魔法钥匙✨
DEEPSEEK_API_URL = "https://api.deepseek.com/v1/chat/completions"
DEEPSEEK_MODEL = "deepseek-chat"

# 机器人配置
BOT_NAME = "小南专属TGbot"  # 机器人的全称
BOT_NAME_SHORT = "小南"      # 机器人的简称（在对话中显示的名字~）
BOT_OWNER_NAME = "主人"      # 主人的名字（会显示在欢迎消息等地方哦~）
BOT_OWNER_ID = 7609256840    # 主人的 Telegram ID（填上才能用主人专属命令哦~）
DEFAULT_PERSONALITY = "default"  # 默认性格 ID（对应 personalities.py 中的 id）
MAX_HISTORY_LENGTH = 10  # 每个小可爱最多保留的对话历史条数~

# 数据文件路径
DATA_DIR = "data"
WHITELIST_FILE = "data/whitelist.json"
ADMIN_FILE = "data/admins.json"
USER_DATA_FILE = "data/user_data.json"
ERROR_LOG_FILE = "data/errors.json"
BACKUP_DIR = "data/backups"
PAID_WHITELIST_FILE = "data/paid_whitelist.json"  # 付费白名单数据文件
PRODUCTS_FILE = "data/products.json"  # 商品配置数据文件

# Webhook 回调服务配置
CALLBACK_HOST = "0.0.0.0"  # 监听地址（0.0.0.0 表示所有网卡）
CALLBACK_PORT = 9876       # 监听端口（如果被占用可以改）
CALLBACK_SECRET = "xiaonan_callback_secret_2024"  # 回调密钥，发卡平台配置用这个验证

# 模块配置
# 模块已改为自动扫描加载~
# 把 .py 文件丢进 src/modules/ 目录就会自动加载啦！(๑•̀ㅂ•́)و✧
